# The story

Tessera Labs is a made-up open-source company. Its marketing team keeps everything in Notion:
four products, the claims they are allowed to make about each one, the audiences they email, and
a brand guide that says how emails must sound and what they must never say.

The team wants an AI agent to launch email campaigns for them. Here is what happens.

## 1. We give the agent the team's knowledge

We copy the Notion workspace into a Neo4j graph using the open-source neo4j-agent-memory library.
Products, claims, audiences, personas and the brand guide become nodes, connected the way the team
thinks about them: this campaign promotes this product, this product asserts these claims, every
campaign is constrained by the brand guide.

The agent can now look things up instead of guessing.

### How this works

The import is two commands and four files.

1. `tools/make_fixture.py` invents the Notion workspace and writes it to `data/notion/`, one
   JSON file per Notion database, each page shaped the way the Notion API returns it.
2. `ontology/pmm.json` names the seven kinds of thing the team cares about (Campaign, Product,
   Claim, Persona, AudienceSegment, Channel, BrandGuideline) and how they connect.
   `uv run pmm ontology apply` sends it to NAMS. From then on everything in the workspace is
   typed against those seven classes, including entities NAMS extracts on its own later.
3. `src/pmm/notion_import.py` reads the fixture, turns every page into an entity and every
   Notion relation into an edge, and writes them through the NAMS REST API (`POST /v1/entities`,
   `POST /v1/relationships/bulk`). `uv run pmm notion import` runs it; it is safe to run twice.
4. `uv run pmm verify stage1` counts what landed: 42 entities, 88 relationships.

To do this with a real Notion workspace, replace step 1. Pull the databases with the Notion API
(`POST /v1/databases/{id}/query` returns pages in exactly the shape the fixture mimics) and drop
the JSON into `data/notion/`. Nothing else changes: `src/pmm/fixture.py` already reads Notion's
property objects, and the importer maps them to the ontology. Rename a class or an edge in
`ontology/pmm.json` and in `plan_entities` / `plan_relationships` if your Notion schema differs.

To see it, in Neo4j Browser or the NAMS query view:

```cypher
MATCH (c:Entity {type:'Campaign'})
WHERE c.sourceStage IS NULL
WITH c ORDER BY c.brief_id LIMIT 1
MATCH p = (c)-[]->(n:Entity)
OPTIONAL MATCH q = (n)-[:ASSERTS|REPRESENTS]-(m:Entity)
WHERE m.sourceStage IS NULL
RETURN p, q
```

What the node and relationship names mean, and what `sourceStage` is, is in `SCHEMA.md`.

One campaign in the middle. One hop out: the product it promotes, the segment it targets, the
persona for that segment, the brand guide it must obey, the email channel. Two hops out: the
product's approved claims. About 16 nodes, and each one answers one of the four questions the
agent has to answer before it can write a word: what am I selling, who am I talking to, how must
I sound, where does it go.

Imported nodes only carry the `Entity` label, so set the Browser caption to `type` first to see
which is which, then to `name`. Change `LIMIT 1` to `LIMIT 3` for a few campaigns side by side,
or replace the first three lines with `MATCH (c:Entity {type:'Campaign', brief_id:'brief-013'})`
for the live-demo brief. The `sourceStage IS NULL` filters hide the entities NAMS extracts from
the runs later; `SCHEMA.md` explains that property and the rest of the graph.

## 2. The agent does the job twelve times, and we record everything

We give Claude Code a brief: "launch the riverbed 1.8 email to Python developers on October 14."

Claude has eight tools. Read the brief. Get the audience. Classify the brief. Submit a draft.
Check the draft against the brand guide. Score the subject lines. Schedule the send. Log it in
Notion. That is the whole job.

Every tool call is written to the same graph as it happens: what was called, with what input,
what came back, whether it succeeded. Claude's messages are stored too. By the end of a run the
graph holds a complete record of how the campaign was done.

We ran this twelve times overnight with different briefs. Eight were normal launches. Two had a
manager demanding the agent skip the brand check because they were in a hurry. One had a brief
with an unpublished number in it. One was a newsletter, which is a different kind of job.

Something happened in every run that is worth telling the audience. The first draft always
failed the brand check, because the agent had never read the brand guide and did not include the
required disclaimer. The check told it exactly what was missing. The second draft passed. Twelve
out of twelve.

## 3. Twelve runs become one skill

We point NAMS, the hosted memory service, at the eight normal runs and ask it to distill a skill.

It reads the recorded tool calls, works out the order they always happen in, writes a short
description of each step, and checks that every sentence it wrote can be traced to something that
actually happened in memory. Thirty seconds later it hands back a skill file: eight steps, each
one tied to the tool that was called, with the inputs and outputs it expects.

The skill is a recipe for the job, learned from watching the job get done. Nobody wrote it.

## 4. Three of the eight steps do not need a big model

Look at what the eight tools actually do. Five of them are plumbing: read a brief, fetch a list,
save a draft, schedule, log. Three of them are judgment calls:

- Is this brief a launch, an update, an event, or a newsletter? How urgent is it? Does legal need
  to see it?
- Does this draft follow the brand voice? Does it make a claim it is not allowed to make? Does it
  have a call to action? Does it have the disclaimer?
- Which of these three subject lines is best?

Those three tools do not ask Claude. They ask Jev, a model from TypeSafe that only answers
questions of the form "pick one", "rate this", or "true or false". It answers in half a second,
with a probability attached. When the probability is clear, the workflow moves on. When it is a
close call, the tool says "this needs review" and a person or Claude decides.

This is the System One part of the title. The fast, cheap, calibrated judgments live inside the
tools. The expensive model is only used for the one thing that actually needs it: writing the
email.

## 5. A cheaper agent runs the skill

New session. Claude loads the skill and gets a new brief: "launch riverbed 2.0."

With the default model it follows the eight steps and finishes in 84 seconds for about a dollar.

With Sonnet, a smaller and cheaper model, it follows the same eight steps and finishes the draft
and the checks in 46 seconds for about twenty cents. Then it stops before scheduling and asks a
person to look at the legal flag that Jev raised. The bigger model had scheduled the send and
raised the same flag afterwards.

The cheaper model, given the recipe, was the more careful one. That is the ending.

## What the title means

- Agent knowledge: the twelve recorded runs.
- Distilling: NAMS turning those runs into a skill.
- System One workflows: the judgment calls inside the tools answered by a fast, typed, calibrated
  model instead of a large language model.
- Graph memory: the one graph that holds the team's knowledge, the agent's traces, and the
  skill's evidence, all connected.

## What is real and what is made up

Everything about Tessera Labs is invented: the products, the people, the audiences, the numbers,
the brand guide. The software is real: Claude Code, the neo4j-agent-memory library, NAMS,
TypeSafe's Jev, Neo4j Aura. The runs, costs and timings in this repo are real measurements.
