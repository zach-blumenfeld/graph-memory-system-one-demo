#!/usr/bin/env python3
"""Submit the rationale with `loan rationale submit`, then lint it with `loan check`.

stdin:  currentState with application_id, outcome, rationale (markdown); attempt (optional, int)
stdout: rationale_id, passed, failures, failures_md, cites, attempt, check_state (passed | fix | stop), note

SOP "The write-up": submit it, run the check, fix what the check names, run it once more. One fix pass,
no loops: the second failure is `stop` and the run ends unfiled with a note for a human.
Used by both the `check` and the `recheck` steps.
"""
import tempfile
from pathlib import Path

from loanlib import loan, read_state, write

state = read_state()
app_id = str(state["application_id"])
outcome = str(state["outcome"])
text = str(state["rationale"]).strip() + "\n"
if not text.strip():
    raise SystemExit("rationale is empty")

path = Path(tempfile.mkdtemp(prefix="loan-rationale-")) / f"{app_id}.md"
path.write_text(text)

submitted = loan("rationale", "submit", "--file", str(path), "--application", app_id, "--outcome", outcome)
rid = submitted["rationale_id"]
check = loan("check", rid)

attempt = int(state.get("attempt", 0)) + 1
passed = bool(check.get("passed"))
failures = check.get("failures", [])
check_state = "passed" if passed else ("fix" if attempt < 2 else "stop")
failures_md = "\n".join(f"- {f.get('check')}: {f.get('detail')}" for f in failures) or "- none"

if passed:
    note = f"{app_id}: rationale {rid} passed the check on attempt {attempt} with {len(check.get('cites', []))} cited records."
elif check_state == "fix":
    note = f"{app_id}: rationale {rid} failed the check on attempt {attempt}; one fix pass follows."
else:
    note = (f"NOT FILED: {app_id} rationale {rid} failed the check twice. Failures: "
            + "; ".join(f"{f.get('check')}: {f.get('detail')}" for f in failures)
            + ". A human must fix the write-up (every figure cited and present in the systems, the outcome stated first, "
              "no personal characteristics), resubmit it with `loan rationale submit`, pass `loan check`, then `loan record` it.")

write({"rationale_id": rid, "rationale": text, "passed": passed, "failures": failures, "failures_md": failures_md,
       "cites": check.get("cites", []), "attempt": attempt, "check_state": check_state, "note": note})
