Build the loan-demo folder end to end by following loan-demo/PLAN.md. Work step by step, in order, and do not start a step until the previous step's verify command passes.

How to work so a long session stays sane:
- First read loan-demo/PLAN.md, loan-demo/docs/STORY.md, aip-demo/README.md, aip-demo/PLAN.md and the files under aip-demo/src/blast/. Then begin step 0.
- After every step, append a dated entry to loan-demo/PROGRESS.md: what was done, the verify command and its result, decisions you made, what is next. If your context is ever compacted or you are restarted, re-read PLAN.md and PROGRESS.md and continue from the last entry. Never redo a step whose checkpoint exists and verifies.
- Never print whole trace JSON files, Claude session JSON, or the exported traces.md into the conversation. Use `loan traces show <run>` and grep or head for anything large.
- Run the headless recordings (step 4) and the authoring run (step 5) as background commands with output redirected to files under .run/, and poll the files. They take minutes each.
- Secrets: copy .env.example to .env and stop to ask me for the memory database credentials and the TypeSafe key if they are not already in .env. Do not ask about anything else; make the routine calls yourself and note them in PROGRESS.md.
- Do not commit. I will review and commit.
- Fictional names in PLAN.md are placeholders. Before step 1, search each business and person name; replace any that collides with a real company or a public person and note the replacement in PROGRESS.md.

Stop only when the "Done when" list in PLAN.md is satisfied, or when you are blocked on credentials or on a failure you have tried to fix three times. In either case, the last entry in PROGRESS.md must say exactly where things stand.
