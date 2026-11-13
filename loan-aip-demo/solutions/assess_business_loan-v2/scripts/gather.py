#!/usr/bin/env python3
"""Gather every figure the lending policy needs for one application from Lantern Mutual's five
systems, held as JSON files under `source/` (core_banking, loans, compliance, ownership, crm).

Reads only those files; touches no network, no credentials and nothing outside the working
directory. `source/` is looked for in the run's working directory, then in its parents.

stdin:  {"state": {"application_id": "APP-1004"}, ...}
stdout: {"figures": {...}, "case_file": "..."}

`figures` is every number the policy tests, each with the record ids it was computed from.
`case_file` is the text the assessment may see: the ownership summary carries names and
percentages only, never a date of birth; an age written into a relationship manager's note is
redacted.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

FILES = {"core_banking": ["Business", "Account", "MonthlyCashflow"], "loans": ["Facility", "Payment", "Application"],
         "compliance": ["KycRecord", "Rule", "FraudEvent"], "ownership": ["Person", "Ownership"],
         "crm": ["RelationshipManager", "Coverage", "Note"]}
MIN_PCT = 25.0                       # an owner's other business counts from this holding


def find_source() -> Path:
    here = Path(os.environ.get("AIP_WORKDIR") or os.getcwd()).resolve()
    for folder in (here, *here.parents):
        if (folder / "source" / "loans.json").exists():
            return folder / "source"
    raise SystemExit(f"no source/ folder with the bank's JSON files under {here} or its parents")


class Systems:
    def __init__(self, source: Path) -> None:
        self.source, self._db = source, {}

    def db(self, name: str) -> dict:
        if name not in self._db:
            self._db[name] = json.loads((self.source / f"{name}.json").read_text(encoding="utf-8"))
        return self._db[name]

    def records(self, kind: str) -> list[dict]:
        for file, kinds in FILES.items():
            if kind in kinds:
                return self.db(file)["records"][kind]
        raise KeyError(kind)

    def one(self, kind: str, key: str) -> dict:
        for r in self.records(kind):
            if r.get("id") == key:
                return r
        raise SystemExit(f"{kind}: no record {key!r} in the {kind} system")

    def as_of(self) -> date:
        return date.fromisoformat(self.db("loans")["as_of"])


def monthly_payment(principal: float, annual_rate: float, term_months: int) -> float:
    r = annual_rate / 12
    return round(principal / term_months, 2) if r == 0 else round(principal * r / (1 - (1 + r) ** -term_months), 2)


def months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month) - (1 if b.day < a.day else 0)


def d(s: str) -> date:
    return date.fromisoformat(str(s)[:10])


def facility_view(sys_: Systems, f: dict, as_of: date) -> dict:
    pays = sorted((p for p in sys_.records("Payment") if p["facility_id"] == f["id"]), key=lambda p: p["due"]) if f.get("status") == "open" else []
    missed = [p for p in pays if p.get("status") == "missed" and not p.get("paid_on")]
    late_days = (as_of - d(missed[0]["due"])).days if missed else 0
    late_once = [p["id"] for p in pays if p.get("status") == "late"]
    payment = f.get("monthly_payment") or (monthly_payment(f["principal"], f["rate"], f["term_months"]) if f.get("term_months") else 0)
    return {"key": f["id"], "product": f.get("product"), "principal": f.get("principal"), "opened": f.get("opened"), "status": f.get("status"),
            "monthly_payment": payment, "late_days": late_days, "missed_payment_keys": [p["id"] for p in missed], "late_payment_keys": late_once,
            "payments_on_record": len(pays)}


def redact(text: str) -> str:
    """An age or a date of birth written into a note is not an input."""
    text = re.sub(r"\s*\(\d{2}\)", " [age redacted]", text)
    return re.sub(r"\b(aged|age|years old|date of birth|born)\b[^.;,]*", "[personal characteristic redacted]", text, flags=re.I)


def main() -> None:
    payload = json.load(sys.stdin)
    application_id = str(payload["state"]["application_id"]).strip()
    s = Systems(find_source())
    as_of = s.as_of()

    app = s.one("Application", application_id)
    biz = s.one("Business", app["business_id"])
    proposed = app.get("monthly_payment") or monthly_payment(float(app["amount"]), float(app["rate"]), int(app["term_months"]))

    own = [facility_view(s, f, as_of) for f in s.records("Facility") if f["business_id"] == biz["id"]]
    own_open = [f for f in own if f["status"] == "open"]

    accounts = [a for a in s.records("Account") if a["business_id"] == biz["id"]]
    rows = [{**m, "account_id": a["id"]} for a in accounts for m in s.records("MonthlyCashflow") if m["account_id"] == a["id"]]
    months = sorted({r["month"] for r in rows})
    last12 = months[-12:]
    sel = [r for r in rows if r["month"] in last12]
    n = max(len(last12), 1)
    avg_in = round(sum(float(r["inflow"]) for r in sel) / n, 2)
    avg_out = round(sum(float(r["outflow"]) for r in sel) / n, 2)
    avg_net = round(avg_in - avg_out, 2)
    cashflow_cites = sorted(r["id"] for r in sel)

    kyc = next((k for k in s.records("KycRecord") if k["business_id"] == biz["id"]), {})
    fraud = [{"key": e["id"], "date": e["date"], "kind": e.get("kind"), "months_ago": round((as_of - d(e["date"])).days / 30.44, 1)}
             for e in s.records("FraudEvent") if e["business_id"] == biz["id"]]

    people = {p["id"]: p for p in s.records("Person")}
    owners, connected = [], []
    for o in (o for o in s.records("Ownership") if o["business_id"] == biz["id"]):
        person = people[o["person_id"]]
        others = []
        for h in (h for h in s.records("Ownership") if h["person_id"] == o["person_id"] and h["business_id"] != biz["id"]):
            if float(h["pct"]) < MIN_PCT:
                continue
            other = s.one("Business", h["business_id"])
            facs = [facility_view(s, f, as_of) for f in s.records("Facility") if f["business_id"] == other["id"] and f.get("status") == "open"]
            entry = {"business": {"key": other["id"], "name": other["dba"]}, "pct": h["pct"], "facilities": facs,
                     "worst_late_days": max([f["late_days"] for f in facs], default=0)}
            others.append(entry)
            connected.append({"owner": person["name"], "owner_pct_of_applicant": o["pct"], **entry})
        owners.append({"person": {"key": person["id"], "name": person["name"]}, "pct": o["pct"], "other_businesses": others})

    existing = round(sum(f["monthly_payment"] for f in own_open), 2)
    total_payments = round(proposed + existing, 2)
    coverage = round(avg_net / total_payments, 2) if total_payments else None
    own_exposure = sum(float(f["principal"]) for f in own_open)
    connected_exposure = sum(float(f["principal"]) for c in connected for f in c["facilities"])
    tenure_months = months_between(d(biz["customer_since"]), as_of)
    worst_connected = max([c["worst_late_days"] for c in connected], default=0)

    notes = [{"key": nt["id"], "date": nt["date"], "text": redact(nt["text"])} for nt in s.records("Note") if nt["business_id"] == biz["id"]]
    cov = {c["business_id"]: c["rm_id"] for c in s.records("Coverage")}
    rms = {r["id"]: r["name"] for r in s.records("RelationshipManager")}

    figures = {
        "as_of": as_of.isoformat(),
        "application": {"key": app["id"], "business": biz["id"], "product": app["product"], "amount": app["amount"], "term_months": app["term_months"],
                        "rate": app["rate"], "purpose": app["purpose"], "submitted": app["submitted"], "proposed_monthly_payment": proposed},
        "business": {"key": biz["id"], "name": biz["legal_name"], "industry": biz["industry"], "customer_since": biz["customer_since"],
                     "tenure_months": tenure_months, "tenure_years": round(tenure_months / 12, 1)},
        "kyc": {"key": kyc.get("id"), "status": kyc.get("status"), "last_review": kyc.get("last_review"),
                "beneficial_owners_verified": kyc.get("beneficial_owners_verified")},
        "fraud_events": fraud,
        "cashflow": {"avg_net_12m": avg_net, "avg_inflow_12m": avg_in, "avg_outflow_12m": avg_out,
                     "window_12m": [last12[0], last12[-1]] if last12 else None, "cites": cashflow_cites},
        "own_facilities": own,
        "connected": connected,
        "coverage": {"ratio": coverage, "avg_net_12m": avg_net, "proposed_monthly_payment": proposed, "existing_monthly_payments": existing,
                     "total_monthly_payments": total_payments, "cites": cashflow_cites + [f["key"] for f in own_open] + [app["id"]]},
        "exposure": {"own": own_exposure, "connected": connected_exposure, "proposed": float(app["amount"]),
                     "total": own_exposure + connected_exposure + float(app["amount"]),
                     "cites": [f["key"] for f in own_open] + [f["key"] for c in connected for f in c["facilities"]] + [app["id"]]},
        "connected_delinquency": {"worst_late_days": worst_connected,
                                  "cites": [f["key"] for c in connected for f in c["facilities"] if f["late_days"] > 0]
                                  + [k for c in connected for f in c["facilities"] for k in f["missed_payment_keys"]]},
    }

    lines = [
        f"Assessment date: {as_of.isoformat()}.",
        f"Application {app['id']}: {biz['legal_name']} [{biz['id']}] asks for a {app['product']} of {app['amount']:,} over {app['term_months']} months "
        f"at {app['rate']:.3%}, proposed monthly payment {proposed:,.2f} [{app['id']}]. Purpose: {app['purpose']} Submitted {app['submitted']}.",
        f"Business: {biz['industry']}; customer since {biz['customer_since']}, tenure {tenure_months} months ({tenure_months / 12:.1f} years) [{biz['id']}]. "
        f"Relationship manager: {rms.get(cov.get(biz['id']), 'none on record')}.",
        f"KYC: status {kyc.get('status')}, last review {kyc.get('last_review')}, beneficial owners verified: {kyc.get('beneficial_owners_verified')} [{kyc.get('id')}].",
        "Fraud events: " + ("; ".join(f"{e['kind']} on {e['date']}, {e['months_ago']} months ago [{e['key']}]" for e in fraud) if fraud else "none on record") + ".",
        f"Cash flow, last 12 months ({last12[0]} to {last12[-1]}): average monthly inflow {avg_in:,.2f}, outflow {avg_out:,.2f}, net {avg_net:,.2f} "
        f"[{', '.join(cashflow_cites)}]. Accounts: " + "; ".join(f"{a['type']} balance {a['balance']:,.2f} [{a['id']}]" for a in accounts) + ".",
        "Own facilities: " + ("; ".join(f"{f['product']} {f['principal']:,} opened {f['opened']}, {f['status']}, payment {f['monthly_payment']:,.2f}, "
                                        f"{f['late_days']} days late, {len(f['missed_payment_keys'])} missed, {len(f['late_payment_keys'])} paid late [{f['key']}]"
                                        for f in own) if own else "none") + ".",
        f"Coverage: net {avg_net:,.2f} / (proposed {proposed:,.2f} + existing {existing:,.2f} = {total_payments:,.2f}) = {coverage}.",
        f"Exposure: own {own_exposure:,.0f} + connected {connected_exposure:,.0f} + proposed {float(app['amount']):,.0f} = {figures['exposure']['total']:,.0f}.",
        "Owners: " + "; ".join(f"{o['person']['name']} {o['pct']}% [{o['person']['key']}]" for o in owners) + ".",
        "Connected businesses (owners' holdings of 25% or more): " + ("; ".join(
            f"{c['owner']} holds {c['pct']}% of {c['business']['name']} [{c['business']['key']}], whose open facilities: "
            + (", ".join(f"{f['product']} {f['principal']:,} at {f['late_days']} days late with {len(f['missed_payment_keys'])} missed payments [{f['key']}]"
                         + (f" (missed: {', '.join(f['missed_payment_keys'])})" if f['missed_payment_keys'] else "") for f in c["facilities"]) or "none")
            for c in connected) if connected else "none") + ".",
        "Relationship manager's notes: " + ("; ".join(f"{nt['date']}: {nt['text']} [{nt['key']}]" for nt in notes) if notes else "none") + ".",
    ]
    json.dump({"figures": figures, "case_file": "\n".join(lines)}, sys.stdout)


if __name__ == "__main__":
    main()
