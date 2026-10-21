# Source

What `launch-email-blast` was compiled from, how each piece of the source became a step, the rules the
scripts carry, what was left out on purpose, and the decisions taken without asking. Compiled 2026-10-21
for AIP format 0.6a1, skill version 1.

## Provenance

- `sop.md`: the Tessera Labs marketing page "How we run an email blast", exported from memory with
  `blast traces export`. Gives the intent and the rules in order.
- `traces.md`: four recorded Claude Code runs of that page with only the `blast` tools and no skill
  (run-01 launch brief-001, run-02 launch brief-003, run-03 digest brief-012, run-04 urgent hotfix
  brief-009): every `blast` call in order with its result, every judgment logged with `blast decide`, and
  the closing summary. Gives the real order of operations, the judgment points and the edge cases.
- The `blast` CLI itself (`blast --help` and every subcommand's `--help`) for the exact flags the scripts
  call, and the JSON `blast brief`, `blast product`, `blast segments` and `blast brand` return.
- The compliance checker's rules were read from the `blast` source to write the "what the check tests"
  section of `references/examples.md`; nothing else was taken from the tool's internals.

## How the source became steps

Every trace follows the same shape: read (sop, brief, brand, product, segments), judge (kind and urgency,
legal, segment, claims), write and submit, check, pick a subject line, schedule or hand off, log. The graph
keeps that order. 14 nodes: 10 working steps, 3 routers, 1 end.

| Source | Step | Kind | Why this kind |
|---|---|---|---|
| The reads at the top of every trace; SOP "Pick the audience" | `load` | execution (`scripts/load.py`) | Four `blast` reads. Segment choice is a rule: the brief's named segment, else the product segment whose persona the brief names. A rule, not a judgment, as the request asked. |
| SOP "Before you write"; judgments 1 and 2 of every trace | `classify` | decision | Three questions about one input (the brief): `email_kind` choice over the SOP's four kinds, `urgency` two-level score, `legal_review` noul. Thresholds 0.6 on kind and urgency, 0.3 margin on legal (a missed legal flag costs more than a spurious one). |
| SOP: flag for legal before scheduling anything | `by-legal` | router on `legal_review` | `true` ends the run at `hold` with a note; `false` writes. |
| same | `hold` | execution (`scripts/close.py hold`) | Writes the hold note to the campaign log with `blast log --draft none --not-scheduled` and logs the judgments. |
| SOP "Writing"; the bodies and subject lines in each trace; the claims judgments | `write` | client_task (`assets/write.md`) | Text generation. The template carries the brief, approved claims, brand guide, persona and the claims rules distilled from the traces' rulings; `references/examples.md` holds the worked examples on demand. |
| `blast draft` then `blast check` in every trace | `submit` | execution (`scripts/submit.py`) | Two `blast` calls; `check_passed` and the failures. |
| SOP "If it fails, fix what it names and run it again" | `gate` | router on `check_passed` | passed goes to the subject line; failed gets one fix-up pass. |
| same | `fix` | client_task (`assets/fix.md`) | Revise against the named failures; the failures and the current text are in the state. |
| same | `recheck` | execution (`scripts/close.py recheck`) | Stores the fixed draft, checks it once more, logs the result either way and ends the run (see "Decisions made without asking"). |
| SOP "Choosing the subject line"; the subject judgment in every trace | `pick-subject` | decision | One choice over first/second/third against the persona and the brief. Threshold 0.45: three close options are common, so only a real toss-up is flagged. |
| SOP rule 5; run-03 "Should we schedule the digest ourselves?" | `by-kind` | router on `email_kind` | digest goes to `handoff` (logged, never scheduled); launch, update and event go to `schedule`. |
| `blast schedule` and `blast log --scheduled`; run-01's and run-04's send-time judgments | `schedule` | execution (`scripts/schedule.py`) | Send time is a rule (below), then schedule, log the judgments with `blast decide`, log the campaign. |
| run-03's not-scheduled log entry | `handoff` | execution (`scripts/close.py newsletter`) | Logs the passing digest with the intended send time and the recommended subject line for the newsletter team. |

### What the decision steps were written from

- `email_kind`: the SOP's four kinds ("a launch, an update to an existing release, a nurture or digest, or
  an event"); run-04's reasoning that a hotfix is an update, not a launch; run-03's "monthly nurture digest
  with three tutorials and no release".
- `urgency`: the SOP ("most briefs are normal, a hotfix or a security notice is urgent and goes out the
  same day") and run-04's "leadership wants it out this morning". Two levels, because the SOP names two.
- `legal_review`: the SOP's list (legal, pricing, a partner, a comparison with another product); the
  `false` criterion carries run-03's point that another Labs project named as a tutorial topic is neither
  a partner nor a competitor.
- `subject_pick`: the SOP ("clearest for the persona, then the most curious, never one that could read as
  spam") plus the traces' reasons: name the version a developer scanning for upgrade news wants (run-01),
  a question line reads as a marketing hook to the platform-lead persona (run-02), "today" with no reason
  reads like a nag (run-04), a restart question could read as a service notice (run-03).

### Rules the scripts carry

- **Send time** (`blastlib.resolve_send_at`): an explicit `send_at` wins (run-04 used the requested 10:00
  over the 09:00 default; run-02 kept the requested time although it had passed). Otherwise urgent goes
  out the same day: today at 09:00 UTC, or the next full hour if 09:00 has passed. Otherwise the brief's
  send window at 09:00 UTC, as-is if the window already carries a time; a window that has already passed
  moves to the next 09:00 UTC slot and the rule text flags it for the brief owner (run-01).
- **Segment** (`load.py`): the brief's named segment, else the product segment matching the brief's
  persona; the first persona of that segment is `persona` in the state.
- **One fix-up pass**: the graph itself. `gate` sends a failure to `fix`, `recheck` ends the run; nothing
  routes back.
- **Body file**: `blast draft` reads the body from a file, so the scripts write it under the run's
  working directory as `drafts/<campaign_id>-draft.md` (`-fixed.md` for the fix-up), where the traces
  also left their body files. The body itself stays in the state.
- **Judgment log** (`blastlib.log_judgments`): every terminal script calls `blast decide` for the typed
  decisions it was given (kind and urgency, legal, segment, claims, subject line), so the SOP's "log every
  judgment call" holds although the decisions are typed. The claims rationale is the agent's own
  `claims_notes`; the typed decisions carry the criteria as their "why" because the decision model returns
  a label and probabilities, not prose. One `blast decide` per question: its `--options` is comma-split.

## Deliberately dropped, with rationale

- **`blast sop` as the first call, `blast --help` and the per-command help calls.** The page is compiled
  into this skill; the scripts know the flags.
- **The trace prompts and the agents' closing summaries.** Context for the recordings and the agent's own
  report format. No summary template is imposed; the consuming agent writes its own from the end state,
  the run history and the campaign log.
- **The `other` option on `email_kind`.** The SOP names exactly four kinds and the router needs a branch
  for every label; a brief that fits none would be forced into the nearest kind. Noted, not modelled.
- **The 120k events/s benchmark reasoning as a rule.** Kept as a worked example in
  `references/examples.md` and as a sentence in the write template ("an approved claim that is not a key
  message may be left out"): whether an approved but off-message claim belongs in a short email is the
  writer's call.
- **Run-04's "product record says 1.8.0 but the brief is 1.8.1, proceed?" as a decision step.** It is a
  claims ruling in the write task (proceed, say so in `claims_notes`), carried in `references/examples.md`.
- **`blast decide` called by the agent at each judgment.** The judgments are typed decision steps whose
  answers and confidences the run history records with attribution; the scripts write the `blast decide`
  records at the end of the run instead.
- **The temporary file paths in the traces** (`/Users/.../blast-body-camp-....md`). Replaced by the
  `drafts/` convention above.

## Decisions made without asking

- **A legal flag ends the run before writing.** The SOP only requires the flag before scheduling; the
  request said a legal flag ends the run with a note instead of scheduling, and drafting first would spend
  a client task on an email legal may rewrite. The hold is logged with `--draft none` so the campaign log
  shows why nothing went out.
- **The fix-up path ends the run either way, as the request said, and a draft that passed after the
  fix-up is scheduled by a human, not by this run.** Format 0.6a1 gives every key one producer, so the
  fixed draft's keys (`fixed_draft_id`, `fixed_subjects`) cannot rejoin the main path's subject pick and
  schedule steps without duplicating them. The `recheck` log entry carries the fixed draft id, the three
  subject lines, the resolved send time and the exact `blast schedule` command, so scheduling is one call.
  A draft that needed a fix-up getting a human look before it sends is also a defensible policy.
- **The end step carries only keys every path produces** (`brief_id`, `campaign_id`, `segment`,
  `email_kind`, `urgency`, `legal_review`). The same one-producer rule means the four terminal steps'
  notes and log ids cannot share a name, so they are in the run history and the campaign log under their
  own names (`note`, `handoff_note`, `hold_note`, `recheck_note`); the end step's description says where
  to look.
- **Scripts run with `python close.py <mode>`** for the three "end without scheduling" steps (hold,
  newsletter, recheck), one file with three modes rather than three near-identical files.
- **The subject pick sees the brief** as well as the subject lines and the persona, so the goal and the
  kind of email inform the pick (run-03 recommended a digest-shaped line).
- **A digest still runs `pick-subject`** before `handoff`, so the log carries a recommended subject line
  for the newsletter team, as run-03 did.
- Thresholds: `legal_review` 0.3 margin, `email_kind` and `urgency` 0.6, `subject_pick` 0.45.
- 14 nodes against "about ten steps": the ten working steps are the minimum that keeps a router per edge
  case the request named and a separate client task for the fix-up.

## Testing

- `aip validate ./skills/launch-email-blast`: clean.
- Scripts run directly against synthetic state in a scratch `BLAST_ROOT` (a copy of `data/`), every
  branch: load for brief-003, brief-012 and brief-009 (segment rule); submit of a passing body then
  schedule (past window moved to the next 09:00 UTC slot and flagged); submit of a failing body (missing
  disclaimer, exclamation mark, 61-character subject) then `recheck` with a fixed draft (passed, logged
  for a human to schedule) and with a still-failing draft (logged as failed twice); `hold`; a digest
  through submit and `newsletter`; the hotfix with an explicit `send_at` (kept as given). The send-time
  rule was unit-tested on the trace cases.
- Full local run with `aip run` on `{"brief_id": "brief-003", "send_at": ""}` in the scratch
  `BLAST_ROOT`, decisions answered by the TypeSafe model: launch (1.00), urgency 0 (1.00), legal false
  (0.91); the write task answered by hand; draft passed the first check; subject "first" (0.88);
  scheduled for 2026-10-22T09:00Z because the brief's 2026-10-16 window had passed, logged as log-0001.
  Same classification and subject line as run-02 of the traces.
- Full local run on brief-012 the same way: digest (1.00), urgency 0 (1.00), legal false (0.93); passed
  the first check. The subject pick paused as a `review`: the model proposed "second" at 0.43 confidence
  (first 0.32, second 0.62, third 0.06), under the 0.45 threshold, and the override was "first" for the
  reason run-03 gave (it says what is inside; the "first pipeline" line undersells two of the three
  tutorials). Routed to `handoff` and logged as not scheduled for the newsletter team, log-0002. The
  threshold flagged the one genuinely close call and nothing else.
- Fresh-agent sessions were not run here; the request scoped testing to one local run.
