# How the skill was compiled

Three inputs, one authoring session, one validated folder.

## 1. The source, read back out of memory

`loan traces export` runs Cypher against the memory graph (`src/loan/record.py`) and writes three
files into `skills/assess-business-loan/source/`:

- `sop.md`: the credit team's page "How we assess a business loan", exactly as imported.
- `policy.md`: the lending policy as prose, so the authoring step has the rules in both forms (the
  `Rule` rows are in the graph, the prose is here).
- `traces.md`: the five recorded runs. For each: the prompt, every `loan` call in order with its JSON
  result, every judgment call as question / options / answer / why, and the agent's closing summary.
  About 280 lines. run-01 and run-05 are the same application, so their differences are the agent's.

The judgment calls are the important part. They were logged with `loan decide` during the runs, so
they sit in the graph as `ReasoningStep` nodes with the `Decision` label and typed fields, and come
out of the export as explicit decision points rather than prose to be guessed at.

## 2. The prompt

`prompts/author.md` tells a fresh Claude Code session to use the `aip` authoring skill on that folder
and sets the constraints: the start input (`application_id`), that scripts may call `loan` and must be
standard-library Python (the server runs them under its own interpreter), the nine steps by name and
kind, what the `assess` decision may and may not see, how `by-confidence` routes, one fix pass and no
loops, how the record step learns its own revision, validate until clean, test locally once on
APP-1002, write `source/README.md`.

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

On 2026-10-13 this took 76 turns and needed one YAML quoting fix the validator caught
(an anti-pattern string containing `[cite: KEY]`). The session could not use `--interactive` (no
terminal), so its test run paused to a run file at the rationale step and was resumed with
`aip resume`; the step 5 verify repeated the run the same way and filed `DEC-APP-1002-03`.

## What came out

`skills/assess-business-loan/`:

```
SKILL.md                 frontmatter (version "1") + the AIP runtime block + the procedure YAML (13 nodes)
scripts/loanlib.py       call loan; the protected-word list; name and dob scrubbing; the revision from SKILL.md
scripts/gather.py        application, ownership two hops, facilities, cash flow, KYC; strips what assess must not see
scripts/hard_rules.py    loan policy -> policy_outcome, fired, guidance, figures, cites
scripts/precedents.py    loan precedents; outcome for the automatic bands; confidence; needs_human (G1); the evidence digest
scripts/check.py         loan rationale submit + loan check; check_state passed/fix/stop (used by check and recheck)
scripts/record.py        loan record with the outcome, confidence and revision; loan decide for the typed judgments
assets/rationale.md      the client-task template: evidence digest, the keys it may cite, the check's rules
assets/fix.md            the one fix-up pass
source/                  sop.md, policy.md, traces.md, README.md (provenance, rules the scripts carry, drops)
```

The graph: `gather` → `hard-rules` → `by-rules` (router: auto_approve and auto_decline skip the
judgment) → `assess` (decision: `risk_tier` choice, `connected_exposure_material` noul, `outcome`
choice; thresholds 0.6 / 0.3 / 0.6) → `precedents` → `by-confidence` (router: a decline under G1 ends
the run unfiled for a human) → `rationale` (client task) → `check` → `gate` → `fix` → `recheck` →
`gate` → `record` → `end`.

Two things worth knowing from `source/README.md`:

- **What the judgment step sees.** `gather` removes dates of birth and every person's name from the
  whole state (owners become "owner 1", "owner 2"; the relationship manager becomes a role), and
  withholds any CRM note that mentions a personal characteristic, including the annual-review note
  that records an owner's age as "Priya (58)". The state `assess` received is stored on every run in
  the aip database, so "the model could not see it" is a query, not a promise.
- **Confidence.** The state the scripts see carries the decision model's collapsed answers, not its
  probabilities, so the filed `confidence` is 1.0 when the hard rules decided and the cleared
  threshold (0.6) when the decision model did. The exact probabilities are on the `Answer` nodes in
  the aip database (`queries.md` beat 6).
