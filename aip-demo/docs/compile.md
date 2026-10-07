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

On 2026-10-07 this took 56 turns, 9.7 minutes and $6.07, and needed one YAML quoting fix that the
validator caught.

## What came out

`skills/launch-email-blast/`:

```
SKILL.md                 frontmatter + the AIP runtime block + the procedure YAML (13 nodes)
scripts/load.py          blast brief/product/segments/brand; segment rule          (execution)
scripts/submit.py        blast draft + blast check; sets check_state passed/fix/stop (execution, used twice)
scripts/schedule.py      send-time rule, blast schedule, blast decide x4, blast log   (execution)
scripts/close.py         not-scheduled log with the reason (legal, digest, 2nd fail) (execution)
scripts/blastlib.py      shared helper
assets/write.md          the client-task template for writing the email
assets/fix.md            the client-task template for the one fix-up pass
references/examples.md   claims rulings, a passing body, subject picks, from the traces
source/                  sop.md, traces.md, README.md (provenance and dropped items)
```

The graph: `load` → `classify` (decision: `email_kind` choice, `urgency` score, `legal_review`
noul) → `by-legal` (router) → `write` (client task) → `submit` → `gate` (router) → `fix` →
`resubmit` → `gate` → `pick-subject` (decision: `subject_pick` choice) → `by-kind` (router) →
`schedule` or `close` → `end`.

`source/README.md` has the table that maps each SOP paragraph and trace pattern to a step, with
the reason for its kind, and the list of deliberate drops.
