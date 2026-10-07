# aip-demo plan (built 2026-10-07 for the talk that night; all seven items done, see STORY.md and REHEARSAL.md)

The email-blast workflow, done the open-source way: agent-memory SDK over bolt (no NAMS, no MCP),
Claude Code doing the job from a Notion SOP, traces distilled into an AIP skill, run on the aip
server with Jev answering the decisions.

Two databases. Memory: Aura `1e78d87c` (this folder's `.env`). AIP catalog and runs: Aura
`659edd6a` (`~/.config/aip/server.toml`, already set, with the TypeSafe key).

## Build order

1. **Fixture + import** — `tools/make_fixture.py` (Tessera Labs, plus the SOP page
   `data/notion/sop_email_blast.md`). `blast import` writes it to memory with the SDK:
   `:Campaign :Product :Claim :Persona :Segment :Brand :Playbook` nodes (all also
   `:Entity`), typed edges `PROMOTES TARGETS ASSERTS CONSTRAINED_BY REPRESENTS FOLLOWS` written
   with the driver so Browser shows real edge types. Proof: `blast verify import`.
2. **The agent's tools** — the `blast` CLI the agent calls from Bash: `sop`, `brief <id>`,
   `segments <product>`, `brand`, `draft submit`, `check <draft>`, `schedule <draft> ...`,
   `log <campaign> ...`, `decide --question --options --answer --why`. JSON in, JSON out. The
   same scripts become the AIP skill's `execution` steps.
3. **Recording** — `.claude/settings.json` hooks → `blast-hook`: UserPromptSubmit starts a
   trace and stores the prompt (`:Conversation`/`:Message`); PostToolUse on Bash records every
   `blast` call as `:ReasoningStep`→`:ToolCall` (decisions get `:Decision`); Stop stores the
   answer and completes the trace. Proof: one headless run, then `blast traces show`.
4. **Four runs** — `prompts/runs.yaml`: launch (brief-001), launch (brief-003), digest
   (brief-012), urgent hotfix (brief-009). `blast record --all`, headless `claude -p`, no skill,
   no MCP, only Bash/Read. Export to `checkpoints/traces/`.
5. **Distill** — `blast traces export --source` writes `source/sop.md` + `source/traces.md`.
   Claude Code with the `aip` authoring skill compiles `./skills/launch-email-blast/` from `source/`.
   `aip validate`, `aip run --interactive` once locally. Scripts under `scripts/` are the
   `blast` commands.
6. **Serve + run** — `aip server --inspector`, retire `billing-support`, `aip publish
   launch-email-blast`. Fresh `claude` with the `aip-runtime` skill: "launch brief-013".
   Jev answers the decisions on the server; the agent writes the draft at the client task.
7. **Docs** — STORY.md (plain English, what to type), queries.md (one query per beat).

Checkpoints in `checkpoints/`: import ids, the four traces, the authored skill folder (committed),
the publish record. Everything re-runnable with `make demo` from this folder.
