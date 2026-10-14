# loan-demo progress log

Resume rule: re-read `PLAN.md` and this file; continue from the last entry. Never redo a step whose
checkpoint exists and verifies.

## 2026-10-13 — step 0: scaffold

Done:
- `pyproject.toml` (package `loan`, scripts `loan`, `loan-hook`, same deps as aip-demo), `.env.example`,
  `.gitignore`, `.claude/settings.json` (three hooks → `loan-hook`), `Makefile` (targets: sync doctor
  fixture import reset record export author serve publish verify clean fresh).
- `src/loan/env.py` (paths: `data/bank`, `sop_assess_loan.md`, `policy.md`, `.run/rationales`,
  `LOAN_ROOT`, `LOAN_RECORD`), `memory.py` (copied), `hooks.py` (copied; `APP-\d{4}`, `application_id`,
  `loan` argv parsing, `loan decide` → `:Decision`), `record.py` (adapted: runs carry `application`,
  `verify traces` per PLAN step 4, `traces export` writes sop.md + policy.md + traces.md),
  `cli.py` with every command from PLAN step 3 plus the pipeline commands (lazy imports, so the help
  works before `tools.py` / `importer.py` / `fixture.py` exist).

Verify: `uv sync && uv tool install --editable . && loan --help` → lists sop, application, ownership,
facilities, cashflow, kyc, policy, precedents, check, record, decide, import, verify, reset, doctor,
rationale (submit), traces (show, export). OK.

Decisions:
- `loan record` is one command with two uses, as in aip-demo: `loan record <rationale-id> --outcome
  --confidence --revision` for the agent, `loan record run-0N | --all` for the pipeline.
- `loan import --rules-only` is the step-7 hook for re-importing the Rule nodes.
- Business ids: PLAN names Alder Logistics `BUS-05` twice, but also needs five applicants plus the
  business Pell's owner co-holds. Resolution: `BUS-01` Harrow, `BUS-02` Ridgeline, `BUS-03` Corvid,
  `BUS-04` Mossbank, `BUS-05` Alder Logistics (no application), `BUS-06` Pell & Daughters (`APP-1005`),
  `BUS-07` the business Pell's owner co-holds (no application). Seven businesses, five applications.

Next: name collision search, then step 1 (fixture).

## 2026-10-13 — name collision search (before step 1)

Searched every business and person name. Businesses (Lantern Mutual, Harrow Street Bakery, Ridgeline
Dental Partners, Corvid Print Co., Mossbank Climbing Gym, Pell & Daughters Plumbing, Alder Logistics,
Wrenfield Mechanical): no real company found. People: replaced three.
- Priya Mehta → **Priya Raghunathan** (several real people, one a named corporate director).
- Renata Szabo (my own pick for Alder Logistics' second owner) → **Ilse Brandvold** (a real person in news coverage).
- Sofia Lindqvist (my pick for Mossbank's owner) → **Ingrid Vossberg** (very common name, a listed athlete).
Kept: Tom Alder (only a 1960s German actor "Thomas Alder" surfaced; the surname is tied to Alder
Logistics), Anneliese Okafor, Marcus Tiller, Declan Hurst, Ben Achterberg, Maureen Pell, Gavin
Wrenfield, Dana Whitlock, Omar Farsi (no public person found for any).

## 2026-10-13 — step 1: the fixture

Done:
- `src/loan/policy.py`: the policy as code, shared by the tools (graph), `verify fixture` (JSON) and the
  tests: `figures(repo, application_id)` computes every figure with its cites through a small `Repo`
  protocol; `evaluate(figures, rules)` applies R1–R6 and G1. `AS_OF = 2026-10-13` is the demo's today.
  `PROTECTED_WORDS` is the one word list used by `loan check` and by the skill's gather step.
- `tools/make_fixture.py` → `data/bank/{core_banking,loans,compliance,ownership,crm}.json`, each
  `{"system", "as_of", "records": {Type: [...]}}`. Cash flow is generated so each business's trailing-12
  average net hits its target coverage exactly (1.6 / 1.9 / 1.3 / 1.15 / 1.4). Payments fall due on the
  15th; Alder Logistics `FAC-03` missed 2026-07-15, 08-15, 09-15 → 90 days late at AS_OF.
- `data/bank/sop_assess_loan.md` (the credit team's page) and `data/bank/policy.md` (the rules as prose).
- `src/loan/fixture.py`: `Fixture` (typed accessors), `FixtureRepo`, `verify_fixture` (counts, the five
  outcomes and fired rules, coverage bands ±0.02, R5 only via ownership, APP-1005 exposure $1.4M, dob present).

Verify: `uv run python tools/make_fixture.py` twice → identical md5s (idempotent). `loan verify fixture` →
APP-1001 review [R5] 1.6 / APP-1002 auto_approve [] 1.9 / APP-1003 auto_decline [R1,R2] 1.3 /
APP-1004 review [R3] 1.15 / APP-1005 auto_approve [] 1.4, exposure 1,400,000. OK.

Decisions:
- Extra fields beyond PLAN's record shapes: `Application.product` and `.rate` (needed for the payment and
  for precedent matching), `Facility.term_months` and `.monthly_payment`, `KycRecord.id`, `Note.id`,
  `Rule.secondary_threshold` on R3. One closed facility (`FAC-07`, no payments) for realism.
- Products: term loan (APP-1001, APP-1004), equipment loan (1002), working capital line (1003), vehicle
  loan (1005), so the free-form Decisions on APP-1001 become precedents for APP-1004 (same product, same band).
- Corvid Print's tenure is 3.4 years so G1 does not catch the hard decline (STORY: "rules fire, no judgment needed").
- One CRM note on Harrow (NOTE-02) mentions an owner's age; the skill's gather step must strip it and
  `loan check` must reject a rationale that repeats it.
- Rationale outcomes: approve | counter | decline | refer.

Next: step 2 (importer). Needs the memory database credentials in `.env`.

## 2026-10-13 — step 2: importer written, blocked on memory database credentials

Done:
- `src/loan/importer.py`: `plan()` → 450 entities (Business 7, Account 10, Month 240, Facility 7, Payment 144,
  Application 5, KycRecord 7, Rule 7, FraudEvent 1, Person 10, RelationshipManager 2, Note 9, Playbook 1)
  and 482 typed edges (OWNS 12 with pct/since, HOLDS 10, HAS_CASHFLOW 240, HAS_FACILITY 7, HAS_PAYMENT 144,
  APPLIED 5, KYC 7, HAD 1, SUBJECT_TO 35, COVERS 7, HAS_NOTE 9, FOLLOWS 5). Entities through the SDK, `key`
  and attributes set with the driver, edges with the driver (batched UNWIND). `import_rules()` for
  `loan import --rules-only` updates existing Rule nodes in place (keeps APPLIED_POLICY edges) and creates new
  ones. `verify()` checks exact counts per label, every edge type, and the proof query (Alder Logistics /
  FAC-03 / 3 missed). `reset()` wipes the database.
- `.env` created from `.env.example`; `TYPESAFE_API_KEY` copied from `~/.config/aip/server.toml` (the aip
  server already uses it). `NEO4J_*` still empty.

Where things stand: BLOCKED on the memory database credentials (a fresh Aura Free instance for this demo:
`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` in `loan-demo/.env`). Once filled:
`loan doctor && loan import && loan verify import`, then step 3.

## 2026-10-13 — correction

Briefly pointed `.env` at the aip catalog instance; reverted before any write (only `loan doctor` reads ran).
The aip database is the one in `~/.config/aip/server.toml`, unchanged. Memory must be a separate database.
`loan reset` is now scoped to the memory labels regardless. Still BLOCKED on memory credentials.

## 2026-10-13 — step 2: import

Memory database: the user's dedicated Aura instance `fd0cf065` (`.env`), separate from the aip catalog.
Two stray nodes were there; `loan reset --yes` cleared them.

Done: `loan import` (about two minutes; 450 entities through the SDK, 482 typed edges), `checkpoints/01-import.json`,
`docs/import.md`. Fix on the way: the SDK capitalises the type label (`KycRecord` → `Kycrecord`), so
`_fix_labels` restores the intended labels after the keys are set.

Verify: `loan verify import` → exact counts per label, all twelve edge types, proof query returns
Alder Logistics / FAC-03 / 3 missed. OK.

Next: step 3 (tools.py, tests/test_tools.py).

## 2026-10-13 — step 3: the agent's tools

Done: `src/loan/tools.py` (`GraphRepo` answers the policy engine from the graph; sop, application,
ownership, facilities, cashflow, kyc, policy, precedents, rationale submit, check, record, decide) and
`tests/test_tools.py` (15 tests: policy on the fixture and on the graph for all five applications, R5 only
via ownership, no dob in any tool output, check rejects a fake cite / invented figure / protected words
and record refuses it, check passes a cited rationale, the protected-word regex has no false positives
on ordinary words).

Verify: `uv run pytest -q tests/test_tools.py` → 15 passed (100 s, Aura round-trips). Smoke-tested the
write path by hand: DEC-APP-1002-01/02 with ABOUT, CITES ×8, PRECEDENT_FOR ×1, then deleted them so the
graph holds no Decision before the recordings.

Decisions:
- `loan check` lint: `[cite: KEY]` (comma lists allowed) must name an Entity or Decision node; every
  `$` amount (K/M suffix ok, rounding to $1 or 0.5%), `Nx` ratio (±0.01), `N%` and `N days` must match a
  number in the evidence (figures, cash-flow rows, payments, balances, ownership pcts, the policy's own
  thresholds); the first paragraph must state the outcome; `PROTECTED_WORDS` must not appear.
- Rationale outcomes: approve | counter | decline | refer. `loan record` recomputes the policy at filing
  time and stores `policy_outcome` and `fired_rules` on the Decision (labels `:Decision:Filed`), links
  APPLIED_POLICY to the fired rules, CITES to every cited entity, PRECEDENT_FOR from every precedent
  `loan precedents` returns for the application plus any `DEC-` key cited in the text.
- Decision keys `DEC-<application>-<nn>`; rationale ids `RAT-<application>-<nn>` under `.run/rationales/`.
- The Cypher that writes a Decision is four statements (an empty UNWIND of fired rules used to cut the
  single-statement version short and lose the CITES edges).

Next: step 4 (prompts/runs.yaml, `loan record --all` in the background, verify traces, docs/recording.md).

## 2026-10-13 — step 4: the free-form runs

Done: `prompts/runs.yaml` (preamble + five runs), `loan record --all` in the background (`.run/record.log`),
`checkpoints/02-runs.json`, `checkpoints/traces/run-0[1-5].json`, `docs/recording.md`.

| run | application | turns | wall | cost | outcome filed |
|---|---|---|---|---|---|
| run-01 | APP-1001 | 31 | 635 s | $1.43 | refer, 0.7 (check bounced twice) |
| run-02 | APP-1002 | 22 | 373 s | $0.74 | approve, 0.92 |
| run-03 | APP-1003 | 22 | 360 s | $0.73 | decline, 0.95 |
| run-04 | APP-1004 | 25 | 494 s | $1.24 | approve, 0.75 (departed from the APP-1001 precedent) |
| run-05 | APP-1001 | 20 | 351 s | $1.00 | refer, 0.7 (followed DEC-APP-1001-01) |

Verify: `loan verify traces` → every run rc=0, ran `loan check`, logged judgments (4–7), filed a decision;
report: run-01 and run-05 both walked ownership. OK. (The STORY's "one run never walked the ownership
graph" did not happen; the README says what did differ: order, wording, bounces, precedent handling.)

Decisions / fixes along the way:
- The hooks also record the session that builds the demo (this one); added `.run/ignore-sessions` (session
  ids the hook never records) and put mine in it; purged my nodes. The authoring run gets `LOAN_RECORD=0`.
- Two lint false positives fixed mid-recording (run-01 hit both): a rate written as a percentage (8.5% for
  0.085) now counts as evidence; headings are skipped when finding the first paragraph for the outcome check.
- Agents wrote their rationale drafts to the project root; moved to `.run/agent-files/`, patterns gitignored.

Next: step 5 — `loan traces export` done (source/sop.md, policy.md, traces.md, 284 lines); `make author` in the
background (`.run/author.log`), then validate, local `aip run` on APP-1002, docs/compile.md.

## 2026-10-13 — step 5: export and author the skill

Done: `loan traces export` (source/sop.md, policy.md, traces.md), `make author` in the background
(`.run/author.log`, `.run/author.json`: 76 turns, 33 min, $9.70). Output: `skills/assess-business-loan/`
with SKILL.md (version "1", 13 nodes: the nine working steps plus gate/fix/recheck and end), six scripts
(stdlib only, `loan` by subprocess), two templates, source/README.md. `docs/compile.md` written.

Verify: `aip validate ./skills/assess-business-loan` → VALID. Local run on `checkpoints/start-app-1002.json`
(started with `--run-file`, paused at `rationale`, answered, `aip resume`): check passed first time, filed
`DEC-APP-1002-03` approve, confidence 1.0, revision "1", needs_human false. OK. (`--interactive` needs a
terminal; the pause-and-resume path exercises the same steps.) The authoring session's own test filed
`DEC-APP-1002-02`; both stay in the graph as revision-1 decisions on APP-1002.

Decisions (the author's, reviewed and kept): owners labelled by position ("owner 1"); `refer` is not an
outcome label of the procedure (close calls pause for review on the server; G1 declines end unfiled);
confidence 1.0 / 0.6 as the plan said; the interest rate is not in the evidence digest; `assess` also
declares `crm_notes` (filtered), one more than PLAN's five inputs, because the SOP's judgment section
names the relationship manager's notes about the business.

Next: step 6 — publish (server already running on :8000), two runs on APP-1005, one on APP-1004 through
`claude` + aip-runtime (LOAN_RECORD=0 so the memory graph keeps exactly the five free-form traces).

## 2026-10-13 — step 6: publish and run through the server

Done: `aip publish` → `assess-business-loan@63c33c7be679ea32` (revision 1), `checkpoints/03-publish.json`;
three headless `claude -p` sessions with the aip-runtime skill (LOAN_RECORD=0; `.run/live/`):
APP-1005 ×2 (10 and 13 turns, 174 s and 209 s, one rationale pause each, DEC-APP-1005-01/02 approve 1.0,
identical outcome / fired rules / 21 cited keys, PRECEDENT_FOR from the first to the second) and
APP-1004 (17 turns, 195 s, assess answered by Jev above every threshold: medium 0.89 / not material 0.07 /
approve 0.73, DEC-APP-1004-02 approve 0.6). Details in `checkpoints/04-live-runs.md`.

Fixes on the way: the server (started 2026-10-06 from another folder) passed another demo's NEO4J_* to
`loan`; this folder's `.env` now overrides NEO4J_* (`env.py` OVERRIDE). One errored server run
(43091c1d509f4923, "unknown application") stays in the aip database. The hook no longer labels
`loan decide --help` as a judgment; the four such steps were unlabelled.

Verify (informal, PLAN has no command for step 6): two APP-1005 decisions match; APP-1004 did not pause
(Jev confident; documented, run kept). Server already running on :8000, not restarted.

Decision for step 7: R7 is evaluated by the bank's policy engine (`loan policy`) only when the R7 Rule node
is in the graph (`loan import --rules-only` is the switch), with a new effect `human`; revision 2 of the
skill routes a fired `human` rule to a person at `by-confidence`. A revision-1 run on APP-1001 is made
first (before R7 exists) so beat 8 shows revision 1 and 2 on the same application.

## 2026-10-13 — step 7: the edit beat

Done: revision-1 run on APP-1001 first (1daa215641134079: review pause at assess, risk tier 0.4; decline
→ G1 → ended unfiled). Then R7 `connected_exposure_cap` added to `tools/make_fixture.py` (compliance.json)
and `data/bank/policy.md`; `src/loan/policy.py` evaluates R7 with effect `human` only when the R7 Rule
row exists; `loan import --rules-only` (1 new rule, 7 updated, 40 SUBJECT_TO); EXPECTED/COUNTS updated
(APP-1001 [R5, R7], APP-1005 [R7] review, Rule 8); skill `precedents.py` sets needs_human for a `human`
effect, SKILL.md version "2" + descriptions, source/README.md revision-2 section; `aip validate` VALID;
`aip publish` → `1c4e170b79c08bb1`; `checkpoints/03-publish.json` lists both revisions. Revision-2 run on
APP-1001 (dea19c49f10944a8): fired [R5, R7], review pause at assess (0.27), ended unfiled with the R7 note.
`checkpoints/04-live-runs.md` has the side-by-side.

Verify: `uv run pytest` 15 passed with R7 in graph and expectations; `loan verify fixture|import|traces` OK.

Note: the server does not persist the review flag on StepRun (null everywhere); the pause was observed
live and the under-threshold confidences are on the Answer nodes. queries.md beat 6/8b say so.

Next: step 8 — test queries 6/8 in both databases, README.md, trim PLAN.md, screenshots into img/.

## 2026-10-13 — step 8: queries, README, docs

Done: `queries.md` (beats 1–8 with table variants; every query run against its database through the driver:
1, 2, 2b, 3, 3b, 4, 7, 7b, 8c on memory; 5, 5b, 6, 6b, 6c, 8, 8b on aip), `README.md` (walkthrough in the
aip-demo style, no timing claims, no regulation names), `PLAN.md` trimmed (original kept as
`docs/PLAN-original.md`), `docs/compile.md` minutes figure removed, top-level `README.md` gained a loan-demo
line, `img/` holds three inspector screenshots (skill graph, revision-2 run replay, history).

Not done, for the user: Neo4j Browser screenshots of the memory and aip graphs. Aura's Browser needs a
login and I do not enter passwords; the queries are tested and paste-ready in `queries.md`, so the PNGs
are a few minutes of clicking (beats 1, 2, 3, 6, 7 are the ones the README would show).

Corrections made during the final pass: beat 8/8b filter on the hard-rules result (`CONTAINS 'APP-1001'`);
README claims checked against the traces (risk tier asked in three phrasings by four runs; only run-01
bounced off the check). Answer nodes carry `accepted` / `overridden` (the revision-1 APP-1001 run shows the
human's override of risk_tier medium → high); beat 6c shows it.

## Where things stand (final)

"Done when" from PLAN.md:
- `make sync doctor import record export author publish` end to end from a clean database: every target
  exists and each ran once in this build, in that order, from a clean database (reset at step 2). Not re-run
  as one command afterwards; a re-run would cost about an hour of model time and wipe the recorded graph.
- `loan verify fixture|import|traces`: all OK (re-run after the R7 edit).
- Five recorded traces: yes. Two live runs on APP-1005 that match: yes (DEC-APP-1005-01/02). One paused run
  on APP-1004 or a documented reason: Jev was confident (0.89 / 0.07 / 0.73); documented in README and
  `checkpoints/04-live-runs.md`. The pause the plan wanted happened on APP-1001 instead, on both revisions
  (risk tier 0.4 and 0.27), which the README uses. One revision-2 run on APP-1001: yes (dea19c49f10944a8).
- Every query in `queries.md` returns what its heading says: yes, via the driver; Browser rendering not
  checked by me.
- No regulation names, no timing claims, no real company or person names: grep clean (STORY.md and
  PLAN-original.md keep the original sketch's *verify* notes and placeholder names on purpose).

Not committed, per instructions. `.env` holds the memory credentials and the TypeSafe key (gitignored).
The aip server on :8000 was left running as found; the memory database holds the import plus the five
traces and eleven filed decisions (five free-form, DEC-APP-1002-02/03 from the authoring and verify runs,
DEC-APP-1005-01/02, DEC-APP-1004-02).

## 2026-10-14 — README metrics section

Added `## Metrics` to README.md (between "What you get" and "Files"): models used (`claude-fable-5-1` for
every Claude Code session, default model, no `--model` flag; TypeSafe `jev-latest` on the server), the five
free-form recordings (wall, API time, cost, turns, output and cache-read tokens, rationale attempts), the
authoring session, the five server runs, and an agreement paragraph in place of accuracy (no labelled set).
Figures come from `.run/*.claude.json`, `.run/author.json`, `.run/live/*.json` via `checkpoints/02-runs.json`
and `checkpoints/04-live-runs.md`. The "No speed claim is made" sentence now points at the section instead.
Not committed.

## 2026-10-14 — Haiku comparison on the server runs

Four headless sessions (`.run/haiku/run.sh`, LOAN_RECORD=0, revision 2, R7 in the graph, nothing deleted or
changed in aip): APP-1005, APP-1004, APP-1001 on `claude-haiku-5-5`, plus APP-1005 on `claude-fable-5-1` as
a same-day R7-path baseline. Results in `checkpoints/05-haiku-runs.md` and a table in the README Metrics
section. Haiku's APP-1004 decision (DEC-APP-1004-03) equals Fable's DEC-APP-1004-02 on outcome, rules and
all 35 cites, check first pass; APP-1001 and APP-1005 took the same path and ended unfiled on R7 as Fable's.
Haiku: half to three-quarters of the wall time, a third to a half of the API time, ~70× cheaper at list.
Side effects: DEC-APP-1004-03 now in memory; four new runs in aip history (724a379fcecf48e5,
689d4f1f068f4cb9, 06a7a1ad5b2140f2, c362515ab5924564). Not committed.

## 2026-10-14 — README "The deltas, in short"

Added a speakable summary before Metrics: performance (wall, model time, turns, cost per run, averaged),
accuracy and trust, governance and traceability, each as Fable alone / Fable + procedure / Haiku +
procedure, with the two deltas (Fable→Fable with the procedure; Fable alone→Haiku with the procedure)
and a "what this does not show" paragraph. Not committed.

## 2026-10-14 — README rewritten as a worked example

Per request: no "acts", "beats", "hero/gray case" or demo framing. Plain descriptive title, neutral voice,
light touch (hedging, "what this does not show", contrast-and-example), stages 1–3 plus "Changing a rule",
a new "Swapping the driving model" section holding the Haiku table (moved out of Metrics), "Side by side",
"What changed, in numbers", Metrics, Files. `queries.md` retitled "in reading order"; README refers to
"query N". docs/import.md and docs/compile.md references fixed. PLAN.md, PROGRESS.md and checkpoints left
as the build log. Not committed.

## 2026-10-14 — docs/walkthrough.md

Plain-language walk of the published procedure (revision 1) node by node, for a reader with no lending
background: the five node kinds, the thirteen nodes in order, three runs as paths, and the one line
revision 2 changed. Linked from the README (stage 2 and Files). Also: `aip get` during this session
wrote an untracked `assess-business-loan/` copy into loan-demo/; removed. Not committed.
