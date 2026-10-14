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
4. `loan cashflow BUS-01` → success: `{"business": "BUS-01", "accounts": [{"key": "ACC-101", "type": "operating", "balance": 86400.0, "opened": "2020-09-14"}, {"key": "ACC-102", "type": "savings", "balance": 150000.0, "opened": "2021-02-01"}], "last_12m": {"months": 12, "avg_inflow": 113582.13, "avg_outflow": 99622.28, "avg_net": 13959.`
5. `loan facilities BUS-01` → success: `{"business": "BUS-01", "as_of": "2026-10-13", "facilities": [{"key": "FAC-01", "product": "equipment loan", "principal": 120000, "rate": 0.0725, "term_months": 60, "monthly_payment": 2390.32, "opened": "2023-03-15", "status": "open", "late_days": 0, "missed_payment_keys": [], "payments": [{"key": "P`
6. `loan kyc BUS-01` → success: `{"business": "BUS-01", "as_of": "2026-10-13", "kyc": {"key": "KYC-BUS-01", "status": "current", "last_review": "2026-03-14", "beneficial_owners_verified": true}, "fraud_events": [], "cites": ["KYC-BUS-01"]}`
7. `loan ownership BUS-01` → success: `{"business": "BUS-01", "owners": [{"person": {"key": "PER-01", "name": "Priya Raghunathan"}, "pct": 55, "since": "2016-03-01", "other_businesses": []}, {"person": {"key": "PER-02", "name": "Tom Alder"}, "pct": 45, "since": "2016-03-01", "other_businesses": [{"business": {"key": "BUS-05", "name": "Al`
8. `loan precedents APP-1001` → success: `{"application": "APP-1001", "product": "term loan", "policy_band": "review", "precedents": [], "cites": []}`
9. **Judgment** `What risk tier is Harrow Street Bakery (BUS-01) for APP-1001?` → **medium** (options: low,medium,high). Why: Standalone the business is low risk: coverage 1.6x on avg net 13,959.86 against total payments 8,724.91, 24 of 24 payments current on FAC-01, prior term loan FAC-07 repaid, KYC current, 6 years tenure, stable cash flow (24m avg 13,538 vs 12m 13,960). It is raised to medium because a 45% owner holds 60% of Alder Logistics (BUS-05), whose 300k term loan FAC-03 has missed three consecutive payments (Jul-Sep 2026, 90 days late), and NOTE-01 says that owner will run the funded second site day to day.
10. **Judgment** `Is the connected exposure (Alder Logistics FAC-03, 300k, 90 days late) material to APP-1001?` → **material** (options: material,not material). Why: Three consecutive missed payments is a pattern, not a one-off, and 90 days is default territory. The connected owner will run the site this loan funds (NOTE-01), so his attention and any cash support to BUS-05 are a direct contagion channel. Total group exposure would be 820k with 300k of it already non-performing. The systems hold no explanation or cure plan for the arrears. Against this: BUS-05 is a different industry, the bakery's own cash flows show no strain to date, and the delinquent owner is the minority holder.
11. **Judgment** `Outcome for APP-1001: approve, counter, decline or refer?` → **refer (recommend approve in full once the Alder Logistics arrears are explained; counter if not)** (options: approve,counter,decline,refer). Why: Approve in full ignores an unexplained 90-day connected default the SOP says is never an automatic approval. Decline is not supported: coverage 1.6x, spotless own history, 6-year tenure, and G1 sends any decline to a human anyway. Counter does not address the risk, which is contagion rather than capacity; the bakery can carry the full payment. The deciding fact (why FAC-03 is 90 days late and whether BUS-05 is being cured or supported from bakery cash) is not in the systems, so per SOP I refer and say so, with a recommendation.
12. **Judgment** `Do any precedents apply to APP-1001?` → **none available** (options: apply,none available). Why: loan precedents returned no filed Decision nodes for a term loan in the review band, so the rationale leans on none and departs from none. This decision will be the first precedent in this band.
13. `loan rationale submit --file /Users/zach/dev/graph-memory-system-one-demo/loan-demo/.run/rationale-APP-1001.md --application APP-1001 --outcome refer` → success: `{"rationale_id": "RAT-APP-1001-01", "application": "APP-1001", "outcome": "refer", "chars": 6232, "cites": []}`
14. `loan check RAT-APP-1001-01` → success: `{"rationale_id": "RAT-APP-1001-01", "application": "APP-1001", "outcome": "refer", "passed": false, "failures": [{"check": "has_cites", "detail": "no [cite: KEY] markers; every figure and fact must cite the record it came from"}, {"check": "figure_in_evidence", "detail": "8.5% matches no percentage `
15. `loan rationale submit --file .run/rationale-APP-1001.md --application APP-1001 --outcome refer` → success: `{"rationale_id": "RAT-APP-1001-02", "application": "APP-1001", "outcome": "refer", "chars": 6240, "cites": ["ACC-101", "ACC-102", "APP-1001", "BUS-01", "BUS-05", "FAC-01", "FAC-03", "FAC-07", "KYC-BUS-01", "MON-101-2025-10", "MON-101-2025-11", "MON-101-2025-12", "MON-101-2026-01", "MON-101-2026-02",`
16. `loan check RAT-APP-1001-02` → success: `{"rationale_id": "RAT-APP-1001-02", "application": "APP-1001", "outcome": "refer", "passed": false, "failures": [{"check": "outcome_stated", "detail": "the first paragraph must state the outcome (refer)"}], "cites": ["ACC-101", "ACC-102", "APP-1001", "BUS-01", "BUS-05", "FAC-01", "FAC-03", "FAC-07",`
17. `loan rationale submit --file .run/rationale-APP-1001.md --application APP-1001 --outcome refer | head -5` → success: `"Outcome: refer. Referred to a human for decision, with a recommendation to approve the full amount once the arrears at a\n{\n  \"rationale_id\": \"RAT-APP-1001-03\",\n  \"application\": \"APP-1001\",\n  \"outcome\": \"refer\",\n  \"chars\": 6179,"`
18. `loan check RAT-APP-1001-03 | python3 -I -c import json,sys; d=json.load(sys.stdin); print(json.dumps({k:d[k] for k in ('rationale_id','outcome','passed','failures','policy_outcome','fired')}, indent=2))` → success: `{"rationale_id": "RAT-APP-1001-03", "outcome": "refer", "passed": true, "failures": [], "policy_outcome": "review", "fired": ["R5"]}`
19. `loan record RAT-APP-1001-03 --outcome refer --confidence 0.7 --revision freeform` → success: `{"decision_id": "DEC-APP-1001-01", "application": "APP-1001", "outcome": "refer", "confidence": 0.7, "skill_revision": "freeform", "policy_outcome": "review", "applied_policy": ["R5"], "cites": ["ACC-101", "ACC-102", "APP-1001", "BUS-01", "BUS-05", "FAC-01", "FAC-03", "FAC-07", "KYC-BUS-01", "MON-10`

Agent's closing summary:

> APP-1001 is assessed and filed. Decision recorded as DEC-APP-1001-01 with outcome **refer**, confidence 0.7, revision freeform.
> 
> **What the systems showed**
> 
> - **Policy outcome: review.** One rule fired, R5 connected delinquency. Tom Alder holds 45% of the bakery and 60% of Alder Logistics, whose $300,000 term loan with us has missed three consecutive payments and is 90 days late.
> - **The bakery itself is clean.** Coverage is 1.6 against a 1.25 floor. All 24 payments on its equipment loan were on time, a prior term loan was repaid, KYC is current, no fraud events, and it has banked with us for six years.
> - **No precedents** exist for a term loan in the review band. This decision is the first.
> 
> **The judgment**
> 
> I rated the business medium risk and the connected exposure material. The connected owner will run the funded second site day to day, so his other business's default is a direct contagion channel, and the systems hold no explanation of the arrears. Approving in full would treat that as immaterial. Declining is not supported by any figure in the file. A counter would not address the risk, which is contagion rather than capacity. Per the SOP, when unsure, refer. The rationale recommends approving the full amount if the relationship manager obtains a satisfactory account of the Alder Logistics arrears, with a counter as fallback.
> 
> **Process notes**
> 
> - Four judgment calls logged with `loan decide`: risk tier, materiality, outcome, precedents.
> - The rationale needed three submissions to pass the check. The fixes were square-bracket cite markers, removing the interest rate as an uncited figure, and opening the file with the outcome paragraph. The final version is RAT-APP-1001-03 and passed cleanly.
> - One CRM note records an owner's age. It was excluded from the rationale per the protected-characteristics rule.
> 
> The referred case now awaits a human reviewer.

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

1. `loan sop` → success: `{"name": "How we assess a business loan", "source": "memory", "text": "# How we assess a business loan\n\nOwner: Lantern Mutual credit team. This is the page new analysts get pointed at; it is how we\nexpect every business-loan application to be worked, from the first look to the filed decision.\n\n`
2. `loan application APP-1002` → success: `{"as_of": "2026-10-13", "application": {"key": "APP-1002", "product": "equipment loan", "amount": 250000, "term_months": 60, "rate": 0.079, "proposed_monthly_payment": 5057.14, "purpose": "Equipment: two digital imaging units and a sterilisation suite for the third chair.", "submitted": "2026-10-02"`
3. `loan policy APP-1002` → success: `{"application": "APP-1002", "outcome": "auto_approve", "fired": [], "guidance": [{"rule": "G1", "name": "long_customer_decline", "value": 7.6, "threshold": 5, "effect": "a decline goes to a human before filing", "cites": ["BUS-02"]}], "figures": {"coverage_ratio": 1.9, "avg_net_12m": 9608.57, "propo`
4. `loan ownership BUS-02` → success: `{"business": "BUS-02", "owners": [{"person": {"key": "PER-03", "name": "Anneliese Okafor"}, "pct": 50, "since": "2015-06-01", "other_businesses": []}, {"person": {"key": "PER-04", "name": "Marcus Tiller"}, "pct": 50, "since": "2015-06-01", "other_businesses": []}], "min_pct": 25.0, "cites": ["BUS-02`
5. `loan facilities BUS-02` → success: `{"business": "BUS-02", "as_of": "2026-10-13", "facilities": [], "existing_monthly_payments": 0, "cites": []}`
6. `loan cashflow BUS-02` → success: `{"business": "BUS-02", "accounts": [{"key": "ACC-201", "type": "operating", "balance": 212000.0, "opened": "2019-03-01"}, {"key": "ACC-202", "type": "savings", "balance": 310000.0, "opened": "2019-03-01"}], "last_12m": {"months": 12, "avg_inflow": 98925.73, "avg_outflow": 89317.17, "avg_net": 9608.5`
7. `loan kyc BUS-02` → success: `{"business": "BUS-02", "as_of": "2026-10-13", "kyc": {"key": "KYC-BUS-02", "status": "current", "last_review": "2026-05-20", "beneficial_owners_verified": true}, "fraud_events": [], "cites": ["KYC-BUS-02"]}`
8. `loan precedents APP-1002` → success: `{"application": "APP-1002", "product": "equipment loan", "policy_band": "auto_approve", "precedents": [], "cites": []}`
9. **Judgment** `APP-1002: what risk tier is Ridgeline Dental (BUS-02)?` → **low** (options: low,medium,high). Why: Coverage 1.90 against a 1.25 floor on operating cash flow alone, no existing facilities, no delinquency anywhere in the graph, KYC current (reviewed 2026-05-20), 7.6 years with us, and a 24-month net trend that is rising rather than flat. Nothing in the record points to medium.
10. **Judgment** `APP-1002: is connected exposure material to this decision?` → **none to assess** (options: material,not material,none to assess). Why: Two-hop ownership query shows both owners (PER-03, PER-04) hold no other businesses. Connected exposure and connected delinquency are both zero, so there is nothing to weigh. Exposure is the new 250,000 alone.
11. **Judgment** `APP-1002: do any precedents apply, and does the rationale need to explain a departure?` → **none exist** (options: apply and followed,apply and departed from,none exist). Why: loan precedents returned no prior Decision nodes for equipment loans in the auto_approve band. The rationale stands on the policy result alone and says so, and this decision becomes the first precedent in that band.
12. **Judgment** `APP-1002: accept the policy's auto_approve at the full 250,000 over 60 months, or counter or refer?` → **approve as asked** (options: approve as asked,counter at lower amount or shorter term,refer to a human). Why: No rule fired and G1 only applies to a decline. The purpose (imaging units and sterilisation suite for a third chair) matches the RM note NOTE-03 that the chair was added in July with a six-week waiting list, so this is growth capex with demand already visible in the operating account. A counter would have no rule or figure behind it. Confidence is high but not certain because no precedent exists in this band yet.
13. `loan rationale submit --file /Users/zach/dev/graph-memory-system-one-demo/loan-demo/rationale-APP-1002.md --application APP-1002 --outcome approve` → success: `{"rationale_id": "RAT-APP-1002-01", "application": "APP-1002", "outcome": "approve", "chars": 3631, "cites": ["ACC-201", "ACC-202", "APP-1002", "BUS-02", "KYC-BUS-02", "MON-201-2025-10", "MON-201-2025-11", "MON-201-2025-12", "MON-201-2026-01", "MON-201-2026-02", "MON-201-2026-03", "MON-201-2026-04",`
14. `loan check RAT-APP-1002-01` → success: `{"rationale_id": "RAT-APP-1002-01", "application": "APP-1002", "outcome": "approve", "passed": true, "failures": [], "cites": ["ACC-201", "ACC-202", "APP-1002", "BUS-02", "KYC-BUS-02", "MON-201-2025-10", "MON-201-2025-11", "MON-201-2025-12", "MON-201-2026-01", "MON-201-2026-02", "MON-201-2026-03", "`
15. `loan record RAT-APP-1002-01 --outcome approve --confidence 0.92 --revision freeform` → success: `{"decision_id": "DEC-APP-1002-01", "application": "APP-1002", "outcome": "approve", "confidence": 0.92, "skill_revision": "freeform", "policy_outcome": "auto_approve", "applied_policy": [], "cites": ["ACC-201", "ACC-202", "APP-1002", "BUS-02", "KYC-BUS-02", "MON-201-2025-10", "MON-201-2025-11", "MON`

Agent's closing summary:

> APP-1002 is approved and filed as decision DEC-APP-1002-01.
> 
> **Outcome.** Ridgeline Dental Partners LLP gets the full equipment loan as asked, over 60 months. The policy check returned auto-approve with no rules fired, so the outcome needed no judgment.
> 
> **Why it cleared.**
> 
> | Check | Result |
> |---|---|
> | Coverage ratio | 1.90 against a 1.25 floor |
> | Existing facilities | none |
> | Connected exposure and delinquency | none, both owners hold no other businesses |
> | KYC | current, last reviewed 2026-05-20, no fraud events |
> | Tenure | 7.6 years |
> | Precedents in this band | none |
> 
> The purpose matches the relationship manager's note that the practice added a third chair in July and carries a six-week waiting list. Guidance G1 for long-standing customers was noted but applies only to declines.
> 
> **What was filed.**
> - Four judgment calls logged with `loan decide`: risk tier low, no connected exposure to weigh, no precedents exist, and approve as asked rather than counter or refer.
> - Rationale written to rationale-APP-1002.md in the loan-demo directory and submitted as RAT-APP-1002-01.
> - The check passed on the first run with no failures.
> - Decision recorded with outcome approve, confidence 0.92, revision freeform.
> 
> Confidence is below certain only because no precedent yet exists for equipment loans in the auto-approve band. This decision now stands as the first one.

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
5. `loan facilities BUS-03` → success: `{"business": "BUS-03", "as_of": "2026-10-13", "facilities": [{"key": "FAC-06", "product": "term loan", "principal": 60000, "rate": 0.095, "term_months": 48, "monthly_payment": 1507.39, "opened": "2024-05-15", "status": "open", "late_days": 0, "missed_payment_keys": [], "payments": [{"key": "PAY-06-2`
6. `loan cashflow BUS-03` → success: `{"business": "BUS-03", "accounts": [{"key": "ACC-301", "type": "operating", "balance": 9800.0, "opened": "2023-05-01"}], "last_12m": {"months": 12, "avg_inflow": 102575.36, "avg_outflow": 94369.33, "avg_net": 8206.03, "from": "2025-10", "to": "2026-09"}, "last_24m": {"months": 24, "avg_inflow": 9830`
7. `loan ownership BUS-03` → success: `{"business": "BUS-03", "owners": [{"person": {"key": "PER-05", "name": "Declan Hurst"}, "pct": 100, "since": "2018-02-01", "other_businesses": []}], "min_pct": 25.0, "cites": ["BUS-03", "PER-05"]}`
8. `loan precedents APP-1003` → success: `{"application": "APP-1003", "product": "working capital line", "policy_band": "auto_decline", "precedents": [], "cites": []}`
9. **Judgment** `APP-1003: file the decline directly or refer to a human first?` → **file decline** (options: file decline,refer to human). Why: Two hard rules fired (R1 KYC overdue, R2 fraud event 4.1 months ago) and the policy outcome is auto_decline. Tenure is 41 months (3.4 years), under the five-year threshold that sends a decline to a human before filing. Nothing in the SOP leaves a judgment open.
10. **Judgment** `APP-1003: does the clean coverage (1.30) and the spotless payment record on FAC-06 change the outcome?` → **no - hard rules stand** (options: no - hard rules stand,argue for review on strength of cash flow). Why: Coverage of 1.30 clears the 1.25 floor and FAC-06 has 24 on-time payments, but the SOP says not to argue with a hard rule in the write-up. KYC and fraud rules are not cash-flow dependent. The strengths are noted in the rationale so the customer knows what a reapplication would rest on once KYC is current and the fraud event ages out.
11. **Judgment** `APP-1003: is a counter-offer (smaller amount or shorter term) preferable to a decline?` → **decline** (options: counter,decline). Why: The fired rules (KYC overdue, fraud event within twelve months) do not depend on amount or term, so no counter-offer would clear them. A counter would also signal that lending is possible while the operating account is under a fraud block and beneficial owners are unverified.
12. **Judgment** `APP-1003: how to treat CRM note NOTE-04, which mentions the director not responding to KYC refresh requests?` → **cite as KYC status of the business** (options: cite as KYC status of the business,omit,characterise the owner). Why: The note is a system record about the business's KYC refresh being requested twice without response and the fraud block on the operating account. It is cited for those facts only. The rationale describes the business, not the person, per SOP rule 4. No connected businesses exist (PER-05 holds nothing else at 25%+), so connected exposure is not material.
13. `loan rationale submit --file /Users/zach/dev/graph-memory-system-one-demo/loan-demo/rationales/APP-1003.md --application APP-1003 --outcome decline` → success: `{"rationale_id": "RAT-APP-1003-01", "application": "APP-1003", "outcome": "decline", "chars": 3626, "cites": ["APP-1003", "BUS-03", "FAC-06", "FRD-01", "KYC-BUS-03", "MON-301-2025-10", "MON-301-2025-11", "MON-301-2025-12", "MON-301-2026-01", "MON-301-2026-02", "MON-301-2026-03", "MON-301-2026-04", "`
14. `loan check RAT-APP-1003-01` → success: `{"rationale_id": "RAT-APP-1003-01", "application": "APP-1003", "outcome": "decline", "passed": true, "failures": [], "cites": ["APP-1003", "BUS-03", "FAC-06", "FRD-01", "KYC-BUS-03", "MON-301-2025-10", "MON-301-2025-11", "MON-301-2025-12", "MON-301-2026-01", "MON-301-2026-02", "MON-301-2026-03", "MO`
15. `loan record RAT-APP-1003-01 --outcome decline --confidence 0.95 --revision freeform` → success: `{"decision_id": "DEC-APP-1003-01", "application": "APP-1003", "outcome": "decline", "confidence": 0.95, "skill_revision": "freeform", "policy_outcome": "auto_decline", "applied_policy": ["R1", "R2"], "cites": ["APP-1003", "BUS-03", "FAC-06", "FRD-01", "KYC-BUS-03", "MON-301-2025-10", "MON-301-2025-1`

Agent's closing summary:

> APP-1003 is declined and filed as decision DEC-APP-1003-01.
> 
> **What the systems showed**
> 
> | Item | Finding |
> |---|---|
> | Policy outcome | auto_decline, rules R1 and R2 fired |
> | KYC | Overdue, last reviewed 2024-07-02, beneficial owners unverified |
> | Fraud | Counterfeit cheque deposits 2026-06-10, 4.1 months ago, operating account blocked |
> | Coverage | 1.30, above the 1.25 floor |
> | Existing facility | Term loan, 24 on-time payments, 0 days late |
> | Connected exposure | None, sole owner holds no other business |
> | Tenure | 3.4 years, so no mandatory human referral on a decline |
> | Precedents | None in this product and band |
> 
> **What I did**
> 
> - Ran the SOP, application, policy, KYC, facilities, cash flow, ownership, and precedent lookups.
> - Logged four judgment calls with `loan decide`: decline rather than refer, hard rules stand despite strong cash flow, no counter-offer since the fired rules do not depend on amount or term, and citing the CRM note only for the business's KYC and fraud facts.
> - Wrote the rationale to `rationales/APP-1003.md`, submitted it as RAT-APP-1003-01, and it passed `loan check` with no failures on the first run.
> - Recorded the decline with confidence 0.95 and revision freeform.
> 
> **For the customer** the rationale states that a future application can be considered once the KYC refresh is complete and the fraud event is outside the twelve-month window. On today's figures the business's cash flow would cover the proposed payments.

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
4. `loan precedents APP-1004` → success: `{"application": "APP-1004", "product": "term loan", "policy_band": "review", "precedents": [{"key": "DEC-APP-1001-01", "application": "APP-1001", "business": "BUS-01", "outcome": "refer", "confidence": 0.7, "skill_revision": "freeform", "at": "2026-10-13T22:20:15+00:00", "rules": ["R5"], "rationale_`
5. `loan ownership BUS-04` → success: `{"business": "BUS-04", "owners": [{"person": {"key": "PER-06", "name": "Ingrid Vossberg"}, "pct": 70, "since": "2018-09-01", "other_businesses": []}, {"person": {"key": "PER-07", "name": "Ben Achterberg"}, "pct": 30, "since": "2020-01-01", "other_businesses": []}], "min_pct": 25.0, "cites": ["BUS-04`
6. `loan facilities BUS-04` → success: `{"business": "BUS-04", "as_of": "2026-10-13", "facilities": [{"key": "FAC-02", "product": "term loan", "principal": 200000, "rate": 0.075, "term_months": 84, "monthly_payment": 3067.66, "opened": "2022-06-15", "status": "open", "late_days": 0, "missed_payment_keys": [], "payments": [{"key": "PAY-02-`
7. `loan cashflow BUS-04` → success: `{"business": "BUS-04", "accounts": [{"key": "ACC-401", "type": "operating", "balance": 142000.0, "opened": "2019-05-20"}, {"key": "ACC-402", "type": "savings", "balance": 95000.0, "opened": "2020-01-15"}], "last_12m": {"months": 12, "avg_inflow": 59464.1, "avg_outflow": 47381.28, "avg_net": 12082.82`
8. `loan kyc BUS-04` → success: `{"business": "BUS-04", "as_of": "2026-10-13", "kyc": {"key": "KYC-BUS-04", "status": "current", "last_review": "2026-01-22", "beneficial_owners_verified": true}, "fraud_events": [], "cites": ["KYC-BUS-04"]}`
9. **Judgment** `APP-1004: what risk tier is Mossbank Climbing (BUS-04)?` → **medium** (options: low,medium,high). Why: Coverage of 1.15 sits inside the judgment band below the 1.25 floor and the loan funds a second site, which carries execution risk. Against that: seven years with us, KYC current, no fraud, a single seven-day late payment in August 2025 explained by a card terminal swap, cash balances across the operating and savings accounts that cover many months of combined payments, and a twelve-month net inflow average above the twenty-four-month average. Not low because of the coverage shortfall and the expansion; not high because every other signal is clean.
10. **Judgment** `APP-1004: is connected exposure material to this decision?` → **no** (options: yes,no). Why: The ownership query two hops out returns no other business for either owner (PER-06 at 70 percent, PER-07 at 30 percent). Connected exposure is zero and connected worst late days is zero. Total exposure of 800000 is the business's own existing term loan FAC-02 plus the new amount, and the exposure cap rule did not fire.
11. **Judgment** `APP-1004: does the precedent DEC-APP-1001-01 (refer) apply here?` → **depart and decide** (options: apply and refer,depart and decide). Why: DEC-APP-1001-01 was referred because of arrears at a connected business (rule R5). APP-1004 has no connected businesses at all; the only fired rule is R3 coverage. The precedent's reason for referral is absent, so it does not bind the outcome here. The rationale says so explicitly.
12. **Judgment** `APP-1004: does the one late payment on FAC-02 (PAY-02-2025-08, paid seven days after due) count against the applicant?` → **treat as isolated operational event** (options: treat as delinquency signal,treat as isolated operational event). Why: A single payment paid on 2025-08-22 against a 2025-08-15 due date, in a 24-month history that is otherwise paid on the due date every month. RM note NOTE-06 attributes it to a card terminal replacement and records nothing since. Thirteen consecutive on-time payments follow it. It is well under the sixty-day threshold and does not change the risk tier.
13. **Judgment** `APP-1004: does the five-year break in the ten-year Mossbank Mill lease (NOTE-05) undermine a 120-month term?` → **note for the relationship manager but not decisive** (options: decisive against the term,note for the relationship manager but not decisive,ignore). Why: The loan runs 120 months and the lease has a break at five years. A break clause is normally the tenant's option and the fit-out only has value in situ, so the borrower has every incentive to stay. It is worth the RM confirming who holds the break, but it does not change the credit outcome on its own.
14. **Judgment** `APP-1004: outcome given policy says review on coverage 1.15?` → **approve** (options: approve,counter,decline,refer). Why: Coverage of 1.15 is above 1.00 and in the judgment band. The ratio is computed on current cash flow only and gives no credit to the second gym, which is the purpose of the loan and already has 412 founder memberships pre-sold against a 600 target (NOTE-05), with the original gym at capacity on weekday evenings. Liquidity in the operating and savings accounts is strong, the payment record on FAC-02 is clean apart from one explained seven-day late payment, KYC is current with no fraud events, tenure is 7.3 years, and there is no connected exposure. The existing loan FAC-02 matures in 2029, after which only the new payment remains. A counter at a smaller amount would push coverage to the floor but risk leaving the fit-out underfunded; a decline is not supported by any figure and would in any case go to a human under G1. Confident enough not to refer.
15. `loan rationale submit --file /Users/zach/dev/graph-memory-system-one-demo/loan-demo/rationale-APP-1004.md --application APP-1004 --outcome approve` → success: `{"rationale_id": "RAT-APP-1004-01", "application": "APP-1004", "outcome": "approve", "chars": 5963, "cites": ["APP-1004", "BUS-04", "DEC-APP-1001-01", "FAC-02", "KYC-BUS-04", "MON-401-2025-10", "MON-401-2025-11", "MON-401-2025-12", "MON-401-2026-01", "MON-401-2026-02", "MON-401-2026-03", "MON-401-20`
16. `loan check RAT-APP-1004-01` → success: `{"rationale_id": "RAT-APP-1004-01", "application": "APP-1004", "outcome": "approve", "passed": true, "failures": [], "cites": ["APP-1004", "BUS-04", "DEC-APP-1001-01", "FAC-02", "KYC-BUS-04", "MON-401-2025-10", "MON-401-2025-11", "MON-401-2025-12", "MON-401-2026-01", "MON-401-2026-02", "MON-401-2026`
17. `loan check RAT-APP-1004-01` → success: `{"rationale_id": "RAT-APP-1004-01", "application": "APP-1004", "outcome": "approve", "passed": true, "failures": [], "cites": ["APP-1004", "BUS-04", "DEC-APP-1001-01", "FAC-02", "KYC-BUS-04", "MON-401-2025-10", "MON-401-2025-11", "MON-401-2025-12", "MON-401-2026-01", "MON-401-2026-02", "MON-401-2026`
18. `loan record RAT-APP-1004-01 --outcome approve --confidence 0.75 --revision freeform` → success: `{"decision_id": "DEC-APP-1004-01", "application": "APP-1004", "outcome": "approve", "confidence": 0.75, "skill_revision": "freeform", "policy_outcome": "review", "applied_policy": ["R3"], "cites": ["APP-1004", "BUS-04", "FAC-02", "KYC-BUS-04", "MON-401-2025-10", "MON-401-2025-11", "MON-401-2025-12",`

Agent's closing summary:

> APP-1004 is assessed and filed. Decision: approve the full $600,000 over 120 months, recorded as DEC-APP-1004-01 with confidence 0.75.
> 
> **What the systems showed**
> 
> | Check | Result |
> |---|---|
> | Coverage (R3) | 1.15, below the 1.25 floor, so policy said review |
> | Exposure | 800,000 total, all the business's own, cap not fired |
> | Connected delinquency | None. Neither owner holds another business |
> | KYC and fraud | Current, reviewed 2026-01-22, no fraud events |
> | Tenure | 7.3 years |
> 
> **Why approve rather than counter or refer**
> 
> - Coverage is in the judgment band, not below 1.00. It is computed on the existing gym alone and gives no credit to the second site the loan funds.
> - The relationship manager recorded 412 founder memberships pre-sold against a 600 target, and the original gym at capacity on weekday evenings.
> - The existing term loan has 24 payments on file, 23 on the due date. The one late payment in August 2025 was seven days and attributed to a card terminal swap.
> - The twelve-month net inflow average is above the twenty-four-month average, so the business is growing.
> - The existing loan matures during the life of the new one, after which only the new payment remains.
> - A counter would lift coverage to the floor but leave a fixed-scope fit-out underfunded. A decline is not supported by any figure.
> 
> **Judgment calls logged** with `loan decide`: risk tier (medium), connected exposure (not material), whether the refer precedent DEC-APP-1001-01 applies (no, its reason was connected arrears, absent here), the August 2025 late payment (isolated), the five-year lease break against a ten-year term (note for the RM, not decisive), and the outcome itself.
> 
> **Process**: the rationale is at `loan-demo/rationale-APP-1004.md`, submitted as RAT-APP-1004-01. It passed `loan check` on the first and second run with no failures, then was recorded with revision freeform.
> 
> **One open item for the relationship manager**: confirm who holds the five-year break in the Mossbank Mill lease. This is flagged in the rationale and does not change the decision.

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

1. `loan sop; echo -----; loan --help` → success: `"with those businesses' facilities and payment status   \u2502\n\u2502              (two hops in the graph).                                        \u2502\n\u2502 facilities   A business's facilities and their payments, with days late per  \u2502\n\u2502              facility.                       `
2. `loan application APP-1001` → success: `{"as_of": "2026-10-13", "application": {"key": "APP-1001", "product": "term loan", "amount": 400000, "term_months": 84, "rate": 0.085, "proposed_monthly_payment": 6334.59, "purpose": "Second location: fit-out and ovens for a second bakery on Lantern Row, with a wholesale kitchen at the back.", "subm`
3. `loan policy APP-1001` → success: `{"application": "APP-1001", "outcome": "review", "fired": [{"rule": "R5", "name": "connected_delinquency", "value": 90, "threshold": 60, "effect": "review", "cites": ["FAC-03", "PAY-03-2026-07", "PAY-03-2026-08", "PAY-03-2026-09"]}], "guidance": [{"rule": "G1", "name": "long_customer_decline", "valu`
4. `loan ownership BUS-01` → success: `{"business": "BUS-01", "owners": [{"person": {"key": "PER-01", "name": "Priya Raghunathan"}, "pct": 55, "since": "2016-03-01", "other_businesses": []}, {"person": {"key": "PER-02", "name": "Tom Alder"}, "pct": 45, "since": "2016-03-01", "other_businesses": [{"business": {"key": "BUS-05", "name": "Al`
5. `loan facilities BUS-01` → success: `{"business": "BUS-01", "as_of": "2026-10-13", "facilities": [{"key": "FAC-01", "product": "equipment loan", "principal": 120000, "rate": 0.0725, "term_months": 60, "monthly_payment": 2390.32, "opened": "2023-03-15", "status": "open", "late_days": 0, "missed_payment_keys": [], "payments": [{"key": "P`
6. `loan cashflow BUS-01` → success: `{"business": "BUS-01", "accounts": [{"key": "ACC-101", "type": "operating", "balance": 86400.0, "opened": "2020-09-14"}, {"key": "ACC-102", "type": "savings", "balance": 150000.0, "opened": "2021-02-01"}], "last_12m": {"months": 12, "avg_inflow": 113582.13, "avg_outflow": 99622.28, "avg_net": 13959.`
7. `loan kyc BUS-01` → success: `{"business": "BUS-01", "as_of": "2026-10-13", "kyc": {"key": "KYC-BUS-01", "status": "current", "last_review": "2026-03-14", "beneficial_owners_verified": true}, "fraud_events": [], "cites": ["KYC-BUS-01"]}`
8. `loan precedents APP-1001` → success: `{"application": "APP-1001", "product": "term loan", "policy_band": "review", "precedents": [{"key": "DEC-APP-1001-01", "application": "APP-1001", "business": "BUS-01", "outcome": "refer", "confidence": 0.7, "skill_revision": "freeform", "at": "2026-10-13T22:20:15+00:00", "rules": ["R5"], "rationale_`
9. `loan rationale submit --file .run/rationale-APP-1001.md --application APP-1001 --outcome refer` → success: `{"rationale_id": "RAT-APP-1001-04", "application": "APP-1001", "outcome": "refer", "chars": 4647, "cites": ["APP-1001", "BUS-01", "BUS-05", "DEC-APP-1001-01", "DEC-APP-1004-01", "FAC-01", "FAC-03", "FAC-07", "KYC-BUS-01", "MON-101-2025-10", "MON-101-2025-11", "MON-101-2025-12", "MON-101-2026-01", "M`
10. **Judgment** `What risk tier is Harrow Street Bakery (BUS-01) for APP-1001?` → **medium** (options: low,medium,high). Why: On its own numbers it is low: coverage 1.6, KYC current, no fraud, six years tenure, FAC-01 fully current and FAC-07 repaid. Lifted one tier because the 45% owner's other business (Alder Logistics, 60% held) is 90 days late on a 300000 term loan FAC-03 with three consecutive missed payments, and that owner will run the new site day to day (NOTE-01).
11. **Judgment** `Is the connected exposure at Alder Logistics (FAC-03) material to APP-1001?` → **material** (options: material,not material). Why: The arrears are recent and worsening (Jul-Sep 2026 missed, 90 days late), the 300000 connected facility exceeds everything the bakery owes us (120000), and the owner under that pressure is the one carrying the new project. The bakery is not liable for FAC-03, but contagion risk (owner drawing on bakery cash to prop up the logistics business) is real and no record in the systems explains the arrears.
12. **Judgment** `Outcome for APP-1001 given the R5 review: approve, counter, decline, or refer?` → **refer** (options: approve,counter,decline,refer). Why: Approve: SOP says a late connected facility is never an automatic approval and the arrears are unexplained in the systems. Counter: a smaller amount does not address the risk, which is the connected business's state, not the bakery's capacity (coverage 1.6). Decline: not supported by a six-year clean record and strong coverage, and G1 routes a decline to a human anyway. Refer with a recommendation to approve the full amount once the FAC-03 arrears are explained and either cured or on a plan, with a condition that the bakery does not guarantee or fund Alder Logistics. Confidence about 0.7.
13. **Judgment** `Do the precedents DEC-APP-1001-01 and DEC-APP-1004-01 apply to APP-1001?` → **follow DEC-APP-1001-01** (options: follow DEC-APP-1001-01,follow DEC-APP-1004-01 and approve,neither applies). Why: DEC-APP-1001-01 is a prior decision on this same application that referred with a recommendation to approve once the arrears were explained; nothing in the systems has changed since, so I reach the same view. DEC-APP-1004-01 approved on a single fired rule, but that rule was the coverage floor (R3), a question about the applicant's own capacity that figures can settle. A connected delinquency (R5) is about a different business and the figures cannot settle it, so that precedent does not transfer.
14. `loan check RAT-APP-1001-04` → success: `{"rationale_id": "RAT-APP-1001-04", "application": "APP-1001", "outcome": "refer", "passed": true, "failures": [], "cites": ["APP-1001", "BUS-01", "BUS-05", "DEC-APP-1001-01", "DEC-APP-1004-01", "FAC-01", "FAC-03", "FAC-07", "KYC-BUS-01", "MON-101-2025-10", "MON-101-2025-11", "MON-101-2025-12", "MON`
15. `loan record RAT-APP-1001-04 --outcome refer --confidence 0.7 --revision freeform` → success: `{"decision_id": "DEC-APP-1001-02", "application": "APP-1001", "outcome": "refer", "confidence": 0.7, "skill_revision": "freeform", "policy_outcome": "review", "applied_policy": ["R5"], "cites": ["APP-1001", "BUS-01", "BUS-05", "FAC-01", "FAC-03", "FAC-07", "KYC-BUS-01", "MON-101-2025-10", "MON-101-2`

Agent's closing summary:

> **APP-1001 is recorded as refer with confidence 0.7, decision DEC-APP-1001-02.** The rationale passed the check on the first submission.
> 
> **What the systems show.** Harrow Street Bakery is clean on its own. Coverage is 1.6 against the 1.25 floor, KYC is current with no fraud events, tenure is six years, the open equipment loan has never been late, and an earlier term loan was repaid in full. Exposure including the new amount stays under the cap.
> 
> **Why it is not an approval.** The policy fired one rule, connected delinquency. Tom Alder, who holds 45 percent of the bakery, holds 60 percent of Alder Logistics. That business has a term loan with us that is 90 days late with three consecutive missed payments, and the relationship manager's note says Tom will run the new site day to day. Nothing in the systems explains the arrears, so I referred rather than assumed an explanation.
> 
> **Recommendation in the file.** Approve the full amount once the arrears are explained and either cured or on a repayment plan, with a condition that the bakery does not guarantee or fund the logistics business. A counter would not address the risk, and a decline is unsupported by the bakery's record.
> 
> **Judgment calls logged** with `loan decide`:
> - Risk tier: medium, low on its own numbers, lifted by the connected arrears.
> - Connected exposure: material, because the arrears are recent and worsening and the owner under pressure carries the new project.
> - Outcome: refer over approve, counter, or decline.
> - Precedents: followed the earlier refer on this same application; the climbing-gym approval does not transfer because its fired rule was the coverage floor, not a connected delinquency.
> 
> **One thing to flag.** The annual-review CRM note records an owner's age. I excluded it from the rationale and cited only the site-visit note. The check also confirmed no protected characteristics in the file.
> 
> Files: rationale at `.run/rationale-APP-1001.md`, submitted as RAT-APP-1001-04.
