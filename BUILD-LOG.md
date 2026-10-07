# Build log

What actually happened, in order. The first unattended build (2026-10-06, 23:02 to 00:14) used a
fixture built around real open-source product names; that fixture was replaced the next morning
with the fictional **Tessera Labs** (four invented projects: riverbed, tidewatch, mooring, ballast)
and every data-producing stage was re-run on a fresh workspace. The numbers below are from the
re-run. The git history was squashed so the old fixture is not in the repo's past.

## Environment

- Workspace `system-one-demo` (NAMS 1.1.0), **external mode on Aura `b919e0ff`**, switched in the
  NAMS console: `PUT /v1/workspace/database` and `/provision` return `403 user token required`
  for API keys, so that step is console-only. `pmm workspace attach` reports the mode and refuses
  if the database already holds nodes.
- Admin API keys are account-level; the SDK sends `MEMORY_WORKSPACE_ID` as `X-Workspace-Id`.
- `pmm doctor`: keys present, workspace active (external), Jev `jev-1.13.0` answers in ~0.5 s,
  Claude Code 2.1.292, `pmm-tools` selftest OK (8 tools, 9 recorded calls, 1 deliberate failure).
- TypeSafe is required. No fallback anywhere; a missing key is an error (`decisions.py`).

## Things learned about the SDK and NAMS while building

- SDK 0.6.0 facts that changed the design: on the NAMS backend `long_term.add_relationship` and `add_fact` raise `NotSupportedError`; relationships go through REST `POST /v1/relationships(/bulk)` instead. `short_term.add_message` drops metadata. `reasoning.complete_trace` is client-side only. `MemoryClient.connect()` probes `GET /v1/conversations`, so the SDK cannot connect until the workspace is provisioned.
- Graph shape observed: entities are `:Entity` nodes with the class in `type` (no per-class labels), NAMS added `normName`, `canonicalName`, `embedding`, `nameEmbedding`, `ontologyVersionId`. NAMS entity resolution added 3 `SAME_AS` pending-review pairs between similarly named campaigns; nothing merged.
- Checked that a nested headless `claude -p ... --output-format json` works from inside this session (haiku, 1 s): the JSON carries `session_id`, `total_cost_usd`, `duration_api_ms`, `modelUsage`, `permission_denials`, `result`.
- Recorder smoke test (SDK `start_trace` / `add_step` / `record_tool_call` on a throwaway conversation): both calls landed as `AgentStep`+`ToolCall` with the failure status preserved; `GET /v1/reasoning/trace/{id}` returns `steps` and `toolCalls` as two flat lists joined by `stepId` (not nested). The smoke conversation was deleted afterwards.
- On NAMS `session_id` is the server-issued conversation UUID; `create_conversation` first.
- Each process (MCP server, each hook invocation, the CLI) does its own `start_trace`; the
  conversation id is shared through `.run/sessions/<claude_session_id>.json`.
- Each tool waits up to 8 s (`PMM_RECORD_SETTLE_SECONDS`) for its record to land so the last
  write of a session cannot race process exit; a slow NAMS never fails a tool.
- Headless runs pass `--tools ""` so the agent can only act through `pmm-tools` (otherwise
  `--permission-mode dontAsk` lets it read the fixture files directly).
- `POST /v1/skills/generate` returns `{runId, status: queued}`; the run walks
  `queued → synthesizing → packaging → succeeded` in about 30 s with `groundingScore`,
  `coverageScore`, `skillId`, `failCode`, `suggestSplitJson`; there is no `outcome` field, `pmm`
  maps `succeeded`+skillId → Created.
- The download zip holds `<name>/SKILL.md`, `references/{domain-model,exemplars,procedures,
  troubleshooting,procedure.schema.json}`, `provenance.json`.

## Stage 1: fixture and ontology

- `tools/make_fixture.py` writes `data/notion/`: 13 briefs, 4 products with approved claims,
  4 personas, 6 segments, a brand guide (voice rules, banned claims, required disclaimer, subject
  line rules), one channel, an empty campaign log. All invented.
- `pmm ontology apply` created and activated ontology `pmm` (Campaign, Persona, Product,
  AudienceSegment, Channel, BrandGuideline, Claim).
- `pmm notion import`: 42 entities, 88 relationships; NAMS entity resolution proposed 3 `SAME_AS`
  pairs between similarly named campaigns, none merged. `verify stage1` OK.

## Stage 3: the 12-run matrix (headless Claude Code, default model = Fable)

| run | kind | calls | turns | wall | cost | path |
|---|---|---|---|---|---|---|
| run-01..08 | clean | 11 each | 12 | 70–148 s | $0.43–0.60 | brief > classify > segments > draft > comply > score > draft > comply > score > schedule > log |
| run-09 | anti-pattern | 8 | 9 | 60 s | $0.34 | brief > draft > **schedule_send fails** (guard) > comply > draft > comply > schedule > log |
| run-10 | anti-pattern | 8 | 9 | 102 s | $0.34 | the model ran the compliance check anyway; guard never needed |
| run-11 | escalation | 11 | 12 | 223 s | $0.61 | clean path; `needs_legal_review` 0.97, three subject-line reviews |
| run-12 | nurture | 8 | 9 | 60 s | $0.33 | brief > segments > classify > draft > comply > draft > comply > log (no scoring, no schedule) |

All 12 exited 0. Traces exported to `checkpoints/03-traces/`, replayable with `pmm traces replay`.
`verify stage3` OK.

What the decisions looked like (Jev, from `ToolCall.output`):

- `classify_brief`: every launch brief → `launch` (confidence 0.54–1.0; run-06, the benchmark
  write-up, was the uncertain one and was flagged for review), urgency level 2 (confidence
  0.56–0.89), `needs_legal_review` 0.16–0.58 on ordinary briefs and 0.97 on the engineered
  brief-011. 7 of 10 classifications carried at least one `review_required` item.
- `check_brand_compliance`: 24 calls, 13 passed, 11 failed. The first draft failed in 11 of 12
  runs, 11 times on `has_labs_disclaimer` (the agent cannot see the brand guide before the first
  check; the tool returns the exact disclaimer and the second draft passed every time). So every
  clean trace contains one draft → check → redraft loop.
- `score_subject_lines`: 1–5 review items per call (per-line clarity, curiosity or spam scores
  under 0.6 confidence); the ranked pick was kept in every run.
- Anti-pattern: with the house rules removed from the prompt, run-09 skipped the check, hit the
  `schedule_send` guard (recorded as a failed tool call), then recovered; run-10's model refused
  to skip the check even under pressure.

## Stage 4: distillation (scripted over REST, auto-approved)

- Clean scope (the 8 clean conversations): **Created**, grounding 1.0, coverage 1.0, PII clean,
  spec lint pass. Published as `launch-email-blast` and installed into
  `.claude/skills/launch-email-blast/` (SKILL.md, references, provenance.json). 8 tool-bound
  steps; `submit_draft` carries `branch: retry` and `classify_brief` `branch: parallel` because
  the recorded order of classify and segments varied. 6 claims, 231 distinct evidence ids, all
  resolve in the workspace (`verify stage4` OK).
- Workspace scope (all 12 conversations, the planned "withheld" demo): also **Created**, grounding
  1.0, coverage 1.0. The multi-procedure gate did not fire; left in review state, unpublished.
  The on-stage beat is therefore a side-by-side of the two skills, not a withhold.
- Reviewed `approve` with feedback "Approved unattended by pmm distill"; provenance summary is in
  `checkpoints/04-skill/`.

## Stage 5: running the skill

- Default model (Fable): completed the launch through the skill, 10 calls, 16 turns, 84 s, $1.11.
  Scheduled and logged, then flagged the legal-review verdict (0.97 noul on the exactly-once
  claim) for a human before the send date.
- Sonnet: 8 calls, 13 turns, 46 s, $0.21. Passed compliance on the second draft, scored the
  subject lines, then **stopped before scheduling and asked for a human decision** on the
  legal-review flag. Honest result: the cheaper System Two model escalates where the expensive
  one decides.
- `verify stage5` OK. `reports/comparison.md`: clean Stage 3 runs average 11.0 calls / 94 s /
  $0.48; skill runs average 9.0 calls / 65 s.

## Status

Works end to end on `system-one-demo` (external mode on Aura `b919e0ff`): `make selftest`,
`pmm doctor`, stages 1–5 with their verifiers, the published skill, the report. Neo4j Browser
against the Aura database shows everything in `queries.md`. Stage 6 (AIP compile) not attempted.

How to run: see README.md. Full pipeline is `make demo` (all keys, ~30 min, ~$8 of Claude usage);
`make replay-from STAGE=5` runs the committed skill against the MCP server.
