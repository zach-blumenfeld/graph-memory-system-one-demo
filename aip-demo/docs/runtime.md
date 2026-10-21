# Running the graph skill

Two ways to run `skills/launch-email-blast`, same file.

**As an ordinary Agent Skill.** Drop the folder into `.claude/skills/` and the agent reads
`SKILL.md`, whose runtime block tells it how to walk the graph itself: run the scripts, answer the
decisions by its own judgment, do the client tasks, follow the routers. Portable, no server, but
every decision is the language model's and nothing enforces the order.

**Through the aip runtime** (what the demo does). `aip publish` puts the folder in the catalog,
stored as a graph in the server's own Neo4j. The server and the `aip` client split the walk the way
CI systems do, orchestration central and work next to the data. The server validates each step's
input and output against what the step declared, follows the routers, and records every step
against the revision that ran. The client (the `aip` command on the agent's machine) fetches the
revision's `scripts/` and `assets/` once, runs each execution step's script where `blast` and the
`.env` are, and sends each `decision` step's questions to TypeSafe's Jev with the author's
thresholds. The server holds no model key and runs no user code. The agent only sees the pauses: a
`client_task` to perform, or a `review` when an answer fell under its confidence threshold. The
architecture diagram and the full description are in the
[AIP README](https://github.com/zach-blumenfeld/aip#how-it-works), the design note in
[docs/client-execution.md](https://github.com/zach-blumenfeld/aip/blob/main/docs/client-execution.md).

## Commands

Server, once, in its own terminal (reads `~/.config/aip/server.toml`: the Neo4j backend; no model
key), and the console in another:

```
aip server
npx aip-console --server http://localhost:8000     # http://localhost:4280/
aip config --decision-model "$TYPESAFE_API_KEY"    # once, on the client
aip publish ./skills/launch-email-blast
aip list
```

From an agent: the `aip-runtime` skill (installed by `aip skill install claude-code`) makes
Claude Code search the catalog, inspect the match, start the run and answer the pauses:

```
make fresh                        # forget earlier local runs and drafts
claude --model sonnet             # or plain claude
> Launch the email blast for brief-013, "riverbed 2.0 release", send 2026-11-04 09:00 UTC.
```

From a terminal, no agent, answering the client task yourself:

```
aip run launch-email-blast --input checkpoints/start-brief-013.json --interactive
```

Or the console's run tab, with buttons: it spawns the same `aip run` on this machine.

## What you get for the graph shape

- **Speed, sometimes.** On the day of this build the free-form agent took 91 to 120 seconds and 17
  to 19 turns; the skill run took 135 seconds with the default model driving and 58 seconds with
  Sonnet. The `aip run` itself is about a minute (scripts here, Jev on the client, routing on the
  server); the rest is the agent reading the skill, searching the catalog and writing the email. The
  smaller model gets the same result because the procedure carries the work.
- **Consistency.** The order is the graph, not the model's mood. Compliance before scheduling,
  digest never scheduled, legal flag stops the run, one fix-up pass and no loops. Four free-form
  runs did these in four slightly different orders; every skill run does them in one.
- **Calibrated decisions.** `email_kind`, `urgency`, `legal_review`, `subject_pick` come back
  with probabilities. Under the threshold the run pauses for a human; above it, nobody is asked.
  In the measured runs: launch 1.00, normal urgency 1.00, no legal review 0.89, subject pick 0.46 and
  0.55 against a 0.45 threshold.
- **A record.** Every run is `Run` → `StepRun` → `Answer` in the aip database, each answer with
  its resolver (`typesafe` or `manual`), model and review status, so the governance views can ask
  which decisions humans overrode, which were answered by hand, which scripts failed (with the
  client's stderr), which branches no run has taken. `queries.md` query 7.
- **Not fewer tokens.** The agent still writes the email, and the client loop carries the run
  state through its context each turn; the table below has the numbers.

## Token usage, measured

From Claude Code's own accounting (`usage` in the JSON result of each headless session).
"Cache read" is context re-sent from the prompt cache each turn; "output" is what the model wrote.

| session | turns | new input | output | cache read | cache write | total tokens | cost |
|---|---|---|---|---|---|---|---|
| free-form run-01 (launch) | 19 | 258 | 6,788 | 120,278 | 21,438 | 148,762 | $0.80 |
| free-form run-02 (launch) | 17 | 258 | 7,007 | 123,551 | 14,724 | 145,540 | $0.68 |
| free-form run-03 (digest) | 18 | 258 | 5,092 | 115,519 | 13,109 | 133,978 | $0.55 |
| free-form run-04 (hotfix) | 17 | 322 | 6,910 | 159,645 | 15,747 | 182,624 | $0.70 |
| skill run, default model | 16 | 324 | 6,836 | 695,204 | 59,639 | 762,003 | $1.71 |
| skill run, Sonnet | 14 | 24 | 3,566 | 530,242 | 41,859 | 575,691 | $0.26 |
| compiling the skill (one-off) | 64 | 772 | 74,137 | 4,272,297 | 234,904 | 4,582,110 | $9.48 |

Honest reading: on this day the free-form agent was already fast (91 to 120 s), and the skill run with the
default model was not faster (135 s); the Sonnet-driven skill run was (58 s). The skill run does not use fewer
tokens either: the agent still writes the email, and the client loop carries the run state through its context
each turn, so cache reads are four to five times higher. What the skill buys is the order (compliance before
scheduling, one fix-up pass, digests never scheduled), decisions with a calibrated probability instead of the
language model's, a smaller driving model that gets the same result, and a record of every step.
