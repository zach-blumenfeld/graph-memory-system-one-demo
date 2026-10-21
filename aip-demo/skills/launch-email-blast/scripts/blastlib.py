"""Shared helpers for the launch-email-blast scripts: call `blast`, read the step payload, apply the SOP's rules.

Every script runs from this folder with one JSON object on stdin ({"state": <the step's declared inputs>,
"assets": ..., "expects": ...}) and prints one JSON object holding exactly the step's declared outputs.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

JSON = dict[str, Any]

SUBJECT_INDEX = {"first": 0, "second": 1, "third": 2}


def read_state() -> JSON:
    return json.load(sys.stdin)["state"]


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
    """SOP "Judgment calls": log each one with `blast decide`. Its --options is comma-split, so one
    question per call and no commas inside an option."""
    opts = ",".join(o.replace(",", ";") for o in options)
    blast("decide", "--question", question, "--options", opts, "--answer", answer, "--why", why)


def workdir() -> Path:
    return Path(os.environ.get("AIP_WORKDIR") or os.getcwd())


def write_body(campaign_id: str, tag: str, body: str) -> Path:
    """The body goes to a markdown file under the run's working directory (the traces wrote
    blast-body-<campaign>.md there) so `blast draft --body-file` can read it."""
    path = workdir() / "drafts" / f"{campaign_id}-{tag}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.strip() + "\n")
    return path


def submit_and_check(campaign_id: str, segment_id: str, subjects: list[Any], body: str, tag: str) -> tuple[JSON, JSON]:
    """`blast draft` then `blast check`, the two calls every trace made in that order."""
    lines = [str(s).strip() for s in subjects]
    if len(lines) != 3 or not all(lines):
        raise SystemExit(f"subjects must be exactly three non-empty lines, got {lines!r}")
    if not str(body).strip():
        raise SystemExit("body is empty")
    path = write_body(campaign_id, tag, str(body))
    draft = blast("draft", campaign_id, "--body-file", str(path), "--segment", segment_id,
                  "--subject", lines[0], "--subject", lines[1], "--subject", lines[2])
    check = blast("check", draft["draft_id"])
    return draft, check


def chosen_subject(subjects: list[Any], pick: str) -> str:
    return str(subjects[SUBJECT_INDEX[pick]])


def resolve_send_at(send_at: str, send_window: str, urgency: int, now: datetime | None = None) -> tuple[str, str]:
    """The send time and the rule that produced it.

    1. An explicit `send_at` wins (run-04 used the requested 10:00 over the 09:00 default; run-02 kept the
       requested time even though it had passed).
    2. Urgent (a hotfix or security notice) goes out the same day: today 09:00 UTC, or the next full hour
       when 09:00 has passed.
    3. Otherwise the brief's send window at 09:00 UTC (a window that already carries a time is used as is).
       A window that has already passed moves to the next 09:00 UTC slot and the rule says so, for the
       brief owner to pull if they disagree (run-01).
    """
    now = now or datetime.now(timezone.utc)
    if send_at and send_at.strip():
        return send_at.strip(), "the send time given with the request"
    if int(urgency) >= 1:
        if now.hour < 9:
            return now.strftime("%Y-%m-%dT09:00Z"), "urgent: same-day send per the SOP, at the 09:00 UTC default"
        nxt = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        return nxt.strftime("%Y-%m-%dT%H:%MZ"), "urgent: same-day send per the SOP; 09:00 UTC has passed, so the next full hour"
    window = (send_window or "").strip()
    if not window:
        raise SystemExit("no send_at given and the brief has no send window")
    if "T" in window:
        return window, "the brief's send window, which carries a time"
    try:
        at = datetime.strptime(window, "%Y-%m-%d").replace(hour=9, tzinfo=timezone.utc)
    except ValueError:
        raise SystemExit(f"the brief's send window {window!r} is not a date (YYYY-MM-DD) or ISO time")
    if at >= now:
        return f"{window}T09:00Z", "the brief's send window at the 09:00 UTC default"
    slot = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if slot <= now:
        slot += timedelta(days=1)
    return slot.strftime("%Y-%m-%dT09:00Z"), (f"the brief's send window {window} had already passed, so the next 09:00 UTC slot; "
                                              f"flagged for the brief owner to pull or re-time")


def urgency_label(urgency: int) -> str:
    return "urgent, same-day" if int(urgency) >= 1 else "normal urgency"


def log_judgments(s: JSON) -> None:
    """Record the typed decisions and the rule-based picks the way the SOP asks (`blast decide`), from
    whichever of these keys the calling step declared."""
    brief_id = s.get("brief_id", "the brief")
    if "email_kind" in s and "urgency" in s:
        decide(f"What kind of email is {brief_id} and how urgent is it?",
               ["launch", "update", "digest", "event", "normal", "urgent same-day"],
               f"{s['email_kind']}, {urgency_label(s['urgency'])}",
               "Decision model, judged from the brief against the SOP: a hotfix or security notice is urgent and goes "
               "the same day; digests and nurture emails are not scheduled by marketing.")
    if "legal_review" in s:
        decide(f"Does {brief_id} need legal review before scheduling?", ["flag for legal", "no legal review"],
               "flag for legal" if s["legal_review"] else "no legal review",
               "Decision model, judged from the brief: legal content, pricing, a partner, or a comparison with "
               "another product means legal must see it first.")
    if "segment" in s:
        decide(f"Which segment for {brief_id}?", [s["segment"]["segment_id"]], s["segment"]["segment_id"],
               f"SOP rule: {s.get('segment_rule', 'the segment named by the brief')}.")
    if s.get("claims_notes"):
        decide(f"Which key messages of {brief_id} are on the approved claims list?",
               ["include as written", "rephrase to an approved claim", "leave out"], "see why", str(s["claims_notes"]))
    if "subject_pick" in s and "subjects" in s:
        persona = (s.get("persona") or {}).get("name", "the persona")
        decide(f"Which subject line for {brief_id}?", [str(x) for x in s["subjects"]],
               chosen_subject(s["subjects"], s["subject_pick"]),
               f"Decision model: clearest for {persona}, then the most curious, never one that could read as spam.")
