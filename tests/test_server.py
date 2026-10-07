import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from pmm import decisions as dec
from pmm.fixture import Fixture
from pmm.mcp_server import TOOL_NAMES, build_server, selftest
from pmm.recorder import FakeRecorder

BODY = (
    "# riverbed 1.8\n\nPipeline state is now checkpointed, so a restarted worker resumes where it stopped.\n\n"
    "Upgrade: `pip install -U riverbed` and open the checkpoint quickstart.\n\n"
    "Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice."
)


def make(drafts_dir, system_one=None, recorder=None):
    rec = recorder or FakeRecorder()
    srv = build_server(Fixture(), dec.Decisions(system_one or dec.FakeSystemOne()), rec, drafts_dir=drafts_dir)
    return srv, rec


async def test_tool_registry_and_schemas(drafts_dir):
    srv, _ = make(drafts_dir)
    tools = {t.name: t for t in await srv.list_tools()}
    assert list(tools) == TOOL_NAMES
    assert set(tools["classify_brief"].output_schema["properties"]) >= {"campaign_type", "urgency", "needs_legal_review", "review_required"}
    assert set(tools["check_brand_compliance"].output_schema["properties"]) >= {"passed", "checks", "flagged", "review_required"}
    assert set(tools["score_subject_lines"].output_schema["properties"]) >= {"ranked", "pick", "review_required"}
    assert tools["submit_draft"].input_schema["required"] == ["campaign_id", "subject_lines", "body_md", "segment_id"]
    assert tools["schedule_send"].input_schema["required"] == ["campaign_id", "draft_id", "segment_id", "subject_line", "send_at"]
    for t in tools.values():
        assert t.description and t.output_schema is not None


async def test_happy_path_records_eight_calls(drafts_dir):
    srv, rec = make(drafts_dir)
    b = (await srv.call_tool("get_campaign_brief", {"brief_id": "brief-001"})).structured_content
    segs = (await srv.call_tool("get_audience_segments", {"product": b["product"]})).structured_content
    assert any(s["segment_id"] == b["segment_id"] for s in segs["segments"])
    cls = (await srv.call_tool("classify_brief", {"brief_id": "brief-001"})).structured_content
    assert cls["campaign_type"]["choice"] == "launch" and cls["review_required"] == []
    d = (await srv.call_tool("submit_draft", {"campaign_id": b["campaign_id"], "subject_lines": ["One", "Two", "Three"], "body_md": BODY, "segment_id": b["segment_id"]})).structured_content
    c = (await srv.call_tool("check_brand_compliance", {"draft_id": d["draft_id"]})).structured_content
    assert c["passed"] and c["disclaimer_text_found_verbatim"]
    s = (await srv.call_tool("score_subject_lines", {"draft_id": d["draft_id"]})).structured_content
    assert s["pick"] in ["One", "Two", "Three"] and len(s["ranked"]) == 3
    sch = (await srv.call_tool("schedule_send", {"campaign_id": b["campaign_id"], "draft_id": d["draft_id"], "segment_id": b["segment_id"], "subject_line": s["pick"], "send_at": "2026-10-14T09:00:00Z"})).structured_content
    assert sch["status"] == "scheduled"
    lg = (await srv.call_tool("log_campaign", {"campaign_id": b["campaign_id"], "draft_id": d["draft_id"], "summary": "done"})).structured_content
    assert lg["scheduled"] is True
    assert [r.tool_name for r in rec.records] == TOOL_NAMES
    assert all(r.status == "success" for r in rec.records)
    assert all(r.step_id and r.tool_call_id for r in rec.records)
    # Jev's typed answers are in the recorded result, which is what the distiller sees.
    recorded_cls = rec.records[2].result
    assert recorded_cls["campaign_type"]["probabilities"]["launch"] >= 0.9


async def test_anti_pattern_schedule_before_compliance_fails(drafts_dir):
    srv, rec = make(drafts_dir)
    b = (await srv.call_tool("get_campaign_brief", {"brief_id": "brief-009"})).structured_content
    d = (await srv.call_tool("submit_draft", {"campaign_id": b["campaign_id"], "subject_lines": ["a", "b", "c"], "body_md": BODY, "segment_id": b["segment_id"]})).structured_content
    with pytest.raises(ToolError, match="compliance has not passed"):
        await srv.call_tool("schedule_send", {"campaign_id": b["campaign_id"], "draft_id": d["draft_id"], "segment_id": b["segment_id"], "subject_line": "a", "send_at": "2026-10-07T09:00:00Z"})
    assert rec.records[-1].tool_name == "schedule_send" and rec.records[-1].status == "failure"
    assert "compliance" in rec.records[-1].result["error"]


async def test_compliance_failure_blocks_schedule(drafts_dir):
    srv, _ = make(drafts_dir, system_one=dec.FakeSystemOne(nouls={"has_labs_disclaimer": 0.1}))
    b = (await srv.call_tool("get_campaign_brief", {"brief_id": "brief-002"})).structured_content
    d = (await srv.call_tool("submit_draft", {"campaign_id": b["campaign_id"], "subject_lines": ["a", "b", "c"], "body_md": BODY.replace("Tessera Labs projects", "Our projects"), "segment_id": b["segment_id"]})).structured_content
    c = (await srv.call_tool("check_brand_compliance", {"draft_id": d["draft_id"]})).structured_content
    assert c["passed"] is False and c["flagged"] == ["has_labs_disclaimer"] and c["disclaimer_text_found_verbatim"] is False
    with pytest.raises(ToolError, match="status: failed"):
        await srv.call_tool("schedule_send", {"campaign_id": b["campaign_id"], "draft_id": d["draft_id"], "segment_id": b["segment_id"], "subject_line": "a", "send_at": "2026-10-15T09:00:00Z"})


async def test_escalation_when_jev_is_unsure(drafts_dir):
    srv, _ = make(drafts_dir, system_one=dec.FakeSystemOne(nouls={"needs_legal_review": 0.55}, confidence=0.5))
    cls = (await srv.call_tool("classify_brief", {"brief_id": "brief-011"})).structured_content
    assert {i["question"] for i in cls["review_required"]} == {"campaign_type", "urgency", "needs_legal_review"}


async def test_input_validation(drafts_dir):
    srv, rec = make(drafts_dir)
    with pytest.raises(ToolError, match="Unknown brief_id"):
        await srv.call_tool("get_campaign_brief", {"brief_id": "nope"})
    with pytest.raises(ToolError, match="exactly 3"):
        await srv.call_tool("submit_draft", {"campaign_id": "camp-x", "subject_lines": ["a"], "body_md": BODY, "segment_id": "seg-python-agent-devs"})
    assert [r.status for r in rec.records] == ["failure", "failure"]


async def test_selftest_entrypoint():
    assert await selftest(verbose=False) == 0
