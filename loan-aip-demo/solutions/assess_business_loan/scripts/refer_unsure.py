#!/usr/bin/env python3
"""The decision model was not sure enough of its outcome: the application goes to a person.

stdin:  {"state": {"judgment": {...}, "policy_check": {...}}}
stdout: {"outcome": "refer", "decision_note": "..."}
Touches nothing outside stdin and stdout.
"""
import json
import sys

payload = json.load(sys.stdin)
state = payload["state"]
j = state["judgment"]
check = state["policy_check"]
fired = ", ".join(f"{f['rule']} ({f['name']}: {f['value']} against {f['threshold']})" for f in check["fired"]) or "no rule"
note = (f"The policy left this to judgment ({fired} sends it to review). The decision model leaned {j['outcome']['value']} but with confidence "
        f"{j['outcome'].get('confidence', 0):.2f}, below the 0.6 the procedure requires (probabilities {json.dumps(j['outcome'].get('probabilities', {}))}); "
        f"it put the risk tier at {j['risk_tier']['value']}. As the SOP says, when not sure, refer: a person decides.")
json.dump({"outcome": "refer", "decision_note": note}, sys.stdout)
