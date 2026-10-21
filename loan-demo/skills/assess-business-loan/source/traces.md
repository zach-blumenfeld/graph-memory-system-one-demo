# Recorded runs: what the agent actually did

Five Claude Code sessions assessed a business-loan application from the credit team's page with only the `loan` tools, no skill. Each run below is read back from memory: the prompt, every `loan` call in order with its result, every judgment call the agent logged with `loan decide`, and the agent's closing summary. Treat the judgment calls as the decision points of the procedure and the `loan` commands as its scripts. run-01 and run-05 are the same application, so differences between them are differences in the agent's path, not the input.

## run-01 (hero, APP-1001)

Prompt:

> You are the credit analyst at Lantern Mutual. Start by reading the team's page: run `loan sop`.
> The `loan` command is your only way to reach the bank's systems (`loan --help` lists it).
> Write the rationale to a file and submit it with `loan rationale submit`, check it with
> `loan check`, and record the decision with `loan record` (use `--revision freeform` and your
> own confidence between 0 and 1). Log every judgment call with `loan decide`. Finish with a
> short summary.
> 
> New application APP-1001: Harrow Street Bakery, $400,000 term loan for a second location.
> Assess it and record the decision.

1. `loan sop` → success: `{"name": "How we assess a business loan", "source": "memory", "text": "# How we assess a business loan\n\nOwner: Lantern Mutual credit team. This is the page new analysts get pointed at; it is how we\nexpect every business-loan application to be worked, from the first look to the filed decision.\n\n`
2. `loan application APP-1001` → success: `{"as_of": "2026-10-13", "application": {"key": "APP-1001", "product": "term loan", "amount": 400000, "term_months": 84, "rate": 0.085, "proposed_monthly_payment": 6334.59, "purpose": "Second location: fit-out and ovens for a second bakery on Lantern Row, with a wholesale kitchen at the back.", "subm`
3. `loan policy APP-1001` → success: `{"application": "APP-1001", "outcome": "review", "fired": [{"rule": "R5", "name": "connected_delinquency", "value": 90, "threshold": 60, "effect": "review", "cites": ["FAC-03", "PAY-03-2026-07", "PAY-03-2026-08", "PAY-03-2026-09"]}], "guidance": [{"rule": "G1", "name": "long_customer_decline", "valu`
4. `loan precedents APP-1001` → success: `{"application": "APP-1001", "product": "term loan", "policy_band": "review", "precedents": [], "cites": []}`
5. `loan ownership BUS-01` → success: `{"business": "BUS-01", "owners": [{"person": {"key": "PER-01", "name": "Priya Raghunathan"}, "pct": 55, "since": "2016-03-01", "other_businesses": []}, {"person": {"key": "PER-02", "name": "Tom Alder"}, "pct": 45, "since": "2016-03-01", "other_businesses": [{"business": {"key": "BUS-05", "name": "Al`
6. `loan facilities BUS-01` → success: `{"business": "BUS-01", "as_of": "2026-10-13", "facilities": [{"key": "FAC-01", "product": "equipment loan", "principal": 120000, "rate": 0.0725, "term_months": 60, "monthly_payment": 2390.32, "opened": "2023-03-15", "status": "open", "late_days": 0, "missed_payment_keys": [], "payments": [{"key": "P`
7. `loan facilities BUS-05` → success: `{"business": "BUS-05", "as_of": "2026-10-13", "facilities": [{"key": "FAC-03", "product": "term loan", "principal": 300000, "rate": 0.08, "term_months": 60, "monthly_payment": 6082.92, "opened": "2024-02-15", "status": "open", "late_days": 90, "missed_payment_keys": ["PAY-03-2026-07", "PAY-03-2026-0`
8. `loan cashflow BUS-01` → success: `{"business": "BUS-01", "accounts": [{"key": "ACC-101", "type": "operating", "balance": 86400.0, "opened": "2020-09-14"}, {"key": "ACC-102", "type": "savings", "balance": 150000.0, "opened": "2021-02-01"}], "last_12m": {"months": 12, "avg_inflow": 113582.13, "avg_outflow": 99622.28, "avg_net": 13959.`
9. `loan kyc BUS-01; echo ---; loan kyc BUS-05` → success: `"{\n  \"business\": \"BUS-01\",\n  \"as_of\": \"2026-10-13\",\n  \"kyc\": {\n    \"key\": \"KYC-BUS-01\",\n    \"status\": \"current\",\n    \"last_review\": \"2026-03-14\",\n    \"beneficial_owners_verified\": true\n  },\n  \"fraud_events\": [],\n  \"cites\": [\n    \"KYC-BUS-01\"\n  ]\n}\n---\n{\n`
10. **Judgment** `What risk tier is Harrow Street Bakery (BUS-01) for APP-1001?` → **medium** (options: low,medium,high). Why: On its own the business is low risk: coverage 1.6 on avg net 13,959.86 against total payments 8,724.91, six years tenure, every FAC-01 payment current, KYC current, no fraud. But a 45% owner holds 60% of Alder Logistics (BUS-05), whose 300,000 term loan FAC-03 paid late in June 2026 and has missed July, August and September (90 days). An owner with a connected business in active default raises the tier one notch to medium.
11. **Judgment** `Is the connected exposure at Alder Logistics (FAC-03, 300,000, 90 days late) material to APP-1001?` → **material** (options: material,not material). Why: Tom Alder owns 45% of the applicant and 60% of Alder Logistics, and NOTE-01 says he will run the second site day to day. FAC-03 is not an old blip: June 2026 was paid late and the next three payments were missed outright, so the trend is worsening at the time of application. Connected exposure is 300,000 of the 820,000 total. The new facility would put a further 400,000 behind the same owner while his other business is three payments behind. That is material.
12. **Judgment** `What outcome for APP-1001: approve, counter, decline, or refer to a human?` → **refer** (options: approve,counter,decline,refer). Why: Approve: not available as an automatic outcome with a 90-day connected delinquency (SOP rule 2), and the delinquency is live and worsening. Counter: a smaller amount or shorter term does not address the connected risk, which is about the owner not the applicant's coverage. Decline: the applicant itself is clean, coverage is 1.6, and G1 sends any decline on a six-year customer to a human anyway. The systems do not say why Alder Logistics stopped paying, whether bakery cash is supporting it, or whether a cure is in train. I am not sure enough to approve or decline, so I refer. A human should consider approval conditioned on FAC-03 being brought current or restructured, or a cross-default term.
13. **Judgment** `Do any precedents apply to APP-1001?` → **none on file** (options: apply,none on file). Why: loan precedents APP-1001 returned no past Decision nodes for a term loan in the review band, so the rationale leans on no precedents and says so.
14. `loan rationale submit --file /Users/zach/dev/graph-memory-system-one-demo/loan-demo/.run/rationale-APP-1001.md --application APP-1001 --outcome refer` → success: `{"rationale_id": "RAT-APP-1001-01", "application": "APP-1001", "outcome": "refer", "chars": 4938, "cites": ["APP-1001", "BUS-01", "BUS-05", "FAC-01", "FAC-03", "FAC-07", "KYC-BUS-01", "KYC-BUS-05", "MON-101-2025-10", "MON-101-2025-11", "MON-101-2025-12", "MON-101-2026-01", "MON-101-2026-02", "MON-10`
15. `loan check RAT-APP-1001-01` → success: `{"rationale_id": "RAT-APP-1001-01", "application": "APP-1001", "outcome": "refer", "passed": true, "failures": [], "cites": ["APP-1001", "BUS-01", "BUS-05", "FAC-01", "FAC-03", "FAC-07", "KYC-BUS-01", "KYC-BUS-05", "MON-101-2025-10", "MON-101-2025-11", "MON-101-2025-12", "MON-101-2026-01", "MON-101-`
16. `loan check RAT-APP-1001-01 | head -8` → success: `"{\n  \"rationale_id\": \"RAT-APP-1001-01\",\n  \"application\": \"APP-1001\",\n  \"outcome\": \"refer\",\n  \"passed\": true,\n  \"failures\": [],\n  \"cites\": [\n    \"APP-1001\","`
17. `loan record RAT-APP-1001-01 --outcome refer --confidence 0.7 --revision freeform` → success: `{"decision_id": "DEC-APP-1001-01", "application": "APP-1001", "outcome": "refer", "confidence": 0.7, "skill_revision": "freeform", "policy_outcome": "review", "applied_policy": ["R5"], "cites": ["APP-1001", "BUS-01", "BUS-05", "FAC-01", "FAC-03", "FAC-07", "KYC-BUS-01", "KYC-BUS-05", "MON-101-2025-1`

Agent's closing summary:

> APP-1001 is assessed and filed as a referral to a human, decision DEC-APP-1001-01, confidence 0.7, revision freeform.
> 
> **What the policy found.** The outcome was review with one rule fired, R5 connected delinquency. Every other test was clean: coverage 1.6 against a 1.25 floor, six years with us, KYC current, no fraud events, no exposure cap breach.
> 
> **What drove the referral.** Tom Alder owns 45% of the bakery and 60% of Alder Logistics. That business's $300k term loan with us paid late in June and has missed July, August and September, so it is 90 days late and getting worse. He is also the person the relationship manager says will run the new site. On its own the bakery is a low-risk credit with a spotless payment record. The systems do not say why the connected business stopped paying or whether bakery cash is propping it up, so neither approve nor decline is defensible yet.
> 
> **Judgments logged with loan decide.**
> - Risk tier: medium. Low on the bakery's own figures, moved up one notch for the owner's connected default.
> - Connected exposure: material. Live, worsening, and the same owner would sit behind another $400k.
> - Outcome: refer. A counter does not address an owner-level risk, and a decline on a six-year customer goes to a human under G1 anyway.
> - Precedents: none on file for a term loan in the review band.
> 
> **Filing steps.** The rationale is at `.run/rationale-APP-1001.md`, submitted as RAT-APP-1001-01. It passed the check twice with no failures, and the decision is recorded.
> 
> **For the human reviewer.** The rationale suggests approval conditioned on the Alder Logistics facility being brought current or restructured first, or a cross-default term.
> 
> One quirk worth knowing: the submit command's help lists the outcome as review, but it only accepts refer. I noted that in my memory for next time.

## run-02 (clean, APP-1002)

Prompt:

> You are the credit analyst at Lantern Mutual. Start by reading the team's page: run `loan sop`.
> The `loan` command is your only way to reach the bank's systems (`loan --help` lists it).
> Write the rationale to a file and submit it with `loan rationale submit`, check it with
> `loan check`, and record the decision with `loan record` (use `--revision freeform` and your
> own confidence between 0 and 1). Log every judgment call with `loan decide`. Finish with a
> short summary.
> 
> New application APP-1002: Ridgeline Dental Partners, $250,000 equipment loan.
> Assess it and record the decision.

1. `loan sop 2>&1; echo -----; loan --help 2>&1` → success: `"with those businesses' facilities and payment status   \u2502\n\u2502              (two hops in the graph).                                        \u2502\n\u2502 facilities   A business's facilities and their payments, with days late per  \u2502\n\u2502              facility.                       `
2. `loan application APP-1002 2>&1` → success: `{"as_of": "2026-10-13", "application": {"key": "APP-1002", "product": "equipment loan", "amount": 250000, "term_months": 60, "rate": 0.079, "proposed_monthly_payment": 5057.14, "purpose": "Equipment: two digital imaging units and a sterilisation suite for the third chair.", "submitted": "2026-10-02"`
3. `loan $c --help 2>&1 | sed -n 1,40p; done` → success: `"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u256f\n\n=== decide\n                                                                                \n Usage: loan decide [OPTION`
4. `loan policy APP-1002 2>&1` → success: `{"application": "APP-1002", "outcome": "auto_approve", "fired": [], "guidance": [{"rule": "G1", "name": "long_customer_decline", "value": 7.6, "threshold": 5, "effect": "a decline goes to a human before filing", "cites": ["BUS-02"]}], "figures": {"coverage_ratio": 1.9, "avg_net_12m": 9608.57, "propo`
5. `loan ownership BUS-02 2>&1` → success: `{"business": "BUS-02", "owners": [{"person": {"key": "PER-04", "name": "Marcus Tiller"}, "pct": 50, "since": "2015-06-01", "other_businesses": []}, {"person": {"key": "PER-03", "name": "Anneliese Okafor"}, "pct": 50, "since": "2015-06-01", "other_businesses": []}], "min_pct": 25.0, "cites": ["BUS-02`
6. `loan facilities BUS-02 2>&1` → success: `{"business": "BUS-02", "as_of": "2026-10-13", "facilities": [], "existing_monthly_payments": 0, "cites": []}`
7. `loan cashflow BUS-02 2>&1` → success: `{"business": "BUS-02", "accounts": [{"key": "ACC-201", "type": "operating", "balance": 212000.0, "opened": "2019-03-01"}, {"key": "ACC-202", "type": "savings", "balance": 310000.0, "opened": "2019-03-01"}], "last_12m": {"months": 12, "avg_inflow": 98925.73, "avg_outflow": 89317.17, "avg_net": 9608.5`
8. `loan kyc BUS-02 2>&1` → success: `{"business": "BUS-02", "as_of": "2026-10-13", "kyc": {"key": "KYC-BUS-02", "status": "current", "last_review": "2026-05-20", "beneficial_owners_verified": true}, "fraud_events": [], "cites": ["KYC-BUS-02"]}`
9. `loan precedents APP-1002 2>&1` → success: `{"application": "APP-1002", "product": "equipment loan", "policy_band": "auto_approve", "precedents": [], "cites": []}`
10. **Judgment** `Accept the policy auto-approve for APP-1002, or refer or counter anyway because the twelve-month cash flow predates the third chair added in July 2026?` → **approve** (options: approve,counter,refer). Why: No rule fired and coverage is 1.9 against a 1.25 floor, so the practice carries the full 5,057.14 payment with nearly half the net inflow to spare before any revenue from the third chair. The business holds no other facilities, the savings account balance exceeds the loan amount, and the relationship manager notes a six-week waiting list, so the expansion is demand-led rather than speculative. Nothing in the systems argues for a smaller amount or a human read.
11. **Judgment** `What risk tier is Ridgeline Dental (BUS-02) for APP-1002?` → **low** (options: low,medium,high). Why: Coverage of 1.9, 7.6 years with us, no existing facilities and so no payment history to fault, KYC current with beneficial owners verified, no fraud events, no connected businesses, and twelve-month average net inflow above the twenty-four-month average so the trend is up. Nothing moves it off low.
12. **Judgment** `Is connected exposure material to the APP-1002 decision?` → **not material** (options: material,not material). Why: Both owners hold 50% of the applicant and neither holds 25% or more of any other business, so the two-hop lookup returns nothing. Connected exposure and connected delinquency are both zero; total exposure is the 250,000 requested alone.
13. **Judgment** `Do any precedents apply to APP-1002?` → **no precedent applies** (options: lean on a precedent,no precedent applies). Why: The precedent lookup for an equipment loan in the auto_approve band returns no past decisions, so there is nothing to follow or depart from. This decision will be the first precedent in that band.
14. `loan rationale submit --file .run/rationale-APP-1002.md --application APP-1002 --outcome approve 2>&1` → success: `{"rationale_id": "RAT-APP-1002-01", "application": "APP-1002", "outcome": "approve", "chars": 4432, "cites": ["APP-1002", "BUS-02", "KYC-BUS-02", "MON-201-2025-10", "MON-201-2025-11", "MON-201-2025-12", "MON-201-2026-01", "MON-201-2026-02", "MON-201-2026-03", "MON-201-2026-04", "MON-201-2026-05", "M`
15. `loan check RAT-APP-1002-01 2>&1` → success: `{"rationale_id": "RAT-APP-1002-01", "application": "APP-1002", "outcome": "approve", "passed": true, "failures": [], "cites": ["APP-1002", "BUS-02", "KYC-BUS-02", "MON-201-2025-10", "MON-201-2025-11", "MON-201-2025-12", "MON-201-2026-01", "MON-201-2026-02", "MON-201-2026-03", "MON-201-2026-04", "MON`
16. `loan record RAT-APP-1002-01 --outcome approve --confidence 0.9 --revision freeform 2>&1` → success: `{"decision_id": "DEC-APP-1002-01", "application": "APP-1002", "outcome": "approve", "confidence": 0.9, "skill_revision": "freeform", "policy_outcome": "auto_approve", "applied_policy": [], "cites": ["APP-1002", "BUS-02", "KYC-BUS-02", "MON-201-2025-10", "MON-201-2025-11", "MON-201-2025-12", "MON-201`

Agent's closing summary:

> APP-1002 is approved and filed as decision DEC-APP-1002-01 with confidence 0.9, revision freeform.
> 
> **What the systems showed.** The policy check returned auto-approve with no rule fired. Ridgeline Dental carries the proposed payment at a coverage ratio of 1.9 on its twelve-month average net inflow, well above the 1.25 floor, and the last year runs ahead of the two-year average. The practice has no existing facilities, so total exposure is just the amount requested. Both owners hold half the business and neither holds a stake in any other business, so the two-hop lookup found no connected exposure or delinquency. KYC is current with beneficial owners verified, there are no fraud events, and the practice has banked with us for 7.6 years. Guidance G1 was noted only because a decline on a customer of that tenure would have needed a human; it has no effect on an approval. No precedents exist for an equipment loan in this band, so this decision becomes the first.
> 
> **Judgment calls logged with `loan decide`:**
> - Accept the auto-approve rather than counter or refer, even though the cash flow predates the third chair added in July. The old run rate alone covers the payment, and the six-week waiting list in the relationship manager's note shows demand-led expansion.
> - Risk tier: low.
> - Connected exposure: not material, because there is none.
> - Precedents: none apply.
> 
> **Filing steps.** The rationale was written to `.run/rationale-APP-1002.md`, submitted as RAT-APP-1002-01, and passed `loan check` on the first run with no failures, so no second pass was needed. It cites 30 records, including every month node behind the coverage figure, and mentions nothing about the owners beyond their names and shares.

## run-03 (decline, APP-1003)

Prompt:

> You are the credit analyst at Lantern Mutual. Start by reading the team's page: run `loan sop`.
> The `loan` command is your only way to reach the bank's systems (`loan --help` lists it).
> Write the rationale to a file and submit it with `loan rationale submit`, check it with
> `loan check`, and record the decision with `loan record` (use `--revision freeform` and your
> own confidence between 0 and 1). Log every judgment call with `loan decide`. Finish with a
> short summary.
> 
> New application APP-1003: Corvid Print Co., $150,000 working capital line.
> Assess it and record the decision.

1. `loan sop` → success: `{"name": "How we assess a business loan", "source": "memory", "text": "# How we assess a business loan\n\nOwner: Lantern Mutual credit team. This is the page new analysts get pointed at; it is how we\nexpect every business-loan application to be worked, from the first look to the filed decision.\n\n`
2. `loan application APP-1003` → success: `{"as_of": "2026-10-13", "application": {"key": "APP-1003", "product": "working capital line", "amount": 150000, "term_months": 36, "rate": 0.095, "proposed_monthly_payment": 4804.94, "purpose": "Working capital: paper stock and payroll through the seasonal trough.", "submitted": "2026-10-05", "reque`
3. `loan policy APP-1003` → success: `{"application": "APP-1003", "outcome": "auto_decline", "fired": [{"rule": "R1", "name": "kyc_current", "value": "overdue", "threshold": "current", "effect": "auto_decline", "cites": ["KYC-BUS-03"]}, {"rule": "R2", "name": "no_fraud_12m", "value": "4.1 months ago", "threshold": "12 months", "effect":`
4. `loan kyc BUS-03` → success: `{"business": "BUS-03", "as_of": "2026-10-13", "kyc": {"key": "KYC-BUS-03", "status": "overdue", "last_review": "2024-07-02", "beneficial_owners_verified": false}, "fraud_events": [{"key": "FRD-01", "date": "2026-06-10", "kind": "counterfeit cheque deposits; operating account blocked by the fraud tea`
5. `loan ownership BUS-03` → success: `{"business": "BUS-03", "owners": [{"person": {"key": "PER-05", "name": "Declan Hurst"}, "pct": 100, "since": "2018-02-01", "other_businesses": []}], "min_pct": 25.0, "cites": ["BUS-03", "PER-05"]}`
6. `loan facilities BUS-03` → success: `{"business": "BUS-03", "as_of": "2026-10-13", "facilities": [{"key": "FAC-06", "product": "term loan", "principal": 60000, "rate": 0.095, "term_months": 48, "monthly_payment": 1507.39, "opened": "2024-05-15", "status": "open", "late_days": 0, "missed_payment_keys": [], "payments": [{"key": "PAY-06-2`
7. `loan cashflow BUS-03` → success: `{"business": "BUS-03", "accounts": [{"key": "ACC-301", "type": "operating", "balance": 9800.0, "opened": "2023-05-01"}], "last_12m": {"months": 12, "avg_inflow": 102575.36, "avg_outflow": 94369.33, "avg_net": 8206.03, "from": "2025-10", "to": "2026-09"}, "last_24m": {"months": 24, "avg_inflow": 9830`
8. `loan precedents APP-1003` → success: `{"application": "APP-1003", "product": "working capital line", "policy_band": "auto_decline", "precedents": [], "cites": []}`
9. **Judgment** `APP-1003 Corvid Print: the policy returns auto_decline on R1 (KYC overdue) and R2 (fraud event 4.1 months ago). Coverage is 1.30 and the existing term loan has no late payments. Should this be filed as a decline, referred to a human, or countered at a smaller amount?` → **decline** (options: decline,refer,counter). Why: R1 and R2 are hard rules and the SOP says not to argue with a hard rule in the write-up. Tenure is 41 months (3.4 years), under the five-year threshold that sends a decline to a human first. The clean payment history and 1.30 coverage do not override an overdue KYC with beneficial owners unverified and a counterfeit cheque fraud event four months ago. A counter is still a credit extension and is barred by the same rules. Noted that the applicant may reapply once KYC is refreshed and twelve months have passed since the fraud event.
10. **Judgment** `APP-1003 Corvid Print: what risk tier applies, and is connected exposure material?` → **high; connected exposure not material** (options: low,medium,high; connected material: yes,no). Why: High because the operating account was blocked by the fraud team in June 2026 after counterfeit cheque deposits (FRD-01), KYC is overdue with beneficial owners unverified (KYC-BUS-03, last review 2024-07-02), and the relationship manager notes two unanswered KYC refresh requests (NOTE-04). Underlying cash flow is sound (coverage 1.30) but integrity and identity risk dominate. Connected exposure is zero: the sole owner holds no other business at 25% or more, so exposure is the existing 60,000 term loan plus the 150,000 requested, 210,000 total, all at Corvid Print itself.
11. `loan rationale submit --file /Users/zach/dev/graph-memory-system-one-demo/loan-demo/corvid-print-app-1003.md --application APP-1003 --outcome decline` → success: `{"rationale_id": "RAT-APP-1003-01", "application": "APP-1003", "outcome": "decline", "chars": 3935, "cites": ["APP-1003", "BUS-03", "FAC-06", "FRD-01", "KYC-BUS-03", "MON-301-2025-10", "MON-301-2025-11", "MON-301-2025-12", "MON-301-2026-01", "MON-301-2026-02", "MON-301-2026-03", "MON-301-2026-04", "`
12. `loan check RAT-APP-1003-01` → success: `{"rationale_id": "RAT-APP-1003-01", "application": "APP-1003", "outcome": "decline", "passed": true, "failures": [], "cites": ["APP-1003", "BUS-03", "FAC-06", "FRD-01", "KYC-BUS-03", "MON-301-2025-10", "MON-301-2025-11", "MON-301-2025-12", "MON-301-2026-01", "MON-301-2026-02", "MON-301-2026-03", "MO`
13. `loan check RAT-APP-1003-01` → success: `{"rationale_id": "RAT-APP-1003-01", "application": "APP-1003", "outcome": "decline", "passed": true, "failures": [], "cites": ["APP-1003", "BUS-03", "FAC-06", "FRD-01", "KYC-BUS-03", "MON-301-2025-10", "MON-301-2025-11", "MON-301-2025-12", "MON-301-2026-01", "MON-301-2026-02", "MON-301-2026-03", "MO`
14. `loan record RAT-APP-1003-01 --outcome decline --confidence 0.95 --revision freeform` → success: `{"decision_id": "DEC-APP-1003-01", "application": "APP-1003", "outcome": "decline", "confidence": 0.95, "skill_revision": "freeform", "policy_outcome": "auto_decline", "applied_policy": ["R1", "R2"], "cites": ["APP-1003", "BUS-03", "FAC-06", "FRD-01", "KYC-BUS-03", "MON-301-2025-10", "MON-301-2025-1`

Agent's closing summary:

> **APP-1003, Corvid Print Co., is declined.** The decision is filed as DEC-APP-1003-01 with confidence 0.95, revision freeform.
> 
> **Why it was declined.** The policy check fired two hard rules, so no judgment was available on the outcome:
> 
> - **KYC overdue (R1).** Last review was July 2024 and beneficial owners are unverified. The relationship manager notes two refresh requests went unanswered.
> - **Fraud event inside twelve months (R2).** The fraud team blocked the operating account in June 2026 after counterfeit cheque deposits, 4.1 months before the assessment date.
> 
> **What was otherwise clean.** Coverage is 1.3, above the 1.25 floor. The existing term loan has never been paid late. The sole owner holds no other businesses, so connected exposure is zero. Tenure is 3.4 years, so a human sign-off before filing the decline was not required. No precedents exist for this product in the auto-decline band.
> 
> **Judgment calls logged with loan decide.**
> - Decline rather than refer or counter. Hard rules bar any credit extension, and the SOP says not to argue with them in the write-up.
> - Risk tier high, connected exposure not material.
> 
> **Process.** The rationale is at `loan-demo/corvid-print-app-1003.md`, submitted as RAT-APP-1003-01. It passed the check on both runs with no failures. The write-up notes the business may reapply once KYC is refreshed and twelve months have passed since the fraud event.
> 
> One note for future runs: the options flag on `loan decide` splits only on commas, so my second call bundling two questions produced a slightly garbled options list in the log. I saved a memory to log one question per call next time.

## run-04 (gray, APP-1004)

Prompt:

> You are the credit analyst at Lantern Mutual. Start by reading the team's page: run `loan sop`.
> The `loan` command is your only way to reach the bank's systems (`loan --help` lists it).
> Write the rationale to a file and submit it with `loan rationale submit`, check it with
> `loan check`, and record the decision with `loan record` (use `--revision freeform` and your
> own confidence between 0 and 1). Log every judgment call with `loan decide`. Finish with a
> short summary.
> 
> New application APP-1004: Mossbank Climbing Gym, $600,000 term loan for a second gym.
> Assess it and record the decision.

1. `loan sop` → success: `{"name": "How we assess a business loan", "source": "memory", "text": "# How we assess a business loan\n\nOwner: Lantern Mutual credit team. This is the page new analysts get pointed at; it is how we\nexpect every business-loan application to be worked, from the first look to the filed decision.\n\n`
2. `loan application APP-1004` → success: `{"as_of": "2026-10-13", "application": {"key": "APP-1004", "product": "term loan", "amount": 600000, "term_months": 120, "rate": 0.085, "proposed_monthly_payment": 7439.14, "purpose": "Fit-out of a second gym in the Mossbank Mill lease: walls, matting, changing rooms.", "submitted": "2026-10-07", "r`
3. `loan policy APP-1004` → success: `{"application": "APP-1004", "outcome": "review", "fired": [{"rule": "R3", "name": "coverage_floor", "value": 1.15, "threshold": 1.25, "effect": "review", "cites": ["MON-401-2025-10", "MON-401-2025-11", "MON-401-2025-12", "MON-401-2026-01", "MON-401-2026-02", "MON-401-2026-03", "MON-401-2026-04", "MO`
4. `loan cashflow BUS-04` → success: `{"business": "BUS-04", "accounts": [{"key": "ACC-401", "type": "operating", "balance": 142000.0, "opened": "2019-05-20"}, {"key": "ACC-402", "type": "savings", "balance": 95000.0, "opened": "2020-01-15"}], "last_12m": {"months": 12, "avg_inflow": 59464.1, "avg_outflow": 47381.28, "avg_net": 12082.82`
5. `loan facilities BUS-04` → success: `{"business": "BUS-04", "as_of": "2026-10-13", "facilities": [{"key": "FAC-02", "product": "term loan", "principal": 200000, "rate": 0.075, "term_months": 84, "monthly_payment": 3067.66, "opened": "2022-06-15", "status": "open", "late_days": 0, "missed_payment_keys": [], "payments": [{"key": "PAY-02-`
6. `loan kyc BUS-04` → success: `{"business": "BUS-04", "as_of": "2026-10-13", "kyc": {"key": "KYC-BUS-04", "status": "current", "last_review": "2026-01-22", "beneficial_owners_verified": true}, "fraud_events": [], "cites": ["KYC-BUS-04"]}`
7. `loan ownership BUS-04` → success: `{"business": "BUS-04", "owners": [{"person": {"key": "PER-06", "name": "Ingrid Vossberg"}, "pct": 70, "since": "2018-09-01", "other_businesses": []}, {"person": {"key": "PER-07", "name": "Ben Achterberg"}, "pct": 30, "since": "2020-01-01", "other_businesses": []}], "min_pct": 25.0, "cites": ["BUS-04`
8. `loan precedents APP-1004` → success: `{"application": "APP-1004", "product": "term loan", "policy_band": "review", "precedents": [{"key": "DEC-APP-1001-01", "application": "APP-1001", "business": "BUS-01", "outcome": "refer", "confidence": 0.7, "skill_revision": "freeform", "at": "2026-10-21T21:37:26+00:00", "rules": ["R5"], "rationale_`
9. **Judgment** `APP-1004: what is the risk tier of Mossbank Climbing (BUS-04)?` → **medium** (options: low,medium,high). Why: Coverage is 1.15 on the twelve-month average, inside the 1.00 to 1.25 judgment band (R3). The summer trough months of 2026 (MON-401-2026-06 to MON-401-2026-08) run close to the combined payments of 10506.80, so the business leans on its balances in those months. Against that: 7.3 years with us, KYC current, no fraud, no connected businesses, FAC-02 at 0 days late, and 12m net above 24m net so the trend is up. A fit-out loan on leased premises has little recoverable security and the lease (NOTE-05) carries a break at five years inside the 120-month term. Not low because of the coverage shortfall and the execution risk of a second site; not high because every other test is clean.
10. **Judgment** `APP-1004: is connected exposure material to this decision?` → **no** (options: yes,no). Why: Neither owner (PER-06 at 70 percent and PER-07 at 30 percent) holds 25 percent or more of any other business, so connected exposure is 0 and connected worst late days is 0. The exposure figure of 800000 is entirely the applicant's own: FAC-02 at 200000 plus the requested 600000. No exposure or connected-delinquency rule fired.
11. **Judgment** `APP-1004: does precedent DEC-APP-1001-01 (term loan in the review band) apply to this case?` → **does not apply** (options: applies,does not apply,applies in part). Why: DEC-APP-1001-01 was referred because a 45 percent owner held 60 percent of a connected business whose facility was 90 days late (R5). It is the only filed decision in the same product and band, but the reason it was referred does not exist here: Mossbank Climbing has no connected businesses and no delinquency anywhere. The review flag here is coverage (R3), which that precedent did not have to judge. Noted in the write-up as the only precedent in the band and the reason it is not followed.
12. **Judgment** `APP-1004: does the one late payment on FAC-02 (PAY-02-2025-08) weigh against the application?` → **no** (options: yes,no). Why: The August 2025 payment on FAC-02 was paid seven days after the due date (due 2025-08-15, paid 2025-08-22). The relationship manager's note NOTE-06 from 2025-11-05 records that the card terminal was being replaced that week. Every other payment from October 2024 to September 2026 was made on its due date and the facility stands at 0 days late. A single seven-day slip with a documented operational cause is conduct noise, not a credit signal.
13. **Judgment** `APP-1004: is a counter-offer at a smaller amount or a shorter term better than the full 600000 over 120 months?` → **approve full amount** (options: approve full amount,counter smaller amount,counter shorter term). Why: A shorter term raises the monthly payment and pushes coverage further below 1.25, so it makes the review flag worse. A smaller amount would lift coverage toward the floor but leaves the fit-out of the second gym underfunded, and an unfinished fit-out is a worse credit than a finished one carrying a 1.15 ratio; the business would fill the gap from the balances that are its cushion for the seasonal trough. The 1.15 ratio is computed on the existing gym's cash flow alone and gives no credit to the second site, where 412 founder memberships were pre-sold before opening (NOTE-05). The full amount at the requested term is the coherent structure.
14. **Judgment** `APP-1004: with the policy at review on coverage alone, what is the outcome?` → **approve** (options: approve,counter,decline,refer). Why: Coverage of 1.15 is a judgment band, not a decline, and every other test is clean: KYC current (KYC-BUS-04), no fraud events, no connected businesses, FAC-02 at 0 days late, 7.3 years of tenure. Operating and savings balances of 142000 and 95000 (ACC-401 and ACC-402) are roughly two years of the combined monthly payments, which covers the summer months where net inflow runs near the payment load. The original gym is at capacity on weekday evenings and the second site has 412 pre-sold memberships (NOTE-05), so the purpose is growth the existing site cannot absorb. I am sure enough to decide rather than refer; confidence 0.7, with the shortfall to 1.25 and the five-year lease break the reasons it is not higher. A decline would in any case go to a human under G1 at this tenure, and the facts do not support one.
15. `loan rationale submit --file /Users/zach/dev/graph-memory-system-one-demo/loan-demo/mossbank-climbing-app-1004.md --application APP-1004 --outcome approve` → success: `{"rationale_id": "RAT-APP-1004-01", "application": "APP-1004", "outcome": "approve", "chars": 7092, "cites": ["ACC-401", "ACC-402", "APP-1004", "BUS-04", "DEC-APP-1001-01", "FAC-02", "KYC-BUS-04", "MON-401-2025-10", "MON-401-2025-11", "MON-401-2025-12", "MON-401-2026-01", "MON-401-2026-02", "MON-401`
16. `loan check RAT-APP-1004-01` → success: `{"rationale_id": "RAT-APP-1004-01", "application": "APP-1004", "outcome": "approve", "passed": true, "failures": [], "cites": ["ACC-401", "ACC-402", "APP-1004", "BUS-04", "DEC-APP-1001-01", "FAC-02", "KYC-BUS-04", "MON-401-2025-10", "MON-401-2025-11", "MON-401-2025-12", "MON-401-2026-01", "MON-401-2`
17. `loan record RAT-APP-1004-01 --outcome approve --confidence 0.7 --revision freeform` → success: `{"decision_id": "DEC-APP-1004-01", "application": "APP-1004", "outcome": "approve", "confidence": 0.7, "skill_revision": "freeform", "policy_outcome": "review", "applied_policy": ["R3"], "cites": ["ACC-401", "ACC-402", "APP-1004", "BUS-04", "FAC-02", "KYC-BUS-04", "MON-401-2025-10", "MON-401-2025-11`

Agent's closing summary:

> APP-1004 is assessed, checked and filed. Decision DEC-APP-1004-01: **approve** at the full 600,000 over 120 months, confidence 0.7, revision freeform.
> 
> **What the policy found.** One rule fired, R3 on coverage, putting the application in the review band. Everything else was clean: KYC current, no fraud events, no connected businesses or connected delinquency, the existing term loan at zero days late, and a 7.3-year tenure that would have sent any decline to a human under G1.
> 
> | Figure | Value |
> |---|---|
> | Coverage ratio | 1.15 against a 1.25 floor |
> | 12-month average net inflow | 12,082.82 |
> | Total monthly payments after the loan | 10,506.80 |
> | Total exposure after the loan | 800,000, none of it connected |
> 
> **Why approve rather than counter or refer.** The ratio is computed on the existing gym alone and gives no credit to the second site, where 412 founder memberships were pre-sold and the original gym is already at capacity on weekday evenings. Operating and savings balances of roughly two years of combined payments cover the summer months where net inflow runs close to the payment load. A shorter term would worsen the flagged ratio, and a smaller amount would leave the fit-out underfunded. The risk tier is medium, held there by the coverage shortfall, the seasonal pattern, the execution risk of a second site, and a five-year lease break inside a ten-year loan.
> 
> **Judgment calls logged with `loan decide`.** Six in total: risk tier, materiality of connected exposure, whether the APP-1001 referral precedent applies, whether the single seven-day late payment in August 2025 counts, counter versus full approval, and the final outcome.
> 
> **Paper trail.** The rationale is at `loan-demo/mossbank-climbing-app-1004.md`, submitted as RAT-APP-1004-01. The check passed on the first submission with no failures, and the decision was recorded citing 36 records and the one precedent. I also added a note to the project memory on what the check accepted this run, since it was more permissive on balances and the 24-month average than an earlier note claimed.

## run-05 (hero-again, APP-1001)

Prompt:

> You are the credit analyst at Lantern Mutual. Start by reading the team's page: run `loan sop`.
> The `loan` command is your only way to reach the bank's systems (`loan --help` lists it).
> Write the rationale to a file and submit it with `loan rationale submit`, check it with
> `loan check`, and record the decision with `loan record` (use `--revision freeform` and your
> own confidence between 0 and 1). Log every judgment call with `loan decide`. Finish with a
> short summary.
> 
> New application APP-1001: Harrow Street Bakery, $400,000 term loan for a second location.
> Assess it and record the decision.

1. `loan sop` → success: `{"name": "How we assess a business loan", "source": "memory", "text": "# How we assess a business loan\n\nOwner: Lantern Mutual credit team. This is the page new analysts get pointed at; it is how we\nexpect every business-loan application to be worked, from the first look to the filed decision.\n\n`
2. `loan application APP-1001` → success: `{"as_of": "2026-10-13", "application": {"key": "APP-1001", "product": "term loan", "amount": 400000, "term_months": 84, "rate": 0.085, "proposed_monthly_payment": 6334.59, "purpose": "Second location: fit-out and ovens for a second bakery on Lantern Row, with a wholesale kitchen at the back.", "subm`
3. `loan policy APP-1001` → success: `{"application": "APP-1001", "outcome": "review", "fired": [{"rule": "R5", "name": "connected_delinquency", "value": 90, "threshold": 60, "effect": "review", "cites": ["FAC-03", "PAY-03-2026-07", "PAY-03-2026-08", "PAY-03-2026-09"]}], "guidance": [{"rule": "G1", "name": "long_customer_decline", "valu`
4. `loan ownership BUS-01` → success: `{"business": "BUS-01", "owners": [{"person": {"key": "PER-01", "name": "Priya Raghunathan"}, "pct": 55, "since": "2016-03-01", "other_businesses": []}, {"person": {"key": "PER-02", "name": "Tom Alder"}, "pct": 45, "since": "2016-03-01", "other_businesses": [{"business": {"key": "BUS-05", "name": "Al`
5. `loan facilities BUS-01` → success: `{"business": "BUS-01", "as_of": "2026-10-13", "facilities": [{"key": "FAC-01", "product": "equipment loan", "principal": 120000, "rate": 0.0725, "term_months": 60, "monthly_payment": 2390.32, "opened": "2023-03-15", "status": "open", "late_days": 0, "missed_payment_keys": [], "payments": [{"key": "P`
6. `loan cashflow BUS-01` → success: `{"business": "BUS-01", "accounts": [{"key": "ACC-101", "type": "operating", "balance": 86400.0, "opened": "2020-09-14"}, {"key": "ACC-102", "type": "savings", "balance": 150000.0, "opened": "2021-02-01"}], "last_12m": {"months": 12, "avg_inflow": 113582.13, "avg_outflow": 99622.28, "avg_net": 13959.`
7. `loan kyc BUS-01` → success: `{"business": "BUS-01", "as_of": "2026-10-13", "kyc": {"key": "KYC-BUS-01", "status": "current", "last_review": "2026-03-14", "beneficial_owners_verified": true}, "fraud_events": [], "cites": ["KYC-BUS-01"]}`
8. `loan precedents APP-1001` → success: `{"application": "APP-1001", "product": "term loan", "policy_band": "review", "precedents": [{"key": "DEC-APP-1001-01", "application": "APP-1001", "business": "BUS-01", "outcome": "refer", "confidence": 0.7, "skill_revision": "freeform", "at": "2026-10-21T21:37:26+00:00", "rules": ["R5"], "rationale_`
9. `loan facilities BUS-05` → success: `{"business": "BUS-05", "as_of": "2026-10-13", "facilities": [{"key": "FAC-03", "product": "term loan", "principal": 300000, "rate": 0.08, "term_months": 60, "monthly_payment": 6082.92, "opened": "2024-02-15", "status": "open", "late_days": 90, "missed_payment_keys": ["PAY-03-2026-07", "PAY-03-2026-0`
10. **Judgment** `APP-1001: what is the risk tier of Harrow Street Bakery?` → **medium** (options: low,medium,high). Why: On its own the business is low risk: coverage 1.6 against a 1.25 floor, 24 months of on-time payments on FAC-01, KYC current, no fraud events, six years with us. It is medium rather than low because the 45% owner who will run the new site day to day (NOTE-01) holds 60% of Alder Logistics, whose 300,000 term loan FAC-03 is 90 days late with three consecutive missed payments and a late payment the month before. That stress sits one hop from the bakery's cash.
11. **Judgment** `APP-1001: is the connected exposure at Alder Logistics (FAC-03) material to this decision?` → **material** (options: material,not material). Why: FAC-03 is 300,000 of our 820,000 total exposure and the delinquency is deteriorating, not stale: late in June 2026 then missed July, August and September. The owner behind it is the one the relationship manager says will run the second bakery site. A 400,000 fit-out loan paid to a business where a co-owner has a failing facility with us is a direct path for our money to leak into servicing FAC-03. The policy also says a connected late facility is never an automatic approval.
12. **Judgment** `APP-1001: does the earlier decision on this same application (DEC-APP-1001-01, refer) apply as a precedent?` → **applies** (options: applies,does not apply,partially applies). Why: It is the same application, same business and same fired rule R5, filed earlier today on a freeform revision. Nothing in the systems has changed since: the as_of date on every record is still 2026-10-13. DEC-APP-1004-01 (approve at coverage 1.15) is in the same band but turned on coverage, not connected delinquency, so it does not pull this case toward approval.
13. **Judgment** `APP-1001: would a counter-offer (smaller amount or shorter term) be better than referring?` → **refer** (options: counter,refer,approve as asked). Why: A counter addresses affordability, and affordability is not the problem: coverage is 1.6 and a smaller loan would not change the connected delinquency. The question that decides this case is why Alder Logistics stopped paying and whether the bakery's cash or owners are exposed to it, and the systems do not hold that. A human can ask the relationship manager and the owners; I cannot. Approve as asked is ruled out by the policy's rule that a connected late facility is never an automatic approval.
14. **Judgment** `APP-1001: what is the outcome?` → **refer** (options: approve,counter,decline,refer). Why: Decline is not justified by the bakery's own record and would go to a human anyway under G1 (customer of six years). Approve is barred by the connected delinquency rule. Counter does not touch the real risk. Refer puts the case in front of someone who can establish the cause of the Alder Logistics arrears and whether to condition the loan on them, consistent with the earlier refer on this application.
15. `loan rationale submit --file /Users/zach/dev/graph-memory-system-one-demo/loan-demo/harrow-street-bakery-app-1001.md --application APP-1001 --outcome refer` → success: `{"rationale_id": "RAT-APP-1001-02", "application": "APP-1001", "outcome": "refer", "chars": 6150, "cites": ["APP-1001", "BUS-01", "BUS-05", "DEC-APP-1001-01", "DEC-APP-1004-01", "FAC-01", "FAC-03", "FAC-07", "KYC-BUS-01", "MON-101-2025-10", "MON-101-2025-11", "MON-101-2025-12", "MON-101-2026-01", "M`
16. `loan check RAT-APP-1001-02` → success: `{"rationale_id": "RAT-APP-1001-02", "application": "APP-1001", "outcome": "refer", "passed": true, "failures": [], "cites": ["APP-1001", "BUS-01", "BUS-05", "DEC-APP-1001-01", "DEC-APP-1004-01", "FAC-01", "FAC-03", "FAC-07", "KYC-BUS-01", "MON-101-2025-10", "MON-101-2025-11", "MON-101-2025-12", "MON`
17. `loan record RAT-APP-1001-02 --outcome refer --confidence 0.75 --revision freeform` → success: `{"decision_id": "DEC-APP-1001-02", "application": "APP-1001", "outcome": "refer", "confidence": 0.75, "skill_revision": "freeform", "policy_outcome": "review", "applied_policy": ["R5"], "cites": ["APP-1001", "BUS-01", "BUS-05", "FAC-01", "FAC-03", "FAC-07", "KYC-BUS-01", "MON-101-2025-10", "MON-101-`

Agent's closing summary:

> **APP-1001 is referred to a human.** The decision is filed as DEC-APP-1001-02 at confidence 0.75 on the freeform revision, after the rationale RAT-APP-1001-02 passed `loan check` on its first run.
> 
> **What the systems show.** Harrow Street Bakery clears every test on its own record. The policy check came back as review on one rule, R5 connected delinquency, with guidance G1 noting a decline on a six-year customer must go to a human.
> 
> | Test | Result |
> |---|---|
> | Coverage | 1.6 against a 1.25 floor |
> | Total exposure | 820,000, under the cap |
> | Own facilities | Equipment loan current, 24 of 24 on time |
> | KYC | Current, no fraud events |
> | Tenure | 6.0 years |
> | Connected delinquency | 90 days late at Alder Logistics |
> 
> **Why refer rather than approve, counter, or decline.** Tom Alder holds 45% of the bakery and 60% of Alder Logistics. That business's 300,000 term loan with us paid late in June and then missed July, August, and September outright. It was performing until then, so this is a live deterioration, not a stale blemish. The relationship manager's note says Tom Alder will run the new site day to day, which puts the stressed owner in charge of the asset we would be funding. Approval is barred by the rule that a connected late facility is never automatic. A counter would only address affordability, which is not the problem. Decline is not supported by the bakery's own record. The deciding question is why Alder Logistics stopped paying and whether the bakery is exposed to it, and the systems do not hold that answer.
> 
> **Judgment calls logged with `loan decide`,** one per call:
> - Risk tier: medium.
> - Connected exposure: material.
> - The earlier refer on this same application, DEC-APP-1001-01, applies as precedent. DEC-APP-1004-01 does not pull toward approval because it turned on coverage.
> - Counter versus refer: refer.
> - Outcome: refer.
> 
> **For the reviewer.** The rationale closes with three things to establish: the cause of the Alder Logistics arrears and whether a cure is under way, whether any personal guarantee or cross-default touches the bakery, and whether the loan could be approved conditional on the arrears being brought current before drawdown.
> 
> **Housekeeping.** The rationale file is at `loan-demo/harrow-street-bakery-app-1001.md`. The annual review note carries an owner's age, so I did not cite it. The submit command's help text still lists `review` as an outcome while the validator requires `refer`; I added that and the figures that passed this run to the existing gotchas memory.
