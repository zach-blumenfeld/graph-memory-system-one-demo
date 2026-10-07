"""Shared helpers for the launch-email-blast scripts: call `blast`, read/write the step payload.

Every script runs with cwd = this folder, one JSON object on stdin
({"currentState": ..., "assets": ..., "expects": ...}) and one JSON object on stdout.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

JSON = dict[str, Any]


def read_state() -> JSON:
    return json.load(sys.stdin)["currentState"]


def write(result: JSON) -> None:
    json.dump(result, sys.stdout)


def blast(*args: str) -> Any:
    """Run `blast <args>` and parse its JSON. A non-zero exit fails the step with blast's message."""
    proc = subprocess.run(["blast", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr.strip() or proc.stdout.strip())[:2000]
        raise SystemExit(f"blast {' '.join(args[:2])} failed (exit {proc.returncode}): {detail}")
    out = proc.stdout.strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise SystemExit(f"blast {' '.join(args[:2])} returned non-JSON output: {out[:500]}")


def decide(question: str, options: list[str], answer: str, why: str) -> None:
    """SOP: every judgment call is logged with `blast decide`. Options are comma-separated, so strip commas."""
    opts = ",".join(o.replace(",", ";") for o in options)
    blast("decide", "--question", question, "--options", opts, "--answer", answer, "--why", why)


SUBJECT_INDEX = {"first": 0, "second": 1, "third": 2}


def chosen_subject(state: JSON) -> str:
    return state["subjects"][SUBJECT_INDEX[state["subject_pick"]]]


def resolve_send_at(send_at: str, send_window: str, urgency: int, now: datetime | None = None) -> tuple[str, str]:
    """The send time and the rule that produced it.

    1. An explicit `send_at` wins (the trace for the hotfix used the requested 10:00 over the 09:00 default).
    2. Urgent (hotfix, security notice) goes out the same day: today at 09:00 UTC, or the next full hour if
       09:00 has passed.
    3. Otherwise the brief's send window at 09:00 UTC (a window that already carries a time is used as is).
    """
    now = now or datetime.now(timezone.utc)
    if send_at and send_at.strip():
        return send_at.strip(), "send time given with the request"
    if int(urgency) >= 1:
        today = now.strftime("%Y-%m-%d")
        if now.hour < 9:
            return f"{today}T09:00Z", "urgent: same-day send per the SOP, at the 09:00 UTC default"
        nxt = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
        return nxt.strftime("%Y-%m-%dT%H:%MZ"), "urgent: same-day send per the SOP; 09:00 UTC has passed so the next full hour"
    window = (send_window or "").strip()
    if not window:
        raise SystemExit("no send_at given and the brief has no send window")
    if "T" in window:
        return window, "the brief's send window, which carries a time"
    return f"{window}T09:00Z", "the brief's send window at the 09:00 UTC default"


def log_judgments(state: JSON) -> None:
    """Record the typed decisions and the rule-based picks the way the SOP asks (`blast decide`)."""
    brief_id = state["brief_id"]
    if "email_kind" in state:
        decide(f"What kind of email is {brief_id} and how urgent is it?",
               ["launch", "update", "digest", "event", "normal", "urgent"],
               f"{state['email_kind']}, {'urgent (same day)' if int(state.get('urgency', 0)) >= 1 else 'normal'}",
               "Decision model, judged from the brief against the SOP: a hotfix or security notice is urgent and goes the same day; "
               "digests and nurture emails are not scheduled by marketing.")
    if "legal_review" in state:
        decide(f"Does {brief_id} need legal review before scheduling?", ["flag for legal", "no legal review needed"],
               "flag for legal" if state["legal_review"] else "no legal review needed",
               "Decision model, judged from the brief: legal content, pricing, a partner, or a comparison with another product means legal must see it first.")
    if "segment" in state:
        decide(f"Which segment should receive {brief_id}?", [state["segment"]["segment_id"]],
               state["segment"]["segment_id"], f"SOP rule: {state.get('segment_rule', 'the segment named by the brief')}.")
    if state.get("claims_notes"):
        decide(f"Which key messages of {brief_id} are on the approved claims list?", ["include as written", "rephrase to an approved claim", "leave out"],
               "see why", state["claims_notes"])
    if "subject_pick" in state and "subjects" in state:
        decide(f"Which subject line for {brief_id}?", list(state["subjects"]), chosen_subject(state),
               f"Decision model: clearest for {state.get('persona', {}).get('name', 'the persona')}, then the most curious, never one that reads as spam.")
