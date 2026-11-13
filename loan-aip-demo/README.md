# The loan demo on AIP

Lantern Mutual's business-loan assessment, built live from an SOP and a policy into an AIP
procedure, run from Claude Code and from two agent frameworks, changed once and re-run, and then
rebuilt by `aip agent` on an empty server. Four parts; the audience should see what each part's
last line says.

The material is `source/`: `policy.md` (rules R1 to R7 and guidance G1), `sop_assess_loan.md`,
and the bank's five systems as JSON (`core_banking`, `loans`, `compliance`, `ownership`, `crm`).
Five applications, APP-1001 to APP-1005. The procedure's scripts read the JSON directly; no
agent memory, no graph database. The 50-application generator is not part of this: it would come
from `loan-demo/tools/make_fixture.py` and `loan-demo/src/loan/policy.py`.

## Prerequisites

- [uv](https://docs.astral.sh/uv/), Node 20 or newer, [Claude Code](https://claude.com/claude-code).
- aip 0.9 is not on PyPI yet. The checkout is `~/dev/aip-0.9` (branch `release-0.9.0`); `make
  setup` installs it with `uv tool install --force 'agent-instruction-protocol[server] @
  ~/dev/aip-0.9'`, so `aip --version` prints `aip 0.9.0 language 0.9`.
- A TypeSafe key in `aip config` (`aip config --decision-model-key KEY`): the procedure's one
  `Decide` asks it.
- The agents' model is Claude. Export `ANTHROPIC_API_KEY` in every terminal you open (the two
  framework agents read it); `aip agent` reads `AIP_AGENT_MODEL_KEY` and `AIP_AGENT_MODEL_NAME`,
  or `aip config agent --model-key KEY`.
- Copy `.env.example` to `.env`. `AIP_DEMO_BACKEND=local` keeps the main server's store in
  `.aip/main.rl`; `aura` puts it in the Aura database named there. Start with `local`.

## Setup

```sh
cd ~/dev/graph-memory-system-one-demo/loan-aip-demo
cp .env.example .env
make setup          # aip from the checkout, the aip skill into Claude Code, aip config server -> the main server, the agents' venvs, the console
make up             # two servers: main http://127.0.0.1:8300 (parts 1 to 3) and empty http://127.0.0.1:8301 (part 4)
make console        # http://localhost:4280/ on the main server; leave it running in its own terminal
```

`make setup` points `aip config server` at the main server, so every `aip` command and every
agent on this machine records there. `aip config server local` puts it back afterwards. `make
down` stops the servers; `make reset` forgets both stores and starts again.

## Part 1: build it, live

**Terminal one**, Claude Code with the aip skill:

```sh
cd ~/dev/graph-memory-system-one-demo/loan-aip-demo && AIP_SESSION=build claude
```

Paste:

> Use aip to build a procedure named `assess_business_loan` from the material in `./source`:
> compile `sop_assess_loan.md` and `policy.md` into a procedure that assesses one business-loan
> application. Its input is the application id (APP-1001 to APP-1005); its result is the outcome
> (approve, refer or decline), the rules that fired, and the written rationale. The hard rules
> R1 to R7 are scripts that read the five JSON files under `source/` (relative to the working
> directory) and read every threshold from a copy of the policy kept at `assets/policy.md`, so a
> rule change is an edit to that file; the risk judgment the SOP leaves open is one `Decide`
> (risk tier, whether connected exposure is material, outcome), with a confidence check that
> refers the case when the model is not sure; the rationale is the one `Task_Agent`. Nothing
> about an owner's age or date of birth reaches the judgment or the rationale. Write it to
> `./built/assess_business_loan`, compile it until it compiles, then publish it as
> `assess_business_loan`. Do not read `./solutions`.

If the build goes wrong: `make publish-solution` publishes the prebuilt, tested procedure under
the same name, and the rest of the demo is unchanged.

**Terminal two**, a second Claude Code session:

```sh
cd ~/dev/graph-memory-system-one-demo/loan-aip-demo && AIP_SESSION=run-1 claude
```

Paste:

> Use aip to run the published procedure `assess_business_loan` on APP-1001, APP-1003 and
> APP-1004, in parallel: start the three runs in one Bash call (in the background, collecting
> their output), then answer each run's pause with `aip resume`, writing the rationale its task
> asks for from the task's state. Do not assess the applications yourself and do not change the
> catalog. Report each application's outcome and run id.

**The console** (http://localhost:4280/): open `assess_business_loan`; the step graph in control
flow, then data flow, then everything, then run traffic. Then:

```sh
make check
```

The audience sees three runs in under a minute, APP-1001 refer, APP-1003 decline, APP-1004
refer, each a tick, with the one `Decide` (APP-1004) and its confidence in the record.

## Part 2: any agent

`agents/adk/` and `agents/langgraph/` are small agents on Claude whose only tools are `aip mcp`'s
`search`, `describe`, `run` and `resume`: no `compile`, no `publish`, no `agent`. They can run
procedures and answer their pauses, and nothing else; the first line each prints is its tool
list. Each runs its applications in parallel, one `aip mcp` process per application, under one
session id.

```sh
uv run --project agents/adk python agents/adk/agent.py APP-1002 APP-1005
uv run --project agents/langgraph python agents/langgraph/agent.py APP-1004 APP-1001
```

The console's History (`#/runs`), filtered by agent and by session: `cli`, `adk` and
`langgraph` side by side, the same procedure, the same record, no code written for aip in
either framework beyond the MCP connection.

## Part 3: change the rule

Edit one threshold in the procedure's policy, `built/assess_business_loan/assets/policy.md`, rule R3:
`A ratio of 1.25 or more may be approved without judgment. A ratio from 1.00 up to 1.25 goes to
review.` becomes `... 1.10 or more ... from 1.00 up to 1.10 ...`. APP-1004's coverage is 1.15,
the application closest to a line: the case the decision model had to judge (and referred, not
being sure) is now approved by the rule, and the `Decide` drops out of its path.
(`solutions/README.md` says why this is the change.) Republish under the same name; it becomes
revision 2:

```sh
aip publish built/assess_business_loan        # or: make publish-v2
```

Run again from all three agents (Claude Code: the terminal-two prompt again, with APP-1004 and
APP-1001; the two commands of part 2 again). The console: the procedure's revisions, the diff
between 1 and 2 (`#/p/assess_business_loan/diff`), the new runs on revision 2. Then:

```sh
make check-v2
```

The audience sees APP-1004 flip from refer to approve on revision 2, with a tick, while every
run on revision 1 keeps its own expectations.

## Part 4: the harness goes away

The empty server has nothing but the procedures aip ships. Point a shell at it and hand the task
to `aip agent`:

```sh
cd ~/dev/graph-memory-system-one-demo/loan-aip-demo
export AIP_SERVER=http://127.0.0.1:8301
aip list
aip agent --new --progress "Assess loan application APP-1004 under Lantern Mutual's lending policy and SOP in ./source (policy.md and sop_assess_loan.md; the bank's five systems are the JSON files there). Report approve, refer or decline, with the rules that fired and a short rationale. If no procedure in the catalog does this, build one from ./source and write it under ./built, then run it."
```

Watch the progress lines: `search` finds nothing, `build_procedure` runs, a name is published,
the new procedure runs, and the command ends with the outcome. Then Claude Code on the same
server runs what the agent built:

```sh
AIP_SERVER=http://127.0.0.1:8301 claude
```

> Use aip to find the loan assessment procedure in the catalog and run it on APP-1002.

A second console shows it: `make console-empty` (http://localhost:4281/). For the slide, the
whole harness is this loop in `src/aip/agent.py`:

```python
result = self.client.run(target, inputs, agent=AGENT, session=session, on_step=on_step)
while isinstance(result, Paused):
    answered = self.answer(result, session, out, on_step)   # one model call, no tools
    if answered is None:
        out.status, out.pause = "paused", result.to_json()
        return out
    result = answered
```

The audience sees an agent with no tools and no prompt engineering build the procedure it
needs, run it, and finish with the outcome, with every step on the server's record.

## Layout

| Path | What |
|---|---|
| `source/` | the material: policy, SOP, the five systems as JSON |
| `solutions/assess_business_loan/` | the procedure, prebuilt and tested; `make publish-solution` |
| `solutions/assess_business_loan-v2/`, `solutions/policy-v2.md` | the same with R3's coverage floor at 1.10; `make publish-v2` |
| `solutions/README.md` | what was run, with run ids, what did not work, and what aip is missing |
| `agents/adk/`, `agents/langgraph/` | the two framework agents, each its own uv project |
| `check.py` | every run beside its expected outcome, tick or cross |
| `Makefile`, `.env.example`, `aip-server.toml` | setup, servers up and down, reset, the console; the demo's own server config |
