# Part 4, pre-built: the first `aip agent` on the empty server

Run 2026-11-13 08:04 UTC by `make prebuild-4` (aip 0.9.0 language 0.9) against `http://127.0.0.1:8301`, whose catalog held only the four shipped procedures (assist, build_procedure, edit_procedure, make_procedure). The README's part 4 continues this session live.

Session: `agent-20261113-000430-a8bd`  (also in `solutions/part4.session`)

Took: **1012 seconds** (16.9 minutes), exit 0, 0 model answers, 11 runs in the session.

## The task, verbatim

> Assess loan application APP-1004 under Lantern Mutual's lending policy and SOP in ./source (policy.md and sop_assess_loan.md; the bank's five systems are the JSON files there). Report approve, refer or decline, with the rules that fired and a short rationale. If no procedure in the catalog does this, build one from ./source and write it under ./built, then run it.

## What it built

`assess_business_loan@1` (bundle `00baf18d630e`): Assess one business-loan application under Lantern Mutual's lending policy: apply hard rules R1 to R7, judge the cases the rules leave open, and write the rationale.

Inputs: {"application_id": "string"}. Result: {"application_id": "string", "outcome": "choice", "rationale": "string", "rules_fired": "list"}.

| Step | Kind | What |
|---|---|---|
| `start` | Start | The application to assess. |
| `gather` | Execute | Pull the application, the business, cash flow, facilities, KYC, fraud events, ownership and RM notes from the five systems; owners appear only by share held. |
| `apply_rules` | Execute | Apply hard rules R1 to R7 and guidance G1, every threshold read from the policy copy. |
| `by_policy` | Route | The hard rules approve, decline or refer on their own; review needs a judgment. |
| `settle_policy` | Execute | Settle a case the policy decided without judgment. |
| `assess` | Decide | The lending policy sent this application to review. Judge it as the SOP asks: the risk tier of the business, whether the connected exposure is material to this decision, and the outcome. Base it on the figures and the rules that fired, the ownership summary, the tenure, the KYC status and the relationship manager's notes about the business. Do not argue with a hard rule. |
| `by_confidence` | Route | A confident judgment stands; an unsure one is referred to a person, as the SOP says. |
| `settle_judgment` | Execute | Settle a review case from the model's answers: a decline on a long-standing customer (G1) goes to a person. |
| `refer_unsure` | Execute | Refer the case: the model was not sure. |
| `write_rationale` | Task_Agent | Write the rationale for the decision. |
| `end` | End | The outcome, the rules that fired, and the rationale. |

## The runs of the session

| Run | Procedure | Rev | Status | Started | Finished |
|---|---|---|---|---|---|
| `2c300724c1ad4a5c` | assist | 1 | done | 08:04:30 | 08:21:22 |
| `f7d8a802491e4b1b` | build_procedure | 1 | paused | 08:04:34 |  |
| `3da832170ad14fb2` | build_procedure | 1 | paused | 08:05:06 |  |
| `0c103470dfdd4152` | build_procedure | 1 | paused | 08:05:46 |  |
| `86d0da2622c541a0` | build_procedure | 1 | paused | 08:06:18 |  |
| `6edb4a342d46465a` | build_procedure | 1 | paused | 08:06:56 |  |
| `cb2eede056294d93` | build_procedure | 1 | paused | 08:07:28 |  |
| `53a151c357b5465d` | build_procedure | 1 | paused | 08:08:04 |  |
| `7d2c5e5489834ba7` | build_procedure | 1 | paused | 08:08:43 |  |
| `8210b76ce8e944a9` | build_procedure | 1 | done | 08:09:23 | 08:13:50 |
| `faaff7c0764a42a8` | build_procedure | 1 | failed | 08:14:01 | 08:21:18 |

## The outcome

`assist` finished. Its note:

> The build_procedure run (faaff7c0764a42a8) failed after 5 revision passes without compiling successfully. The procedure could not be built from the source materials in ./source. This requires human intervention to either: (1) review the compilation errors to understand what went wrong, (2) simplify the source materials or brief, or (3) manually create the procedure. Without a working procedure, I cannot assess loan application APP-1004.

## Live, from here

```sh
export AIP_SERVER=http://127.0.0.1:8301
export AIP_SESSION=$(cat solutions/part4.session)
aip runs --session $AIP_SESSION
```

## stderr

```
aip: session: agent-20261113-000430-a8bd (`export AIP_SESSION=agent-20261113-000430-a8bd` to continue it)
```

## The final object

```json
{
  "done": true,
  "result": {
    "note": "The build_procedure run (faaff7c0764a42a8) failed after 5 revision passes without compiling successfully. The procedure could not be built from the source materials in ./source. This requires human intervention to either: (1) review the compilation errors to understand what went wrong, (2) simplify the source materials or brief, or (3) manually create the procedure. Without a working procedure, I cannot assess loan application APP-1004."
  },
  "run_id": "2c300724c1ad4a5c",
  "run_file": "/Users/zach/.aip/runs/2c300724c1ad4a5c.json",
  "recorded": true,
  "session": "agent-20261113-000430-a8bd"
}
```
