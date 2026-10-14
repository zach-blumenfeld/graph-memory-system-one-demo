#!/usr/bin/env python3
"""File the decision with `loan record` and log the judgment calls with `loan decide`.

stdin:  currentState with rationale_id, outcome, confidence, application_id, passed (true)
stdout: decision_id, skill_revision, judgments_logged, note

SOP rule 5: nothing is filed until it has passed the check and the decision is recorded with its
confidence and the procedure revision that produced it. The revision is this skill's
`metadata.version`, plus the published revision hash when the server runs it from its cache.
SOP "Judgment calls": the typed answers (risk tier, connected exposure, outcome) and the precedent
ruling are logged with `loan decide` so the log holds even though the decisions were typed.
"""
from loanlib import decide, loan, read_state, skill_revision, write

state = read_state()
app_id = str(state["application_id"])
if not state.get("passed"):
    raise SystemExit("the rationale has not passed the check; record refuses to file it")

revision = skill_revision()
rec = loan("record", str(state["rationale_id"]), "--outcome", str(state["outcome"]),
           "--confidence", str(float(state["confidence"])), "--revision", revision)
decision_id = rec["decision_id"]

judgment = state.get("judgment", {})
source = judgment.get("source", "hard rules")
fired = ", ".join(f["rule"] for f in state.get("fired", [])) or "none"
logged = 0

if "risk_tier" in state:
    decide(f"{app_id}: what risk tier is the business?", ["low", "medium", "high"], str(state["risk_tier"]),
           f"Decision model (assess step) on the figures, fired rules ({fired}), ownership summary, tenure, KYC status and the "
           f"relationship manager's notes about the business. Filed as {decision_id}.")
    logged += 1
if "connected_exposure_material" in state:
    decide(f"{app_id}: is the connected exposure material to this decision?", ["material", "not material"],
           "material" if state["connected_exposure_material"] else "not material",
           f"Decision model (assess step): connected exposure {state.get('figures', {}).get('exposure_connected')}, worst connected late days "
           f"{state.get('figures', {}).get('connected_worst_late_days')}. {state.get('ownership_summary', {}).get('text', '')}")
    logged += 1
decide(f"{app_id}: outcome?", ["approve", "counter", "decline"], str(state["outcome"]),
       (f"Hard rules decided: policy {state.get('policy_outcome')}, fired {fired}; no judgment was open." if source == "hard rules"
        else f"Decision model (assess step) after policy review on {fired}; confidence {state.get('confidence')} is the threshold cleared.")
       + f" Filed as {decision_id}, revision {revision}.")
logged += 1
if state.get("precedents_note"):
    keys = [p["key"] for p in state.get("precedents", [])]
    decide(f"{app_id}: do the precedents apply?", ["apply and followed", "apply and departed from", "none exist"] + keys,
           "see why", str(state["precedents_note"]))
    logged += 1

note = (f"{app_id}: decision {decision_id} filed as {state['outcome']} with confidence {state['confidence']} under revision {revision}; "
        f"rationale {state['rationale_id']} passed the check; {logged} judgment call(s) logged; policy {state.get('policy_outcome')}, fired {fired}.")
write({"decision_id": decision_id, "skill_revision": revision, "judgments_logged": logged, "note": note})
