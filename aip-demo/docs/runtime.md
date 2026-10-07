# Running the graph skill

Two ways to run `skills/launch-email-blast`, same file.

**As an ordinary Agent Skill.** Drop the folder into `.claude/skills/` and the agent reads
`SKILL.md`, whose runtime block tells it how to walk the graph itself: run the scripts, answer the
decisions by its own judgment, do the client tasks, follow the routers. Portable, no server, but
every decision is the language model's and nothing enforces the order.

**Through the aip server** (what the demo does). `aip publish` puts the folder in the catalog,
stored as a graph in the server's own Neo4j. The server walks the graph: it validates each step's
input, runs the scripts in its own process, sends each `decision` step's questions to TypeSafe's
Jev and gets typed answers with probabilities, follows the routers, and records every step
against the revision that ran. The agent only sees the pauses: a `client_task` to perform, or a
`review` when an answer fell under its confidence threshold. The architecture diagram and the
full description are in the [AIP README](https://github.com/zach-blumenfeld/aip/tree/aip-0.5a0#how-it-works).

## Commands

Server, once, in its own terminal (reads `~/.config/aip/server.toml`: the Neo4j backend and the
TypeSafe key):

```
aip server --inspector            # http://localhost:8000/inspector/
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

Or the inspector's run tab, with buttons.

## What you get for the graph shape

- **Speed.** The same job that took the free-form agent five to eight minutes and 14 to 32 turns
  takes 70 to 120 seconds and one pause: the server does the walking, Jev does the judging, the
  agent writes the email.
- **Consistency.** The order is the graph, not the model's mood. Compliance before scheduling,
  digest never scheduled, legal flag stops the run, one fix-up pass and no loops. Four free-form
  runs did these in four slightly different orders; every skill run does them in one.
- **Calibrated decisions.** `email_kind`, `urgency`, `legal_review`, `subject_pick` come back
  with probabilities. Under the threshold the run pauses for a human; above it, nobody is asked.
  In the measured runs: launch 1.0, normal urgency 0.98, no legal review 0.11.
- **A record.** Every run is `Run` → `StepRun` → `Answer` in the aip database, so the
  governance views can ask which decisions humans overrode, which scripts failed, which branches
  no run has taken. `queries.md` beat 5.
- **Not fewer tokens.** The agent still writes the email, and the client loop carries the run
  state through its context each turn; see the token table in `STORY.md`.
