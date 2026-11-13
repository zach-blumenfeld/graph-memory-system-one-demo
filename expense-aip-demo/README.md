# The expense demo on AIP

An expense claim review, built live in the console's Studio from a plain brief, run from the
Studio, from Claude Code and from a LangGraph agent, changed once and re-run. Then the reveal:
the build was `aip agent --answer`, one model call per pause. Then the general loop: `aip agent`
on an empty server builds the procedure itself. Everything is copy-paste.
Background, run ids and what aip lacks: `solutions/README.md`.

Claims and outcomes: C-1001 and C-1002 approved (no person). C-1003 (one item over 200),
C-1004 (wine), C-1005 (no receipt), C-1006 (a split) go to a person, who declines.
After part 3, C-1003 is approved.

## Before the demo (once)

Needs: uv, Node 20+, Claude Code, the aip checkout at `~/dev/aip-0.9`, a TypeSafe key, an
Anthropic key.

```sh
cd ~/dev/graph-memory-system-one-demo/expense-aip-demo
cp ../loan-aip-demo/.env .env   # then make its lines match .env.example (ports, AIP_SERVER, the model)
aip config --decision-model-key <TYPESAFE_KEY>
make setup
make prebuild-5                 # part 5's first `aip agent`, once, before the demo; see solutions/part5.md
```

## Start (every time)

Terminal A:

```sh
cd ~/dev/graph-memory-system-one-demo/expense-aip-demo
set -a; source .env; set +a
make reset                      # fresh main store and ledger; part 5's store kept; servers :8310, :8311
make console                    # http://localhost:4283, with the key, so the Studio's chat has a model
```

Every other terminal starts with the same `cd` and `set -a; source .env; set +a`.
`.env` sets `AIP_SERVER`, so nothing here talks to the loan demo's servers.

## Part 1: build it, live, in the Studio

1. Console, http://localhost:4283: Studio, new procedure. Name: `expense_claim_review`.
   Paste all of `brief.txt`. About 2 to 3 minutes, no questions. The trace: read the
   documents, worked out the rules, wrote the procedure, compiled it, tried it, reviewed it.
2. Save draft. It asks once whether you read the scripts the model wrote: "I have read them".
3. Show the step graph: control flow, data flow, everything.
4. Run. Tick the person's step as yours (its name says person or human). Fill the form with
   C-1004:

   | Field | Value |
   |---|---|
   | id | C-1004 |
   | amount | 86.40 |
   | category | meals |
   | date (the claim's) | 2026-11-11 |
   | claimant | Jonah Abebe |
   | approver | Owen Mardsen |
   | receipt | the whole of `claims/C-1004.receipt.txt` |

   The model reads the receipt. The Decides run, one per rule. The no-alcohol rule fails.
   Your form comes up: `declined`, "Alcohol is not claimable; resubmit without the wine."

   You see: the For over the rules with a Decide each, the Aggregate's confidence bar, the
   Task_Agent that read the receipt, your form, and a line in `ledger.txt`.

5. Terminal A, the procedure this brief built in rehearsal, tested on all six claims:

```sh
make publish-solution
```

   Each live build is a little different (`solutions/README.md`, "Live builds vary"). Parts 2
   and 3 use the tested one.

## Part 2: any agent

1. Terminal B:

```sh
cd ~/dev/graph-memory-system-one-demo/expense-aip-demo && set -a && source .env && set +a && AIP_SESSION=run-1 claude
```

   Paste:

> Use aip to review expense claims C-1002 and C-1005. Each claim is in ./claims: C-1002.json and the receipt text it names. Run expense_claim_review on each, in parallel, with the claim fields and the receipt text as given. Where a run asks a person to decide, you are the reviewer: decide from what it found and give a one-line reason. Report each status, reason and run id.

   About 30 seconds. C-1002 approved with no person; C-1005 comes to Claude as the person.

2. Terminal A:

```sh
uv run --project agents/langgraph python agents/langgraph/agent.py C-1001 C-1006
```

   It prints its tool list first: search, describe, run, resume. About 15 seconds.

3. Console: History, filter by agent (`cli`, `langgraph`, `studio`), then by session.

   You see: four runs, two agents, one procedure, every answer named.

## Part 3: change a rule

The single-item limit goes from 200 to 250. C-1003's monitor arm is 236.00, so it flips.

1. Terminal A:

```sh
make publish-v2                 # revision 2: the Studio's own edit of the solution, "Raise the single-item limit from 200 to 250."
```

   To show the edit itself: Studio, chat "Raise the single-item limit from 200 to 250." About
   15 seconds; the diff is 200 to 250. Do not publish that draft.

2. Terminal B, paste:

> Use aip to run expense_claim_review by its name alone, no @1, so the newest revision runs, on claims C-1003 and C-1001 from ./claims, in parallel, with the claim fields and the receipt text as given. Where a run asks a person to decide, you are the reviewer: decide from what it found and give a one-line reason. Report each status, reason, revision and run id.

3. Terminal A:

```sh
uv run --project agents/langgraph python agents/langgraph/agent.py C-1003
make check-v2
```

4. Console: the procedure's revisions, the diff of 1 and 2, the runs on revision 2.

   You see: C-1003 approved on revision 2 with no person. Every row a tick.

## Part 4: the reveal

1. Terminal A:

```sh
aip runs --agent studio             # the Studio's runs, with their session
aip runs <the build_procedure run id>
```

   You see: `read_documents`, `extract_rules`, `draft` and `review` "answered by studio
   (claude-sonnet-5-5)", with tokens and seconds. The scripts did the rest.

2. The slide: `~/dev/aip-0.9/src/aip/agent.py`. The Studio calls `aip agent --answer` once per
   pause, the same inner loop (`answer_once` in `aip/chat.py`): one model call, no tools.

## Part 5: the general loop

`make prebuild-5` ran this before the demo on the empty server (:8311), in `./part5`, in about
6 minutes. `aip agent` was told, in words, to review C-1003 under the policy. `assist` searched,
found nothing, built and published `expense_claim_review` (3 minutes) and ran it. The same session
then reviewed C-1001: it found the procedure and ran it in 10 seconds. Both stopped at the
person's step; `assist` will not decide for a person. Two more turns gave the person's answers.
`solutions/part5.md` has the times and the runs.

1. Terminal A:

```sh
export AIP_SERVER=http://127.0.0.1:8311
export AIP_SESSION=$(cat solutions/part5.session)
cd part5
aip list
aip runs --session $AIP_SESSION
```

   You see: one procedure that was not there before, and the session: `assist`,
   `build_procedure`, the two claim runs, all answered by `agent`.

2. Live, the same session, a third claim (about 7 seconds):

```sh
aip agent --progress "Review expense claim C-1002 the same way: the claim and its receipt are the files under ./claims. Approve or decline it under our policy and report the status and the reason."
```

   You see: `search` finds the procedure, nothing is built, it runs, and stops for the approver
   (this build doubts the monthly limit without a history). Answer as the approver (8 seconds):

```sh
aip agent "I am the approver. C-1002 is approved: the receipt matches and the monthly limit is judged from this claim alone."
```

3. The slide again: `agent.py`, the whole harness. Then `aip runs --session $AIP_SESSION`.

4. `cd ..; unset AIP_SESSION; export AIP_SERVER=http://127.0.0.1:8310`

## Appendix: the loan procedure in the Studio

A console whose working directory is the loan folder, on this folder's main server:

```sh
make console-loan               # http://localhost:4285
```

Studio, new procedure. Name: `assess_business_loan`. Drop `../loan-aip-demo/source/policy.md`
and `../loan-aip-demo/source/sop_assess_loan.md` on the chat as documents. Paste:

> Assess a business-loan application by its id, using the policy and SOP and the bank's five systems in ./source.

About 8 minutes in rehearsal, no questions. It builds about 22 steps: intake of the five
systems, a For over R1 to R7, a judgment Decide, two person's steps, a write-up with a check
loop. Save draft and show the graph; do not run it (`solutions/README.md` says why).

## After

```sh
make down
```

## Layout

| Path | What |
|---|---|
| `brief.txt` | the brief the presenter pastes |
| `claims/` | six claims as JSON and a messy receipt each |
| `solutions/expense_claim_review/`, `-v2/` | the procedure as the Studio built it, and after the part-3 chat |
| `solutions/README.md` | the design, run ids, what did not work, what aip lacks |
| `solutions/part5.md`, `.session`, `.name`, `part5-built/`, `prebuild_5.py`, `part5/` | part 5: the pre-built `aip agent` session, the folder it built, and where it runs |
| `agents/langgraph/` | the framework agent: search, describe, run, resume |
| `check.py` | each run beside its expected status, tick or cross |
| `rehearse_studio.py` | part 1 and the part-3 edit through the console's endpoints, for rehearsal |
| `Makefile`, `.env.example`, `aip-server.toml` | setup, servers, consoles, reset |
