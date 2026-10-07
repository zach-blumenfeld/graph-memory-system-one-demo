#!/usr/bin/env python3
"""Store the draft with `blast draft`, then run `blast check` on it.

stdin:  currentState with campaign_id, segment, subjects (3 strings), body (markdown); attempt (optional)
stdout: draft_id, passed, failures, attempt, check_state (passed | fix | stop), required_disclaimer
"""
import tempfile
from pathlib import Path

from blastlib import blast, read_state, write

state = read_state()
subjects = [str(s).strip() for s in state["subjects"]]
if len(subjects) != 3 or not all(subjects):
    raise SystemExit(f"subjects must be exactly three non-empty lines, got {subjects!r}")
body = str(state["body"]).strip() + "\n"
if not body.strip():
    raise SystemExit("body is empty")

body_file = Path(tempfile.mkdtemp(prefix="blast-")) / f"{state['campaign_id']}.md"
body_file.write_text(body)

draft = blast("draft", state["campaign_id"], "--body-file", str(body_file), "--segment", state["segment"]["segment_id"],
              "--subject", subjects[0], "--subject", subjects[1], "--subject", subjects[2])
check = blast("check", draft["draft_id"])

attempt = int(state.get("attempt", 0)) + 1
# One fix-up pass only: a second failure ends the run.
check_state = "passed" if check["passed"] else ("fix" if attempt < 2 else "stop")

write({"draft_id": draft["draft_id"], "subjects": subjects, "body": body, "passed": bool(check["passed"]),
       "failures": check.get("failures", []), "attempt": attempt, "check_state": check_state,
       "required_disclaimer": check.get("required_disclaimer", "")})
