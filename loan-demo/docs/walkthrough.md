# The procedure, top to bottom

One loan application in, one filed decision (or a note for a person) out. Thirteen nodes. Scripts are
Python, no model. The judgment is a decision model with a probability. The agent writes the letter.

| # | node | who | what happens |
|---|---|---|---|
| 1 | gather | script | Pull everything the bank holds on the applicant, plus every other business its owners hold a quarter or more of and whether those are paying. Strip names and dates of birth. |
| 2 | hard-rules | script | Apply the seven policy rules (below). Result: `auto_approve`, `auto_decline` or `review`, with the rules that fired. |
| 3 | by-rules | branch | Automatic result: skip to 5. `review`: go to 4. |
| 4 | assess | model | Three typed questions (below). Each answer has a probability. Under the threshold: pause, ask a person. |
| 5 | precedents | script | Look up earlier filed decisions on the same loan product in the same policy band, and settle what will be filed (below). |
| 6 | by-confidence | branch | `needs_human`: go to 13, unfiled. Else: go to 7. |
| 7 | rationale | agent | Write the decision letter. First words "Outcome: …". Every number cites a record. No person named. |
| 8 | check | script | Lint it: every cite exists, every number matches a record, outcome up front, no protected words. |
| 9 | gate | branch | Passed: 12. First failure: 10. Second failure: 13, unfiled. |
| 10 | fix | agent | Fix exactly what the check named. Once. |
| 11 | recheck | script | Lint again. Back to 9. |
| 12 | record | script | File the decision with its outcome, confidence, revision, cited records and applied rules. |
| 13 | end | | Returns five fields (below). |

Two places a person enters: a low-probability answer at 4, or the flag at 6.

**2, the policy.** R1 customer record (KYC) current, else decline. R2 no fraud event in 12 months, else
decline. R3 cash flow covers all loan payments 1.25× or better; 1.00 to 1.25 is review; under 1.00 is
decline. R4 total lending to the business and its owners' other businesses under $1.5M, else review.
R5 any loan 60+ days late at a business an owner holds 25% or more of: review, never auto-approve.
R6 under two years with the bank: review. G1 a decline on a customer of five years or more goes to a
person before filing.

**4, the three questions.**

1. `risk_tier`, TypeSafe `choice` of low / medium / high, threshold 0.6. How risky is this business:
   its own cash cover, payment record and balances, lifted for anything around it (an owner's other
   business in arrears, an expansion the numbers give no credit to).
2. `connected_exposure_material`, TypeSafe `noul` (yes/no with a probability), threshold 0.3. Does
   trouble at an owner's other business change this decision, or is it noise.
3. `outcome`, TypeSafe `choice` of approve / counter / decline, threshold 0.6. The lending decision
   itself: full amount, a smaller amount or shorter term, or no.

**5, what it settles.** (a) Outcome: if the policy said auto_approve the outcome is approve, if
auto_decline it is decline, if review it is whatever the model answered at 4. (b) Confidence: 1.0 when
the rules decided, 0.6 (the threshold the model cleared) when the model did. (c) `needs_human`: true
when the outcome is decline and the customer has five or more years with the bank (G1). (d) The
evidence digest: every figure with the id of the record it came from, which is the only material the
letter at 7 may quote.

**13, what comes back.** `application_id`; `outcome` (approve / counter / decline);
`needs_human` (true / false); `decision_id`, the key of the Decision node written into the memory
graph at 12, e.g. `DEC-APP-1005-02`, empty if nothing was filed; and `note`, one paragraph saying
what was filed or what a person must do next. The decision node is what the next run's step 5 finds
as a precedent.

Revision 2: one change at 5(c). A fired R7 rule (group lending over $250K) also sets `needs_human`.
