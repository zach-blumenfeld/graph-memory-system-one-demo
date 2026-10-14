#!/usr/bin/env python3
"""Apply the lending policy with `loan policy`: the hard rules R1-R6 and guidance G1.

stdin:  currentState with application_id (str) and ownership_summary (from gather)
stdout: policy_outcome (auto_approve | auto_decline | review), fired, guidance, figures, cites,
        connected (scrubbed), own_facilities, policy_as_of

SOP rule 1: policy first, before forming a view. The policy engine is the bank's; this script only
calls it and removes the one name it returns (`connected[].owner`), replacing it with the owner label
from `ownership_summary`.
"""
from loanlib import loan, read_state, write

state = read_state()
policy = loan("policy", str(state["application_id"]))

outcome = policy.get("outcome")
if outcome not in ("auto_approve", "auto_decline", "review"):
    raise SystemExit(f"loan policy returned an unknown outcome {outcome!r}")

held_by = {c.get("key"): c.get("held_by") for c in state.get("ownership_summary", {}).get("connected_businesses", [])}
connected = []
for c in policy.get("connected", []):
    c = dict(c)
    c["owner"] = held_by.get((c.get("business") or {}).get("key"), "an owner")
    connected.append(c)

write({
    "policy_outcome": outcome,
    "fired": policy.get("fired", []),
    "guidance": policy.get("guidance", []),
    "figures": policy.get("figures", {}),
    "cites": policy.get("cites", {}),
    "connected": connected,
    "own_facilities": policy.get("own_facilities", []),
    "policy_as_of": policy.get("as_of"),
})
