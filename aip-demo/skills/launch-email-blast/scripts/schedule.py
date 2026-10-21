#!/usr/bin/env python3
"""Schedule the passing draft to the segment for the send time the SOP's rule gives, then log the campaign
and the judgment calls (SOP "Scheduling and logging").

stdin:  state with brief_id, campaign_id, brief, segment, segment_rule, persona, draft_id, subjects, subject_pick,
        send_at, email_kind, urgency, legal_review, claims_notes
stdout: send_id, scheduled_at, send_rule, subject, log_id, note
"""
from blastlib import blast, chosen_subject, log_judgments, read_state, resolve_send_at, urgency_label, write

s = read_state()
subject = chosen_subject(s["subjects"], s["subject_pick"])
scheduled_at, send_rule = resolve_send_at(s.get("send_at", ""), s["brief"].get("send_window", ""), s["urgency"])
seg = s["segment"]

sent = blast("schedule", s["draft_id"], "--segment", seg["segment_id"], "--at", scheduled_at, "--subject", subject)

note = (f"{s['brief']['title']} ({s['brief_id']}): {s['email_kind']}, {urgency_label(s['urgency'])}. "
        f"Draft {s['draft_id']} passed compliance on the first check and is scheduled as {sent['send_id']} to "
        f"{seg['segment_id']} ({seg['name']}, {sent.get('recipients', seg.get('size'))} recipients) for {scheduled_at} "
        f"({send_rule}) with subject '{subject}'. Segment: {s['segment_rule']}. "
        f"Legal review: {'flagged' if s['legal_review'] else 'not needed, no pricing, partner, legal or comparison content'}. "
        f"Claims: {s['claims_notes']}")
log_judgments(s)
logged = blast("log", s["campaign_id"], "--draft", s["draft_id"], "--scheduled", "--summary", note)

write({"send_id": sent["send_id"], "scheduled_at": scheduled_at, "send_rule": send_rule, "subject": subject,
       "log_id": logged["log_id"], "note": note})
