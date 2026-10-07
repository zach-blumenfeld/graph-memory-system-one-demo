"""Claude Code hooks (`blast-hook <event>`), payload on stdin. Records the conversation and the
agent's tool calls into memory with the SDK (bolt backend):

  UserPromptSubmit  -> :Conversation + :Message(user); start a :ReasoningTrace
  PostToolUse(Bash) -> :ReasoningStep -> :ToolCall for every `blast ...` command (a `blast decide`
                       step also gets the :Decision label and the decision fields)
  Stop              -> :Message(assistant); complete the trace

The claude session id is the memory session id. Trace ids live in .run/sessions/<session>.json.
Hooks never fail the session: every error is logged to .run/recorder.log, exit code is 0.
"""

from __future__ import annotations

import asyncio
import json
import re
import shlex
import sys
from datetime import datetime, timezone
from typing import Any

from blast.env import RECORDER_LOG, SESSIONS_DIR, ensure_run_dirs, load_dotenv, recording_enabled

BRIEF_RE = re.compile(r"brief-\d{3}")


def _quiet() -> None:
    """Silence the SDK's info logs and the driver's schema-warning notifications on stderr."""
    import logging

    for name in ("neo4j", "neo4j.notifications", "neo4j_agent_memory"):
        logging.getLogger(name).setLevel(logging.ERROR)


def log_line(msg: str) -> None:
    ensure_run_dirs()
    with RECORDER_LOG.open("a") as fh:
        fh.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}\n")


def session_path(session_id: str):
    return SESSIONS_DIR / f"{session_id}.json"


def read_session(session_id: str) -> dict[str, Any] | None:
    p = session_path(session_id)
    return json.loads(p.read_text()) if p.exists() else None


def write_session(session_id: str, data: dict[str, Any]) -> None:
    ensure_run_dirs()
    session_path(session_id).write_text(json.dumps(data, indent=2) + "\n")


def _blast_args(command: str) -> list[str] | None:
    """The argv of a `blast ...` invocation inside a shell command, or None."""
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    for i, p in enumerate(parts):
        if p == "blast" or p.endswith("/blast"):
            return parts[i + 1 :]
        if p == "uv" and parts[i + 1 : i + 3] == ["run", "blast"]:
            return parts[i + 3 :]
    return None


def _opt(args: list[str], name: str) -> str | None:
    for i, a in enumerate(args):
        if a == name and i + 1 < len(args):
            return args[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return None


def _stdout(resp: Any) -> str:
    if isinstance(resp, dict):
        return str(resp.get("stdout") or resp.get("output") or resp.get("content") or json.dumps(resp))
    return str(resp)


async def handle(event: str, payload: dict[str, Any]) -> None:
    from blast.memory import client

    session_id = payload.get("session_id") or "unknown"
    data = read_session(session_id)

    if event == "user-prompt-submit":
        prompt = payload.get("prompt") or ""
        async with client() as m:
            if data is None:
                b = BRIEF_RE.search(prompt)
                task = prompt.strip()[:200]
                trace = await m.reasoning.start_trace(session_id, task, generate_embedding=False,
                                                      metadata={"briefId": b.group(0) if b else "", "runId": payload.get("run_id") or "interactive"})
                data = {"session_id": session_id, "trace_id": str(trace.id), "brief_id": b.group(0) if b else "", "task": task,
                        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "steps": 0, "messages": 0}
                log_line(f"hook: trace {trace.id} started for session {session_id}")
            if prompt.strip():
                await m.short_term.add_message(session_id, "user", prompt, extract_entities=False, extract_relations=False, generate_embedding=False)
                data["messages"] += 1
        # The package keeps conversations and traces apart (they only share session_id); one edge
        # joins them so a run is one connected subgraph in Browser.
        from blast.memory import cypher

        cypher("MATCH (c:Conversation {session_id: $sid}), (t:ReasoningTrace {id: $tid}) MERGE (c)-[:HAS_TRACE]->(t)",
               sid=session_id, tid=data["trace_id"])
        write_session(session_id, data)
        return

    if data is None:
        log_line(f"hook {event}: no session file for {session_id}; nothing recorded")
        return

    if event == "post-tool-use":
        if payload.get("tool_name") != "Bash":
            return
        command = (payload.get("tool_input") or {}).get("command") or ""
        args = _blast_args(command)
        if args is None:
            return
        tool = args[0] if args else "blast"
        output = _stdout(payload.get("tool_response"))
        try:
            result: Any = json.loads(output)
        except Exception:
            result = output[-2000:]
        failed = isinstance(result, dict) and "error" in result
        meta: dict[str, Any] = {"command": command, "kind": "decision" if tool == "decide" else "tool"}
        thought = f"blast {tool}"
        if tool == "decide":
            q, opts, ans, why = _opt(args, "--question"), _opt(args, "--options"), _opt(args, "--answer"), _opt(args, "--why")
            meta.update({"question": q, "options": opts, "answer": ans, "why": why})
            thought = f"decision {q}: {ans} (options: {opts}). {why}"
        async with client() as m:
            step = await m.reasoning.add_step(data["trace_id"], thought=thought, action=f"blast {' '.join(args)}"[:500],
                                              observation=(json.dumps(result)[:500] if not isinstance(result, str) else result[:500]),
                                              generate_embedding=False, metadata=meta)
            from neo4j_agent_memory import ToolCallStatus

            await m.reasoning.record_tool_call(step.id, f"blast {tool}", {"args": args[1:]}, result=result,
                                               status=ToolCallStatus.FAILURE if failed else ToolCallStatus.SUCCESS)
        if tool == "decide":
            from blast.memory import cypher

            cypher("MATCH (s:ReasoningStep {id: $id}) SET s:Decision, s.question = $q, s.options = $o, s.answer = $a, s.why = $w",
                   id=str(step.id), q=meta.get("question"), o=meta.get("options"), a=meta.get("answer"), w=meta.get("why"))
        data["steps"] += 1
        write_session(session_id, data)
        return

    if event == "stop":
        msg = payload.get("last_assistant_message") or ""
        async with client() as m:
            if msg.strip():
                await m.short_term.add_message(session_id, "assistant", msg, extract_entities=False, extract_relations=False, generate_embedding=False)
                data["messages"] += 1
            await m.reasoning.complete_trace(data["trace_id"], outcome="completed", success=True)
        data["completed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        write_session(session_id, data)
        log_line(f"hook: trace {data['trace_id']} completed ({data['steps']} steps)")
        return


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    _quiet()
    load_dotenv()
    if not recording_enabled():
        return 0
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}
    try:
        asyncio.run(handle(event, payload))
    except Exception as exc:  # never fail the session
        log_line(f"hook {event}: failed: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
