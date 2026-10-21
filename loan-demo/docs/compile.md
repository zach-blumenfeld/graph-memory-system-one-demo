# How the skill was compiled

Three inputs, one authoring session, one validated folder.

## 1. The source, read back out of memory

`loan traces export` runs Cypher against the memory graph (`src/loan/record.py`) and writes three
files into `skills/assess-business-loan/source/`:

- `sop.md`: the credit team's page "How we assess a business loan", exactly as imported.
- `policy.md`: the lending policy as prose, so the authoring step has the rules in both forms (the
  `Rule` rows are in the graph, the prose is here). The export drops the paragraph of any rule
  `loan import --without-rule` left out of the graph, so before the rule change it reads R1 to R6 and G1.
- `traces.md`: the five recorded runs. For each: the prompt, every `loan` call in order with its JSON
  result, every judgment call as question / options / answer / why, and the agent's closing summary.
  About 280 lines. run-01 and run-05 are the same application, so their differences are the agent's.

The judgment calls are the important part. They were logged with `loan decide` during the runs, so
they sit in the graph as `ReasoningStep` nodes with the `Decision` label and typed fields, and come
out of the export as explicit decision points rather than prose to be guessed at.

## 2. The prompt

`prompts/author.md` tells a fresh Claude Code session to use the `aip` authoring skill on that folder
and sets the constraints: the start input (`application_id`), that scripts may call `loan` and must be
standard-library Python (they run on the client under the `aip` command's own interpreter, wherever
`aip run` is started; `requires.tools` names `loan`), nine steps by name and kind, what the `assess`
decision may and may not see, one fix pass and no loops, how the record step learns its own revision
(from `../SKILL.md` on a folder run; from the cache folder's name, `<name>@<hash>`, on a served run,
since the client fetches only `scripts/` and `assets/`), validate until clean, test locally once on
APP-1002 by pause and resume (no terminal), write `source/README.md`.

```
make author      # LOAN_RECORD=0 claude -p "$(cat prompts/author.md)" with Read/Write/Edit/Bash/Skill allowed
```

`LOAN_RECORD=0` keeps the authoring session out of the memory graph; only the five free-form runs are
recorded there.

## 3. The authoring skill

The `aip` skill (from [aip-spec](https://github.com/zach-blumenfeld/aip-spec)) does the compile:
read the source, choose a step kind for every item in the order the spec prescribes (script if it
can be code, decision if it is a judgment with a fixed answer space, client task only for
generation), write the YAML, the scripts and the templates, run `aip validate` until clean, run the
procedure once locally against the decision model, and record in `source/README.md` what came from
where and what was dropped.

On 2026-10-21, against AIP format 0.6a1, this took 70 turns, 26 minutes and $12.14 (105K output
tokens, 5.0M cache-read tokens), the most expensive step in the build. The 0.6 format asks for more
than 0.5a1 did: every execution and client-task step declares its `outputs`, a `requires` block names
the interpreter and the `loan` tool, each step sees only its declared `inputs`, and the validator
checks the data flow (every key read is produced on every path to it, by exactly one step). The
session's first local test paused for a review on `risk_tier` (low 0.66); it sharpened the question's
criteria from run-02's reasoning and the second test cleared every threshold (1.0 / 0.93 / 0.97),
filed `DEC-APP-1002-02` and checked, in the run's history, that `assess` received only its six
declared keys and no person's name. (The first compile of the same source, 2026-10-13 on format
0.5a1: 76 turns, 20 minutes, $9.70.)

## What came out

`skills/assess-business-loan/`:

```
SKILL.md                 frontmatter (version "1") + the AIP runtime block + requires + the procedure YAML (11 nodes)
scripts/loanlib.py       call loan; the protected-word list; name and dob scrubbing; the revision; the recheck handoff file
scripts/gather.py        application, ownership two hops, facilities, cash flow, KYC; strips what assess must not see
scripts/hard_rules.py    loan policy -> policy_outcome, fired, guidance, figures, cites
scripts/precedents.py    loan precedents; outcome for the automatic bands; confidence; needs_human (G1); the evidence digest
scripts/check.py         loan rationale submit + loan check; check_state passed/fix (first pass), recheck_* keys (second)
scripts/record.py        loan decide for the typed judgments; loan record with the outcome, confidence and revision, or the not-filed note
assets/rationale.md      the client-task template: evidence digest, the keys it may cite, the check's rules
assets/fix.md            the one fix-up pass
source/                  sop.md, policy.md, traces.md, README.md (provenance, rules the scripts carry, drops, the test log)
```

The graph (11 nodes: seven working steps, one router, three sub-steps of the check): `gather` →
`hard-rules` → `assess` (decision: `risk_tier` choice, `connected_exposure_material` noul,
`assessed_outcome` choice; thresholds 0.6 / 0.3 / 0.6) → `precedents` → `rationale` (client task) →
`check` → `gate` (router) → `record` → `end`, with `fix` (client task) → `recheck` → `record` on the
failed-check branch.

Three things the prompt asked for could not be built under 0.6a1, and the author changed them, with
the reasons in `source/README.md` under "Decisions made without asking":

- **No `by-rules` router: `assess` runs on every band.** 0.6 forbids a step after a join from reading
  a key that only one branch produced, and each key has exactly one producer, so a skipped decision
  could never reach `precedents` or the result. The hard rules still decide: the question is named
  `assessed_outcome`, its instructions say the policy's outcome is the answer where a hard rule fired
  or nothing fired, and `precedents.py` overrides it with the policy's outcome on the automatic bands.
  The cost is one decision-model call per run on those bands. The traces support it: the free-form
  runs on the automatic bands logged a risk tier too.
- **No `by-confidence` router: `record` is on every path.** `decision_id` at `end` needs one producer
  on every path, so a G1 decline now writes and checks its rationale, and `record.py` files nothing,
  logs the judgments, and tells the human the exact `loan record` command. The human gets a checked
  draft instead of nothing.
- **`recheck` produces its own keys** (`recheck_state`, `recheck_rationale_id`) and hands its result
  to `record` through a file under the run's working directory, since `record` can only declare the
  keys both of its incoming paths produce.

Two things worth knowing from `source/README.md`:

- **What the judgment step sees.** `gather` removes dates of birth and every person's name from the
  whole state (owners become "owner 1", "owner 2"; the relationship manager becomes a role), and
  withholds any CRM note that mentions a personal characteristic, including the annual-review note
  that records an owner's age as "Priya (58)". The state `assess` received is stored on every run in
  the aip database, so "the model could not see it" is a query, not a promise.
- **Confidence.** The state the scripts see carries the decision model's collapsed answers, not its
  probabilities, so the filed `confidence` is 1.0 when the hard rules decided and the cleared
  threshold (0.6) when the decision model did. The exact probabilities, the resolver (`typesafe` or
  `manual`) and whether a human overrode an answer at a review are on the `Answer` nodes in the aip
  database (`queries.md` queries 6b and 6c).
