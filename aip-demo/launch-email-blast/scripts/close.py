#!/usr/bin/env python3
"""End the run without scheduling: legal hold, a digest handed to the newsletter team, or a draft that failed twice.

stdin:  currentState after classify (legal hold), after resubmit (compliance failed), or after pick-subject (digest)
stdout: outcome (legal-hold | compliance-failed | handed-to-newsletter-team), note, log_id
"""
from blastlib import blast, chosen_subject, log_judgments, read_state, resolve_send_at, write

state = read_state()
brief = state["brief"]
title = f"{brief['title']} ({state['brief_id']})"
draft_id = state.get("draft_id", "none")

if state.get("legal_review") and "draft_id" not in state:
    outcome = "legal-hold"
    note = (f"HOLD for legal review: {title}. The brief mentions legal content, pricing, a partner, or a comparison with another "
            f"product, so nothing was drafted or scheduled. A human must get legal sign-off, then rerun the blast for {state['brief_id']}.")
elif not state.get("passed", False):
    outcome = "compliance-failed"
    failures = "; ".join(f"{f.get('check')}: {f.get('detail')}" for f in state.get("failures", [])) or "unknown"
    note = (f"NOT SCHEDULED: {title}. Draft {draft_id} failed the compliance check after one fix-up pass ({failures}). "
            f"A human must fix the draft and rerun the blast. Claims: {state.get('claims_notes', 'n/a')}")
else:
    outcome = "handed-to-newsletter-team"
    send_at, send_rule = resolve_send_at(state.get("send_at", ""), brief.get("send_window", ""), 0)
    note = (f"NOT SCHEDULED (digest/nurture, SOP rule 5): {title}. Draft {draft_id} passed compliance for {state['segment']['segment_id']} "
            f"({state['segment']['name']}, {state['segment'].get('size')} recipients). The newsletter team sends it; suggested send {send_at} "
            f"({send_rule}); recommended subject '{chosen_subject(state)}'. Claims: {state.get('claims_notes', 'n/a')}")

log_judgments(state)
logged = blast("log", state["campaign_id"], "--draft", draft_id, "--not-scheduled", "--summary", note)
write({"outcome": outcome, "note": note, "log_id": logged["log_id"]})
