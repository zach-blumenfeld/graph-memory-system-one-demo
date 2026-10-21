# Live runs of the published procedure, 2026-10-21

Headless Claude Code sessions with the aip-runtime skill (`.run/live/run.sh`, `LOAN_RECORD=0`), aip 0.6a1
client against the aip server on localhost:8000, TypeSafe Jev (`jev-1.13.0`) configured on the client. The
scripts ran on this machine; the server validated each step and recorded the run. Revision 1 is
`assess-business-loan@8ffe579680fbdf23` (before R7), revision 2 is `@946cbe6ba6a55848` (after `make rule`).

| run | application | revision | server run | wall | API | cost | turns | pauses | ended |
|---|---|---|---|---|---|---|---|---|---|
| 1 | APP-1005 | 1 | 11e91506c8c54ed9 | 93 s | 83 s | $1.28 | 14 | review, rationale | DEC-APP-1005-01 approve 1.0, 21 cites |
| 2 | APP-1005 | 1 | 0050361f9ccc47d2 | 101 s | 92 s | $1.34 | 16 | review, rationale | DEC-APP-1005-02 approve 1.0, 21 cites, PRECEDENT_FOR from -01 |
| 3 | APP-1004 | 1 | 87154d51bab6483c | 70 s | 61 s | $1.03 | 7 | rationale | DEC-APP-1004-02 approve 0.6, R3, 35 cites |
| 4 | APP-1001 | 1 | 9ae85ebb033f47d3 | 119 s | 111 s | $1.63 | 12 | review, rationale | unfiled: decline on a 6-year customer, G1 |
| 5 | APP-1001 | 2 | 52d82bdbec6749b7 | 109 s | 100 s | $1.46 | 12 | review, rationale | unfiled: R5 and R7 fired, R7 is for a human |

Jev's answers (resolver `typesafe`; a `noul` pauses for review when its probability is within the 0.3 margin
of 0.5, a `choice` when its confidence is under its threshold):

| run | risk_tier | connected_exposure_material | assessed_outcome | review pause on |
|---|---|---|---|---|
| 1 APP-1005 | low 0.98 | not material 0.77 | approve 0.98 | connected exposure (0.77 is within 0.3 of 0.5); accepted |
| 2 APP-1005 | low 0.97 | not material 0.79 | approve 0.98 | connected exposure (0.79); accepted |
| 3 APP-1004 | medium 0.92 | not material 0.93 | approve 0.77 | none |
| 4 APP-1001 rev 1 | medium 0.28 | material 0.96 | decline 0.97 | risk tier (0.28 under 0.6); accepted |
| 5 APP-1001 rev 2 | medium 0.22 | material 0.96 | decline 0.92 | risk tier (0.22); accepted |

The second APP-1005 session, prompted exactly like the first, did not run the procedure: it found
DEC-APP-1005-01 on file (the aip-runtime skill says not to start a second run of the same task) and reported
the existing decision (10 turns, 49 s, $0.88). Run 2 above is the same prompt with one sentence added, that a
second, independent assessment is wanted. The same happened to the Haiku APP-1004 session below.

`assess` ran on every band in this revision (format 0.6a1 lets no step read a key a skipped step would have
produced), so APP-1005 shows Jev's answers even though the policy auto-approved; `precedents.py` settled the
outcome from the policy and the filed confidence is 1.0.

## Side effects

Memory: DEC-APP-1005-01, DEC-APP-1005-02, DEC-APP-1004-02 (plus DEC-APP-1002-02 from the authoring session's
test). aip history: the five runs above; the R7 runs are in `05-haiku-runs.md`.
