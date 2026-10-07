"""Step 1: the Notion workspace into memory.

Entities go through the neo4j-agent-memory SDK (`long_term.add_entity`), which writes
`(:Entity:<Type>)` nodes. The SDK stores every relationship as `RELATED_TO {type}`, which is
hard to read in Browser, so the domain edges are written with the driver as real edge types:
PROMOTES, TARGETS, ASSERTS, CONSTRAINED_BY, REPRESENTS, FOLLOWS.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from blast.env import CHECKPOINTS, SOP_FILE, ensure_run_dirs
from blast.fixture import Fixture
from blast.memory import client, cypher

CHECKPOINT = CHECKPOINTS / "01-import.json"
SOP_NAME = "How we run an email blast"


def _s(v: Any) -> str:
    return " | ".join(str(x) for x in v) if isinstance(v, list) else ("" if v is None else str(v))


def plan(fx: Fixture) -> tuple[list[dict[str, Any]], list[tuple[str, str, str]]]:
    ents: list[dict[str, Any]] = []
    rels: list[tuple[str, str, str]] = []
    bg = fx.brand_guide()
    for p in fx.products():
        ents.append({"key": p["id"], "name": p["Name"], "type": "Product", "description": p["Tagline"], "attributes": {"version": _s(p["Version"]), "repo": _s(p["Repo"])}})
        claims = p["Approved claims"] if isinstance(p["Approved claims"], list) else [p["Approved claims"]]
        for i, c in enumerate(claims, 1):
            ents.append({"key": f"{p['id']}-claim-{i}", "name": c, "type": "Claim", "description": f"Approved claim for {p['Name']}", "attributes": {"product": p["Name"]}})
            rels.append((p["id"], "ASSERTS", f"{p['id']}-claim-{i}"))
        rels.append((p["id"], "CONSTRAINED_BY", bg["id"]))
    for p in fx.personas():
        ents.append({"key": p["id"], "name": p["Name"], "type": "Persona", "description": p["Cares about"], "attributes": {"role": _s(p["Role"]), "preferred_tone": _s(p["Preferred tone"]), "turn_offs": _s(p["Turn-offs"])}})
    for s in fx.segments():
        ents.append({"key": s["id"], "name": s["Name"], "type": "Segment", "description": s["Description"], "attributes": {"segment_id": s["id"], "size": _s(s["Size"]), "product": _s(s["Product"])}})
        for pid in s["Persona"]:
            rels.append((pid, "REPRESENTS", s["id"]))
    ents.append({"key": bg["id"], "name": bg["Name"], "type": "Brand", "description": _s(bg["Voice rules"]), "attributes": {"required_disclaimer": _s(bg["Required disclaimer"]), "banned_claims": _s(bg["Banned claims"]), "subject_line_rules": _s(bg["Subject line rules"])}})
    ents.append({"key": "sop-email-blast", "name": SOP_NAME, "type": "Playbook", "description": "The team's own page on how an email blast is done", "attributes": {"text": SOP_FILE.read_text()}})
    for b in fx.briefs():
        ents.append({"key": b["id"], "name": b["Name"], "type": "Campaign", "description": b["Goal"], "attributes": {"brief_id": b["id"], "campaign_id": b["Campaign ID"], "send_window": _s(b["Send window"]), "product": _s(b["Product"]), "cta": _s(b["CTA"])}})
        rels.append((b["id"], "PROMOTES", fx.product(b["Product"])["id"]))
        for sid in b["Segment"]:
            rels.append((b["id"], "TARGETS", sid))
        rels.append((b["id"], "CONSTRAINED_BY", bg["id"]))
        rels.append((b["id"], "FOLLOWS", "sop-email-blast"))
    return ents, rels


async def _create(ents: list[dict[str, Any]], log) -> dict[str, str]:
    mapping: dict[str, str] = {}
    async with client() as m:
        for e in ents:
            ent, _ = await m.long_term.add_entity(e["name"], e["type"], description=e["description"], attributes=e["attributes"],
                                                 resolve=False, generate_embedding=False, deduplicate=False, geocode=False, enrich=False)
            mapping[e["key"]] = str(ent.id)
    log(f"entities: {len(mapping)} written through the SDK")
    return mapping


def run_import(log=print) -> dict[str, Any]:
    ensure_run_dirs()
    fx = Fixture()
    ents, rels = plan(fx)
    existing = cypher("MATCH (e:Entity) RETURN count(e) AS n")[0]["n"]
    if existing:
        raise SystemExit(f"the memory database already holds {existing} entities; run `blast reset` first")
    mapping = asyncio.run(_create(ents, log))
    # typed edges, matched on the SDK's entity id, plus our stable key as a property for later joins
    rows = [{"id": mapping[e["key"]], "key": e["key"], "attrs": e["attributes"]} for e in ents]
    cypher("UNWIND $rows AS r MATCH (e:Entity {id: r.id}) SET e.key = r.key SET e += r.attrs", rows=rows)
    n = 0
    for s, t, o in rels:
        cypher(f"MATCH (a:Entity {{key: $s}}), (b:Entity {{key: $o}}) MERGE (a)-[:`{t}`]->(b)", s=s, o=o)
        n += 1
    log(f"relationships: {n} typed edges written")
    ck = {"stage": 1, "entities": mapping, "relationships": n}
    CHECKPOINT.write_text(json.dumps(ck, indent=2) + "\n")
    return ck


def verify(log=print) -> int:
    counts = {r["label"]: r["n"] for r in cypher("MATCH (e:Entity) UNWIND [l IN labels(e) WHERE l <> 'Entity'] AS label RETURN label, count(*) AS n")}
    rels = {r["t"]: r["n"] for r in cypher("MATCH (:Entity)-[r]->(:Entity) RETURN type(r) AS t, count(*) AS n")}
    log(f"nodes: {json.dumps(counts)}")
    log(f"edges: {json.dumps(rels)}")
    want = {"Campaign": 13, "Product": 4, "Claim": 13, "Persona": 4, "Segment": 6, "Brand": 1, "Playbook": 1}
    failures = [f"{k}: want {v}, got {counts.get(k, 0)}" for k, v in want.items() if counts.get(k, 0) != v]
    for t in ("PROMOTES", "TARGETS", "ASSERTS", "CONSTRAINED_BY", "REPRESENTS", "FOLLOWS"):
        if not rels.get(t):
            failures.append(f"no {t} edges")
    for f in failures:
        log("FAIL " + f)
    log("verify import: " + ("OK" if not failures else "FAILED"))
    return 1 if failures else 0


def reset(log=print) -> None:
    """Wipe everything the demo wrote (memory layers and traces). The database is ours."""
    n = cypher("MATCH (n) DETACH DELETE n RETURN count(n) AS n")[0]["n"] if False else None
    with __import__("blast.memory", fromlist=["driver"]).driver() as d:
        total = 0
        while True:
            r = d.execute_query("MATCH (n) WITH n LIMIT 5000 DETACH DELETE n RETURN count(n) AS n").records[0]["n"]
            total += r
            if r == 0:
                break
    log(f"reset: {total} nodes deleted")
    if CHECKPOINT.exists():
        CHECKPOINT.unlink()
