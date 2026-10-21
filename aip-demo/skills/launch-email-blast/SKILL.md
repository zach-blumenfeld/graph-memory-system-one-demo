---
name: launch-email-blast
description: Run a Tessera Labs email blast end to end from a campaign brief id - read the brief, product claims, segment persona and brand guide with the blast CLI, classify the email (launch, update, digest, event), its urgency and legal sensitivity, write three subject lines and a markdown body against the approved claims list, store and compliance-check the draft with one fix-up pass, pick the subject line, schedule it for the send window (09:00 UTC default, same day when urgent) and log the campaign and every judgment call. Use for any campaign brief, launch email, release announcement, hotfix notice, newsletter digest or nurture email that needs drafting, checking, scheduling or logging. Digests are drafted and logged but never scheduled; legal-sensitive briefs stop for a human.
metadata:
  aip-version: "0.6a1"
  author: tessera-labs-marketing
  version: "1"
---

# AIP runtime — format 0.6a1

You are executing an Agent Instruction Protocol (AIP) procedure: the fenced YAML block in this skill's `SKILL.md`. AIP is a protocol for cheaply, quickly, and accurately executing multi-step tasks as a graph of typed steps. You drive the run and execute every step yourself, following the semantics below.

Critical terminology:

- **Client**: you, the agent running this procedure; the `client_task` step kind is named for it. You supply each step's input, run its script, answer its questions by your own judgment, perform its task, follow its router, and make the final call at every step.
- **State**: the one JSON object a run carries. Each step declares the keys it reads as `inputs`; `execution` and `client_task` steps declare the keys they add as `outputs`, and a `decision` adds one key per question.
- **Step kinds**: `execution` runs a script, `decision` asks typed questions about the state, `client_task` hands work to you, `router` branches on a value in the state, `end` declares the procedure's result.

## Execution

The state starts as the start step's `inputs` and flows along `inputs_to`; each step adds its outputs to it. Every key is produced by exactly one step, so keys accumulate and nothing is overwritten. A step runs only if the state holds every key it declares in `inputs`, with the declared types; check that before each step. A step sees only those keys: give it its declared `inputs` and nothing else from the state. You have the final say at every step.

- **`execution`**: before the first one, check that this machine has everything `requires` names (the interpreter at its minimum version, the packages, the tools); if anything is missing, stop and name all of it. Run `script` from its folder, launched with the step's `command` when it has one and `python <script>` otherwise, with one JSON object on stdin, `{"state": <the step's inputs>, "assets": {<file stem>: <content>}, "expects": <the next step's inputs>}`. The script writes one JSON object to stdout holding exactly the step's `outputs`; add them to the state. A non-zero exit, or output missing a declared key, fails the step: stop there and report it rather than doing the step by hand.
- **`decision`**: answer each question from the step's inputs, and from the run so far only when the step sets `history: true`. Each answer collapses to one value under its question name and is added to the state: a noul to `true`/`false`, a choice to its label, a score to its level number. `thresholds` name the questions where an uncertain answer matters most; when your answer to one is a close call, reconsider it before continuing.
- **`client_task`**: render `template` with `{key}` from the step's inputs, `{assets[stem]}` for its assets, and `{meta.name}` for the skill name. Perform the task, loading `references` if their descriptions apply, and produce the step's `outputs`; add them to the state.
- **`router`**: read the state's `branch_on` key and continue at `branches[value]`. A value with no branch is an error.
- **`end`**: the state must hold `end`'s `inputs`. Those keys are the procedure's result.

```yaml
purpose: >
  Turn one campaign brief into one compliant, scheduled, logged email to one audience segment, the way
  the Tessera Labs marketing SOP says and the way four recorded runs actually did it. Scripts call the
  `blast` CLI (the only way to reach the Notion briefs, drafts, scheduling and the campaign log) and apply
  the SOP's rules: the segment the brief names, the send window at 09:00 UTC unless a time is given, same
  day when urgent, one fix-up pass after a failed compliance check. The decision model classifies the
  email, its urgency and legal sensitivity and picks the subject line. The agent writes the email against
  the approved claims list, the brand guide and the persona. A legal flag stops the run for a human
  before anything is drafted; a digest is drafted, checked and logged but handed to the newsletter team
  instead of scheduled; a draft that needed a fix-up is logged for a human to schedule. Every path ends
  with a campaign log entry that carries the note for the next person, and every judgment call is logged.

trigger_when:
  - A campaign brief id (brief-NNN) needs its email blast done - drafted, checked, scheduled, logged.
  - Someone asks to launch, announce or send a product release, hotfix, security notice, event or digest to a segment.
  - A brief in the Campaign Briefs database is marked ready and names a product, segment or persona and a send window.

do_not_use_when:
  - There is no brief id; writing the brief itself is a different job.
  - The ask is to edit, reschedule or cancel a blast that is already scheduled.
  - The email is not a Tessera Labs marketing send (support replies, transactional mail, internal memos).

requires:
  interpreter:
    name: python
    version: "3.10"
  tools:
    - blast

steps:
  - name: load
    kind: execution
    description: Read the brief, product claims, segments and brand guide with blast; pick the segment by the SOP rule (the brief's segment, else the product segment for the brief's persona).
    inputs:
      - name: brief_id
        type: string
        description: The brief's id in the Campaign Briefs database, e.g. brief-003.
      - name: send_at
        type: string
        description: ISO send time, e.g. 2026-10-16T09:00Z. Empty means the brief's send window at 09:00 UTC.
    script: scripts/load.py
    timeout: 120
    outputs:
      - name: brief
        type: object
        description: The brief as blast returns it - title, product, goal, key messages, CTA, send window, notes.
      - name: campaign_id
        type: string
        description: The campaign id the brief belongs to, e.g. camp-2026-10-003.
      - name: product
        type: object
        description: Name, version, tagline, docs and repo URLs, approved claims.
      - name: brand
        type: object
        description: Voice rules, banned claims, required disclaimer, subject line rules.
      - name: segment
        type: object
        description: The chosen segment - id, name, size, description, persona list.
      - name: persona
        type: object
        description: The segment's persona - name, preferred tone, turn-offs.
      - name: segment_rule
        type: string
        description: Which SOP rule chose the segment, for the judgment log.
    inputs_to: classify

  - name: classify
    kind: decision
    description: What kind of email the brief asks for, how urgent it is, and whether legal must see it first.
    inputs:
      - name: brief
        type: object
    questions:
      email_kind:
        type: choice
        instructions: >
          What kind of email does this brief describe? Judge from the title, goal, key messages and notes. A hotfix,
          patch or security notice for a version that already shipped is an update, not a launch.
        criteria:
          launch: Announces a new release or version of a product and asks readers to try or upgrade to it.
          update: A change to a release that already shipped - hotfix, patch, security notice, deprecation, breaking change.
          digest: A newsletter, monthly digest, roundup or nurture email - tutorials or stories, no release to announce.
          event: Invites readers to a webinar, meetup, talk, workshop or office hours.
      urgency:
        type: score
        instructions: >
          How urgent is the send? Most briefs are normal and go out in their send window. Only a hotfix, a security
          notice, or a brief that says same day, today, this morning or now is urgent and goes out the same day.
        criteria:
          - Normal - a launch, update, digest or event with a send window; nothing says it must go out today.
          - Urgent - a hotfix or security notice, or the brief asks for a same-day send (today, this morning, now).
      legal_review:
        type: noul
        instructions: >
          Must legal review this brief before anything is scheduled? Yes if the brief mentions legal matters, pricing
          or money, a partner or partnership, or compares the product with another product.
        criteria:
          "true": Pricing, cost, licence or contract terms, a partner or co-marketing, a named competitor or a comparison with another product, or anything legal.
          "false": Product capabilities, bug fixes, tutorials, releases and events only; another Tessera Labs project named as a topic is not a partner or a competitor.
    thresholds:
      email_kind: 0.6
      urgency: 0.6
      legal_review: 0.3
    inputs_to: by-legal

  - name: by-legal
    kind: router
    description: A legal flag ends the run with a hold note for a human before anything is drafted; otherwise write the email.
    branch_on: legal_review
    branches:
      "true": hold
      "false": write

  - name: hold
    kind: execution
    description: Log the campaign as on hold for legal review, with a note saying what a human must do, and log the judgment calls.
    inputs:
      - name: brief_id
        type: string
      - name: campaign_id
        type: string
      - name: brief
        type: object
      - name: email_kind
        type: string
      - name: urgency
        type: integer
      - name: legal_review
        type: boolean
    script: scripts/close.py
    command: ["python", "close.py", "hold"]
    timeout: 120
    outputs:
      - name: hold_log_id
        type: string
        description: The campaign log entry recording the hold.
      - name: hold_note
        type: string
        description: Why nothing was drafted or scheduled and what the human must do next.
    inputs_to: end

  - name: write
    kind: client_task
    description: Write three subject lines and a markdown body from the brief, approved claims, brand guide and persona.
    inputs:
      - name: brief_id
        type: string
      - name: campaign_id
        type: string
      - name: brief
        type: object
      - name: product
        type: object
      - name: brand
        type: object
      - name: segment
        type: object
      - name: persona
        type: object
      - name: email_kind
        type: string
      - name: urgency
        type: integer
    template: assets/write.md
    references:
      - path: references/examples.md
        description: Claims rulings from four recorded runs, a body that passed first time, the subject line picks, and what the compliance check tests. Load when a key message is not on the approved list or you are unsure what shape the body should take.
    outputs:
      - name: subjects
        type: list[*]
        description: Exactly three subject lines, in order.
      - name: body
        type: string
        description: The email body in markdown, with the disclaimer verbatim and one call to action.
      - name: claims_notes
        type: string
        description: For the log - which key messages were kept, rephrased or dropped and why; anything a human must confirm before the send.
    inputs_to: submit

  - name: submit
    kind: execution
    description: Store the draft with blast draft and run blast check on it.
    inputs:
      - name: campaign_id
        type: string
      - name: segment
        type: object
      - name: subjects
        type: list[*]
      - name: body
        type: string
    script: scripts/submit.py
    timeout: 120
    outputs:
      - name: draft_id
        type: string
        description: The stored draft, e.g. draft-camp-2026-10-003-01.
      - name: check_passed
        type: boolean
        description: Whether the compliance check passed.
      - name: failures
        type: list[*]
        description: The checker's failures, each with check and detail; empty when it passed.
      - name: required_disclaimer
        type: string
        description: The disclaimer the checker requires, verbatim.
    inputs_to: gate

  - name: gate
    kind: router
    description: A passing draft goes on to the subject line; a failing one gets exactly one fix-up pass and a recheck, after which the run ends.
    branch_on: check_passed
    branches:
      "true": pick-subject
      "false": fix

  - name: fix
    kind: client_task
    description: Fix exactly what the compliance check named; one pass only.
    inputs:
      - name: brief_id
        type: string
      - name: brief
        type: object
      - name: draft_id
        type: string
      - name: failures
        type: list[*]
      - name: subjects
        type: list[*]
      - name: body
        type: string
      - name: required_disclaimer
        type: string
      - name: brand
        type: object
      - name: product
        type: object
      - name: persona
        type: object
      - name: claims_notes
        type: string
    template: assets/fix.md
    outputs:
      - name: fixed_subjects
        type: list[*]
        description: The three subject lines after the fix, in order.
      - name: fixed_body
        type: string
        description: The revised markdown body.
      - name: fix_notes
        type: string
        description: What was changed and why, for the log.
    inputs_to: recheck

  - name: recheck
    kind: execution
    description: Store the fixed draft, check it again, and log the result either way - a draft that needed fixing is scheduled by a human, not by this run.
    inputs:
      - name: brief_id
        type: string
      - name: campaign_id
        type: string
      - name: brief
        type: object
      - name: segment
        type: object
      - name: segment_rule
        type: string
      - name: draft_id
        type: string
      - name: failures
        type: list[*]
      - name: fixed_subjects
        type: list[*]
      - name: fixed_body
        type: string
      - name: fix_notes
        type: string
      - name: claims_notes
        type: string
      - name: send_at
        type: string
      - name: email_kind
        type: string
      - name: urgency
        type: integer
      - name: legal_review
        type: boolean
    script: scripts/close.py
    command: ["python", "close.py", "recheck"]
    timeout: 120
    outputs:
      - name: fixed_draft_id
        type: string
        description: The fixed draft as stored.
      - name: fixed_passed
        type: boolean
        description: Whether the fixed draft passed the compliance check.
      - name: fixed_failures
        type: list[*]
        description: The failures still named after the fix; empty when it passed.
      - name: recheck_log_id
        type: string
        description: The campaign log entry for the fix-up pass.
      - name: recheck_note
        type: string
        description: What happened and what a human must do - schedule the passing draft, or fix the failing one.
    inputs_to: end

  - name: pick-subject
    kind: decision
    description: Which of the three subject lines goes out, for this persona.
    inputs:
      - name: subjects
        type: list[*]
        description: The three subject lines of the passing draft, in order.
      - name: persona
        type: object
        description: Who reads it - name, preferred tone, turn-offs.
      - name: brief
        type: object
        description: The brief, for the goal and the kind of email.
    questions:
      subject_pick:
        type: choice
        instructions: >
          Which subject line should be sent? Pick the one that is clearest for the persona: it names the release (product
          and version) or the thing the reader can now do, in the persona's preferred tone. Prefer the more curious line
          only when it is just as clear. Never pick a line that could read as spam, a teaser, an alarm, a marketing hook,
          or urgency pressure the persona dislikes, or that hides the version a reader scanning for upgrade news wants.
        criteria:
          first: The first subject line in the list.
          second: The second subject line in the list.
          third: The third subject line in the list.
    thresholds:
      subject_pick: 0.45
    inputs_to: by-kind

  - name: by-kind
    kind: router
    description: Digests and nurture emails are logged for the newsletter team, never scheduled; everything else is scheduled.
    branch_on: email_kind
    branches:
      digest: handoff
      launch: schedule
      update: schedule
      event: schedule

  - name: schedule
    kind: execution
    description: Resolve the send time (the request's, else same day when urgent, else the brief's window at 09:00 UTC), schedule the draft with blast schedule, log the judgment calls and the campaign.
    inputs:
      - name: brief_id
        type: string
      - name: campaign_id
        type: string
      - name: brief
        type: object
      - name: segment
        type: object
      - name: segment_rule
        type: string
      - name: persona
        type: object
      - name: draft_id
        type: string
      - name: subjects
        type: list[*]
      - name: subject_pick
        type: string
      - name: send_at
        type: string
      - name: email_kind
        type: string
      - name: urgency
        type: integer
      - name: legal_review
        type: boolean
      - name: claims_notes
        type: string
    script: scripts/schedule.py
    timeout: 120
    outputs:
      - name: send_id
        type: string
        description: The scheduled send, e.g. send-213716.
      - name: scheduled_at
        type: string
        description: The ISO time the send is scheduled for.
      - name: send_rule
        type: string
        description: Which rule produced the send time; says so when a past window was moved.
      - name: subject
        type: string
        description: The subject line that goes out.
      - name: log_id
        type: string
        description: The campaign log entry.
      - name: note
        type: string
        description: What went out, to whom, when, which subject, and anything a human should look at.
    inputs_to: end

  - name: handoff
    kind: execution
    description: Log the passing digest as not scheduled, with the intended send time and the recommended subject line for the newsletter team, and log the judgment calls.
    inputs:
      - name: brief_id
        type: string
      - name: campaign_id
        type: string
      - name: brief
        type: object
      - name: segment
        type: object
      - name: segment_rule
        type: string
      - name: persona
        type: object
      - name: draft_id
        type: string
      - name: subjects
        type: list[*]
      - name: subject_pick
        type: string
      - name: send_at
        type: string
      - name: email_kind
        type: string
      - name: urgency
        type: integer
      - name: legal_review
        type: boolean
      - name: claims_notes
        type: string
    script: scripts/close.py
    command: ["python", "close.py", "newsletter"]
    timeout: 120
    outputs:
      - name: handoff_log_id
        type: string
        description: The campaign log entry handing the digest to the newsletter team.
      - name: handoff_note
        type: string
        description: The draft, the intended send time and the recommended subject line for the newsletter team.
    inputs_to: end

  - name: end
    kind: end
    description: The brief's classification and ids. How it ended is in the campaign log and in the run history, on the last step before end - note (scheduled), handoff_note (digest for the newsletter team), hold_note (legal hold) or recheck_note (one fix-up pass, a human schedules or fixes).
    inputs:
      - name: brief_id
        type: string
      - name: campaign_id
        type: string
      - name: segment
        type: object
        description: The segment the email was written for.
      - name: email_kind
        type: string
        description: launch | update | digest | event.
      - name: urgency
        type: integer
        description: 0 normal, 1 urgent (same-day send).
      - name: legal_review
        type: boolean
        description: True when the run stopped for legal review before drafting.

anti_patterns:
  - Writing a number, comparison or promise about product behaviour that is not on the approved claims list because the brief asked for it; drop it and say so in claims_notes.
  - Inventing a URL, a command name or a figure the brief and product record do not give; use the docs root or repo, describe the feature, and flag it.
  - Scheduling a digest or nurture email; the newsletter team sends those.
  - Scheduling before the compliance check passes, or looping on fixes; one fix-up pass, then a human.
  - Picking the most curious subject line over the clearest one, or one with urgency words or a hook the persona dislikes.
  - Leaving out the Labs disclaimer, adding a second call to action, or using an exclamation mark anywhere in the body.
  - Choosing the segment by judgment when the brief names one; the rule is the brief's segment, else the product segment for the brief's persona.
  - Naming a competitor product in the body, even when an approved claim does.
```
