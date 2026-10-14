# The procedure, top to bottom

One loan application in, one filed decision (or a note for a person) out. Scripts are Python, no
model. Node 4 is a decision model with a probability per answer. The agent writes the letter.

| # | node | who | what happens |
|---|---|---|---|
| 1 | gather | script | Pull everything the bank holds on the applicant, plus every other business any of its owners holds 25%+ of (all owners, all their businesses) and whether each is paying. Strip names and dates of birth. |
| 2 | hard-rules | script | Apply the policy:<br>R1 customer record (KYC) current, else decline<br>R2 no fraud event in 12 months, else decline<br>R3 cash flow covers all loan payments 1.25× or better; 1.00–1.25 review; under 1.00 decline<br>R4 total lending to the business and its owners' other businesses under $1.5M, else review<br>R5 any loan 60+ days late at any business any owner holds 25%+ of: review, never auto-approve<br>R6 under two years with the bank: review<br>G1 a decline on a customer of 5+ years goes to a person before filing<br>Result: `auto_approve`, `auto_decline` or `review`, plus the rules that fired. |
| 3 | by-rules | branch | `auto_approve` or `auto_decline`: skip to 5. `review`: go to 4. |
| 4 | assess | model | Three questions, each answered with a probability:<br>1. `risk_tier`: choice of low / medium / high, threshold 0.6. How risky is the business: its own cash cover, payment record, balances, lifted for any owner's other businesses in arrears or an expansion the numbers give no credit to.<br>2. `connected_exposure_material`: noul (yes/no), threshold 0.3. Does trouble at any of the owners' other businesses, taken together, change this decision.<br>3. `outcome`: choice of approve / counter / decline, threshold 0.6. The lending decision: full amount, smaller or shorter, or no.<br>Any answer under its threshold: pause, a person answers it. |
| 5 | precedents | script | Look up earlier filed decisions on the same loan product in the same policy band. Then settle:<br>outcome = approve if `auto_approve`, decline if `auto_decline`, the model's answer if `review`<br>confidence = 1.0 if the rules decided, 0.6 if the model did<br>`needs_human` = true if outcome is decline and the customer has 5+ years (G1)<br>evidence digest = every figure with the id of the record it came from, the only material the letter may quote |
| 6 | by-confidence | branch | `needs_human` true: go to 13, unfiled. Else: go to 7. |
| 7 | rationale | agent | Write the decision letter. First words "Outcome: …". Every number cites a record. No person named. |
| 8 | check | script | Lint it: every cite exists, every number matches a record, outcome up front, no protected words. |
| 9 | gate | branch | Passed: 12. First failure: 10. Second failure: 13, unfiled. |
| 10 | fix | agent | Fix exactly what the check named. Once. |
| 11 | recheck | script | Lint again. Back to 9. |
| 12 | record | script | Write a Decision node into the memory graph with outcome, confidence, revision, edges to every cited record and applied rule. |
| 13 | end | | Returns: `application_id`; `outcome` (approve / counter / decline); `needs_human` (true/false); `decision_id`, the key of the Decision node from 12, e.g. `DEC-APP-1005-02`, empty if unfiled; `note`, one paragraph: what was filed, or what a person must do. |

Two places a person enters: a low-probability answer at 4, or the flag at 6.

Revision 2: one change at 5. A fired R7 rule (lending to the owners' group over $250K) also sets `needs_human`.
