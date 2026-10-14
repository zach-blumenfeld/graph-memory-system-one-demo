# Source

What `assess-business-loan` was compiled from, how each piece of the source became a step, the rules the
scripts carry, and what was left out on purpose. Compiled 2026-10-13 for AIP format 0.5a1, skill version 1.

## Provenance

- `sop.md`: the Lantern Mutual credit team's page "How we assess a business loan", exported from memory with
  `loan traces export`. Gives the intent: the rules in order, what to pull, the checks, the judgment, the
  write-up, the judgment log.
- `policy.md`: the lending policy as prose (hard rules R1-R6, guidance G1, how the outcome is formed, what the
  assessment may see). Gives the rules the policy engine applies and the inputs the judgment may see.
- `traces.md`: five recorded Claude Code runs of that page with only the `loan` tools and no skill (run-01 hero
  APP-1001, run-02 clean APP-1002, run-03 decline APP-1003, run-04 gray APP-1004, run-05 hero again APP-1001):
  every `loan` call in order with its result, every judgment logged with `loan decide`, the closing summary.
  Gives the real order of operations, the judgment points, the edge cases and the check's bounces.
- The `loan` CLI itself (`loan --help` and every subcommand's `--help`) for the exact flags the scripts call.
- The check's word list for protected characteristics was read from the `loan` source (`policy.py`
  `PROTECTED_WORDS`) and copied into `scripts/loanlib.py`, as the authoring request asked; nothing else was
  taken from the tool's internals.

## How the source became steps

Every trace follows the same shape: read (sop, application, policy, the business views, precedents), judge
(risk tier, connected exposure, outcome, precedents), write and submit, check (and fix), record. Run-01 and
run-05 are the same application; what differed was the order of the reads, how the rationale was worded,
whether the check bounced, and how precedents were handled. The graph fixes the order and keeps the judgment.
13 nodes: 9 working steps, 3 routers, 1 end.

| Source | Step | Kind | Why this kind |
|---|---|---|---|
| SOP "Before you start" (the five things the policy needs); SOP rule 2 "look two hops out"; the reads at the top of every trace; policy "What the assessment may see" | `gather` | execution (`scripts/gather.py`) | Five `loan` reads, the same every run. The two-hop ownership walk is code so it cannot be skipped. Stripping dates of birth, people's names and notes that mention a personal characteristic is a rule over structured data, so it is code too. |
| SOP rule 1 "policy first"; policy "Hard rules", "How the outcome is formed"; `loan policy` as the second or third call in every trace | `hard-rules` | execution (`scripts/hard_rules.py`) | The policy engine is the bank's; the script calls it and removes the one name it returns. |
| Policy "How the outcome is formed": auto_decline, else review, else auto_approve; run-02 and run-03 made no judgment on the outcome | `by-rules` | router on `policy_outcome` | Automatic bands skip the judgment. |
| SOP "The judgment, when the rules leave one": three things, how sure you are; the risk-tier, materiality and outcome judgments in run-01, run-04, run-05 | `assess` | decision | Three questions about one input, answer spaces fixed in advance: `risk_tier` choice low/medium/high, `connected_exposure_material` noul, `outcome` choice approve/counter/decline. Thresholds 0.6 / 0.3 / 0.6 as requested. The instructions and criteria are the traces' reasoning distilled (see below). Declared inputs are exactly the policy's list: figures, fired rules, ownership summary, tenure, KYC status, the filtered notes. |
| SOP "Before you start" on precedents; `loan precedents` in every trace; policy G1; SOP "A decline on a customer of five years or more goes to a human before it is filed" | `precedents` | execution (`scripts/precedents.py`) | One `loan` read plus rules: the automatic outcome, the confidence, the G1 stop, and the evidence digest the rationale is written from. |
| G1; the request's "a human only when the model is unsure" | `by-confidence` | router on `needs_human` | A G1 decline ends the run unfiled with a note. An answer under its threshold has already paused for review on the server; that is the other way a human enters. |
| SOP "The write-up"; SOP rule 3 "only cite what is in the systems"; SOP rule 4; the rationales in every trace; run-01's three bounces | `rationale` | client_task (`assets/rationale.md`) | The one generative step. The template carries the evidence digest with every key, the rules the check enforces, and the three fixes run-01 needed (square-bracket markers, no uncited figure such as the rate, outcome paragraph first). |
| SOP "Submit it, run the check"; `loan rationale submit` then `loan check` in every trace | `check` | execution (`scripts/check.py`) | Two `loan` calls; `check_state` (passed / fix / stop) from the result and the attempt count. |
| SOP "fix what the check names, run it once more" | `gate` | router on `check_state` | passed → record, fix → one fix pass, stop → end unfiled. |
| same; run-01's second and third submissions | `fix` | client_task (`assets/fix.md`) | Revise against the named failures; the failures, the current text and the evidence are in the state. |
| same | `recheck` | execution (same script) | Second submission and check; the script sets `stop` on a second failure so there is no loop. |
| SOP rule 5 "nothing is filed until it has passed the check and the decision has been recorded with its confidence and the procedure revision"; SOP "Judgment calls"; `loan record` and the `loan decide` calls in every trace | `record` | execution (`scripts/record.py`) | `loan record` with the outcome, confidence and this skill's revision, then `loan decide` for the typed judgments and the precedent ruling. |

### What the decision step was written from

- `risk_tier`: run-02 ("coverage 1.90 ... no existing facilities, no delinquency anywhere in the graph, KYC
  current, 7.6 years, a rising 24-month trend. Nothing points to medium"), run-01/05 ("standalone low ...
  raised to medium because a 45% owner holds 60% of a business 90 days late and will run the funded site"),
  run-04 ("coverage 1.15 inside the judgment band and a second site ... not high because every other signal
  is clean"; the seven-day late payment "treat as isolated operational event"). The criteria are those three
  pictures; the instruction says what lifts a tier and what does not.
- `connected_exposure_material`: run-01/05 (three consecutive missed payments, 90 days, the connected
  facility larger than everything the applicant owes, the owner under pressure carries the new project, no
  explanation in the systems; against it a different industry and a minority holder), run-02 and run-04
  ("none to assess": no owner holds another business), run-03 (sole owner, nothing else).
- `outcome`: run-04's approve reasoning (band not breach, ratio gives no credit to the funded site, pre-sales
  and a signed lease, strong liquidity, rising trend, existing loan matures first; a counter would leave the
  fit-out underfunded; a decline has no figure behind it), run-01/05's refusal to approve an unexplained
  connected default and their reasoning that a counter "does not address the risk, which is contagion rather
  than capacity", run-03's "no counter-offer would clear a rule that does not depend on amount or term".
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
  travels as `crm_notes_dropped`; their keys and text do not.
- **Outcome for the automatic bands** (`precedents.py`): auto_approve → approve, auto_decline → decline; a
  decision-step outcome is kept as is.
- **Confidence** (`precedents.py`): 1.0 when the hard rules decided; otherwise 0.6, the `outcome` threshold
  the decision model cleared, because the state carries collapsed answers, not probabilities.
- **needs_human** (`precedents.py`): outcome is decline and G1 is in `guidance` (tenure five years or more).
  The run ends unfiled with `decision_id` "" and a note saying what the human must do.
- **One fix pass** (`check.py`): `attempt` counts submissions; the second failure is `stop` with a note
  listing the failures and what a human must do.
- **Revision** (`record.py`, `loanlib.skill_revision`): `metadata.version` read from `../SKILL.md`; when the
  script sits under `<cache>/<name>@<hash>/<name>/scripts/` the hash is appended: `"1 (a1b2c3...)"`.
- **Judgment log** (`record.py`): `loan decide` for the risk tier and connected-exposure answers when the
  assess step ran, for the outcome always (saying whether the hard rules or the decision model settled it),
  and for the precedent ruling the rationale task returns as `precedents_note`.
- **Evidence digest** (`precedents.py`): every figure in the state with the keys it was computed from, in
  one markdown block the rationale template shows; `cite_keys` is the full list of keys the rationale may
  use. The check rejects any other key or any figure not in the systems.

## Deliberately dropped, with rationale

- **`loan sop` as the first call, `loan --help` and the per-command help.** The page is compiled into this
  skill; the scripts know the flags.
- **The trace prompts and the agents' closing summaries.** Context for the recordings and the agent's own
  report format. The end state carries `outcome`, `needs_human`, `decision_id`, `note` so the consuming agent
  writes its own summary.
- **`--revision freeform` and the agents' self-chosen confidences (0.7, 0.92, 0.95, 0.75).** The revision is
  now this skill's; the confidence is the rule above. The agents' reasons for their numbers ("no precedent
  exists yet", "confident enough not to refer") are not a rule the state can apply.
- **`refer` as an outcome label.** The traces referred twice (run-01, run-05). The request fixes the outcome
  choice to approve / counter / decline; the SOP's "if you are not sure, say so and refer it" is carried by
  the 0.6 threshold on `outcome`, which pauses the run for a human on a close call, and by G1 on a decline.
  A human can still file `refer` by hand (`loan rationale submit --outcome refer`); the procedure does not.
- **Run-04's extra judgments as separate questions** (the five-year lease break against a ten-year term, the
  single seven-day late payment). The SOP names three judgments. Both are folded into the `risk_tier`
  instruction ("a single short late payment with an operational explanation is an isolated event"; an
  expansion lifts the tier) and are visible to the rationale writer through the notes and the facility's
  late-payment rows.
- **The precedent judgment as a typed decision.** Precedents are read after the judgment (they are not an
  input to the risk tier or the outcome in the SOP), and whether one applies is prose reasoning about two
  decisions; it is the rationale writer's call, returned as `precedents_note` and logged with `loan decide`.
- **The `rationale_excerpt` of each precedent** that `loan precedents` returns. A freeform rationale can
  name a person (the run-01 one did), and the comparison the traces made was on the fired rules and outcome,
  which are kept. The rationale writer sees key, application, business, outcome, confidence, rules, revision.
- **Per-month cash-flow rows and per-payment rows.** The averages and the Month keys they cite are kept; the
  payment rows collapse to counts plus the late or missed ones (what run-04 actually used). The rationale cites
  Month keys for the average, as every trace did.
- **The relationship manager's name.** The key `RM-*` stays for citation; the name is a person's.
- **The interest rate as something to quote.** It stays in the application view (`rate`) but is not in the
  evidence digest; run-01 bounced on "8.5%" and the template says not to write it.
- **Shell post-processing in the traces** (`| head -5`, `python3 -I -c ...`), file paths of the agents' drafts
  (`.run/rationale-APP-1001.md`, `rationales/APP-1003.md`). `check.py` writes the text to a temp file; the
  text itself stays in the state.
- **`loan decide` called by the agent at each judgment.** The judgments are typed; `record.py` writes the
  `loan decide` records at filing time. Side effects: on a run that ends unfiled (G1 decline, second check
  failure) nothing is logged, and under the AIP server the records come from a script, not the agent's Bash,
  so recording hooks do not see them.

## Decisions made without asking

- Owners are labelled by position ("owner 1", "owner 2") rather than by share, because two owners can hold
  the same share (Ridgeline, 50/50). Their `PER-*` keys stay in `ownership_summary` so a rationale can cite
  the ownership record without naming anyone; a key is not a name.
- `hard-rules` declares `ownership_summary` as an input only to replace the policy's `connected[].owner`
  name with the owner label; the policy engine itself takes just the application id.
- The automatic bands set `judgment.risk_tier` and `judgment.connected_exposure_material` to "not asked: the
  hard rules decided" so the rationale template and the judgment log say so instead of inventing a tier.
- If a reviewer overrides an under-threshold answer on the server, the confidence filed is still 0.6; the
  state does not say who answered.
- Execution steps carry `timeout: 180`: `loan policy` alone takes about nine seconds against the hosted
  database and `gather` makes five calls (four of them in parallel threads), `record` up to five.
- An empty cite list in the evidence digest renders no marker at all; an early version rendered
  `[cite: none]`, which the check would reject if copied.
- The rationale template asks for plain prose, headings allowed after the first paragraph, no tables: the
  check reads the first paragraph after skipping heading lines.

## Testing

- `aip validate ./skills/assess-business-loan`: clean (one fix on the way: an anti-pattern string containing
  `[cite: KEY]` had to be quoted for YAML).
- Scripts driven by hand against synthetic state (`python3 <script>` with `{"currentState": ...}` on stdin):
  - APP-1001 through gather → hard-rules: no "Priya", "Raghunathan", "Tom Alder", "Dana", "Whitlock", "dob" or
    "(58)" anywhere in the state; NOTE-02 (the age note) withheld, NOTE-01 kept with "owner 1" / "owner 2";
    `connected[].owner` is "owner 2 (45%)"; "Alder Logistics" (a business) kept. With injected answers
    risk_tier medium / material / decline, `precedents` sets needs_human true (G1, 6.0 years), decision_id "",
    confidence 0.6, and a note for the human.
  - APP-1002 through gather → hard-rules → precedents: auto_approve → approve, confidence 1.0, needs_human
    false, no owner or RM names in the state.
  - APP-1003: auto_decline (R1, R2) → decline, confidence 1.0, needs_human false (3.4 years, no G1); the
    sole owner's name absent; NOTE-04 kept (it describes the business's KYC and fraud block, no name).
  - APP-1004 through gather → hard-rules: review on R3; both notes kept; FAC-02's one late payment
    (PAY-02-2025-08, paid seven days after due) is the only row in `late_or_missed_payments`.
  - `check.py` on a rationale with no markers, an uncited "8.5%", no outcome word and the word "age": first
    submission → `fix` with the four failures named; second (attempt 1) → `stop` with the human note.
    `record.py` with `passed: false` refuses. The two throwaway rationale files were deleted afterwards.
    One run of this test exited 2 before any output and did not recur on the next two runs; not explained.
  - Both templates render against a real state with no unrendered placeholders.
- Full local run on `checkpoints/start-app-1002.json`: gather → hard-rules → by-rules → precedents →
  by-confidence → rationale (pause) → check (passed first time, 33 cites) → gate → record → end. Filed
  `DEC-APP-1002-02`, outcome approve, confidence 1.0, revision "1", two judgment calls logged (outcome,
  precedents); `loan precedents APP-1002` now lists it with `skill_revision` "1" beside the freeform
  `DEC-APP-1002-01`. The request said `--interactive`; this session has no terminal for the prompts, so the
  run was started without the flag, paused to `.aip/runs/app-1002.json` at the rationale step, and resumed
  with `aip resume ... --input` carrying the rationale and `precedents_note`. Same steps, same result; a
  terminal session gets the prompts instead.
- Not run here, by request: the other applications through the skill (the plan runs them through the
  server), fresh-agent sessions, and the review band end to end with the decision model (its path was
  exercised with injected answers only).
