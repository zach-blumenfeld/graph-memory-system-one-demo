"""Trace recording through the neo4j-agent-memory SDK against NAMS.

Process model: the MCP server, each Claude Code hook and the CLI are separate processes. They
share one conversation UUID kept in `.run/sessions/<claude_session_id>.json` (and a `current.json`
copy). Each process does its own `start_trace(session_id=<conversation uuid>, ...)`; on NAMS the
trace id is synthesized client-side and steps attach to the conversation directly.

Writes are queued and executed in order by one worker; `flush()` waits for the queue. A failed
write never fails the tool: errors go to `.run/recorder.log`.
"""

from __future__ import annotations

import asyncio
import json
import os
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from pmm.env import RECORDER_LOG, SESSIONS_DIR, ensure_run_dirs, load_dotenv


def log_line(msg: str) -> None:
    try:
        ensure_run_dirs()
        with RECORDER_LOG.open("a") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} {msg}\n")
    except Exception:  # pragma: no cover
        pass


# --------------------------------------------------------------------------- session file
def session_file_for(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def current_session_file() -> Path:
    return SESSIONS_DIR / "current.json"


def read_session(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_session(path: Path, data: dict[str, Any]) -> None:
    ensure_run_dirs()
    path.write_text(json.dumps(data, indent=2) + "\n")
    current_session_file().write_text(json.dumps(data, indent=2) + "\n")


def resolve_conversation_file() -> Path:
    explicit = os.environ.get("PMM_CONVERSATION_FILE")
    if explicit:
        return Path(explicit)
    return current_session_file()


# --------------------------------------------------------------------------- recorder API
@dataclass
class ToolRecord:
    tool_name: str
    thought: str
    arguments: dict[str, Any]
    result: Any
    status: str
    duration_ms: int
    observation: str | None = None
    step_id: str | None = None
    tool_call_id: str | None = None


class Recorder(Protocol):
    async def record(self, rec: ToolRecord) -> None: ...
    async def flush(self) -> None: ...
    async def close(self, outcome: str | None = None, success: bool | None = None) -> None: ...


class NullRecorder:
    async def record(self, rec: ToolRecord) -> None:
        return None

    async def flush(self) -> None:
        return None

    async def close(self, outcome: str | None = None, success: bool | None = None) -> None:
        return None


@dataclass
class FakeRecorder:
    records: list[ToolRecord] = field(default_factory=list)
    closed: bool = False

    async def record(self, rec: ToolRecord) -> None:
        rec.step_id = f"step-{len(self.records) + 1:03d}"
        rec.tool_call_id = f"call-{len(self.records) + 1:03d}"
        self.records.append(rec)

    async def flush(self) -> None:
        return None

    async def close(self, outcome: str | None = None, success: bool | None = None) -> None:
        self.closed = True


def make_client():
    """MemoryClient(NamsSettings()) reading MEMORY_API_KEY / MEMORY_ENDPOINT / MEMORY_WORKSPACE_ID."""
    load_dotenv()
    from neo4j_agent_memory import MemoryClient, NamsSettings

    return MemoryClient(NamsSettings())


class NamsRecorder:
    """Records AgentStep + ToolCall pairs under one conversation through the SDK."""

    def __init__(self, conversation_file: Path | None = None, conversation_id: str | None = None, task: str | None = None) -> None:
        self.conversation_file = conversation_file
        self.conversation_id = conversation_id
        self.task = task
        self._client = None
        self._trace_id: str | None = None
        self._queue: asyncio.Queue[ToolRecord | None] | None = None
        self._worker: asyncio.Task | None = None
        self._disabled_reason: str | None = None
        self.written: int = 0

    # -- wiring
    def _resolve_conversation(self) -> str | None:
        if self.conversation_id:
            return self.conversation_id
        path = self.conversation_file or resolve_conversation_file()
        data = read_session(path)
        if data and data.get("conversation_id"):
            self.conversation_id = data["conversation_id"]
            self.task = self.task or data.get("task") or data.get("brief_title")
            return self.conversation_id
        return None

    async def _ensure_started(self) -> bool:
        if self._disabled_reason:
            return False
        if self._trace_id:
            return True
        cid = self._resolve_conversation()
        if not cid:
            log_line(f"recorder: no conversation id yet (looked at {self.conversation_file or resolve_conversation_file()})")
            return False
        try:
            self._client = make_client()
            await self._client.connect()
            trace = await self._client.reasoning.start_trace(session_id=cid, task=self.task or "pmm tool calls")
            self._trace_id = str(trace.id)
            log_line(f"recorder: trace started for conversation {cid}")
            return True
        except Exception as exc:
            self._disabled_reason = f"{type(exc).__name__}: {exc}"
            log_line(f"recorder: disabled, could not start trace: {self._disabled_reason}")
            return False

    async def _write(self, rec: ToolRecord) -> None:
        if not await self._ensure_started():
            return
        assert self._client is not None and self._trace_id is not None
        try:
            step = await self._client.reasoning.add_step(self._trace_id, thought=rec.thought, action=rec.tool_name, observation=rec.observation)
            rec.step_id = str(step.id)
            call = await self._client.reasoning.record_tool_call(
                step.id, rec.tool_name, rec.arguments, result=rec.result, status=rec.status, duration_ms=rec.duration_ms
            )
            rec.tool_call_id = str(call.id)
            self.written += 1
        except Exception as exc:
            log_line(f"recorder: write failed for {rec.tool_name}: {type(exc).__name__}: {exc}\n{traceback.format_exc()}")

    async def _run(self) -> None:
        assert self._queue is not None
        while True:
            rec = await self._queue.get()
            try:
                if rec is None:
                    return
                await self._write(rec)
            finally:
                self._queue.task_done()

    # -- API
    async def record(self, rec: ToolRecord) -> None:
        if self._queue is None:
            self._queue = asyncio.Queue()
            self._worker = asyncio.create_task(self._run())
        await self._queue.put(rec)

    async def flush(self) -> None:
        if self._queue is not None:
            await self._queue.join()

    async def close(self, outcome: str | None = None, success: bool | None = None) -> None:
        await self.flush()
        if self._queue is not None:
            await self._queue.put(None)
            if self._worker is not None:
                await self._worker
        if self._client is not None and self._trace_id is not None:
            try:
                await self._client.reasoning.complete_trace(self._trace_id, outcome=outcome, success=success)
            except Exception as exc:  # pragma: no cover
                log_line(f"recorder: complete_trace failed: {exc}")
        if self._client is not None:
            try:
                await self._client.close()
            except Exception:  # pragma: no cover
                pass
        log_line(f"recorder: closed, {self.written} tool calls written")
