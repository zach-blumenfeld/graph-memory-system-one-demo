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

How: `tools/make_fixture.py` invents the workspace as Notion-shaped JSON in `data/notion/`;
`src/blast/importer.py` writes it through the SDK (`long_term.add_entity`) and adds the typed
edges. Two commands: `blast import`, `blast verify import`.

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

## What the title means

Agent knowledge: the four recorded runs. Distilling: compiling the SOP and the traces into the
skill. System One workflow: the judgment calls answered by a fast, typed, calibrated model on the
server instead of a language model improvising. Graph memory: the one graph that holds the team's
knowledge and the agent's traces, and the second graph that holds the procedure and its runs.

## What is real and what is made up

Everything about Tessera Labs is invented. The software is real: Claude Code, neo4j-agent-memory,
Neo4j Aura, AIP, TypeSafe's Jev.
