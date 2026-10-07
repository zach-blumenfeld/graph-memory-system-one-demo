"""Stage 1: load the Notion fixture into the NAMS workspace under the PMM ontology."""

from __future__ import annotations

import json
from typing import Any

from pmm.env import CHECKPOINTS
from pmm.fixture import Fixture
from pmm.nams_rest import NamsRest

CHECKPOINT = CHECKPOINTS / "01-notion-import.json"


def _s(v: Any) -> str:
    if isinstance(v, list):
        return " | ".join(str(x) for x in v)
    return "" if v is None else str(v)


def plan_entities(fx: Fixture) -> list[dict[str, Any]]:
    """Entities keyed by Notion page id (Claims get synthetic ids)."""
    ents: list[dict[str, Any]] = []
    for p in fx.products():
        ents.append({"page_id": p["id"], "name": p["Name"], "type": "Product", "description": p["Tagline"], "properties": {"version": _s(p["Version"]), "repo": _s(p["Repo"])}})
        claims = p["Approved claims"] if isinstance(p["Approved claims"], list) else [p["Approved claims"]]
        for i, c in enumerate(claims, 1):
            ents.append({"page_id": f"{p['id']}-claim-{i}", "name": c, "type": "Claim", "description": f"Approved claim for {p['Name']}", "properties": {"approved": "true", "product": p["Name"]}})
    for p in fx.personas():
        ents.append({"page_id": p["id"], "name": p["Name"], "type": "Persona", "description": p["Cares about"], "properties": {"role": _s(p["Role"]), "preferred_tone": _s(p["Preferred tone"])}})
    for s in fx.segments():
        ents.append({"page_id": s["id"], "name": s["Name"], "type": "AudienceSegment", "description": s["Description"], "properties": {"segment_id": s["id"], "size": _s(s["Size"]), "product": _s(s["Product"])}})
    for c in fx.channels():
        ents.append({"page_id": c["id"], "name": c["Name"], "type": "Channel", "description": c["Description"], "properties": {}})
    bg = fx.brand_guide()
    ents.append({"page_id": bg["id"], "name": bg["Name"], "type": "BrandGuideline", "description": _s(bg["Voice rules"]), "properties": {"required_disclaimer": _s(bg["Required disclaimer"]), "banned_claims": _s(bg["Banned claims"])}})
    for b in fx.briefs():
        ents.append({"page_id": b["id"], "name": b["Name"], "type": "Campaign", "description": b["Goal"], "properties": {"campaign_id": b["Campaign ID"], "brief_id": b["id"], "send_window": _s(b["Send window"]), "product": _s(b["Product"])}})
    return ents


def plan_relationships(fx: Fixture) -> list[tuple[str, str, str]]:
    """(source page id, type, target page id)."""
    rels: list[tuple[str, str, str]] = []
    bg = fx.brand_guide()["id"]
    channel = fx.channels()[0]["id"]
    for p in fx.products():
        claims = p["Approved claims"] if isinstance(p["Approved claims"], list) else [p["Approved claims"]]
        for i in range(1, len(claims) + 1):
            rels.append((p["id"], "ASSERTS", f"{p['id']}-claim-{i}"))
        rels.append((p["id"], "CONSTRAINED_BY", bg))
    for s in fx.segments():
        for pid in s["Persona"]:
            rels.append((pid, "REPRESENTS", s["id"]))
    for b in fx.briefs():
        rels.append((b["id"], "PROMOTES", fx.product(b["Product"])["id"]))
        for sid in b["Segment"]:
            rels.append((b["id"], "TARGETS", sid))
        for pid in b["Persona"]:
            rels.append((b["id"], "TARGETS", pid))
        rels.append((b["id"], "USES_CHANNEL", channel))
        rels.append((b["id"], "CONSTRAINED_BY", bg))
    return rels


def _extract_ids(resp: Any, n: int) -> list[dict[str, Any]]:
    """Normalise a bulk response to a list of per-item dicts with at least `id`."""
    if isinstance(resp, dict):
        for key in ("entities", "results", "items", "created", "relationships"):
            if key in resp and isinstance(resp[key], list):
                return resp[key]
        if "id" in resp and n == 1:
            return [resp]
    if isinstance(resp, list):
        return resp
    raise RuntimeError(f"unexpected bulk response shape: {json.dumps(resp)[:300]}")


def run_import(nams: NamsRest, fx: Fixture, log=print, force: bool = False) -> dict[str, Any]:
    ents = plan_entities(fx)
    rels = plan_relationships(fx)
    mapping: dict[str, str] = {}
    if CHECKPOINT.exists() and not force:
        mapping = json.loads(CHECKPOINT.read_text()).get("entities", {})
        if mapping:
            existing = {r["id"] for r in nams.cypher("MATCH (e:Entity) WHERE e.id IN $ids RETURN e.id AS id", {"ids": list(mapping.values())})}
            mapping = {k: v for k, v in mapping.items() if v in existing}
            log(f"checkpoint: {len(mapping)} of {len(ents)} entities already present, importing the rest")

    todo = [e for e in ents if e["page_id"] not in mapping]
    merged: list[dict[str, str]] = []
    created = 0
    for e in todo:  # one at a time: the per-entity response tells us about resolve-before-create merges
        resp = nams.create_entity(e["name"], e["type"], e["description"], e["properties"])
        eid = resp.get("id") or resp.get("merged_into") or resp.get("mergedInto")
        if not eid:
            raise RuntimeError(f"entity create returned no id: {json.dumps(resp)[:300]}")
        if resp.get("resolution") == "merged":
            merged.append({"page_id": e["page_id"], "name": e["name"], "merged_into": eid})
        else:
            created += 1
        mapping[e["page_id"]] = eid
    log(f"entities: {created} created, {len(merged)} merged by entity resolution, {len(mapping)} mapped")
    for m in merged:
        log(f"  merged: {m['name'][:60]!r} -> {m['merged_into']}")

    # relationships: idempotent on the server? unknown, so skip ones already present
    have = {(r["s"], r["t"], r["type"]) for r in nams.cypher(
        "MATCH (a:Entity)-[r]->(b:Entity) WHERE a.id IN $ids AND b.id IN $ids RETURN a.id AS s, b.id AS t, type(r) AS type",
        {"ids": list(mapping.values())})}
    want = [{"sourceId": mapping[s], "targetId": mapping[t], "relationshipType": typ} for s, typ, t in rels if s in mapping and t in mapping]
    missing = [w for w in want if (w["sourceId"], w["targetId"], w["relationshipType"]) not in have]
    rel_created = 0
    for i in range(0, len(missing), 50):
        chunk = missing[i : i + 50]
        nams.bulk_relationships(chunk)
        rel_created += len(chunk)
    log(f"relationships: {rel_created} created ({len(want) - len(missing)} already present, {len(rels) - len(want)} skipped for unmapped endpoints)")

    CHECKPOINTS.mkdir(exist_ok=True)
    ckpt = {"stage": 1, "entities": mapping, "merged": merged, "relationship_count": len(want), "source": "data/notion"}
    CHECKPOINT.write_text(json.dumps(ckpt, indent=2) + "\n")
    return ckpt
