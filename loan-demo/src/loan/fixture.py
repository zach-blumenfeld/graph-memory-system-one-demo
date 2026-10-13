"""Read the five bank systems in data/bank/*.json: `{"system": ..., "as_of": ..., "records": {Type: [...]}}`
with flat records. `Fixture` gives typed access; `FixtureRepo` is the JSON-backed `loan.policy.Repo`
used by `loan verify fixture` and the tests (the agent's tools read the memory graph instead)."""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from loan.env import DATA
from loan.policy import AS_OF, evaluate, figures

FILES = {"core_banking": ["Business", "Account", "MonthlyCashflow"], "loans": ["Facility", "Payment", "Application"],
         "compliance": ["KycRecord", "Rule", "FraudEvent"], "ownership": ["Person", "Ownership"],
         "crm": ["RelationshipManager", "Coverage", "Note"]}


class Fixture:
    """All five systems. `data_dir` lets tests point at a copy."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or DATA
        self._db: dict[str, dict[str, Any]] = {}

    def db(self, name: str) -> dict[str, Any]:
        if name not in self._db:
            self._db[name] = json.loads((self.data_dir / f"{name}.json").read_text())
        return self._db[name]

    def records(self, kind: str) -> list[dict[str, Any]]:
        for file, kinds in FILES.items():
            if kind in kinds:
                return self.db(file)["records"][kind]
        raise KeyError(f"unknown record type {kind!r}")

    def as_of(self) -> date:
        return date.fromisoformat(self.db("loans").get("as_of", AS_OF.isoformat()))

    def one(self, kind: str, key: str, field: str = "id") -> dict[str, Any]:
        for r in self.records(kind):
            if r.get(field) == key:
                return r
        raise KeyError(f"{kind}: no record with {field}={key!r}")

    # ------------------------------------------------------------- typed accessors
    def businesses(self) -> list[dict[str, Any]]:
        return self.records("Business")

    def business(self, business_id: str) -> dict[str, Any]:
        return self.one("Business", business_id)

    def accounts(self, business_id: str | None = None) -> list[dict[str, Any]]:
        return [a for a in self.records("Account") if business_id is None or a["business_id"] == business_id]

    def cashflow(self, account_id: str) -> list[dict[str, Any]]:
        return sorted((m for m in self.records("MonthlyCashflow") if m["account_id"] == account_id), key=lambda m: m["month"])

    def facilities(self, business_id: str | None = None) -> list[dict[str, Any]]:
        return [f for f in self.records("Facility") if business_id is None or f["business_id"] == business_id]

    def payments(self, facility_id: str) -> list[dict[str, Any]]:
        return sorted((p for p in self.records("Payment") if p["facility_id"] == facility_id), key=lambda p: p["due"])

    def applications(self) -> list[dict[str, Any]]:
        return self.records("Application")

    def application(self, application_id: str) -> dict[str, Any]:
        return self.one("Application", application_id)

    def kyc(self, business_id: str) -> dict[str, Any] | None:
        return next((k for k in self.records("KycRecord") if k["business_id"] == business_id), None)

    def rules(self) -> list[dict[str, Any]]:
        return self.records("Rule")

    def fraud_events(self, business_id: str) -> list[dict[str, Any]]:
        return [e for e in self.records("FraudEvent") if e["business_id"] == business_id]

    def people(self) -> list[dict[str, Any]]:
        return self.records("Person")

    def person(self, person_id: str) -> dict[str, Any]:
        return self.one("Person", person_id)

    def ownership(self) -> list[dict[str, Any]]:
        return self.records("Ownership")

    def owners(self, business_id: str) -> list[dict[str, Any]]:
        return [{"person_id": o["person_id"], "name": self.person(o["person_id"])["name"], "pct": o["pct"], "since": o["since"]}
                for o in self.ownership() if o["business_id"] == business_id]

    def holdings(self, person_id: str) -> list[dict[str, Any]]:
        return [{"business_id": o["business_id"], "name": self.business(o["business_id"])["dba"], "pct": o["pct"], "since": o["since"]}
                for o in self.ownership() if o["person_id"] == person_id]

    def rms(self) -> list[dict[str, Any]]:
        return self.records("RelationshipManager")

    def coverage(self) -> list[dict[str, Any]]:
        return self.records("Coverage")

    def notes(self, business_id: str | None = None) -> list[dict[str, Any]]:
        return [n for n in self.records("Note") if business_id is None or n["business_id"] == business_id]


class FixtureRepo:
    """`loan.policy.Repo` over the JSON files."""

    def __init__(self, fx: Fixture | None = None) -> None:
        self.fx = fx or Fixture()

    def application(self, application_id: str): return self.fx.application(application_id)
    def business(self, business_id: str): return self.fx.business(business_id)
    def accounts(self, business_id: str): return self.fx.accounts(business_id)
    def cashflow(self, account_id: str): return self.fx.cashflow(account_id)
    def facilities(self, business_id: str): return self.fx.facilities(business_id)
    def payments(self, facility_id: str): return self.fx.payments(facility_id)
    def kyc(self, business_id: str): return self.fx.kyc(business_id)
    def fraud_events(self, business_id: str): return self.fx.fraud_events(business_id)
    def owners(self, business_id: str): return self.fx.owners(business_id)
    def holdings(self, person_id: str): return self.fx.holdings(person_id)
    def rules(self): return self.fx.rules()


@lru_cache(maxsize=1)
def default_fixture() -> Fixture:
    return Fixture()


# The five facts of PLAN step 1, checked against the JSON with the shared policy engine.
# With R7 in the compliance system (added in step 7): connected exposure over $250K fires for APP-1001
# (Alder Logistics, $300K) and APP-1005 (Wrenfield Mechanical, $950K). Before step 7 those two were
# ["R5"] review and [] auto_approve, which is what the recordings and the revision-1 runs saw.
EXPECTED = {
    "APP-1001": {"outcome": "review", "fired": ["R5", "R7"], "coverage": 1.60},
    "APP-1002": {"outcome": "auto_approve", "fired": [], "coverage": 1.90},
    "APP-1003": {"outcome": "auto_decline", "fired": ["R1", "R2"], "coverage": 1.30},
    "APP-1004": {"outcome": "review", "fired": ["R3"], "coverage": 1.15},
    "APP-1005": {"outcome": "review", "fired": ["R7"], "coverage": 1.40},
}
COUNTS = {"Business": 7, "Account": 10, "MonthlyCashflow": 240, "Facility": 7, "Application": 5, "KycRecord": 7, "Rule": 8,
          "FraudEvent": 1, "Person": 10, "Ownership": 12, "RelationshipManager": 2, "Coverage": 7, "Note": 9}


def verify_fixture(log=print) -> int:
    fx = Fixture()
    failures: list[str] = []
    for kind, want in COUNTS.items():
        got = len(fx.records(kind))
        if got != want:
            failures.append(f"{kind}: want {want} records, got {got}")
    payments = len(fx.records("Payment"))
    log(f"records: {json.dumps({k: len(fx.records(k)) for k in COUNTS})}, Payment {payments}")
    repo = FixtureRepo(fx)
    for app_id, want in EXPECTED.items():
        fig = figures(repo, app_id, fx.as_of())
        res = evaluate(fig, fx.rules())
        fired = [f["rule"] for f in res["fired"]]
        cov = res["figures"]["coverage_ratio"]
        log(f"{app_id}: outcome={res['outcome']} fired={fired} coverage={cov} exposure={res['figures']['exposure_total']:.0f} "
            f"connected_late_days={res['figures']['connected_worst_late_days']} tenure={res['figures']['tenure_years']}y guidance={[g['rule'] for g in res['guidance']]}")
        if res["outcome"] != want["outcome"]:
            failures.append(f"{app_id}: outcome {res['outcome']}, want {want['outcome']}")
        if fired != want["fired"]:
            failures.append(f"{app_id}: fired {fired}, want {want['fired']}")
        if cov is None or abs(cov - want["coverage"]) > 0.02:
            failures.append(f"{app_id}: coverage {cov}, want about {want['coverage']}")
    # R5 for APP-1001 comes only through the ownership graph: the applicant's own facilities are current.
    fig = figures(repo, "APP-1001", fx.as_of())
    if any(f["late_days"] for f in fig["own_facilities"]):
        failures.append("APP-1001: the applicant's own facilities are late; R5 should fire only through ownership")
    late = [(c["business"]["name"], f["key"], f["late_days"]) for c in fig["connected"] for f in c["facilities"] if f["late_days"] >= 60]
    if late != [("Alder Logistics", "FAC-03", 90)]:
        failures.append(f"APP-1001: connected delinquency {late}, want Alder Logistics FAC-03 at 90 days")
    # APP-1005: the co-held business is current, exposure close to the cap
    fig5 = figures(repo, "APP-1005", fx.as_of())
    if not fig5["connected"] or fig5["connected"][0]["worst_late_days"] != 0:
        failures.append("APP-1005: expected one connected business with current payments")
    if abs(fig5["exposure"]["total"] - 1_400_000) > 1:
        failures.append(f"APP-1005: exposure {fig5['exposure']['total']}, want 1,400,000")
    # dob exists in the ownership system (so the demo can show it is never passed on)
    if not all(p.get("dob") for p in fx.people()):
        failures.append("Person records must carry dob")
    for f in failures:
        log("FAIL " + f)
    log("verify fixture: " + ("OK" if not failures else "FAILED"))
    return 1 if failures else 0
