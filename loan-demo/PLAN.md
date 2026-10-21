# loan-demo plan (built 2026-10-13; every step done, see README.md and PROGRESS.md)

The business-loan assessment, done the open-source way: agent-memory SDK over bolt (no NAMS, no MCP),
Claude Code doing the job from the credit team's page, five traces distilled into an AIP skill, run on
the aip server with Jev answering the decisions, one rule added, revision 2 run on the same application.

Two databases. Memory: the instance in this folder's `.env` (Aura for the first build; a local Neo4j in
Docker for the 0.6a1 rebuild of 2026-10-21). AIP catalog and runs: the instance in `~/.config/aip/server.toml`
(shared with aip-demo; it is catalog-only, never memory). Since aip 0.6 the TypeSafe key lives on the client.

## What was built, in order

0. **Scaffold**: `pyproject.toml` (package `loan`, commands `loan` and `loan-hook`), `.claude/settings.json`
   hooks, `Makefile`, `src/loan/{env,memory,hooks,record,cli}.py` adapted from `aip-demo/src/blast/`.
1. **Fixture**: `tools/make_fixture.py` → `data/bank/*.json` (five systems, flat records, deterministic),
   `sop_assess_loan.md`, `policy.md`. The policy as code in `src/loan/policy.py`, shared by the tools, the
   fixture check and the tests. `loan verify fixture`.
2. **Import**: `src/loan/importer.py`, 450 entities through the SDK, 482 typed edges with the driver,
   `loan import --rules-only` for the edit beat. `loan verify import`.
3. **Tools**: `src/loan/tools.py` over the graph (`GraphRepo`), the twelve agent commands, the `loan check`
   lint and `loan record` (Decision with ABOUT, APPLIED_POLICY, CITES, PRECEDENT_FOR). `tests/test_tools.py`.
4. **Five recordings**: `prompts/runs.yaml`, `loan record --all`, `checkpoints/02-runs.json`,
   `checkpoints/traces/run-0[1-5].json`. `loan verify traces`.
5. **Distill**: `loan traces export` → `source/`, `prompts/author.md` + the `aip` skill →
   `skills/assess-business-loan/` (version 1), validated, one local run on APP-1002.
6. **Serve and run**: `aip publish` (revision 8ffe579680fbdf23 in the 0.6a1 rebuild), four runs through
   `claude` + aip-runtime with the scripts and Jev on the client: APP-1005 twice (match), APP-1004 (Jev
   confident, no review pause), APP-1001 (review pause, G1 stop). `checkpoints/03-publish.json`,
   `checkpoints/04-live-runs.md`.
7. **Edit**: R7 `connected_exposure_cap` in the fixture, the prose and the engine; `make rule` (`loan import
   --rules-only`); the skill's `precedents.py` and `record.py` honour a `human` effect; version 2 published
   (946cbe6ba6a55848); APP-1001 on revision 2 stops for a human naming R7.
8. **Docs**: `README.md`, `docs/{import,recording,compile}.md`, `queries.md` (every query run against
   its database).

Decisions made along the way, and what differed from the original sketch, are in `PROGRESS.md`. The
original plan is kept as `docs/PLAN-original.md`.
