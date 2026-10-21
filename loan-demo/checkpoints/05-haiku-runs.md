# Swapping the driving model, 2026-10-21

Revision 2 (`946cbe6ba6a55848`), R7 in the graph. The same prompts with `--model claude-haiku-5-5` on the
Claude Code session that drives the aip-runtime skill, and one Fable session on APP-1005 as a same-day R7-path
baseline. Nothing else changed: scripts on this machine, Jev on the decision step.

| application | model | server run | wall | API | cost | turns | output tokens | pauses | ended |
|---|---|---|---|---|---|---|---|---|---|
| APP-1005 | Haiku 5.5 | 0181809629854f15 | 62 s | 53 s | $0.019 | 13 | 10.2K | review, rationale | unfiled, R7 |
| APP-1005 | Fable 5.1 | f25c7faab2fc411f | 140 s | 132 s | $1.58 | 14 | 10.6K | review, rationale | unfiled, R7 |
| APP-1004 | Haiku 5.5 | 3d895abce4e94a5e | 42 s | 35 s | $0.015 | 9 | 7.8K | rationale | DEC-APP-1004-03 approve 0.6, R3, 35 cites |
| APP-1004 | Fable 5.1 (revision 1, earlier) | 87154d51bab6483c | 70 s | 61 s | $1.03 | 7 | 5.1K | rationale | DEC-APP-1004-02 |
| APP-1001 | Haiku 5.5 | 41907366509942df | 59 s | 51 s | $0.022 | 12 | 10.2K | review, rationale | unfiled, R7 |
| APP-1001 | Fable 5.1 (revision 2) | 52d82bdbec6749b7 | 109 s | 100 s | $1.46 | 12 | 7.6K | review, rationale | unfiled, R7 |

Jev's answers on the R7 path, and what the session did at the review:

| run | risk_tier | connected_exposure_material | assessed_outcome | at the review |
|---|---|---|---|---|
| APP-1005 Haiku | low 0.33 | not material 0.70 | decline 0.37 | overrode the outcome to approve; accepted the rest |
| APP-1005 Fable | low 0.37 | not material 0.66 | decline 0.28 | overrode the outcome to approve; accepted the rest |
| APP-1004 Haiku | medium 0.94 | not material 0.94 | approve 0.73 | no review |
| APP-1001 Haiku | high 0.37 | material 0.96 | decline 0.91 | accepted |

With R7 fired on APP-1005 (the owner's other business carries a $950K facility, current), the policy band is
review and Jev leans decline at low confidence; both sessions overrode it to approve at the review pause, so
the `Answer` nodes for those runs carry `value` decline and `accepted` approve with `overridden` true (query 6c).
Either way the run ended unfiled: R7 is for a human.

The first Haiku APP-1004 session (33 s, 9 turns, $0.014) started the run, saw two approve decisions on file, and
stopped at the rationale pause rather than file a third; that run, 5f4a8044a8e944b4, stays paused in the history.
The row above is the rerun with one sentence added to the prompt, that a fresh, independent assessment is wanted.

Haiku's APP-1004 decision equals Fable's DEC-APP-1004-02 on outcome, confidence, the fired rule and all 35 cited
keys, with a PRECEDENT_FOR edge from it. Its APP-1001 and APP-1005 runs took the same steps, paused at the same
answers and ended the same way as the Fable runs. Haiku: about half the wall time, a third to a half of the API
time, 60 to 100 times cheaper at list price.
