# Solutions: what was built, what was run, what did not work

Built 2026-11-13 on aip 0.9.0 (checkout `~/dev/aip-0.9` at commit 7b284d7, "build_procedure drafts
a policy as a For over Decides"). The Studio's model was `claude-sonnet-5-5` (`.env`); the decision
model was TypeSafe (`aip config`). Servers: 8310 (main), 8311 (part 5), consoles 4283 and 4285.

## The brief, and what was added to it

The brief in `brief.txt` is the fixed brief with four sentences added at the end. All are plain
language.

1. The first rehearsal build asked two questions (run `feff63e7ed044a23`, session `studio-023956`):
   which date the 30 days run to, and which claims get a ledger line. The answers were added:
   "The claim's date is the day it was submitted; the 30 days run from the receipt's date to the
   claim's date." and "Every decided claim gets a ledger line, approved or declined, whoever
   decided it."
2. The coordinator added, from a build on another server: the claim carries an `approver` field
   ("The approver is the name in the claim's approver field; the self-approval rule holds when it
   differs from the claimant.") and "The ledger file is ledger.txt in the working directory." The
   six claims got an `approver`.
3. Rehearsal 2's build invented a rule ("the currency is clearly the claim's currency") and sent
   clean claims to a person. Added: "All amounts are in one currency, so a receipt's currency sign
   or code is never a reason to doubt it." This answers no question the build asked; it closes a
   gap the build filled wrongly.

With 1 and 2 in the brief, four builds in a row asked nothing.

## The procedure (`expense_claim_review/`)

Built by the Studio in rehearsal 1 (build run `f7477ab401444e53`, 136 s, no questions; brief
with additions 1 and 2), saved as bundle `05323bd150a4`. Twelve steps:

| Step | Kind | What |
|---|---|---|
| `start` | Start | claim_id, amount, category, date, claimant, approver, receipt |
| `read_receipt` | Task_Agent | vendor, receipt date, total, line items, and why the receipt does or does not support the claim |
| `load_rules` | Execute | the nine rules from `assets/rules.json` |
| `compute_facts` | Execute | the exact facts: amounts against 200, 1000 and 25, the days between, the category, the approver |
| `check_each` | For | over the nine rules |
| `judge_rule` | Decide | one rule, one `follows: true_or_false` |
| `summarize_checks` | Aggregate | `All verdicts.follows With Confidence_Above 0.8` |
| `route_checks` | Route | true to `auto_approve`, false to `person_decides` |
| `auto_approve` | Execute | approved, a fixed reason |
| `person_decides` | Task_Agent | the person's status and one-line reason |
| `record_ledger` | Execute | one line in `ledger.txt` |
| `end` | End | status, reason |

`expense_claim_review-v2/` is the same draft after one Studio chat message, "Raise the single-item
limit from 200 to 250." (edit run `9c1637f52d0f4488`, 16 s). It changed `assets/rules.json` and
`scripts/compute_facts.py`; `procedure.aip` is unchanged. Bundle `1ac72c6529dc`.

The part-3 rule: the single-item limit, 200 to 250. C-1003's one item is 236.00, so it flips from
a person's decline to an approve with no person.

## Tested on all six claims

Rehearsal 1, the draft run from the Studio's endpoints, the model answering, the person's step
answered by me (session `studio-024111`):

| Claim | Expected | Went to | Result | Run |
|---|---|---|---|---|
| C-1001 | approved | no person | approved | `435de464c5834a9d` |
| C-1002 | approved | no person | approved | `b04b14bb8c9a4e90` |
| C-1003 | declined | person (`no_item_over_200`, false 0.98) | declined | `71881c2acf86432f` |
| C-1004 | declined | person (`no_alcohol`, false 0.98) | declined | `f8206daa86cf4477` |
| C-1005 | declined | person (no receipt, and others) | declined | `9aca249c66d645f4` |
| C-1006 | declined | person (`receipt_supports`, `no_splitting`) | declined | `9bda86491dc545a8` |

Rehearsal 4, the same folder published with `make publish-solution` and run through the console
(session `solution-test`): the same six outcomes, the same routes. Runs `d4265fb4ea6e4dff`,
`75096f9ab6f34d54`, `b7e1c9dfd5ce45bf`, `bffa17e2ad8d4bac`, `4e5c378eb6b8450b`, `666ff4d800654393`.

## The final rehearsal (rehearsal 4, store `.aip/main.rl` as left)

`make reset`, `make console`, then the README's parts as written, Claude Code as `claude -p`.

| Part | What | Time | Runs |
|---|---|---|---|
| 1 | Studio build (`studio-030212`, build run `5eb6ac64cf8e4b7f`), no questions | 141 s | |
| 1 | Studio Run of the draft on C-1004, `human_review` ticked as the person's, declined | 4 s | `b79c9bd3059c4f2e` |
| 1 | `make publish-solution` | 1 s | |
| 2 | Claude Code, session `run-1`: C-1002 approved, C-1005 declined | 30 s | `394119462ab547bc`, `dea61591462349fa` |
| 2 | LangGraph: C-1001 approved, C-1006 declined | 13 s | `f04f0b183bcc46d9`, `aa597a81c2644b47` |
| 3 | `make publish-v2` | 1 s | |
| 3 | Claude Code: C-1003 approved, C-1001 approved, both rev 2 | 31 s | `5279385322274bf5`, `b2c77ee8aeab4b29` |
| 3 | LangGraph: C-1003 approved, rev 2 | 13 s | `20e42e591de34abe` |

`make check-v2`: 13 right, 0 wrong.

## Live builds vary

Four Studio builds of the same brief, four procedures. All compiled; none asked a question once
additions 1 and 2 were in. All sent C-1004 to the person.

| Rehearsal | Build | Shape | Clean claims (C-1001, C-1002) |
|---|---|---|---|
| 1 | 136 s | For over 9 rules, a Decide each (the solution) | approved, no person |
| 2 | 165 s | For over 7 exact checks (Execute), For over 3 judged rules (Decide), two Routes | to a person: an invented currency rule |
| 3 | 131 s | For over 9 rules, a Decide each, status a `choice` | to a person: TypeSafe unsure (0.59) on "the receipt supports the claim" |
| 4 | 141 s | exact checks in one script, For over judged rules, two Routes | not tested on the clean claims |

So the README runs the live build for part 1 only (build, save, graph, one Studio run on C-1004,
which goes to the person in every build), and publishes this tested solution for parts 2 and 3.
The agents answer the person's step themselves; in rehearsals 2 and 3 they approved the clean
claims that went to them, so `check.py` still ticked, but the "no person" path was not shown.

## Part 4: the reveal

`aip runs --agent studio` lists the Studio's runs. `aip runs <build run>` shows each step and who
answered it: `read_documents`, `extract_rules`, `draft` and `review` "answered by studio
(claude-sonnet-5-5), reported: N tokens, S s"; the scripts did the rest. In rehearsal 4: 2189,
4119, 23092 and 20879 tokens; the `draft` answer took 84 s.

`~/dev/aip-0.9/src/aip/agent.py` is 19 lines with its imports; the function is 15. The Studio
does not call `agent()`: it calls `aip agent --answer <run>` once per pause, which is
`answer_once` in `aip/chat.py`, the same inner loop (one answer, up to three corrections, no tools).

## Part 5: the general loop

`part5.md` is the record `make prebuild-5` wrote, plus the hand-run fourth turn.

The record (attempt 2, session `agent-20261113-031712-9a24`, in `./part5`, model `claude-sonnet-5-5`):

| Turn | Time | What happened |
|---|---|---|
| 1, C-1003 | 188 s | `assist` searched, found nothing, ran `build_procedure` (162 s, run `72f9fedaa1bd4e30`), published `expense_claim_review@1`, ran it (`8fbc649d06c9470d`); it stopped at `person_decision` and `assist` finished with the question for the person |
| 2, C-1001 | 10 s | found it, ran it (`b4a3c940289142e7`), stopped at the person (the build doubts the monthly limit without a history) |
| 3, the person | 137 s | resumed C-1003: declined, over 200. Ran out of passes before C-1001 |
| 4, the person | 12 s | resumed C-1001: approved |

`make check-5`: 2 right. The live step was rehearsed too: C-1002 in the same session found the
procedure and ran it in 7 s, stopped at the person, and the approver's turn finished it in 8 s
(approved). The store was then put back as the pre-build left it (copy: `.aip/empty-prebuilt.rl`).

Attempt 1 (session `agent-20261113-030819-4063`, in this folder): built and published in 168 s,
found again in 13 s. Both runs stopped at the person. A person's turn then failed both runs at
`record_ledger`: the person's `status` reached the script as `{"value": "declined"}`. That build
also read `ledger.txt` for the monthly limit and could not parse the main demo's lines; part 5
now runs in `./part5` with its own ledger. Attempt 2's ledger has the same object in its status
column, but its script did not refuse it.

## Appendix: the loan procedure in the Studio

`make console-loan` (port 4285; 4284 was held by another console on 8300), working directory
`../loan-aip-demo`. Rehearsed once through the console's endpoints: new procedure
`assess_business_loan`, the two documents dropped (`policy.md`, `sop_assess_loan.md`), the
one-line brief. Session `studio-loan-030859`, build run `6f3729099f4b4f8f`, 456 s (7.6 min), no
questions, compiles. It built 22 steps and 10 scripts: `intake` (the five systems from
`./source`), gates that refer a missing record or figure to a person, a For over R1 to R7 with one
`eval_rule` script each, `combine`, a Route by path, a `judge` Decide for review cases with a guard
script, two person's steps (`human_review_policy`, `human_review_judgment`), a `write_up`
Task_Agent with a check-and-fix Loop, and `file_decision`, which calls the SOP's `loan decide`.
Its review lists eleven doubts for a person, among them that the fix may run after a passing check
and that the refer paths may fail at End. It was not run: the trial runs no script, and the loan
folder was not touched.

## What aip lacks

- **A Task_Agent's choice reaches a script as `{"value": ...}`.** A `status` with labels is stored
  as `{"value": "declined"}`; a script that reads `state["status"]` gets the object. Part 5's build
  failed on it. The language page the drafting model reads does not say so. Either say it there,
  or hand scripts the bare label.
- **Builds vary, and nothing in the Studio flags it.** The same brief gave four procedures. One
  invented a currency rule; one gave TypeSafe a compound rule it could not answer with confidence.
  A built-in trial on example inputs (the brief's own, or documents the person drops) that runs the
  scripts and Decides would show "clean claims go to a person" before Save.
- **`Confidence_Above` compares the probability, the Decide shows `confidence`.** For a
  `true_or_false`, `confidence` is |2·noul − 1| and the bar is on `noul`. A verdict shown as
  "confidence 0.76" passes a 0.8 bar (noul 0.88). The built `person_decision.md` tells the person
  "doubtful if the confidence is below 0.8", which is the other number. Name the bar's number on
  the Aggregate, or use one number in both places.
- **`assist` stops at a person's step and the run waits.** Right by design, but `aip agent` then
  needs the person's answer as a new task, and the model must find the paused run and map the
  answer. A `--person` reply that resumes the waiting run directly would be cleaner.
- **The Studio's session is the browser tab's.** `aip runs --session` needs it; the page shows it
  only in the run console. `aip runs --agent studio` is the way in.
- **`make console`'s pid.** The launcher runs under a shell that `$!` names, not node; the Makefile
  now records the listener's pid (`lsof`), so `make down` stops it. The loan Makefile has the same
  pattern and may leave a console running after `make down`.
- **Headless Claude Code needs tools allowed.** `claude -p` with `--permission-mode dontAsk` and only
  `Bash(aip:*)` denied the agent's own file reads; `--allowedTools Bash Read Write Skill` ran clean.
  Live, the presenter approves prompts by hand.
