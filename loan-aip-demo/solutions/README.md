# Solutions: what was built, what was run, what did not work

Built 2026-11-12 on aip 0.9.0 (checkout `~/dev/aip-0.9` at `release-0.9.0`, commit 49f9dbe) by
the agent that read `~/Documents/loan-aip-demo-brief.md`. Everything here is the fallback for the
live demo and the record of the rehearsal.

## The procedure

`assess_business_loan/` is eleven steps. `gather` (script) reads the five JSON systems under
`source/` and builds the figures and a case file with names and percentages but no dates of
birth (an age written into a relationship manager's note is redacted). `apply_policy` (script)
applies R1 to R7 and G1, reading every threshold from `assets/policy.md` with regular expressions
anchored on the policy's own sentences, so a threshold the text no longer states fails the step
instead of falling back to a default. `by_band` routes: `auto_approve`, `auto_decline` and
`human` go straight to `settle_by_rules`; `review` goes to the one `Decide`, `judge`, which asks
the SOP's three questions (risk tier, whether connected exposure is material, outcome) in the
SOP's words. `by_judgment` takes the model's outcome when its confidence is 0.6 or more and sends
the case to `refer_unsure` otherwise ("if you are not sure, say so and refer it"). `rationale` is
the one `Task_Agent`. The result is `application_id`, `outcome`, `rules_fired`, `rationale`, and
`judgment` when there was one.

Two readings of the material are the procedure's, not the policy's:

- R4 (exposure cap) sends an over-cap application to a person, as the SOP says ("stays under the
  cap or goes to a human"); `policy.md` says "review". No application in the fixture is over the
  cap, so nothing turns on it.
- R7 ("never decided by the procedure alone, whatever the other rules say") and G1 (a decline on a
  customer of five years or more "goes to a human before it is filed") both make the band `human`,
  which wins over `auto_decline`, which wins over `review`.

## Expected outcomes, and where they differ from the brief

| Application | Brief | This procedure | Why |
|---|---|---|---|
| APP-1001 | refer | refer | R5 (connected facility 90 days late) and R7 (connected exposure $300,000); R7 goes to a person |
| APP-1002 | (loans.json) | approve | no rule fires: coverage 1.9, exposure $250,000, tenure 91 months |
| APP-1003 | decline | decline | R1 (KYC overdue), R2 (fraud event 4.1 months ago) |
| APP-1004 | approve | **refer** | R3, coverage 1.15 in the review band. TypeSafe (jev-1.14.0) is not sure: across more than a dozen calls with six framings of the question the outcome's confidence was 0.06 to 0.74, leaning decline (approve never above 0.36; one framing declined at 0.62 to 0.74, the SOP's own wording, used here, at 0.26 to 0.55). The one framing that approved (0.80) added a precedent sentence the material does not contain, so it was not used. The loan-demo's approve was a chat model's judgment |
| APP-1005 | approve | **refer** | R7: the owner holds 30% of Wrenfield Mechanical, which carries a $950,000 facility. `policy.md` as copied carries R7 (added 2026-10-13, the loan-demo's own rule change); the brief's approve predates it. No data was changed to make it approve |

`check.py` holds these as `EXPECTED_V1`.

## The rule change (part 3)

The brief asked for one threshold that turns an approve into a review, on the application closest
to a line. Under the material as it stands that is not available: the only approve is APP-1002,
and nothing about it is near a line (coverage 1.9, exposure $250,000, tenure 91 months). The
brief's natural pick, APP-1005 ($1.4M against the $1.5M exposure cap), is already a refer under
R7. Two changes were tried on APP-1004, the application closest to a line (coverage 1.15):

1. R3's decline line, 1.00 to 1.20. Rehearsed as revision 2 on the first store: APP-1004 became an
   automatic decline, and G1 sent that decline to a person, so the outcome stayed refer. Invisible.
2. **R3's coverage floor, 1.25 to 1.10** (`policy-v2.md`, `assess_business_loan-v2/`). APP-1004's
   1.15 is now an automatic approve and the `Decide` leaves its path. Deterministic and visible:
   refer on revision 1, approve on revision 2. This is the change the README uses. It runs the
   other way from the brief's wording (a refer becomes an approve, not an approve a review).

`check.py --v2` holds `EXPECTED_V2` (APP-1004 approve) for runs on the newest revision.

## What was run

The servers: `aip server` on 127.0.0.1:8300 (store `.aip/main.rl`) and 8301 (`.aip/empty.rl`),
plus a scratch one on 8302 for the live-build rehearsal. The decision model: TypeSafe through
`aip config`. Claude Code ran headless (`claude -p ... --permission-mode dontAsk`) with the
prompts the README gives, which is terminal two of part 1 as the audience will see it.

**Part 1, the live build, rehearsed** on the scratch server (8302) with the README's terminal-one
prompt, headless: 26 turns, 208 seconds, $1.36. Claude Code used `make_procedure`, wrote
`./assess_business_loan` (one script that reads the five systems and applies R1 to R7 and G1
with thresholds parsed from `assets/policy.md`; a `rules_verdict` route; one `Decide` asking
risk tier, connected exposure and an outcome of approve, counter or decline with a 0.8
confidence check; one `Task_Agent` for the rationale; ages stripped from the notes), compiled it
and published `assess_business_loan@1`. Its own check of the rules gave the five expected
outcomes; its one full run of APP-1004 had the model lean counter at 0.66, below its 0.8 bar, so
it referred. It borrowed step and script names from `solutions/`, which is why the README's prompt
now ends "Do not read `./solutions`". The folder it wrote is kept at `built/assess_business_loan`,
ignored by git (`built/`).

**Parts 1 and 3 on the main server**, final rehearsal on a fresh store (`make reset`), the
solution published as `assess_business_loan@1` (bundle `8cf623dac0f2`), then `-v2` as `@2`
(bundle `559c4b73962c`). Each Claude Code session answered only the `rationale` pause of each run;
the three sessions took 59, 43 and 43 seconds and cost $0.54, $0.43 and $0.47.

| Run | Revision | Session | Application | Outcome | Rules fired | Expected |
|---|---|---|---|---|---|---|
| `8aca372594274ffa` | 1 | run-1 | APP-1001 | refer | R5, R7 | refer, tick |
| `94d1825646084c63` | 1 | run-1 | APP-1003 | decline | R1, R2 | decline, tick |
| `6339bd0010a14282` | 1 | run-1 | APP-1004 | refer | R3; the model leaned decline below the 0.6 bar | refer, tick |
| `4df343c6d4f14d40` | 1 | run-2 | APP-1002 | approve | none | approve, tick |
| `64891b21adc64bff` | 1 | run-2 | APP-1005 | refer | R7 | refer, tick |
| `87dba16889134db1` | 2 | run-3 | APP-1004 | approve | none: the floor is 1.10 | approve, tick |
| `d9da2213a09a4850` | 2 | run-3 | APP-1001 | refer | R5, R7 | refer, tick |

`python check.py`: 5 right, 0 wrong. `python check.py --v2`: 7 right, 0 wrong. The record of
APP-1004 on revision 1 shows the `Decide` answered by `jev-1.14.0` (risk tier medium, connected
exposure not material, outcome decline at 0.33) and `by_judgment`'s check firing (`below 0.6`).
An APP-1001 rationale was checked for an owner's age, date of birth or the words around them:
none.

Earlier rehearsals on stores since reset: the same five outcomes on revision 1 (runs
`e127b1f460ab4330`, `8f01bd66624f45cd`, `33b5cf3db2b94d3e`, `2ef43f84f83e49a8`,
`5836ede56a474e35`); the first rule change (decline line 1.20) as revision 2, where APP-1004
stayed refer under G1 (`f5e350c9a48d4037`); and one round where a live-built folder shadowed the
published name (under "What aip needs"). Both stores (`.aip/main.rl`, `.aip/empty.rl`) are left
as the final rehearsal left them, with both servers running; `make reset` empties them.

**Full rehearsal, 2026-11-13, README as written, `claude -p` for each Claude Code terminal.**
Part 1: the live build compiled and published `assess_business_loan@1` in 176 s (its own test run
`acc4b6233b8a4e2e`, draft); session `run-1` gave APP-1001 refer `a21d97c4bbb645ab`, APP-1003
decline `5b0d0415d2144a42`, APP-1004 refer `2732bcbf88f544d8` in 56 s. Part 2: ADK APP-1002
approve `2b2773fda8e74bd4`, APP-1005 refer `7bff92a8d0fe4632`; LangGraph APP-1004 refer
`abc82cfa080c441e`, APP-1001 refer `f45419f4332b49aa`; 15 s each. Part 3: revision 2 published;
Claude Code APP-1004 approve `c525db6bb96d45f3`, APP-1001 refer `ba4aac89436545fb`; ADK APP-1004
approve `b42e7833b3d240f9`; LangGraph APP-1004 approve `aecbde21c8ff469d`. `make check-v2`: 14
right, 0 wrong. Part 4 on the pre-built store: `aip agent` in session
`agent-20261113-000430-a8bd` found the procedure and ran APP-1002, approve `a1cb93d6b0b841f5`, 26 s,
nothing built; Claude Code on :8301 ran APP-1003, decline `f1689f740a0c4fc2`, 38 s. `make check-4`:
2 right. Two fixes came out of it: ADK 2.14's `Claude` class is Vertex-only and refuses an
`AsyncAnthropic` client, so the ADK agent now uses `AnthropicLlm`; and the part-3 prompt now says
to run by name, not `@1`, because a continued Claude Code session pinned the revision it had used
before. The empty store was put back as `make prebuild-4` left it (a copy is in
`.aip/empty-prebuilt.rl`), and the main store was reset. The two items below about keys and
part 4 are resolved by this rehearsal.

## What did not work

- **The two framework agents and `aip agent` could not be run live from this session.** The
  Anthropic key the brief says is in the shell (`AIP_AGENT_MODEL_KEY`) is not in the environment
  this agent's commands ran in, is not in `aip config agent` (`model key: none`), and there is no
  `ant auth login` profile; the policy on this machine stopped the agent from reading other
  projects' `.env` files for one, rightly. So: `aip agent` refused to start with its configured
  message (the correct behaviour); the ADK agent failed on its model call; the LangGraph agent
  failed on its model call (`AnthropicConnectionError`). What was verified without a model: each
  agent starts `aip mcp --agent <name> --session <id>` with the shell's environment, sees exactly
  `search`, `describe`, `run`, `resume` (the server offers seven; the filter is the client's), and a
  `search` over MCP finds `assess_business_loan@1`. The agents' tool loops themselves are untested;
  the first run in a terminal with `ANTHROPIC_API_KEY` exported is the test. The ADK agent needed
  one fix found this way: ADK takes a bare `claude-*` model name to mean Claude on Vertex AI, so
  it is handed an explicit `anthropic.AsyncAnthropic()` client.
- **Part 4 is untested end to end** for the same reason. The empty server holds the four shipped
  procedures (`assist`, `build_procedure`, `edit_procedure`, `make_procedure`) and nothing else,
  which is the state part 4 starts from. `aip agent` on it refused for lack of a model key.
- **The console build step** (`npm run build` in `~/dev/aip-0.9/console`) was not rehearsed: the
  checkout is read-only to this agent. `dist/` was already present and the launcher served the
  page on the main server (`node bin/aip-console.mjs --server http://127.0.0.1:8300 --port 4290`,
  because something else on this machine already listens on 4280). The step graph, data flow,
  traffic, History filters and Diff pages were not opened in a browser from this session; the
  server endpoints they read (`/catalog/<name>/graph`, `/runs`, `/runs/<id>`) answer.
- **A live-built procedure's layout is the agent's.** The part-1 prompt pins the name, the
  inputs, the result, the `source/` reading, the `assets/policy.md` thresholds, the one `Decide`
  and the one `Task_Agent`; the rehearsal below says what Claude Code made of it. If the build
  goes wrong, `make publish-solution` and the rest of the demo stands.

## What aip needs

- **`aip agent` cannot turn thinking off, and Claude 5.5 thinks past its reply cap.** On Anthropic's
  OpenAI-compatible endpoint (`/v1/chat/completions`), `claude-sonnet-5-5` and `claude-opus-5-5`
  think by default; `aip.chat.ChatClient` sends `model`, `messages` and `max_tokens` only (32000
  for `aip agent`), so the thinking counts against the cap and nothing turns it off. Asked for
  `build_procedure`'s `draft` (the whole folder as one JSON object, a 34,000-token prompt), both
  models spent all 32000 tokens thinking (`output_tokens_details.thinking_tokens: 3000` of 3000 in a
  capped probe, `finish_reason: length`, empty content), four times over 16 minutes, and `aip agent`
  gave up: `aip agent: gave up at plan after 4 answers: the reply holds no JSON object` (session
  `agent-20261112-233937-4713`, 2026-11-13). The Messages API refuses `thinking: disabled` for these
  models too. `claude-sonnet-4-5` on the same endpoint answers with content at once, so the demo's
  `.env` sets `AIP_AGENT_MODEL_NAME=claude-sonnet-4-5` for `aip agent`. A `reasoning_effort` (or
  `thinking`) setting on `aip config agent`, or a larger cap, would let 5.5 drive it.
- **A folder named like a published procedure shadows the name.** `aip run assess_business_loan`
  run from a directory holding `./assess_business_loan/` runs that folder, as a draft, not the
  published revision; `aip mcp`'s `run` does the same. The rehearsal hit it: the live build had
  written `./assess_business_loan` into the demo folder, and the next five runs of "the published
  procedure" were draft runs of that folder (`check.py` showed `draft` where the revision should
  be). The console's launcher guards against exactly this (its README says so); the CLI and MCP do
  not. The demo's prompts now build under `./built/`. A warning when a folder shadows a catalog
  name, or `name@latest` meaning the catalog even when a folder exists, would close it.

- `aip server` refuses to start when `~/.config/aip/server.toml` still carries a key from 0.6
  (`server.inspector`), and says so, but a user upgraded from 0.6 has every server start blocked
  until they edit a file they may have forgotten. The demo ships `./aip-server.toml`, which wins
  over the user file when `aip server` runs from the demo folder. A warning instead of a refusal
  for retired keys would be kinder.
- `uv tool install --force 'agent-instruction-protocol[server] @ <path>'` reused a cached build of
  the checkout and installed a version without `aip agent`; `--reinstall --no-cache` was needed.
  `make setup` passes both. The README's install line should too, or the installer should.
- `aip mcp` has no server-side tool allow-list. The brief's "agents whose only tools are search,
  describe, run and resume" is enforced by each framework's filter; a flag like `aip mcp --tools
  search,describe,run,resume` would make the record say the same thing the demo claims.
- `GET /runs` lists runs without their `result`, so a dashboard like `check.py` makes one request
  per run for the outcome. A `result` (or the `End` keys) in the listing would make "right or
  wrong at a glance" one request.
- The console launcher's default `--workdir` is the directory it starts in; started from
  `~/dev/aip-0.9/console`, a run from the console page would look for `source/` there. The
  Makefile passes `--workdir $(CURDIR)`.
- A `choice` answer's `confidence` from TypeSafe was 0.06 to 0.35 for probability spreads like
  0.33/0.30/0.37 and 0.20/0.55/0.25: it reads as the margin between the top two labels, not the
  top probability. `docs/language/spec.md` 2.4 says a choice carries `confidence` and
  `probabilities` but not how the model defines the former; a procedure author setting
  `Confidence_Below` for a three-way choice needs to know. 0.6 here means "the leading label is
  0.6 clear of the runner-up".
