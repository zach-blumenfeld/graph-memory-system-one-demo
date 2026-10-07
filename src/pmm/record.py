"""Stage 3: run the matrix headlessly, export traces, replay them without Claude."""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from pmm.env import CHECKPOINTS, ROOT, RUNS_FILE, RUN_DIR, ensure_run_dirs
from pmm.nams_rest import NamsRest
from pmm.recorder import session_file_for, write_session

TRACES_DIR = CHECKPOINTS / "03-traces"
RUNS_CKPT = CHECKPOINTS / "03-runs.json"


def load_runs(path: Path | None = None) -> dict[str, Any]:
    return yaml.safe_load((path or RUNS_FILE).read_text())


def run_by_id(run_id: str) -> dict[str, Any]:
    for r in load_runs()["runs"]:
        if r["id"] == run_id:
            return r
    raise KeyError(run_id)


def full_prompt(run: dict[str, Any], house_rules: str | None) -> str:
    text = run["prompt"].strip()
    if house_rules and run.get("house_rules", True):
        text += "\n\n" + house_rules.strip()
    return text


def claude_command(prompt: str, session_id: str, model: str | None, allowed_tools: str, extra: list[str] | None = None, builtin_tools: str = "") -> list[str]:
    cmd = [
        "claude", "-p", prompt,
        "--mcp-config", ".mcp.json", "--strict-mcp-config",
        "--allowedTools", allowed_tools,
        "--tools", builtin_tools,  # "" = no built-in tools (Stage 3); "Skill" for Stage 5 so the skill can be invoked
        "--permission-mode", "dontAsk",
        "--output-format", "json",
        "--session-id", session_id,
    ]
    if model:
        cmd += ["--model", model]
    if extra:
        cmd += extra
    return cmd


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_runs_ckpt() -> dict[str, Any]:
    if RUNS_CKPT.exists():
        return json.loads(RUNS_CKPT.read_text())
    return {"stage": 3, "workspace_id": None, "runs": {}}


def save_runs_ckpt(data: dict[str, Any]) -> None:
    CHECKPOINTS.mkdir(exist_ok=True)
    RUNS_CKPT.write_text(json.dumps(data, indent=2) + "\n")


def export_trace(nams: NamsRest, run: dict[str, Any], conversation_id: str, claude_result: dict[str, Any] | None, out_dir: Path = TRACES_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    conv = nams.conversation(conversation_id)
    msgs = nams.messages(conversation_id)
    trace = nams.trace(conversation_id)
    slim_claude = None
    if claude_result:
        slim_claude = {k: claude_result.get(k) for k in ("session_id", "total_cost_usd", "duration_ms", "duration_api_ms", "num_turns", "result", "modelUsage", "permission_denials", "stop_reason", "is_error", "terminal_reason")}
    doc = {"run": {k: run[k] for k in ("id", "kind", "brief", "product", "segment")}, "exported_at": _now(), "conversation": conv, "messages": msgs, "trace": trace, "claude": slim_claude}
    path = out_dir / f"{run['id']}.json"
    path.write_text(json.dumps(doc, indent=2, default=str) + "\n")
    return path


def run_one(run: dict[str, Any], *, model: str | None = None, run_kind: str | None = None, house_rules: str | None = None, allowed_tools: str = "mcp__pmm-tools__*", extra_args: list[str] | None = None, log=print, timeout: int = 2400, export: bool = True, builtin_tools: str = "", record: bool = True, export_dir: Path | None = None) -> dict[str, Any]:
    """Create the conversation, run headless Claude Code with recording on, export the trace."""
    ensure_run_dirs()
    nams = NamsRest() if record else None
    session_id = str(uuid.uuid4())
    kind = run_kind or run["kind"]
    metadata = {"runKind": kind, "runId": run["id"], "briefId": run["brief"], "product": run["product"], "segmentId": run.get("segment", ""), "claudeSessionId": session_id, "model": model or "default"}
    cid = nams.create_conversation(metadata)["id"] if nams else None
    session_path = session_file_for(session_id)
    write_session(session_path, {"session_id": session_id, "conversation_id": cid, "run_id": run["id"], "kind": kind, "brief_id": run["brief"], "task": run["prompt"].strip().splitlines()[0][:160], "created_at": _now(), "messages": 0, "tool_uses": []})
    prompt = full_prompt(run, house_rules)
    cmd = claude_command(prompt, session_id, model, allowed_tools, extra_args, builtin_tools=builtin_tools)
    env = dict(os.environ)
    env["PMM_CONVERSATION_FILE"] = str(session_path)
    env["PMM_RECORD"] = "1" if record else "0"
    log(f"{run['id']} [{kind}] conversation {cid or '(recording off)'}; launching claude -p (model={model or 'default'}) ...")
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    wall_ms = int((time.perf_counter() - t0) * 1000)
    result: dict[str, Any] | None = None
    try:
        result = json.loads(proc.stdout) if proc.stdout.strip() else None
    except json.JSONDecodeError:
        result = None
    (RUN_DIR / "runs").mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "runs" / f"{run['id']}.json").write_text(json.dumps({"cmd": cmd[:1] + ["-p", "<prompt>"] + cmd[3:], "returncode": proc.returncode, "wall_ms": wall_ms, "stdout": result or proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}, indent=2) + "\n")
    status = "ok" if proc.returncode == 0 and result and not result.get("is_error") else "error"
    log(f"{run['id']} finished in {wall_ms / 1000:.0f}s: rc={proc.returncode} status={status} turns={result.get('num_turns') if result else '?'} cost=${(result or {}).get('total_cost_usd', 0):.2f}")
    if proc.returncode != 0:
        log(f"  stderr: {proc.stderr.strip()[-600:]}")
    tools: list[str] = []
    trace_path = None
    if nams and cid:
        time.sleep(2)  # the server settles each write, but give NAMS a moment before exporting
        trace_path = export_trace(nams, run, cid, result, out_dir=export_dir or TRACES_DIR) if export else None
        tr = nams.trace(cid)
        tools = tool_path_of(tr)
        log(f"  recorded {len(tr.get('steps', []))} steps, tools: {' > '.join(tools) if tools else '(none)'}")
    else:
        log("  recording off: no trace exported")
    entry = {"run_id": run["id"], "conversation_id": cid, "claude_session_id": session_id, "kind": kind, "brief": run["brief"], "product": run["product"], "segment": run.get("segment"), "model": model or "default", "status": status, "wall_ms": wall_ms, "cost_usd": (result or {}).get("total_cost_usd"), "num_turns": (result or {}).get("num_turns"), "tool_path": tools, "trace_checkpoint": str(trace_path.relative_to(ROOT)) if trace_path else None, "recorded_at": _now()}
    return entry


def tool_path_of(trace: dict[str, Any]) -> list[str]:
    """Tool names in step order, failed calls marked with `!`."""
    order = {s.get("id"): (s.get("createdAt") or "") for s in trace.get("steps", [])}
    calls = sorted(trace.get("toolCalls") or [], key=lambda tc: (order.get(tc.get("stepId"), tc.get("createdAt") or ""), tc.get("createdAt") or ""))
    return [str(tc.get("toolName")) + ("!" if tc.get("status") == "failure" else "") for tc in calls]


def replay(nams: NamsRest, traces_dir: Path = TRACES_DIR, log=print) -> dict[str, Any]:
    """Re-create every exported conversation (messages, steps, tool calls) in the current workspace."""
    mapping: dict[str, Any] = {}
    for path in sorted(traces_dir.glob("run-*.json")):
        doc = json.loads(path.read_text())
        run = doc["run"]
        meta = dict((doc.get("conversation") or {}).get("metadata") or {})
        meta["replayedFrom"] = (doc.get("conversation") or {}).get("id", "")
        meta.setdefault("runKind", run["kind"])
        meta.setdefault("runId", run["id"])
        cid = nams.create_conversation(meta)["id"]
        msgs = [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in doc.get("messages") or [] if m.get("content")]
        for i in range(0, len(msgs), 100):
            nams.bulk_messages(cid, msgs[i : i + 100])
        n_calls = 0
        trace = doc.get("trace", {})
        calls_by_step: dict[str, list[dict[str, Any]]] = {}
        for tc in trace.get("toolCalls") or []:
            calls_by_step.setdefault(tc.get("stepId") or "", []).append(tc)
        for step in sorted(trace.get("steps", []), key=lambda x: x.get("createdAt", "")):
            s = nams.record_step(cid, step.get("reasoning") or " ", step.get("actionTaken") or " ", step.get("result"))
            sid = s.get("id")
            for tc in sorted(calls_by_step.get(step.get("id"), []) + (step.get("toolCalls") or []), key=lambda x: x.get("createdAt", "")):
                nams.record_tool_call(tc["toolName"], tc.get("input") or "{}", sid, tc.get("status") or "success", tc.get("output"), tc.get("durationMs"))
                n_calls += 1
        mapping[run["id"]] = {"conversation_id": cid, "kind": run["kind"], "brief": run["brief"], "product": run["product"], "segment": run.get("segment"), "replayed_from": meta["replayedFrom"], "messages": len(msgs), "tool_calls": n_calls, "recorded_at": _now()}
        log(f"{run['id']}: replayed {len(msgs)} messages and {n_calls} tool calls into {cid}")
    return mapping
