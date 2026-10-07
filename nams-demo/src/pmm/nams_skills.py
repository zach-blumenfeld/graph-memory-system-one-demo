"""Stage 4 over REST: generate a skill from recorded conversations, poll the run, review, publish,
download the zip and install it as a Claude Code project skill."""

from __future__ import annotations

import io
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pmm.env import CHECKPOINTS, SKILL_DIR
from pmm.nams_rest import NamsError, NamsRest

SKILL_CKPT_DIR = CHECKPOINTS / "04-skill"
TERMINAL_OUTCOMES = {"created", "withheld", "failed"}
TERMINAL_STATUSES = {"completed", "complete", "succeeded", "success", "failed", "failure", "error", "withheld", "done", "cancelled"}


def _pick(d: dict[str, Any] | None, *keys: str, default: Any = None) -> Any:
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def scope_conversations(ids: list[str], name_hint: str | None = None) -> dict[str, Any]:
    s: dict[str, Any] = {"type": "conversations", "conversationIds": list(ids)}
    if name_hint:
        s["nameHint"] = name_hint
    return s


def scope_workspace() -> dict[str, Any]:
    return {"type": "workspace"}


def generate(nams: NamsRest, scope: dict[str, Any], name_hint: str | None, procedure_format: str = "graph") -> tuple[str, dict[str, Any]]:
    resp = nams.skill_generate(scope, name_hint=name_hint, procedure_format=procedure_format)
    run_id = _pick(resp, "runId", "run_id", "id")
    if not run_id:
        raise RuntimeError(f"generate returned no run id: {json.dumps(resp)[:300]}")
    return str(run_id), resp


def run_outcome(run: dict[str, Any]) -> str | None:
    """Normalise a run to Created | Withheld | Failed, or None while it is still running.

    Observed shape (NAMS 1.1.0): status queued -> synthesizing -> packaging -> succeeded, with
    groundingScore / coverageScore / skillId / skillVersionId / failCode / error / suggestSplitJson."""
    outcome = _pick(run, "outcome")
    if outcome and str(outcome).lower() in TERMINAL_OUTCOMES:
        return str(outcome).capitalize()
    status = str(_pick(run, "status", "state", default="")).lower()
    if status in ("succeeded", "success", "completed", "complete", "done"):
        return "Created" if skill_id_of(run) else "Withheld"
    if status == "withheld":
        return "Withheld"
    if status in ("failed", "failure", "error", "cancelled"):
        return "Failed"
    return None


def wait_run(nams: NamsRest, run_id: str, timeout: float = 1200.0, interval: float = 5.0, log=print) -> dict[str, Any]:
    deadline = time.time() + timeout
    last_stage = None
    while True:
        run = nams.skill_run(run_id)
        stage = _pick(run, "stage", "phase", "step", "status", "state")
        if stage != last_stage:
            log(f"  run {run_id}: {stage}")
            last_stage = stage
        if run_outcome(run):
            return run
        if time.time() > deadline:
            raise TimeoutError(f"distillation run {run_id} did not finish within {timeout:.0f}s; last state: {json.dumps(run)[:300]}")
        time.sleep(interval)


def skill_id_of(run: dict[str, Any]) -> str | None:
    sid = _pick(run, "skillId", "skill_id")
    if sid:
        return str(sid)
    skill = _pick(run, "skill", "result")
    if isinstance(skill, dict):
        return _pick(skill, "skillId", "skill_id", "id")
    return None


def withhold_reason(run: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("failCode", "reason", "withheldReason", "withhold_reason", "message", "error", "details"):
        v = run.get(key)
        if v:
            parts.append(f"{key}={v if isinstance(v, str) else json.dumps(v)[:300]}")
    for key in ("suggestSplitJson", "gates", "gateResults"):
        v = run.get(key)
        if v:
            parts.append(f"{key}={v if isinstance(v, str) else json.dumps(v)[:400]}")
    return "; ".join(parts) if parts else json.dumps(run)[:400]


def install_zip(data: bytes, dest: Path = SKILL_DIR) -> list[str]:
    """Unpack a skill package into dest (flattening a single top-level folder if present)."""
    zf = zipfile.ZipFile(io.BytesIO(data))
    names = [n for n in zf.namelist() if not n.endswith("/")]
    if not names:
        raise RuntimeError("skill zip is empty")
    roots = {n.split("/", 1)[0] for n in names if "/" in n}
    strip = None
    if not any(n == "SKILL.md" for n in names) and len(roots) == 1 and all("/" in n for n in names):
        strip = next(iter(roots)) + "/"
    if dest.exists():
        for p in sorted(dest.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
    dest.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for n in names:
        rel = n[len(strip):] if strip and n.startswith(strip) else n
        if not rel or rel.startswith("/") or ".." in rel.split("/"):
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(zf.read(n))
        written.append(rel)
    if not (dest / "SKILL.md").exists():
        raise RuntimeError(f"no SKILL.md in the skill package (files: {written[:10]})")
    return written


def summarize_skill_dir(dest: Path = SKILL_DIR) -> dict[str, Any]:
    text = (dest / "SKILL.md").read_text()
    front = {}
    if text.startswith("---"):
        for line in text.split("---", 2)[1].strip().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                front[k.strip()] = v.strip().strip('"')
    import re

    steps = [l for l in text.splitlines() if re.match(r"^\s*\d+\.\s+\*\*", l)]
    prov = dest / "provenance.json"
    claims = len(json.loads(prov.read_text()).get("claims", [])) if prov.exists() else 0
    return {"frontmatter": front, "steps": len(steps), "claims": claims, "files": sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())}


def distill(nams: NamsRest, conversation_ids: list[str], *, name_hint: str = "launch-email-blast", fallback_ids: list[str] | None = None, workspace_demo: bool = True, install: bool = True, log=print, out_dir: Path = SKILL_CKPT_DIR, skill_dir: Path = SKILL_DIR) -> dict[str, Any]:
    """The whole Stage 4 flow, unattended. Returns the meta written to checkpoints/04-skill/meta.json."""
    out_dir.mkdir(parents=True, exist_ok=True)
    meta: dict[str, Any] = {"stage": 4, "started_at": _now(), "workspace_id": nams.workspace_id, "name_hint": name_hint, "attempts": [], "capabilities": nams.skill_capabilities()}

    def attempt(label: str, scope: dict[str, Any]) -> dict[str, Any]:
        log(f"generate [{label}]: scope={scope.get('type')} n={len(scope.get('conversationIds', []))} format=graph")
        run_id, resp = generate(nams, scope, name_hint)
        log(f"  enqueued run {run_id}: {json.dumps(resp)[:200]}")
        run = wait_run(nams, run_id, log=log)
        outcome = run_outcome(run) or "?"
        rec = {"label": label, "scope": scope, "run_id": run_id, "outcome": outcome, "skill_id": skill_id_of(run), "skill_version_id": _pick(run, "skillVersionId"),
               "grounding_score": _pick(run, "groundingScore"), "coverage_score": _pick(run, "coverageScore"), "run": run, "finished_at": _now()}
        if outcome.lower() != "created":
            rec["reason"] = withhold_reason(run)
            log(f"  outcome {outcome}: {rec['reason']}")
        else:
            log(f"  outcome Created: skill {rec['skill_id']} (grounding {rec['grounding_score']}, coverage {rec['coverage_score']})")
        meta["attempts"].append(rec)
        (out_dir / f"run-{label}.json").write_text(json.dumps(run, indent=2, default=str) + "\n")
        return rec

    chosen: dict[str, Any] | None = None
    first = attempt("clean-scope", scope_conversations(conversation_ids, name_hint))
    if first["outcome"].lower() == "created" and first["skill_id"]:
        chosen = first
    elif fallback_ids:
        log("falling back to a narrower scope")
        second = attempt("fallback-scope", scope_conversations(fallback_ids, name_hint))
        if second["outcome"].lower() == "created" and second["skill_id"]:
            chosen = second

    if workspace_demo:
        try:
            attempt("workspace-scope-demo", scope_workspace())
        except Exception as exc:  # the deliberate-failure demo must never block the flow
            log(f"  workspace-scope demo errored: {exc}")
            meta["attempts"].append({"label": "workspace-scope-demo", "error": str(exc)})

    if chosen is None:
        meta["result"] = "no skill created"
        meta["finished_at"] = _now()
        (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")
        return meta

    skill_id = chosen["skill_id"]
    meta["skill_id"] = skill_id
    meta["run_id"] = chosen["run_id"]
    detail = nams.skill(skill_id)
    (out_dir / "skill.json").write_text(json.dumps(detail, indent=2, default=str) + "\n")
    try:
        prov = nams.skill_explain_provenance(skill_id)
        (out_dir / "provenance-explain.json").write_text(json.dumps(prov, indent=2, default=str) + "\n")
        meta["provenance_explain"] = prov if len(json.dumps(prov)) < 4000 else {"truncated": True}
    except NamsError as exc:
        log(f"  explain-provenance: {exc}")
    log(f"review: approve {skill_id}")
    meta["review"] = nams.skill_review(skill_id, "approve", "Approved unattended by pmm distill; provenance summary in BUILD-LOG.md")
    log(f"publish: {skill_id}")
    meta["publish"] = nams.skill_publish(skill_id)
    data = nams.skill_download(skill_id)
    zip_path = out_dir / f"{name_hint}.zip"
    zip_path.write_bytes(data)
    meta["zip"] = str(zip_path)
    meta["zip_bytes"] = len(data)
    log(f"downloaded {len(data)} bytes -> {zip_path}")
    if install:
        files = install_zip(data, skill_dir)
        meta["installed"] = files
        meta["skill_summary"] = summarize_skill_dir(skill_dir)
        log(f"installed {len(files)} files into {skill_dir}")
    try:
        meta["drift"] = nams.skill_drift(skill_id)
    except NamsError as exc:
        meta["drift"] = {"error": str(exc)}
    meta["result"] = "published"
    meta["finished_at"] = _now()
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, default=str) + "\n")
    return meta
