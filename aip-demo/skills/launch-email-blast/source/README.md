# Source

What `launch-email-blast` was compiled from, how each piece of the source became a step, and what was
left out on purpose. Compiled 2026-10-07 for AIP format 0.5a1.

## Provenance

- `sop.md` — the Tessera Labs marketing page "How we run an email blast", exported from memory with
  `blast traces export --source`. Gives the intent and the rules.
- `traces.md` — four recorded Claude Code runs of that page with only the `blast` tools and no skill
  (run-01 launch brief-001, run-02 launch brief-003, run-03 digest brief-012, run-04 urgent hotfix
  brief-009): every `blast` call in order with its result, every judgment logged with `blast decide`,
  and the closing summary. Gives the real order of operations, the judgment points and the edge cases.
- The `blast` CLI itself (`blast --help` and the subcommand help) for the exact flags the scripts call.
- The compliance checker's rules were read from the `blast` source to write the "what the check tests"
  section of `references/examples.md`; nothing else was taken from the tool's internals.

## How the source became steps

The traces all follow the same shape: read (sop, brief, brand, product, segments), judge (kind and
urgency, legal, segment, claims), write and submit, check, pick a subject, schedule, log. The graph keeps
that order with 13 nodes: 9 working steps, 3 routers, 1 end.

| Source | Step | Kind | Why this kind |
|---|---|---|---|
| Reads at the start of every trace; SOP "Pick the audience" | `load` | execution (`scripts/load.py`) | Four `blast` reads. Segment choice is a rule: the brief's named segment, else the product segment whose persona the brief names. Rule, not judgment, as the request asked. |
| SOP "Before you write"; judgments 1–2 of every trace | `classify` | decision | Three questions about one input (the brief): `email_kind` choice over the SOP's four kinds, `urgency` two-level score, `legal_review` noul. Thresholds: 0.6 confidence on kind and urgency, 0.3 margin on legal (a missed legal flag costs more than a spurious one). |
| SOP: flag for legal before scheduling anything | `by-legal` | router | `true` ends the run at `close` with a hold note; `false` writes. |
| SOP "Writing"; the body and subject lines in each trace; claims judgments | `write` | client_task (`assets/write.md`) | Text generation. The template carries the brief, approved claims, brand guide, persona and the claims rules distilled from the traces' rulings; `references/examples.md` holds the worked examples on demand. |
| `blast draft` then `blast check` in every trace | `submit` | execution (`scripts/submit.py`) | Two `blast` calls; computes `check_state` (passed / fix / stop) from the result and the attempt count. |
| SOP "If it fails, fix what it names and run it again" | `gate` | router | Shared by `submit` and `resubmit`. passed → pick-subject, fix → one fix-up pass, stop → close. |
| same | `fix` | client_task (`assets/fix.md`) | Revise the draft against the named failures; the failures and the current text are in the state. |
| same | `resubmit` | execution (same script) | Second draft and recheck; the script sets `stop` on a second failure so there is no loop. |
| SOP "Choosing the subject line"; the subject judgment in every trace | `pick-subject` | decision | One choice over first/second/third against the persona. Threshold 0.45: three close options are common, so only a real toss-up is flagged. |
| SOP rule 5; run-03 judgment "Should this draft be scheduled by us?" | `by-kind` | router | digest → close (logged, never scheduled); launch, update, event → schedule. |
| `blast schedule` + `blast log --scheduled`; run-04 send-time judgment | `schedule` | execution (`scripts/schedule.py`) | Send time is a rule (see below), then schedule, log the judgments with `blast decide`, log the campaign. |
| run-03's not-scheduled log; the legal flag; a draft that fails twice | `close` | execution (`scripts/close.py`) | Writes the not-scheduled log entry with the reason and a note for the human; logs the judgments. |

### Rules the scripts carry

- **Send time** (`blastlib.resolve_send_at`): an explicit `send_at` wins (run-04 used the requested
  10:00 over the 09:00 default); otherwise urgent goes out today at 09:00 UTC, or the next full hour if
  09:00 has passed (SOP: "a hotfix or a security notice is urgent and goes out the same day"); otherwise
  the brief's send window at 09:00 UTC, or as-is if the window already carries a time.
- **Segment**: the brief's named segment, else the product segment matching the brief's persona; the
  first persona of that segment is `persona` in the state.
- **One fix-up pass**: `attempt` counts drafts; the second failure is `stop`.
- **Judgment log**: `schedule.py` and `close.py` call `blast decide` for kind/urgency, legal, segment,
  claims and subject line so the SOP's "log every judgment call" holds even though the decisions are
  typed. The claims rationale is the agent's own `claims_notes`; the typed decisions carry the criteria
  as their "why" because the decision model returns a label and probabilities, not prose.

## Deliberately dropped, with rationale

- **`blast sop` as the first call.** The SOP is compiled into this skill; reading it at runtime would
  be redundant. The rules it states are all in steps, templates or scripts.
- **`blast --help` and the per-command help calls** in the traces. Tool discovery; the scripts know the
  flags.
- **The trace prompts and the agents' closing summaries.** Context for the runs and the agent's own
  report format. The end state carries `outcome`, `note`, `log_id` so the consuming agent can write its
  own summary; no template for the summary is imposed.
- **Tool denials** (a shell loop to count subject-line characters was refused in runs 01 and 02). An
  artefact of the recording sandbox. The compliance check counts characters.
- **The 120k events/s benchmark reasoning** as a rule. Kept as a worked example in
  `references/examples.md`, not as a step: whether an approved but off-message claim belongs in a short
  email is the writer's call.
- **`blast decide` called by the agent at each judgment.** The judgments are typed decision steps; the
  scripts write the `blast decide` records at the end of the run instead. Side effect: when the skill
  runs under the AIP server those records come from a script, not from the agent's Bash, so the
  recording hooks do not see them.
- **The body file path** (`/tmp/blast/...`, `drafts/...`). `submit.py` writes the body to a temp file
  for `blast draft`; the body itself stays in the state.
- **The "other" option on `email_kind`.** The SOP names exactly four kinds and the router needs a branch
  for every label; a brief that fits none would be forced into the nearest kind. Noted, not modelled.

## Decisions made without asking

- A legal flag ends the run before writing (the request said so). The SOP only requires the flag before
  scheduling; drafting first would give legal something to review but was out of scope. The hold is
  logged with `--draft none` so the campaign log shows why nothing went out.
- Draft that fails twice is logged as not scheduled with the failures, so the next person sees it.
- A digest is run through `pick-subject` before `close` so the log carries a recommended subject line
  for the newsletter team, as run-03 did.
- `schedule`/`close` log the judgment calls with `blast decide` (see above).
- Thresholds: `legal_review` 0.3 margin, `email_kind` and `urgency` 0.6, `subject_pick` 0.45.

## Testing

- `aip validate ./launch-email-blast`: clean.
- Full local run on `{"brief_id": "brief-003", "send_at": ""}` with the TypeSafe decision model: launch,
  urgency 0, legal false (p=0.12), draft passed first check, subject "first", scheduled
  2026-10-16T09:00Z, logged. Same result as run-02 of the traces.
- Full local run on brief-012 in a scratch `BLAST_ROOT`: classified digest, passed, subject picked,
  routed to `close`, logged not-scheduled.
- Scripts run directly against synthetic state for the remaining branches: first failure → `fix`,
  second failure → `stop` → compliance-failed log; fixed draft → scheduled; urgent with empty `send_at`
  → same-day; legal flag → legal-hold log.
- Fresh-agent sessions were not run here; the request scoped testing to one local run. The plan's step
  6 (publish, then a fresh `claude` with `aip-runtime` on brief-013) is that test.
