#!/usr/bin/env python3
"""Look up precedents, settle the outcome for the automatic bands, set confidence and needs_human, and
build the evidence digest the rationale is written from.

stdin:  currentState after hard-rules (auto bands) or after assess (review band: risk_tier,
        connected_exposure_material, outcome present)
stdout: precedents, policy_band, outcome, confidence, judgment, needs_human, decision_id (""), note,
        evidence_md, cite_keys

Rules carried here (policy "How the outcome is formed", G1; SOP "Before you start" on precedents):
- auto_approve -> approve, auto_decline -> decline; a decision-step outcome is kept as is.
- confidence 1.0 when the hard rules decided; otherwise 0.6, the `outcome` threshold the decision model
  cleared (the state carries collapsed answers, not probabilities).
- needs_human: a decline on a customer of five years or more (G1 in `guidance`) goes to a human before
  it is filed; and, since revision 2, any fired rule whose effect is "human" (R7, connected exposure over
  $250,000) does too, whatever the judgment said. The run then ends unfiled with a note for the human.
"""
from loanlib import collect_cites, loan, read_state, write

state = read_state()
app_id = str(state["application_id"])
band = state["policy_outcome"]

pre = loan("precedents", app_id)
# Keep what the traces compared: outcome, rules, confidence, revision. The excerpt of a prior rationale
# is dropped: it can carry names (freeform rationales did) and the judgment is already in `rules`.
precedents = [{k: p.get(k) for k in ("key", "application", "business", "outcome", "confidence", "skill_revision", "at", "rules")}
              for p in pre.get("precedents", [])]

# --- outcome and confidence
if band == "auto_approve":
    outcome, confidence, source = "approve", 1.0, "hard rules"
elif band == "auto_decline":
    outcome, confidence, source = "decline", 1.0, "hard rules"
else:
    outcome = state.get("outcome")
    if outcome not in ("approve", "counter", "decline"):
        raise SystemExit(f"policy said review but the state holds no outcome from the assess step (got {outcome!r})")
    confidence, source = 0.6, "decision model"

judgment = {
    "source": source,
    "risk_tier": state.get("risk_tier", "not asked: the hard rules decided"),
    "connected_exposure_material": state.get("connected_exposure_material", "not asked: the hard rules decided"),
    "outcome": outcome,
}

# --- G1: a decline on a long-standing customer goes to a human before filing
g1 = next((g for g in state.get("guidance", []) if g.get("rule") == "G1"), None)
# --- revision 2: a hard rule whose effect is "human" (R7, connected exposure over the cap) always goes
#     to a person, whatever the judgment said
human_rules = [f for f in state.get("fired", []) if f.get("effect") == "human"]
needs_human = (outcome == "decline" and g1 is not None) or bool(human_rules)

fig = state.get("figures", {})
fired = state.get("fired", [])
fired_txt = ", ".join(f"{f['rule']} {f.get('name')} ({f.get('value')} vs {f.get('threshold')})" for f in fired) or "none"
if human_rules:
    rules_txt = "; ".join(f"{f['rule']} {f.get('name')} ({f.get('value')} vs {f.get('threshold')})" for f in human_rules)
    note = (f"NOT FILED: {app_id} goes to a human because {rules_txt} fired - the policy says connected exposure over the cap is "
            f"never decided by the procedure alone. The assessment so far: outcome {outcome} ({source}), fired {fired_txt}. A human must "
            f"read the figures and the fired rules in this run, decide approve, counter or decline, then file by hand with a rationale that "
            f"cites the records.")
elif needs_human:
    note = (f"NOT FILED: {app_id} is a decline ({'hard rules' if source == 'hard rules' else 'assessed'}; fired: {fired_txt}) on a "
            f"customer of {g1.get('value')} years, at or over the {g1.get('threshold')}-year guidance line (G1). A human must review "
            f"the decline before anything is filed: read the figures and fired rules in this run, decide approve, counter or decline, "
            f"then rerun or file by hand with a rationale that cites the records.")
else:
    note = f"{app_id}: policy {band}, outcome {outcome} ({source}), confidence {confidence}; fired: {fired_txt}. Rationale not yet written."

# --- the evidence digest: every figure with the keys it came from, for the rationale template
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
    f"- KYC status {fig.get('kyc_status')}, last review {kyc.get('kyc', {}).get('last_review')}, beneficial owners verified "
    f"{kyc.get('kyc', {}).get('beneficial_owners_verified')}{cite(cites.get('kyc', []))}",
    f"- Fraud events: " + ("; ".join(f"{e.get('key')} on {e.get('date')} ({e.get('months_ago')} months ago): {e.get('kind')}" for e in kyc.get("fraud_events", [])) or "none")
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
    f"- Accounts: " + ("; ".join(f"{a['key']} {a['type']} balance {a['balance']} opened {a['opened']}" for a in cf.get("accounts", [])) or "none"),
    f"- Last 12 months ({cf.get('last_12m', {}).get('from')} to {cf.get('last_12m', {}).get('to')}): avg inflow {cf.get('last_12m', {}).get('avg_inflow')}, "
    f"avg outflow {cf.get('last_12m', {}).get('avg_outflow')}, avg net {cf.get('last_12m', {}).get('avg_net')}{cite(cf.get('cites', []))}",
    f"- Last 24 months: avg inflow {cf.get('last_24m', {}).get('avg_inflow')}, avg outflow {cf.get('last_24m', {}).get('avg_outflow')}, "
    f"avg net {cf.get('last_24m', {}).get('avg_net')}",
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
    f"- Source: {source}; risk tier: {judgment['risk_tier']}; connected exposure material: {judgment['connected_exposure_material']}; "
    f"outcome: {outcome}; confidence {confidence}",
]

cite_keys = sorted(set(collect_cites(state, precedents)) | {p["key"] for p in precedents})

write({
    "precedents": precedents,
    "policy_band": pre.get("policy_band", band),
    "outcome": outcome,
    "confidence": confidence,
    "judgment": judgment,
    "needs_human": bool(needs_human),
    "decision_id": "",
    "note": note,
    "evidence_md": "\n".join(lines),
    "cite_keys": cite_keys,
})
