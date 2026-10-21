# Live runs of the published skill, 2026-10-21

Brief-013, fresh headless Claude Code sessions with the aip-runtime skill (`.run/live/run.sh`), aip 0.6a1
client against the aip server on localhost:8000 (Neo4j catalog), TypeSafe Jev configured on the client
(`aip config --decision-model`). Server runs: 26de899fd30640ae (default model), 1fa3ef12691b49e5 (Sonnet).
Both: 10 steps, one pause (write), check passed first time, scheduled 2026-11-04T09:00Z, subject line "riverbed
2.0: write a connector in one class".

| model | turns | wall | API time | cost | pauses |
|---|---|---|---|---|---|
| default (claude-fable-5-1) | 16 | 135 s | 125 s | $1.71 | write |
| sonnet (claude-sonnet-5-5) | 14 | 58 s | 50 s | $0.26 | write |

Jev (jev-1.13.0, answered on the client, resolver `typesafe`, no review pause):

| run | email_kind | urgency | legal_review | subject_pick |
|---|---|---|---|---|
| default | launch 1.00 | normal 1.00 | false 0.89 | first 0.46 (threshold 0.45) |
| sonnet | launch 1.00 | normal 1.00 | false 0.88 | first 0.55 (threshold 0.45) |

The subject pick is close to its threshold both times: three near-equal lines, as the author expected when
setting 0.45. The aip run itself (scripts here, decisions with Jev, routing on the server) took about 60 s of
the default session's 135 s; the rest is the agent reading the skill, searching the catalog and writing the email.

## Token usage, measured

From Claude Code's own accounting (`usage` in the JSON result of each headless session).
"Cache read" is context re-sent from the prompt cache each turn; "output" is what the model wrote.

| session | turns | new input | output | cache read | cache write | total tokens | cost |
|---|---|---|---|---|---|---|---|
| free-form run-01 (launch) | 19 | 258 | 6,788 | 120,278 | 21,438 | 148,762 | $0.80 |
| free-form run-02 (launch) | 17 | 258 | 7,007 | 123,551 | 14,724 | 145,540 | $0.68 |
| free-form run-03 (digest) | 18 | 258 | 5,092 | 115,519 | 13,109 | 133,978 | $0.55 |
| free-form run-04 (hotfix) | 17 | 322 | 6,910 | 159,645 | 15,747 | 182,624 | $0.70 |
| skill run, default model | 16 | 324 | 6,836 | 695,204 | 59,639 | 762,003 | $1.71 |
| skill run, Sonnet | 14 | 24 | 3,566 | 530,242 | 41,859 | 575,691 | $0.26 |
| compiling the skill (one-off) | 64 | 772 | 74,137 | 4,272,297 | 234,904 | 4,582,110 | $9.48 |

Honest reading: on this day the free-form agent was already fast (91 to 120 s), and the skill run with the
default model was not faster (135 s); the Sonnet-driven skill run was (58 s). The skill run does not use fewer
tokens either: the agent still writes the email, and the client loop carries the run state through its context
each turn, so cache reads are four to five times higher. What the skill buys is the order (compliance before
scheduling, one fix-up pass, digests never scheduled), decisions with a calibrated probability instead of the
language model's, a smaller driving model that gets the same result, and a record of every step.
