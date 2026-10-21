#!/usr/bin/env python3
"""Store the draft with `blast draft`, then run `blast check` on it (SOP "Writing": run the compliance check).

stdin:  state with campaign_id, segment, subjects (3 strings), body (markdown)
stdout: draft_id, check_passed, failures, required_disclaimer
"""
from blastlib import read_state, submit_and_check, write

state = read_state()
draft, check = submit_and_check(state["campaign_id"], state["segment"]["segment_id"], state["subjects"], state["body"], "draft")

write({"draft_id": draft["draft_id"], "check_passed": bool(check["passed"]),
       "failures": check.get("failures", []), "required_disclaimer": check.get("required_disclaimer", "")})
