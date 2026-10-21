#!/usr/bin/env python3
"""Look up precedents, settle the outcome, set confidence and needs_human, and build the evidence
digest the rationale is written from.

stdin:  state after assess: application_id, policy_outcome, fired, guidance, figures, cites, policy_as_of,
        application, ownership_summary, facilities, cashflow, kyc, crm_notes, crm_notes_dropped,
        risk_tier, connected_exposure_material, assessed_outcome
stdout: precedents, policy_band, outcome, confidence, judgment, needs_human, evidence_md, cite_keys

Rules carried here (policy "How the outcome is formed", G1; SOP "Before you start" on precedents):
- auto_approve -> approve, auto_decline -> decline: the hard rules decide and are not argued with.
  review -> the decision step's `assessed_outcome` is kept as is.
- confidence 1.0 when the hard rules decided; otherwise 0.6, the `assessed_outcome` threshold the
  decision model cleared (the state carries collapsed answers, not probabilities).
- needs_human: a decline on a customer of five years or more (G1 in `guidance`), or any fired rule with
  effect `human` (R7 from revision 2), goes to a human before it is filed. `record` then leaves the decision unfiled and says what the human must do.
"""
from loanlib import collect_cites, loan, read_state, write

state = read_state()
app_id = str(state["application_id"])
band = state["policy_outcome"]

pre = loan("precedents", app_id)
# Keep what the traces compared: outcome, rules, confidence, revision. The excerpt of a prior rationale
# is dropped: a freeform rationale can carry names, and the judgment is already in `rules`.
precedents = [{k: p.get(k) for k in ("key", "application", "business", "outcome", "confidence", "skill_revision", "at", "rules")}
              for p in pre.get("precedents", [])]

# --- outcome and confidence
assessed = state.get("assessed_outcome")
if assessed not in ("approve", "counter", "decline"):
    raise SystemExit(f"the assess step left no outcome in the state (got {assessed!r})")
if band == "auto_approve":
    outcome, confidence, source = "approve", 1.0, "hard rules"
elif band == "auto_decline":
    outcome, confidence, source = "decline", 1.0, "hard rules"
else:
    outcome, confidence, source = assessed, 0.6, "decision model"

judgment = {
    "source": source,
    "risk_tier": state.get("risk_tier"),
    "connected_exposure_material": bool(state.get("connected_exposure_material")),
    "assessed_outcome": assessed,
    "outcome": outcome,
    "assessment_agrees_with_policy": assessed == outcome,
}

# --- G1: a decline on a long-standing customer goes to a human before filing
g1 = next((g for g in state.get("guidance", []) if g.get("rule") == "G1"), None)
needs_human = outcome == "decline" and g1 is not None
# --- revision 2: a fired rule with effect "human" (R7, the connected exposure cap) always goes to a human before filing
human_rules = [f for f in state.get("fired", []) if f.get("effect") == "human"]
needs_human = needs_human or bool(human_rules)

# --- the evidence digest: every figure with the keys it came from, for the rationale template
fig = state.get("figures", {})
fired = state.get("fired", [])
fired_txt = ", ".join(f"{f['rule']} {f.get('name')} ({f.get('value')} vs {f.get('threshold')})" for f in fired) or "none"
app = state.get("application", {}).get("application", {})
biz = state.get("application", {}).get("business", {})
cites = state.get("cites", {})
own = state.get("ownership_summary", {})
cf = state.get("cashflow", {})
kyc = state.get("kyc", {})


def j(keys):
    return ", ".join(keys) if keys else "none"


def cite(keys):
    """A cite marker for the keys, or nothing when there are none (a `[cite: none]` would fail the check)."""
    return f" [cite: {', '.join(keys)}]" if keys else ""


lines = [
    f"### Application [cite: {app.get('key')}]",
    f"- {biz.get('legal_name') or biz.get('name')} ({biz.get('key')}), {biz.get('industry')}; customer since {biz.get('customer_since')}, "
    f"tenure {fig.get('tenure_years')} years ({fig.get('tenure_months')} months) [cite: {biz.get('key')}]",
    f"- Product {app.get('product')}, amount {app.get('amount')}, term {app.get('term_months')} months, proposed monthly payment "
    f"{app.get('proposed_monthly_payment')}, submitted {app.get('submitted')} [cite: {app.get('key')}]",
    f"- Purpose: {app.get('purpose')} [cite: {app.get('key')}]",
    "",
    f"### Policy: {band} (as of {state.get('policy_as_of')})",
    f"- Fired rules: {fired_txt}",
]
for f in fired:
    lines.append(f"  - {f['rule']} {f.get('name')}: value {f.get('value')}, threshold {f.get('threshold')}, effect {f.get('effect')}{cite(f.get('cites', []))}")
for g in state.get("guidance", []):
    lines.append(f"- Guidance {g['rule']} {g.get('name')}: value {g.get('value')}, threshold {g.get('threshold')}; {g.get('effect')}{cite(g.get('cites', []))}")
lines += [
    f"- Coverage ratio {fig.get('coverage_ratio')} = twelve-month average monthly net inflow {fig.get('avg_net_12m')} / total monthly payments "
    f"{fig.get('total_monthly_payments')} (proposed {fig.get('proposed_monthly_payment')} + existing {fig.get('existing_monthly_payments')}); "
    f"floor 1.25, review band 1.00 to 1.25{cite(cites.get('coverage', []))}",
    f"- Exposure total {fig.get('exposure_total')} = own open facilities {fig.get('exposure_own')} + connected {fig.get('exposure_connected')} + "
    f"amount {fig.get('amount')}; cap 1500000{cite(cites.get('exposure', []))}",
    f"- Connected worst late days {fig.get('connected_worst_late_days')}; review at 60 or more{cite(cites.get('connected_delinquency', []))}",
    f"- KYC status {fig.get('kyc_status')}, last review {(kyc.get('kyc') or {}).get('last_review')}, beneficial owners verified "
    f"{(kyc.get('kyc') or {}).get('beneficial_owners_verified')}{cite(cites.get('kyc', []))}",
    "- Fraud events: " + ("; ".join(f"{e.get('key')} on {e.get('date')} ({e.get('months_ago')} months ago): {e.get('kind')}" for e in kyc.get("fraud_events", [])) or "none")
    + cite(cites.get("fraud", [])),
    "",
    "### Ownership (two hops out)",
    f"- {own.get('text')}{cite(own.get('cites', []))}",
    "",
    "### Facilities at the business",
]
for f in state.get("facilities", {}).get("facilities", []):
    late = f.get("late_or_missed_payments", [])
    late_txt = "; ".join(f"{p['key']} due {p['due']} paid {p.get('paid_on') or 'not paid'} ({p['status']})" for p in late) or "none"
    record = (f"{f['on_time_count']} of {f['payments_count']} payments on time; late or missed: {late_txt}" if f["payments_count"]
              else "no payment rows on record")
    lines.append(f"- {f['key']} {f['product']}, principal {f['principal']}, monthly payment {f['monthly_payment']}, opened {f['opened']}, "
                 f"{f['status']}, {f['late_days']} days late; {record} [cite: {f['key']}]")
if not state.get("facilities", {}).get("facilities"):
    lines.append("- none")
lines += [
    "",
    "### Cash flow",
    "- Accounts: " + ("; ".join(f"{a['key']} {a['type']} balance {a['balance']} opened {a['opened']}" for a in cf.get("accounts", [])) or "none"),
    f"- Last 12 months ({(cf.get('last_12m') or {}).get('from')} to {(cf.get('last_12m') or {}).get('to')}): avg inflow {(cf.get('last_12m') or {}).get('avg_inflow')}, "
    f"avg outflow {(cf.get('last_12m') or {}).get('avg_outflow')}, avg net {(cf.get('last_12m') or {}).get('avg_net')}{cite(cf.get('cites', []))}",
    f"- Last 24 months: avg inflow {(cf.get('last_24m') or {}).get('avg_inflow')}, avg outflow {(cf.get('last_24m') or {}).get('avg_outflow')}, "
    f"avg net {(cf.get('last_24m') or {}).get('avg_net')}",
    "",
    "### Relationship manager notes about the business (names removed; notes mentioning a personal characteristic withheld)",
]
for n in state.get("crm_notes", []):
    lines.append(f"- {n.get('date')}: {n.get('text')} [cite: {n.get('key')}]")
if not state.get("crm_notes"):
    lines.append("- none usable")
if state.get("crm_notes_dropped"):
    lines.append(f"- {state['crm_notes_dropped']} note(s) withheld because they mention a personal characteristic; do not refer to them.")
lines += [
    "",
    f"### Precedents ({pre.get('product')}, band {pre.get('policy_band')})",
]
for p in precedents:
    lines.append(f"- {p['key']}: {p['outcome']} on {p['application']} ({p['business']}), confidence {p['confidence']}, rules {j(p.get('rules') or [])}, "
                 f"revision {p['skill_revision']} [cite: {p['key']}]")
if not precedents:
    lines.append("- none filed yet in this product and band; this decision becomes the first")
lines += [
    "",
    "### Judgment",
    f"- Settled by: {source}; risk tier: {judgment['risk_tier']}; connected exposure material: {judgment['connected_exposure_material']}; "
    f"outcome: {outcome}; confidence {confidence}",
]
if source == "hard rules":
    lines.append(f"- The assessment's own reading of the outcome was {assessed}; the policy band {band} decides and is not argued with.")
if outcome == "decline" and g1 is not None:
    lines.append(f"- This decline is on a customer of {g1.get('value')} years (G1, at or over {g1.get('threshold')}): it goes to a human before filing. "
                 "Write the rationale the human will review.")
for f in human_rules:
    lines.append(f"- {f['rule']} {f.get('name')} fired (value {f.get('value')}, threshold {f.get('threshold')}): the policy says this is never decided "
                 "by the procedure alone, so it goes to a human before filing. Write the rationale the human will review.")

cite_keys = sorted(set(collect_cites(state.get("application"), state.get("ownership_summary"), state.get("facilities"),
                                     state.get("cashflow"), state.get("kyc"), state.get("crm_notes"), state.get("fired"),
                                     state.get("guidance"), cites, precedents)) | {p["key"] for p in precedents})

write({
    "precedents": precedents,
    "policy_band": str(pre.get("policy_band") or band),
    "outcome": outcome,
    "confidence": float(confidence),
    "judgment": judgment,
    "needs_human": bool(needs_human),
    "evidence_md": "\n".join(lines),
    "cite_keys": cite_keys,
})
