# How the recording works

Three pieces, all in this folder, all picked up automatically when you run `claude` here.

**The tools.** One shell command, `loan`, with twelve subcommands for the analyst. Claude calls it
through its built-in Bash tool, the way it would call `git`; there is no MCP server and no tool
schema. The agent learns what exists from `loan --help` and from the team's page.

| command | what it does |
|---|---|
| `loan sop` | the credit team's "How we assess a business loan" page, read from the graph (`Playbook` node) |
| `loan application <id>` | the application, the business, its owners (name and share only, never a date of birth), the relationship manager, the CRM notes |
| `loan ownership <business>` | the owners, and every other business each owner holds 25% or more of, with those businesses' open facilities and their worst payment status. Two hops through `OWNS`, from the graph |
| `loan facilities <business>` | the business's facilities, their payments, and days late per facility |
| `loan cashflow <business>` | 12- and 24-month average inflow, outflow and net across the business's accounts, with the `Month` keys cited |
| `loan kyc <business>` | the KYC record and any fraud events |
| `loan policy <application>` | R1–R6 and G1 applied: `outcome` (auto_approve, auto_decline, review), the rules that `fired` with value, threshold and cites, the `figures` |
| `loan precedents <application>` | filed `Decision` nodes on applications of the same product in the same policy band; empty before the first run |
| `loan rationale submit --file F --application ID --outcome O` | stores the write-up under `.run/rationales/`, returns its id |
| `loan check <rationale>` | the lint: every `[cite: KEY]` names a node in the graph; every dollar figure, ratio, percentage and day count matches a figure the systems hold; the first paragraph states the outcome; no protected characteristic is mentioned |
| `loan record <rationale> --outcome O --confidence C --revision R` | files the decision as a `Decision` node with `ABOUT`, `APPLIED_POLICY`, `CITES`, `PRECEDENT_FOR`; refuses an unchecked rationale |
| `loan decide --question Q --options a,b,c --answer A --why TEXT` | logs a judgment call |

The logic is `src/loan/tools.py`, one plain function per command, reading the graph with Cypher;
`src/loan/cli.py` wraps them and prints JSON. The policy itself is `src/loan/policy.py`, shared
with the fixture check and the tests. `uv tool install --editable .` puts `loan` on PATH. Every
figure a write-up might quote comes back with the keys it was computed from, which is what makes
`loan check` possible: a rationale can only cite what the systems hold.

**The hooks.** `.claude/settings.json` attaches three Claude Code hooks to `loan-hook`
(`src/loan/hooks.py`), each a separate process that opens the memory SDK over bolt:

- `UserPromptSubmit`: starts a reasoning trace for the session (`reasoning.start_trace`) and
  stores the prompt as a user message (`short_term.add_message`). The Claude session id is the
  memory session id, so one `Conversation` per Claude session; the trace id is kept in
  `.run/sessions/<session id>.json` for the other hooks.
- `PostToolUse`, Bash only: ignores anything that is not a `loan` command. For a `loan` command
  it writes a `ReasoningStep` (`reasoning.add_step`, thought and action) and a `ToolCall`
  (`reasoning.record_tool_call`: tool name, the parsed arguments, the JSON result, success or
  failure). For `loan decide` it also sets the `Decision` label on the step with `question`,
  `options`, `answer` and `why` as properties.
- `Stop`: stores Claude's final answer as an assistant message and completes the trace.

Hooks never fail the session: an error is written to `.run/recorder.log` and the hook exits 0.
`LOAN_RECORD=0` switches recording off.

The package keeps a session's `Conversation` and its `ReasoningTrace` as separate nodes that only
share a `session_id`; the prompt hook adds one `(:Conversation)-[:HAS_TRACE]->(:ReasoningTrace)`
edge so a run is a single connected subgraph.

So one run produces, in the graph: `(:Conversation)-[:HAS_MESSAGE]->(:Message)` twice, and
`(:ReasoningTrace)-[:HAS_STEP]->(:ReasoningStep)-[:USES_TOOL]->(:ToolCall)` once per `loan` call in
order, with the judgment calls also labelled `Decision`. And, because the agent ends with
`loan record`, a filed `(:Decision:Filed)` node hanging off the application with its `CITES`
edges into the evidence. The filed decision and the judgment-call steps share the `Decision`
label on purpose: both are decisions the graph can be asked about; `Filed` and `ReasoningStep`
tell them apart.

**The five recorded runs.** `loan record --all` (or `loan record run-03`) runs each entry of
`prompts/runs.yaml` through headless Claude Code: a short preamble ("start by reading the team's
page with `loan sop`") plus one application, `--tools Bash,Read,Write`, Bash restricted to `loan`,
skills disallowed, an empty MCP config, and the hooks doing the recording. When the session ends,
the run's trace is read back out of the graph and saved to `checkpoints/traces/<run>.json`;
`loan traces show run-01` prints it, `loan verify traces` checks that every run exited cleanly,
ran `loan check`, logged at least one judgment call and filed a decision, and reports (without
asserting) whether run-01 and run-05, the same application twice, both walked the ownership graph.

**To show it live.** `claude --disallowedTools Skill` in this folder, then paste the text of any
`prompt:` in `prompts/runs.yaml` after the preamble. The flag matters: with skills enabled, the
`aip-runtime` skill would spot that a matching procedure is published and run that instead.
Expect several minutes with the default model, most of it the model thinking between calls, so on
stage prefer `loan traces show run-01` and the queries. If you do run it live, `tail -f
.run/recorder.log` in a second terminal shows each step land, and this shows the run as it grows:

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
a Neo4j connection, `loan import`. `.claude/settings.json` is committed, so any `claude` session
started in the folder gets the hooks. For your own agent and your own tools the pattern is the
same four SDK calls, from wherever your agent sees prompts, tool calls and answers:
`short_term.add_message`, `reasoning.start_trace`, `reasoning.add_step` with
`reasoning.record_tool_call`, `reasoning.complete_trace`. The judgment log is the one habit to
carry over: give the agent a way to record a question, its options, its answer and why.
