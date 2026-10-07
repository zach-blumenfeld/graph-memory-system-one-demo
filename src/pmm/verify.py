"""Per-stage verifiers against the live workspace (REST /v1/query)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pmm.env import CHECKPOINTS, SKILL_DIR
from pmm.mcp_server import TOOL_NAMES
from pmm.nams_rest import NamsRest

EXPECTED_ENTITY_COUNTS = {"Campaign": 13, "Product": 4, "Persona": 4, "AudienceSegment": 6, "Channel": 1, "BrandGuideline": 1, "Claim": 13}
CLEAN_PATH = TOOL_NAMES


class VerifyFailure(AssertionError):
    pass


def _check(cond: bool, msg: str, failures: list[str]) -> None:
    if not cond:
        failures.append(msg)


def stage1(nams: NamsRest, log=print) -> list[str]:
    failures: list[str] = []
    rows = nams.cypher("MATCH (e:Entity) RETURN e.type AS type, count(*) AS n ORDER BY type")
    counts = {r["type"]: r["n"] for r in rows}
    log(f"entity counts: {json.dumps(counts)}")
    for t, want in EXPECTED_ENTITY_COUNTS.items():
        got = counts.get(t) or counts.get(t.lower()) or counts.get(t.upper()) or 0
        _check(got >= want, f"expected at least {want} {t} entities, found {got}", failures)
    rels = nams.cypher("MATCH (:Entity)-[r]->(:Entity) RETURN type(r) AS type, count(*) AS n ORDER BY type")
    relc = {r["type"]: r["n"] for r in rels}
    log(f"relationship counts: {json.dumps(relc)}")
    for t in ("TARGETS", "PROMOTES", "USES_CHANNEL", "CONSTRAINED_BY", "ASSERTS"):
        _check(relc.get(t, 0) > 0, f"no {t} relationships", failures)
    paths = nams.cypher(
        "MATCH (c:Entity {type:'Campaign'})-[:PROMOTES]->(p:Entity {type:'Product'})-[:ASSERTS]->(cl:Entity {type:'Claim'}) "
        "RETURN count(DISTINCT c) AS campaigns, count(DISTINCT cl) AS claims")
    log(f"campaign->product->claim reach: {paths}")
    _check(bool(paths) and paths[0]["campaigns"] >= 13, "not every campaign reaches an approved claim through its product", failures)
    return failures


def tool_paths(nams: NamsRest) -> list[dict[str, Any]]:
    return nams.cypher(
        "MATCH (c:Conversation)-[:HAS_STEP]->(s:AgentStep)-[:USED_TOOL]->(t:ToolCall) "
        "WITH c, s, t ORDER BY s.createdAt, t.createdAt "
        "WITH c, collect(t.toolName + CASE t.status WHEN 'failure' THEN '!' ELSE '' END) AS path "
        "RETURN c.id AS conversation_id, c.metadata AS metadata, size(path) AS steps, path ORDER BY c.createdAt")


def clean_path_problems(path: list[str]) -> list[str]:
    """The 8-tool launch path: every tool used successfully, brief first, log last, and the
    guard-rail order draft -> compliance -> scoring -> schedule. Redraft loops are allowed."""
    ok = [p for p in path if not p.endswith("!")]
    problems: list[str] = []
    missing = [t for t in CLEAN_PATH if t not in ok]
    if missing:
        problems.append(f"never called {missing}")
    extra = sorted({t for t in ok if t not in CLEAN_PATH})
    if extra:
        problems.append(f"unknown tools {extra}")
    if any(p.endswith("!") for p in path):
        problems.append(f"failed calls {[p for p in path if p.endswith('!')]}")
    if ok and ok[0] != "get_campaign_brief":
        problems.append(f"first call was {ok[0]}")
    if ok and ok[-1] != "log_campaign":
        problems.append(f"last call was {ok[-1]}")

    def last(t: str) -> int:
        return max((i for i, p in enumerate(ok) if p == t), default=-1)

    def first(t: str) -> int:
        return next((i for i, p in enumerate(ok) if p == t), 10**6)

    if not (first("submit_draft") < last("check_brand_compliance") < first("schedule_send")):
        problems.append("compliance did not sit between the draft and the schedule")
    if not (last("score_subject_lines") < first("schedule_send")):
        problems.append("subject lines were not scored before scheduling")
    return problems


def stage3(nams: NamsRest, log=print) -> list[str]:
    failures: list[str] = []
    runs_file = CHECKPOINTS / "03-runs.json"
    _check(runs_file.exists(), "checkpoints/03-runs.json missing (run `pmm record --all`)", failures)
    if failures:
        return failures
    runs = json.loads(runs_file.read_text())["runs"]
    by_cid = {r["conversation_id"]: r for r in tool_paths(nams)}
    clean_ok = 0
    anti_total = anti_tripped = 0
    for run_id, r in runs.items():
        cid = r["conversation_id"]
        row = by_cid.get(cid)
        if row is None:
            failures.append(f"{run_id}: conversation {cid} has no recorded tool calls")
            continue
        path = row["path"]
        log(f"{run_id} ({r['kind']}): {len(path)} calls: {' > '.join(path)}")
        if r["kind"] == "clean":
            problems = clean_path_problems(path)
            if not problems:
                clean_ok += 1
            else:
                failures.append(f"{run_id}: clean run deviates from the 8-tool path: {'; '.join(problems)}")
        elif r["kind"] == "anti-pattern":
            anti_total += 1
            if "schedule_send!" in path:
                anti_tripped += 1
            _check("schedule_send" in path and "check_brand_compliance" in path, f"{run_id}: anti-pattern run never recovered (compliance then a successful schedule_send)", failures)
    log(f"clean runs matching the 8-tool path: {clean_ok}/{sum(1 for r in runs.values() if r['kind'] == 'clean')}")
    if anti_total:
        log(f"anti-pattern runs that tripped the schedule_send guard: {anti_tripped}/{anti_total}")
        _check(anti_tripped >= 1, "no anti-pattern run produced a failed schedule_send; the guard was never exercised", failures)
    return failures


EVIDENCE_RE = re.compile(r"_evidence:\s*([0-9a-fA-F\-,\s]+)_")


def evidence_ids(skill_dir: Path = SKILL_DIR) -> list[str]:
    ids: set[str] = set()
    for md in skill_dir.rglob("*.md"):
        for m in EVIDENCE_RE.finditer(md.read_text()):
            for part in m.group(1).split(","):
                part = part.strip()
                if part:
                    ids.add(part)
    prov = skill_dir / "provenance.json"
    if prov.exists():
        data = json.loads(prov.read_text())
        for claim in data.get("claims", []):
            ids.update(claim.get("groundedIn", []))
        for step in data.get("steps", []) or []:
            ids.update(step.get("groundedIn", []))
    return sorted(ids)


def bound_tools(skill_dir: Path = SKILL_DIR) -> list[str]:
    text = (skill_dir / "SKILL.md").read_text()
    return sorted(set(re.findall(r"_\(tool: ([a-zA-Z0-9_]+)\)_", text)))


def stage4(nams: NamsRest, log=print, skill_dir: Path = SKILL_DIR) -> list[str]:
    failures: list[str] = []
    _check((skill_dir / "SKILL.md").exists(), f"{skill_dir}/SKILL.md missing (run `pmm distill --install`)", failures)
    if failures:
        return failures
    ids = evidence_ids(skill_dir)
    log(f"{len(ids)} evidence ids referenced by the skill package")
    found = {r["id"] for r in nams.cypher("MATCH (n) WHERE n.id IN $ids RETURN n.id AS id", {"ids": ids})}
    missing = [i for i in ids if i not in found]
    _check(not missing, f"{len(missing)} evidence ids do not resolve to workspace nodes: {missing[:5]}", failures)
    kinds = nams.cypher("MATCH (n) WHERE n.id IN $ids RETURN labels(n)[0] AS label, count(*) AS n ORDER BY label", {"ids": ids})
    log(f"evidence node labels: {kinds}")
    tools = bound_tools(skill_dir)
    log(f"bound tools: {tools}")
    unknown = [t for t in tools if t not in TOOL_NAMES]
    _check(not unknown, f"skill binds to tools the server does not have: {unknown}", failures)
    _check(len(tools) >= 3, f"skill binds fewer than 3 tools ({len(tools)}); distillation degraded to prose?", failures)
    return failures


def stage5(nams: NamsRest, log=print) -> list[str]:
    """Skill runs: every run used the tools through the skill; at least one completed the launch
    (schedule + log). Runs that stop at a `review_required` escalation are legitimate and reported."""
    failures: list[str] = []
    ck = CHECKPOINTS / "05-skill-run.json"
    _check(ck.exists(), "checkpoints/05-skill-run.json missing (run `pmm run-skill`)", failures)
    if failures:
        return failures
    data = json.loads(ck.read_text())
    by_cid = {r["conversation_id"]: r for r in tool_paths(nams)}
    completed = 0
    for r in data["runs"]:
        row = by_cid.get(r["conversation_id"])
        if row is None:
            failures.append(f"{r['run_id']}: conversation {r['conversation_id']} has no recorded tool calls")
            continue
        path = row["path"]
        done = "schedule_send" in path and "log_campaign" in path
        completed += done
        log(f"{r['run_id']} ({r.get('model')}): {len(path)} calls, {'completed' if done else 'stopped before scheduling (escalation)'}: {' > '.join(path)}")
        _check(path and path[0] == "get_campaign_brief", f"{r['run_id']}: did not start from the brief", failures)
        _check("check_brand_compliance" in path, f"{r['run_id']}: never ran the brand check", failures)
    _check(completed >= 1, "no skill run completed the launch (schedule_send + log_campaign)", failures)
    log(f"skill runs completed: {completed}/{len(data['runs'])}")
    return failures
