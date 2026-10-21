# How the skill was compiled

Three inputs, one authoring session, one validated folder.

## 1. The source, read back out of memory

`blast traces export` runs Cypher against the memory graph (`src/blast/record.py`) and writes
two files into `skills/launch-email-blast/source/`:

- `sop.md`: the team's Notion page "How we run an email blast", exactly as imported.
- `traces.md`: the four recorded runs. For each: the prompt, every `blast` call in order with
  its JSON result, every judgment call as question / options / answer / why, and the agent's
  closing summary. About 220 lines.

The judgment calls are the important part. They were logged with `blast decide` during the runs,
so they sit in the graph as `ReasoningStep` nodes with the `Decision` label and typed fields, and
come out of the export as explicit decision points rather than prose to be guessed at.

## 2. The prompt

`prompts/author.md` tells a fresh Claude Code session to use the `aip` authoring skill on that
folder, and sets the constraints: the start input (`brief_id`, `send_at`), that scripts may call
`blast`, that the judgment calls become `decision` steps answered by the decision model, that
segment selection is a rule in the SOP and therefore a script, the three routers, one fix-up pass
and no loops, validate until clean, test locally once, write `source/README.md`.

```
make author      # claude -p "$(cat prompts/author.md)" with Read/Write/Edit/Bash/Skill allowed
```

## 3. The authoring skill

The `aip` skill (from [aip-spec](https://github.com/zach-blumenfeld/aip-spec)) does the compile:
read the source, choose a step kind for every item in the order the spec prescribes (script if it
can be code, decision if it is a judgment with a fixed answer space, client task only for
generation), write the YAML, the scripts, the templates and a reference file of worked examples
lifted from the traces, run `aip validate` until clean, run the procedure once locally against the
decision model, and record in `source/README.md` what came from where and what was dropped.

On 2026-10-21, against AIP format 0.6a1, this took 64 turns, 15 minutes and $9.48 (74K output
tokens, 4.3M cache-read tokens). The 0.6 format asks for more than 0.5a1 did: every execution and
client-task step declares its `outputs`, a `requires` block names the interpreter and the `blast`
tool the scripts need, and the validator checks the data flow (every key read is produced on every
path to it, by exactly one step). The session ran every script against synthetic state in a scratch
`BLAST_ROOT`, then two full local runs with the decision model (brief-003 as a launch; brief-012 as a
digest, where the subject pick fell under its threshold and paused for review). Earlier compiles of the
same source: 56 turns and $6.07 on format 0.5a1 (2026-10-07).

## What came out

`skills/launch-email-blast/`:

```
SKILL.md                 frontmatter + the AIP runtime block + requires + the procedure YAML (14 nodes)
scripts/load.py          blast brief/product/segments/brand; the segment rule              (execution)
scripts/submit.py        blast draft + blast check; check_passed and the failures           (execution)
scripts/schedule.py      send-time rule, blast schedule, blast decide, blast log --scheduled (execution)
scripts/close.py         three modes: legal hold, digest handoff, fix-up recheck; each logs (execution, used three times)
scripts/blastlib.py      shared helper: call blast, read the state, print exactly the declared outputs
assets/write.md          the client-task template for writing the email
assets/fix.md            the client-task template for the one fix-up pass
references/examples.md   claims rulings, a passing body, subject picks, what the check tests, from the traces
source/                  sop.md, traces.md, README.md (provenance and dropped items)
```

The graph (14 nodes: 10 working steps, 3 routers, 1 end): `load` → `classify` (decision:
`email_kind` choice, `urgency` score, `legal_review` noul; thresholds 0.6 / 0.6 / 0.3) → `by-legal`
(router: a legal flag goes to `hold`, which logs and ends) → `write` (client task) → `submit` →
`gate` (router) → `fix` (client task) → `recheck` → `end`, or → `pick-subject` (decision:
`subject_pick` choice, threshold 0.45) → `by-kind` (router) → `schedule` or `handoff` → `end`.

One shape changed from the 0.5a1 compile. There, a fixed draft rejoined the main path at the subject
pick. Under 0.6 every key has exactly one producer, so a branch cannot re-run `submit`'s outputs and
rejoin; the author chose to end the fix-up path after the recheck, logging the result either way, and
leave a fixed draft for a human to schedule. It is noted in `source/README.md` under "decisions taken
without asking".

`source/README.md` has the table that maps each SOP paragraph and trace pattern to a step, with
the reason for its kind, and the list of deliberate drops.
