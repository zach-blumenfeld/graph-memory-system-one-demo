"""Generate the Notion-shaped fixture in data/notion/. Run: uv run python tools/make_fixture.py

Every file is a Notion database object with its pages inlined under "pages"; each page carries
Notion-style `properties` (title / rich_text / select / multi_select / number / date / checkbox /
relation). The JSON is committed and is the source of truth; this script exists so the fixture is
reproducible and reviewable as code.
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "notion"

DISCLAIMER = (
    "Tessera Labs projects are experimental and community-supported. They are not covered by "
    "support contracts and may change without notice."
)


def title(text: str) -> dict:
    return {"type": "title", "title": [{"type": "text", "plain_text": text, "text": {"content": text}}]}


def rich(text: str) -> dict:
    return {"type": "rich_text", "rich_text": [{"type": "text", "plain_text": text, "text": {"content": text}}]}


def select(name: str) -> dict:
    return {"type": "select", "select": {"name": name}}


def multi(names: list[str]) -> dict:
    return {"type": "multi_select", "multi_select": [{"name": n} for n in names]}


def number(n: float) -> dict:
    return {"type": "number", "number": n}


def date(start: str) -> dict:
    return {"type": "date", "date": {"start": start}}


def checkbox(v: bool) -> dict:
    return {"type": "checkbox", "checkbox": v}


def relation(ids: list[str]) -> dict:
    return {"type": "relation", "relation": [{"id": i} for i in ids]}


def page(page_id: str, props: dict) -> dict:
    return {
        "object": "page",
        "id": page_id,
        "created_time": "2026-09-28T09:00:00.000Z",
        "last_edited_time": "2026-10-06T09:00:00.000Z",
        "archived": False,
        "properties": props,
    }


def database(db_id: str, name: str, schema: dict, pages: list[dict]) -> dict:
    return {
        "object": "database",
        "id": db_id,
        "title": [{"type": "text", "plain_text": name, "text": {"content": name}}],
        "properties": {k: {"type": v} for k, v in schema.items()},
        "pages": pages,
    }


# --------------------------------------------------------------------------- products
# Tessera Labs is a fictional open-source lab; every project, person, number and claim below is invented.
PRODUCTS = [
    {
        "id": "prod-riverbed",
        "name": "riverbed",
        "tagline": "Stream processing for Python that fits in one file",
        "repo": "https://github.com/tessera-labs/riverbed",
        "docs": "https://tessera-labs.example/riverbed/",
        "claims": [
            "Runs windowed aggregations over Kafka, Kinesis and local files with one API",
            "Checkpoints pipeline state so a restarted worker resumes without reprocessing",
            "Ships typed connectors for Postgres, DuckDB and Parquet",
            "Processes 120k events per second per core on the published benchmark suite",
        ],
        "version": "1.8.0",
    },
    {
        "id": "prod-tidewatch",
        "name": "tidewatch",
        "tagline": "See every pipeline, lag and retry in one place",
        "repo": "https://github.com/tessera-labs/tidewatch",
        "docs": "https://tessera-labs.example/tidewatch/",
        "claims": [
            "Collects lag, throughput and error metrics from any riverbed pipeline with no code changes",
            "Alerts on consumer lag with per-topic thresholds",
            "Stores 30 days of metrics in an embedded time-series store",
        ],
        "version": "0.9.0",
    },
    {
        "id": "prod-mooring",
        "name": "mooring",
        "tagline": "A schema registry you can run from a laptop",
        "repo": "https://github.com/tessera-labs/mooring",
        "docs": "https://tessera-labs.example/mooring/",
        "claims": [
            "Registers Avro, Protobuf and JSON Schema definitions with compatibility checks",
            "Single binary, SQLite-backed, starts in under a second",
            "Compatible with the Confluent-style REST API for existing clients",
        ],
        "version": "2.1.0",
    },
    {
        "id": "prod-ballast",
        "name": "ballast",
        "tagline": "Load-test a streaming pipeline before your users do",
        "repo": "https://github.com/tessera-labs/ballast",
        "docs": "https://tessera-labs.example/ballast/",
        "claims": [
            "Replays recorded traffic at 1x to 50x speed against a staging pipeline",
            "Reports p50/p95/p99 end-to-end latency per stage",
            "Runs as a GitHub Action with a pass/fail latency budget",
        ],
        "version": "0.4.0",
    },
]

# --------------------------------------------------------------------------- personas
PERSONAS = [
    {
        "id": "persona-stream-dev",
        "name": "Noor the Streaming Developer",
        "role": "Python developer building event pipelines",
        "cares_about": "shipping a pipeline that survives restarts without babysitting it",
        "reads": "release notes, code samples, GitHub READMEs",
        "turn_offs": "marketing fluff, vague claims, anything that reads like an enterprise brochure",
        "preferred_tone": "direct, technical, show me the code",
    },
    {
        "id": "persona-platform-lead",
        "name": "Teo the Platform Lead",
        "role": "platform engineer standardising streaming tooling for several teams",
        "cares_about": "operability, upgrade safety, benchmarks that can be reproduced",
        "reads": "architecture docs, benchmark tables, specs",
        "turn_offs": "lock-in, unverifiable numbers, hype",
        "preferred_tone": "measured, evidence-led, specific",
    },
    {
        "id": "persona-data-engineer",
        "name": "Ines the Data Engineer",
        "role": "data engineer who already runs batch pipelines and is adding streaming",
        "cares_about": "reusing existing schemas and warehouses instead of adding systems",
        "reads": "data modelling guides, migration write-ups",
        "turn_offs": "yet another database to operate, buzzwords",
        "preferred_tone": "practical, concrete, migration-first",
    },
    {
        "id": "persona-community-organiser",
        "name": "Sam the Community Organiser",
        "role": "developer advocate and meetup organiser",
        "cares_about": "demos that work live, tutorials to share, things to talk about at meetups",
        "reads": "blog posts, demo repos, conference talks",
        "turn_offs": "closed betas, demos that need a sales call",
        "preferred_tone": "warm, curious, story-driven",
    },
]

# --------------------------------------------------------------------------- segments
SEGMENTS = [
    {"id": "seg-python-stream-devs", "name": "Python streaming developers", "product": "riverbed", "persona": "persona-stream-dev", "size": 3700, "description": "Developers who installed riverbed or starred the repo in the last 6 months"},
    {"id": "seg-pipeline-operators", "name": "Pipeline operators", "product": "tidewatch", "persona": "persona-platform-lead", "size": 1300, "description": "People who run riverbed pipelines in a shared environment and asked about monitoring"},
    {"id": "seg-mooring-early-adopters", "name": "mooring early adopters", "product": "mooring", "persona": "persona-data-engineer", "size": 650, "description": "People who registered a schema in mooring during the 2.0 beta"},
    {"id": "seg-ci-builders", "name": "CI builders", "product": "ballast", "persona": "persona-platform-lead", "size": 900, "description": "Developers who added a Tessera Labs GitHub Action to a repo"},
    {"id": "seg-connector-maintainers", "name": "Connector maintainers", "product": "riverbed", "persona": "persona-platform-lead", "size": 280, "description": "Maintainers and contributors of riverbed connectors"},
    {"id": "seg-labs-newsletter", "name": "Tessera Labs newsletter", "product": "all", "persona": "persona-community-organiser", "size": 8400, "description": "Everyone subscribed to the monthly Tessera Labs digest"},
]

# --------------------------------------------------------------------------- briefs
BRIEFS = [
    {"id": "brief-001", "campaign_id": "camp-2026-10-001", "title": "riverbed 1.8: checkpointed state for every pipeline", "product": "riverbed", "segment": "seg-python-stream-devs", "persona": "persona-stream-dev", "kind_hint": "launch",
     "goal": "Announce the 1.8 release, whose headline is checkpointed pipeline state, and drive upgrades.",
     "key_messages": ["Pipeline state is checkpointed, so a restarted worker resumes where it stopped", "One pip install, no changes to existing pipelines", "New CLI command to inspect a checkpoint"],
     "cta": "Upgrade with pip install -U riverbed and open the checkpoint quickstart", "send_window": "2026-10-14", "notes": "Keep it short, developers only. Link the quickstart and the changelog."},
    {"id": "brief-002", "campaign_id": "camp-2026-10-002", "title": "mooring 2.1: compatibility checks for Protobuf", "product": "mooring", "segment": "seg-mooring-early-adopters", "persona": "persona-data-engineer", "kind_hint": "launch",
     "goal": "Launch mooring 2.1 to the early adopter list and get them to try Protobuf compatibility checks.",
     "key_messages": ["Protobuf schemas now get the same compatibility checks as Avro", "Single binary, starts in under a second", "Published benchmark: 4,000 schema lookups per second on a laptop"],
     "cta": "Read the 2.1 release notes and run the quickstart", "send_window": "2026-10-15", "notes": "Cite the published benchmark page for the number. No forward-looking claims."},
    {"id": "brief-003", "campaign_id": "camp-2026-10-003", "title": "tidewatch 0.9", "product": "tidewatch", "segment": "seg-pipeline-operators", "persona": "persona-platform-lead", "kind_hint": "launch",
     "goal": "Announce the 0.9 release of the dashboard and get operators to run it once.",
     "key_messages": ["One command attaches the dashboard to a running riverbed pipeline", "Per-topic lag alerts", "30 days of metrics in an embedded store, nothing else to run"],
     "cta": "Run tidewatch attach and share a screenshot", "send_window": "2026-10-16", "notes": "Operator tone. Mention that it is a Labs project."},
    {"id": "brief-004", "campaign_id": "camp-2026-10-004", "title": "ballast 0.4: latency budgets in CI", "product": "ballast", "segment": "seg-ci-builders", "persona": "persona-platform-lead", "kind_hint": "launch",
     "goal": "Introduce the latency-budget feature to CI builders and invite them to add it to a workflow.",
     "key_messages": ["Fail the build when p99 latency exceeds a budget you set", "Replays recorded traffic at up to 50x", "Reports latency per pipeline stage"],
     "cta": "Add the ballast action to one workflow and open an issue with results", "send_window": "2026-10-17", "notes": "Small, technical list. Be concrete about what the action checks."},
    {"id": "brief-005", "campaign_id": "camp-2026-10-005", "title": "Hosted tidewatch preview for pipeline operators", "product": "tidewatch", "segment": "seg-pipeline-operators", "persona": "persona-platform-lead", "kind_hint": "launch",
     "goal": "Tell operators that a hosted preview of the dashboard exists so they can try it without running anything.",
     "key_messages": ["Same dashboard, hosted, zero infrastructure to try it", "Point it at a staging pipeline in five minutes", "Bring your own metrics store if you prefer"],
     "cta": "Request early access to the hosted preview", "send_window": "2026-10-20", "notes": "Early access, no SLA language, no pricing. Labs disclaimer required."},
    {"id": "brief-006", "campaign_id": "camp-2026-10-006", "title": "riverbed benchmark write-up published", "product": "riverbed", "segment": "seg-connector-maintainers", "persona": "persona-platform-lead", "kind_hint": "launch",
     "goal": "Announce the published benchmark write-up and the reproducible harness.",
     "key_messages": ["Write-up: how the 120k events per second per core number was measured", "Harness and raw results in the benchmarks repo", "Reproduce it on your own hardware"],
     "cta": "Read the write-up and reproduce the benchmark", "send_window": "2026-10-21", "notes": "Technical tone is fine. Link the benchmarks repo."},
    {"id": "brief-007", "campaign_id": "camp-2026-10-007", "title": "tidewatch: Grafana and Datadog exporters", "product": "tidewatch", "segment": "seg-pipeline-operators", "persona": "persona-platform-lead", "kind_hint": "launch",
     "goal": "Announce new exporters so operators on an existing monitoring stack can keep it.",
     "key_messages": ["Export tidewatch metrics to the stack you already run", "Same alerts, different dashboard", "Exporters are community-contributed and open"],
     "cta": "Enable an exporter and tell us what is missing", "send_window": "2026-10-22", "notes": "Thank the contributors by project, not by name."},
    {"id": "brief-008", "campaign_id": "camp-2026-10-008", "title": "ballast: GitLab CI and Buildkite support", "product": "ballast", "segment": "seg-ci-builders", "persona": "persona-platform-lead", "kind_hint": "launch",
     "goal": "Announce that ballast now runs on GitLab CI and Buildkite too.",
     "key_messages": ["Same latency budgets on GitHub Actions, GitLab CI and Buildkite", "One config file, any runner", "CI recipes for each included"],
     "cta": "Add ballast to your CI", "send_window": "2026-10-23", "notes": "Short. Link the CI recipes."},
    {"id": "brief-009", "campaign_id": "camp-2026-10-009", "title": "riverbed 1.8.1 hotfix: checkpoint retry bug", "product": "riverbed", "segment": "seg-python-stream-devs", "persona": "persona-stream-dev", "kind_hint": "launch",
     "goal": "Get everyone on 1.8.0 to upgrade to 1.8.1 today because of a retry bug in checkpoint writes.",
     "key_messages": ["1.8.0 can write a checkpoint twice under retry; 1.8.1 fixes it", "Upgrade is a drop-in pip install", "No data loss, no config change"],
     "cta": "pip install -U riverbed today", "send_window": "2026-10-07", "notes": "URGENT. Leadership wants this out this morning."},
    {"id": "brief-010", "campaign_id": "camp-2026-10-010", "title": "mooring at the Streams conference: live demo and office hours", "product": "mooring", "segment": "seg-mooring-early-adopters", "persona": "persona-data-engineer", "kind_hint": "launch",
     "goal": "Announce the mooring demo at the conference and the office-hours slot, and get sign-ups.",
     "key_messages": ["Live demo of schema evolution with compatibility checks", "Office hours for teams migrating registries", "Bring your own schemas"],
     "cta": "Sign up for office hours", "send_window": "2026-10-08", "notes": "The conference is in two days; the organiser asked for the mail yesterday."},
    {"id": "brief-011", "campaign_id": "camp-2026-10-011", "title": "Stream processing without the batch ceiling", "product": "riverbed", "segment": "seg-labs-newsletter", "persona": "persona-community-organiser", "kind_hint": "ambiguous",
     "goal": "A thought piece that also mentions the 1.8 release. Position streaming-first pipelines against batch-only ones. Some stakeholders want it to read as an announcement, others as an essay; the brief leaves that open.",
     "key_messages": ["Batch gives you throughput; streaming gives you freshness", "Checkpointed state makes streaming as safe to restart as batch", "Our internal tests show riverbed beats the leading batch framework on end-to-end latency (numbers not yet published)"],
     "cta": "Read the essay; try 1.8 if you want", "send_window": "2026-10-28", "notes": "Marketing wants the comparison to be punchy and name the alternatives. Legal has not seen the unpublished numbers. Deadline is soft."},
    {"id": "brief-012", "campaign_id": "camp-2026-10-012", "title": "Tessera Labs monthly digest: three tutorials on streaming", "product": "riverbed", "segment": "seg-labs-newsletter", "persona": "persona-community-organiser", "kind_hint": "nurture",
     "goal": "Monthly nurture digest. Three tutorials, no release. The newsletter team schedules and sends it; we only draft, check and log.",
     "key_messages": ["Tutorial: your first riverbed pipeline", "Tutorial: inspecting checkpoints", "Tutorial: schema evolution with mooring"],
     "cta": "Pick a tutorial and try it this week", "send_window": "2026-10-31", "notes": "Nurture, not a launch. No scheduling from our side."},
    {"id": "brief-013", "campaign_id": "camp-2026-11-001", "title": "riverbed 2.0 release", "product": "riverbed", "segment": "seg-python-stream-devs", "persona": "persona-stream-dev", "kind_hint": "launch",
     "goal": "Announce 2.0: a new connector API, pipeline graphs you can inspect from Python, and the exactly-once preview.",
     "key_messages": ["New connector API: write a source or sink in one class", "Inspect the pipeline graph from Python", "Exactly-once preview for Kafka sinks"],
     "cta": "Upgrade to 2.0 and try the connector quickstart", "send_window": "2026-11-04", "notes": "This is the brief for the live demo. Developer tone, Labs disclaimer."},
]

BRAND_GUIDE = {
    "id": "brand-tessera-labs",
    "name": "Tessera Labs email voice",
    "voice_rules": [
        "Lead with what the developer can do now, not with adjectives",
        "One idea per sentence; no exclamation marks; no emoji in subject lines",
        "Say 'Tessera Labs project', 'experimental', 'community-supported' where relevant",
        "Prefer code and concrete nouns to superlatives",
        "Always include exactly one clear call to action",
    ],
    "banned_claims": [
        "production-ready",
        "enterprise-grade",
        "officially supported",
        "SLA",
        "guaranteed",
        "100%",
        "best-in-class",
        "unlimited",
        "naming a competitor product",
        "unpublished benchmark numbers",
    ],
    "required_disclaimer": DISCLAIMER,
    "subject_line_rules": ["Under 60 characters", "No ALL CAPS words", "No 'free', 'act now', 'last chance'"],
}

CHANNELS = [{"id": "channel-email", "name": "Email", "description": "Tessera Labs email programme, sent through the marketing automation platform"}]


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    products = database(
        "db-products", "Products",
        {"Name": "title", "Tagline": "rich_text", "Repo": "url", "Docs": "url", "Version": "rich_text", "Approved claims": "rich_text", "Disclaimer": "rich_text"},
        [page(p["id"], {
            "Name": title(p["name"]), "Tagline": rich(p["tagline"]), "Repo": {"type": "url", "url": p["repo"]},
            "Docs": {"type": "url", "url": p["docs"]}, "Version": rich(p["version"]),
            "Approved claims": {"type": "rich_text", "rich_text": [{"type": "text", "plain_text": c, "text": {"content": c}} for c in p["claims"]]},
            "Disclaimer": rich(DISCLAIMER),
        }) for p in PRODUCTS],
    )

    personas = database(
        "db-personas", "Personas",
        {"Name": "title", "Role": "rich_text", "Cares about": "rich_text", "Reads": "rich_text", "Turn-offs": "rich_text", "Preferred tone": "rich_text"},
        [page(p["id"], {
            "Name": title(p["name"]), "Role": rich(p["role"]), "Cares about": rich(p["cares_about"]),
            "Reads": rich(p["reads"]), "Turn-offs": rich(p["turn_offs"]), "Preferred tone": rich(p["preferred_tone"]),
        }) for p in PERSONAS],
    )

    segments = database(
        "db-audience-segments", "Audience segments",
        {"Name": "title", "Product": "select", "Persona": "relation", "Size": "number", "Description": "rich_text"},
        [page(s["id"], {
            "Name": title(s["name"]), "Product": select(s["product"]), "Persona": relation([s["persona"]]),
            "Size": number(s["size"]), "Description": rich(s["description"]),
        }) for s in SEGMENTS],
    )

    briefs = database(
        "db-campaign-briefs", "Campaign briefs",
        {"Name": "title", "Campaign ID": "rich_text", "Product": "select", "Segment": "relation", "Persona": "relation", "Channel": "select",
         "Goal": "rich_text", "Key messages": "rich_text", "CTA": "rich_text", "Send window": "date", "Notes": "rich_text", "Status": "select"},
        [page(b["id"], {
            "Name": title(b["title"]), "Campaign ID": rich(b["campaign_id"]), "Product": select(b["product"]),
            "Segment": relation([b["segment"]]), "Persona": relation([b["persona"]]), "Channel": select("Email"),
            "Goal": rich(b["goal"]),
            "Key messages": {"type": "rich_text", "rich_text": [{"type": "text", "plain_text": m, "text": {"content": m}} for m in b["key_messages"]]},
            "CTA": rich(b["cta"]), "Send window": date(b["send_window"]), "Notes": rich(b["notes"]), "Status": select("Ready"),
        }) for b in BRIEFS],
    )

    brand = database(
        "db-brand-guide", "Brand guide",
        {"Name": "title", "Voice rules": "rich_text", "Banned claims": "multi_select", "Required disclaimer": "rich_text", "Subject line rules": "rich_text"},
        [page(BRAND_GUIDE["id"], {
            "Name": title(BRAND_GUIDE["name"]),
            "Voice rules": {"type": "rich_text", "rich_text": [{"type": "text", "plain_text": r, "text": {"content": r}} for r in BRAND_GUIDE["voice_rules"]]},
            "Banned claims": multi(BRAND_GUIDE["banned_claims"]),
            "Required disclaimer": rich(BRAND_GUIDE["required_disclaimer"]),
            "Subject line rules": {"type": "rich_text", "rich_text": [{"type": "text", "plain_text": r, "text": {"content": r}} for r in BRAND_GUIDE["subject_line_rules"]]},
        })],
    )

    channels = database(
        "db-channels", "Channels", {"Name": "title", "Description": "rich_text"},
        [page(c["id"], {"Name": title(c["name"]), "Description": rich(c["description"])}) for c in CHANNELS],
    )

    log = database(
        "db-campaign-log", "Campaign log",
        {"Name": "title", "Campaign ID": "rich_text", "Draft ID": "rich_text", "Summary": "rich_text", "Logged at": "date", "Scheduled": "checkbox"},
        [],
    )

    for name, db in {
        "products": products, "personas": personas, "audience_segments": segments, "campaign_briefs": briefs,
        "brand_guide": brand, "channels": channels, "campaign_log": log,
    }.items():
        (OUT / f"{name}.json").write_text(json.dumps(db, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(BRIEFS)} briefs, {len(PRODUCTS)} products, {len(PERSONAS)} personas, {len(SEGMENTS)} segments to {OUT}")


if __name__ == "__main__":
    build()
