# The loan demo on AIP

Lantern Mutual's business-loan assessment: built live from an SOP and a policy, run from Claude
Code and two agent frameworks, changed once and re-run, then rebuilt by `aip agent` on an empty
server. Everything is copy-paste. Background and why-it-is-this-way: `solutions/README.md`.

Applications and outcomes: APP-1001 refer, APP-1002 approve, APP-1003 decline, APP-1004 refer
(the decision model is not sure), APP-1005 refer. After part 3, APP-1004 is approve.

## Before the demo (once)

Needs: uv, Node 20+, Claude Code, the aip checkout at `~/dev/aip-0.9`, a TypeSafe key, an
Anthropic key.

```sh
cd ~/dev/graph-memory-system-one-demo/loan-aip-demo
cp .env.example .env            # then put your Anthropic key on the ANTHROPIC_API_KEY= line
aip config --decision-model-key <TYPESAFE_KEY>
make setup
make prebuild-4                 # part 4's first `aip agent`, once, before the demo; see solutions/part4.md
```

## Start (every time)

Terminal A:

```sh
cd ~/dev/graph-memory-system-one-demo/loan-aip-demo
set -a; source .env; set +a
make reset                      # fresh stores, both servers up: main :8300, empty :8301
make console                    # http://localhost:4280 in the background; `make down` stops it
```

If anything is off: `make down`, then `make reset` again. If port 4280 is taken, `make console`
names the process holding it: kill it, or set `AIP_DEMO_CONSOLE_PORT` in `.env`.

## Part 1: build it, live

1. Terminal B:

```sh
cd ~/dev/graph-memory-system-one-demo/loan-aip-demo && AIP_SESSION=build claude
```

2. Paste:

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

   Takes 3 to 4 minutes. Answer its questions if it asks.

   **Fallback** if the build goes wrong, in Terminal A: `make publish-solution`

3. Terminal C:

```sh
cd ~/dev/graph-memory-system-one-demo/loan-aip-demo && AIP_SESSION=run-1 claude
```

4. Paste:

> Use aip to run the published procedure `assess_business_loan` on APP-1001, APP-1003 and
> APP-1004, in parallel: start the three runs in one Bash call (in the background, collecting
> their output), then answer each run's pause with `aip resume`, writing the rationale its task
> asks for from the task's state. Do not assess the applications yourself and do not change the
> catalog. Report each application's outcome and run id.

5. Console, http://localhost:4280: open `assess_business_loan`. Step graph: control flow, then
   data flow, then everything, then run traffic.

6. Terminal A:

```sh
make check
```

   You see: APP-1001 refer, APP-1003 decline, APP-1004 refer, three ticks.

## Part 2: any agent

1. Terminal A:

```sh
uv run --project agents/adk python agents/adk/agent.py APP-1002 APP-1005
uv run --project agents/langgraph python agents/langgraph/agent.py APP-1004 APP-1001
```

   Each prints its tool list first: search, describe, run, resume. Nothing else.

2. Console: History, filter by agent: `cli`, `adk`, `langgraph`. Then by session.

## Part 3: change the rule

1. Terminal A, rule R3's coverage floor from 1.25 to 1.10:

```sh
sed -i '' 's/A ratio of 1.25 or more/A ratio of 1.10 or more/; s/from 1.00 up to 1.25/from 1.00 up to 1.10/' built/assess_business_loan/assets/policy.md
aip publish built/assess_business_loan
```

   If part 1 used the fallback: `make publish-v2` instead.

2. Terminal C, paste:

> Use aip to run the published procedure `assess_business_loan` on APP-1004 and APP-1001, in
> parallel, answering each pause with `aip resume`. Report each outcome and run id.

3. Terminal A:

```sh
uv run --project agents/adk python agents/adk/agent.py APP-1004
uv run --project agents/langgraph python agents/langgraph/agent.py APP-1004
```

4. Console: the procedure's revisions; the diff of 1 and 2; the new runs on revision 2.

5. Terminal A:

```sh
make check-v2
```

   You see: APP-1004 approve on revision 2, a tick; revision 1's runs unchanged.

## Part 4: the harness goes away

The first `aip agent` on the empty server, the one that built the procedure from scratch, was
done before the demo: `make prebuild-4` ran it once, timed it, and wrote `solutions/part4.md`
(the session id, how long it took, what it built, the outcome). `make reset` keeps that server
as it is. Live, the same session carries on.

1. Terminal A, pointed at the empty server and the session the build ran in:

```sh
export AIP_SERVER=http://127.0.0.1:8301
export AIP_SESSION=$(cat solutions/part4.session)
aip list
aip runs --session $AIP_SESSION
```

   You see: a catalog with one procedure that was not there before, and the session's runs:
   `assist`, the `build_procedure` it ran, and the first run of what it built. `solutions/part4.md`
   has the timing to say out loud.

2. Terminal A: `make console-empty`, then http://localhost:4281: the procedure the agent built,
   its step graph, and the build's runs under History.

3. Terminal A, the same session, a second application:

```sh
aip agent --progress "Now assess loan application APP-1002 the same way: approve, refer or decline, the rules that fired and a short rationale."
```

   You see: `search` finds the procedure, nothing is built, it runs, the outcome prints.

4. Terminal D:

```sh
cd ~/dev/graph-memory-system-one-demo/loan-aip-demo && AIP_SERVER=http://127.0.0.1:8301 claude
```

   Paste:

> Use aip to find the loan assessment procedure in the catalog and run it on APP-1003.

5. Terminal A:

```sh
make check-4
```

   You see: every run of the agent-built procedure on the empty server beside the known outcome.

6. The slide, the whole harness (`~/dev/aip-0.9/src/aip/agent.py`):

```python
def agent(client, chat, text, session):
    r = client.run("assist", {"task": text, "outcome": history(client, session, text)}, agent="agent", session=session)
    while isinstance(r, Paused):
        msg = message_for(client, r)
        for _ in range(4):                                   # one answer, up to three corrections
            reply = chat(msg)
            try:
                r = client.resume(r, parse(reply), agent="agent", session=session, work=work_of(reply, r))
                break
            except RunError as e:
                msg = msg + refused(reply, e)
        else:
            break                                            # left paused, for whoever answers next
    return r
```

## After

```sh
make down
aip config server local
```

## Layout

| Path | What |
|---|---|
| `source/` | policy, SOP, the five systems as JSON |
| `solutions/assess_business_loan/`, `-v2/`, `policy-v2.md` | the prebuilt procedure and its revision 2 |
| `solutions/README.md` | the design, what was run with run ids, what did not work, what aip is missing |
| `solutions/part4.md`, `part4.session`, `part4.name`, `prebuild_4.py` | part 4's pre-built `aip agent` session: the record, its id, the name it published, and the script `make prebuild-4` runs |
| `agents/adk/`, `agents/langgraph/` | the two framework agents |
| `check.py` | each run beside its expected outcome, tick or cross |
| `Makefile`, `.env.example`, `aip-server.toml` | setup, servers, console, reset |
