# Morning

**Status: works end to end.** I ran parts 1 to 4 tonight, exactly as the README says. Every check was a tick.

## Do first

1. Free port 4280. An old demo console holds it (pid 45320 tonight). Run `lsof -nP -iTCP:4280 -sTCP:LISTEN`, then `kill <pid>` (`kill 65711` if that is the one it names). Another old one holds 4290 (pid 76065). It does no harm.
2. Do not run `make reset-empty` or `make prebuild-4`. Those commands wipe part 4's pre-build, and rebuilding it takes 17 minutes.
3. In each terminal you use for `make`, the agents or `aip agent`: `cd ~/dev/graph-memory-system-one-demo/loan-aip-demo; set -a; source .env; set +a`.

## The order

Terminal A:

```sh
cd ~/dev/graph-memory-system-one-demo/loan-aip-demo
set -a; source .env; set +a
make reset                      # 2 s. Main store emptied; part 4's store kept.
make console                    # http://localhost:4280
```

**Part 1.** Terminal B: `AIP_SESSION=build claude`, then paste the build prompt from the README. It takes about 3 minutes (176 s tonight).
Terminal C: `AIP_SESSION=run-1 claude`, then paste the three-application prompt. About 1 minute.
Console: open `assess_business_loan` and show control flow, then data flow, then everything, then traffic.
Terminal A: `make check`. You get three ticks, plus a `draft` row if the build tried its procedure once.

**Part 2.** Terminal A:

```sh
uv run --project agents/adk python agents/adk/agent.py APP-1002 APP-1005        # 15 s
uv run --project agents/langgraph python agents/langgraph/agent.py APP-1004 APP-1001   # 15 s
```

Console: History, filtered by agent, then by session.

**Part 3.** Terminal A: the `sed` line, then `aip publish built/assess_business_loan`. You get `@2`.
Terminal C: paste the new part-3 prompt from the README. It says "by its name alone, no `@1`". About 40 s.
Terminal A: the two agent commands on APP-1004 (15 s each), then `make check-v2`.
Console: revisions, the diff, the runs on revision 2.

**Part 4.** Terminal A:

```sh
export AIP_SERVER=http://127.0.0.1:8301
export AIP_SESSION=$(cat solutions/part4.session)
aip list
aip runs --session $AIP_SESSION
make console-empty              # http://localhost:4281
aip agent --progress "Now assess loan application APP-1002 the same way: approve, refer or decline, the rules that fired and a short rationale."   # 26 s
```

Terminal D: `AIP_SERVER=http://127.0.0.1:8301 claude`, then paste "Use aip to find the loan assessment procedure in the catalog and run it on APP-1003." About 40 s.
Terminal A: `make check-4`.

What to say about the pre-build: it took 17 minutes. It published `assess_business_loan`. Then `assist` started a second build, which failed, so `assist` never ran the procedure. The live APP-1002 run in step 3 is its first run. `solutions/part4.md` has the details.

## Expected outcomes

| App | Before part 3 (rev 1) | After part 3 (rev 2) |
|---|---|---|
| APP-1001 | refer (R5, R7) | refer |
| APP-1002 | approve | approve |
| APP-1003 | decline (R1, R2) | decline |
| APP-1004 | refer (R3 review; the decision model is not sure) | **approve** (coverage 1.15 is above the new 1.10 floor) |
| APP-1005 | refer (R7) | refer |

On the empty server (part 4): APP-1002 approve, APP-1003 decline.

## What I changed tonight

1. Committed the earlier agent's part-4 work: the pre-build, `make reset` keeping the empty store, and `reset-empty`.
2. ADK agent: ADK 2.14's `Claude` class works only with Vertex. It crashed with "Claude requires an AsyncAnthropicVertex client", so the agent now uses `AnthropicLlm`.
3. Part 3 prompt: a continued Claude Code session kept running `@1`. The prompt now says to run by name, so the newest revision runs.
4. Added `solutions/part4.name`, which `make check-4` needed. Corrected the README's "you see" lines for part 1 and part 4.
5. Restored the empty store to the state the pre-build left it in. A spare copy is at `.aip/empty-prebuilt.rl`.

## aip blocks

Nothing blocked tonight's run. Two things to know:
- The pre-build's `assist` gave up after its second build failed, even though the first build had already published the procedure.
- `aip agent` has to use `claude-sonnet-4-5`, which `.env` already sets. Claude 5.5 spends the whole reply cap on thinking. `solutions/README.md` has the details under "What aip needs".

Your Claude Code memory for this repo shapes the live sessions. It lives in `~/.claude/projects/-Users-zach-dev-graph-memory-system-one-demo/memory/`. One note, `loan-decide-no-counter-label`, is why the build leaves out "counter", so APP-1004 refers. Another, `aip-bare-name-resolves-local-folder`, is why a session pins `@N`. I left both as they are.

## If X goes wrong

- **Live build fails or hangs:** in Terminal A, run `make publish-solution`. In part 3, use `make publish-v2` instead of the `sed` and publish.
- **A framework agent errors:** run the other agent, or paste the same applications into Terminal C.
- **Part 4 store looks wrong:** `make down; cp .aip/empty-prebuilt.rl .aip/empty.rl; make up`.
- **Part 4 `aip agent` fails:** show `solutions/part4.md`, then go straight to Terminal D.
- **Port 4280 is taken and you cannot kill the process:** put `AIP_DEMO_CONSOLE_PORT=4282` in `.env` and run `make console` again.
- **Anything else:** `make down`, then `make reset`.
