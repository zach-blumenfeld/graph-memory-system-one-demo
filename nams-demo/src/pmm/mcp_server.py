"""pmm-tools: the eight typed MCP tools of the launch-email-blast workflow.

Three tools (classify_brief, check_brand_compliance, score_subject_lines) hand their decision to
TypeSafe Jev and return the typed answer with probabilities, confidence and a `review_required`
list. Every call is recorded as an AgentStep + ToolCall pair through the neo4j-agent-memory SDK.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from pmm import decisions as dec
from pmm.env import DRAFTS_DIR, ensure_run_dirs, load_dotenv, recording_enabled
from pmm.fixture import Fixture
from pmm.recorder import FakeRecorder, NamsRecorder, NullRecorder, Recorder, ToolRecord, log_line

TOOL_NAMES = [
    "get_campaign_brief",
    "get_audience_segments",
    "classify_brief",
    "submit_draft",
    "check_brand_compliance",
    "score_subject_lines",
    "schedule_send",
    "log_campaign",
]

INSTRUCTIONS = (
    "Product-marketing tools over a Notion workspace for Tessera Labs campaigns. Decision-shaped steps "
    "(classify_brief, check_brand_compliance, score_subject_lines) are answered by a calibrated System One "
    "model and return typed answers with probabilities and confidence; when `review_required` is non-empty "
    "the model is unsure and you must decide. schedule_send refuses drafts whose brand compliance has not "
    "passed. Drafts are written by you and stored with submit_draft."
)


# --------------------------------------------------------------------------- output models
class Brief(BaseModel):
    brief_id: str
    campaign_id: str
    title: str
    product: str
    segment_id: str
    persona_id: str
    channel: str
    goal: str
    key_messages: list[str]
    cta: str
    send_window: str
    notes: str


class Segment(BaseModel):
    segment_id: str
    name: str
    product: str
    persona_id: str
    size: int
    description: str


class SegmentList(BaseModel):
    product: str
    segments: list[Segment]


class Classification(BaseModel):
    brief_id: str
    campaign_type: dec.ChoiceAnswer
    urgency: dec.ScoreAnswer
    needs_legal_review: dec.NoulAnswer
    review_required: list[dec.ReviewItem] = Field(description="Empty means every answer is confident enough to act on")
    decision_model: str


class DraftReceipt(BaseModel):
    draft_id: str
    campaign_id: str
    segment_id: str
    subject_lines: list[str]
    body_chars: int
    compliance_status: str = Field(description="unchecked | passed | failed")
    stored_at: str


class ComplianceResult(BaseModel):
    draft_id: str
    passed: bool
    checks: dict[str, dec.NoulAnswer]
    flagged: list[str] = Field(description="Checks whose verdict is false")
    review_required: list[dec.ReviewItem]
    disclaimer_text_found_verbatim: bool
    required_disclaimer: str = Field(description="The exact Labs disclaimer the brand guide requires")
    voice_rules: list[str] = Field(description="Brand voice rules the draft is checked against")
    banned_claims: list[str]
    decision_model: str


class LineScore(BaseModel):
    line: str
    clarity: dec.ScoreAnswer
    curiosity: dec.ScoreAnswer
    spam_risk: dec.ScoreAnswer
    composite: float = Field(description="clarity + curiosity - spam_risk, using expected levels")


class SubjectLineScores(BaseModel):
    draft_id: str
    persona: str
    ranked: list[LineScore]
    pick: str
    review_required: list[dec.ReviewItem]
    decision_model: str


class ScheduleResult(BaseModel):
    schedule_id: str
    campaign_id: str
    draft_id: str
    segment_id: str
    subject_line: str
    send_at: str
    status: str


class LogResult(BaseModel):
    log_id: str
    campaign_id: str
    draft_id: str
    scheduled: bool
    logged_at: str


# --------------------------------------------------------------------------- draft store
class DraftStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, draft_id: str) -> Path:
        return self.root / f"{draft_id}.json"

    def new_id(self, campaign_id: str) -> str:
        n = len(list(self.root.glob(f"draft-{campaign_id}-*.json"))) + 1
        return f"draft-{campaign_id}-{n:02d}"

    def save(self, draft: dict[str, Any]) -> None:
        self._path(draft["draft_id"]).write_text(json.dumps(draft, indent=2) + "\n")

    def load(self, draft_id: str) -> dict[str, Any]:
        p = self._path(draft_id)
        if not p.exists():
            raise ToolError(f"Unknown draft_id {draft_id!r}. Call submit_draft first.")
        return json.loads(p.read_text())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


RECORD_SETTLE_SECONDS = float(os.environ.get("PMM_RECORD_SETTLE_SECONDS", "1"))


async def _settle(recorder: Recorder) -> None:
    """Wait (bounded) for the recorder queue so a write is durable before the model gets the result.
    A slow or failing NAMS never blocks the tool for longer than RECORD_SETTLE_SECONDS."""
    try:
        await asyncio.wait_for(recorder.flush(), timeout=RECORD_SETTLE_SECONDS)
    except (asyncio.TimeoutError, Exception) as exc:  # noqa: BLE001
        log_line(f"recorder: settle skipped ({type(exc).__name__}: {exc})")


def _summary(obj: Any, limit: int = 240) -> str:
    text = json.dumps(obj, default=str)
    return text if len(text) <= limit else text[: limit - 3] + "..."


# --------------------------------------------------------------------------- server factory
def build_server(fixture: Fixture, decisions: dec.Decisions, recorder: Recorder, drafts_dir: Path | None = None) -> MCPServer:
    store = DraftStore(drafts_dir or DRAFTS_DIR)

    @asynccontextmanager
    async def lifespan(_server: MCPServer):
        try:
            yield {}
        finally:
            await recorder.close(outcome="server shutdown", success=None)

    server = MCPServer("pmm-tools", instructions=INSTRUCTIONS, lifespan=lifespan)

    async def traced(name: str, why: str, arguments: dict[str, Any], fn: Callable[[], Awaitable[BaseModel]], observe: Callable[[BaseModel], str] | None = None) -> BaseModel:
        doc = TOOL_DOCS[name]
        started = time.perf_counter()
        try:
            out = await fn()
        except ToolError as exc:
            ms = int((time.perf_counter() - started) * 1000)
            await recorder.record(ToolRecord(tool_name=name, thought=f"{doc} Why now: {why}", arguments=arguments, result={"error": str(exc)}, status="failure", duration_ms=ms, observation=f"failed: {exc}"))
            await _settle(recorder)
            raise
        except Exception as exc:
            ms = int((time.perf_counter() - started) * 1000)
            await recorder.record(ToolRecord(tool_name=name, thought=f"{doc} Why now: {why}", arguments=arguments, result={"error": f"{type(exc).__name__}: {exc}"}, status="error", duration_ms=ms, observation=f"error: {exc}"))
            raise ToolError(f"{name} failed: {type(exc).__name__}: {exc}") from exc
        ms = int((time.perf_counter() - started) * 1000)
        payload = out.model_dump(mode="json")
        await recorder.record(ToolRecord(tool_name=name, thought=f"{doc} Why now: {why}", arguments=arguments, result=payload, status="success", duration_ms=ms, observation=observe(out) if observe else _summary(payload)))
        await _settle(recorder)
        return out

    # 1 ------------------------------------------------------------------
    @server.tool()
    async def get_campaign_brief(brief_id: str) -> Brief:
        """Fetch a campaign brief from the Notion briefs database: product, segment, persona, goal, key messages, CTA, send window and notes."""
        async def run() -> Brief:
            try:
                b = fixture.brief(brief_id)
            except KeyError as exc:
                raise ToolError(f"Unknown brief_id {brief_id!r}. Known ids look like brief-001.") from exc
            return Brief(
                brief_id=b["id"], campaign_id=b["Campaign ID"], title=b["Name"], product=b["Product"],
                segment_id=(b["Segment"] or [""])[0], persona_id=(b["Persona"] or [""])[0], channel=b["Channel"] or "Email",
                goal=b["Goal"], key_messages=b["Key messages"] if isinstance(b["Key messages"], list) else [b["Key messages"]],
                cta=b["CTA"], send_window=b["Send window"] or "", notes=b["Notes"] or "",
            )
        return await traced("get_campaign_brief", f"the brief {brief_id} is the source of truth for the campaign", {"brief_id": brief_id}, run, lambda o: f"brief {o.brief_id}: {o.title} ({o.product}, {o.segment_id})")

    # 2 ------------------------------------------------------------------
    @server.tool()
    async def get_audience_segments(product: str) -> SegmentList:
        """List the audience segments available for a product, with persona, size and description, so a send can be targeted."""
        async def run() -> SegmentList:
            try:
                segs = fixture.segments(product)
            except KeyError as exc:
                raise ToolError(f"Unknown product {product!r}. Known products: {', '.join(p['Name'] for p in fixture.products())}.") from exc
            return SegmentList(product=product, segments=[Segment(segment_id=s["id"], name=s["Name"], product=s["Product"], persona_id=(s["Persona"] or [""])[0], size=int(s["Size"] or 0), description=s["Description"]) for s in segs])
        return await traced("get_audience_segments", f"the send must target a segment that exists for {product}", {"product": product}, run, lambda o: f"{len(o.segments)} segments for {o.product}")

    # 3 ------------------------------------------------------------------
    @server.tool()
    async def classify_brief(brief_id: str) -> Classification:
        """Ask the System One model to classify a brief: campaign_type (launch/update/nurture/event), urgency 1-5 and whether it needs legal review. Returns typed answers with probabilities, confidence and review_required."""
        async def run() -> Classification:
            try:
                b = fixture.brief(brief_id)
            except KeyError as exc:
                raise ToolError(f"Unknown brief_id {brief_id!r}.") from exc
            r = decisions.classify(b)
            a = r["answers"]
            return Classification(brief_id=brief_id, campaign_type=a["campaign_type"], urgency=a["urgency"], needs_legal_review=a["needs_legal_review"], review_required=r["review_required"], decision_model=r["model"])
        return await traced("classify_brief", "the campaign type, urgency and legal exposure decide how the rest of the launch is handled", {"brief_id": brief_id}, run,
                            lambda o: f"{o.campaign_type.choice} (p={o.campaign_type.probabilities.get(o.campaign_type.choice, 0):.2f}), urgency {o.urgency.level}/5, legal review p={o.needs_legal_review.noul:.2f}, review_required={len(o.review_required)}")

    # 4 ------------------------------------------------------------------
    @server.tool()
    async def submit_draft(campaign_id: str, subject_lines: list[str], body_md: str, segment_id: str) -> DraftReceipt:
        """Store an email draft you wrote: exactly three subject lines and a Markdown body, for a campaign and segment. Returns a draft_id for compliance checking, scoring and scheduling."""
        args = {"campaign_id": campaign_id, "subject_lines": subject_lines, "body_md": body_md, "segment_id": segment_id}
        async def run() -> DraftReceipt:
            if len(subject_lines) != 3:
                raise ToolError(f"submit_draft needs exactly 3 subject lines, got {len(subject_lines)}.")
            if len(body_md.strip()) < 80:
                raise ToolError("body_md is too short to be an email; write the full body in Markdown.")
            try:
                fixture.segment(segment_id)
            except KeyError as exc:
                raise ToolError(f"Unknown segment_id {segment_id!r}; use get_audience_segments.") from exc
            draft_id = store.new_id(campaign_id)
            draft = {"draft_id": draft_id, "campaign_id": campaign_id, "segment_id": segment_id, "subject_lines": subject_lines, "body_md": body_md, "compliance_status": "unchecked", "stored_at": _now()}
            store.save(draft)
            return DraftReceipt(draft_id=draft_id, campaign_id=campaign_id, segment_id=segment_id, subject_lines=subject_lines, body_chars=len(body_md), compliance_status="unchecked", stored_at=draft["stored_at"])
        return await traced("submit_draft", "the draft has to exist in the system before it can be checked, scored or scheduled", args, run, lambda o: f"stored {o.draft_id} ({o.body_chars} chars, 3 subject lines)")

    # 5 ------------------------------------------------------------------
    @server.tool()
    async def check_brand_compliance(draft_id: str) -> ComplianceResult:
        """Ask the System One model whether a draft is on brand: voice, no unapproved claims, one clear CTA, Labs disclaimer. Returns pass/fail, the flagged checks, confidences and review_required."""
        async def run() -> ComplianceResult:
            draft = store.load(draft_id)
            brief = next((b for b in fixture.briefs() if b["Campaign ID"] == draft["campaign_id"]), None)
            product = fixture.product(brief["Product"]) if brief else fixture.products()[0]
            r = decisions.compliance(draft, fixture.brand_guide(), product)
            checks: dict[str, dec.NoulAnswer] = r["answers"]
            flagged = [k for k, v in checks.items() if not v.verdict]
            passed = not flagged
            draft["compliance_status"] = "passed" if passed else "failed"
            draft["compliance"] = {k: v.model_dump() for k, v in checks.items()}
            store.save(draft)
            bg = fixture.brand_guide()
            rules = bg["Voice rules"] if isinstance(bg["Voice rules"], list) else [bg["Voice rules"]]
            return ComplianceResult(draft_id=draft_id, passed=passed, checks=checks, flagged=flagged, review_required=r["review_required"], disclaimer_text_found_verbatim=r["disclaimer_text_found_verbatim"],
                                    required_disclaimer=bg["Required disclaimer"], voice_rules=rules, banned_claims=list(bg["Banned claims"]), decision_model=r["model"])
        return await traced("check_brand_compliance", "nothing may be scheduled until the draft passes the brand check", {"draft_id": draft_id}, run,
                            lambda o: f"{'passed' if o.passed else 'FAILED'}; flagged={o.flagged}; review_required={[i.question for i in o.review_required]}")

    # 6 ------------------------------------------------------------------
    @server.tool()
    async def score_subject_lines(draft_id: str) -> SubjectLineScores:
        """Ask the System One model to score each subject line of a draft on clarity, curiosity and spam risk for the segment's persona. Returns ranked lines, the pick and review_required."""
        async def run() -> SubjectLineScores:
            draft = store.load(draft_id)
            seg = fixture.segment(draft["segment_id"])
            persona = fixture.persona((seg["Persona"] or [""])[0])
            brief = next((b for b in fixture.briefs() if b["Campaign ID"] == draft["campaign_id"]), None) or {"Name": draft["campaign_id"], "Goal": ""}
            r = decisions.score_lines(draft["subject_lines"], persona, brief)
            a = r["answers"]
            ranked: list[LineScore] = []
            for i, line in enumerate(draft["subject_lines"]):
                c, u, s = a[f"line_{i + 1}_clarity"], a[f"line_{i + 1}_curiosity"], a[f"line_{i + 1}_spam_risk"]
                ranked.append(LineScore(line=line, clarity=c, curiosity=u, spam_risk=s, composite=round(c.score + u.score - s.score, 2)))
            ranked.sort(key=lambda x: x.composite, reverse=True)
            draft["scores"] = [x.model_dump() for x in ranked]
            draft["pick"] = ranked[0].line
            store.save(draft)
            return SubjectLineScores(draft_id=draft_id, persona=persona["Name"], ranked=ranked, pick=ranked[0].line, review_required=r["review_required"], decision_model=r["model"])
        return await traced("score_subject_lines", "the subject line is chosen by calibrated score, not by taste", {"draft_id": draft_id}, run,
                            lambda o: f"pick: {o.pick!r} (composite {o.ranked[0].composite}); review_required={len(o.review_required)}")

    # 7 ------------------------------------------------------------------
    @server.tool()
    async def schedule_send(campaign_id: str, draft_id: str, segment_id: str, subject_line: str, send_at: str) -> ScheduleResult:
        """Schedule the email send for a draft to a segment at an ISO-8601 time. Fails if the draft's brand compliance has not passed."""
        args = {"campaign_id": campaign_id, "draft_id": draft_id, "segment_id": segment_id, "subject_line": subject_line, "send_at": send_at}
        async def run() -> ScheduleResult:
            draft = store.load(draft_id)
            if draft.get("compliance_status") != "passed":
                raise ToolError(f"Brand compliance has not passed for {draft_id} (status: {draft.get('compliance_status', 'unchecked')}). Run check_brand_compliance and fix any flagged items before scheduling.")
            if draft["campaign_id"] != campaign_id:
                raise ToolError(f"{draft_id} belongs to campaign {draft['campaign_id']}, not {campaign_id}.")
            try:
                fixture.segment(segment_id)
            except KeyError as exc:
                raise ToolError(f"Unknown segment_id {segment_id!r}.") from exc
            try:
                datetime.fromisoformat(send_at.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ToolError(f"send_at must be ISO-8601, got {send_at!r}.") from exc
            schedule_id = f"send-{uuid.uuid4().hex[:8]}"
            draft["schedule"] = {"schedule_id": schedule_id, "segment_id": segment_id, "subject_line": subject_line, "send_at": send_at, "scheduled_at": _now()}
            store.save(draft)
            return ScheduleResult(schedule_id=schedule_id, campaign_id=campaign_id, draft_id=draft_id, segment_id=segment_id, subject_line=subject_line, send_at=send_at, status="scheduled")
        return await traced("schedule_send", "the draft passed compliance and has a scored subject line, so it can go on the calendar", args, run, lambda o: f"{o.schedule_id} at {o.send_at} to {o.segment_id}")

    # 8 ------------------------------------------------------------------
    @server.tool()
    async def log_campaign(campaign_id: str, draft_id: str, summary: str) -> LogResult:
        """Append the campaign outcome to the Notion campaign log: what was sent, to whom, when, and the decisions made along the way."""
        args = {"campaign_id": campaign_id, "draft_id": draft_id, "summary": summary}
        async def run() -> LogResult:
            draft = store.load(draft_id)
            scheduled = "schedule" in draft
            page = fixture.append_campaign_log(campaign_id, draft_id, summary, scheduled)
            return LogResult(log_id=page["id"], campaign_id=campaign_id, draft_id=draft_id, scheduled=scheduled, logged_at=page["Logged at"])
        return await traced("log_campaign", "the team tracks every campaign in the Notion log, scheduled or not", args, run, lambda o: f"{o.log_id} scheduled={o.scheduled}")

    return server


TOOL_DOCS = {
    "get_campaign_brief": "Fetch the campaign brief from Notion.",
    "get_audience_segments": "List the audience segments for the product.",
    "classify_brief": "Classify the brief with the System One model (type, urgency, legal review).",
    "submit_draft": "Store the email draft (three subject lines and a body).",
    "check_brand_compliance": "Check the draft against the brand guide with the System One model.",
    "score_subject_lines": "Score the subject lines for the persona with the System One model.",
    "schedule_send": "Schedule the send for the compliant draft.",
    "log_campaign": "Log the campaign outcome in Notion.",
}


# --------------------------------------------------------------------------- entrypoints
def make_runtime_server() -> MCPServer:
    """Real wiring: Jev required, recorder on unless PMM_RECORD=0."""
    load_dotenv()
    ensure_run_dirs()
    system_one = dec.TypeSafeSystemOne()  # raises JevUnavailable when the key is missing
    # Fail fast: one tiny round trip proves Jev is reachable before any tool is offered.
    system_one.system_one({"ping": "pmm-tools startup"}, {"ok": {"type": "noul", "instructions": "Is this a startup ping?"}})
    recorder: Recorder = NamsRecorder() if recording_enabled() else NullRecorder()
    log_line(f"pmm-tools starting; recording={'on' if recording_enabled() else 'off'}; conversation file={os.environ.get('PMM_CONVERSATION_FILE') or '(current.json)'}")
    return build_server(Fixture(), dec.Decisions(system_one), recorder)


async def selftest(verbose: bool = True) -> int:
    """No-network check: fake Jev, fake recorder, every tool called once on the happy path."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        rec = FakeRecorder()
        server = build_server(Fixture(), dec.Decisions(dec.FakeSystemOne()), rec, drafts_dir=Path(tmp))
        tools = await server.list_tools()
        names = [t.name for t in tools]
        assert names == TOOL_NAMES, names
        brief = await server.call_tool("get_campaign_brief", {"brief_id": "brief-001"})
        b = brief.structured_content
        await server.call_tool("get_audience_segments", {"product": b["product"]})
        await server.call_tool("classify_brief", {"brief_id": "brief-001"})
        body = "# Hi\n\nReasoning traces are now graph nodes. Upgrade today.\n\n" + Fixture().brand_guide()["Required disclaimer"]
        d = (await server.call_tool("submit_draft", {"campaign_id": b["campaign_id"], "subject_lines": ["a", "b", "c"], "body_md": body, "segment_id": b["segment_id"]})).structured_content
        try:
            await server.call_tool("schedule_send", {"campaign_id": b["campaign_id"], "draft_id": d["draft_id"], "segment_id": b["segment_id"], "subject_line": "a", "send_at": "2026-10-14T09:00:00Z"})
            raise AssertionError("schedule_send should refuse an unchecked draft")
        except ToolError:
            pass
        c = (await server.call_tool("check_brand_compliance", {"draft_id": d["draft_id"]})).structured_content
        assert c["passed"], c
        s = (await server.call_tool("score_subject_lines", {"draft_id": d["draft_id"]})).structured_content
        await server.call_tool("schedule_send", {"campaign_id": b["campaign_id"], "draft_id": d["draft_id"], "segment_id": b["segment_id"], "subject_line": s["pick"], "send_at": "2026-10-14T09:00:00Z"})
        await server.call_tool("log_campaign", {"campaign_id": b["campaign_id"], "draft_id": d["draft_id"], "summary": "selftest"})
        statuses = [r.status for r in rec.records]
        assert statuses == ["success"] * 4 + ["failure"] + ["success"] * 4, statuses
    if verbose:
        print(f"pmm-tools selftest OK: {len(names)} tools, {len(rec.records)} recorded calls (1 deliberate failure)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pmm-tools")
    parser.add_argument("--selftest", action="store_true", help="run the in-process check with fakes and exit")
    args = parser.parse_args(argv)
    if args.selftest:
        return asyncio.run(selftest())
    try:
        server = make_runtime_server()
    except dec.JevUnavailable as exc:
        print(f"pmm-tools refused to start: {exc}", file=sys.stderr)
        return 2
    server.run("stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
