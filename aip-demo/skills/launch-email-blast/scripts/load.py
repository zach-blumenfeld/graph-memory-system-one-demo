#!/usr/bin/env python3
"""Read the brief, product, segments and brand guide; pick the segment by the SOP rule.

stdin:  currentState with brief_id (str) and send_at (str, may be empty)
stdout: brief, campaign_id, product, brand, segment, persona, segment_rule
"""
from blastlib import blast, read_state, write

state = read_state()
brief = blast("brief", state["brief_id"])
product = blast("product", brief["product"])
segments = blast("segments", brief["product"])["segments"]
brand = blast("brand")

# SOP: the brief usually names a segment; if it only names a persona, pick the product segment for that persona.
named = [s for s in segments if s["segment_id"] in (brief.get("segment_ids") or [])]
if named:
    segment, rule = named[0], "the brief names this segment"
else:
    by_persona = [s for s in segments if any(p["id"] in (brief.get("persona_ids") or []) for p in s["persona"])]
    if not by_persona:
        raise SystemExit(f"brief {brief['brief_id']} names no segment and no persona matching a {brief['product']} segment; "
                         f"available: {[s['segment_id'] for s in segments]}")
    segment, rule = by_persona[0], "the brief names only a persona; this is the product's segment for that persona"

persona = segment["persona"][0] if segment.get("persona") else {"id": "", "name": "the reader", "preferred_tone": "", "turn_offs": ""}

write({"brief": brief, "campaign_id": brief["campaign_id"], "product": product, "brand": brand,
       "segment": segment, "persona": persona, "segment_rule": rule})
