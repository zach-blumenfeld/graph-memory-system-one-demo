# Live runs of the published skill, 2026-10-07

Brief-013, fresh headless Claude Code session with the aip-runtime skill, aip server on localhost:8000
with TypeSafe Jev as the decision model. Server runs: 69a1abda347d4fdd (CLI), b6840e4502894fc8
(default model), 6a8374f5577e47d4 (Sonnet).

| model | turns | wall | cost | pauses |
|---|---|---|---|---|
| default | 20 | 100-120 s | $1.37-1.48 | write |
| sonnet | 15 | 70 s | $0.27 | write, fix |

Jev on classify: email_kind launch 1.0, urgency normal 0.98, legal_review 0.11. No manual decisions.
An earlier attempt ran the skill locally (same-named folder in cwd) with manual decisions: 27 turns,
122 s, $1.85; that is why the skill lives under skills/.

## Token usage, measured

From Claude Code's own accounting (`modelUsage` in the JSON result of each headless session).
"Cache read" is context re-sent from the prompt cache each turn; "output" is what the model wrote.

| session | turns | new input | output | cache read | cache write | total tokens | cost |
|---|---|---|---|---|---|---|---|
| free-form run-01 (launch) | 17 | 290 | 7,685 | 139,819 | 22,086 | 169,880 | $0.86 |
| free-form run-02 (launch) | 21 | 322 | 6,544 | 155,492 | 15,067 | 177,425 | $0.67 |
| free-form run-03 (digest) | 14 | 258 | 4,706 | 108,423 | 11,921 | 125,308 | $0.50 |
| free-form run-04 (hotfix) | 22 | 386 | 6,744 | 187,661 | 14,946 | 209,737 | $0.69 |
| skill run, default model | 20 | 484 | 7,912 | 600,023 | 41,155 | 649,574 | $1.37 |
| skill run, Sonnet | 15 | 28 | 4,583 | 405,240 | 35,173 | 445,024 | $0.27 |
| compiling the skill (one-off) | 56 | 708 | 46,243 | 2,642,879 | 154,303 | 2,844,133 | $6.07 |

Honest reading: the skill run is three to five times faster and moves every judgment call off the
language model, but it does not use fewer tokens. The agent's own output is about the same (it
still writes the email), and the client loop carries the whole run state through its context on
every turn, so cache reads are three to four times higher. What the skill buys is time, consistency
and calibrated decisions, not token count. Sonnet makes it cheap anyway. Trimming the state the
server hands back at each pause is the obvious next optimisation.
