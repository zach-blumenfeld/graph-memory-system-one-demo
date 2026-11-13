# Morning

**Status: works end to end, with one change of plan.** I rehearsed every part on this machine:
the Studio build through the console's own endpoints, Claude Code as `claude -p`, the LangGraph
agent, `aip agent` for part 5, and the loan appendix once. The last full run of parts 1 to 3 gave
13 right, 0 wrong in `make check-v2`. Part 5's record gave 2 right in `make check-5`.

The change: each live Studio build of the brief is a little different. One of four rehearsal
builds approved the clean claims with no person; the others sent them to a person. So part 1 is
live (build, save, graph, one Studio run on C-1004, which went to the person in every build), and
parts 2 and 3 use the tested procedure: `make publish-solution`, then `make publish-v2`. Say "the
one this brief built in rehearsal". `solutions/README.md`, "Live builds vary", has the four builds.

## Do first

1. Do not run `make reset-empty` or `make prebuild-5`. They wipe part 5's pre-build (6 minutes to redo).
2. Port 4284 is held by another console on the loan server (pid 48394). It is not this folder's.
   The loan appendix uses 4285.
3. In every terminal: `cd ~/dev/graph-memory-system-one-demo/expense-aip-demo; set -a; source .env; set +a`.
4. Claude Code live will ask to run commands. Approve `aip`, reading the claim files, and writing
   temp files.

## The order

Terminal A:

```sh
make reset                      # 3 s. Main store and ledger emptied; part 5's store kept.
make console                    # http://localhost:4283
```

**Part 1.** Studio, new procedure, name `expense_claim_review`, paste `brief.txt`. 2 to 3 minutes
(131 to 165 s in rehearsal). No questions. Save draft ("I have read them"). Graph: control flow,
data flow, everything. Run: tick the person's step, fill C-1004 (the README's table), answer
`declined`, "Alcohol is not claimable; resubmit without the wine." 5 to 10 s.
Terminal A: `make publish-solution` (1 s).

**Part 2.** Terminal B: `AIP_SESSION=run-1 claude`, paste the part-2 prompt. 30 to 50 s.
Terminal A: `uv run --project agents/langgraph python agents/langgraph/agent.py C-1001 C-1006` (15 s).
Console: History by agent, then by session.

**Part 3.** Terminal A: `make publish-v2` (1 s). Optional, in the Studio: "Raise the single-item
limit from 200 to 250." (15 s; show the diff; do not publish). Terminal B: the part-3 prompt (30 to
45 s). Terminal A: the LangGraph agent on C-1003 (15 s), then `make check-v2`. Console: revisions,
the diff, the runs on revision 2.

**Part 4.** Terminal A: `aip runs --agent studio`, then `aip runs <build_procedure run id>`. The
slide: `agent.py`.

**Part 5.** Terminal A: `export AIP_SERVER=http://127.0.0.1:8311; export AIP_SESSION=$(cat solutions/part5.session); cd part5`,
then `aip list`, `aip runs --session $AIP_SESSION`. Live: the C-1002 `aip agent` line (7 s), then
the approver's line (8 s). Then back: `cd ..; unset AIP_SESSION; export AIP_SERVER=http://127.0.0.1:8310`.

What to say about the pre-build: 6 minutes in all. The build and publish took 3 minutes. The
second claim found the procedure in 10 s. Both claims stopped for a person, because `assist` will
not decide for one; two short turns gave the person's answers.

**Appendix, if asked.** Terminal A: `make console-loan`, http://localhost:4285. Studio, new
procedure `assess_business_loan`, drop the loan folder's `source/policy.md` and
`source/sop_assess_loan.md`, paste the one-line brief. 7.6 minutes in rehearsal, no questions,
22 steps. Show the graph; do not run it.

## Expected outcomes

| Claim | What | Rev 1 | Rev 2 (limit 250) |
|---|---|---|---|
| C-1001 | meals 48.60, clean | approved, no person | approved |
| C-1002 | software 129.00, clean | approved, no person | approved |
| C-1003 | equipment 236.00, one item | person, declined (over 200) | **approved, no person** |
| C-1004 | meals 86.40, a bottle of Chianti | person, declined (alcohol) | declined |
| C-1005 | travel 64.00, no receipt | person, declined | declined |
| C-1006 | equipment 180.00 of a 540.00 order | person, declined (a split) | declined |

When an agent is the person, it decides. In every rehearsal it declined the four that should be
declined.

Part 5 (its own build): C-1003 declined, C-1001 approved, C-1002 approved; all three by the person.

## What I changed on the way

1. The brief: the first build asked two questions; their answers are two sentences at the end of
   `brief.txt`. The coordinator added two more (the approver field, `ledger.txt`). I added one
   after a build invented a currency rule: "All amounts are in one currency..." After that, no
   build asked anything. `solutions/README.md` lists all five.
2. The claims carry an `approver`.
3. Parts 2 and 3 publish the tested solution instead of the live draft (above).
4. Part 5 runs in `./part5`, with its own ledger, after the first attempt read the main ledger.
5. The Makefile records the console's real pid, so `make down` stops it.

## aip blocks

Nothing blocked the demo. What to know, all in `solutions/README.md`, "What aip lacks":
- A person's choice (`approved`, `declined`) reaches a script as `{"value": ...}`. It failed part
  5's first attempt and puts `{'value': 'declined'}` in part 5's ledger.
- Builds vary. Nothing in the Studio shows that a build sends clean claims to a person before Save.
- The Aggregate's bar compares the probability (`noul`), not the `confidence` the Decide shows.

## If X goes wrong

- **Live build fails, hangs, or asks something:** go on. `make publish-solution` is the next step anyway.
  Answer a question in plain words if one comes.
- **The Studio's chat says it has no model:** the console was started without `.env`. `make down`,
  `set -a; source .env; set +a`, `make reset`, `make console`.
- **A framework agent errors:** run the claims from Claude Code instead.
- **Part 5's store looks wrong:** `make down; cp .aip/empty-prebuilt.rl .aip/empty.rl; make up`.
- **Part 5's live claim stops somewhere else:** show `solutions/part5.md` and `aip runs --session $AIP_SESSION`.
- **Port 4283 is taken:** `make console` names the process. Kill it, or set `AIP_DEMO_CONSOLE_PORT` in `.env`.
- **Anything else:** `make down`, then `make reset`, then `make console`.
