# Distilling agent knowledge into System One workflows with graph memory


A product-marketing agent (Claude Code) runs a "launch email blast" workflow against a simulated
Notion workspace through eight typed MCP tools. Every tool call is recorded by the open-source
[`neo4j-agent-memory`](https://github.com/neo4j-labs/agent-memory) SDK into a Neo4j Agent Memory
Service (NAMS) workspace. NAMS distils those traces into a provenance-grounded Agent Skill whose
steps are bound to the tools that were actually called. The decision-shaped steps inside those
tools (classify the brief, check brand compliance, score subject lines) are answered by TypeSafe's
Jev, a System One model that returns typed answers with calibrated confidence. A fresh agent then
loads the skill and runs the campaign end to end.

PLAN.md is the design contract. BUILD-LOG.md is what actually happened, step by step, including
what is blocked and why. REHEARSAL.md is the beat-by-beat script with timings.

## State after the build (2026-10-07, Tessera Labs fixture)

| stage | state |
|---|---|
| 0 env | `pmm doctor` green. Workspace `system-one-demo` in external mode on Aura `b919e0ff` (switched once in the NAMS console; API keys cannot change database mode) |
| 1 fixture + ontology | PMM ontology active; 42 entities, 88 relationships imported from the fictional Tessera Labs workspace; `verify stage1` OK |
| 2 server | 8 tools, 30 tests, `make selftest` green |
| 3 traces | 12 runs recorded headlessly, exported to `checkpoints/03-traces/`; `verify stage3` OK (8/8 clean paths, anti-pattern guard tripped once) |
| 4 skill | distilled from the 8 clean conversations: grounding 1.0, coverage 1.0, 8 tool-bound steps, 231 evidence ids all resolve; published and installed; `verify stage4` OK |
| 5 run | default model completed the launch through the skill (10 calls, 84 s, $1.11); Sonnet stopped before scheduling and asked a human about the legal-review flag (8 calls, 46 s, $0.21); `verify stage5` OK; `reports/comparison.md` |
| 6 AIP | not attempted (stretch) |

## The five beats

1. **Memory.** Three memory layers in one graph: the PMM ontology (campaigns, products, personas,
   segments, claims, brand guide), the conversations, and the reasoning traces. `queries.md` §1.
2. **Traces.** Claude Code does the work; the graph fills with `AgentStep` and `ToolCall` nodes
   whose inputs and outputs are the tools' Pydantic schemas, including Jev's typed answers. §2.
3. **Distillation.** NAMS lifts one procedure out of the traces, grounds every claim in a node id,
   gates it (grounding ≥ 0.9, coverage ≥ 0.6, coherence, PII, spec) and packages `SKILL.md`. §3.
4. **System One.** The tools the skill binds to are where Jev lives: typed questions, probabilities,
   thresholds (noul margin 0.15, min confidence 0.6), explicit escalation via `review_required`. §4.
5. **Run it.** A new Claude Code session loads `.claude/skills/launch-email-blast/` and executes the
   procedure against the same MCP server; the run lands in the same graph. §5 and `reports/`.

## Quick start

Requirements: [uv](https://docs.astral.sh/uv/), Claude Code 2.1.x, Python 3.12+ (3.14 used here).

```bash
cp .env.example .env            # fill MEMORY_API_KEY, MEMORY_WORKSPACE_ID, NEO4J_*, TYPESAFE_API_KEY
make sync                       # uv sync --all-groups
make selftest                   # no network: pytest + in-process MCP server with fakes
uv run pmm doctor               # every key and service, one live Jev round trip
```

Then either the full pipeline or a checkpoint:

```bash
make demo                       # stages 0..5: attach, ontology, import, record 12 runs, distill, run skill, report
make replay-from STAGE=5        # fresh clone: run the committed skill against the MCP server, recording off
make replay-from STAGE=3        # fresh workspace: replay the committed traces (no Claude), then distil
```

Interactive, on stage:

```bash
claude                          # project picks up .mcp.json (pmm-tools) and .claude/skills/launch-email-blast
> New brief in Notion: "riverbed 2.0 release". Launch the email blast.
```

Hooks in `.claude/settings.json` record the prompt and the final answer; the MCP server records
every tool call. Set `PMM_RECORD=0` to run without recording.

## What is where

| Path | What |
|---|---|
| `src/pmm/mcp_server.py` | The eight tools. `pmm-tools` on stdio; `pmm-tools --selftest` in-process with fakes |
| `src/pmm/decisions.py` | TypeSafe Jev question sets and the review thresholds. No heuristic fallback |
| `src/pmm/recorder.py` | SDK trace recording (`start_trace` / `add_step` / `record_tool_call`) with an ordered queue |
| `src/pmm/hooks.py` | `pmm-hook user-prompt-submit\|post-tool-use\|stop` |
| `src/pmm/record.py` | Headless `claude -p` runs, trace export, replay |
| `src/pmm/nams_skills.py` | Stage 4 over REST: generate, poll, review, publish, download, install |
| `src/pmm/cli.py` | `pmm doctor \| workspace \| ontology \| notion \| record \| traces \| distill \| skill \| run-skill \| verify \| report \| replay-from \| cypher` |
| `data/notion/` | Notion-shaped fixture (13 briefs, 4 products, 4 personas, 6 segments, brand guide, campaign log). Regenerate with `make fixture` |
| `ontology/pmm.json` | The PMM ontology NAMS validates entities against |
| `prompts/runs.yaml` | The 12-run matrix: 8 clean, 2 anti-pattern, 1 escalation, 1 nurture |
| `checkpoints/` | Per-stage artifacts: env, ontology, import map, 12 exported traces, the skill zip and run metadata, the skill run |
| `.claude/skills/launch-email-blast/` | The distilled skill, unmodified from the NAMS download |
| `queries.md` | Cypher for each beat |
| `reports/comparison.md` | Stage 3 vs Stage 5 tool counts, turns, wall clock, cost |

## The tools

| # | Tool | Decision model |
|---|---|---|
| 1 | `get_campaign_brief(brief_id)` | none |
| 2 | `get_audience_segments(product)` | none |
| 3 | `classify_brief(brief_id)` | Choice `campaign_type`, Score `urgency` 1–5, Noul `needs_legal_review` |
| 4 | `submit_draft(campaign_id, subject_lines[3], body_md, segment_id)` | none (Claude writes it) |
| 5 | `check_brand_compliance(draft_id)` | Nouls `on_brand_voice`, `no_unapproved_claims`, `has_clear_cta`, `has_labs_disclaimer` |
| 6 | `score_subject_lines(draft_id)` | Score per line on clarity, curiosity, spam risk |
| 7 | `schedule_send(...)` | none; fails with status `failure` if compliance has not passed |
| 8 | `log_campaign(campaign_id, draft_id, summary)` | none |

Every Jev-backed tool returns the typed answer (choice / score / noul, probabilities, confidence)
and a `review_required` list computed with AIP's defaults. When it is non-empty the tool says so
and Claude decides; that escalation is itself recorded.

## Numbers from the build

| group | runs | avg tool calls | avg turns | avg wall | avg cost |
|---|---|---|---|---|---|
| Stage 3 clean launches, no skill (Fable) | 8 | 12.1 | 13.8 | 96 s | $0.64 |
| Stage 5 with the distilled skill (1 Fable, 2 Sonnet) | 3 | 9.3 | 15.3 | 70 s | $0.53 |

Jev answered every decision in under half a second. 33 compliance checks: 18 failed (every first
draft, on the Labs disclaimer), 15 passed (every second draft). Full tables in
`reports/comparison.md` and BUILD-LOG.md.

## Versions

neo4j-agent-memory 0.6.0 · mcp 2.3.0 · typesafe-sdk 0.7.2 (Jev 1.13.0) · NAMS API 1.1.0 ·
Claude Code 2.1.292 · Python 3.14.5 · uv 0.11.14. `uv.lock` is committed.

## Pointers

- AIP paper: *AIP: A Graph Representation for Learning and Governing Agent Skills*, VLDB 2026
  workshop, arXiv 2606.04781.
- NAMS skills: [From Agent Memory to Portable Skills](https://neo4j.com/blog/genai/from-agent-memory-to-portable-skills/)
  and the [Skills Quickstart (Preview)](https://neo4j.com/labs/agent-memory/tutorials/skills-quickstart/).
- TypeSafe: [System One](https://docs.typesafe.ai/concepts/system-one), Choice / Score / Noul.

Neo4j Labs projects are experimental and community-supported. NAMS is early access: no SLA or
pricing claims are made here.
