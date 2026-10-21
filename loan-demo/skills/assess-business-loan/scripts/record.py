#!/usr/bin/env python3
"""Log the judgment calls with `loan decide`, then file the decision with `loan record` when it may be filed.

stdin:  application_id, outcome, confidence, needs_human, rationale_id, check_state, policy_outcome, fired,
        guidance, figures, risk_tier, connected_exposure_material, assessed_outcome, precedents,
        precedents_ruling, precedents_note
stdout: decision_id ("" when nothing was filed), filed_rationale_id, skill_revision, judgments_logged, note

SOP rule 5: nothing is filed until it has passed the check and the decision is recorded with its
confidence and the procedure revision that produced it. The revision is this skill's `metadata.version`
on a local run and the published revision hash when `aip` runs it from its cache.
SOP "Judgment calls": the typed answers (risk tier, connected exposure, outcome) and the precedent ruling
are logged with `loan decide`, one question per call, whether or not the decision is filed.
Not filed: a decline on a customer of five years or more (G1, needs_human) waits for a human, as does any
fired rule with effect `human` (R7, revision 2); a rationale that failed the check twice waits for a human to fix it.
"""
from loanlib import decide, loan, read_handoff, read_state, skill_revision, write

state = read_state()
app_id = str(state["application_id"])
outcome = str(state["outcome"])
confidence = float(state["confidence"])
needs_human = bool(state["needs_human"])
revision = skill_revision()

# --- which rationale, and did it pass? The first check's keys are in the state; a recheck's are in the handoff.
rationale_id = str(state["rationale_id"])
passed = state["check_state"] == "passed"
failures = []
if not passed:
    latest = read_handoff(app_id)
    if latest and latest.get("application_id") == app_id and int(latest.get("attempt", 0)) >= 2:
        rationale_id = str(latest["rationale_id"])
        passed = bool(latest.get("passed"))
        failures = latest.get("failures", [])
    elif latest and latest.get("rationale_id") == rationale_id:
        failures = latest.get("failures", [])
    else:
        raise SystemExit(f"the first check of {rationale_id} did not pass and no recheck result was found for {app_id}; "
                         "the fix and recheck steps must run before record")

# --- the judgment log, one question per call
fired = state.get("fired", [])
fired_txt = ", ".join(f["rule"] for f in fired) or "none"
fig = state.get("figures", {})
basis = (f"figures (coverage {fig.get('coverage_ratio')}, avg net 12m {fig.get('avg_net_12m')}, total payments {fig.get('total_monthly_payments')}, "
         f"exposure {fig.get('exposure_total')} of which connected {fig.get('exposure_connected')}, connected worst late days "
         f"{fig.get('connected_worst_late_days')}, tenure {fig.get('tenure_years')} years, KYC {fig.get('kyc_status')}), fired rules ({fired_txt}), "
         "the ownership summary and the relationship manager's notes about the business")
logged = 0

decide(f"{app_id}: what risk tier is the business?", ["low", "medium", "high"], str(state["risk_tier"]),
       f"Decision model (assess step) on the {basis}.")
logged += 1
decide(f"{app_id}: is the connected exposure material to this decision?", ["material", "not material"],
       "material" if state["connected_exposure_material"] else "not material",
       f"Decision model (assess step): connected exposure {fig.get('exposure_connected')}, worst connected late days "
       f"{fig.get('connected_worst_late_days')}, judged on the {basis}.")
logged += 1
if state["policy_outcome"] == "review":
    why = (f"Policy said review on {fired_txt}; the decision model (assess step) judged the outcome on the {basis}. "
           f"Confidence {confidence} is the threshold it cleared.")
else:
    why = (f"Hard rules decided: policy {state['policy_outcome']} on {fired_txt}; a hard rule is not argued with. "
           f"The assessment's own reading was {state['assessed_outcome']}.")
decide(f"{app_id}: what is the outcome?", ["approve", "counter", "decline"], outcome, why)
logged += 1
keys = [str(p.get("key")) for p in state.get("precedents", [])]
decide(f"{app_id}: do the filed precedents in this product and band apply?",
       ["followed", "departed", "none"], str(state["precedents_ruling"]),
       (str(state["precedents_note"]) + (f" Precedents on file: {', '.join(keys)}." if keys else " None on file.")).strip())
logged += 1

# --- file, or say why not
g1 = next((g for g in state.get("guidance", []) if g.get("rule") == "G1"), None)
how_to_file = (f"loan record {rationale_id} --outcome {outcome} --confidence {confidence} --revision {revision}")
if needs_human:
    decision_id = ""
    tenure = g1.get("value") if g1 else fig.get("tenure_years")
    note = (f"NOT FILED: {app_id} is a decline ({'hard rules' if state['policy_outcome'] != 'review' else 'assessed'}; fired: {fired_txt}) "
            f"on a customer of {tenure} years, at or over the five-year guidance line (G1), so a human reviews it before anything is filed. "
            f"The rationale {rationale_id} {'passed' if passed else 'did not pass'} the check. The human must read the figures, the fired "
            f"rules and the rationale, decide approve, counter or decline, then file: `{how_to_file}` if they agree, or submit their own "
            f"rationale with `loan rationale submit`, pass `loan check`, and `loan record` it. {logged} judgment call(s) were logged.")
    human_rules = [f for f in state.get("fired", []) if f.get("effect") == "human"]
    if human_rules:
        rules_txt = "; ".join(f"{f['rule']} {f.get('name')} (value {f.get('value')}, threshold {f.get('threshold')})" for f in human_rules)
        note = (f"NOT FILED: {app_id} fired a rule the policy says is never decided by the procedure alone: {rules_txt}. "
                f"The rationale {rationale_id} {'passed' if passed else 'did not pass'} the check. A human must read the figures, the fired "
                f"rules and the rationale, decide approve, counter or decline, then file: `{how_to_file}` if they agree, or submit their own.")
elif not passed:
    decision_id = ""
    note = (f"NOT FILED: {app_id} rationale {rationale_id} failed the check twice. Failures: "
            + ("; ".join(f"{f.get('check')}: {f.get('detail')}" for f in failures) or "unknown")
            + ". A human must fix the write-up (every figure cited and present in the systems, the outcome stated first, no personal "
              f"characteristics), resubmit it with `loan rationale submit --application {app_id} --outcome {outcome}`, pass `loan check`, "
              f"then `loan record <id> --outcome {outcome} --confidence {confidence} --revision {revision}`. {logged} judgment call(s) were logged.")
else:
    rec = loan("record", rationale_id, "--outcome", outcome, "--confidence", str(confidence), "--revision", revision)
    decision_id = str(rec["decision_id"])
    note = (f"{app_id}: decision {decision_id} filed as {outcome} with confidence {confidence} under revision {revision}; rationale "
            f"{rationale_id} passed the check citing {len(rec.get('cites', []))} record(s); {logged} judgment call(s) logged; "
            f"policy {state['policy_outcome']}, fired {fired_txt}.")

write({"decision_id": decision_id, "filed_rationale_id": rationale_id if decision_id else "", "skill_revision": revision,
       "judgments_logged": logged, "note": note})
