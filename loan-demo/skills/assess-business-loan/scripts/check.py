#!/usr/bin/env python3
"""Submit the rationale with `loan rationale submit`, then lint it with `loan check`.

Used by two steps; the state tells it which:
  check    stdin: application_id, outcome, rationale
           stdout: rationale_id, passed, failures, failures_md, attempt (1), check_state (passed | fix)
  recheck  stdin: application_id, outcome, rationale_fixed, attempt (from check)
           stdout: recheck_rationale_id, recheck_passed, recheck_failures, recheck_state (passed | stop)

SOP "The write-up": submit it, run the check, fix what the check names, run it once more. One fix pass,
no loops: the second failure is `stop` and `record` leaves the decision unfiled with a note for a human.
Each run also writes the latest submission's id and result to the run's working directory for `record`,
which can only declare the first check's keys (see loanlib.handoff_path).
"""
import tempfile
from pathlib import Path

from loanlib import loan, read_state, write, write_handoff

state = read_state()
app_id = str(state["application_id"])
outcome = str(state["outcome"])
recheck = "rationale_fixed" in state
text = str(state["rationale_fixed"] if recheck else state["rationale"]).strip() + "\n"
if not text.strip():
    raise SystemExit("the rationale is empty")

path = Path(tempfile.mkdtemp(prefix="loan-rationale-")) / f"{app_id}.md"
path.write_text(text)

submitted = loan("rationale", "submit", "--file", str(path), "--application", app_id, "--outcome", outcome)
rid = str(submitted["rationale_id"])
result = loan("check", rid)

attempt = int(state.get("attempt", 0)) + 1
passed = bool(result.get("passed"))
failures = result.get("failures", [])
if passed:
    check_state = "passed"
elif attempt < 2:
    check_state = "fix"
else:
    check_state = "stop"

write_handoff(app_id, {"application_id": app_id, "rationale_id": rid, "outcome": outcome, "passed": passed,
                       "failures": failures, "attempt": attempt, "check_state": check_state,
                       "cites": result.get("cites", [])})

if recheck:
    write({"recheck_rationale_id": rid, "recheck_passed": passed, "recheck_failures": failures, "recheck_state": check_state})
else:
    failures_md = "\n".join(f"- {f.get('check')}: {f.get('detail')}" for f in failures) or "- none"
    write({"rationale_id": rid, "passed": passed, "failures": failures, "failures_md": failures_md,
           "attempt": attempt, "check_state": check_state})
