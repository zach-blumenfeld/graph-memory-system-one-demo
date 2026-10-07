# The story

Tessera Labs is a made-up open-source company. Its marketing team keeps everything in Notion:
four products and the claims they are allowed to make about each, the audiences they email, a
brand guide, and a page called "How we run an email blast" that new people get pointed at.

The team wants an agent to do email blasts. Here is what happens, in five beats.

## 1. The team's knowledge goes into a graph

The Notion workspace is loaded into Neo4j with the open-source `neo4j-agent-memory` library
(`blast import`). Products, claims, audiences, personas, the brand guide and the SOP page become
nodes; the relations between them become edges: this campaign promotes this product, this product
asserts these claims, every campaign is constrained by the brand guide and follows the SOP.

Show: `queries.md` beat 1. One campaign in the middle, everything it depends on around it.

### How this works

The import is two commands and four files.

1. `tools/make_fixture.py` invents the Notion workspace and writes it to `data/notion/`: one JSON
   file per Notion database (products, personas, audience segments, campaign briefs, brand guide,
   channels, campaign log), each page shaped the way the Notion API returns it, plus the SOP page
   as `sop_email_blast.md`.
2. `src/blast/fixture.py` reads those files back and flattens Notion's property objects into plain
   dicts. The `blast` tools in step 2 read the same files.
3. `src/blast/importer.py` turns every page into an entity and every Notion relation into an edge.
   Entities go through the memory SDK, `long_term.add_entity(name, type, ...)`, which writes an
   `Entity` node and adds the type as a second label (`Campaign`, `Product`, `Claim`, `Persona`,
   `Segment`, `Brand`, `Playbook`), then the page's fields are set as plain properties (`brief_id`,
   `send_window`, the SOP's full `text`, ...). The SDK stores every relationship as one generic
   `RELATED_TO` edge with the real type in a property, which is unreadable in Browser, so the six
   domain edges are written with the Neo4j driver as real edge types: `PROMOTES`, `ASSERTS`,
   `TARGETS`, `REPRESENTS`, `CONSTRAINED_BY`, `FOLLOWS`.
4. `blast import` runs it and then counts what landed (`blast verify import` on its own does just
   the count): 42 entities, 75 edges. `blast reset --yes` wipes the database to start over.

No embeddings and no entity extraction are switched on: nothing in this demo needs similarity
search, and the graph stays exactly what was imported plus what the agent did.

To do this with a real Notion workspace, replace item 1. Pull the databases with the Notion API
(`POST /v1/databases/{id}/query` returns pages in the shape the fixture mimics) and drop the JSON
into `data/notion/`. `fixture.py` already reads Notion's property objects. If your databases have
different names or fields, `plan()` in `importer.py` is the one function that maps pages to
entities and edges.

To see it, in Neo4j Browser on the memory database:

```cypher
MATCH (c:Campaign {brief_id: 'brief-001'})
MATCH p = (c)-[]->(n)
OPTIONAL MATCH q = (n)-[:ASSERTS|REPRESENTS]-(m)
RETURN p, q
```

One campaign in the middle. One hop out: the product it promotes, the segment it targets, the
brand guide it must obey, the SOP page it follows. Two hops out: the product's approved claims,
and the persona who represents the segment. About 12 nodes, and each answers one of the questions
the agent must settle before it writes a word: what am I selling, what may I say about it, who am
I talking to, how must I sound, what is the process.

Labels are real, so Browser colours by class out of the box; set the caption to `name`. Change the
`brief_id` to `brief-013` for the live-demo brief, or drop the `{brief_id: ...}` filter and add
`WITH c LIMIT 3` after the first line for a few campaigns side by side. `queries.md` beat 1 has
the same query and the one that prints the SOP page.

## 2. The agent does the job four times, from the SOP, and the graph watches

Claude Code gets a brief and one instruction: start by reading the team's page (`blast sop`). It
has no skill and no MCP server, only a `blast` command for the things an agent cannot do by hand:
read the brief, the product, the audiences and the brand guide; store a draft; run the compliance
check; schedule; log. The SOP says to log every judgment call (`blast decide`): what kind of email
this is, how urgent, whether legal needs to see it, which segment, which subject line.

Three Claude Code hooks record everything into the same graph with the SDK: the prompt and the
closing answer as a conversation, and every `blast` call as a reasoning step with its tool call,
in order, with inputs, outputs and status. Judgment calls get a `Decision` label.

Four runs were recorded headlessly (`blast record --all`): two launches, a monthly digest, an
urgent hotfix. The agent worked out the procedure itself every time: 12 to 18 `blast` calls and
6 or 7 judgment calls per run, 5 to 8 minutes and 50 to 90 cents each with the default model.
In run-01 it read the brand guide before writing, so the draft passed first time, and two of its
judgment calls were about claims the brief wanted that were not on the approved list. In run-03
it decided a digest is not scheduled. In run-04 it classified the hotfix as urgent and scheduled
it the same morning.

Show: `queries.md` beat 2, the run as a table, then the judgment calls grouped by question.
Live option: `claude` in this folder, paste a brief, watch it go; about five minutes with the
default model, so prefer the recorded run on stage.

### How this works

Three pieces, all in this folder, all picked up automatically when you run `claude` here.

**The tools.** One shell command, `blast`, with ten subcommands. Claude calls it through its
built-in Bash tool, the way it would call `git`; there is no MCP server and no tool schema. The
agent learns what exists from `blast --help` and from the SOP.

| command | what it does |
|---|---|
| `blast sop` | the team's "How we run an email blast" page, read from the graph (`Playbook` node) |
| `blast brief <id>` | one brief: product, goal, key messages, call to action, send window, notes |
| `blast product <name>` | the product, its docs and repo URLs, its approved claims |
| `blast segments <product>` | the audience segments for a product, each with its persona and tone notes |
| `blast brand` | voice rules, banned claims, required disclaimer, subject-line rules |
| `blast draft <campaign> --body-file F --subject S --subject S --subject S --segment SEG` | store a draft, get a draft id |
| `blast check <draft>` | the compliance check: disclaimer verbatim, no banned phrases, no exclamation marks, the brief's call to action or a link present, subject-line rules; returns pass or the named failures |
| `blast schedule <draft> --segment SEG --at T --subject S` | schedule a checked draft; refuses an unchecked one |
| `blast log <campaign> --draft D --summary TEXT [--scheduled]` | append to the campaign log |
| `blast decide --question Q --options a,b,c --answer A --why TEXT` | log a judgment call |

The logic is `src/blast/tools.py`, one plain function per command; `src/blast/cli.py` wraps them
and prints JSON. `uv tool install --editable .` puts `blast` on PATH. The check is deterministic
code over the brand guide and the brief; the only judgments in the whole system are the ones the
agent logs with `blast decide`, which is the point: those are what become decision steps.

**The hooks.** `.claude/settings.json` attaches three Claude Code hooks to `blast-hook`
(`src/blast/hooks.py`), each a separate process that opens the memory SDK over bolt:

- `UserPromptSubmit`: starts a reasoning trace for the session (`reasoning.start_trace`) and
  stores the prompt as a user message (`short_term.add_message`). The Claude session id is the
  memory session id, so one `Conversation` per Claude session; the trace id is kept in
  `.run/sessions/<session id>.json` for the other hooks.
- `PostToolUse`, Bash only: ignores anything that is not a `blast` command. For a `blast` command
  it writes a `ReasoningStep` (`reasoning.add_step`, thought and action) and a `ToolCall`
  (`reasoning.record_tool_call`: tool name, the parsed arguments, the JSON result, success or
  failure). For `blast decide` it also sets the `Decision` label on the step with `question`,
  `options`, `answer` and `why` as properties.
- `Stop`: stores Claude's final answer as an assistant message and completes the trace.

Hooks never fail the session: an error is written to `.run/recorder.log` and the hook exits 0.
`BLAST_RECORD=0` switches recording off.

So one run produces, in the graph: `(:Conversation)-[:HAS_MESSAGE]->(:Message)` twice, and
`(:ReasoningTrace)-[:HAS_STEP]->(:ReasoningStep)-[:USES_TOOL]->(:ToolCall)` once per `blast`
call in order, with some steps also labelled `Decision`. That is the memory SDK's own schema;
nothing here was designed, only the labels on the entities and the `Decision` label were added.

**The four recorded runs.** `blast record --all` (or `blast record run-03`) runs each entry of
`prompts/runs.yaml` through headless Claude Code: a short preamble ("start by reading the team's
page with `blast sop`") plus the brief, `--tools Bash,Read,Write`, Bash restricted to `blast`,
skills disallowed, an empty MCP config, and the hooks doing the recording. When the session
ends, the run's trace is read back out of the graph and saved to `checkpoints/traces/<run>.json`;
`blast traces show run-01` prints it, `blast verify traces` checks the four did what their kind
requires (launches scheduled, the digest not).

**To show it live.** `claude` in this folder, then paste a brief (the text of any `prompt:` in
`prompts/runs.yaml` works; keep the preamble so it reads the SOP first). Expect five minutes with
the default model, most of it the model thinking between calls, so on stage prefer
`blast traces show run-01` and the queries. If you do run it live, `tail -f .run/recorder.log`
in a second terminal shows each step land, and this shows the run as it grows:

```cypher
MATCH (t:ReasoningTrace)
WITH t ORDER BY t.started_at DESC LIMIT 1
MATCH (t)-[:HAS_STEP]->(s:ReasoningStep)-[:USES_TOOL]->(tc:ToolCall)
RETURN s.step_number AS n,
       CASE WHEN s:Decision THEN 'decision: ' + s.question + ' -> ' + s.answer ELSE tc.tool_name END AS what,
       tc.status AS status
ORDER BY s.step_number
```

**To set this up elsewhere.** Clone, `uv sync`, `uv tool install --editable .`, fill `.env` with
a Neo4j connection, `blast import`. `.claude/settings.json` is committed, so any `claude` session
started in the folder gets the hooks. For your own agent and your own tools the pattern is the
same four SDK calls, from wherever your agent sees prompts, tool calls and answers:
`short_term.add_message`, `reasoning.start_trace`, `reasoning.add_step` with
`reasoning.record_tool_call`, `reasoning.complete_trace`. The judgment log is the one habit to
carry over: give the agent a way to record a question, its options, its answer and why.

## 3. The SOP and the four traces become an AIP skill

`blast traces export` reads the traces back out of memory and writes two files into
`skills/launch-email-blast/source/`: the SOP page and `traces.md`, every call and every judgment of the
four runs in order. Then Claude Code, with the `aip` authoring skill, compiles the folder into an
AIP procedure: a typed step graph. The SOP's rules become scripts (`execution`), the judgment calls
become `decision` steps with typed questions, the one thing only a language model can do (write the
email) becomes a `client_task`, and the branches the traces showed (digest is not scheduled, legal
flag stops the run, one fix-up pass after a failed check) become routers.

Show: `skills/launch-email-blast/SKILL.md`, and `source/README.md` for what was kept and dropped.

## 4. The skill is published to the aip server, where Jev answers the decisions

`aip publish ./skills/launch-email-blast` puts it in the catalog. The server stores the procedure as a
graph in its own Neo4j database and answers every `decision` step with TypeSafe's Jev: typed
answers with calibrated probabilities. Below the threshold, the run pauses for a human.

Show: the inspector catalog page (the step graph), and `queries.md` beat 4.

## 5. A fresh agent runs the skill

New Claude Code session with the `aip-runtime` skill. It searches the catalog, finds the skill,
starts a run, and only does what the server hands back: writes the email at the client task,
confirms any low-confidence decision. The server runs the scripts, Jev makes the judgment calls,
the run is recorded step by step.

Measured on 2026-10-07, same brief, fresh session each time:

| | turns | wall | cost | pauses for the agent |
|---|---|---|---|---|
| free-form agent from the SOP (step 2) | 14 to 32 | 5 to 8 min | $0.50 to $1.03 | n/a, it did everything |
| published skill, default model | 20 | 100 to 120 s | $1.37 | 1 (write the email) |
| published skill, Sonnet | 15 | 70 s | $0.27 | 2 (write, then one fix-up after a failed check) |

Jev answered every decision above its threshold: launch at 1.0, normal urgency at 0.98, no legal
review at 0.11. The agent never saw those questions.

Show: the live run, then the inspector history and `queries.md` beat 5.

## Token usage, measured

From Claude Code's own accounting (`modelUsage` in the JSON result of each headless session).
"Cache read" is context re-sent from the prompt cache each turn; "output" is what the model wrote.

| session | turns | new input | output | cache read | cache write | total tokens | cost |
|---|---|---|---|---|---|---|---|
| free-form run-01 (launch) | 17 | 290 | 7,685 | 139,819 | 22,086 | 169,880 | $0.86 |
| free-form run-02 (launch) | 21 | 322 | 6,544 | 155,492 | 15,067 | 177,425 | $0.67 |
| free-form run-03 (digest) | 14 | 258 | 4,706 | 108,423 | 11,921 | 125,308 | $0.50 |
| free-form run-04 (hotfix) | 22 | 386 | 6,744 | 187,661 | 14,946 | 209,737 | $0.69 |
| skill run, default model | 20 | 484 | 7,912 | 600,023 | 41,155 | 649,574 | $1.37 |
| skill run, Sonnet | 15 | 28 | 4,583 | 405,240 | 35,173 | 445,024 | $0.27 |
| compiling the skill (one-off) | 56 | 708 | 46,243 | 2,642,879 | 154,303 | 2,844,133 | $6.07 |

Honest reading: the skill run is three to five times faster and moves every judgment call off the
language model, but it does not use fewer tokens. The agent's own output is about the same (it
still writes the email), and the client loop carries the whole run state through its context on
every turn, so cache reads are three to four times higher. What the skill buys is time, consistency
and calibrated decisions, not token count. Sonnet makes it cheap anyway. Trimming the state the
server hands back at each pause is the obvious next optimisation.

## What the title means

Agent knowledge: the four recorded runs. Distilling: compiling the SOP and the traces into the
skill. System One workflow: the judgment calls answered by a fast, typed, calibrated model on the
server instead of a language model improvising. Graph memory: the one graph that holds the team's
knowledge and the agent's traces, and the second graph that holds the procedure and its runs.

## What is real and what is made up

Everything about Tessera Labs is invented. The software is real: Claude Code, neo4j-agent-memory,
Neo4j Aura, AIP, TypeSafe's Jev.
