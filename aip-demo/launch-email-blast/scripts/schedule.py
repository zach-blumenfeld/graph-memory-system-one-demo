#!/usr/bin/env python3
"""Schedule the passing draft to the segment and log the campaign as scheduled.

stdin:  currentState with draft_id, subjects, subject_pick, segment, send_at, brief, urgency, email_kind, ...
stdout: send_id, send_at, send_rule, subject, log_id, outcome ("scheduled"), note
"""
from blastlib import blast, chosen_subject, log_judgments, read_state, resolve_send_at, write

state = read_state()
subject = chosen_subject(state)
send_at, send_rule = resolve_send_at(state.get("send_at", ""), state["brief"].get("send_window", ""), state.get("urgency", 0))
seg = state["segment"]

sent = blast("schedule", state["draft_id"], "--segment", seg["segment_id"], "--at", send_at, "--subject", subject)
log_judgments(state)

urgency = "urgent, same-day" if int(state.get("urgency", 0)) >= 1 else "normal urgency"
fixup = (f" Compliance failed once ({'; '.join(f['check'] for f in state.get('failures', []))} on the first draft) and passed after one fix-up pass."
         if int(state.get("attempt", 1)) > 1 else " Draft passed compliance on the first check.")
summary = (f"{state['brief']['title']} ({state['brief_id']}): {state.get('email_kind', 'email')}, {urgency}. "
           f"Draft {state['draft_id']} scheduled as {sent['send_id']} to {seg['segment_id']} ({seg['name']}, {sent.get('recipients', seg.get('size'))} recipients) "
           f"for {send_at} ({send_rule}) with subject '{subject}'.{fixup} Segment: {state.get('segment_rule', 'named by the brief')}. "
           f"Legal review: {'flagged' if state.get('legal_review') else 'not needed'}. "
           f"Claims: {state.get('claims_notes', 'all key messages on the approved list')}")
logged = blast("log", state["campaign_id"], "--draft", state["draft_id"], "--scheduled", "--summary", summary)

write({"send_id": sent["send_id"], "send_at": send_at, "send_rule": send_rule, "subject": subject,
       "log_id": logged["log_id"], "outcome": "scheduled", "note": summary})
