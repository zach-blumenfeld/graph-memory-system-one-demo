Use the `aip` skill to author an AIP skill named `launch-email-blast` in the folder `./skills/launch-email-blast/`.
The folder already exists with `source/` filled in: `source/sop.md` is the marketing team's own page on
how an email blast is done, and `source/traces.md` is what an agent actually did when it followed that
page four times (every tool call in order with its result, every judgment call it logged, its closing
summary). Compile the procedure from both: the SOP gives the intent and rules, the traces give the real
order of operations, the judgment points, and the edge cases (a digest is not scheduled; an urgent hotfix
goes the same day; claims not on the approved list are dropped; legal-sensitive briefs are flagged).

Constraints for this skill:
- Start input: `brief_id` (string) and `send_at` (string, ISO time; empty means "use the brief's send
  window at 09:00 UTC").
- Scripts (`execution` steps) may call the `blast` command, which is on PATH where the server runs. It is
  the only way to reach the Notion data, drafts, scheduling and the log. `blast brief <id>`,
  `blast product <name>`, `blast segments <product>`, `blast brand` return JSON; `blast draft <campaign_id>
  --body-file F --subject S --subject S --subject S --segment SEG` stores a draft and returns its id;
  `blast check <draft_id>` returns `{passed, failures[]}`; `blast schedule <draft_id> --segment SEG --at T
  --subject S` schedules (refuses unchecked drafts); `blast log <campaign_id> --draft D --summary TEXT
  [--scheduled]` logs. Run `blast --help` to confirm. Keep scripts thin: call `blast`, shape the state.
- The judgment calls in the traces become `decision` steps answered by the decision model: what kind of
  email (choice), how urgent (score), whether legal must review (noul), which subject line to send
  (choice over first/second/third). Put every question about the same input in one decision step and
  set thresholds. Segment selection is a rule in the SOP, so make it a script, not a decision.
- Routers: a legal flag ends the run with a note for a human instead of scheduling; a digest/nurture
  email is logged but never scheduled; a draft that fails the compliance check gets exactly one
  `client_task` fix-up pass and a recheck, then the run ends either way (no loops).
- Writing the email is a `client_task`: three subject lines and a markdown body, with the brand guide,
  approved claims and persona in the state. Keep the procedure to about ten steps.
- Validate with `aip validate ./skills/launch-email-blast` until clean. Then test it locally once with
  `aip run ./skills/launch-email-blast --input start.json` using `{"brief_id": "brief-003", "send_at": ""}`,
  answering the client task yourself, and fix whatever breaks. `TYPESAFE_API_KEY` is in `.env` (load it
  with `set -a; . ./.env; set +a` before `aip run`).
- Write `source/README.md` as the skill asks: provenance and the log of what was deliberately dropped.
Do not ask questions; decide and note the decision in `source/README.md`. Finish with a short summary.
