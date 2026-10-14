---
name: assess-business-loan
description: Assess one Lantern Mutual business-loan application from its id (APP-NNNN) the way the credit team's page says and five recorded runs did it - gather the application, ownership two hops out, facilities, cash flow and KYC with the loan CLI (dates of birth and people's names stripped before any judgment), apply the lending policy (hard rules R1-R6, guidance G1) for auto_approve, auto_decline or review, judge risk tier, connected exposure and outcome (approve, counter, decline) only when the policy leaves a judgment, look up precedents, write a rationale that cites every figure to a record, pass the check with one fix pass, and file the decision with its confidence and skill revision, logging every judgment call. Use for any new business loan, term loan, equipment loan, working capital line or vehicle loan application that needs an assessment, a credit decision or a written rationale. A decline on a customer of five years or more stops for a human before filing.
metadata:
  aip-version: "0.5a1"
  author: lantern-mutual-credit
  version: "1"
---

# AIP runtime — format 0.5a1

You are executing an Agent Instruction Protocol (AIP) procedure: the fenced YAML block in this skill's `SKILL.md`. AIP is a protocol for cheaply, quickly, and accurately executing multi-step tasks as a graph of typed steps. You drive the run and execute every step yourself, following the semantics below.

Critical terminology:

- **Client**: you, the agent running this procedure; the `client_task` step kind is named for it. You supply each step's input, run its script, answer its questions by your own judgment, perform its task, follow its router, and make the final call at every step.
- **State**: the JSON object a step receives. Each step declares its required keys as `inputs`; extra keys pass through.
- **Step kinds**: `execution` runs a script, `decision` asks typed questions about the state, `client_task` hands work to you, `router` branches on a value in the state, `end` declares the final state's shape.

## Execution

The state is one JSON object. It starts as the start step's `inputs` and flows along `inputs_to`; each step's output is merged over it, so keys accumulate and extra keys pass through untouched. A step runs only if the state holds every key it declares in `inputs`, with the declared types; check that before each step. You may change the state before any step runs; you have the final say at every step.

- **`execution`**: run `script` with one JSON object on stdin, `{"currentState": <state>, "assets": {<file stem>: <content>}, "expects": <the next step's inputs>}`. The script writes one JSON object to stdout; merge it over the state.
- **`decision`**: answer each question against the state. Each answer collapses to one value under its question name and is merged over the state: a noul to `true`/`false`, a choice to its label, a score to its level number. `thresholds` name the questions where an uncertain answer matters most; when your answer to one is a close call, reconsider it before continuing.
- **`client_task`**: render `template` with `{key}` from the state, `{assets[stem]}` for its assets, and `{meta.name}` for the skill name. Perform the task, loading `references` if their descriptions apply, and produce the next step's `inputs`; merge them over the state.
- **`router`**: read the state's `branch_on` key and continue at `branches[value]`. A value with no branch is an error.
- **`end`**: the state must hold `end`'s `inputs`. That state is the procedure's result.

```yaml
purpose: >
  Turn one business-loan application into one filed, auditable decision the way the Lantern Mutual credit
  team's page says and the way five recorded runs actually did it. Scripts call the `loan` CLI (the only way
  to reach the bank's five systems and the memory graph): gather the application, ownership two hops out,
  facilities, cash flow and KYC with every figure keeping the record keys it came from; apply the lending
  policy (hard rules R1-R6, guidance G1); look up precedents; submit and check the rationale; file the
  decision with its confidence and this skill's revision. The judgment step cannot see protected
  characteristics: gather strips dates of birth, people's names and any note that mentions a personal
  characteristic before the decision model judges risk tier, connected exposure and outcome, and it is only
  asked when the policy leaves a judgment. The agent writes the one generative piece, the rationale, which
  must state the outcome first and cite every figure to a record; when you decline someone you owe them a
  reason. One fix pass after a failed check, no loops. A decline on a customer of five years or more goes to a
  human before filing. Every decision is auditable: filed with the rules it applied, the records it cited,
  its confidence, the procedure revision, and every judgment call logged.

trigger_when:
  - A business-loan application id (APP-NNNN) needs assessing, a credit decision, or a written rationale.
  - Someone asks to assess, underwrite, decide, approve, counter or decline a business loan, term loan, equipment loan, working capital line or vehicle loan for a Lantern Mutual customer.
  - A new application has been submitted and the credit team's page "How we assess a business loan" applies.

do_not_use_when:
  - There is no application id; taking or writing an application is a different job.
  - The ask is about a consumer or personal loan, a mortgage, or a customer who is not a business.
  - The ask is to amend, restructure or collect on a facility that already exists, or to redo a decision already filed and under review by a human.

steps:
  - name: gather
    kind: execution
    description: Read the application, ownership two hops out, facilities, cash flow and KYC with loan; strip dates of birth, people's names and any note that mentions a personal characteristic.
    inputs:
      - name: application_id
        type: string
        description: The application's id in the loan system, e.g. APP-1002.
    script: scripts/gather.py
    timeout: 180
    inputs_to: hard-rules

  - name: hard-rules
    kind: execution
    description: Apply the lending policy with loan policy - hard rules R1-R6 and guidance G1 - giving auto_approve, auto_decline or review with the rules that fired, the figures and their cites.
    inputs:
      - name: application_id
        type: string
      - name: ownership_summary
        type: object
        description: Owners as shares and the businesses they hold 25% or more of, with those businesses' facilities and days late; no names of people.
    script: scripts/hard_rules.py
    timeout: 180
    inputs_to: by-rules

  - name: by-rules
    kind: router
    description: The hard rules decide the automatic bands without judgment; only review goes to the assessment.
    branch_on: policy_outcome
    branches:
      auto_approve: precedents
      auto_decline: precedents
      review: assess

  - name: assess
    kind: decision
    description: The judgment the policy left open - risk tier, whether the connected exposure is material, and the outcome - from the figures, the fired rules, the ownership summary, tenure, KYC status and the notes about the business.
    inputs:
      - name: figures
        type: object
        description: The policy's figures - coverage_ratio, avg_net_12m, proposed and existing and total monthly payments, exposure_total/own/connected, connected_worst_late_days, tenure, kyc_status, amount, term_months.
      - name: fired
        type: list[*]
        description: The rules that fired, each with rule, name, value, threshold, effect, cites.
      - name: ownership_summary
        type: object
        description: Owners as shares (owner 1, owner 2 ...) and the businesses they hold 25% or more of, with facilities and days late. Names of people are never in it.
      - name: tenure_years
        type: float
        description: Years the business has been a customer.
      - name: kyc_status
        type: string
        description: current | refresh_due | overdue.
      - name: crm_notes
        type: list[*]
        description: The relationship manager's notes about the business, names replaced by owner labels; notes mentioning a personal characteristic were withheld.
    questions:
      risk_tier:
        type: choice
        instructions: >
          What risk tier is the business? Start from its own numbers: the coverage ratio against the 1.25 floor
          (1.00 to 1.25 is the judgment band), the payment record on its own facilities, the twelve-month average
          net inflow against the twenty-four-month average (rising means growing), account balances against the
          total monthly payments, tenure and KYC status. Then lift the tier for what sits outside those numbers: a
          connected business with a facility 60 or more days late or consecutive missed payments, an expansion or
          second site this loan funds that the ratio gives no credit to, a fraud event, a KYC refresh due. A single
          short late payment with an operational explanation in the notes is an isolated event, not a delinquency
          signal. Judge the business, not the people.
        criteria:
          low: Coverage at or above 1.25 on the business's own cash flow, every own facility paid on time, KYC current, no fraud event, no connected arrears, and nothing in the notes that strains the business.
          medium: Clean on its own numbers but carrying one thing the figures cannot settle - coverage in the 1.00 to 1.25 band, a connected business with a late facility, or a second-site expansion the ratio gives no credit to - with every other signal clean.
          high: Several strains at once - coverage near 1.00 or weak liquidity, the business's own payments late or missed, a KYC refresh due or overdue, a fraud event, or a connected delinquency with nothing in the record to offset it.
      connected_exposure_material:
        type: noul
        instructions: >
          Is the connected exposure material to this decision? Connected exposure is what we lend to businesses an
          owner of the applicant holds 25% or more of: see ownership_summary.connected_businesses,
          figures.exposure_connected and figures.connected_worst_late_days. When no owner holds another business
          with us, or every connected facility is current, the answer is no.
        criteria:
          "true": A connected facility is 60 or more days late or has missed consecutive payments; or the connected principal is comparable to or larger than what the business itself owes us; or the owner who holds the connected business is the one the notes say will run what this loan funds; and nothing in the systems explains the arrears.
          "false": No owner holds another business with us; or every connected facility is current; or the connected balance is small next to the business's own exposure and nothing in the notes ties it to the funded project.
      outcome:
        type: choice
        instructions: >
          Approve, counter or decline? The policy said review, so this is the judgment. Approve when the rule that
          fired is answered by the business's own record: coverage inside the 1.00 to 1.25 band but strong balances, a
          rising twelve-month trend, a clean payment record, long tenure, KYC current, and the notes show demand for
          what the loan funds (pre-sales, a signed lease, a waiting list); or the connected business's facilities are
          current. Counter, a smaller amount or shorter term, only when the risk is capacity: the full payment is not
          covered but a smaller one is, and the purpose survives the cut. A counter does not address a risk that lives
          at a connected business. Decline when coverage sits near 1.00 with weak liquidity, the business's own
          payments are late or missed, or KYC is refresh_due with nothing to offset it; say what a reapplication would
          rest on. A connected facility 60 or more days late is never an automatic approval: when the deciding fact
          is not in the systems (why it is late, whether it is being cured or supported from the applicant's cash),
          lean on the outcome the business's own record supports and let your uncertainty show; a close call goes to
          a human. A decline on a customer of five years or more goes to a human before filing in any case.
        criteria:
          approve: Lend the full amount at the requested term; the fired review rule is answered by the business's own record and the notes about it.
          counter: Lend a smaller amount or a shorter term; capacity is the problem and the business covers a smaller payment.
          decline: Do not lend now; the figures and the record do not support it, and the rationale names what a reapplication would rest on.
    thresholds:
      risk_tier: 0.6
      connected_exposure_material: 0.3
      outcome: 0.6
    inputs_to: precedents

  - name: precedents
    kind: execution
    description: Look up filed decisions on the same product and band with loan precedents; settle the outcome for the automatic bands, set confidence and needs_human (a decline under G1), and build the evidence digest for the rationale.
    inputs:
      - name: application_id
        type: string
      - name: policy_outcome
        type: string
        description: auto_approve | auto_decline | review.
      - name: fired
        type: list[*]
      - name: guidance
        type: list[*]
        description: Guidance rules that apply (G1 when the customer has five years or more of tenure).
      - name: figures
        type: object
    script: scripts/precedents.py
    timeout: 180
    inputs_to: by-confidence

  - name: by-confidence
    kind: router
    description: A decline on a customer of five years or more ends the run unfiled for a human; everything else goes to the write-up. (An answer under its threshold has already paused for a review; that is the other way a human enters.)
    branch_on: needs_human
    branches:
      "true": end
      "false": rationale

  - name: rationale
    kind: client_task
    description: Write the rationale the customer and the examiner will read - outcome first, every figure cited to its record, precedents named, no person named, no personal characteristic.
    inputs:
      - name: application_id
        type: string
      - name: outcome
        type: string
        description: approve | counter | decline, already settled.
      - name: policy_outcome
        type: string
      - name: confidence
        type: float
      - name: judgment
        type: object
        description: source (hard rules | decision model), risk_tier, connected_exposure_material, outcome.
      - name: evidence_md
        type: string
        description: Every figure and fact in the state with the record keys it came from; the only material the rationale may quote.
      - name: cite_keys
        type: list[*]
        description: Every record key the rationale may cite.
    template: assets/rationale.md
    inputs_to: check

  - name: check
    kind: execution
    description: Write the rationale to a file, submit it with loan rationale submit, lint it with loan check; passed, fix (first failure) or stop.
    inputs:
      - name: application_id
        type: string
      - name: outcome
        type: string
      - name: rationale
        type: string
        description: The rationale in markdown, beginning with the outcome paragraph.
      - name: precedents_note
        type: string
        description: For the judgment log - which precedents applied and were followed or departed from, and why.
    script: scripts/check.py
    timeout: 180
    inputs_to: gate

  - name: gate
    kind: router
    description: Passed is filed; the first failure gets one fix pass; a second failure ends the run unfiled with a note for a human.
    branch_on: check_state
    branches:
      passed: record
      fix: fix
      stop: end

  - name: fix
    kind: client_task
    description: Fix exactly what the check named; one pass only.
    inputs:
      - name: rationale_id
        type: string
      - name: application_id
        type: string
      - name: outcome
        type: string
      - name: failures_md
        type: string
        description: The check's failures, one per line, as it named them.
      - name: rationale
        type: string
      - name: evidence_md
        type: string
      - name: cite_keys
        type: list[*]
    template: assets/fix.md
    inputs_to: recheck

  - name: recheck
    kind: execution
    description: Submit the fixed rationale and check it again; a second failure sets check_state to stop.
    inputs:
      - name: application_id
        type: string
      - name: outcome
        type: string
      - name: rationale
        type: string
      - name: attempt
        type: integer
        description: Rationales submitted so far; the second failure is stop.
    script: scripts/check.py
    timeout: 180
    inputs_to: gate

  - name: record
    kind: execution
    description: File the decision with loan record (outcome, confidence, this skill's revision) and log the judgment calls - risk tier, connected exposure, outcome, precedents - with loan decide.
    inputs:
      - name: application_id
        type: string
      - name: rationale_id
        type: string
      - name: outcome
        type: string
      - name: confidence
        type: float
        description: 1.0 when the hard rules decided; else the outcome threshold the decision model cleared.
      - name: passed
        type: boolean
        description: The check passed; record refuses an unchecked rationale.
    script: scripts/record.py
    timeout: 180
    inputs_to: end

  - name: end
    kind: end
    description: The decision for the application - filed with a decision id, or ended unfiled with a note saying what a human must do.
    inputs:
      - name: application_id
        type: string
      - name: outcome
        type: string
        description: approve | counter | decline.
      - name: needs_human
        type: boolean
        description: True when a decline on a customer of five years or more stopped before filing.
      - name: decision_id
        type: string
        description: The filed Decision's key (DEC-APP-NNNN-NN); empty when nothing was filed.
      - name: note
        type: string
        description: What was decided and filed, or what a human must do next.

anti_patterns:
  - Forming a view before the policy has run, or arguing with a hard rule in the write-up because the cash flow looks strong.
  - Treating a late facility at a business an owner holds a quarter or more of as immaterial because the applicant looks clean on its own; it is never an automatic approval.
  - "Quoting a figure the systems do not hold - the interest rate as a percentage, a derived or rounded-up number, a day count the records do not show - or leaving a figure without its [cite: KEY] marker."
  - Naming a person, or mentioning an owner's age, date of birth, sex, gender, ethnicity, race, religion, national origin, nationality, marital status, disability or pregnancy anywhere in the file; describe the business, not the people.
  - Passing a withheld note, a date of birth or a person's name into the assessment by editing the state; the judgment step cannot see protected characteristics.
  - Looping on fixes after a failed check; one fix pass, then a human.
  - Filing a decline on a customer of five years or more without a human seeing it first, or filing anything before the check has passed.
  - Countering at a smaller amount to address a risk that lives at a connected business rather than in the applicant's capacity.
  - Treating precedents as binding; follow or depart, but say which and why.
```
