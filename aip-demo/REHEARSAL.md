# Rehearsal: what to type, in order

Before the talk, once:

```
cd ~/dev/graph-memory-systemone-demo/aip-demo
uv run blast doctor                 # memory db, keys, aip, claude, blast on PATH
aip config                          # server: http://localhost:8000 ; if not: aip config --server http://localhost:8000
curl -s localhost:8000/catalog | head -c 200   # the aip server is up (else: aip server --inspector, in its own terminal)
aip list                            # launch-email-blast is published
```

Open: Neo4j Browser on the memory database (`1e78d87c`, creds in `.env`) and on the aip database
(`659edd6a`, creds in `~/.config/aip/server.toml`), and http://localhost:8000/inspector/ .

## Beat 1: the team's knowledge (2 min)

Browser, memory db, `queries.md` beat 1. Say: this is the Notion workspace, loaded with the
open-source memory SDK. One campaign, and the four things the agent must know to run it.
Then `blast sop` in a terminal: the team's own page, read from the graph.

## Beat 2: the agent works it out (4 min)

Do not run it live, it takes five minutes. Show the recording:

```
blast traces show run-01
```

Say: no skill, no MCP. It read the SOP, found the tools, made seven judgment calls, drafted,
checked, scheduled, logged. Then Browser, `queries.md` beat 2, the table, then the judgment
calls grouped by question: "these are the decision points of the procedure, and the agent found
them itself, four times."

## Beat 3: distillation (3 min)

```
head -60 skills/launch-email-blast/source/traces.md      # what the compiler read
cat skills/launch-email-blast/SKILL.md                    # what it wrote
```

Say: the SOP gave the rules, the traces gave the order, the decision points and the edge cases.
Scripts are the `blast` commands. Decisions are typed questions for Jev. The one client task is
writing the email. `source/README.md` lists what was dropped and why.

## Beat 4: the skill as a graph (2 min)

Inspector catalog page (the step graph), then Browser on the aip db, `queries.md` beat 4.

## Beat 5: run it, live (3 min)

Fresh terminal in this folder. `make fresh` first: it forgets earlier local runs and drafts, or
the agent notices brief-013 was already scheduled today and refuses to send it twice.

```
make fresh
claude --model sonnet        # 70 s; plain `claude` is the default model, about 2 min
```

Paste: `Launch the email blast for brief-013, "riverbed 2.0 release", send 2026-11-04 09:00 UTC.`

Claude uses the `aip-runtime` skill: `aip search`, `aip info`, `aip run`. The server runs the
scripts and Jev answers the decisions; Claude is only asked to write the email, and to confirm
anything Jev was unsure about. Say the numbers: the same job took the free-form agent five to
eight minutes and seven judgment calls; here it is one pause and about a minute. Then inspector
history, and `queries.md` beat 5.

If the first draft fails the compliance check (it happens with Sonnet), the run pauses a second
time with the failure named; the fix-up pass is part of the procedure, not a bug.

If the live run misbehaves: `aip run launch-email-blast --input checkpoints/start-brief-013.json
--interactive` does the same from the terminal, and the inspector run console does it with buttons.

## Fallbacks

| problem | do |
|---|---|
| aip server down | `aip server --inspector` in a spare terminal, wait 5 s |
| Jev unreachable | the run pauses at each decision and asks you; answer it, say why |
| Browser slow | the queries are small; if a query hangs, re-run it, Aura Free cold-starts |
| inspector page is blank | open the browser console; if it is `Cannot read properties of null (reading 'slice')`, a catalog name has no live revision (every revision retired). Republish or pin a revision of that name, or delete it from the aip db. The example `billing-support` was removed for this reason |
