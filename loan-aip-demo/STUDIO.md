# Ad hoc: the Studio

A quick Studio check, outside the four parts. One script, one judgment, one step for a person.

## Before

The console must come from a shell with the key loaded, or its chat has no model:

```sh
cd ~/dev/graph-memory-system-one-demo/loan-aip-demo
set -a; source .env; set +a
make console                    # http://localhost:4280
```

If 4280 is held by an old console, `lsof -nP -iTCP:4280 -sTCP:LISTEN`, kill it, run `make console` again.

## The brief

Studio, new procedure. Name: `expense_approval`. Paste:

> An expense approval procedure. A script checks the claim against a 500 limit and whether a receipt is attached; claims under the limit with a receipt are approved; claims over the limit go to a person who approves or declines; anything without a receipt is sent back with a note the agent drafts.

It asks three questions. Answer:

> 1. Both: the status "sent_back" and the agent's note.
> 2. The person gives the reason in one line; the agent does not draft anything for a decline.
> 3. Inclusive: exactly 500 is auto-approved. Over 500 goes to the person.

The trace reads: listed the documents, read the documents, worked out the rules, you answered, took your answers, worked out the rules, clarify: 2 passes. Then it writes the folder, compiles, tries it once without running the script, and reviews it.

## Run it

Save draft, then Run. Tick the person's step (approve or decline) as yours. Give a claim over 500 with a receipt: the script runs, the form comes to you, the model handles the rest.
