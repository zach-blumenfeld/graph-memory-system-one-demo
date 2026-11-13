# Part 5, pre-built: the general loop on the empty server

Run 2026-11-13 11:17 UTC by `make prebuild-5` (aip 0.9.0 language 0.9, model `claude-sonnet-5-5`) against `http://127.0.0.1:8311`, whose catalog held only the shipped procedures (assist, build_procedure, edit_procedure, make_procedure).

Session: `agent-20261113-031712-9a24` (also in `solutions/part5.session`).

## C-1003: 188 seconds (3.1 minutes), exit 0, 0 model answers, done

> Review expense claim C-1003: the claim and its receipt are the files under ./claims (C-1003.json and the receipt text file it names). Approve or decline it under our policy: no single item over 200, no more than 1000 a month, only travel, meals, software and equipment, a receipt for anything over 25, no alcohol, submitted within 30 days of the receipt date (the claim's date is the day it was submitted), the claimant cannot be the approver named on the claim, and no splitting one purchase into several claims, judged from the claim and its receipt alone. If every rule clearly holds, approve it; if anything fails or is doubtful, a person decides with a one-line reason. Every decided claim gets a line (claim id, claimant, amount, category, date, status) in ledger.txt in the working directory. Report the status, approved or declined, and the reason.

`assist` said:

> Claim C-1003 needs a person's decision, and I cannot make it for them. Run 8fbc649d06c9470d (expense_claim_review) is paused at person_decision. Claim: Mei Lindqvist, equipment, 236.00 GBP, submitted 2026-11-10 with a BrightDesk receipt dated 03 Nov 2026 for one ergonomic monitor arm. Approver on the claim is Owen Mardsen. Rules that fail or are doubtful: (1) the single item of 236.00 is over the 200 limit, which is a clear failure; (2) the monthly total cannot be established from the claim and receipt alone. The other rules look fine: the category is allowed, a receipt is present, there is no alcohol, the submission is 7 days after the receipt date, the claimant is not the approver, and there is no sign of splitting. Question for the expense approver (Owen Mardsen or whoever decides): should C-1003 be approved or declined, and what is your one-line reason? Once I have that, I will resume the run with {status, reason}, and the ledger line will be written after the decision.

```
aip: session: agent-20261113-031712-9a24 (`export AIP_SESSION=agent-20261113-031712-9a24` to continue it)
```

## C-1001: 10 seconds (0.2 minutes), exit 0, 0 model answers, done

> Review expense claim C-1001 the same way: the claim and its receipt are the files under ./claims (C-1001.json and the receipt text file it names). Approve or decline it under our policy: no single item over 200, no more than 1000 a month, only travel, meals, software and equipment, a receipt for anything over 25, no alcohol, submitted within 30 days of the receipt date (the claim's date is the day it was submitted), the claimant cannot be the approver named on the claim, and no splitting one purchase into several claims, judged from the claim and its receipt alone. If every rule clearly holds, approve it; if anything fails or is doubtful, a person decides with a one-line reason. Every decided claim gets a line (claim id, claimant, amount, category, date, status) in ledger.txt in the working directory. Report the status, approved or declined, and the reason.

`assist` said:

> Run b4a3c940289142e7 (expense_claim_review) is paused at person_decision for claim C-1001. Only the expense approver can answer, because the policy says a person decides when a rule is doubtful, and the decision is final. Please show the approver the claim and receipt and ask: approve or decline C-1001, and why, in one line? Claim: Priya Okafor, meals, 48.60, submitted 2026-11-06, approver Hannah Brightwell. The receipt is from The Copper Kettle, dated 05 Nov 2026, total 48.60. It includes 3.00 of optional service, and the only drinks are sparkling water and a flat white, with no alcohol. The doubtful rule is the 1000-a-month limit, because the monthly total cannot be established from the claim and receipt alone. The other rules appear to hold: the amount is under 200, the category is allowed, a receipt is present, it was submitted within 30 days, the claimant is not the approver, and there is no sign of splitting. Once they answer, I will resume the run with their status and reason so the ledger line is written.

```
aip: session: agent-20261113-031712-9a24 (`export AIP_SESSION=agent-20261113-031712-9a24` to continue it)
```

## person: 137 seconds (2.3 minutes), exit 0, 0 model answers, done

> I am the person who decides expense claims. If a claim's run is waiting for me: C-1003 is declined, the 236.00 monitor arm is over the 200 single-item limit; C-1001 is approved, the receipt matches the claim and every rule holds. Finish each run and report each claim's status.

`assist` said:

> Not finished. Run 8fbc649d06c9470d (expense_claim_review) is done: the claim is declined, reason: the 236.00 monitor arm is over the 200 single-item limit. That matches your decision on C-1003. Run b4a3c940289142e7 (expense_claim_review) is still paused. It is presumably the C-1001 run, but I have not seen its pause tasks or confirmed which claim it is. So I have not resumed it with your approval, and C-1001 has no recorded status and no ledger entry. This is the last pass the loop allows, so I could not look at that pause and answer it. To finish it, someone needs to inspect run b4a3c940289142e7, confirm it is C-1001, and resume it with the approval.

```
aip: session: agent-20261113-031712-9a24 (`export AIP_SESSION=agent-20261113-031712-9a24` to continue it)
```

## A fourth turn, by hand: 12 seconds

The third turn finished C-1003 and ran out of passes before C-1001. One more `aip agent` in the
session, from `./part5`:

> I am the person who decides expense claims. C-1001 is approved: the receipt matches the claim and every rule holds; the monthly limit is judged from this claim alone. Its run is waiting for me.

`assist` resumed run `b4a3c940289142e7`: C-1001 approved (assist run `cce3f7dfef944851`).
`make check-5`: C-1003 declined, C-1001 approved, 2 right. Both went to a person: this build
treats the monthly limit as doubtful without a history. The ledger's status column holds
`{'value': 'declined'}`, the choice-as-object problem in `solutions/README.md`.

## What it built

`expense_claim_review@1` (bundle `d8ba03c53311`): Review one expense claim against the expense policy: approve it automatically when every rule clearly holds, otherwise a person decides, and record every decided claim in ledger.txt.

Inputs: {"claim_id": "string", "claims_folder": "string"}.

| Step | Kind | What |
|---|---|---|
| `start` | Start | The folder holding the claim files and the id of the claim to review. |
| `read_claim` | Execute | Read the claim file and the receipt text file it names. |
| `exact_checks` | Execute | Check item limit, month total, category, receipt present, 30-day window and claimant not the approver. |
| `load_rules` | Execute | Load the list of judgement rules a person would read and judge. |
| `judge_rule` | Decide | Does the claim and its receipt clearly satisfy this judgement rule? |
| `summarize_judgement` | Aggregate | Every judgement rule clearly holds, and the model was sure of each. |
| `combine` | Execute | Combine the exact checks and the judgement verdicts into one answer and a list of issues. |
| `by_auto` | Route | A claim where every rule clearly holds is approved automatically; anything else goes to a person. |
| `auto_approve` | Execute | Approve the claim automatically, with a reason saying all rules hold. |
| `person_decision` | Task_Agent | A person decides this expense claim, because at least one rule failed or is doubtful. Take it to the person who approves expenses and show them the claim, the receipt text and the rules that failed or are doubtful.

Claim: {claim}

Receipt text: {receipt_text}

Rules that failed or are doubtful: {issues}

The person answers approved or declined and gives a one-line reason. Their decision is final. Answer with exactly these keys: status (approved or declined) and reason (their reason, on one line). |
| `record_ledger` | Execute | Append one line for the decided claim to ledger.txt. |
| `end` | End | The claim is decided and recorded in the ledger; the status and the reason are the result. |

## The runs of the session

| Run | Procedure | Rev | Status | Started | Finished | Result |
|---|---|---|---|---|---|---|
| `248a9063cc1d4517` | assist | 1 | done | 11:17:12 | 11:20:20 |  |
| `72f9fedaa1bd4e30` | build_procedure | 1 | done | 11:17:22 | 11:20:04 |  |
| `8fbc649d06c9470d` | expense_claim_review | 1 | done | 11:20:10 | 11:20:35 | {"reason": "The 236.00 monitor arm is over the 200 single-item limit.", "status": {"value": "declined"}} |
| `568edb6ac8224da0` | assist | 1 | done | 11:20:20 | 11:20:31 |  |
| `b4a3c940289142e7` | expense_claim_review | 1 | done | 11:20:23 | 11:20:43 | {"reason": "Receipt matches the claim and every rule holds, as decided by the approver.", "status": {"value": "approved"}} |
| `0ec1d95a0c7f454b` | assist | 1 | done | 11:20:31 | 11:22:47 |  |

## Live, from here

```sh
export AIP_SERVER=http://127.0.0.1:8311
export AIP_SESSION=$(cat solutions/part5.session)
cd part5
aip runs --session $AIP_SESSION
```
