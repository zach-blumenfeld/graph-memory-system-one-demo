# How the recording works

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

