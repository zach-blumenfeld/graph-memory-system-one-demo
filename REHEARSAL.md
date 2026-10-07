# Rehearsal script

Timings are from the Tessera Labs run on 2026-10-07 (Fable as the System Two model, Jev 1.13.0,
NAMS 1.1.0, workspace `system-one-demo` in external mode on Aura). Budget about 18 minutes of demo inside the talk; everything live has a replay.

## Before the talk (10 min, once)

1. `uv run pmm doctor` — all green or do not go on stage. It makes one live Jev call (~0.4 s).
2. The workspace `system-one-demo` is already in external mode on Aura `b919e0ff`, so Neo4j
   Browser against that database shows everything in `queries.md`.
3. Open three terminals in the repo: one for `claude`, one for `pmm` commands, one tailing
   `.run/recorder.log`. Open the NAMS console query view (or Browser) with `queries.md` §1 pasted.
4. `rm -rf .run/drafts .run/notion` so draft ids start at `-01` again (optional, cosmetic).

## Beat 1: Memory (2 min)

- Run `queries.md` §1 (the ontology graph). Point at: 13 campaigns, 4 products, the claims, the
  brand guideline every campaign is `CONSTRAINED_BY`.
- Say: this is the long-term layer under a custom PMM ontology; the SDK wrote it through NAMS;
  entity resolution already flagged three look-alike campaigns (`SAME_AS`).

## Beat 2: Traces (5 min, live)

- In the `claude` terminal: `New brief in Notion: brief-001, "riverbed 1.8: checkpointed state for
  every pipeline". Launch the email blast to the Python streaming developers, scheduled for
  2026-10-14 09:00 UTC.` (Project skill is installed, so Claude may load it; for a pure Stage 3
  feel, run `PMM_RECORD=1 claude --disallowedTools Skill` or temporarily move `.claude/skills/`.)
- Expect ~90–120 s: brief → classify → segments → draft → compliance **fails on the disclaimer** →
  redraft → passes → scoring → schedule → log. Narrate the `review_required` items Claude explains.
- While it runs, tail `.run/recorder.log` and run `queries.md` §2 (every run as a tool path) to show
  the new conversation appearing. Replay if the network is bad: `pmm traces show run-01`.

## Beat 3: Distillation (3 min)

- `pmm skill status` shows the published skill, the in-review workspace-scope twin and the rejected
  trial. Open `.claude/skills/launch-email-blast/SKILL.md`: 8 steps, each bound to a tool, inputs
  and outputs are our Pydantic fields, `submit_draft` has `branch: retry`.
- Run `queries.md` §3 (skill step → grounding → recorded step). 231 evidence ids, all resolve.
- Live option (~45 s): `pmm distill --scope run-03 --name-hint launch-email-blast-live
  --no-install --no-workspace-demo` to watch `queued → synthesizing → packaging → succeeded`.
  Reject it afterwards with `pmm skill review <id> --reject`.
- Say what did not happen: the multi-procedure gate did not fire even at workspace scope; the
  nurture and anti-pattern runs got folded into `parallel` branches instead. Show the two skills
  side by side if asked.

## Beat 4: System One (3 min)

- `queries.md` §4: pull Jev's typed answers out of `ToolCall.output`. Points to make:
  - `classify_brief`: launch with confidence 0.54–1.0 (the benchmark write-up brief was the
    uncertain one), urgency 2/5, `needs_legal_review` 0.16–0.58 on normal briefs and 0.97 on the
    engineered brief-011.
  - `check_brand_compliance`: 11 failed, 13 passed; the first draft failed `has_labs_disclaimer`
    in 11 of 12 runs, the tool returns the exact disclaimer, second drafts pass. The decision
    model told the generative model what was missing.
  - Thresholds: noul margin 0.15, min confidence 0.6 (AIP defaults). `review_required` is the
    escalation contract.
- Show `src/pmm/decisions.py` briefly: three question sets, no fallback.

## Beat 5: Run it (4 min)

- Fresh `claude` session: `New brief in Notion: "riverbed 2.0 release". Launch the email
  blast.` Claude loads `launch-email-blast` (watch for the `Skill` call) and runs the 8 tools.
  ~2 min with the default model.
- Headless twin to compare: `pmm run-skill --brief brief-013 --model sonnet` (~45 s). In the build,
  Sonnet stopped before scheduling and asked a human about the legal-review flag; the default
  model scheduled, logged, and then raised the same flag for a human before the send date. Show `reports/comparison.md` and `queries.md` §5.
- Close with drift: `pmm skill explain <skill-id>` (provenance + drift) and the governance
  duplicates. Then the research pointers (AIP paper, SkillsBench, TypeSafe calibration).

## If something breaks

| symptom | do |
|---|---|
| `pmm doctor` fails on Jev | nothing works by design; check `TYPESAFE_API_KEY`, retry once, otherwise replay from checkpoints and say so |
| NAMS 503 `workspace_not_provisioned` | `MEMORY_WORKSPACE_ID` points at a pending workspace; use the active one or provision in the console |
| Claude run goes off script | that is the point of recording; `pmm traces show <run>` afterwards. The guard in `schedule_send` cannot be bypassed |
| No network | `make selftest` still runs; show `checkpoints/03-traces/run-01.json` and the committed `SKILL.md` |
