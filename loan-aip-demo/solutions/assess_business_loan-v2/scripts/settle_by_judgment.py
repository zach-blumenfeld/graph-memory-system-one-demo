#!/usr/bin/env python3
"""The outcome the decision model judged, with its risk tier and confidence, as a note.

stdin:  {"state": {"judgment": {"risk_tier": {...}, "connected_material": {...}, "outcome": {...}}, "policy_check": {...}}}
stdout: {"outcome": "approve" | "decline" | "refer", "decision_note": "..."}
Touches nothing outside stdin and stdout.
"""
import json
import sys

payload = json.load(sys.stdin)
state = payload["state"]
j = state["judgment"]
check = state["policy_check"]
fired = ", ".join(f"{f['rule']} ({f['name']}: {f['value']} against {f['threshold']})" for f in check["fired"]) or "no rule"
outcome = j["outcome"]["value"]
note = (f"The policy left this to judgment ({fired} sends it to review). The decision model judged the outcome {outcome} "
        f"with confidence {j['outcome'].get('confidence', 0):.2f} (probabilities {json.dumps(j['outcome'].get('probabilities', {}))}), "
        f"the risk tier {j['risk_tier']['value']} (confidence {j['risk_tier'].get('confidence', 0):.2f}), and the connected exposure "
        f"{'material' if j['connected_material']['value'] else 'not material'} (confidence {j['connected_material'].get('confidence', 0):.2f}).")
json.dump({"outcome": outcome, "decision_note": note}, sys.stdout)
