"""Read the Notion-shaped fixture in data/notion/ and flatten page properties."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from blast.env import DATA, RUN_DIR


def _flatten(prop: dict[str, Any]) -> Any:
    kind = prop.get("type")
    if kind == "title":
        return "".join(t.get("plain_text", "") for t in prop["title"])
    if kind == "rich_text":
        parts = [t.get("plain_text", "") for t in prop["rich_text"]]
        return parts if len(parts) > 1 else (parts[0] if parts else "")
    if kind == "select":
        return (prop.get("select") or {}).get("name")
    if kind == "multi_select":
        return [o["name"] for o in prop.get("multi_select") or []]
    if kind == "number":
        return prop.get("number")
    if kind == "date":
        return (prop.get("date") or {}).get("start")
    if kind == "checkbox":
        return bool(prop.get("checkbox"))
    if kind == "url":
        return prop.get("url")
    if kind == "relation":
        return [r["id"] for r in prop.get("relation") or []]
    return prop.get(kind)


def flatten_page(page: dict[str, Any]) -> dict[str, Any]:
    out = {"id": page["id"]}
    for name, prop in page["properties"].items():
        out[name] = _flatten(prop)
    return out


class Fixture:
    """All Notion databases, flattened. `data_dir` lets tests point at a copy."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or DATA
        self._db: dict[str, dict[str, Any]] = {}

    def db(self, name: str) -> dict[str, Any]:
        if name not in self._db:
            self._db[name] = json.loads((self.data_dir / f"{name}.json").read_text())
        return self._db[name]

    def pages(self, name: str) -> list[dict[str, Any]]:
        return [flatten_page(p) for p in self.db(name)["pages"]]

    def by_id(self, name: str, page_id: str) -> dict[str, Any]:
        for p in self.pages(name):
            if p["id"] == page_id:
                return p
        raise KeyError(f"{name}: no page with id {page_id!r}")

    # ------------------------------------------------------------- typed accessors
    def brief(self, brief_id: str) -> dict[str, Any]:
        return self.by_id("campaign_briefs", brief_id)

    def briefs(self) -> list[dict[str, Any]]:
        return self.pages("campaign_briefs")

    def product(self, name_or_id: str) -> dict[str, Any]:
        for p in self.pages("products"):
            if p["id"] == name_or_id or p["Name"].lower() == name_or_id.lower():
                return p
        raise KeyError(f"unknown product {name_or_id!r}")

    def products(self) -> list[dict[str, Any]]:
        return self.pages("products")

    def persona(self, persona_id: str) -> dict[str, Any]:
        return self.by_id("personas", persona_id)

    def personas(self) -> list[dict[str, Any]]:
        return self.pages("personas")

    def segment(self, segment_id: str) -> dict[str, Any]:
        return self.by_id("audience_segments", segment_id)

    def segments(self, product: str | None = None) -> list[dict[str, Any]]:
        segs = self.pages("audience_segments")
        if product is None:
            return segs
        wanted = self.product(product)["Name"].lower()
        return [s for s in segs if (s["Product"] or "").lower() in (wanted, "all")]

    def brand_guide(self) -> dict[str, Any]:
        return self.pages("brand_guide")[0]

    def channels(self) -> list[dict[str, Any]]:
        return self.pages("channels")

    # ------------------------------------------------------------- campaign log
    def campaign_log_path(self) -> Path:
        """The agent appends to a working copy under .run/ so the committed fixture stays clean."""
        live = RUN_DIR / "notion" / "campaign_log.json"
        if not live.exists():
            live.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(self.data_dir / "campaign_log.json", live)
        return live

    def append_campaign_log(self, campaign_id: str, draft_id: str, summary: str, scheduled: bool) -> dict[str, Any]:
        path = self.campaign_log_path()
        db = json.loads(path.read_text())
        n = len(db["pages"]) + 1
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        page = {
            "object": "page",
            "id": f"log-{n:04d}",
            "created_time": now,
            "last_edited_time": now,
            "archived": False,
            "properties": {
                "Name": {"type": "title", "title": [{"type": "text", "plain_text": f"{campaign_id} / {draft_id}", "text": {"content": f"{campaign_id} / {draft_id}"}}]},
                "Campaign ID": {"type": "rich_text", "rich_text": [{"type": "text", "plain_text": campaign_id, "text": {"content": campaign_id}}]},
                "Draft ID": {"type": "rich_text", "rich_text": [{"type": "text", "plain_text": draft_id, "text": {"content": draft_id}}]},
                "Summary": {"type": "rich_text", "rich_text": [{"type": "text", "plain_text": summary, "text": {"content": summary}}]},
                "Logged at": {"type": "date", "date": {"start": now}},
                "Scheduled": {"type": "checkbox", "checkbox": scheduled},
            },
        }
        db["pages"].append(page)
        path.write_text(json.dumps(db, indent=2, ensure_ascii=False) + "\n")
        return flatten_page(page)


@lru_cache(maxsize=1)
def default_fixture() -> Fixture:
    return Fixture()
