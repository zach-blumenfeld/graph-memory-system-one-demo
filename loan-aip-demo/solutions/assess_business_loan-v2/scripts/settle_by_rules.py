#!/usr/bin/env python3
"""The outcome the hard rules decided, and a note saying why. No judgment was needed.

stdin:  {"state": {"band": "auto_approve" | "auto_decline" | "human", "policy_check": {...}}}
stdout: {"outcome": "approve" | "decline" | "refer", "decision_note": "..."}
Touches nothing outside stdin and stdout.
"""
import json
import sys

OUTCOME = {"auto_approve": "approve", "auto_decline": "decline", "human": "refer"}

payload = json.load(sys.stdin)
state = payload["state"]
band = state["band"] if isinstance(state["band"], str) else state["band"]["value"]
check = state["policy_check"]
fired = check["fired"]
names = ", ".join(f"{f['rule']} ({f['name']}: {f['value']} against {f['threshold']})" for f in fired) or "no rule"
if band == "auto_approve":
    note = f"No hard rule fired: coverage {check['figures']['coverage_ratio']}, total exposure {check['figures']['exposure_total']:,.0f}, KYC {check['figures']['kyc_status']}, tenure {check['figures']['tenure_months']} months. The policy approves without judgment."
elif band == "auto_decline":
    note = f"Automatic decline on {names}. A hard rule decides; no judgment was needed."
else:
    to_human = [f for f in fired if f["effect"] == "human"]
    why = ", ".join(f"{f['rule']} ({f['name']}: {f['value']:,} against {f['threshold']:,})" if isinstance(f["value"], (int, float)) else f"{f['rule']} ({f['name']})" for f in to_human)
    if why:
        note = f"Referred to a person: {why} sends the application to a human whatever the other rules say. Also fired: {names}." if len(to_human) < len(fired) else f"Referred to a person: {why} sends the application to a human. The procedure does not decide it alone."
    else:
        note = f"Referred to a person: the policy declines on {names}, and guidance G1 sends a decline on a customer of this standing to a human before it is filed."
json.dump({"outcome": OUTCOME[band], "decision_note": note}, sys.stdout)
