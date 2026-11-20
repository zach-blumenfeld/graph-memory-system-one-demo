# How we assess a small-business term loan

Owner: Lantern Mutual credit team. One application comes in as one written form. One assessment
ends in exactly one of four ways: returned, declined, approved, or escalated to a credit officer.
The rules and every number are in `policy.md`; this page is the order of work.

## 1. Check the form

Read the fields in sections 1 to 3 and the documents listed in section 4. Check completeness
first, then every hard rule, H1 to H7. Check all of them even after one fails, because a decline
must name every rule that failed. These checks are arithmetic and lookups. Nobody uses judgment
here.

## 2. Act on what the form says

- **Incomplete:** return the application to the applicant with the list of what is missing.
  Stop.
- **Fails a hard rule:** decline. Record each failed rule with its figure and its threshold.
  Stop.
- **Complete and passes every hard rule:** go on to the judgment rules.

## 3. Judge each judgment rule

Take the judgment rules from the policy one at a time, J1 to J5. For each one, read the whole
application and answer a single question: does this rule hold for this application? Answer
yes or no and say how sure you are. Judge each rule separately; the answer to one rule is not
a reason for the answer to another.

## 4. Combine the answers

- **Every rule holds, each with a probability above 0.75:** approve.
- **Anything else:** escalate. That is any rule that does not hold, and any rule the reader is
  not sure of.

## 5. The four endings

- **Return:** the application goes back to the applicant with what is missing.
- **Decline:** the decision is filed with the failed hard rules.
- **Approve:** the decision is filed with the amount, the term and the quoted payment.
- **Escalate:** the application is placed in the credit officer queue with the judgment rules
  that did not hold and the answer given for each. The assessment ends there. The credit officer
  decides later, outside this procedure.

## 6. What every assessment returns

Every ending returns the same six fields, so any two assessments can be compared line by line:

| Field | What it holds |
|---|---|
| `application_id` | The id on the form, such as `APP-2001` |
| `outcome` | One of `return`, `decline`, `approve`, `escalate` |
| `failed_rules` | The ids of the rules that decided it, in order: the failed hard rules for a decline (`["H3", "H4"]`), the judgment rules that did not hold for an escalation (`["J1"]`), and an empty list for an approval or a return |
| `missing` | For a return, the names of the empty fields and absent documents exactly as the form and the policy write them; otherwise an empty list |
| `customer_message` | A short message to the applicant |
| `officer_message` | A short note to the credit officer |

## 7. The two messages

Both are written after the outcome is settled, from the outcome and its reasons. Neither changes
the outcome. Both are plain language, under 150 words, with the outcome in the first sentence.

**To the customer.** Say what was decided and why, in words someone who has never read the
policy would follow. Do not use rule ids.

- Return: list what is missing and say the application will be assessed once it arrives.
- Decline: give each reason with the applicant's own figure and the figure required ("your
  business has operated for 17 months; we require 24").
- Approve: state the amount, the term and the monthly payment.
- Escalate: say a credit officer will review the application, and name in one sentence each
  thing they will look at. Do not say or suggest what the officer will decide.

**To the credit officer.** Say the outcome, then each reason with its rule id, the figure or
the passage from the application it rests on, and for a judgment rule how sure the reader was.
For an escalation, end with the question the officer needs to settle. For the other three
outcomes it is the note that goes on file.
