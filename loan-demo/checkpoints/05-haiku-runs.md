# Server runs on Haiku, 2026-10-14

Same prompts and flags as the 2026-10-13 server runs (`checkpoints/04-live-runs.md`), with
`--model claude-haiku-5-5` on the Claude Code session that drives the `aip-runtime` skill. Nothing
else changed: skill revision 2 (`1c4e170b79c08bb1`), the same aip server, Jev (`jev-1.13.0`) on the
decision step, R7 present in the memory graph. One Fable session on APP-1005 was run in the same
batch so the R7 path has a same-day baseline (the 2026-10-13 APP-1005 runs predate R7). Script and
raw session JSON under `.run/haiku/`.

| session | model | server run | wall | API | cost (list) | turns | output tokens | pauses | ended |
|---|---|---|---|---|---|---|---|---|---|
| APP-1005 | Haiku 5.5 | 724a379fcecf48e5 | 83 s | 20 s | $0.013 | 9 | 3.5K | 2 review | unfiled, R7 |
| APP-1004 | Haiku 5.5 | 689d4f1f068f4cb9 | 164 s | 53 s | $0.021 | 13 | 10.2K | 1 rationale | DEC-APP-1004-03 approve 0.6 |
| APP-1001 | Haiku 5.5 | 06a7a1ad5b2140f2 | 106 s | 35 s | $0.014 | 12 | 5.3K | 1 review | unfiled, R7 and G1 |
| APP-1005 | Fable 5.1 | c362515ab5924564 | 114 s | 68 s | $0.94 | 9 | 3.1K | 2 review | unfiled, R7 |

Jev's answers at `assess`, which are independent of the driving model:

| server run | application | risk_tier | connected_exposure_material | outcome |
|---|---|---|---|---|
| 724a379fcecf48e5 (Haiku) | APP-1005 | low 0.92 | 0.36 (under threshold) | approve 0.59 (under threshold) |
| c362515ab5924564 (Fable) | APP-1005 | low 0.94 | 0.42 (under threshold) | approve 0.59 (under threshold) |
| 689d4f1f068f4cb9 (Haiku) | APP-1004 | medium 0.91 | 0.07 | approve 0.73 |
| 06a7a1ad5b2140f2 (Haiku) | APP-1001 | medium 0.25 (0.50 / 0.50) | 0.97 | decline 0.72 |

## What matched

- **APP-1004.** DEC-APP-1004-03 (Haiku) equals DEC-APP-1004-02 (Fable, 2026-10-13): approve,
  confidence 0.6, R3, the same 35 cited keys, `PRECEDENT_FOR` from the Fable decision. The check
  passed on the first attempt. The rationale is 3.8K characters against Fable's 6.7K, same
  structure, same precedent handling (follows the APP-1004 approves, departs from the APP-1001
  refers and says why).
- **APP-1001.** Same path as the Fable revision-2 run: one review pause at `assess` on the risk
  tier, ended for a human on R7 (and G1, since Jev said decline). Haiku overrode the tier to high,
  as Fable did on revision 1; the Fable revision-2 run accepted medium.
- **APP-1005 under R7.** Haiku and Fable walked the same seven steps, paused twice on the same two
  under-threshold answers, accepted the suggested answers, and ended unfiled on R7.
- Every Haiku summary stated the right figures, the right fired rules and the right connected
  business.

## What differed

- Haiku's APP-1001 session ran `aip run` from `/tmp`, so its run file landed outside the project,
  and it called `aip resume` a second time on the finished run. The server accepted that and
  appended `precedents`, `by-confidence`, `end` to the history again (10 entries instead of 7); the
  result is unchanged.
- Wall time about half to three-quarters of Fable's; API time a third to a half. Cost is Claude
  Code's list-price estimate: roughly seventy times lower.

## Caveats

- One run each. Jev's probabilities moved between same-day runs on the same application
  (materiality 0.36 against 0.42), so the pause count is Jev's, not the driving model's.
- Both models could read this project's Claude Code auto-memory, which holds a note on the check's
  rules written by the first 2026-10-13 server run. Neither model was writing the rationale cold.
- The memory graph now holds DEC-APP-1004-03 alongside the earlier APP-1004 decisions; nothing was
  deleted. The four runs stay in the aip history.
