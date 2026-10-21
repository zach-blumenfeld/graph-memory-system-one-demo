# Source

What `assess-business-loan` was compiled from, how each piece of the source became a step and why that kind,
the rules the scripts carry, what was left out on purpose, and the decisions made without asking. Compiled
2026-10-21 for AIP format 0.6a1, skill version 1.

## Provenance

- `sop.md`: the Lantern Mutual credit team's page "How we assess a business loan", exported from memory with
  `loan traces export`. Gives the intent: the rules in order, what to pull, the checks, the judgment, the
  write-up, the judgment log.
- `policy.md`: the lending policy as prose (hard rules R1-R6, guidance G1, how the outcome is formed, what the
  assessment may see). Gives the rules the policy engine applies and the inputs the judgment may see.
- `traces.md`: five recorded Claude Code runs of that page with only the `loan` tools and no skill (run-01 hero
  APP-1001, run-02 clean APP-1002, run-03 decline APP-1003, run-04 gray APP-1004, run-05 hero again APP-1001):
  every `loan` call in order with its result, every judgment logged with `loan decide`, the closing summary.
  Gives the real order of operations, the judgment points, the edge cases and the check's rejections.
- The `loan` CLI itself (`loan --help` and every subcommand's `--help`) for the exact flags the scripts call.
- The check's word list for protected characteristics was copied into `scripts/loanlib.py` from the authoring
  request (it is the list `loan check` uses); nothing else was taken from the tool's internals.

## How the source became steps

Every trace follows the same shape: read (application, policy, the business views, precedents), judge (risk
tier, connected exposure, outcome, precedents), write and submit, check (and fix), record. Run-01 and run-05
are the same application; what differed was the order of the reads, how the rationale was worded, and how
precedents were handled. The graph fixes the order and keeps the judgment. 11 nodes: 7 working steps, the
`gate` router with its `fix` and `recheck` sub-steps, and `end`.

| Source | Step | Kind | Why this kind |
|---|---|---|---|
| SOP "Before you start" (the five things the policy needs); SOP rule 2 "look two hops out"; the reads at the top of every trace; policy "What the assessment may see" | `gather` | execution (`scripts/gather.py`) | Five `loan` reads, the same every run. The two-hop ownership walk is code so it cannot be skipped. Stripping dates of birth, people's names and notes that mention a personal characteristic is a rule over structured data, so it is code too. |
| SOP rule 1 "policy first"; policy "Hard rules", "How the outcome is formed"; `loan policy` as the second or third call in every trace | `hard-rules` | execution (`scripts/hard_rules.py`) | The policy engine is the bank's; the script calls it and replaces the one person's name it returns with an owner label. |
| SOP "The judgment, when the rules leave one": three things, how sure you are; the risk-tier, materiality and outcome judgments in run-01, run-04, run-05; the risk-tier and materiality judgments run-02 and run-03 logged on automatic bands too | `assess` | decision | Three questions about one input, answer spaces fixed in advance: `risk_tier` choice low/medium/high, `connected_exposure_material` noul, `assessed_outcome` choice approve/counter/decline. Thresholds 0.6 / 0.3 / 0.6 as requested. The instructions and criteria are the traces' reasoning distilled (below). Declared inputs are exactly the policy's list: figures, fired rules, ownership summary, tenure, KYC status, the filtered notes. Runs on every band; see "Decisions made without asking". |
| SOP "Before you start" on precedents; `loan precedents` in every trace; policy "How the outcome is formed"; G1; SOP "A decline on a customer of five years or more goes to a human before it is filed" | `precedents` | execution (`scripts/precedents.py`) | One `loan` read plus rules: the outcome (the policy's where a hard rule decided, the assessment's where it said review), the confidence, the G1 flag, and the evidence digest the rationale is written from. |
| SOP "The write-up"; SOP rule 3 "only cite what is in the systems"; SOP rule 4; the rationales in every trace; the three rejections run-01 reported | `rationale` | client_task (`assets/rationale.md`) | The one generative step. The template carries the evidence digest with every key, the rules the check enforces, and the fixes run-01 needed (square-bracket markers, no uncited figure such as the rate, outcome paragraph first). It also returns the precedent ruling for the judgment log. |
| SOP "Submit it, run the check"; `loan rationale submit` then `loan check` in every trace | `check` | execution (`scripts/check.py`) | Two `loan` calls; `check_state` (passed / fix) from the result. |
| SOP "fix what the check names, run it once more" | `gate` | router on `check_state` | passed → record, fix → one fix pass. |
| same | `fix` | client_task (`assets/fix.md`) | Revise against the named failures; the failures, the current text and the evidence are in the state. |
| same | `recheck` | execution (same script) | Second submission and check; the script sets `recheck_state` stop on a second failure so there is no loop, and `record` then leaves the decision unfiled. |
| SOP rule 5 "nothing is filed until it has passed the check and the decision has been recorded with its confidence and the procedure revision"; SOP "Judgment calls"; `loan record` and the `loan decide` calls in every trace; G1 | `record` | execution (`scripts/record.py`) | `loan decide` for the typed judgments and the precedent ruling, then `loan record` with the outcome, confidence and this skill's revision, unless a G1 decline waits for a human or the rationale never passed. |

### What the decision step was written from

- `risk_tier`: run-02 ("coverage 1.9, 7.6 years, no existing facilities and so no payment history to fault, KYC
  current, no connected businesses, twelve-month average above the twenty-four-month average. Nothing moves it
  off low"; the third chair is demand-led, the old run rate alone covers the payment), run-01/05 ("on its own the
  business is low risk ... medium because a 45% owner holds 60% of a business 90 days late and will run the new
  site"), run-04 ("coverage 1.15 inside the judgment band ... a fit-out on leased premises, a lease break inside
  the term, execution risk of a second site; not high because every other test is clean"; the seven-day late
  payment with the card-terminal note "is conduct noise, not a credit signal"), run-03 ("high because the
  operating account was blocked by the fraud team, KYC overdue, two unanswered refresh requests"). The criteria
  are those pictures; the instruction says what lifts a tier and what does not. The first local test paused for
  review because the model read the third chair as an expansion that lifts the tier (low 0.66 / medium 0.34);
  the instruction now says an expansion the existing cash flow already covers leaves the tier low, which is
  run-02's reasoning, and the second test cleared the threshold (risk_tier 1.0).
- `connected_exposure_material`: run-01/05 (three consecutive missed payments, 90 days, 300,000 of the 820,000
  exposure, the owner under pressure will run the funded site, no explanation in the systems), run-02 and run-04
  (no owner holds another business, so nothing to assess), run-03 (sole owner, nothing else).
- `assessed_outcome`: run-04's approve reasoning (band not breach, the ratio gives no credit to the second site,
  pre-sold memberships and a signed lease, balances of about two years of payments, a shorter term worsens the
  flagged ratio and a smaller amount leaves the fit-out underfunded), run-01/05's refusal to approve an
  unexplained connected default and their reasoning that a counter "does not address the connected risk, which
  is about the owner not the applicant's coverage", run-03's "a counter is still a credit extension and is barred
  by the same rules" and run-02's "nothing argues for a smaller amount or a human read". The SOP's "do not argue
  with a hard rule" is the opening of the instruction: where a hard rule decided, the answer is the policy's.
  The SOP's "if you are not sure, say so and refer it" is the threshold: a close call pauses for a human.

## Rules the scripts carry

- **Two hops out, every run** (`gather.py`): `loan ownership` is called unconditionally; the summary lists
  every business an owner holds 25% or more of, with its facilities, days late and missed payments, and
  totals `connected_exposure` and `connected_worst_late_days`.
- **What the judgment step cannot see** (`loanlib.py`): keys `dob`, `date_of_birth`, `birth_date`,
  `birthdate`, `requested_by` are removed anywhere in a tool result; `name` is removed from any person or
  relationship-manager record (key `PER-*` / `RM-*`); the policy's `connected[].owner` is replaced by the
  owner label; every remaining string has full names and first names replaced by role labels ("owner 1",
  "owner 2" in ownership order, "the relationship manager"). Surnames on their own are not replaced because
  an owner's surname can be part of the name of the business they hold (Alder / Alder Logistics). A CRM note
  is dropped if it matches the check's word list (dob, date of birth, born, years old, aged, age, sex,
  gender, ethnicity, race, religion, national origin, nationality, marital, married, divorced, disability,
  pregnant, with the same variants `loan check` matches) or if it records an age the way the annual-review
  note does, a person's name followed by a bracketed number ("Priya (58)"). The count of withheld notes
  travels as `crm_notes_dropped`; their keys and text do not. The 0.6a1 runtime also projects the state to the
  decision step's six declared inputs, so the raw views never reach the model either way; the run history of
  the local test confirms the `assess` input held no name.
- **Outcome** (`precedents.py`): auto_approve → approve, auto_decline → decline, whatever the decision model's
  `assessed_outcome` was (it is recorded in `judgment` and logged); review → `assessed_outcome` as is.
- **Confidence** (`precedents.py`): 1.0 when the hard rules decided; otherwise 0.6, the `assessed_outcome`
  threshold the decision model cleared, because the state carries collapsed answers, not probabilities.
- **needs_human** (`precedents.py`): outcome is decline and G1 is in `guidance` (tenure five years or more).
- **One fix pass** (`check.py`): `attempt` counts submissions; the second failure is `stop`. The script knows
  it is the recheck because `rationale_fixed` is in its input, and then prefixes its outputs with `recheck_`.
- **Check → record handoff** (`loanlib.py`): each check writes the latest submission's id and result to
  `$AIP_WORKDIR/.run/assess-business-loan/<application_id>.check.json`. `record` reads it only when the first
  check did not pass, requires `attempt` 2, and exits non-zero if it is missing.
- **Filing** (`record.py`): `loan record` only when `needs_human` is false and the latest check passed;
  otherwise `decision_id` is "" and the note says exactly what the human must do, including the `loan record`
  command that files the checked rationale if they agree. `loan record` itself refuses a rationale that has not
  passed the check, so nothing can be filed around this rule.
- **Revision** (`loanlib.skill_revision`): `metadata.version` from `../SKILL.md` on a local folder run; on a
  published run only `scripts/` and `assets/` are in `~/.aip/cache/<name>@<hash>/`, so the hash after `@` in the
  script folder's parent name is passed. Tested on both layouts ("1" and the hash).
- **Judgment log** (`record.py`): four `loan decide` calls, one question each (the `--options` flag is a plain
  comma split, run-03's lesson): risk tier, connected exposure material, outcome (saying whether the hard rules
  or the decision model settled it, and what the assessment's own reading was), and the precedent ruling the
  rationale task returns. Logged whether or not the decision is filed: the judgments were made.
- **Evidence digest** (`precedents.py`): every figure in the state with the keys it was computed from, in one
  markdown block the rationale template shows; `cite_keys` is the full list of keys the rationale may use. The
  check rejects any other key or any figure not in the systems. An empty cite list renders no marker (a
  `[cite: none]` would fail the check).

## Deliberately dropped, with rationale

- **`loan sop` as the first call, `loan --help` and the per-command help.** The page is compiled into this
  skill; the scripts know the flags.
- **The trace prompts and the agents' closing summaries.** Context for the recordings and the agent's own
  report format. The end state carries `outcome`, `needs_human`, `decision_id`, `note` so the consuming agent
  writes its own summary.
- **`--revision freeform` and the agents' self-chosen confidences (0.7, 0.9, 0.95, 0.7, 0.75).** The revision
  is now this skill's; the confidence is the rule above. The agents' reasons for their numbers ("no precedent
  exists yet", "confident enough not to refer") are not a rule the state can apply.
- **`refer` as an outcome label.** The traces referred twice (run-01, run-05). The request fixes the outcome
  choice to approve / counter / decline; the SOP's "if you are not sure, say so and refer it" is carried by the
  0.6 threshold on `assessed_outcome`, which pauses the run for a human on a close call, and by G1 on a decline.
  A human can still file `refer` by hand (`loan rationale submit --outcome refer`); the procedure does not.
- **Run-04's extra judgments as separate questions** (the five-year lease break against a ten-year term, the
  single seven-day late payment, counter versus full amount). The SOP names three judgments. All three are
  folded into the `risk_tier` and `assessed_outcome` instructions and are visible to the rationale writer
  through the notes and the facility's late-payment rows.
- **Run-02's "accept the auto-approve or counter or refer anyway" and run-03's "file as decline, refer or
  counter" as separate questions.** They are the `assessed_outcome` question on an automatic band: the model
  answers it, the policy's outcome stands, and the log records whether the two agreed.
- **The precedent judgment as a typed decision.** Precedents are read after the judgment (they are not an
  input to the risk tier or the outcome in the SOP), and whether one applies is prose reasoning about two
  decisions; it is the rationale writer's call, returned as `precedents_ruling` and `precedents_note` and
  logged with `loan decide`.
- **The `rationale_excerpt` of each precedent** that `loan precedents` returns. A freeform rationale can name a
  person, and the comparison the traces made was on the fired rules and outcome, which are kept.
- **Per-month cash-flow rows and per-payment rows.** The averages and the Month keys they cite are kept; the
  payment rows collapse to counts plus the late or missed ones (what run-04 actually used).
- **The relationship manager's name.** The key `RM-*` stays for citation; the name is a person's.
- **The interest rate as something to quote.** It stays in the application view (`rate`) but is not in the
  evidence digest; run-01's first submission was rejected for "8.5%" and the template says not to write it.
- **Shell post-processing in the traces** (`| head -8`, `2>&1`), file paths of the agents' drafts. `check.py`
  writes the text to a temp file; the text itself stays in the state.
- **`loan decide` called by the agent at each judgment.** The judgments are typed; `record.py` writes the
  `loan decide` records at filing time. Under `aip` they come from a script, not the agent's shell, so Claude
  Code recording hooks do not see them.
- **Run-01's "the submit help lists review but only accepts refer" and run-05's "did not cite the annual review
  note because it carries an age".** The first is moot (the procedure never submits review or refer); the
  second is code in `gather.py`.

## Decisions made without asking

The authoring request describes a 0.5a1-shaped graph (merge semantics, keys overwritten, every step seeing
the whole state). Format 0.6a1 enforces three rules the validator and the runtime both apply: a step sees
only its declared inputs; every key has exactly one producer; every consumed key must be produced on every
path to its consumer. Three parts of the requested graph cannot exist under those rules, and were changed:

1. **`assess` runs on every band; `by-rules` is gone.** Requested: auto_approve and auto_decline skip the
   judgment and rejoin at `precedents`, which "keeps a decision-step outcome as is". Under 0.6a1 nothing after
   a join may read a key produced on one branch only, so `precedents`, `rationale`, `record` and `end` could
   never see the judgment, and `outcome` could never reflect it. The only producer that can see the judgment
   and feed every path is the decision step itself on every path. The traces support this: run-02
   (auto_approve) and run-03 (auto_decline) both logged a risk tier and a materiality judgment. The hard
   rules still decide: the question is named `assessed_outcome` (it cannot share the name `outcome` with the
   key `precedents` produces), its instructions say the policy's outcome is the answer where a hard rule fired
   or nothing fired, and `precedents.py` overrides it with the policy's outcome for the automatic bands
   regardless. Cost: one decision-model call per run on the automatic bands, and a possible review pause there
   if the model hedges (the APP-1002 test did not: 1.0 / 0.93 / 0.97).
2. **`by-confidence` is gone; `record` is on every path.** Requested: `needs_human` true ends the run unfiled
   from `precedents`. Under 0.6a1 `decision_id` and `note` at `end` need one producer on every path; if a path
   ends before `record`, `record` cannot be that producer and the end state could never carry a real decision
   id. So every run writes and checks its rationale, and `record.py` is where "a human before filing" happens:
   with `needs_human` true it logs the judgments, files nothing, and the note gives the human the checked
   rationale id and the exact `loan record` command. The human gets a checked draft instead of nothing, which
   is what run-01 produced for its referral. Same for a rationale that failed twice: `recheck` feeds `record`,
   which files nothing and says what to fix.
3. **`recheck` has its own output names and hands its result to `record` through the run's working
   directory.** Requested: `recheck` reuses the check script and feeds `gate` again. Under 0.6a1 it cannot
   re-produce `rationale_id`, `check_state` and so on, so it produces `recheck_*` keys, and `gate` has only
   `passed` and `fix` (a first check cannot `stop`). `record` can only declare keys produced on both of its
   incoming paths, which are the first check's; the second submission's id and result travel through
   `$AIP_WORKDIR/.run/assess-business-loan/<application_id>.check.json`, the directory the runtime names as the
   place for a run's files. The state still records both ids (`rationale_id`, `recheck_rationale_id`) and
   `record` adds `filed_rationale_id`, so the history shows which write-up was filed.

Other decisions:

- Owners are labelled by position ("owner 1", "owner 2") rather than by share, because two owners can hold
  the same share (Ridgeline, 50/50). Their `PER-*` keys stay in `ownership_summary` so a rationale can cite the
  ownership record without naming anyone; a key is not a name.
- `hard-rules` declares `ownership_summary` as an input only to replace the policy's `connected[].owner` name
  with the owner label; the policy engine itself takes just the application id.
- The automatic bands' `judgment` carries the model's `assessed_outcome` and `assessment_agrees_with_policy`
  so the rationale template and the judgment log say whether the two agreed instead of inventing a tier.
- Execution steps carry `timeout: 180`: `loan policy` alone can take several seconds against a hosted
  database and `gather` makes five calls (four of them in parallel threads), `record` five.
- The judgments are logged even when nothing is filed (G1 decline, second check failure).
- If a reviewer overrides an under-threshold answer, the confidence filed is still 0.6; the state does not
  say who answered.

## Functional test (2026-10-21, local folder run, headless)

No terminal, so no `--interactive`: `aip run ./skills/assess-business-loan --input checkpoints/start-app-1002.json`
pauses to a run file; `aip resume <run_id> --input answer.json` answers it.

- First run (e13e4b8f38d04953) paused at `assess` for a review: `risk_tier` low 0.66 / medium 0.34, confidence
  0.49 under the 0.6 threshold. The criteria were sharpened as described above; that run file is left paused.
- Second run (fd43ec9d1dc843a9): gather → hard-rules → assess (typesafe, jev-1.13.0, risk_tier low 1.0,
  connected_exposure_material false 0.93, assessed_outcome approve 0.97, no review) → precedents → paused at
  `rationale`; answered with a rationale citing 32 records → check passed first time (RAT-APP-1002-02) → gate →
  record → end. Filed DEC-APP-1002-02, approve, confidence 1.0, revision "1", 4 judgment calls logged. The
  `assess` history entry holds only the six declared keys and no person's name. `loan precedents APP-1002` now
  lists DEC-APP-1002-01 (freeform) and DEC-APP-1002-02 (revision 1).
- Offline, with the scripts alone: a rationale with no cites and the wrong outcome word gives `check_state`
  fix with the check's four failures; the recheck on still-bad text gives `recheck_state` stop; `record.py`
  on that path files nothing and names the failures; with `needs_human` true it files nothing and gives the
  human the `loan record` command; with `check_state` fix and no handoff it exits non-zero. These test
  submissions (RAT-APP-1002-03, -04) were deleted from `.run/rationales/` afterwards. No other application was
  run through the skill.

## Revision 2 (2026-10-21): a fired rule with effect `human`

The compliance officer added R7, `connected_exposure_cap`: connected exposure over $250,000 always goes to a
human; it is never decided by the procedure alone. The bank's policy engine reports it as a fired rule with
effect `human` once the rule row exists in the compliance system (`loan import --rules-only`). Revision 1
would see it fire and file anyway, since `needs_human` was only G1. Revision 2 changes `precedents.py`
(`needs_human` is also true when any fired rule has effect `human`, and the evidence digest says so) and
`record.py` (the not-filed note names the rule and what the human must do). `SKILL.md` `metadata.version`
is "2" and the `precedents` and `record` descriptions say it. Nothing else changed; the graph is the same
eleven nodes.
