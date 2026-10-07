"""Claude Code hook entrypoints (`pmm-hook <event>`), fed the hook payload on stdin.

UserPromptSubmit: make sure the session has a NAMS conversation (pre-created by `pmm record`, or
created here for interactive sessions), then store the prompt as a user message.
PostToolUse (mcp__pmm-tools__.* only): append the tool use to the session file; the server already
recorded the step. Stop: store the final assistant message and mark the session complete.

Hooks never fail the session: every error is logged to .run/recorder.log and exit code is 0.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from typing import Any, Protocol

from pmm.env import load_dotenv, recording_enabled
from pmm.recorder import log_line, read_session, session_file_for, write_session

BRIEF_RE = re.compile(r"brief-\d{3}")


class Memory(Protocol):
    async def create_conversation(self, metadata: dict[str, str]) -> str: ...
    async def add_message(self, conversation_id: str, role: str, content: str) -> None: ...


class SdkMemory:
    """neo4j-agent-memory SDK on the NAMS backend (short_term sub-client)."""

    async def _client(self):
        from pmm.recorder import make_client

        client = make_client()
        await client.connect()
        return client

    async def create_conversation(self, metadata: dict[str, str]) -> str:
        # Same route `pmm record` uses. The SDK's short_term.create_conversation needs a session_id
        # on the NAMS backend, which does not exist yet for a brand-new interactive session.
        from pmm.nams_rest import NamsRest

        return str(NamsRest().create_conversation({k: str(v) for k, v in metadata.items()})["id"])

    async def add_message(self, conversation_id: str, role: str, content: str) -> None:
        client = await self._client()
        try:
            await client.short_term.add_message(session_id=conversation_id, role=role, content=content)
        finally:
            await client.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def handle(event: str, payload: dict[str, Any], memory: Memory | None = None) -> dict[str, Any] | None:
    if not recording_enabled():
        return None
    memory = memory or SdkMemory()
    session_id = payload.get("session_id")
    if not session_id:
        log_line(f"hook {event}: payload without session_id")
        return None
    path = session_file_for(session_id)
    data = read_session(path)

    if event == "user-prompt-submit":
        prompt = payload.get("prompt") or ""
        if data is None:
            m = BRIEF_RE.search(prompt)
            metadata = {"runKind": "interactive", "briefId": m.group(0) if m else "", "task": prompt.strip()[:160], "claudeSessionId": session_id}
            try:
                cid = await memory.create_conversation(metadata)
            except Exception:
                # Never let the MCP server fall back to a stale current.json and record into the
                # wrong conversation: drop it so this session simply goes unrecorded.
                from pmm.recorder import current_session_file

                current_session_file().unlink(missing_ok=True)
                raise
            data = {"session_id": session_id, "conversation_id": cid, "run_id": "interactive", "kind": "interactive", "brief_id": metadata["briefId"], "task": metadata["task"], "created_at": _now(), "messages": 0, "tool_uses": []}
            log_line(f"hook: created conversation {cid} for interactive session {session_id}")
        if prompt.strip():
            await memory.add_message(data["conversation_id"], "user", prompt)
            data["messages"] = int(data.get("messages", 0)) + 1
        write_session(path, data)
        return data

    if data is None:
        log_line(f"hook {event}: no session file for {session_id}; nothing recorded")
        return None

    if event == "post-tool-use":
        data.setdefault("tool_uses", []).append({"tool_name": payload.get("tool_name"), "tool_use_id": payload.get("tool_use_id"), "at": _now()})
        write_session(path, data)
        return data

    if event == "stop":
        msg = payload.get("last_assistant_message") or ""
        if msg.strip():
            await memory.add_message(data["conversation_id"], "assistant", msg)
            data["messages"] = int(data.get("messages", 0)) + 1
        data["completed_at"] = _now()
        data["outcome"] = "stopped"
        write_session(path, data)
        return data

    log_line(f"hook: unknown event {event!r}")
    return None


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: pmm-hook <user-prompt-submit|post-tool-use|stop>", file=sys.stderr)
        return 0
    event = argv[0]
    load_dotenv()
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        log_line(f"hook {event}: bad stdin payload: {exc}")
        return 0
    try:
        asyncio.run(handle(event, payload))
    except Exception as exc:
        log_line(f"hook {event}: failed: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
