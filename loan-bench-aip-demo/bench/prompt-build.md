Build an AIP procedure named `assess_term_loan` that assesses one small-business term loan
application for Lantern Mutual. Write it to `./built/assess_term_loan`.

## What you have

- `source/sop.md`: the order of work and the six fields every assessment returns.
- `source/policy.md`: the rules and every number.
- `examples/`: two applications in the form every application arrives in. They are there to
  show the form and to try the procedure on. The procedure will be run on applications you have
  not seen, so nothing in it may depend on these two.
- `/opt/aip/skill/SKILL.md` and `/opt/aip/skill/references/language.md`: how to write, compile
  and run a procedure with the `aip` command. Read both before writing anything.
- The `aip` command, with a decision model configured, so `Decide` steps run.

## What the procedure must be

Its one input is `application_file`, a string: the path of one application form's file under the
run's working directory. The form check opens the file itself, so nobody re-types the form to
start a run. Its result is
the six fields of SOP section 6, with exactly those names: `application_id`, `outcome`,
`failed_rules`, `missing`, `customer_message`, `officer_message`.

Follow the SOP's order of work, and give each kind of work to the right kind of step:

1. **The form check is a script.** One `Execute` opens the application file, reads the fields
   out of it and checks completeness and hard rules H1 to H7. It reads every threshold and the list of
   required documents from a copy of the policy kept at `assets/policy.md`, so a changed number
   is an edit to that file and nothing else. It produces an answer a route can read: incomplete,
   failed, or passed.
2. **A route sends the application one of three ways:** returned, declined, or on to the
   judgment rules.
3. **The judgment rules are a `For` over the rules, with one `Decide` per rule.** A script reads
   the judgment rules out of `assets/policy.md` as a list, so a rule added to the policy needs no
   new step. Each pass asks the decision model one true-or-false question, whether this rule
   holds for this application, and the loop collects the verdicts.
4. **An `Aggregate` combines the verdicts** with the probability bar the policy names, and a
   route reads it: every rule holds, or not.
5. **There are four endings, one step each, each a script:** return, decline, approve, escalate.
   Each sets `outcome`, `failed_rules` and `missing`, and appends one line of JSON to a file
   under the run's working directory: `returns.jsonl`, `decisions.jsonl` (decline and approve)
   or `credit_officer_queue.jsonl`. Escalating is placing the application in that queue. No
   step asks a person to decide anything, and no step waits for the credit officer.
6. **The two messages are the one `Task_Agent`,** after the ending, written from the outcome and
   its reasons under the rules of SOP section 7. It cannot change the outcome. It is the only
   step an agent does.

Keep it easy to follow as a picture: someone looking at the step graph should see the form
check, the three-way route, the loop over judgment rules, the aggregate, the two-way route, the
four endings and the messages, and little else.

## Done means

- `aip compile --check ./built/assess_term_loan` reports no errors, and
  `aip fmt --check ./built/assess_term_loan` reports nothing to change.
- You have run it with `aip run ./built/assess_term_loan` on both examples, each to its end,
  answered the messages step yourself, and the result of each has the six fields and the
  outcome the SOP and policy give that application.
- You have tried the form check on variations you write yourself (an empty field, a missing
  document, a figure just under and just over a threshold) and it answers as the policy says.

Finish by saying, in a few lines, what you built, what you ran and what each run returned, and
anything in the SOP or the policy that was ambiguous and how you resolved it.
