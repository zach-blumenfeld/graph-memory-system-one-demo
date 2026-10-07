"""The agent's tools: what `blast <cmd>` does. Plain functions returning JSON-able dicts so the same
logic serves the CLI (the agent in step 2) and the AIP skill's scripts (step 5)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from blast.env import DRAFTS_DIR, SOP_FILE, ensure_run_dirs
from blast.fixture import Fixture

SPAM_WORDS = ("free", "act now", "last chance")


def sop() -> dict[str, Any]:
    """The team's page, read from memory when the graph has it, else from the file."""
    try:
        from blast.memory import cypher

        rows = cypher("MATCH (p:Playbook) RETURN p.name AS name, p.text AS text LIMIT 1")
        if rows and rows[0].get("text"):
            return {"name": rows[0]["name"], "source": "memory", "text": rows[0]["text"]}
    except Exception:
        pass
    return {"name": "How we run an email blast", "source": "file", "text": SOP_FILE.read_text()}


def brief(brief_id: str) -> dict[str, Any]:
    fx = Fixture()
    b = fx.brief(brief_id)
    return {"brief_id": b["id"], "campaign_id": b["Campaign ID"], "title": b["Name"], "product": b["Product"], "segment_ids": b["Segment"],
            "persona_ids": b["Persona"], "goal": b["Goal"], "key_messages": b["Key messages"], "cta": b["CTA"], "send_window": b["Send window"], "notes": b["Notes"]}


def segments(product: str) -> dict[str, Any]:
    fx = Fixture()
    out = []
    for s in fx.segments(product):
        personas = [fx.persona(p) for p in s["Persona"]]
        out.append({"segment_id": s["id"], "name": s["Name"], "size": s["Size"], "description": s["Description"],
                    "persona": [{"id": p["id"], "name": p["Name"], "preferred_tone": p["Preferred tone"], "turn_offs": p["Turn-offs"]} for p in personas]})
    return {"product": product, "segments": out}


def product(name: str) -> dict[str, Any]:
    p = Fixture().product(name)
    claims = p["Approved claims"] if isinstance(p["Approved claims"], list) else [p["Approved claims"]]
    return {"name": p["Name"], "tagline": p["Tagline"], "version": p["Version"], "docs_url": p["Docs"], "repo_url": p["Repo"], "approved_claims": claims}


def brand() -> dict[str, Any]:
    bg = Fixture().brand_guide()
    return {"voice_rules": bg["Voice rules"], "banned_claims": bg["Banned claims"], "required_disclaimer": bg["Required disclaimer"], "subject_line_rules": bg["Subject line rules"]}


def _draft_path(draft_id: str):
    return DRAFTS_DIR / f"{draft_id}.json"


def submit_draft(campaign_id: str, subject_lines: list[str], body_md: str, segment_id: str) -> dict[str, Any]:
    ensure_run_dirs()
    n = len(list(DRAFTS_DIR.glob(f"draft-{campaign_id}-*.json"))) + 1
    draft_id = f"draft-{campaign_id}-{n:02d}"
    rec = {"draft_id": draft_id, "campaign_id": campaign_id, "segment_id": segment_id, "subject_lines": subject_lines, "body_md": body_md,
           "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "compliance": None}
    _draft_path(draft_id).write_text(json.dumps(rec, indent=2))
    return {"draft_id": draft_id, "campaign_id": campaign_id, "segment_id": segment_id, "subject_lines": subject_lines, "body_chars": len(body_md)}


def _cta_for_campaign(campaign_id: str) -> str:
    for b in Fixture().briefs():
        if b["Campaign ID"] == campaign_id:
            return str(b["CTA"])
    return ""


def _load_draft(draft_id: str) -> dict[str, Any]:
    p = _draft_path(draft_id)
    if not p.exists():
        raise SystemExit(f"unknown draft {draft_id}")
    return json.loads(p.read_text())


def check(draft_id: str) -> dict[str, Any]:
    """Deterministic compliance check against the brand guide and the product's approved claims."""
    d = _load_draft(draft_id)
    bg = Fixture().brand_guide()
    body = d["body_md"]
    failures: list[dict[str, str]] = []
    disclaimer = bg["Required disclaimer"]
    if disclaimer.split(".")[0].lower() not in body.lower():
        failures.append({"check": "has_disclaimer", "detail": f"the required disclaimer is missing; include verbatim: {disclaimer}"})
    banned = [b for b in bg["Banned claims"] if not b.startswith("naming") and not b.startswith("unpublished")]
    hits = [b for b in banned if re.search(r"\b" + re.escape(b.lower()) + r"\b", body.lower())]
    if hits:
        failures.append({"check": "no_banned_claims", "detail": "banned phrases present: " + ", ".join(hits)})
    if "!" in body:
        failures.append({"check": "no_exclamation_marks", "detail": "the body contains an exclamation mark"})
    cta = _cta_for_campaign(d["campaign_id"])
    cta_words = [w for w in re.findall(r"[a-z0-9.-]+", cta.lower()) if len(w) > 3][:4]
    has_link = bool(re.search(r"\[[^\]]+\]\([^)]+\)|https?://", body))
    has_cta_text = bool(cta_words) and sum(w in body.lower() for w in cta_words) >= max(1, len(cta_words) - 1)
    if not (has_link or has_cta_text):
        failures.append({"check": "has_call_to_action", "detail": f"the body carries neither a link nor the brief's call to action ({cta!r})"})
    for s in d["subject_lines"]:
        if len(s) > 60:
            failures.append({"check": "subject_length", "detail": f"over 60 characters: {s!r}"})
        if any(w.isupper() and len(w) > 2 for w in s.split()):
            failures.append({"check": "subject_caps", "detail": f"all-caps word: {s!r}"})
        if any(sw in s.lower() for sw in SPAM_WORDS):
            failures.append({"check": "subject_spam_words", "detail": f"spam word: {s!r}"})
    passed = not failures
    d["compliance"] = {"passed": passed, "failures": failures, "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _draft_path(draft_id).write_text(json.dumps(d, indent=2))
    return {"draft_id": draft_id, "passed": passed, "failures": failures, "required_disclaimer": disclaimer}


def schedule(draft_id: str, segment_id: str, send_at: str, subject_line: str) -> dict[str, Any]:
    d = _load_draft(draft_id)
    if not (d.get("compliance") or {}).get("passed"):
        raise SystemExit(json.dumps({"error": "draft has not passed the compliance check; run `blast check` first", "draft_id": draft_id}))
    if subject_line not in d["subject_lines"]:
        raise SystemExit(json.dumps({"error": "subject_line must be one of the draft's subject lines", "subject_lines": d["subject_lines"]}))
    seg = Fixture().segment(segment_id)
    send_id = "send-" + datetime.now(timezone.utc).strftime("%H%M%S")
    d["scheduled"] = {"send_id": send_id, "segment_id": segment_id, "send_at": send_at, "subject_line": subject_line}
    _draft_path(draft_id).write_text(json.dumps(d, indent=2))
    return {"send_id": send_id, "draft_id": draft_id, "segment": seg["Name"], "recipients": seg["Size"], "send_at": send_at, "subject_line": subject_line, "status": "scheduled"}


def log(campaign_id: str, draft_id: str, summary: str, scheduled: bool) -> dict[str, Any]:
    page = Fixture().append_campaign_log(campaign_id, draft_id, summary, scheduled)
    return {"log_id": page["id"], "campaign_id": campaign_id, "draft_id": draft_id, "scheduled": scheduled}


def decide(question: str, options: list[str], answer: str, why: str) -> dict[str, Any]:
    """Record a judgment call. The hook stores it as a :Decision step; here it just echoes the record."""
    return {"decision": question, "options": options, "answer": answer, "why": why, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
