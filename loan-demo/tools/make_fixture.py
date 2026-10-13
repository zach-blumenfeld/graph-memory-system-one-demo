#!/usr/bin/env python3
"""Invent Lantern Mutual's five systems and write them to data/bank/*.json. Deterministic: fixed
seed, fixed dates, generated against AS_OF = 2026-10-13. Re-running produces identical files.

Run from loan-demo/: `uv run python tools/make_fixture.py`.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from loan.policy import AS_OF, monthly_payment  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "data" / "bank"
rng = random.Random(20261013)


def iso(d: date) -> str:
    return d.isoformat()


def add_months(d: date, n: int) -> date:
    y, m = d.year, d.month + n
    while m > 12:
        y, m = y + 1, m - 12
    while m < 1:
        y, m = y - 1, m + 12
    return date(y, m, min(d.day, 28))


# ------------------------------------------------------------------ the world
BUSINESSES = [
    {"id": "BUS-01", "legal_name": "Harrow Street Bakery Ltd", "dba": "Harrow Street Bakery", "industry": "food retail: bakery and wholesale", "founded": "2016-03-01", "customer_since": "2020-09-14"},
    {"id": "BUS-02", "legal_name": "Ridgeline Dental Partners LLP", "dba": "Ridgeline Dental", "industry": "healthcare: dental practice", "founded": "2015-06-01", "customer_since": "2019-03-01"},
    {"id": "BUS-03", "legal_name": "Corvid Print Co. Ltd", "dba": "Corvid Print", "industry": "commercial printing", "founded": "2018-02-01", "customer_since": "2023-05-01"},
    {"id": "BUS-04", "legal_name": "Mossbank Climbing Gym Ltd", "dba": "Mossbank Climbing", "industry": "leisure: climbing gym", "founded": "2018-09-01", "customer_since": "2019-05-20"},
    {"id": "BUS-05", "legal_name": "Alder Logistics Ltd", "dba": "Alder Logistics", "industry": "road freight", "founded": "2019-04-01", "customer_since": "2022-03-01"},
    {"id": "BUS-06", "legal_name": "Pell & Daughters Plumbing Ltd", "dba": "Pell & Daughters", "industry": "building services: plumbing", "founded": "2011-05-01", "customer_since": "2023-07-01"},
    {"id": "BUS-07", "legal_name": "Wrenfield Mechanical Ltd", "dba": "Wrenfield Mechanical", "industry": "building services: heating and ventilation", "founded": "2012-01-01", "customer_since": "2021-09-01"},
]

ACCOUNTS = [
    {"id": "ACC-101", "business_id": "BUS-01", "type": "operating", "opened": "2020-09-14", "balance": 86400.00},
    {"id": "ACC-102", "business_id": "BUS-01", "type": "savings", "opened": "2021-02-01", "balance": 150000.00},
    {"id": "ACC-201", "business_id": "BUS-02", "type": "operating", "opened": "2019-03-01", "balance": 212000.00},
    {"id": "ACC-202", "business_id": "BUS-02", "type": "savings", "opened": "2019-03-01", "balance": 310000.00},
    {"id": "ACC-301", "business_id": "BUS-03", "type": "operating", "opened": "2023-05-01", "balance": 9800.00},
    {"id": "ACC-401", "business_id": "BUS-04", "type": "operating", "opened": "2019-05-20", "balance": 142000.00},
    {"id": "ACC-402", "business_id": "BUS-04", "type": "savings", "opened": "2020-01-15", "balance": 95000.00},
    {"id": "ACC-501", "business_id": "BUS-05", "type": "operating", "opened": "2022-03-01", "balance": 4100.00},
    {"id": "ACC-601", "business_id": "BUS-06", "type": "operating", "opened": "2023-07-01", "balance": 61000.00},
    {"id": "ACC-701", "business_id": "BUS-07", "type": "operating", "opened": "2021-09-01", "balance": 388000.00},
]

# Facilities: payments fall due on the 15th, monthly, from the month after opening. 24 months of
# payment history at most. `missed` lists due dates never paid; `late` maps due date -> paid date.
FACILITIES = [
    {"id": "FAC-01", "business_id": "BUS-01", "product": "equipment loan", "principal": 120000, "rate": 0.0725, "term_months": 60, "opened": "2023-03-15", "status": "open"},
    {"id": "FAC-02", "business_id": "BUS-04", "product": "term loan", "principal": 200000, "rate": 0.075, "term_months": 84, "opened": "2022-06-15", "status": "open",
     "late": {"2025-08-15": "2025-08-22"}},
    {"id": "FAC-03", "business_id": "BUS-05", "product": "term loan", "principal": 300000, "rate": 0.08, "term_months": 60, "opened": "2024-02-15", "status": "open",
     "late": {"2026-06-15": "2026-06-25"}, "missed": ["2026-07-15", "2026-08-15", "2026-09-15"]},
    {"id": "FAC-04", "business_id": "BUS-06", "product": "equipment loan", "principal": 250000, "rate": 0.0775, "term_months": 60, "opened": "2024-01-15", "status": "open"},
    {"id": "FAC-05", "business_id": "BUS-07", "product": "term loan", "principal": 950000, "rate": 0.07, "term_months": 120, "opened": "2023-09-15", "status": "open"},
    {"id": "FAC-06", "business_id": "BUS-03", "product": "term loan", "principal": 60000, "rate": 0.095, "term_months": 48, "opened": "2024-05-15", "status": "open"},
    {"id": "FAC-07", "business_id": "BUS-01", "product": "term loan", "principal": 50000, "rate": 0.069, "term_months": 36, "opened": "2021-01-15", "status": "closed"},
]

APPLICATIONS = [
    {"id": "APP-1001", "business_id": "BUS-01", "product": "term loan", "amount": 400000, "term_months": 84, "rate": 0.085,
     "purpose": "Second location: fit-out and ovens for a second bakery on Lantern Row, with a wholesale kitchen at the back.", "submitted": "2026-10-06", "requested_by": "Priya Raghunathan"},
    {"id": "APP-1002", "business_id": "BUS-02", "product": "equipment loan", "amount": 250000, "term_months": 60, "rate": 0.079,
     "purpose": "Equipment: two digital imaging units and a sterilisation suite for the third chair.", "submitted": "2026-10-02", "requested_by": "Anneliese Okafor"},
    {"id": "APP-1003", "business_id": "BUS-03", "product": "working capital line", "amount": 150000, "term_months": 36, "rate": 0.095,
     "purpose": "Working capital: paper stock and payroll through the seasonal trough.", "submitted": "2026-10-05", "requested_by": "Declan Hurst"},
    {"id": "APP-1004", "business_id": "BUS-04", "product": "term loan", "amount": 600000, "term_months": 120, "rate": 0.085,
     "purpose": "Fit-out of a second gym in the Mossbank Mill lease: walls, matting, changing rooms.", "submitted": "2026-10-07", "requested_by": "Ingrid Vossberg"},
    {"id": "APP-1005", "business_id": "BUS-06", "product": "vehicle loan", "amount": 200000, "term_months": 60, "rate": 0.075,
     "purpose": "Vehicles: three fitted service vans for the new county maintenance contract.", "submitted": "2026-10-09", "requested_by": "Maureen Pell"},
]

RULES = [
    {"id": "R1", "name": "kyc_current", "kind": "hard", "field": "kyc_status", "threshold": "current",
     "text": "KYC status must be current. Overdue is an automatic decline. Refresh due goes to review."},
    {"id": "R2", "name": "no_fraud_12m", "kind": "hard", "field": "months_since_fraud_event", "threshold": 12,
     "text": "A fraud event on the business in the last 12 months is an automatic decline."},
    {"id": "R3", "name": "coverage_floor", "kind": "hard", "field": "coverage_ratio", "threshold": 1.25, "secondary_threshold": 1.0,
     "text": "Debt service coverage is the 12-month average monthly net inflow divided by the proposed monthly payment plus the payments on existing facilities. 1.25 or more can be approved without judgment. From 1.00 up to 1.25 goes to review. Below 1.00 is an automatic decline."},
    {"id": "R4", "name": "exposure_cap", "kind": "hard", "field": "total_exposure", "threshold": 1500000,
     "text": "Total exposure to the business, plus every business its owners hold 25% or more of, including the proposed amount, must stay at or under $1,500,000. Over the cap goes to review."},
    {"id": "R5", "name": "connected_delinquency", "kind": "hard", "field": "connected_worst_late_days", "threshold": 60,
     "text": "Any facility 60 or more days late at a business an owner holds 25% or more of goes to review. Never an automatic approval."},
    {"id": "R6", "name": "tenure", "kind": "hard", "field": "tenure_months", "threshold": 24,
     "text": "A customer of fewer than 24 months goes to review."},
    {"id": "G1", "name": "long_customer_decline", "kind": "guidance", "field": "tenure_years", "threshold": 5,
     "text": "A decline on a customer of five years or more goes to a human before it is filed."},
    # Added 2026-10-13 by the compliance officer (the step-7 edit beat): connected exposure over $250,000 always goes to a human.
    {"id": "R7", "name": "connected_exposure_cap", "kind": "hard", "field": "connected_exposure", "threshold": 250000,
     "text": "Connected exposure, the principal of every open facility at businesses an owner of the applicant holds 25% or more of, over $250,000 always goes to a human. It is never decided by the procedure alone."},
]

KYC = [
    {"id": "KYC-BUS-01", "business_id": "BUS-01", "status": "current", "last_review": "2026-03-14", "beneficial_owners_verified": True},
    {"id": "KYC-BUS-02", "business_id": "BUS-02", "status": "current", "last_review": "2026-05-20", "beneficial_owners_verified": True},
    {"id": "KYC-BUS-03", "business_id": "BUS-03", "status": "overdue", "last_review": "2024-07-02", "beneficial_owners_verified": False},
    {"id": "KYC-BUS-04", "business_id": "BUS-04", "status": "current", "last_review": "2026-01-22", "beneficial_owners_verified": True},
    {"id": "KYC-BUS-05", "business_id": "BUS-05", "status": "current", "last_review": "2025-11-30", "beneficial_owners_verified": True},
    {"id": "KYC-BUS-06", "business_id": "BUS-06", "status": "current", "last_review": "2026-08-11", "beneficial_owners_verified": True},
    {"id": "KYC-BUS-07", "business_id": "BUS-07", "status": "refresh_due", "last_review": "2024-10-01", "beneficial_owners_verified": True},
]

FRAUD_EVENTS = [
    {"id": "FRD-01", "business_id": "BUS-03", "date": "2026-06-10", "kind": "counterfeit cheque deposits; operating account blocked by the fraud team"},
]

PEOPLE = [
    {"id": "PER-01", "name": "Priya Raghunathan", "dob": "1968-04-12", "role": "owner-director"},
    {"id": "PER-02", "name": "Tom Alder", "dob": "1975-09-03", "role": "owner-director"},
    {"id": "PER-03", "name": "Anneliese Okafor", "dob": "1980-02-27", "role": "partner"},
    {"id": "PER-04", "name": "Marcus Tiller", "dob": "1977-11-15", "role": "partner"},
    {"id": "PER-05", "name": "Declan Hurst", "dob": "1985-06-30", "role": "owner-director"},
    {"id": "PER-06", "name": "Ingrid Vossberg", "dob": "1983-01-19", "role": "owner-director"},
    {"id": "PER-07", "name": "Ben Achterberg", "dob": "1990-08-08", "role": "owner"},
    {"id": "PER-08", "name": "Ilse Brandvold", "dob": "1971-12-02", "role": "owner"},
    {"id": "PER-09", "name": "Maureen Pell", "dob": "1966-03-25", "role": "owner-director"},
    {"id": "PER-10", "name": "Gavin Wrenfield", "dob": "1979-07-07", "role": "owner-director"},
]

OWNERSHIP = [
    {"person_id": "PER-01", "business_id": "BUS-01", "pct": 55, "since": "2016-03-01"},
    {"person_id": "PER-02", "business_id": "BUS-01", "pct": 45, "since": "2016-03-01"},
    {"person_id": "PER-03", "business_id": "BUS-02", "pct": 50, "since": "2015-06-01"},
    {"person_id": "PER-04", "business_id": "BUS-02", "pct": 50, "since": "2015-06-01"},
    {"person_id": "PER-05", "business_id": "BUS-03", "pct": 100, "since": "2018-02-01"},
    {"person_id": "PER-06", "business_id": "BUS-04", "pct": 70, "since": "2018-09-01"},
    {"person_id": "PER-07", "business_id": "BUS-04", "pct": 30, "since": "2020-01-01"},
    {"person_id": "PER-02", "business_id": "BUS-05", "pct": 60, "since": "2019-04-01"},
    {"person_id": "PER-08", "business_id": "BUS-05", "pct": 40, "since": "2019-04-01"},
    {"person_id": "PER-09", "business_id": "BUS-06", "pct": 100, "since": "2011-05-01"},
    {"person_id": "PER-10", "business_id": "BUS-07", "pct": 70, "since": "2012-01-01"},
    {"person_id": "PER-09", "business_id": "BUS-07", "pct": 30, "since": "2019-06-01"},
]

RMS = [{"id": "RM-01", "name": "Dana Whitlock"}, {"id": "RM-02", "name": "Omar Farsi"}]
COVERAGE = [
    {"rm_id": "RM-01", "business_id": "BUS-01", "since": "2021-01-01"},
    {"rm_id": "RM-01", "business_id": "BUS-04", "since": "2021-01-01"},
    {"rm_id": "RM-01", "business_id": "BUS-05", "since": "2022-03-01"},
    {"rm_id": "RM-02", "business_id": "BUS-02", "since": "2019-03-01"},
    {"rm_id": "RM-02", "business_id": "BUS-03", "since": "2023-05-01"},
    {"rm_id": "RM-02", "business_id": "BUS-06", "since": "2023-07-01"},
    {"rm_id": "RM-02", "business_id": "BUS-07", "since": "2021-09-01"},
]
NOTES = [
    {"id": "NOTE-01", "business_id": "BUS-01", "date": "2026-09-18", "text": "Site visit to Harrow Street. The second location on Lantern Row has signed heads of terms; Priya wants to open before the spring. Tom will run the second site day to day. Wholesale now a third of sales."},
    {"id": "NOTE-02", "business_id": "BUS-01", "date": "2026-04-02", "text": "Annual review. Priya (58) is thinking about succession in five years; Tom would take over. Strong wholesale pipeline with three cafes signed this quarter."},
    {"id": "NOTE-03", "business_id": "BUS-02", "date": "2026-08-30", "text": "The practice added a third chair in July; the waiting list is six weeks. Equipment quotes attached to the application."},
    {"id": "NOTE-04", "business_id": "BUS-03", "date": "2026-07-01", "text": "The fraud team placed a block on the operating account in June after counterfeit cheque deposits. KYC refresh requested twice; no response from the director."},
    {"id": "NOTE-05", "business_id": "BUS-04", "date": "2026-09-25", "text": "Mossbank Mill lease signed 2026-09-20, ten years with a break at five. Founder memberships pre-sold: 412 at the visit, target 600 before opening. Original gym at capacity on weekday evenings."},
    {"id": "NOTE-06", "business_id": "BUS-04", "date": "2025-11-05", "text": "Membership growth steady through the year. One payment on the fit-out loan went in a week late in August while the card terminal was replaced; nothing since."},
    {"id": "NOTE-07", "business_id": "BUS-05", "date": "2026-08-20", "text": "Alder Logistics missed the July and August payments. Tom Alder says two large customers are paying late. Collections engaged; no arrangement agreed yet."},
    {"id": "NOTE-08", "business_id": "BUS-06", "date": "2026-09-30", "text": "Maureen Pell wants three fitted vans for the new county maintenance contract; the current fleet is two vans at end of life. Contract runs three years."},
    {"id": "NOTE-09", "business_id": "BUS-07", "date": "2026-06-15", "text": "Wrenfield Mechanical on plan; Maureen Pell holds a minority stake and sits on the board. KYC refresh scheduled for Q4."},
]

# Cash flow: a target 12-month-average coverage ratio per business (against its open facilities and
# its application, if any), a margin (net / inflow), and a seasonal shape. The generator scales the
# nets so the trailing-12 average hits the target exactly.
TARGET_COVERAGE = {"BUS-01": 1.60, "BUS-02": 1.90, "BUS-03": 1.30, "BUS-04": 1.15, "BUS-05": 0.70, "BUS-06": 1.40, "BUS-07": 2.20}
MARGIN = {"BUS-01": 0.12, "BUS-02": 0.09, "BUS-03": 0.08, "BUS-04": 0.20, "BUS-05": 0.05, "BUS-06": 0.15, "BUS-07": 0.14}
SEASON = {  # multiplier by calendar month (Jan..Dec)
    "BUS-01": [0.85, 0.9, 1.0, 1.05, 1.05, 1.0, 0.95, 0.9, 1.0, 1.05, 1.1, 1.15],
    "BUS-02": [1.0, 1.0, 1.05, 1.0, 1.0, 0.95, 0.9, 0.9, 1.05, 1.05, 1.05, 1.05],
    "BUS-03": [0.8, 0.85, 1.0, 1.05, 1.1, 1.1, 1.0, 0.9, 1.1, 1.15, 1.1, 0.85],
    "BUS-04": [1.2, 1.1, 1.0, 0.95, 0.9, 0.85, 0.85, 0.9, 1.1, 1.1, 1.05, 1.0],
    "BUS-05": [0.95, 0.95, 1.0, 1.0, 1.05, 1.05, 1.0, 0.95, 1.0, 1.05, 1.1, 0.9],
    "BUS-06": [1.05, 1.1, 1.0, 0.95, 0.95, 0.95, 0.95, 1.0, 1.0, 1.05, 1.0, 1.0],
    "BUS-07": [1.1, 1.1, 1.0, 0.95, 0.9, 0.9, 1.0, 1.0, 1.0, 1.05, 1.05, 0.95],
}
SAVINGS_RATE = 0.03


def month_list(n: int = 24) -> list[str]:
    last = date(AS_OF.year, AS_OF.month, 1) - timedelta(days=1)  # last full month
    first = add_months(date(last.year, last.month, 1), -(n - 1))
    return [f"{add_months(first, i).year}-{add_months(first, i).month:02d}" for i in range(n)]


def payments_for(f: dict) -> list[dict]:
    rows = []
    opened = date.fromisoformat(f["opened"])
    amt = monthly_payment(f["principal"], f["rate"], f["term_months"])
    i = 1
    while True:
        due = add_months(opened, i)
        due = date(due.year, due.month, 15)
        if due > AS_OF:
            break
        if due > AS_OF - timedelta(days=24 * 30.5):  # 24 months of history
            k = due.isoformat()
            if k in f.get("missed", []):
                rows.append({"id": f"PAY-{f['id'][4:]}-{k[:7]}", "facility_id": f["id"], "due": k, "paid_on": None, "amount": amt, "status": "missed"})
            elif k in f.get("late", {}):
                rows.append({"id": f"PAY-{f['id'][4:]}-{k[:7]}", "facility_id": f["id"], "due": k, "paid_on": f["late"][k], "amount": amt, "status": "late"})
            else:
                rows.append({"id": f"PAY-{f['id'][4:]}-{k[:7]}", "facility_id": f["id"], "due": k, "paid_on": k, "amount": amt, "status": "current"})
        i += 1
    return rows


def cashflow_rows() -> list[dict]:
    months = month_list(24)
    rows: list[dict] = []
    for b in BUSINESSES:
        bid = b["id"]
        own_pay = sum(monthly_payment(f["principal"], f["rate"], f["term_months"]) for f in FACILITIES if f["business_id"] == bid and f["status"] == "open")
        app = next((a for a in APPLICATIONS if a["business_id"] == bid), None)
        proposed = monthly_payment(app["amount"], app["rate"], app["term_months"]) if app else 0.0
        target_net = TARGET_COVERAGE[bid] * (own_pay + proposed) if (own_pay + proposed) else 9000.0
        accts = [a for a in ACCOUNTS if a["business_id"] == bid]
        savings = [a for a in accts if a["type"] == "savings"]
        savings_net = sum(round(a["balance"] * SAVINGS_RATE / 12, 2) for a in savings)
        op_target = target_net - savings_net
        # shape: season x noise, growth from the earlier year to the later one
        shape = []
        for i, m in enumerate(months):
            cal = int(m[5:7]) - 1
            noise = 1 + rng.uniform(-0.08, 0.08)
            growth = 0.9 if i < 12 else 1.0
            shape.append(SEASON[bid][cal] * noise * growth)
        last12 = shape[12:]
        scale = op_target * 12 / sum(last12)
        nets = [round(s * scale, 2) for s in shape]
        # make the trailing-12 average exact after rounding
        diff = round(op_target * 12 - sum(nets[12:]), 2)
        nets[-1] = round(nets[-1] + diff, 2)
        op = next(a for a in accts if a["type"] == "operating")
        for m, net in zip(months, nets):
            inflow = round(net / MARGIN[bid], 2)
            rows.append({"id": f"MON-{op['id'][4:]}-{m}", "account_id": op["id"], "month": m, "inflow": inflow, "outflow": round(inflow - net, 2)})
        for a in savings:
            interest = round(a["balance"] * SAVINGS_RATE / 12, 2)
            for m in months:
                rows.append({"id": f"MON-{a['id'][4:]}-{m}", "account_id": a["id"], "month": m, "inflow": interest, "outflow": 0.0})
    return rows


def write(name: str, system: str, records: dict[str, list]) -> None:
    doc = {"system": system, "as_of": iso(AS_OF), "records": records}
    (OUT / f"{name}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"{name}.json: " + ", ".join(f"{k} {len(v)}" for k, v in records.items()))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    facilities = [{k: v for k, v in f.items() if k not in ("late", "missed")} | {"monthly_payment": monthly_payment(f["principal"], f["rate"], f["term_months"])} for f in FACILITIES]
    payments = [p for f in FACILITIES if f["status"] == "open" for p in payments_for(f)]
    applications = [a | {"monthly_payment": monthly_payment(a["amount"], a["rate"], a["term_months"])} for a in APPLICATIONS]
    write("core_banking", "Core banking", {"Business": BUSINESSES, "Account": ACCOUNTS, "MonthlyCashflow": cashflow_rows()})
    write("loans", "Loan and credit", {"Facility": facilities, "Payment": payments, "Application": applications})
    write("compliance", "Compliance", {"KycRecord": KYC, "Rule": RULES, "FraudEvent": FRAUD_EVENTS})
    write("ownership", "Ownership", {"Person": PEOPLE, "Ownership": OWNERSHIP})
    write("crm", "CRM", {"RelationshipManager": RMS, "Coverage": COVERAGE, "Note": NOTES})


if __name__ == "__main__":
    main()
