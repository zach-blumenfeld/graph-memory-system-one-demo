"""The agent's tools: what `loan <cmd>` does. Plain functions returning JSON-able dicts so the same
logic serves the CLI (the agent in step 4) and the AIP skill's scripts (step 5).

Everything is read from the memory graph with Cypher. `GraphRepo` answers the policy engine's
questions (`loan.policy.Repo`) from the graph; `policy()` is `figures()` + `evaluate()` over it.
Every figure a write-up might quote carries the keys of the nodes it was computed from.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loan.env import RATIONALES_DIR, SOP_FILE, ensure_run_dirs
from loan.memory import cypher
from loan.policy import AS_OF, PROTECTED_WORDS, cashflow_view, evaluate, figures, months_between, ownership_view


class GraphRepo:
    """`loan.policy.Repo` over the memory graph. Owners come back as name and percentage only."""

    def application(self, application_id: str) -> dict[str, Any]:
        rows = cypher("MATCH (a:Application {key: $k}) RETURN a.key AS id, a.business_id AS business_id, a.product AS product, a.amount AS amount, "
                      "a.term_months AS term_months, a.rate AS rate, a.purpose AS purpose, a.submitted AS submitted, a.requested_by AS requested_by, "
                      "a.monthly_payment AS monthly_payment", k=application_id)
        if not rows:
            raise SystemExit(json.dumps({"error": f"unknown application {application_id}"}))
        return rows[0]

    def business(self, business_id: str) -> dict[str, Any]:
        rows = cypher("MATCH (b:Business {key: $k}) RETURN b.key AS id, b.name AS name, b.legal_name AS legal_name, b.dba AS dba, b.industry AS industry, "
                      "b.founded AS founded, b.customer_since AS customer_since", k=business_id)
        if not rows:
            raise SystemExit(json.dumps({"error": f"unknown business {business_id}"}))
        return rows[0]

    def accounts(self, business_id: str) -> list[dict[str, Any]]:
        return cypher("MATCH (:Business {key: $k})-[:HOLDS]->(a:Account) RETURN a.key AS id, a.type AS type, a.opened AS opened, a.balance AS balance ORDER BY a.key", k=business_id)

    def cashflow(self, account_id: str) -> list[dict[str, Any]]:
        return cypher("MATCH (:Account {key: $k})-[:HAS_CASHFLOW]->(m:Month) RETURN m.key AS id, m.month AS month, m.inflow AS inflow, m.outflow AS outflow ORDER BY m.month", k=account_id)

    def facilities(self, business_id: str) -> list[dict[str, Any]]:
        return cypher("MATCH (:Business {key: $k})-[:HAS_FACILITY]->(f:Facility) RETURN f.key AS id, f.product AS product, f.principal AS principal, f.rate AS rate, "
                      "f.term_months AS term_months, f.monthly_payment AS monthly_payment, f.opened AS opened, f.status AS status ORDER BY f.key", k=business_id)

    def payments(self, facility_id: str) -> list[dict[str, Any]]:
        return cypher("MATCH (:Facility {key: $k})-[:HAS_PAYMENT]->(p:Payment) RETURN p.key AS id, p.due AS due, p.paid_on AS paid_on, p.amount AS amount, p.status AS status ORDER BY p.due", k=facility_id)

    def kyc(self, business_id: str) -> dict[str, Any] | None:
        rows = cypher("MATCH (:Business {key: $k})-[:KYC]->(r:KycRecord) RETURN r.key AS id, r.status AS status, r.last_review AS last_review, "
                      "r.beneficial_owners_verified AS beneficial_owners_verified", k=business_id)
        return rows[0] if rows else None

    def fraud_events(self, business_id: str) -> list[dict[str, Any]]:
        return cypher("MATCH (:Business {key: $k})-[:HAD]->(e:FraudEvent) RETURN e.key AS id, e.date AS date, e.kind AS kind ORDER BY e.date", k=business_id)

    def owners(self, business_id: str) -> list[dict[str, Any]]:
        return cypher("MATCH (p:Person)-[o:OWNS]->(:Business {key: $k}) RETURN p.key AS person_id, p.name AS name, o.pct AS pct, o.since AS since ORDER BY o.pct DESC", k=business_id)

    def holdings(self, person_id: str) -> list[dict[str, Any]]:
        return cypher("MATCH (:Person {key: $k})-[o:OWNS]->(b:Business) RETURN b.key AS business_id, b.name AS name, o.pct AS pct, o.since AS since ORDER BY b.key", k=person_id)

    def rules(self) -> list[dict[str, Any]]:
        return cypher("MATCH (r:Rule) RETURN r.key AS id, r.rule_name AS name, r.kind AS kind, r.field AS field, r.threshold AS threshold, r.text AS text ORDER BY r.key")


def _repo() -> GraphRepo:
    return GraphRepo()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ reads
def sop() -> dict[str, Any]:
    """The credit team's page, read from memory when the graph has it, else from the file."""
    try:
        rows = cypher("MATCH (p:Playbook) RETURN p.name AS name, p.text AS text LIMIT 1")
        if rows and rows[0].get("text"):
            return {"name": rows[0]["name"], "source": "memory", "text": rows[0]["text"]}
    except Exception:
        pass
    return {"name": "How we assess a business loan", "source": "file", "text": SOP_FILE.read_text()}


def application(application_id: str) -> dict[str, Any]:
    repo = _repo()
    app = repo.application(application_id)
    biz = repo.business(app["business_id"])
    owners = [{"name": o["name"], "pct": o["pct"], "since": o["since"]} for o in repo.owners(biz["id"])]
    rm = cypher("MATCH (r:RelationshipManager)-[:COVERS]->(:Business {key: $k}) RETURN r.key AS key, r.name AS name", k=biz["id"])
    notes = cypher("MATCH (:Business {key: $k})-[:HAS_NOTE]->(n:Note) RETURN n.key AS key, n.date AS date, n.text AS text ORDER BY n.date DESC", k=biz["id"])
    tenure = months_between(datetime.fromisoformat(biz["customer_since"]).date(), AS_OF)
    return {"as_of": AS_OF.isoformat(),
            "application": {"key": app["id"], "product": app["product"], "amount": app["amount"], "term_months": app["term_months"], "rate": app["rate"],
                            "proposed_monthly_payment": app["monthly_payment"], "purpose": app["purpose"], "submitted": app["submitted"], "requested_by": app["requested_by"]},
            "business": {"key": biz["id"], "name": biz["dba"], "legal_name": biz["legal_name"], "industry": biz["industry"], "founded": biz["founded"],
                         "customer_since": biz["customer_since"], "tenure_months": tenure, "tenure_years": round(tenure / 12, 1)},
            "owners": owners,
            "relationship_manager": rm[0] if rm else None,
            "crm_notes": notes,
            "cites": [app["id"], biz["id"]] + [n["key"] for n in notes]}


def ownership(business_id: str) -> dict[str, Any]:
    repo = _repo()
    repo.business(business_id)
    view = ownership_view(repo, business_id, AS_OF)
    cites = [business_id]
    for o in view["owners"]:
        cites.append(o["person"]["key"])
        for ob in o["other_businesses"]:
            cites.append(ob["business"]["key"])
            cites += [f["key"] for f in ob["facilities"]]
            cites += [k for f in ob["facilities"] for k in f["missed_payment_keys"]]
    view["cites"] = cites
    return view


def facilities(business_id: str) -> dict[str, Any]:
    repo = _repo()
    repo.business(business_id)
    out = []
    for f in repo.facilities(business_id):
        pays = repo.payments(f["id"])
        from loan.policy import late_days

        days, missed = late_days(pays, AS_OF)
        out.append({"key": f["id"], "product": f["product"], "principal": f["principal"], "rate": f["rate"], "term_months": f["term_months"],
                    "monthly_payment": f["monthly_payment"], "opened": f["opened"], "status": f["status"], "late_days": days, "missed_payment_keys": missed,
                    "payments": [{"key": p["id"], "due": p["due"], "paid_on": p["paid_on"], "amount": p["amount"], "status": p["status"]} for p in pays]})
    return {"business": business_id, "as_of": AS_OF.isoformat(), "facilities": out,
            "existing_monthly_payments": round(sum(f["monthly_payment"] for f in out if f["status"] == "open"), 2),
            "cites": [f["key"] for f in out] + [p["key"] for f in out for p in f["payments"]]}


def cashflow(business_id: str) -> dict[str, Any]:
    repo = _repo()
    repo.business(business_id)
    view = cashflow_view(repo, business_id, AS_OF)
    months = []
    for a in view["accounts"]:
        for m in repo.cashflow(a["key"]):
            months.append({"key": m["id"], "account": a["key"], "month": m["month"], "inflow": m["inflow"], "outflow": m["outflow"], "net": round(m["inflow"] - m["outflow"], 2)})
    view["months"] = sorted(months, key=lambda m: (m["month"], m["account"]))
    view["as_of"] = AS_OF.isoformat()
    return view


def kyc(business_id: str) -> dict[str, Any]:
    repo = _repo()
    repo.business(business_id)
    rec = repo.kyc(business_id) or {}
    events = [{"key": e["id"], "date": e["date"], "kind": e["kind"], "months_ago": round((AS_OF - datetime.fromisoformat(e["date"]).date()).days / 30.44, 1)}
              for e in repo.fraud_events(business_id)]
    return {"business": business_id, "as_of": AS_OF.isoformat(),
            "kyc": {"key": rec.get("id"), "status": rec.get("status"), "last_review": rec.get("last_review"), "beneficial_owners_verified": rec.get("beneficial_owners_verified")},
            "fraud_events": events, "cites": ([rec["id"]] if rec else []) + [e["key"] for e in events]}


def policy(application_id: str) -> dict[str, Any]:
    """R1-R6 and G1 applied to the application, with every figure and the keys it was computed from."""
    repo = _repo()
    fig = figures(repo, application_id, AS_OF)
    res = evaluate(fig, repo.rules())
    res["as_of"] = AS_OF.isoformat()
    res["connected"] = [{"owner": c["owner"], "business": c["business"], "pct": c["pct"], "worst_late_days": c["worst_late_days"],
                         "facilities": [{"key": f["key"], "product": f["product"], "principal": f["principal"], "status": f["status"], "late_days": f["late_days"]} for f in c["facilities"]]}
                        for c in fig["connected"]]
    res["own_facilities"] = [{"key": f["key"], "product": f["product"], "principal": f["principal"], "status": f["status"], "monthly_payment": f["monthly_payment"], "late_days": f["late_days"]}
                             for f in fig["own_facilities"]]
    return res


def _band(application_id: str) -> tuple[str, str]:
    repo = _repo()
    app = repo.application(application_id)
    res = evaluate(figures(repo, application_id, AS_OF), repo.rules())
    return app["product"], res["outcome"]


def precedents(application_id: str) -> dict[str, Any]:
    """Past filed decisions on applications of the same product in the same policy band."""
    product, band = _band(application_id)
    rows = cypher("""
        MATCH (d:Decision)-[:ABOUT]->(a:Application {product: $product})
        WHERE d.policy_outcome = $band
        OPTIONAL MATCH (d)-[:APPLIED_POLICY]->(r:Rule)
        WITH d, a, collect(r.key) AS rules
        RETURN d.key AS key, a.key AS application, a.business_id AS business, d.outcome AS outcome, d.confidence AS confidence,
               d.skill_revision AS skill_revision, d.at AS at, rules, left(d.rationale, 400) AS rationale_excerpt
        ORDER BY d.at""", product=product, band=band)
    return {"application": application_id, "product": product, "policy_band": band, "precedents": rows, "cites": [r["key"] for r in rows]}


# ------------------------------------------------------------------ the rationale
CITE_RE = re.compile(r"\[cite:\s*([^\]]+)\]")
MONEY_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*([kKmM])?\b")
RATIO_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?x\b")
PCT_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?%")
DAYS_RE = re.compile(r"\b(\d+)\s+days?\b")
OUTCOME_WORDS = {"approve": r"\bapprov(e|ed|al|ing)\b", "counter": r"\bcounter(-|\s)?(offer|ed|proposal)?\b", "decline": r"\bdeclin(e|ed|ing)\b", "refer": r"\brefer(red|ral|ring)?\b"}


def _rationale_path(rationale_id: str) -> Path:
    return RATIONALES_DIR / f"{rationale_id}.json"


def _load_rationale(rationale_id: str) -> dict[str, Any]:
    p = _rationale_path(rationale_id)
    if not p.exists():
        raise SystemExit(json.dumps({"error": f"unknown rationale {rationale_id}"}))
    return json.loads(p.read_text())


def submit_rationale(application_id: str, outcome: str, text: str) -> dict[str, Any]:
    ensure_run_dirs()
    if outcome not in OUTCOME_WORDS:
        raise SystemExit(json.dumps({"error": f"outcome must be one of {sorted(OUTCOME_WORDS)}", "got": outcome}))
    _repo().application(application_id)
    n = len(list(RATIONALES_DIR.glob(f"RAT-{application_id}-*.json"))) + 1
    rid = f"RAT-{application_id}-{n:02d}"
    rec = {"rationale_id": rid, "application": application_id, "outcome": outcome, "text": text, "submitted_at": _now(), "check": None}
    _rationale_path(rid).write_text(json.dumps(rec, indent=2))
    return {"rationale_id": rid, "application": application_id, "outcome": outcome, "chars": len(text), "cites": sorted({k.strip() for m in CITE_RE.findall(text) for k in m.split(",")})}


def _numbers(obj: Any, out: set[float]) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _numbers(v, out)


def _allowed_numbers(application_id: str) -> tuple[set[float], dict[str, Any]]:
    repo = _repo()
    fig = figures(repo, application_id, AS_OF)
    res = evaluate(fig, repo.rules())
    allowed: set[float] = set()
    _numbers(fig, allowed)
    _numbers(res["figures"], allowed)
    for f in fig["own_facilities"]:
        allowed.add(float(f["principal"]))
    for a in repo.accounts(fig["business"]["key"]):
        allowed.add(float(a["balance"]))
        for m in repo.cashflow(a["id"]):
            allowed.update({float(m["inflow"]), float(m["outflow"]), round(float(m["inflow"]) - float(m["outflow"]), 2)})
    for f in fig["own_facilities"] + [f for c in fig["connected"] for f in c["facilities"]]:
        for p in repo.payments(f["key"]):
            allowed.add(float(p["amount"]))
    for c in fig["connected"]:
        allowed.add(float(c["pct"]))
    for o in repo.owners(fig["business"]["key"]):
        allowed.add(float(o["pct"]))
    allowed.update({1.25, 1.0, 1_500_000.0, 25.0, 60.0, 12.0, 24.0, 5.0})  # the policy's own thresholds
    for rate in [fig["application"]["rate"]] + [f["rate"] for f in fig["own_facilities"]] + [f["rate"] for c in fig["connected"] for f in c["facilities"]]:
        if rate is not None:
            allowed.add(round(float(rate) * 100, 2))  # a rate written as a percentage (8.5% for 0.085)
    return allowed, res


def _close(value: float, allowed: set[float], tol_abs: float, tol_rel: float) -> bool:
    return any(abs(value - a) <= max(tol_abs, tol_rel * abs(a)) for a in allowed)


def check(rationale_id: str) -> dict[str, Any]:
    """The lint: every cite exists in the graph, every dollar figure, ratio, percentage and day count
    matches a figure the systems hold, the outcome stated matches the submitted outcome, and no protected
    characteristic is mentioned."""
    rec = _load_rationale(rationale_id)
    text = rec["text"]
    failures: list[dict[str, str]] = []
    cites = sorted({k.strip() for m in CITE_RE.findall(text) for k in m.split(",") if k.strip()})
    if not cites:
        failures.append({"check": "has_cites", "detail": "no [cite: KEY] markers; every figure and fact must cite the record it came from"})
    found = {r["key"] for r in cypher("UNWIND $keys AS k MATCH (n {key: k}) WHERE n:Entity OR n:Decision RETURN DISTINCT n.key AS key", keys=cites)} if cites else set()
    for k in cites:
        if k not in found:
            failures.append({"check": "cite_exists", "detail": f"[cite: {k}] names no node in the graph"})
    allowed, res = _allowed_numbers(rec["application"])
    for m in MONEY_RE.finditer(text):
        v = float(m.group(1).replace(",", ""))
        v *= {"k": 1_000, "m": 1_000_000}.get((m.group(2) or "").lower(), 1)
        # a rounded figure is fine ($6,336 for 6335.74; $1.4M for 1,400,000); an invented one is not
        if not _close(v, allowed, 1.0, 0.005):
            failures.append({"check": "figure_in_evidence", "detail": f"{m.group(0).strip()} matches no figure in the evidence (see `loan policy`)"})
    for m in RATIO_RE.finditer(text):
        if not _close(float(m.group(1)), allowed, 0.011, 0.0):
            failures.append({"check": "figure_in_evidence", "detail": f"ratio {m.group(0).strip()} matches no figure in the evidence"})
    for m in PCT_RE.finditer(text):
        if not _close(float(m.group(1)), allowed, 0.5, 0.0):
            failures.append({"check": "figure_in_evidence", "detail": f"{m.group(0).strip()} matches no percentage in the evidence"})
    for m in DAYS_RE.finditer(text):
        if not _close(float(m.group(1)), allowed, 0.0, 0.0):
            failures.append({"check": "figure_in_evidence", "detail": f"'{m.group(0)}' matches no day count in the evidence"})
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#")).strip()
    first = re.split(r"\n\s*\n", body)[0] if body else ""
    if not re.search(OUTCOME_WORDS[rec["outcome"]], first, re.I):
        failures.append({"check": "outcome_stated", "detail": f"the first paragraph must state the outcome ({rec['outcome']})"})
    for line in text.splitlines():
        if re.match(r"\s*\**\s*(outcome|decision|recommendation)\s*:?\**\s*:", line, re.I) and not re.search(OUTCOME_WORDS[rec["outcome"]], line, re.I):
            failures.append({"check": "outcome_stated", "detail": f"this line names a different outcome than {rec['outcome']}: {line.strip()[:80]!r}"})
    words = sorted({w.lower() for w in PROTECTED_WORDS.findall(text) if isinstance(w, str)} | {m.group(0).lower() for m in PROTECTED_WORDS.finditer(text)})
    if words:
        failures.append({"check": "no_protected_characteristics", "detail": "mentions " + ", ".join(words) + "; describe the business, not the people"})
    passed = not failures
    rec["check"] = {"passed": passed, "failures": failures, "cites": cites, "checked_at": _now(), "policy_outcome": res["outcome"], "fired": [f["rule"] for f in res["fired"]]}
    _rationale_path(rationale_id).write_text(json.dumps(rec, indent=2))
    return {"rationale_id": rationale_id, "application": rec["application"], "outcome": rec["outcome"], "passed": passed, "failures": failures,
            "cites": cites, "policy_outcome": res["outcome"], "fired": rec["check"]["fired"]}


def record(rationale_id: str, outcome: str, confidence: float, revision: str) -> dict[str, Any]:
    """File the decision: a Decision node with ABOUT, APPLIED_POLICY, CITES and PRECEDENT_FOR edges.
    Refuses a rationale that has not passed `loan check`."""
    rec = _load_rationale(rationale_id)
    chk = rec.get("check") or {}
    if not chk.get("passed"):
        raise SystemExit(json.dumps({"error": "the rationale has not passed `loan check`; run it first and fix what it names", "rationale_id": rationale_id,
                                     "failures": chk.get("failures")}))
    if outcome != rec["outcome"]:
        raise SystemExit(json.dumps({"error": f"--outcome {outcome} does not match the rationale's outcome {rec['outcome']}"}))
    if not 0.0 <= float(confidence) <= 1.0:
        raise SystemExit(json.dumps({"error": "--confidence must be between 0 and 1"}))
    app_id = rec["application"]
    repo = _repo()
    res = evaluate(figures(repo, app_id, AS_OF), repo.rules())
    pre = precedents(app_id)["precedents"]
    cited_decisions = [k for k in chk["cites"] if k.startswith("DEC-")]
    precedent_keys = sorted({p["key"] for p in pre} | set(cited_decisions))
    n = cypher("MATCH (d:Decision)-[:ABOUT]->(:Application {key: $k}) RETURN count(d) AS n", k=app_id)[0]["n"] + 1
    key = f"DEC-{app_id}-{n:02d}"
    fired = [f["rule"] for f in res["fired"]]
    cypher("""
        MATCH (a:Application {key: $app})
        CREATE (d:Decision:Filed {key: $key, outcome: $outcome, confidence: $confidence, skill_revision: $revision, at: $at,
                                  policy_outcome: $policy_outcome, fired_rules: $fired, rationale_id: $rid, rationale: $text, application: $app,
                                  name: $key + ' ' + $outcome})
        CREATE (d)-[:ABOUT]->(a)""",
           app=app_id, key=key, outcome=outcome, confidence=float(confidence), revision=str(revision), at=_now(), policy_outcome=res["outcome"],
           fired=fired, rid=rationale_id, text=rec["text"])
    cypher("UNWIND $fired AS rid MATCH (d:Decision {key: $key}), (r:Rule {key: rid}) MERGE (d)-[:APPLIED_POLICY]->(r)", key=key, fired=fired)
    cypher("UNWIND $cites AS ck MATCH (d:Decision {key: $key}), (c:Entity {key: ck}) MERGE (d)-[:CITES]->(c)",
           key=key, cites=[c for c in chk["cites"] if not c.startswith("DEC-")])
    cypher("UNWIND $precedents AS pk MATCH (d:Decision {key: $key}), (p:Decision {key: pk}) WHERE p <> d MERGE (p)-[:PRECEDENT_FOR]->(d)",
           key=key, precedents=precedent_keys)
    rec["decision"] = {"key": key, "outcome": outcome, "confidence": float(confidence), "skill_revision": str(revision), "at": _now()}
    _rationale_path(rationale_id).write_text(json.dumps(rec, indent=2))
    return {"decision_id": key, "application": app_id, "outcome": outcome, "confidence": float(confidence), "skill_revision": str(revision),
            "policy_outcome": res["outcome"], "applied_policy": fired, "cites": [c for c in chk["cites"] if not c.startswith("DEC-")],
            "precedents": precedent_keys, "rationale_id": rationale_id}


def decide(question: str, options: list[str], answer: str, why: str) -> dict[str, Any]:
    """Record a judgment call. The hook stores it as a :Decision step; here it just echoes the record."""
    return {"decision": question, "options": options, "answer": answer, "why": why, "at": _now()}
