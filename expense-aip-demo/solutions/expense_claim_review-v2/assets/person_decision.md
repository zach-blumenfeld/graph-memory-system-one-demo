A person must decide this expense claim. Take the findings below to them and answer with what they decided.

Claim {claim_id}: amount {amount}, category {category}, submitted {date}, claimant {claimant}, approver {approver}.

Receipt findings:
- Vendor: {vendor}
- Receipt date: {receipt_date}
- Receipt total: {receipt_total} (-1 means not found)
- Does the receipt support the claim, and why: {receipt_why}

Policy rules, in order:
{rules}

Verdicts for those rules, in the same order. Each has follows (true or false) and a confidence. A rule failed if follows is false. It is doubtful if the confidence is below 0.8:
{verdicts}

Exact computed facts:
{facts}

First write the findings for the person: vendor, date, total, which checks failed or were doubtful and why. Then ask the person to set the status to approved or declined and to give a one-line reason.

Answer with exactly the keys status and reason. status must be exactly the word approved or the word declined. reason must be the person's one-line reason, in their words.
