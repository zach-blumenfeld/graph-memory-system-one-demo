"""Step 2: the five bank systems into memory.

Entities go through the neo4j-agent-memory SDK (`long_term.add_entity`), which writes
`(:Entity:<Type>)` nodes. The SDK stores every relationship as `RELATED_TO {type}`, which is hard to
read in Browser, so the domain edges are written with the driver as real edge types:
OWNS, HOLDS, HAS_CASHFLOW, HAS_FACILITY, HAS_PAYMENT, APPLIED, KYC, HAD, SUBJECT_TO, COVERS,
HAS_NOTE, FOLLOWS. Decision nodes are not imported; `loan record` creates them later.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from loan.env import CHECKPOINTS, SOP_FILE, ensure_run_dirs
from loan.fixture import Fixture
from loan.memory import client, cypher

CHECKPOINT = CHECKPOINTS / "01-import.json"
SOP_NAME = "How we assess a business loan"
SOP_KEY = "sop-assess-loan"

Entity = dict[str, Any]
Edge = tuple[str, str, str, dict[str, Any]]  # (from key, type, to key, props)


def _money(v: float) -> str:
    return f"${v:,.0f}"


def plan(fx: Fixture) -> tuple[list[Entity], list[Edge]]:
    ents: list[Entity] = []
    rels: list[Edge] = []

    def ent(key: str, name: str, type_: str, description: str, **attrs: Any) -> None:
        ents.append({"key": key, "name": name, "type": type_, "description": description, "attributes": {k: v for k, v in attrs.items() if v is not None}})

    for b in fx.businesses():
        ent(b["id"], b["dba"], "Business", f"{b['legal_name']}, {b['industry']}; customer since {b['customer_since']}",
            legal_name=b["legal_name"], dba=b["dba"], industry=b["industry"], founded=b["founded"], customer_since=b["customer_since"])
    for a in fx.accounts():
        ent(a["id"], f"{a['id']} ({a['type']})", "Account", f"{a['type']} account of {a['business_id']}, opened {a['opened']}",
            type=a["type"], opened=a["opened"], balance=a["balance"], business_id=a["business_id"])
        rels.append((a["business_id"], "HOLDS", a["id"], {}))
        for m in fx.cashflow(a["id"]):
            ent(m["id"], f"{a['id']} {m['month']}", "Month", f"cash flow of {a['id']} in {m['month']}",
                month=m["month"], inflow=m["inflow"], outflow=m["outflow"], net=round(m["inflow"] - m["outflow"], 2), account_id=a["id"])
            rels.append((a["id"], "HAS_CASHFLOW", m["id"], {}))
    for f in fx.facilities():
        ent(f["id"], f"{f['id']} {f['product']} {_money(f['principal'])}", "Facility", f"{f['product']} of {_money(f['principal'])} at {f['business_id']}, {f['status']}",
            product=f["product"], principal=f["principal"], rate=f["rate"], term_months=f["term_months"], monthly_payment=f["monthly_payment"],
            opened=f["opened"], status=f["status"], business_id=f["business_id"])
        rels.append((f["business_id"], "HAS_FACILITY", f["id"], {}))
        for p in fx.payments(f["id"]):
            ent(p["id"], p["id"], "Payment", f"payment on {f['id']} due {p['due']}: {p['status']}",
                due=p["due"], paid_on=p["paid_on"], amount=p["amount"], status=p["status"], facility_id=f["id"])
            rels.append((f["id"], "HAS_PAYMENT", p["id"], {}))
    ent(SOP_KEY, SOP_NAME, "Playbook", "The credit team's own page on how a business loan is assessed", text=SOP_FILE.read_text())
    for r in fx.rules():
        ent(r["id"], f"{r['id']} {r['name']}", "Rule", r["text"], rule_id=r["id"], rule_name=r["name"], kind=r["kind"], field=r["field"],
            threshold=r["threshold"], secondary_threshold=r.get("secondary_threshold"), text=r["text"])
    for a in fx.applications():
        ent(a["id"], f"{a['id']} {a['product']} {_money(a['amount'])}", "Application", a["purpose"],
            application_id=a["id"], product=a["product"], amount=a["amount"], term_months=a["term_months"], rate=a["rate"], monthly_payment=a["monthly_payment"],
            purpose=a["purpose"], submitted=a["submitted"], requested_by=a["requested_by"], business_id=a["business_id"])
        rels.append((a["business_id"], "APPLIED", a["id"], {}))
        rels.append((a["id"], "FOLLOWS", SOP_KEY, {}))
        for r in fx.rules():
            rels.append((a["id"], "SUBJECT_TO", r["id"], {}))
    for k in fx.records("KycRecord"):
        ent(k["id"], f"KYC {k['business_id']}", "KycRecord", f"KYC {k['status']} for {k['business_id']}, last review {k['last_review']}",
            status=k["status"], last_review=k["last_review"], beneficial_owners_verified=k["beneficial_owners_verified"], business_id=k["business_id"])
        rels.append((k["business_id"], "KYC", k["id"], {}))
    for e in fx.records("FraudEvent"):
        ent(e["id"], e["id"], "FraudEvent", e["kind"], date=e["date"], kind=e["kind"], business_id=e["business_id"])
        rels.append((e["business_id"], "HAD", e["id"], {}))
    for p in fx.people():
        # dob is imported on purpose: the demo shows it is never passed to the judgment step.
        ent(p["id"], p["name"], "Person", f"{p['role']}", dob=p["dob"], role=p["role"])
    for o in fx.ownership():
        rels.append((o["person_id"], "OWNS", o["business_id"], {"pct": o["pct"], "since": o["since"]}))
    for rm in fx.rms():
        ent(rm["id"], rm["name"], "RelationshipManager", "relationship manager")
    for c in fx.coverage():
        rels.append((c["rm_id"], "COVERS", c["business_id"], {"since": c["since"]}))
    for n in fx.notes():
        ent(n["id"], n["id"], "Note", n["text"], date=n["date"], text=n["text"], business_id=n["business_id"])
        rels.append((n["business_id"], "HAS_NOTE", n["id"], {}))
    return ents, rels


async def _create(ents: list[Entity], log) -> dict[str, str]:
    mapping: dict[str, str] = {}
    async with client() as m:
        for i, e in enumerate(ents, 1):
            ent, _ = await m.long_term.add_entity(e["name"], e["type"], description=e["description"], attributes=e["attributes"],
                                                 resolve=False, generate_embedding=False, deduplicate=False, geocode=False, enrich=False)
            mapping[e["key"]] = str(ent.id)
            if i % 100 == 0:
                log(f"  {i}/{len(ents)} entities written")
    log(f"entities: {len(mapping)} written through the SDK")
    return mapping


def _set_keys(ents: list[Entity], mapping: dict[str, str]) -> None:
    rows = [{"id": mapping[e["key"]], "key": e["key"], "attrs": e["attributes"]} for e in ents]
    for i in range(0, len(rows), 200):
        cypher("UNWIND $rows AS r MATCH (e:Entity {id: r.id}) SET e.key = r.key SET e += r.attrs", rows=rows[i:i + 200])
    _fix_labels(ents)


def _fix_labels(ents: list[Entity]) -> None:
    """The SDK capitalises the type (`KycRecord` lands as `Kycrecord`); restore the intended label."""
    for t in {e["type"] for e in ents}:
        if t != t.capitalize():
            cypher(f"MATCH (e:Entity:`{t.capitalize()}`) SET e:`{t}` REMOVE e:`{t.capitalize()}`")


def _write_edges(rels: list[Edge]) -> int:
    by_type: dict[str, list[dict[str, Any]]] = {}
    for s, t, o, props in rels:
        by_type.setdefault(t, []).append({"s": s, "o": o, "p": props})
    n = 0
    for t, rows in by_type.items():
        cypher(f"UNWIND $rows AS r MATCH (a:Entity {{key: r.s}}), (b:Entity {{key: r.o}}) MERGE (a)-[e:`{t}`]->(b) SET e += r.p", rows=rows)
        n += len(rows)
    return n


def run_import(log=print) -> dict[str, Any]:
    ensure_run_dirs()
    fx = Fixture()
    ents, rels = plan(fx)
    existing = cypher("MATCH (e:Entity) RETURN count(e) AS n")[0]["n"]
    if existing:
        raise SystemExit(f"the memory database already holds {existing} entities; run `loan reset --yes` first")
    cypher("CREATE INDEX entity_key IF NOT EXISTS FOR (e:Entity) ON (e.key)")
    log(f"plan: {len(ents)} entities, {len(rels)} edges")
    mapping = asyncio.run(_create(ents, log))
    _set_keys(ents, mapping)
    n = _write_edges(rels)
    log(f"relationships: {n} typed edges written")
    ck = {"stage": 2, "as_of": fx.as_of().isoformat(), "entities": mapping, "relationships": n}
    CHECKPOINT.write_text(json.dumps(ck, indent=2) + "\n")
    return ck


def import_rules(log=print) -> None:
    """Step 7: (re)import the Rule nodes only. Existing rules are updated in place (their edges, including
    APPLIED_POLICY from earlier Decisions, survive); new rules are created through the SDK and every
    Application gets a SUBJECT_TO edge to them."""
    fx = Fixture()
    ents, _ = plan(fx)
    rules = [e for e in ents if e["type"] == "Rule"]
    have = {r["key"] for r in cypher("MATCH (r:Rule) RETURN r.key AS key")}
    new = [r for r in rules if r["key"] not in have]
    for r in rules:
        if r["key"] in have:
            cypher("MATCH (r:Rule {key: $key}) SET r.name = $name, r.description = $d SET r += $attrs", key=r["key"], name=r["name"], d=r["description"], attrs=r["attributes"])
    mapping = asyncio.run(_create(new, log)) if new else {}
    if new:
        _set_keys(new, mapping)
    edges = [(a["id"], "SUBJECT_TO", r["key"], {}) for a in fx.applications() for r in rules]
    n = _write_edges(edges)
    log(f"rules: {len(rules)} in the fixture, {len(new)} new ({', '.join(r['key'] for r in new) or 'none'}), {len(rules) - len(new)} updated; {n} SUBJECT_TO edges merged")
    if CHECKPOINT.exists():
        ck = json.loads(CHECKPOINT.read_text())
        ck["entities"].update(mapping)
        ck.setdefault("rules_reimported", []).append({"new": [r["key"] for r in new], "updated": len(rules) - len(new)})
        CHECKPOINT.write_text(json.dumps(ck, indent=2) + "\n")


WANT = {"Business": 7, "Account": 10, "Month": 240, "Facility": 7, "Payment": 144, "Application": 5, "KycRecord": 7, "Rule": 8,
        "FraudEvent": 1, "Person": 10, "RelationshipManager": 2, "Note": 9, "Playbook": 1}
EDGE_TYPES = ("OWNS", "HOLDS", "HAS_CASHFLOW", "HAS_FACILITY", "HAS_PAYMENT", "APPLIED", "KYC", "HAD", "SUBJECT_TO", "COVERS", "HAS_NOTE", "FOLLOWS")
PROOF = """
MATCH (a:Application {key: 'APP-1001'})<-[:APPLIED]-(b)<-[:OWNS]-(p)-[:OWNS]->(o)-[:HAS_FACILITY]->(f)-[:HAS_PAYMENT]->(pay {status: 'missed'})
RETURN o.name AS business, f.key AS facility, count(pay) AS missed"""


def verify(log=print) -> int:
    counts = {r["label"]: r["n"] for r in cypher("MATCH (e:Entity) UNWIND [l IN labels(e) WHERE l <> 'Entity'] AS label RETURN label, count(*) AS n")}
    rels = {r["t"]: r["n"] for r in cypher("MATCH (:Entity)-[r]->(:Entity) RETURN type(r) AS t, count(*) AS n")}
    log(f"nodes: {json.dumps(counts)}")
    log(f"edges: {json.dumps(rels)}")
    failures = [f"{k}: want {v}, got {counts.get(k, 0)}" for k, v in WANT.items() if counts.get(k, 0) != v]
    for t in EDGE_TYPES:
        if not rels.get(t):
            failures.append(f"no {t} edges")
    proof = cypher(PROOF)
    log(f"proof (APP-1001 → owners → other business → facility → missed payments): {proof}")
    if not (len(proof) == 1 and proof[0]["business"] == "Alder Logistics" and proof[0]["facility"] == "FAC-03" and proof[0]["missed"] == 3):
        failures.append("the connected-delinquency query did not return Alder Logistics / FAC-03 / 3 missed payments")
    for f in failures:
        log("FAIL " + f)
    log("verify import: " + ("OK" if not failures else "FAILED"))
    return 1 if failures else 0


MEMORY_LABELS = ("Entity", "Conversation", "Message", "ReasoningTrace", "ReasoningStep", "ToolCall", "Decision")


def reset(log=print) -> None:
    """Wipe everything the demo wrote to memory: the imported entities, conversations, traces and decisions.
    Scoped to the memory labels, so an aip catalog sharing the instance is untouched."""
    from loan.memory import driver

    with driver() as d:
        total = 0
        for label in MEMORY_LABELS:
            while True:
                r = d.execute_query(f"MATCH (n:{label}) WITH n LIMIT 5000 DETACH DELETE n RETURN count(n) AS n").records[0]["n"]
                total += r
                if r == 0:
                    break
    log(f"reset: {total} memory nodes deleted ({', '.join(MEMORY_LABELS)})")
    if CHECKPOINT.exists():
        CHECKPOINT.unlink()
