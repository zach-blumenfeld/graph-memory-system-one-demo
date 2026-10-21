#!/usr/bin/env python3
"""End the run without scheduling, and log why. Launched as `python close.py <mode>`:

  hold        a legal flag: nothing is drafted; the campaign log carries a hold note for a human
              (SOP: flag for legal review before you schedule anything)
  newsletter  a digest or nurture email: drafted, checked and logged; the newsletter team sends it
              (SOP rule 5)
  recheck     the one fix-up pass: store the fixed draft, check it again, log the result either way;
              a human schedules a draft that needed fixing (SOP: fix what it names and run it again)

stdin:  state with the keys the step declares (see SKILL.md)
stdout: hold_log_id, hold_note | handoff_log_id, handoff_note |
        fixed_draft_id, fixed_passed, fixed_failures, recheck_log_id, recheck_note
"""
import sys

from blastlib import blast, chosen_subject, log_judgments, read_state, resolve_send_at, submit_and_check, urgency_label, write

mode = sys.argv[1] if len(sys.argv) > 1 else ""
s = read_state()
brief = s["brief"]
title = f"{brief['title']} ({s['brief_id']})"

if mode == "hold":
    note = (f"HOLD for legal review: {title}, classed as {s['email_kind']}, {urgency_label(s['urgency'])}. The brief "
            f"mentions legal content, pricing, a partner, or a comparison with another product, so nothing was drafted "
            f"or scheduled. A human must get legal sign-off, then rerun the blast for {s['brief_id']} "
            f"(send window {brief.get('send_window', 'unknown')}).")
    log_judgments(s)
    logged = blast("log", s["campaign_id"], "--draft", "none", "--not-scheduled", "--summary", note)
    write({"hold_log_id": logged["log_id"], "hold_note": note})

elif mode == "newsletter":
    seg = s["segment"]
    send_at, send_rule = resolve_send_at(s.get("send_at", ""), brief.get("send_window", ""), 0)
    note = (f"NOT SCHEDULED by marketing (digest or nurture, SOP rule 5): {title}. Draft {s['draft_id']} passed compliance "
            f"for {seg['segment_id']} ({seg['name']}, {seg.get('size')} recipients). The newsletter team sends it; "
            f"intended send {send_at} ({send_rule}); recommended subject '{chosen_subject(s['subjects'], s['subject_pick'])}'. "
            f"Segment: {s['segment_rule']}. Legal review: {'flagged' if s['legal_review'] else 'not needed'}. "
            f"Claims: {s['claims_notes']}")
    log_judgments(s)
    logged = blast("log", s["campaign_id"], "--draft", s["draft_id"], "--not-scheduled", "--summary", note)
    write({"handoff_log_id": logged["log_id"], "handoff_note": note})

elif mode == "recheck":
    seg = s["segment"]
    draft, check = submit_and_check(s["campaign_id"], seg["segment_id"], s["fixed_subjects"], s["fixed_body"], "fixed")
    passed = bool(check["passed"])
    first = "; ".join(f"{f.get('check')}: {f.get('detail')}" for f in s["failures"]) or "unknown"
    if passed:
        send_at, send_rule = resolve_send_at(s.get("send_at", ""), brief.get("send_window", ""), s["urgency"])
        if s["email_kind"] == "digest":
            next_step = "The newsletter team sends it (SOP rule 5)."
        else:
            next_step = (f"A draft that needed fixing is scheduled by a human: pick one of its three subject lines and run "
                         f"`blast schedule {draft['draft_id']} --segment {seg['segment_id']} --at {send_at} --subject <line>` "
                         f"({send_rule}).")
        note = (f"PASSED AFTER ONE FIX-UP, not scheduled: {title}, {s['email_kind']}, {urgency_label(s['urgency'])}. "
                f"The first draft {s.get('draft_id', '')} failed the compliance check ({first}); the fixed draft "
                f"{draft['draft_id']} passed. Fix: {s['fix_notes']} {next_step} Claims: {s['claims_notes']}")
    else:
        again = "; ".join(f"{f.get('check')}: {f.get('detail')}" for f in check.get("failures", []))
        note = (f"NOT SCHEDULED, compliance failed twice: {title}. The first draft failed ({first}); after one fix-up pass "
                f"the fixed draft {draft['draft_id']} still fails ({again}). A human must fix the draft, pass `blast check`, "
                f"and schedule it. Fix attempted: {s['fix_notes']} Claims: {s['claims_notes']}")
    log_judgments(s)
    logged = blast("log", s["campaign_id"], "--draft", draft["draft_id"], "--not-scheduled", "--summary", note)
    write({"fixed_draft_id": draft["draft_id"], "fixed_passed": passed, "fixed_failures": check.get("failures", []),
           "recheck_log_id": logged["log_id"], "recheck_note": note})

else:
    raise SystemExit(f"close.py: unknown mode {mode!r}; expected hold, newsletter or recheck")
