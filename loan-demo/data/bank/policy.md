# Lantern Mutual business lending policy (extract)

The rules below are the policy rows in the compliance system (`Rule` records R1 to R6 and G1), in
prose. Hard rules decide; guidance rules route to a person.

## Hard rules

**R1, KYC current.** The business's KYC status must be `current`. A status of `overdue` is an
automatic decline. A status of `refresh_due` sends the application to review.

**R2, no fraud event in twelve months.** A fraud event recorded against the business in the last
twelve months is an automatic decline.

**R3, coverage floor.** Debt service coverage is the twelve-month average monthly net inflow across
the business's accounts, divided by the proposed monthly payment plus the monthly payments on the
business's existing open facilities. A ratio of 1.25 or more may be approved without judgment.
A ratio from 1.00 up to 1.25 goes to review. A ratio under 1.00 is an automatic decline.

**R4, exposure cap.** Total exposure is the principal of every open facility at the business, plus
the principal of every open facility at any business an owner of the applicant holds 25% or more
of, plus the amount applied for. Total exposure must stay at or under $1,500,000. Over the cap goes
to review.

**R5, connected delinquency.** If any facility at a business an owner of the applicant holds 25% or
more of is 60 days or more late, the application goes to review. It is never an automatic approval.

**R6, tenure.** A business that has been a customer for fewer than 24 months goes to review.

**R7, connected exposure cap** (added 2026-10-13). Connected exposure is the principal of every open
facility at businesses an owner of the applicant holds 25% or more of. Connected exposure over
$250,000 always goes to a human; it is never decided by the procedure alone, whatever the other rules say.

## Guidance

**G1, long-standing customer decline.** A decline on a business that has been a customer for five
years or more goes to a human before it is filed.

## How the outcome is formed

If any hard rule produces an automatic decline, the outcome is `auto_decline`. Otherwise, if any
hard rule sends the application to review, the outcome is `review` and an assessment is needed.
Otherwise the outcome is `auto_approve`. Days late are counted from the due date of the oldest
unpaid payment to the assessment date. Tenure is counted from the customer-since date.

## What the assessment may see

The assessment is made from the figures and the rules that fired, the ownership summary (names of
businesses and percentages held), the tenure, the KYC status and the relationship manager's notes
about the business. Dates of birth and any personal characteristic of an owner are not inputs and
must not appear in a rationale.
