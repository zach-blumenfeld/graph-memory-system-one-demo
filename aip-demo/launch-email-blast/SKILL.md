---
name: launch-email-blast
description: Run a Tessera Labs email blast end to end from a campaign brief id - read the brief, product claims, segment persona and brand guide with the blast CLI, classify the email (launch, update, digest, event), urgency and legal sensitivity, write three subject lines and a markdown body against the approved claims list, store and compliance-check the draft with one fix-up pass, pick the subject line, schedule it for the send window (09:00 UTC default, same day when urgent) and log the campaign and every judgment call. Use for any campaign brief, launch email, release announcement, hotfix notice, newsletter digest or nurture email that needs drafting, checking, scheduling or logging. Digests are drafted and logged but never scheduled; legal-sensitive briefs stop for a human.
metadata:
  aip-version: "0.5a1"
  author: tessera-labs-marketing
  version: "1.0"
---

# AIP runtime — format 0.5a1

You are executing an Agent Instruction Protocol (AIP) procedure: the fenced YAML block in this skill's `SKILL.md`. AIP is a protocol for cheaply, quickly, and accurately executing multi-step tasks as a graph of typed steps. You drive the run and execute every step yourself, following the semantics below.

Critical terminology:

- **Client**: you, the agent running this procedure; the `client_task` step kind is named for it. You supply each step's input, run its script, answer its questions by your own judgment, perform its task, follow its router, and make the final call at every step.
- **State**: the JSON object a step receives. Each step declares its required keys as `inputs`; extra keys pass through.
- **Step kinds**: `execution` runs a script, `decision` asks typed questions about the state, `client_task` hands work to you, `router` branches on a value in the state, `end` declares the final state's shape.

## Execution

The state is one JSON object. It starts as the start step's `inputs` and flows along `inputs_to`; each step's output is merged over it, so keys accumulate and extra keys pass through untouched. A step runs only if the state holds every key it declares in `inputs`, with the declared types; check that before each step. You may change the state before any step runs; you have the final say at every step.

- **`execution`**: run `script` with one JSON object on stdin, `{"currentState": <state>, "assets": {<file stem>: <content>}, "expects": <the next step's inputs>}`. The script writes one JSON object to stdout; merge it over the state.
- **`decision`**: answer each question against the state. Each answer collapses to one value under its question name and is merged over the state: a noul to `true`/`false`, a choice to its label, a score to its level number. `thresholds` name the questions where an uncertain answer matters most; when your answer to one is a close call, reconsider it before continuing.
- **`client_task`**: render `template` with `{key}` from the state, `{assets[stem]}` for its assets, and `{meta.name}` for the skill name. Perform the task, loading `references` if their descriptions apply, and produce the next step's `inputs`; merge them over the state.
- **`router`**: read the state's `branch_on` key and continue at `branches[value]`. A value with no branch is an error.
- **`end`**: the state must hold `end`'s `inputs`. That state is the procedure's result.

```yaml
purpose: >
  Turn one campaign brief into one compliant, scheduled, logged email to one audience segment, the way
  the Tessera Labs marketing SOP says and the way four recorded runs actually did it. Scripts call the
  `blast` CLI (the only way to reach the Notion briefs, drafts, scheduling and the campaign log) and apply
  the SOP's rules: segment by the brief, 09:00 UTC send window, same-day when urgent, one fix-up pass
  after a failed compliance check. The decision model classifies the email, its urgency and legal
  sensitivity and picks the subject line. The agent writes the email against the approved claims list,
  the brand guide and the persona. A legal flag stops the run for a human; a digest is drafted, checked
  and logged but handed to the newsletter team instead of scheduled.

trigger_when:
  - A campaign brief id (brief-NNN) needs its email blast done - drafted, checked, scheduled, logged.
  - Someone asks to launch, announce or send a product release, hotfix, security notice, event or digest to a segment.
  - A brief in the Campaign Briefs database is marked ready and names a product, segment or persona and a send window.

do_not_use_when:
  - There is no brief id; writing the brief itself is a different job.
  - The ask is to edit, reschedule or cancel a blast that is already scheduled.
  - The email is not a Tessera Labs marketing send (support replies, transactional mail, internal memos).

steps:
  - name: load
    kind: execution
    description: Read the brief, product claims, segments and brand guide with blast; pick the segment by the SOP rule.
    inputs:
      - name: brief_id
        type: string
        description: The brief's id in the Campaign Briefs database, e.g. brief-003.
      - name: send_at
        type: string
        description: ISO send time, e.g. 2026-10-16T09:00Z. Empty means the brief's send window at 09:00 UTC.
    script: scripts/load.py
    inputs_to: classify

  - name: classify
    kind: decision
    description: What kind of email the brief asks for, how urgent it is, and whether legal must see it first.
    inputs:
      - name: brief
        type: object
        description: The brief as blast returns it - title, product, goal, key messages, CTA, send window, notes.
    questions:
      email_kind:
        type: choice
        instructions: >
          What kind of email does this brief describe? Judge from the title, goal and notes. A hotfix, patch or
          security notice for a version that already shipped is an update, not a launch.
        criteria:
          launch: Announces a new release or version of a product and asks readers to try or upgrade to it.
          update: A change to a release that already shipped - hotfix, patch, security notice, deprecation, breaking change.
          digest: A newsletter, monthly digest, roundup or nurture email - tutorials or stories, no release to announce.
          event: Invites readers to a webinar, meetup, talk, workshop or office hours.
      urgency:
        type: score
        instructions: >
          How urgent is the send? Most briefs are normal and go out in their send window. Only a hotfix, a security
          notice, or a brief that says same day, today or this morning is urgent and goes out the same day.
        criteria:
          - Normal - a launch, update, digest or event with a send window; nothing says it must go today.
          - Urgent - a hotfix or security notice, or the brief asks for a same-day send (today, this morning, now).
      legal_review:
        type: noul
        instructions: >
          Must legal review this brief before anything is scheduled? Yes if the brief mentions legal matters, pricing
          or money, a partner or partnership, or compares the product with another product.
        criteria:
          "true": Pricing, cost, licence or contract terms, a partner or co-marketing, a named competitor or a comparison with another product, or anything legal.
          "false": Product capabilities, tutorials, releases and events only; another Labs project named as a tutorial topic is not a partner or competitor.
    thresholds:
      email_kind: 0.6
      urgency: 0.6
      legal_review: 0.3
    inputs_to: by-legal

  - name: by-legal
    kind: router
    description: A legal flag ends the run with a note for a human; otherwise write the email.
    branch_on: legal_review
    branches:
      "true": close
      "false": write

  - name: write
    kind: client_task
    description: Write three subject lines and a markdown body from the brief, approved claims, brand guide and persona.
    inputs:
      - name: brief
        type: object
      - name: product
        type: object
        description: Name, version, tagline, docs and repo URLs, approved claims.
      - name: brand
        type: object
        description: Voice rules, banned claims, required disclaimer, subject line rules.
      - name: segment
        type: object
        description: The chosen segment with its persona notes.
      - name: persona
        type: object
        description: The segment's persona - name, preferred tone, turn-offs.
      - name: email_kind
        type: string
    template: assets/write.md
    references:
      - path: references/examples.md
        description: Claims rulings from four recorded runs, a body that passed first time, subject line picks, and what the compliance check tests. Load when a key message is not on the approved list or you are unsure what shape the body should take.
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
        description: Exactly three subject lines, in order.
      - name: body
        type: string
        description: The email body in markdown.
      - name: claims_notes
        type: string
        description: For the log - which key messages were kept, rephrased or dropped and why; open items for a human.
    script: scripts/submit.py
    inputs_to: gate

  - name: gate
    kind: router
    description: Passed goes on to the subject line; the first failure gets one fix-up pass; a second failure ends the run.
    branch_on: check_state
    branches:
      passed: pick-subject
      fix: fix
      stop: close

  - name: fix
    kind: client_task
    description: Fix exactly what the compliance check named; one pass only.
    inputs:
      - name: draft_id
        type: string
      - name: failures
        type: list[*]
        description: The checker's failures, each with check and detail.
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
    template: assets/fix.md
    inputs_to: resubmit

  - name: resubmit
    kind: execution
    description: Store the fixed draft and recheck it; a second failure sets check_state to stop.
    inputs:
      - name: campaign_id
        type: string
      - name: segment
        type: object
      - name: subjects
        type: list[*]
      - name: body
        type: string
      - name: attempt
        type: integer
        description: Number of drafts submitted so far; the script refuses a third pass.
    script: scripts/submit.py
    inputs_to: gate

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
    questions:
      subject_pick:
        type: choice
        instructions: >
          Which subject line should be sent? Pick the one that is clearest for the persona: it names the release or
          the thing the reader can now do, in the persona's preferred tone. Prefer the more curious line only when it
          is just as clear. Never pick a line that could read as spam, a teaser, an alarm, or urgency pressure
          (today, now), or that hides the version number a reader scanning for upgrade news wants.
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
      digest: close
      launch: schedule
      update: schedule
      event: schedule

  - name: schedule
    kind: execution
    description: Resolve the send time (request, else same day when urgent, else the brief's window at 09:00 UTC), schedule, log judgments and the campaign.
    inputs:
      - name: draft_id
        type: string
      - name: subjects
        type: list[*]
      - name: subject_pick
        type: string
      - name: segment
        type: object
      - name: send_at
        type: string
      - name: brief
        type: object
      - name: urgency
        type: integer
      - name: email_kind
        type: string
    script: scripts/schedule.py
    inputs_to: end

  - name: close
    kind: execution
    description: End without scheduling - legal hold, compliance failed twice, or a digest for the newsletter team - and log it.
    inputs:
      - name: brief
        type: object
      - name: campaign_id
        type: string
      - name: legal_review
        type: boolean
    script: scripts/close.py
    inputs_to: end

  - name: end
    kind: end
    description: The outcome - scheduled, legal-hold, compliance-failed or handed-to-newsletter-team - with the log entry and a note for the human reading the result.
    inputs:
      - name: brief_id
        type: string
      - name: campaign_id
        type: string
      - name: outcome
        type: string
        description: scheduled | legal-hold | compliance-failed | handed-to-newsletter-team
      - name: note
        type: string
        description: What went out, to whom, when, which subject, and what a human still has to do.
      - name: log_id
        type: string

anti_patterns:
  - Writing a number, comparison or promise about product behaviour that is not on the approved claims list because the brief asked for it; drop it and say so in claims_notes.
  - Inventing a URL, a command name or a figure the brief and product record do not give; use a marked placeholder and flag it.
  - Scheduling a digest or nurture email; the newsletter team sends those.
  - Scheduling before the compliance check passes, or looping on fixes; one fix-up pass, then a human.
  - Picking the most curious subject line over the clearest one, or one with urgency words the persona dislikes.
  - Leaving out the Labs disclaimer, adding a second call to action, or using an exclamation mark anywhere in the body.
  - Choosing the segment by judgment when the brief names one; the rule is the brief's segment, else the product segment for the brief's persona.
```
