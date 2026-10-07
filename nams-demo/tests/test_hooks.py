import json
import os

import pytest

from pmm import hooks
from pmm.recorder import read_session, session_file_for


class FakeMemory:
    def __init__(self):
        self.conversations = []
        self.messages = []

    async def create_conversation(self, metadata):
        self.conversations.append(metadata)
        return f"conv-{len(self.conversations)}"

    async def add_message(self, conversation_id, role, content):
        self.messages.append((conversation_id, role, content))


@pytest.fixture(autouse=True)
def recording_on(monkeypatch):
    monkeypatch.setenv("PMM_RECORD", "1")


# Payloads shaped like the Claude Code hooks reference (checked 2026-10-06).
UPS = {"session_id": "sess-1", "transcript_path": "/tmp/t.jsonl", "cwd": "/repo", "hook_event_name": "UserPromptSubmit", "prompt": "New brief in Notion: brief-013. Launch the email blast."}
PTU = {"session_id": "sess-1", "hook_event_name": "PostToolUse", "tool_name": "mcp__pmm-tools__classify_brief", "tool_input": {"brief_id": "brief-013"}, "tool_response": "{}", "tool_use_id": "toolu_1"}
STOP = {"session_id": "sess-1", "hook_event_name": "Stop", "last_assistant_message": "Scheduled and logged.", "tool_use_ids": ["toolu_1"]}


async def test_interactive_session_lifecycle():
    mem = FakeMemory()
    data = await hooks.handle("user-prompt-submit", UPS, mem)
    assert data["conversation_id"] == "conv-1" and data["brief_id"] == "brief-013"
    assert mem.conversations[0]["runKind"] == "interactive"
    assert mem.messages == [("conv-1", "user", UPS["prompt"])]
    await hooks.handle("post-tool-use", PTU, mem)
    await hooks.handle("stop", STOP, mem)
    saved = read_session(session_file_for("sess-1"))
    assert saved["tool_uses"][0]["tool_name"] == "mcp__pmm-tools__classify_brief"
    assert saved["completed_at"] and saved["messages"] == 2
    assert mem.messages[-1] == ("conv-1", "assistant", "Scheduled and logged.")


async def test_precreated_session_is_reused():
    from pmm.recorder import write_session

    write_session(session_file_for("sess-2"), {"session_id": "sess-2", "conversation_id": "pre-made", "messages": 0, "tool_uses": []})
    mem = FakeMemory()
    data = await hooks.handle("user-prompt-submit", {**UPS, "session_id": "sess-2"}, mem)
    assert data["conversation_id"] == "pre-made" and mem.conversations == []
    assert mem.messages[0][0] == "pre-made"


async def test_recording_off_is_a_noop(monkeypatch):
    monkeypatch.setenv("PMM_RECORD", "0")
    mem = FakeMemory()
    assert await hooks.handle("user-prompt-submit", {**UPS, "session_id": "sess-3"}, mem) is None
    assert mem.conversations == []


async def test_stop_without_session_file_is_ignored():
    mem = FakeMemory()
    assert await hooks.handle("stop", {**STOP, "session_id": "nope"}, mem) is None


def test_main_never_fails(monkeypatch, capsys):
    import io, sys

    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert hooks.main(["stop"]) == 0
