#!/usr/bin/env python3
"""Pull the five things the policy needs and strip what the judgment step must never see.

stdin:  currentState with application_id (str)
stdout: application (scrubbed), business_id, ownership_summary, facilities, cashflow, kyc,
        tenure_years, kyc_status, crm_notes (filtered, names redacted), crm_notes_dropped, as_of

SOP "Before you start": the application, the business, cash flow, facilities, KYC and fraud, the owners
and everything else they hold. SOP rule 2: look two hops out, every run; it is code here.
SOP rule 4: dates of birth and people's names never enter the state; a CRM note that mentions a
personal characteristic is dropped before the judgment step.
"""
from concurrent.futures import ThreadPoolExecutor

from loanlib import collect_cites, filter_notes, loan, person_labels, read_state, scrub, write

state = read_state()
app_id = str(state["application_id"]).strip()
if not app_id:
    raise SystemExit("application_id is empty")

application = loan("application", app_id)
business_id = application["business"]["key"]

# The four business views are independent of each other: fetch them together.
with ThreadPoolExecutor(max_workers=4) as pool:
    f_own = pool.submit(loan, "ownership", business_id)
    f_fac = pool.submit(loan, "facilities", business_id)
    f_cf = pool.submit(loan, "cashflow", business_id)
    f_kyc = pool.submit(loan, "kyc", business_id)
    ownership, facilities, cashflow, kyc = f_own.result(), f_fac.result(), f_cf.result(), f_kyc.result()

labels = person_labels(application, ownership)

# --- ownership two hops out: owners as shares, other businesses by name, their facilities and days late
owners = []
connected = []
for i, o in enumerate(ownership.get("owners", []), start=1):
    label = f"owner {i}"
    others = []
    for ob in o.get("other_businesses", []):
        biz = ob.get("business", {})
        facs = [{k: f.get(k) for k in ("key", "product", "principal", "status", "monthly_payment", "late_days",
                                        "worst_payment_status", "missed_payment_keys")} for f in ob.get("facilities", [])]
        entry = {"key": biz.get("key"), "name": biz.get("name"), "pct": ob.get("pct"), "since": ob.get("since"),
                 "worst_late_days": ob.get("worst_late_days", 0), "facilities": facs}
        others.append(entry)
        connected.append({**entry, "held_by": f"{label} ({o.get('pct')}%)"})
    owners.append({"owner": label, "person_key": (o.get("person") or {}).get("key"), "pct": o.get("pct"),
                   "since": o.get("since"), "other_businesses": others})

connected_exposure = sum(float(f.get("principal") or 0) for c in connected for f in c["facilities"] if f.get("status") == "open")
connected_worst = max([int(c.get("worst_late_days") or 0) for c in connected], default=0)
parts = [f"{len(owners)} owner(s): " + ", ".join(f"{o['owner']} holds {o['pct']}%" for o in owners) + "."]
for c in connected:
    if c["facilities"]:
        fac_txt = "; ".join(f"{f['key']} {f['product']} principal {f['principal']} {f['status']}, {f['late_days']} days late"
                            + (f", missed {len(f['missed_payment_keys'])} payment(s)" if f.get("missed_payment_keys") else "")
                            for f in c["facilities"])
        parts.append(f"{c['held_by']} also holds {c['pct']}% of {c['name']} ({c['key']}): {fac_txt}.")
    else:
        parts.append(f"{c['held_by']} also holds {c['pct']}% of {c['name']} ({c['key']}): no facilities with us.")
if not connected:
    parts.append("No owner holds 25% or more of another business: no connected exposure.")
ownership_summary = {"business": business_id, "owners": owners, "connected_businesses": connected,
                     "connected_exposure": connected_exposure, "connected_worst_late_days": connected_worst,
                     "min_pct": ownership.get("min_pct", 25.0), "text": " ".join(parts), "cites": ownership.get("cites", [])}

# --- facilities: every figure keeps its key; the 24 payment rows collapse to counts plus the late ones
fac_view = []
for f in facilities.get("facilities", []):
    pays = f.get("payments", [])
    late = [{k: p.get(k) for k in ("key", "due", "paid_on", "amount", "status")} for p in pays if p.get("status") != "current"]
    fac_view.append({**{k: f.get(k) for k in ("key", "product", "principal", "rate", "term_months", "monthly_payment",
                                                "opened", "status", "late_days", "missed_payment_keys")},
                     "payments_count": len(pays), "on_time_count": sum(1 for p in pays if p.get("status") == "current"),
                     "late_or_missed_payments": late})
facilities_view = {"business": business_id, "as_of": facilities.get("as_of"), "facilities": fac_view,
                   "existing_monthly_payments": facilities.get("existing_monthly_payments", 0), "cites": facilities.get("cites", [])}

# --- cash flow: the averages and the Month keys they were computed from; the per-month rows stay in the systems
cashflow_view = {k: cashflow.get(k) for k in ("business", "accounts", "last_12m", "last_24m", "cites", "as_of")}

# --- CRM notes: drop any that mention a personal characteristic, redact names in the rest
crm_notes, dropped = filter_notes(application.get("crm_notes", []), labels)

# --- the application view, scrubbed: no requested_by, no owner names, no RM name, notes replaced by the filtered list
app_view = scrub({k: v for k, v in application.items() if k not in ("owners", "crm_notes")}, labels)
app_view["crm_notes"] = crm_notes
app_view["cites"] = [c for c in application.get("cites", []) if not c.startswith("NOTE-") or any(n["key"] == c for n in crm_notes)]

result = {
    "application": app_view,
    "business_id": business_id,
    "ownership_summary": scrub(ownership_summary, labels),
    "facilities": scrub(facilities_view, labels),
    "cashflow": scrub(cashflow_view, labels),
    "kyc": scrub(kyc, labels),
    "tenure_years": float(application["business"].get("tenure_years") or 0.0),
    "kyc_status": str(kyc.get("kyc", {}).get("status", "unknown")),
    "crm_notes": crm_notes,
    "crm_notes_dropped": dropped,
    "as_of": application.get("as_of"),
}
result["gathered_cites"] = collect_cites(result)
write(result)
