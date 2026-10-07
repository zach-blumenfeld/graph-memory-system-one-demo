"""Step 2 (headless) and step 3 (export): run the agent, read the traces back, write the source for AIP."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

import yaml

from blast.env import CHECKPOINTS, ROOT, RUN_DIR, RUNS_FILE, SOP_FILE, SOURCE, ensure_run_dirs
from blast.hooks import read_session
from blast.memory import cypher

TRACES = CHECKPOINTS / "traces"


def runs() -> dict[str, Any]:
    return yaml.safe_load(RUNS_FILE.read_text())


def claude_command(prompt: str, session_id: str, model: str | None) -> list[str]:
    cmd = ["claude", "-p", prompt, "--session-id", session_id, "--output-format", "json",
           "--permission-mode", "dontAsk",
           "--tools", "Bash,Read,Write",
           "--allowedTools", "Bash(blast:*),Bash(uv run blast:*),Read,Write",
           "--disallowedTools", "Skill,WebFetch,WebSearch,Agent",
           "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}']
    if model:
        cmd += ["--model", model]
    return cmd


def record_one(run_id: str, *, model: str | None = None, log=print) -> dict[str, Any]:
    ensure_run_dirs()
    cfg = runs()
    run = next((r for r in cfg["runs"] if r["id"] == run_id), None)
    if not run:
        raise SystemExit(f"no run {run_id} in prompts/runs.yaml")
    prompt = cfg["defaults"]["preamble"].strip() + "\n\n" + run["prompt"].strip()
    session_id = str(uuid.uuid4())
    env = dict(__import__("os").environ)
    env["BLAST_RECORD"] = "1"
    env["CLAUDE_PROJECT_DIR"] = str(ROOT)
    bin_dir = ROOT / ".venv" / "bin"
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    log(f"{run_id} [{run['kind']}] session {session_id}; launching claude -p (model={model or 'default'}) ...")
    t0 = time.time()
    proc = subprocess.run(claude_command(prompt, session_id, model), cwd=ROOT, env=env, capture_output=True, text=True, timeout=1800)
    wall = int(time.time() - t0)
    try:
        res = json.loads(proc.stdout)
    except Exception:
        res = {"result": proc.stdout[-2000:], "error": proc.stderr[-2000:]}
    sess = read_session(session_id) or {}
    entry = {"run_id": run_id, "kind": run["kind"], "brief": run["brief"], "session_id": session_id, "trace_id": sess.get("trace_id"),
             "model": model or "default", "rc": proc.returncode, "wall_s": wall, "cost_usd": res.get("total_cost_usd"), "turns": res.get("num_turns"),
             "steps": sess.get("steps"), "final": (res.get("result") or "")[:4000]}
    log(f"{run_id} finished in {wall}s: rc={proc.returncode} turns={entry['turns']} steps={entry['steps']} cost=${(entry['cost_usd'] or 0):.2f}")
    (RUN_DIR / f"{run_id}.claude.json").write_text(json.dumps(res, indent=2))
    export_trace(entry, log=log)
    ck = CHECKPOINTS / "02-runs.json"
    data = json.loads(ck.read_text()) if ck.exists() else {"runs": []}
    data["runs"] = [r for r in data["runs"] if r["run_id"] != run_id] + [entry]
    ck.write_text(json.dumps(data, indent=2) + "\n")
    return entry


def record_all(*, model: str | None = None, log=print) -> None:
    for r in runs()["runs"]:
        record_one(r["id"], model=model, log=log)


def trace_rows(trace_id: str) -> list[dict[str, Any]]:
    return cypher("""
        MATCH (t:ReasoningTrace {id: $id})-[:HAS_STEP]->(s:ReasoningStep)
        OPTIONAL MATCH (s)-[:USES_TOOL]->(c:ToolCall)
        RETURN s.id AS step_id, s.thought AS thought, s.action AS action, s.observation AS observation,
               s:Decision AS is_decision, s.question AS question, s.options AS options, s.answer AS answer, s.why AS why,
               c.tool_name AS tool, c.arguments AS arguments, c.result AS result, c.status AS status, s.created_at AS at
        ORDER BY s.created_at, s.step_number""", id=trace_id)


def messages(session_id: str) -> list[dict[str, Any]]:
    return cypher("MATCH (c:Conversation {session_id: $sid})-[:HAS_MESSAGE]->(m:Message) RETURN m.role AS role, m.content AS content, m.created_at AS at ORDER BY m.created_at", sid=session_id)


def export_trace(entry: dict[str, Any], log=print) -> Path:
    TRACES.mkdir(parents=True, exist_ok=True)
    data = {"run": entry, "messages": messages(entry["session_id"]), "steps": trace_rows(entry["trace_id"]) if entry.get("trace_id") else []}
    p = TRACES / f"{entry['run_id']}.json"
    p.write_text(json.dumps(data, indent=2, default=str) + "\n")
    log(f"exported {len(data['steps'])} steps, {len(data['messages'])} messages -> {p.relative_to(ROOT)}")
    return p


def show_trace(run_id: str, log=print) -> None:
    p = TRACES / f"{run_id}.json"
    if not p.exists():
        raise SystemExit(f"no exported trace for {run_id}")
    d = json.loads(p.read_text())
    log(f"{run_id} [{d['run']['kind']}] {d['run']['brief']}  {d['run']['wall_s']}s  ${d['run']['cost_usd']}")
    for i, s in enumerate(d["steps"], 1):
        if s["is_decision"]:
            log(f"  {i:2d}. DECISION {s['question']}: {s['answer']}   (options: {s['options']})")
        else:
            log(f"  {i:2d}. {s['tool']}  {s['status']}  {str(s['action'])[:90]}")


def verify_traces(log=print) -> int:
    ck = CHECKPOINTS / "02-runs.json"
    if not ck.exists():
        log("FAIL no checkpoints/02-runs.json")
        return 1
    failures = []
    for r in json.loads(ck.read_text())["runs"]:
        d = json.loads((TRACES / f"{r['run_id']}.json").read_text())
        tools = [s["tool"] for s in d["steps"] if s["tool"]]
        decisions = [s for s in d["steps"] if s["is_decision"]]
        log(f"{r['run_id']}: {len(tools)} tool calls, {len(decisions)} decisions, rc={r['rc']}")
        if r["rc"] != 0:
            failures.append(f"{r['run_id']} exited {r['rc']}")
        if "blast check" not in tools:
            failures.append(f"{r['run_id']} never ran the compliance check")
        if not decisions:
            failures.append(f"{r['run_id']} logged no judgment calls")
        if r["kind"] in ("launch", "hotfix") and "blast schedule" not in tools:
            failures.append(f"{r['run_id']} never scheduled")
        if r["kind"] == "digest" and "blast schedule" in tools:
            failures.append(f"{r['run_id']} scheduled a digest")
    for f in failures:
        log("FAIL " + f)
    log("verify traces: " + ("OK" if not failures else "FAILED"))
    return 1 if failures else 0


def export_source(log=print) -> None:
    """source/sop.md and source/traces.md: what the AIP authoring skill compiles from."""
    SOURCE.mkdir(exist_ok=True)
    shutil.copy(SOP_FILE, SOURCE / "sop.md")
    ck = json.loads((CHECKPOINTS / "02-runs.json").read_text())
    lines = ["# Recorded runs: what the agent actually did", "",
             "Four Claude Code sessions did the email blast from the SOP with only the `blast` tools, no skill. "
             "Each run below is read back from memory: the prompt, every `blast` call in order with its result, "
             "every judgment call the agent logged with `blast decide`, and the agent's closing summary. "
             "Treat the judgment calls as the decision points of the procedure and the `blast` commands as its scripts.", ""]
    for r in sorted(ck["runs"], key=lambda x: x["run_id"]):
        d = json.loads((TRACES / f"{r['run_id']}.json").read_text())
        lines += [f"## {r['run_id']} ({r['kind']}, {r['brief']})", "", "Prompt:", ""]
        user = [m for m in d["messages"] if m["role"] == "user"]
        lines += ["> " + user[0]["content"].replace("\n", "\n> ") if user else "> (missing)", ""]
        for i, s in enumerate(d["steps"], 1):
            if s["is_decision"]:
                lines.append(f"{i}. **Judgment** `{s['question']}` → **{s['answer']}** (options: {s['options']}). Why: {s['why']}")
            else:
                res = s["result"] if isinstance(s["result"], str) else json.dumps(s["result"])
                lines.append(f"{i}. `{s['action']}` → {s['status']}: `{res[:300]}`")
        lines.append("")
        final = r.get("final") or ""
        lines += ["Agent's closing summary:", "", "> " + final.strip().replace("\n", "\n> "), ""]
    (SOURCE / "traces.md").write_text("\n".join(lines))
    log(f"wrote {SOURCE / 'sop.md'} and {SOURCE / 'traces.md'} ({len(ck['runs'])} runs)")
