"""pmm: one CLI for every stage of the demo."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import typer

from pmm import __version__
from pmm.env import CHECKPOINTS, ONTOLOGY_FILE, REQUIRED_KEYS, ROOT, SKILL_DIR, ensure_run_dirs, load_dotenv, require
from pmm.fixture import Fixture
from pmm.nams_rest import NamsError, NamsRest

app = typer.Typer(no_args_is_help=True, add_completion=False, help="System One demo: PMM tools, traces, distillation.")
workspace_app = typer.Typer(help="NAMS workspace database mode")
ontology_app = typer.Typer(help="PMM ontology in NAMS")
notion_app = typer.Typer(help="Simulated Notion fixture")
traces_app = typer.Typer(help="Recorded traces: ids, export, replay")
skill_app = typer.Typer(help="Distilled skill lifecycle")
app.add_typer(workspace_app, name="workspace")
app.add_typer(ontology_app, name="ontology")
app.add_typer(notion_app, name="notion")
app.add_typer(traces_app, name="traces")
app.add_typer(skill_app, name="skill")


def say(msg: str) -> None:
    typer.echo(msg)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_checkpoint(name: str, data: dict[str, Any]) -> Path:
    CHECKPOINTS.mkdir(exist_ok=True)
    p = CHECKPOINTS / name
    p.write_text(json.dumps(data, indent=2, default=str) + "\n")
    say(f"checkpoint written: {p.relative_to(ROOT)}")
    return p


def aura_node_count() -> int:
    env = require("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")
    from neo4j import GraphDatabase

    with GraphDatabase.driver(env["NEO4J_URI"], auth=(env["NEO4J_USERNAME"], env["NEO4J_PASSWORD"])) as d:
        recs, _, _ = d.execute_query("MATCH (n) RETURN count(n) AS n", database_=os.environ.get("NEO4J_DATABASE", "neo4j"))
        return int(recs[0]["n"])


# ====================================================================== stage 0
@app.command()
def doctor() -> None:
    """Check keys, NAMS workspace, Aura, a live Jev round trip, Claude Code and the server selftest. Any failure is an error."""
    load_dotenv()
    failures: list[str] = []
    missing = [k for k in REQUIRED_KEYS if not os.environ.get(k)]
    say(f"[keys] {'all present' if not missing else 'MISSING: ' + ', '.join(missing)}")
    if missing:
        failures.append("missing keys")
    nams: NamsRest | None = None
    if not missing:
        try:
            nams = NamsRest()
            v = nams.version()
            ws = nams.workspace()
            db = nams.database()
            say(f"[nams] api {v.get('version')} ({v.get('released')}); workspace {ws.get('name')!r} status={ws.get('status')} db mode={db.get('mode')}")
            if ws.get("status") != "active":
                failures.append(f"workspace status is {ws.get('status')} (run `pmm workspace attach`)")
            caps = nams.skill_capabilities()
            say(f"[nams] skills: distillation={caps.get('distillation')} grounding>={caps.get('groundingThreshold')} coverage>={caps.get('coverageThreshold')}")
        except Exception as exc:
            say(f"[nams] FAILED: {exc}")
            failures.append("nams")
        try:
            n = aura_node_count()
            say(f"[aura] connected to {os.environ['NEO4J_URI'].split('@')[-1]}; {n} nodes")
        except Exception as exc:
            say(f"[aura] FAILED: {type(exc).__name__}: {exc}")
            failures.append("aura")
        try:
            from pmm.decisions import TypeSafeSystemOne

            t0 = time.perf_counter()
            r = TypeSafeSystemOne().system_one({"text": "pmm doctor ping"}, {"ok": {"type": "noul", "instructions": "Is this a health-check ping?"}})
            say(f"[jev] {r.get('model')} answered in {time.perf_counter() - t0:.2f}s (noul={r['answers']['ok']['noul']})")
        except Exception as exc:
            say(f"[jev] FAILED: {exc}")
            failures.append("jev")
    try:
        out = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=30)
        say(f"[claude] {out.stdout.strip() or out.stderr.strip()}")
        if out.returncode != 0:
            failures.append("claude")
    except Exception as exc:
        say(f"[claude] FAILED: {exc}")
        failures.append("claude")
    out = subprocess.run([sys.executable, "-m", "pmm.mcp_server", "--selftest"], capture_output=True, text=True, cwd=ROOT)
    selftest_line = out.stdout.strip() or (out.stderr.strip().splitlines()[-1] if out.stderr.strip() else "no output")
    say(f"[pmm-tools] {selftest_line}")
    if out.returncode != 0:
        failures.append("selftest")
    if failures:
        say(f"doctor: FAILED ({', '.join(failures)})")
        raise typer.Exit(1)
    if nams is not None:
        write_checkpoint("00-env.json", {
            "stage": 0, "checked_at": now(), "workspace_id": nams.workspace_id, "workspace_name": nams.workspace().get("name"),
            "db_mode": nams.database().get("mode"), "nams_api_version": nams.version().get("version"),
            "pmm_version": __version__, "claude_code": subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip(),
            "python": sys.version.split()[0], "aura_instance": os.environ.get("AURA_INSTANCEID"),
        })
    say("doctor: OK")


@workspace_app.command("status")
def workspace_status() -> None:
    nams = NamsRest()
    say(json.dumps({"workspace": nams.workspace(), "database": {k: v for k, v in nams.database().items() if k != "connection"}}, indent=2))


@workspace_app.command("attach")
def workspace_attach(force: bool = typer.Option(False, help="attach even if the Aura database already has nodes"), timeout: int = 900) -> None:
    """Switch the NAMS workspace to external mode on the Aura database from .env and wait until it is active."""
    env = require("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")
    nams = NamsRest()
    db = nams.database()
    ws = nams.workspace()
    if ws.get("status") == "active":
        say(f"workspace {ws.get('name')!r} is already active in {db.get('mode')} mode; nothing to do")
        return
    n = aura_node_count()
    if n and not force:
        say(f"refusing: the Aura database already holds {n} nodes (use --force to attach anyway)")
        raise typer.Exit(2)
    say(f"testing connection through NAMS ...")
    say(f"  {nams.test_connection(env['NEO4J_URI'], env['NEO4J_USERNAME'], env['NEO4J_PASSWORD'], database)}")
    try:
        resp = nams.set_database_external(env["NEO4J_URI"], env["NEO4J_USERNAME"], env["NEO4J_PASSWORD"], database)
    except NamsError as exc:
        if exc.status == 403:
            say("NAMS refused: switching the database mode requires a user token (dashboard login), not an API key.")
            say("Do it once in the NAMS console: Workspace > Database > External, paste the Aura URI/user/password from .env.")
            say("Then re-run `pmm doctor`. Until then point MEMORY_WORKSPACE_ID at an active workspace.")
            raise typer.Exit(3)
        raise
    say(f"PUT /v1/workspace/database -> {resp}")
    last = {"status": None}

    def on_poll(w: dict[str, Any]) -> None:
        if w.get("status") != last["status"] or w.get("provisioningStage"):
            say(f"  workspace status={w.get('status')} stage={w.get('provisioningStage')} msg={w.get('statusMessage')}")
            last["status"] = w.get("status")

    ws = nams.wait_for_workspace(timeout=timeout, on_poll=on_poll)
    say(f"workspace status={ws.get('status')} db mode={nams.database().get('mode')}")
    if ws.get("status") != "active":
        raise typer.Exit(1)


# ====================================================================== stage 1
@ontology_app.command("apply")
def ontology_apply(validation_mode: str = "permissive") -> None:
    """Create (or reuse) the PMM ontology in NAMS and activate it."""
    nams = NamsRest()
    doc = json.loads(ONTOLOGY_FILE.read_text())
    existing = [o for o in nams.ontologies() if o.get("name") == doc["domain"]["id"] and not o.get("is_system")]
    if existing:
        ont = existing[0]
        say(f"ontology {ont['name']!r} already exists (id {ont['id']}, revision {ont.get('current_revision')}, active={ont.get('is_active')})")
        detail = nams.ontology(ont["id"])
        versions = detail.get("versions") or []
        current = max(versions, key=lambda v: v.get("revision", 0)) if versions else None
        version_id = current["id"] if current else None
    else:
        resp = nams.create_ontology(doc, validation_mode=validation_mode, message="PMM ontology for the System One demo")
        say(f"created: {json.dumps(resp)[:400]}")
        version_id = resp.get("id") or (resp.get("version") or {}).get("id") or resp.get("version_id")
        ont = {"id": resp.get("ontology_id") or (resp.get("record") or {}).get("id"), "name": doc["domain"]["id"]}
    if not version_id:
        raise typer.Exit("could not determine the ontology version id to activate")
    act = nams.activate_ontology(version_id)
    active = nams.active_ontology()
    labels = [t["label"] for t in active.get("ontology", {}).get("entity_types", [])]
    say(f"activated version {version_id}; active ontology {active.get('ontology', {}).get('domain', {}).get('id')} with types {labels}")
    write_checkpoint("01-ontology.json", {"stage": 1, "ontology_id": ont.get("id"), "version_id": version_id, "activated_at": now(), "entity_types": labels, "activate_response": act})


@notion_app.command("import")
def notion_import(force: bool = typer.Option(False, help="ignore the checkpoint and re-create everything")) -> None:
    """Load data/notion into the workspace as typed entities and relationships."""
    from pmm.notion_import import run_import

    nams = NamsRest()
    ck = run_import(nams, Fixture(), log=say, force=force)
    say(f"import done: {len(ck['entities'])} entities mapped, {ck['relationship_count']} relationships")


# ====================================================================== verify
@app.command()
def verify(stage: str = typer.Argument(..., help="stage1 | stage3 | stage4 | stage5")) -> None:
    from pmm import verify as v

    nams = NamsRest()
    fn = {"stage1": v.stage1, "stage3": v.stage3, "stage4": v.stage4, "stage5": v.stage5}.get(stage)
    if fn is None:
        raise typer.BadParameter(f"unknown stage {stage!r}")
    failures = fn(nams, log=say)
    if failures:
        for f in failures:
            say(f"FAIL: {f}")
        say(f"verify {stage}: FAILED ({len(failures)})")
        raise typer.Exit(1)
    say(f"verify {stage}: OK")


# ====================================================================== stage 3
@app.command()
def record(
    run_ids: Optional[list[str]] = typer.Argument(None, help="run ids from prompts/runs.yaml (e.g. run-01)"),
    all_runs: bool = typer.Option(False, "--all", help="run the whole matrix"),
    model: Optional[str] = typer.Option(None, help="Claude model alias/name for the headless runs (default: CLI default)"),
    no_house_rules: bool = typer.Option(False, help="send only the run prompt, without the shared house rules"),
) -> None:
    """Run the Stage 3 matrix headlessly (claude -p) with recording on; export each trace to checkpoints/03-traces/."""
    from pmm.record import load_runs, load_runs_ckpt, run_one, save_runs_ckpt

    cfg = load_runs()
    wanted = cfg["runs"] if all_runs or not run_ids else [r for r in cfg["runs"] if r["id"] in set(run_ids)]
    if not wanted:
        raise typer.BadParameter("no matching runs")
    ckpt = load_runs_ckpt()
    ckpt["workspace_id"] = NamsRest().workspace_id
    house = None if no_house_rules else cfg["defaults"].get("house_rules")
    for run in wanted:
        try:
            entry = run_one(run, model=model, house_rules=house, allowed_tools=cfg["defaults"].get("allowed_tools", "mcp__pmm-tools__*"), log=say)
        except Exception as exc:
            say(f"{run['id']} FAILED: {type(exc).__name__}: {exc}")
            entry = {"kind": run["kind"], "brief": run["brief"], "product": run["product"], "segment": run.get("segment"), "status": "exception", "error": str(exc), "recorded_at": now()}
        ckpt["runs"][run["id"]] = entry
        save_runs_ckpt(ckpt)
    say(f"recorded {sum(1 for r in ckpt['runs'].values() if r.get('status') == 'ok')} ok of {len(ckpt['runs'])} runs; checkpoint checkpoints/03-runs.json")


@traces_app.command("ids")
def traces_ids(scope: str = typer.Option("clean", help="clean | all | anti-pattern | escalation | nurture | <run-id,...>")) -> None:
    """Print conversation ids from checkpoints/03-runs.json (paste into the console or feed pmm distill)."""
    from pmm.record import load_runs_ckpt

    runs = load_runs_ckpt()["runs"]
    if scope == "all":
        picked = runs.items()
    elif scope in ("clean", "anti-pattern", "escalation", "nurture"):
        picked = [(k, v) for k, v in runs.items() if v.get("kind") == scope]
    else:
        ids = set(scope.split(","))
        picked = [(k, v) for k, v in runs.items() if k in ids]
    for k, v in picked:
        if v.get("conversation_id"):
            say(v["conversation_id"])


@traces_app.command("delete")
def traces_delete(run_ids: list[str] = typer.Argument(...), yes: bool = typer.Option(False, "--yes", help="actually delete; otherwise print what would go")) -> None:
    """Delete recorded conversations (and their steps) for runs that will be re-recorded; drops them from the checkpoint."""
    from pmm.record import load_runs_ckpt, save_runs_ckpt

    nams = NamsRest()
    ck = load_runs_ckpt()
    for rid in run_ids:
        entry = ck["runs"].get(rid)
        if not entry or not entry.get("conversation_id"):
            say(f"{rid}: nothing recorded")
            continue
        if not yes:
            say(f"{rid}: would delete conversation {entry['conversation_id']} (pass --yes)")
            continue
        say(f"{rid}: delete {entry['conversation_id']} -> {nams.delete_conversation(entry['conversation_id'])}")
        del ck["runs"][rid]
        tp = CHECKPOINTS / "03-traces" / f"{rid}.json"
        if tp.exists():
            tp.unlink()
    save_runs_ckpt(ck)


@traces_app.command("export")
def traces_export(run_ids: Optional[list[str]] = typer.Argument(None)) -> None:
    """Re-export traces for recorded runs into checkpoints/03-traces/."""
    from pmm.record import export_trace, load_runs_ckpt, run_by_id

    nams = NamsRest()
    ck = load_runs_ckpt()
    for run_id, entry in ck["runs"].items():
        if run_ids and run_id not in run_ids:
            continue
        if not entry.get("conversation_id"):
            continue
        p = export_trace(nams, run_by_id(run_id), entry["conversation_id"], None)
        say(f"{run_id}: {p.relative_to(ROOT)}")


@traces_app.command("replay")
def traces_replay() -> None:
    """Re-create the committed traces in the current workspace without Claude (fresh-clone path)."""
    from pmm.record import load_runs_ckpt, replay, save_runs_ckpt

    nams = NamsRest()
    mapping = replay(nams, log=say)
    ck = load_runs_ckpt()
    ck["workspace_id"] = nams.workspace_id
    ck["replayed_at"] = now()
    ck["runs"] = mapping
    save_runs_ckpt(ck)
    say(f"replayed {len(mapping)} conversations; checkpoints/03-runs.json now points at them")


@traces_app.command("show")
def traces_show(run_id: str) -> None:
    """Print the recorded tool path and step reasoning for one run."""
    from pmm.record import load_runs_ckpt, tool_path_of

    nams = NamsRest()
    cid = load_runs_ckpt()["runs"][run_id]["conversation_id"]
    tr = nams.trace(cid)
    say(f"{run_id} conversation {cid}: {' > '.join(tool_path_of(tr))}")
    for s in sorted(tr.get("steps", []), key=lambda x: x.get("createdAt", "")):
        say(f"- [{s.get('actionTaken')}] {s.get('reasoning', '')[:140]} => {s.get('result', '')[:160]}")


@app.command()
def cypher(query: str, params: str = typer.Option("{}", help="JSON object of parameters")) -> None:
    """Run a read-only Cypher query through NAMS /v1/query and print JSON rows."""
    rows = NamsRest().cypher(query, json.loads(params))
    say(json.dumps(rows, indent=2, default=str))


# ====================================================================== stage 4
@app.command()
def distill(
    scope: str = typer.Option("clean", help="clean | all | <run-id,...>: which recorded conversations to distil from"),
    name_hint: str = typer.Option("launch-email-blast"),
    install: bool = typer.Option(True, "--install/--no-install", help="unzip the published skill into .claude/skills/"),
    workspace_demo: bool = typer.Option(True, help="also run the deliberate workspace-scope attempt and record the withhold"),
    fallback: str = typer.Option("run-01", help="run id to retry with when the clean scope is withheld"),
) -> None:
    """Stage 4 unattended: generate -> poll -> review(approve) -> publish -> download -> install."""
    from pmm.nams_skills import distill as _distill
    from pmm.record import load_runs_ckpt

    runs = load_runs_ckpt()["runs"]
    if scope == "all":
        ids = [v["conversation_id"] for v in runs.values() if v.get("conversation_id")]
    elif scope == "clean":
        ids = [v["conversation_id"] for v in runs.values() if v.get("kind") == "clean" and v.get("conversation_id") and v.get("status") == "ok"]
    else:
        ids = [runs[k]["conversation_id"] for k in scope.split(",") if k in runs and runs[k].get("conversation_id")]
    if not ids:
        raise typer.BadParameter(f"no conversations for scope {scope!r}")
    fb = [runs[fallback]["conversation_id"]] if fallback in runs and runs[fallback].get("conversation_id") else None
    meta = _distill(NamsRest(), ids, name_hint=name_hint, fallback_ids=fb, workspace_demo=workspace_demo, install=install, log=say)
    say(f"distill: {meta.get('result')}; skill {meta.get('skill_id')}; attempts: {[(a.get('label'), a.get('outcome')) for a in meta['attempts']]}")
    if meta.get("result") != "published":
        raise typer.Exit(1)


@skill_app.command("status")
def skill_status(skill_id: Optional[str] = typer.Argument(None)) -> None:
    nams = NamsRest()
    if skill_id:
        say(json.dumps(nams.skill(skill_id), indent=2, default=str)[:6000])
    else:
        say(json.dumps(nams.skills(), indent=2, default=str)[:6000])


@skill_app.command("review")
def skill_review(skill_id: str, approve: bool = typer.Option(False, "--approve"), reject: bool = typer.Option(False, "--reject"), feedback: Optional[str] = None) -> None:
    decision = "approve" if approve or not reject else "reject"
    say(json.dumps(NamsRest().skill_review(skill_id, decision, feedback), indent=2, default=str))


@skill_app.command("publish")
def skill_publish(skill_id: str) -> None:
    say(json.dumps(NamsRest().skill_publish(skill_id), indent=2, default=str))


@skill_app.command("download")
def skill_download(skill_id: str, out: Path = typer.Option(Path("checkpoints/04-skill/launch-email-blast.zip"))) -> None:
    data = NamsRest().skill_download(skill_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    say(f"wrote {len(data)} bytes to {out}")


@skill_app.command("install")
def skill_install(zip_path: Path = typer.Argument(Path("checkpoints/04-skill/launch-email-blast.zip"))) -> None:
    """Unzip a downloaded skill package into .claude/skills/launch-email-blast/."""
    from pmm.nams_skills import install_zip, summarize_skill_dir

    files = install_zip(zip_path.read_bytes())
    say(f"installed {len(files)} files into {SKILL_DIR.relative_to(ROOT)}: {json.dumps(summarize_skill_dir())}")


@skill_app.command("explain")
def skill_explain(skill_id: str) -> None:
    nams = NamsRest()
    say(json.dumps({"provenance": nams.skill_explain_provenance(skill_id), "drift": nams.skill_drift(skill_id)}, indent=2, default=str)[:8000])


# ====================================================================== stage 5
SKILL_RUN_PROMPT = 'New brief in Notion: brief-013, "riverbed 2.0 release". Launch the email blast to the Python streaming developers, scheduled for 2026-11-04 09:00 UTC.'


@app.command("run-skill")
def run_skill(
    brief: str = typer.Option("brief-013"),
    model: Optional[str] = typer.Option(None, help="e.g. sonnet, to compare a cheaper System Two"),
    record: bool = typer.Option(True, "--record/--no-record", help="keep recording on so the skill run lands in the same graph (runKind=skill-run)"),
    prompt: Optional[str] = None,
) -> None:
    """Stage 5 headless twin: a fresh Claude Code session with the distilled skill installed."""
    from pmm.record import run_one

    if not (SKILL_DIR / "SKILL.md").exists():
        raise typer.Exit(f"{SKILL_DIR} has no SKILL.md; run `pmm distill --install` or `pmm skill install` first")
    fx = Fixture()
    b = fx.brief(brief)
    run = {"id": f"skill-run-{brief}-{(model or 'default').replace('/', '_')}", "kind": "skill-run", "brief": brief, "product": b["Product"], "segment": (b["Segment"] or [""])[0],
           "prompt": prompt or SKILL_RUN_PROMPT.replace("brief-013", brief).replace('"riverbed 2.0 release"', f'"{b["Name"]}"')}
    entry = run_one(run, model=model, run_kind="skill-run", allowed_tools="Skill,mcp__pmm-tools__*", builtin_tools="Skill", record=record, log=say, export_dir=CHECKPOINTS / "05-traces")
    ck_path = CHECKPOINTS / "05-skill-run.json"
    ck = json.loads(ck_path.read_text()) if ck_path.exists() else {"stage": 5, "runs": []}
    ck["runs"] = [r for r in ck["runs"] if r.get("run_id") != entry["run_id"]] + [entry]
    write_checkpoint("05-skill-run.json", ck)


@app.command()
def report() -> None:
    """Write reports/comparison.md from the Stage 3 and Stage 5 checkpoints."""
    from pmm import report as rp

    p = rp.write(NamsRest())
    say(p.read_text())


@app.command("replay-from")
def replay_from(stage: int = typer.Argument(..., help="1: re-import fixture; 3: replay traces; 4: install committed skill; 5: run the committed skill with recording off")) -> None:
    """Fresh-clone path: start the demo from a committed checkpoint."""
    from pmm.nams_skills import install_zip
    from pmm.notion_import import run_import
    from pmm.record import load_runs_ckpt, replay, save_runs_ckpt, run_one

    nams = NamsRest()
    if stage <= 1:
        ontology_apply()
        run_import(nams, Fixture(), log=say)
        verify("stage1")
    if stage <= 3:
        mapping = replay(nams, log=say)
        ck = load_runs_ckpt()
        ck.update({"workspace_id": nams.workspace_id, "replayed_at": now(), "runs": mapping})
        save_runs_ckpt(ck)
        verify("stage3")
    if stage <= 4:
        zip_path = CHECKPOINTS / "04-skill" / "launch-email-blast.zip"
        if zip_path.exists():
            install_zip(zip_path.read_bytes())
            say(f"installed committed skill from {zip_path.relative_to(ROOT)}")
        elif not (SKILL_DIR / "SKILL.md").exists():
            raise typer.Exit("no committed skill zip and no installed skill")
    if stage <= 5:
        run_skill(brief="brief-013", model=None, record=False, prompt=None)


def main() -> None:
    load_dotenv()
    ensure_run_dirs()
    app()


if __name__ == "__main__":
    main()
