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
