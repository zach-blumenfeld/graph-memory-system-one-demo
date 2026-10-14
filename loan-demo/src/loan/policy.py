"""The lending policy as code, shared by the agent's tools (graph-backed), `loan verify fixture`
(JSON-backed) and the tests.

Two halves:
  figures(repo, application_id) -> every number a write-up may quote, each with the node keys it
                                   was computed from ("cites"), read through a small Repo interface
  evaluate(figures, rules)       -> {outcome, fired, guidance} by applying R1-R6, G1 and (once it exists) R7

A Repo is whatever can answer the nine questions below: `loan.fixture.FixtureRepo` reads the JSON
files, `loan.tools.GraphRepo` reads the memory graph.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Protocol

AS_OF = date(2026, 10, 13)  # the demo's "today"; the fixture is generated against it

# Words a rationale (and the state the judgment step sees) must not carry.
PROTECTED_WORDS = re.compile(
    r"\b(dob|date of birth|born|years old|aged|age|sex|gender|ethnicit\w*|ethnic|race|racial|religio\w*|"
    r"national origin|nationality|marital|married|divorced|disabilit\w*|disabled|pregnan\w*)\b", re.I)


class Repo(Protocol):
    def application(self, application_id: str) -> dict[str, Any]: ...
    def business(self, business_id: str) -> dict[str, Any]: ...
    def accounts(self, business_id: str) -> list[dict[str, Any]]: ...
    def cashflow(self, account_id: str) -> list[dict[str, Any]]: ...
    def facilities(self, business_id: str) -> list[dict[str, Any]]: ...
    def payments(self, facility_id: str) -> list[dict[str, Any]]: ...
    def kyc(self, business_id: str) -> dict[str, Any] | None: ...
    def fraud_events(self, business_id: str) -> list[dict[str, Any]]: ...
    def owners(self, business_id: str) -> list[dict[str, Any]]: ...          # [{person_id, name, pct, since}]
    def holdings(self, person_id: str) -> list[dict[str, Any]]: ...          # [{business_id, name, pct, since}]
    def rules(self) -> list[dict[str, Any]]: ...


# ------------------------------------------------------------------ arithmetic
def monthly_payment(principal: float, annual_rate: float, term_months: int) -> float:
    r = annual_rate / 12
    if r == 0:
        return principal / term_months
    return round(principal * r / (1 - (1 + r) ** -term_months), 2)


def months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month) - (1 if b.day < a.day else 0)


def _d(s: str | date) -> date:
    return s if isinstance(s, date) else date.fromisoformat(str(s)[:10])


def late_days(payments: list[dict[str, Any]], as_of: date = AS_OF) -> tuple[int, list[str]]:
    """Days since the oldest unpaid (missed) payment fell due, and the keys of the missed payments."""
    missed = sorted((p for p in payments if p.get("status") == "missed" and not p.get("paid_on")), key=lambda p: str(p["due"]))
    if not missed:
        return 0, []
    return (as_of - _d(missed[0]["due"])).days, [p["id"] for p in missed]


# ------------------------------------------------------------------ figures
def _facility_view(repo: Repo, f: dict[str, Any], as_of: date) -> dict[str, Any]:
    pays = repo.payments(f["id"]) if f.get("status") == "open" else []
    days, missed = late_days(pays, as_of)
    worst = "missed" if missed else ("late" if any(p.get("status") == "late" for p in pays) else "current")
    return {"key": f["id"], "product": f.get("product"), "principal": f.get("principal"), "rate": f.get("rate"),
            "opened": str(f.get("opened")), "status": f.get("status"), "term_months": f.get("term_months"),
            "monthly_payment": f.get("monthly_payment") or (monthly_payment(f["principal"], f["rate"], f["term_months"]) if f.get("term_months") else 0),
            "late_days": days, "worst_payment_status": worst, "missed_payment_keys": missed, "payments": len(pays)}


def ownership_view(repo: Repo, business_id: str, as_of: date = AS_OF, min_pct: float = 25.0) -> dict[str, Any]:
    """Owners of a business, and every other business each owner holds >= min_pct of, with those
    businesses' open facilities and payment status. Two hops. Names and percentages only."""
    owners = []
    for o in repo.owners(business_id):
        other = []
        for h in repo.holdings(o["person_id"]):
            if h["business_id"] == business_id or float(h["pct"]) < min_pct:
                continue
            facs = [_facility_view(repo, f, as_of) for f in repo.facilities(h["business_id"]) if f.get("status") == "open"]
            other.append({"business": {"key": h["business_id"], "name": h.get("name")}, "pct": h["pct"], "since": str(h.get("since")),
                          "facilities": facs, "worst_late_days": max([f["late_days"] for f in facs], default=0)})
        owners.append({"person": {"key": o["person_id"], "name": o.get("name")}, "pct": o["pct"], "since": str(o.get("since")), "other_businesses": other})
    return {"business": business_id, "owners": owners, "min_pct": min_pct}


def cashflow_view(repo: Repo, business_id: str, as_of: date = AS_OF) -> dict[str, Any]:
    accounts = repo.accounts(business_id)
    rows: list[dict[str, Any]] = []
    for a in accounts:
        for m in repo.cashflow(a["id"]):
            rows.append({**m, "account_id": a["id"]})
    months = sorted({r["month"] for r in rows})
    last12, last24 = months[-12:], months[-24:]

    def avg(ms: list[str]) -> dict[str, float]:
        sel = [r for r in rows if r["month"] in ms]
        n = max(len(ms), 1)
        inflow = sum(float(r["inflow"]) for r in sel) / n
        outflow = sum(float(r["outflow"]) for r in sel) / n
        return {"months": len(ms), "avg_inflow": round(inflow, 2), "avg_outflow": round(outflow, 2), "avg_net": round(inflow - outflow, 2)}

    return {"business": business_id, "accounts": [{"key": a["id"], "type": a.get("type"), "balance": a.get("balance"), "opened": str(a.get("opened"))} for a in accounts],
            "last_12m": {**avg(last12), "from": last12[0] if last12 else None, "to": last12[-1] if last12 else None},
            "last_24m": {**avg(last24), "from": last24[0] if last24 else None, "to": last24[-1] if last24 else None},
            "cites": sorted({r["id"] for r in rows if r["month"] in last12})}


def figures(repo: Repo, application_id: str, as_of: date = AS_OF) -> dict[str, Any]:
    app = repo.application(application_id)
    biz = repo.business(app["business_id"])
    proposed_payment = monthly_payment(float(app["amount"]), float(app["rate"]), int(app["term_months"]))
    own = [_facility_view(repo, f, as_of) for f in repo.facilities(biz["id"])]
    own_open = [f for f in own if f["status"] == "open"]
    cf = cashflow_view(repo, biz["id"], as_of)
    kyc = repo.kyc(biz["id"]) or {}
    fraud = []
    for e in repo.fraud_events(biz["id"]):
        fraud.append({"key": e["id"], "date": str(e["date"]), "kind": e.get("kind"), "months_ago": round((as_of - _d(e["date"])).days / 30.44, 1)})
    own_view = ownership_view(repo, biz["id"], as_of)
    connected = []
    for o in own_view["owners"]:
        for ob in o["other_businesses"]:
            connected.append({"owner": o["person"]["name"], "owner_pct_of_applicant": o["pct"], "business": ob["business"], "pct": ob["pct"],
                              "facilities": ob["facilities"], "worst_late_days": ob["worst_late_days"]})
    existing_payments = round(sum(f["monthly_payment"] for f in own_open), 2)
    denominator = round(proposed_payment + existing_payments, 2)
    coverage = round(cf["last_12m"]["avg_net"] / denominator, 2) if denominator else None
    own_exposure = sum(float(f["principal"]) for f in own_open)
    connected_exposure = sum(float(f["principal"]) for c in connected for f in c["facilities"])
    tenure_months = months_between(_d(biz["customer_since"]), as_of)
    return {
        "as_of": as_of.isoformat(),
        "application": {"key": app["id"], "business": biz["id"], "product": app.get("product"), "amount": app["amount"], "term_months": app["term_months"],
                        "rate": app["rate"], "purpose": app.get("purpose"), "submitted": str(app.get("submitted")), "proposed_monthly_payment": proposed_payment},
        "business": {"key": biz["id"], "name": biz.get("legal_name") or biz.get("name"), "industry": biz.get("industry"), "customer_since": str(biz["customer_since"]),
                     "tenure_months": tenure_months, "tenure_years": round(tenure_months / 12, 1)},
        "kyc": {"key": kyc.get("id"), "status": kyc.get("status"), "last_review": str(kyc.get("last_review")), "beneficial_owners_verified": kyc.get("beneficial_owners_verified")},
        "fraud_events": fraud,
        "cashflow": {"avg_net_12m": cf["last_12m"]["avg_net"], "avg_inflow_12m": cf["last_12m"]["avg_inflow"], "avg_outflow_12m": cf["last_12m"]["avg_outflow"],
                     "avg_net_24m": cf["last_24m"]["avg_net"], "window_12m": [cf["last_12m"]["from"], cf["last_12m"]["to"]], "cites": cf["cites"]},
        "own_facilities": own,
        "connected": connected,
        "coverage": {"ratio": coverage, "avg_net_12m": cf["last_12m"]["avg_net"], "proposed_monthly_payment": proposed_payment,
                     "existing_monthly_payments": existing_payments, "total_monthly_payments": denominator,
                     "cites": cf["cites"] + [f["key"] for f in own_open] + [app["id"]]},
        "exposure": {"own": own_exposure, "connected": connected_exposure, "proposed": float(app["amount"]), "total": own_exposure + connected_exposure + float(app["amount"]),
                     "cites": [f["key"] for f in own_open] + [f["key"] for c in connected for f in c["facilities"]] + [app["id"]]},
        "connected_delinquency": {"worst_late_days": max([c["worst_late_days"] for c in connected], default=0),
                                  "cites": [f["key"] for c in connected for f in c["facilities"] if f["late_days"] >= 60]
                                  + [k for c in connected for f in c["facilities"] if f["late_days"] >= 60 for k in f["missed_payment_keys"]]},
    }


# ------------------------------------------------------------------ the rules
def evaluate(fig: dict[str, Any], rules: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Apply R1-R6 and G1 to the figures. Returns outcome, the rules that fired (with value, threshold,
    effect and cites) and the guidance rules that apply."""
    by_id = {r["id"]: r for r in (rules or [])}

    def rule(rid: str) -> dict[str, Any]:
        return by_id.get(rid, {"id": rid, "name": rid, "kind": "hard"})

    fired: list[dict[str, Any]] = []
    guidance: list[dict[str, Any]] = []

    # R1 KYC
    kyc_status = fig["kyc"].get("status")
    if kyc_status == "overdue":
        fired.append({"rule": "R1", "name": rule("R1").get("name"), "value": kyc_status, "threshold": "current", "effect": "auto_decline", "cites": [fig["kyc"]["key"]]})
    elif kyc_status == "refresh_due":
        fired.append({"rule": "R1", "name": rule("R1").get("name"), "value": kyc_status, "threshold": "current", "effect": "review", "cites": [fig["kyc"]["key"]]})
    # R2 fraud in 12 months
    recent = [e for e in fig["fraud_events"] if e["months_ago"] <= 12]
    if recent:
        fired.append({"rule": "R2", "name": rule("R2").get("name"), "value": f"{recent[0]['months_ago']} months ago", "threshold": "12 months", "effect": "auto_decline", "cites": [e["key"] for e in recent]})
    # R3 coverage
    cov = fig["coverage"]["ratio"]
    if cov is not None:
        if cov < 1.0:
            fired.append({"rule": "R3", "name": rule("R3").get("name"), "value": cov, "threshold": 1.25, "effect": "auto_decline", "cites": fig["coverage"]["cites"]})
        elif cov < 1.25:
            fired.append({"rule": "R3", "name": rule("R3").get("name"), "value": cov, "threshold": 1.25, "effect": "review", "cites": fig["coverage"]["cites"]})
    # R4 exposure cap
    if fig["exposure"]["total"] > 1_500_000:
        fired.append({"rule": "R4", "name": rule("R4").get("name"), "value": fig["exposure"]["total"], "threshold": 1_500_000, "effect": "review", "cites": fig["exposure"]["cites"]})
    # R5 connected delinquency
    if fig["connected_delinquency"]["worst_late_days"] >= 60:
        fired.append({"rule": "R5", "name": rule("R5").get("name"), "value": fig["connected_delinquency"]["worst_late_days"], "threshold": 60, "effect": "review",
                      "cites": fig["connected_delinquency"]["cites"]})
    # R6 tenure
    if fig["business"]["tenure_months"] < 24:
        fired.append({"rule": "R6", "name": rule("R6").get("name"), "value": fig["business"]["tenure_months"], "threshold": 24, "effect": "review", "cites": [fig["business"]["key"]]})
    # R7 connected exposure cap: only once the compliance system holds the rule (step 7 adds it); effect "human"
    if "R7" in by_id:
        cap = float(by_id["R7"].get("threshold") or 250_000)
        if fig["exposure"]["connected"] > cap:
            fired.append({"rule": "R7", "name": rule("R7").get("name"), "value": fig["exposure"]["connected"], "threshold": cap, "effect": "human",
                          "cites": [f["key"] for c in fig["connected"] for f in c["facilities"]]})
    # G1 guidance
    if fig["business"]["tenure_months"] >= 60:
        guidance.append({"rule": "G1", "name": rule("G1").get("name"), "value": fig["business"]["tenure_years"], "threshold": 5,
                         "effect": "a decline goes to a human before filing", "cites": [fig["business"]["key"]]})

    if any(f["effect"] == "auto_decline" for f in fired):
        outcome = "auto_decline"
    elif any(f["effect"] in ("review", "human") for f in fired):
        outcome = "review"  # a "human" effect still needs the judgment first; the procedure routes it to a person after
    else:
        outcome = "auto_approve"
    return {"application": fig["application"]["key"], "outcome": outcome, "fired": fired, "guidance": guidance,
            "figures": {"coverage_ratio": cov, "avg_net_12m": fig["coverage"]["avg_net_12m"], "proposed_monthly_payment": fig["coverage"]["proposed_monthly_payment"],
                        "existing_monthly_payments": fig["coverage"]["existing_monthly_payments"], "total_monthly_payments": fig["coverage"]["total_monthly_payments"],
                        "exposure_total": fig["exposure"]["total"], "exposure_own": fig["exposure"]["own"], "exposure_connected": fig["exposure"]["connected"],
                        "connected_worst_late_days": fig["connected_delinquency"]["worst_late_days"], "tenure_months": fig["business"]["tenure_months"],
                        "tenure_years": fig["business"]["tenure_years"], "kyc_status": kyc_status, "amount": float(fig["application"]["amount"]),
                        "term_months": fig["application"]["term_months"]},
            "cites": {"coverage": fig["coverage"]["cites"], "exposure": fig["exposure"]["cites"], "connected_delinquency": fig["connected_delinquency"]["cites"],
                      "kyc": [fig["kyc"]["key"]] if fig["kyc"].get("key") else [], "fraud": [e["key"] for e in fig["fraud_events"]], "business": [fig["business"]["key"]]}}
