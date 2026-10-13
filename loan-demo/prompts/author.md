Use the `aip` skill to author an AIP skill named `assess-business-loan` in the folder
`./skills/assess-business-loan/`. The folder already exists with `source/` filled in: `source/sop.md` is the
credit team's own page on how a business loan is assessed, `source/policy.md` is the lending policy (rules
R1–R6 and guidance G1) as prose, and `source/traces.md` is what an agent actually did when it followed that
page five times (every `loan` call in order with its result, every judgment call it logged, its closing
summary; run-01 and run-05 are the same application, so their differences are differences in the agent's
path, not the input). Compile the procedure from all three: the SOP gives the intent, the policy gives the
rules, the traces give the real order of operations, the judgment points, and the edge cases.

Constraints for this skill:

- Start input: `application_id` (string), e.g. `APP-1002`.
- Scripts (`execution` steps) may call the `loan` command, which is on PATH where the server runs. It is the
  only way to reach the bank's systems and the memory graph. Scripts run under the aip server's own Python
  with the standard library only: no `loan` package import, call `loan` with `subprocess` and parse its JSON.
  `loan application <id>`, `loan ownership <business>`, `loan facilities <business>`, `loan cashflow
  <business>`, `loan kyc <business>`, `loan policy <application>`, `loan precedents <application>` return
  JSON; `loan rationale submit --file F --application ID --outcome O` stores a write-up and returns its id;
  `loan check <rationale_id>` returns `{passed, failures[], cites[]}`; `loan record <rationale_id> --outcome O
  --confidence C --revision R` files the decision and returns `{decision_id, ...}` (it refuses an unchecked
  rationale); `loan decide --question Q --options a,b --answer A --why W` logs a judgment call. Run
  `loan --help` and each subcommand's `--help` to confirm. Keep scripts thin: call `loan`, shape the state.
  Favour one shared helper module plus one script per execution step.
- Exactly nine working steps, these names and kinds, in this order:
  1. `gather` (execution): application, ownership two hops out (every run, it is code), facilities, cash
     flow, KYC. Every figure keeps the node keys it was computed from. It strips from the state anything the
     judgment step must never see: dates of birth (the tools never return them, strip anyway), the names of
     people (owners appear as shares and business names only in `ownership_summary`), and any CRM note that
     mentions a personal characteristic (use the same word list `loan check` uses: dob, date of birth, born,
     years old, aged, age, sex, gender, ethnicity, race, religion, national origin, nationality, marital,
     married, divorced, disability, pregnant; copy it into the helper). Produces `ownership_summary`,
     `tenure_years`, `kyc_status`, `crm_notes` (filtered) and the raw views.
  2. `hard-rules` (execution): `loan policy`. Produces `policy_outcome` (auto_approve | auto_decline |
     review), `fired`, `guidance`, `figures`, `cites`.
  3. `by-rules` (router on `policy_outcome`): auto_approve → precedents, auto_decline → precedents, review → assess.
  4. `assess` (decision): three questions about one input: `risk_tier` (choice: low, medium, high),
     `connected_exposure_material` (noul), `outcome` (choice: approve, counter, decline). Thresholds 0.6 /
     0.3 / 0.6. It declares exactly these inputs: `figures`, `fired`, `ownership_summary`, `tenure_years`,
     `kyc_status`, `crm_notes` (the filtered ones). It must not declare or receive `owners[].dob`, names of
     people, or anything from CRM notes that mentions personal characteristics. Write the instructions and
     criteria from the SOP's "The judgment" section and the traces' judgment calls.
  5. `precedents` (execution): `loan precedents`. Also settles the outcome for the automatic bands
     (auto_approve → `outcome` approve, auto_decline → `outcome` decline; a decision-step outcome is kept as
     is), sets `confidence` (1.0 when the hard rules decided; otherwise the `outcome` threshold the decision
     model cleared, 0.6, since the state carries collapsed answers, not probabilities), and computes
     `needs_human` (boolean): true when the outcome is decline and G1 is in `guidance` (a decline on a
     customer of five years or more goes to a human before filing). Sets a `note` string.
  6. `by-confidence` (router on `needs_human`): `"true"` → end (the run ends unfiled with the note saying what
     the human must do), `"false"` → rationale. (A decision answered under its threshold pauses on the
     server for a review anyway; that is the other way a human enters.)
  7. `rationale` (client_task, template `assets/rationale.md`): the one generative step. It must state the
     outcome in the first paragraph, mark every figure and fact with `[cite: KEY]` using the keys in the
     state (several keys may be comma-separated inside one marker), quote only figures that are in the state,
     name the precedents it leaned on, and never mention a person's name or any personal characteristic.
     Produces `rationale` (markdown string).
  8. `check` (execution): write the rationale to a temp file, `loan rationale submit`, `loan check`. Produces
     `rationale_id`, `passed`, `failures`, `attempt`, `check_state` (passed | fix | stop). One fix pass, no
     loops: a `gate` router on `check_state` (passed → record, fix → `fix`, stop → end), a `fix` client_task
     (template `assets/fix.md`: fix exactly what the check named) and a `recheck` execution step reusing the
     same script that sets `stop` on a second failure. `fix`, `gate` and `recheck` count as sub-steps of check.
  9. `record` (execution): `loan record <rationale_id> --outcome <outcome> --confidence <confidence>
     --revision <revision>`. The revision is read from this skill's own `SKILL.md` frontmatter
     (`metadata.version`, resolve the file relative to the script: `../SKILL.md`); when the server runs the
     skill the script's folder sits under `<cache>/<name>@<revision-hash>/<name>/scripts/`, so also pass the
     hash as part of the revision when it is there (`"2 (a1b2c3...)"`), else just the version. Also logs the
     typed judgment calls with `loan decide` (risk tier, connected exposure material, outcome) so the SOP's
     "log every judgment call" holds. Produces `decision_id` and the final `note`.
  Then `end`: `application_id`, `outcome`, `needs_human`, `decision_id` (empty string when nothing was filed),
  `note`. Every path to `end` must leave those keys in the state.
- Set `metadata.version: "1"` in the frontmatter and `metadata.author: lantern-mutual-credit`.
- No regulation names anywhere. Say "when you decline someone you owe them a reason", "the judgment step
  cannot see protected characteristics", "every decision is auditable".
- Validate with `aip validate ./skills/assess-business-loan` until clean. Then test it locally once with
  `aip run ./skills/assess-business-loan --input checkpoints/start-app-1002.json --interactive`, answering
  the client task yourself, and fix whatever breaks; the run must end with a filed decision (`decision_id`
  starting `DEC-APP-1002`). `TYPESAFE_API_KEY` is in `.env` (load it with `set -a; . ./.env; set +a` before
  `aip run`). Do not run other applications through the skill; the plan runs them through the server later.
- Write `source/README.md` as the skill asks: provenance (which SOP paragraph, policy rule or trace pattern
  became which step and why that kind), the rules the scripts carry, and the log of what was deliberately
  dropped with rationale.
Do not ask questions; decide and note the decision in `source/README.md`. Finish with a short summary.
