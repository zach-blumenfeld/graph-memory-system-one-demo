# Demo sketch: "Show me how you decided. Now do it a hundred times."

**Status:** sketch v3, 2026-10-13. v1 (portfolio risk flags) and v2 (consumer
loan, fourteen steps) are superseded. Not on a slide yet; slide 16 stays a
placeholder. Fictional names need a collision search before use. Regulatory
points are from memory and marked *verify*; nothing goes on a slide or into
the spoken line without a row in `docs/citations.md`.

## The story in plain words

A small business applies to a bank for a loan to open a second location. Inside
the bank, someone pulls data from five systems, stitches it together by hand,
and forms a judgment nobody can fully reconstruct later. Act one: an AI agent
does that job over a graph that connects the five systems, finds a fact that
lives in no single system (one of the owners is behind on another loan with
the same bank), and shows every step of how it decided. Act two: the bank has
to do this a hundred times a week. Each run is slow and reasons a little
differently. We take the recorded runs, distill them into a fixed procedure
where the evidence gathering is code, the judgment is a typed question with a
confidence score, and the written rationale is the only thing the model
writes. Run it on the next applicants: the same steps every time, every run recorded
against the procedure that ran it, a human only when the model is unsure, and
the decision lands back in the graph as a precedent for the next one. Then we
change the procedure, one rule, one new revision, and run again. The point is
not that it is faster. The point is that you can say exactly what was done,
show it for every run, and change it on purpose.

## Where it comes from

- **The knowledge-layer demo** (internal narrative, "Show me how you
  decided", read 2026-10-13): a small business, five systems, a connected
  delinquency found through the ownership graph, the decision trace as the
  explanation, a human approving from the trace. Its beat 6, "learning from
  use", is marked least built. Our act two is that beat made real.
- **Lyon's context-graphs post** (Jan 14, 2026): the credit-line-increase
  workflow, decisions as nodes with APPLIED_POLICY, ABOUT, PRECEDENT_FOR
  edges, precedent search. The record step writes exactly that.
- **The AIP worked example** (`graph-memory-system-one-demo/aip-demo`): the
  plumbing. Fixture, CLI, hooks that record every call into
  `neo4j-agent-memory`, trace export, compile with the `aip` authoring skill,
  publish, run through the server with Jev answering the decisions.
- **Slides 12 and 13**: Arhasi for "an answer is worth its trace", Uber for
  "rules checked before anything ships."

Keep internal material internal: no product packaging, no strategy notes,
no internal names on a slide. The small-business loan shape is generic; the
names and data are ours.

## The synthetic world

A fictional bank (working name *Lantern Mutual*) and applicant (working name
*Harrow Street Bakery*, owners Priya Mehta and Tom Alder, applying for $400K
for a second location). Five systems, each a JSON fixture from a
`make_fixture.py`, imported into one memory graph:

| System | In plain terms | Holds |
|---|---|---|
| Core banking | the applicant's accounts and six-year history with the bank | accounts, balances, monthly cash flow |
| Loan and credit | current facilities plus this application; every facility's payment status | facilities, applications, payments, delinquencies |
| Compliance | KYC status and the bank's lending policy | KYC records, policy rules as nodes |
| Ownership | who owns the applicant, and what else those owners own | people, businesses, OWNS with percentages |
| CRM | who at the bank covers this relationship, past interactions | relationship manager, notes |

```
(:Business)-[:APPLIED]->(:Application)-[:FOR_AMOUNT]
(:Person)-[:OWNS {pct}]->(:Business)
(:Business)-[:HOLDS]->(:Account)-[:HAS_CASHFLOW]->(:Month)
(:Business)-[:HAS_FACILITY]->(:Facility)-[:HAS_PAYMENT]->(:Payment {status})
(:Business)-[:KYC]->(:KycRecord), (:Application)-[:SUBJECT_TO]->(:Rule)
(:RelationshipManager)-[:COVERS]->(:Business)
(:Decision)-[:ABOUT]->(:Application), (:Decision)-[:APPLIED_POLICY]->(:Rule)
(:Decision)-[:CITES]->(:Facility|:Payment|:Month|:KycRecord|:Rule)
(:Decision)-[:PRECEDENT_FOR]->(:Decision)
```

**Four applicants**, so the free-form runs have real judgment to do and the
procedure has every branch to take, plus a fifth held back for the live run:

1. **The connected delinquency.** Strong six-year history, clean KYC. Tom
   Alder also owns 60% of *Alder Logistics*, which is 90 days behind on a
   facility with the same bank. Flat retrieval approves; the graph sees it.
   The hero case.
2. **Clean approve.** Passes every hard rule; the procedure never asks the
   model anything except the rationale.
3. **Hard decline.** KYC refresh overdue and a recent fraud block. Rules
   fire, no judgment needed, the rationale names the rules.
4. **The gray one.** Cash flow covers the payment at 1.15x against a 1.25x
   policy floor, but a signed lease and a strong precedent. The decision
   model should be unsure; this is the case that goes to a human.

## Act one: the knowledge layer (about 2:30)

Headless or live Claude Code, no skill, Bash plus Read and Write, the bank's
own page on how a loan is assessed (`loan sop`), and the `loan` CLI as the
only way to touch the five systems. The agent discovers what exists, walks
the ownership graph, finds the Alder Logistics delinquency, writes a
recommendation with its evidence. Three hooks record it all into memory.

On screen, in order: the five systems lit up in the graph; the traversal
Harrow Street → owners → Alder Logistics → facility → 90-day payment; the
recommendation; the recorded trace (Conversation → ReasoningTrace → steps →
tool calls, judgment calls carrying the Decision label).

Then the pivot, said out loud: that took minutes, and here are four more
runs on the same kind of application. Same job, four orders, four wordings
of the same judgment, and one run that never walked the ownership graph.
The Decision query from the email demo shows it in one table.

## Act two: graph engineering (about 3:30)

`loan traces export --source`, one authoring prompt, the `aip` skill
compiles `assess-business-loan`. Nine steps:

| # | step | kind | does | from which beat |
|---|---|---|---|---|
| 1 | gather | script | accounts, cash flow, facilities, KYC, ownership two hops out and the facilities of everything the owners own, policy rules. Node ids on every figure. | discovery + the connected fact, now deterministic |
| 2 | hard-rules | script | policy thresholds that need no judgment: KYC current, no fraud block in 12 months, coverage ratio floor, exposure cap. Returns auto_approve / auto_decline / review with the rules that fired. | the policy |
| 3 | by-rules | router | auto outcomes skip the judgment | |
| 4 | assess | decision | risk_tier (choice); connected_exposure_material (noul); outcome (approve / counter / decline). Each with a probability and a threshold. Declared inputs exclude protected characteristics. | the judgment |
| 5 | precedents | script | similar past Decision nodes and what was done | Lyon's find_precedents |
| 6 | by-confidence | router | under threshold, or a decline on a six-year customer, goes to a human; else continue | the human in control |
| 7 | rationale | client task | the one generative step: the plain-language explanation citing evidence nodes and precedents | the explanation |
| 8 | check | script | every cited node exists, every figure matches the evidence, the outcome matches the decision; one fix pass, no loops | |
| 9 | record | script | writes the Decision node with ABOUT, APPLIED_POLICY, CITES, PRECEDENT_FOR; logs the typed answers with their probabilities | learning from use, now real |

Narrate two steps only: gather, because it is what the free-form runs did
differently, and assess, because the typed answers with confidence are where
the speed and the consistency come from. One sentence on record: the skill
writes back into the memory it was distilled from.

Then run it on the fifth applicant through the server. The room sees: the
catalog search, the run start, typed answers with probabilities as the
server walks the graph, one pause (the rationale), the filed decision. Two
Browser queries: the run (`Run → StepRun → Answer → Question`) and the trace
(Decision → CITES → the Alder facility → the payment → the rule). Run it
again: same evidence, same figures, same outcome.

Then edit it. Open the skill, change one thing a compliance officer would
actually change (raise the coverage floor from 1.25x to 1.35x, or add
"connected exposure over $250K always goes to a human" to the by-confidence
router), validate, publish revision 2. Run the gray applicant again: the new
rule fires, the run record names revision 2, and the two runs sit side by
side in the graph. That is the beat the room should leave with: the
procedure is a thing you can read, run, record and change, not a prompt
somebody tuned.

## Where the procedure graph adds value, shown not said

| Free-form agent (act one) | Procedure (act two) | On screen |
|---|---|---|
| One run never walked the ownership graph | gather walks OWNS two hops every run; it is a script | run twice, same delinquency found |
| Evidence chosen differently each run | one gather step, node ids on every figure | the CITES edges |
| Judgment worded differently each run, no record of confidence | assess returns typed answers with probabilities; under threshold a human | the Answer nodes; the gray applicant pausing |
| Rationale could state a number with nothing behind it | check rejects any cited node or figure not in the evidence | the check step passing or bouncing |
| A different path each time, no record of which | the same path, every run recorded against the skill revision that ran it | the Run query, several runs side by side |
| Change the behaviour by editing a prompt and hoping | change one step, validate, publish revision 2; old runs still point at revision 1 | the edit beat |
| Nothing learned for next time | record writes the Decision as a precedent; precedents reads it | the PRECEDENT_FOR edge on the next run |
| Lives in one agent's prompt | one SKILL.md: server with Jev, or plain agent walk, or MCP | open the same file in a plain session |

No numbers are promised. Speed is a side effect and we do not lead with
it. What we measure and show: how many runs, which steps each took, where a
human was asked, and that two runs on the same applicant match. The earlier
credit-limit eval from the Europe talk is a different demo and is not quoted
here.

## Compliance, said plainly

Three beats, no regulation named on stage. The citations go in the notes as
Q&A backup.

- **When you decline someone, you owe them a reason.** That applies to
  business loans too. The rationale the model writes is that letter, and the
  check that it only cites real evidence is what makes the letter defensible.
- **The judgment step can only see what we hand it.** The assess step
  declares its inputs; they do not include the owners' age, sex, ethnicity or
  anything else protected, and the state it received is stored on every run.
  Stronger than "we told the model to ignore those things": it could not see
  them, and you can prove it for every decision.
- **Every decision is auditable.** Saved with the rules it applied, the facts
  it cited and the confidence it had. "How did you decide this one" is a
  query. That is the Arhasi point from slide 12.

## How it lands on the three words

- **Predictability.** The order is the graph. The ownership traversal
  happens every run because it is code. Decisions carry a probability; under
  threshold a human is asked. Two runs on the same applicant match.
- **Governance.** Every figure and every reason cites a node; the rationale
  cannot invent one. Runs are recorded against a skill revision, and a
  revision is something you edit, validate and publish on purpose. The
  decision is a node the next decision can cite.
- **Portability.** One SKILL.md on the agentskills.io format. Server with
  Jev, or plain agent walk, or MCP. Same skill, two runtimes, same demo.

## Timing (target 6:30 inside the 5 to 8 budget)

| at | beat | live or canned |
|---|---|---|
| 0:00 | The setup. One applicant, five systems, the question: show me how you decided. | one slide |
| 0:30 | Act one. The agent works the application; the ownership traversal; the recommendation; its trace in memory. | canned recording, Browser live |
| 2:30 | The pivot. Four more runs side by side; the Decision query. | Browser, canned |
| 3:15 | The skill. Nine steps in the inspector; zoom on gather and assess. | inspector |
| 4:00 | Run it. Fifth applicant, typed answers, one pause, filed decision. | live, video fallback |
| 5:00 | The trace. Decision → CITES → the connected facility → the rule. Several runs side by side. | Browser, live |
| 5:30 | Edit it. One rule changed, revision 2 published, the gray applicant run again. | live, video fallback |
| 6:15 | Portability. Same SKILL.md in a plain session. One sentence. | canned |

Fallbacks: a recorded video of the live run; PNGs of every Browser query;
the aip server and both Neo4j databases on the laptop so the only network
call is Jev. Decide whether to accept that call on expo wifi or pre-record.

## What to build, reusing `aip-demo`

1. `tools/make_fixture.py` → five systems, the policy, the SOP, five
   applicants. New.
2. `src/<pkg>/tools.py` and `cli.py` → `loan sop | application | ownership
   | facilities | cashflow | kyc | policy | precedents | rationale submit |
   check | record | decide`. New bodies, same shape.
3. `importer.py` `plan()` → the labels and edges above.

Unchanged: hooks, recorder, memory setup, Makefile, `.claude` settings,
export and authoring flow. Then five recordings, the authoring run, publish,
the held-back applicant, the Browser queries saved as favourites. About a day
plus recordings. If the knowledge-layer demo's data becomes available first,
act one can run on it instead and the fixture only needs act two's shape.

## Regulatory points to verify before they are spoken (*verify*)

Not on slides. Business lending carries fewer consumer rules than a personal
loan, which is one reason the story is simpler.

- KYC / customer identification and beneficial ownership on a business
  applicant: 31 CFR 1020.220 and 1010.230.
- Adverse action for business credit: ECOA / Reg B applies to business
  applicants too, with a lighter notice regime, 12 CFR 1002.9(a)(3).
- Fair lending: Reg B prohibited bases apply; the assess step's declared
  inputs must not include them.
- Safety and soundness underwriting: coverage ratios and exposure caps are
  bank policy, not statute; say "policy", not "the law requires."

## Open questions for the author

- Memory side is the open-source `neo4j-agent-memory` library over Bolt, as
  in the email demo (decided 2026-10-13). The author may port act one to NAMS
  separately; the fixture and import are written so the graph can be lifted
  as is. The skill side stays on AIP.
- Align names and data with the knowledge-layer demo if it is public by the
  talk, or keep ours and say "the same shape as the knowledge-layer demo."
- Slide 10's procedure-graph diagram shows incident triage. Swap it for
  `assess-business-loan` so the room sees the same graph twice.
- Names: Lantern Mutual, Harrow Street Bakery, Alder Logistics, Priya Mehta,
  Tom Alder are placeholders. Search before use.
