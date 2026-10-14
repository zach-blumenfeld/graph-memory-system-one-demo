# The procedure, top to bottom

One loan application in, one filed decision (or a note for a person) out. Thirteen nodes. Scripts are
Python, no model. The judgment is a decision model with a probability. The agent writes the letter.

| # | node | who | what happens |
|---|---|---|---|
| 1 | gather | script | Pull everything the bank holds on the applicant, plus every other business its owners hold a quarter or more of and whether those are paying. Strip names and dates of birth. |
| 2 | hard-rules | script | Apply the policy. Result: `auto_approve`, `auto_decline` or `review`, with the rules that fired. |
| 3 | by-rules | branch | Automatic result: skip to 5. `review`: go to 4. |
| 4 | assess | model | Three questions: risk tier (low / medium / high), is the owner's other business a problem (yes / no), approve / counter / decline. Each answer has a probability. Under the threshold: pause, ask a person. |
| 5 | precedents | script | Find earlier decisions on the same kind of loan. Fix the outcome and confidence (1.0 if the rules decided, 0.6 if the model did). Flag `needs_human` if this is a decline on a customer of five years or more. |
| 6 | by-confidence | branch | `needs_human`: go to 13, unfiled. Else: go to 7. |
| 7 | rationale | agent | Write the decision letter. First words "Outcome: …". Every number cites a record. No person named. |
| 8 | check | script | Lint it: every cite exists, every number matches a record, outcome up front, no protected words. |
| 9 | gate | branch | Passed: 12. First failure: 10. Second failure: 13, unfiled. |
| 10 | fix | agent | Fix exactly what the check named. Once. |
| 11 | recheck | script | Lint again. Back to 9. |
| 12 | record | script | File the decision with its outcome, confidence, revision, cited records and applied rules. |
| 13 | end | | Decision id, or a note saying what a person must do. |

Two places a person enters: a low-probability answer at 4, or the flag at 6.

Revision 2: one change at 5. A fired R7 rule (group lending over $250K) also sets `needs_human`.
