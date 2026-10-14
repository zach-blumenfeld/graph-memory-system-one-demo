# Build plan: `loan-demo/` in graph-memory-system-one-demo

For an implementing agent. Target repo: `github.com/zach-blumenfeld/graph-memory-system-one-demo`.
Add a third folder, `loan-demo/`, beside `aip-demo/` and `nams-demo/`, following
`aip-demo/` file for file. Read `aip-demo/README.md`, `aip-demo/PLAN.md`, `aip-demo/docs/*.md`
and the whole of `aip-demo/src/blast/` before writing anything. The story and the procedure
are in `loan-demo/docs/STORY.md`; read that too. Keep `loan-demo/PROGRESS.md` up to date: after
every step, append what was done, what was verified, and what is next, so a fresh session can
resume from it without re-reading the traces.

Written 2026-10-13. Decisions already made: memory on the open-source `neo4j-agent-memory`
library over Bolt (not NAMS); skills on AIP 0.5a1 with the aip server and TypeSafe Jev; the
payoff we demonstrate is a traceable, editable procedure, not speed, so no timing claims
anywhere in the docs. Everything about the bank, the applicants and the policy is invented.

## Ground rules

- Same shape as `aip-demo`: `data/` fixture as JSON, `src/<pkg>/` with `cli.py`, `tools.py`,
  `hooks.py`, `importer.py`, `fixture.py`, `record.py`, `memory.py`, `env.py`; `prompts/`,
  `checkpoints/`, `skills/<name>/`, `docs/`, `queries.md`, `Makefile`, `.env.example`,
  `.claude/settings.json`, `pyproject.toml`. Package `loan`, commands `loan` and `loan-hook`.
- Copy `hooks.py`, `memory.py`, `env.py`, `record.py` from `aip-demo/src/blast/` and rename
  `blast` → `loan`, `BLAST_RECORD` → `LOAN_RECORD`, `BLAST_ROOT` → `LOAN_ROOT`, the id regex
  `brief-\d{3}` → `APP-\d{4}`, `brief_id` → `application_id`. Keep the hook semantics exactly:
  UserPromptSubmit starts a trace and stores the prompt, PostToolUse on Bash records every
  `loan ...` call as ReasoningStep → ToolCall, `loan decide` adds the `Decision` label, Stop
  stores the answer and completes the trace. Hooks never fail the session.
- Fixture is not Notion-shaped this time. Five plain JSON files, one per bank system, each
  `{"system": "...", "records": [...]}` with flat records. `fixture.py` is simpler than the
  Notion one; keep the `Fixture` class name and the typed-accessor style.
- Two Neo4j databases, as in `aip-demo`: memory (this folder's `.env`) and the aip server's
  catalog (`~/.config/aip/server.toml`). Do not reuse the email demo's memory database; use a
  fresh Aura Free instance or `loan reset --yes` on one dedicated to this demo.
- Checkpoints after every stage, committed, so the walkthrough can be replayed without rerunning
  the model. Every stage has a `loan verify <stage>` that exits non-zero on failure.
- No regulation names in README or SOP. Say "when you decline someone you owe them a reason",
  "the judgment step cannot see protected characteristics", "every decision is auditable".

## Step 0: scaffold

Create `loan-demo/` with `pyproject.toml` (name `loan`, scripts `loan = "loan.cli:app"`,
`loan-hook = "loan.hooks:main"`, same dependencies as `aip-demo`), `.env.example`,
`.gitignore` (`.env`, `.run/`, `.aip/`, `.venv/`), `.claude/settings.json` (copy, with
`loan-hook`), `Makefile` (copy, rename targets' commands), `src/loan/__init__.py`.

Verify: `uv sync && uv tool install --editable . && loan --help` lists the commands below.

## Step 1: the fixture (`tools/make_fixture.py` → `data/bank/*.json`)

Fictional bank **Lantern Mutual**. Generate deterministically (fixed seed, fixed dates). Files:

`core_banking.json`: businesses and their deposit accounts with 24 months of cash flow.
- `Business {id, legal_name, dba, industry, founded, customer_since}`
- `Account {id, business_id, type, opened, balance}`
- `MonthlyCashflow {account_id, month, inflow, outflow}` (24 rows per account)

`loans.json`: facilities, payments, applications.
- `Facility {id, business_id, product, principal, rate, opened, status}`
- `Payment {id, facility_id, due, paid_on|null, amount, status: current|late|missed}`
- `Application {id, business_id, amount, term_months, purpose, submitted, requested_by}`

`compliance.json`: KYC and the policy.
- `KycRecord {business_id, status: current|refresh_due|overdue, last_review, beneficial_owners_verified}`
- `Rule {id, name, kind: hard|guidance, text, threshold, field}` (see the policy below)
- `FraudEvent {id, business_id, date, kind}` (one, on the hard-decline applicant)

`ownership.json`: who owns what.
- `Person {id, name, dob, role}` — `dob` exists so the demo can show it is NOT passed to the decision step
- `Ownership {person_id, business_id, pct, since}`

`crm.json`: coverage and notes.
- `RelationshipManager {id, name}`, `Coverage {rm_id, business_id, since}`, `Note {business_id, date, text}`

Also `data/bank/sop_assess_loan.md` (the credit team's page "How we assess a business loan",
written like `aip-demo/data/notion/sop_email_blast.md`: the rules in order of how much trouble
they save; before you start; the checks; the write-up; judgment calls to log with `loan decide`)
and `data/bank/policy.md` (the same rules as prose, so the authoring step has both forms).

**The policy (hard rules, all in `compliance.json` as `Rule` rows):**
- R1 `kyc_current`: KYC status must be `current`; `overdue` is an auto decline, `refresh_due` is review.
- R2 `no_fraud_12m`: a FraudEvent in the last 12 months is an auto decline.
- R3 `coverage_floor`: debt service coverage (12-month average monthly net inflow ÷ proposed monthly payment, existing facility payments included) ≥ 1.25 to auto approve; 1.00–1.25 is review; < 1.00 is auto decline.
- R4 `exposure_cap`: total exposure to the business plus businesses its owners hold ≥ 25% of must stay ≤ $1.5M; over is review.
- R5 `connected_delinquency`: any facility ≥ 60 days late at a business an owner holds ≥ 25% of is review, never auto approve.
- R6 `tenure`: customer for < 24 months is review.
- G1 (guidance): a decline on a customer of 5+ years goes to a human before filing.

**The six businesses** (ids `BUS-01..06`), one application each except BUS-06 (none):
1. `APP-1001` **Harrow Street Bakery**, $400K, second location. 6-year customer, KYC current, coverage 1.6x. Owners Priya Mehta 55%, Tom Alder 45%. Tom Alder also owns 60% of **Alder Logistics** (`BUS-05`), which has a $300K facility 90 days late. R5 fires → review; everything else passes. The hero case: flat retrieval says approve, the graph says review.
2. `APP-1002` **Ridgeline Dental Partners**, $250K equipment. Clean on every rule, coverage 1.9x, no connected businesses. Auto approve.
3. `APP-1003` **Corvid Print Co.**, $150K working capital. KYC overdue and a FraudEvent 4 months ago. R1 and R2 fire → auto decline.
4. `APP-1004` **Mossbank Climbing Gym**, $600K fit-out. Coverage 1.15x (review band), 7-year customer, strong CRM note (signed lease, pre-sales), no connected issues. The gray case: the decision model should be uncertain and the confidence router should send it to a human; G1 also applies if the answer is decline.
5. `APP-1005` **Pell & Daughters Plumbing**, $200K vehicles. Held back from the recordings for the live run. 3-year customer, coverage 1.4x, owner also holds 30% of a business with a facility that is current. R5 does not fire (not late), R4 close to the cap (exposure $1.4M). Procedure outcome: approve, one pause for the rationale.
6. `BUS-05` **Alder Logistics**, no application; exists for the connected delinquency. `BUS-06` is the business Pell's owner co-holds.

Verify: `uv run python tools/make_fixture.py` is idempotent (git diff clean on rerun);
`loan verify fixture` checks the counts and the five facts above (R5 fires for APP-1001 only
via the graph of ownership, coverage bands as stated).

## Step 2: import into memory (`src/loan/importer.py`)

`plan()` maps records to entities and typed edges, as `aip-demo` does: entities via
`long_term.add_entity(name, type, description=, attributes=)` so each is `(:Entity:<Type>)`,
then `key` and attributes set with the driver, then real edge types with the driver.

Labels: `Business`, `Account`, `Facility`, `Payment`, `Application`, `KycRecord`, `Rule`,
`FraudEvent`, `Person`, `RelationshipManager`, `Note`, `Playbook` (the SOP page, `text` attr).
Cash flow months: write as `Month` nodes (`HAS_CASHFLOW`) so the coverage figure can cite them;
24 × accounts is fine for Browser.

Edges: `(:Person)-[:OWNS {pct, since}]->(:Business)`, `(:Business)-[:HOLDS]->(:Account)`,
`(:Account)-[:HAS_CASHFLOW]->(:Month)`, `(:Business)-[:HAS_FACILITY]->(:Facility)`,
`(:Facility)-[:HAS_PAYMENT]->(:Payment)`, `(:Business)-[:APPLIED]->(:Application)`,
`(:Business)-[:KYC]->(:KycRecord)`, `(:Business)-[:HAD]->(:FraudEvent)`,
`(:Application)-[:SUBJECT_TO]->(:Rule)` (all rules), `(:RelationshipManager)-[:COVERS]->(:Business)`,
`(:Business)-[:HAS_NOTE]->(:Note)`, `(:Application)-[:FOLLOWS]->(:Playbook)`.

Decision nodes are NOT imported; the `record` step creates them later (step 7).

Verify: `loan import` then `loan verify import` (exact counts per label, every edge type
present, and the one-query proof: `MATCH (a:Application {key:'APP-1001'})<-[:APPLIED]-(b)<-[:OWNS]-(p)-[:OWNS]->(o)-[:HAS_FACILITY]->(f)-[:HAS_PAYMENT]->(pay {status:'missed'}) RETURN o.name, f.key, count(pay)` returns Alder Logistics).
Checkpoint `checkpoints/01-import.json`. Document in `docs/import.md`.

## Step 3: the agent's tools (`src/loan/tools.py`, `src/loan/cli.py`)

Plain functions returning JSON-able dicts; the CLI wraps them; the skill's scripts call the CLI.
Every figure that a later write-up might quote carries the node keys it was computed from
(`"cites": ["MON-...", "FAC-..."]`). Commands:

| command | returns |
|---|---|
| `loan sop` | the Playbook text from memory (file fallback) |
| `loan application <id>` | application, business, owners (name and pct only; never dob) |
| `loan ownership <business>` | owners, and every other business each owner holds ≥ 25% of, with their facilities and worst payment status. Two hops, from the graph. |
| `loan facilities <business>` | facilities and payments; `late_days` per facility |
| `loan cashflow <business>` | 12- and 24-month averages with the Month keys cited |
| `loan kyc <business>` | KYC record and fraud events |
| `loan policy <application>` | applies R1–R6 and G1 with the figures above; returns `{outcome: auto_approve|auto_decline|review, fired: [{rule, value, threshold, cites}], figures: {...}}` |
| `loan precedents <application>` | past `Decision` nodes on similar applications (same product, same outcome band), with what was decided; empty before the first run |
| `loan rationale submit --file F --application ID --outcome O` | stores the write-up under `.run/rationales/`, returns its id |
| `loan check <rationale>` | the lint: every `[cite: KEY]` in the text exists in the graph; every dollar figure and ratio in the text matches a figure returned by `loan policy`; the outcome stated matches `--outcome`; no mention of dob/age/sex/ethnicity words. Returns `{passed, failures[]}` |
| `loan record <rationale> --outcome O --confidence C --revision R` | creates `(:Decision {outcome, confidence, skill_revision, at})` with `ABOUT`→Application, `APPLIED_POLICY`→each fired Rule, `CITES`→each cited node, `PRECEDENT_FOR` from the precedents used; refuses an unchecked rationale |
| `loan decide --question --options --answer --why` | echoes the judgment (the hook labels it) |

Also the pipeline commands as in `aip-demo`: `import`, `verify <stage>`, `reset --yes`,
`doctor`, `record [run|--all]`, `traces show|export`.

Verify: a `tests/test_tools.py` that runs `loan policy` on the five applications and asserts
the outcomes and fired rules listed in step 1; `loan check` on a rationale with a fake cite fails.

## Step 4: record the free-form runs (`prompts/runs.yaml`, `src/loan/record.py`)

Preamble: "You are the credit analyst at Lantern Mutual. Start by reading the team's page:
run `loan sop`. The `loan` command is your only way to reach the bank's systems (`loan --help`).
Write the rationale to a file and submit it with `loan rationale submit`, check it with
`loan check`, and record the decision with `loan record`. Log every judgment call with
`loan decide`. Finish with a short summary."

Runs: `run-01` APP-1001 (hero), `run-02` APP-1002 (clean), `run-03` APP-1003 (decline),
`run-04` APP-1004 (gray), `run-05` APP-1001 again (same input, to show the path differs).
Headless `claude -p` with the same flags as `aip-demo` (`--tools Bash,Read,Write`,
`--allowedTools "Bash(loan:*),Bash(uv run loan:*),Read,Write"`, `--disallowedTools Skill,...`).

`verify traces`: every run exited 0, called `loan check`, logged at least one decision, and
recorded a decision; run-01 and run-05 both touched `loan ownership` or did not (report, do not
assert); the exported `checkpoints/traces/run-0N.json` exist.

Do not stage failures. Export what happened. Write `checkpoints/02-runs.json`. Document in
`docs/recording.md` (copy and adapt).

## Step 5: export and author the skill (`skills/assess-business-loan/`)

`loan traces export` writes `source/sop.md`, `source/policy.md`, `source/traces.md`.
`prompts/author.md`, modelled on `aip-demo/prompts/author.md`, with these constraints:

- Start input: `application_id` (string).
- Scripts may call `loan`. Gather, policy, precedents, check and record are scripts, never
  decisions. The ownership traversal is inside gather and runs every time.
- Exactly nine steps: `gather` (execution) → `hard-rules` (execution, calls `loan policy`) →
  `by-rules` (router: auto_approve → precedents, auto_decline → precedents, review → assess) →
  `assess` (decision: `risk_tier` choice low/medium/high; `connected_exposure_material` noul;
  `outcome` choice approve/counter/decline; thresholds 0.6 / 0.3 / 0.6) → `precedents`
  (execution) → `by-confidence` (router on a `needs_human` flag the server sets when any
  threshold is missed, or G1 fired with a decline: true → close, false → rationale) →
  `rationale` (client_task, template `assets/rationale.md`, must use `[cite: KEY]` markers and
  state the outcome) → `check` (execution: submit + check; one fix pass via a second
  client_task `fix` and a `gate` router, no loops; the authoring skill may count fix/gate as
  sub-steps) → `record` (execution: `loan record` with the outcome, confidence and skill
  revision) → `end`.
- `assess` declares its inputs explicitly: `figures`, `fired`, `ownership_summary`, `tenure_years`,
  `kyc_status`. It must not declare or receive `owners[].dob`, names of people, or anything
  from `crm` notes that mentions personal characteristics. `gather` strips them from the state.
- Validate with `aip validate` until clean; test locally once with APP-1002; write
  `source/README.md` with provenance and the drop list.

Verify: `aip validate ./skills/assess-business-loan` clean; `aip run ... --input
checkpoints/start-app-1002.json --interactive` ends with a filed Decision node for APP-1002.
Document in `docs/compile.md`.

## Step 6: publish and run through the server

`aip server --inspector`, `aip publish ./skills/assess-business-loan`. Then
`make fresh && claude` with the `aip-runtime` skill: "Assess application APP-1005 for Pell &
Daughters Plumbing." Expect: catalog search, run, typed answers, one pause (rationale),
Decision recorded with `skill_revision: 1`. Run APP-1005 a second time; the two Decision nodes
must have the same `outcome`, the same cited keys and the same fired rules.

Then APP-1004 through the server: expect the run to pause at `by-confidence` for a human
(verify, do not assume; if Jev is confident, say so in the README and keep the run).

Save `checkpoints/03-publish.json` and `checkpoints/04-live-runs.md` (what happened, turns,
pauses, outcomes; no timing claims beyond the raw wall-clock in the checkpoint file).

## Step 7: the edit beat

Make one change a compliance officer would make: add rule R7 `connected_exposure_cap`
("connected exposure over $250K always goes to a human") to `compliance.json` and
`policy.md`, re-import the Rule node only (`loan import --rules-only`), update the
`by-confidence` router condition in the skill, `aip validate`, `aip publish` → revision 2.
Run APP-1001 through the server: R7 fires, the run pauses for a human, and the run record
names revision 2. `queries.md` beat 6 shows revision-1 and revision-2 runs on the same
application side by side.

## Step 8: queries, README, docs

`queries.md`, one Cypher query per beat, each tested in Browser:
1. the applicant's world (APP-1001 two hops out, the five systems colour-coded by label)
2. the connected delinquency path
3. one recorded run as a connected subgraph; `LIMIT 5` for all five
4. the Decision query (judgment calls grouped across runs)
5. the skill as a graph in the aip database (steps and edges)
6. `Run → StepRun → Answer → Question`, plus the `assess` StepRun's stored input (proves no dob)
7. the Decision trace in memory: `Decision → CITES → ...`, `APPLIED_POLICY`, `PRECEDENT_FOR`
8. revision 1 vs revision 2 runs on APP-1001

`README.md` in the `aip-demo` walkthrough style: story (from `docs/STORY.md`), the five
systems, import, the free-form runs and what differed, distillation, the server run, the edit,
what you get. Screenshots into `img/`. `PLAN.md` is this file, trimmed to what was done.

## Done when

- `make sync doctor import record export author publish` runs end to end from a clean database.
- `loan verify fixture|import|traces` all pass.
- Five recorded traces, two live runs on APP-1005 that match, one paused run on APP-1004 (or
  a documented reason it did not pause), one revision-2 run on APP-1001.
- Every query in `queries.md` returns what its heading says.
- No regulation names, no timing claims, no real company or person names (search the five
  business names and the people before committing).
