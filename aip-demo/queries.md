# Queries for the talk

Two databases. Beats 1 and 2 run against the memory database (`1e78d87c`, the `.env` in this
folder). Beat 4 and 5 run against the aip server's database (`659edd6a`, `~/.config/aip/server.toml`).
Paste into Neo4j Browser or the Aura query view.

## Beat 1: the team's knowledge (memory db)

One campaign and everything the agent needs to know to run it: the product it promotes and that
product's approved claims, the segment it targets and that segment's persona, the brand guide, and
the SOP page it follows.

```cypher
MATCH (c:Campaign {brief_id: 'brief-001'})
MATCH p = (c)-[]->(n)
OPTIONAL MATCH q = (n)-[:ASSERTS|REPRESENTS]-(m)
RETURN p, q
```

About 12 nodes. Labels are plain: `Campaign`, `Product`, `Claim`, `Segment`, `Persona`, `Brand`,
`Playbook` (every one also carries `:Entity`, which is the memory SDK's label). Edge types are the
ones the Notion relations imply: `PROMOTES`, `ASSERTS`, `TARGETS`, `REPRESENTS`, `CONSTRAINED_BY`,
`FOLLOWS`.

The SOP page itself, as the agent reads it (`blast sop` runs this):

```cypher
MATCH (p:Playbook) RETURN p.name, p.text
```

## Beat 2: what the agent did (memory db)

One run as a connected subgraph: the conversation and its two messages, the trace, every step
with its tool call. Judgment calls carry the extra `Decision` label; colour by label and they
stand out. Change `LIMIT 1` to `LIMIT 4` for all four runs side by side.

```cypher
MATCH (c:Conversation)-[ht:HAS_TRACE]->(t:ReasoningTrace)
WITH c, ht, t ORDER BY t.started_at LIMIT 1
MATCH p1 = (c)-[:HAS_MESSAGE]->(:Message)
MATCH p2 = (t)-[:HAS_STEP]->(:ReasoningStep)-[:USES_TOOL]->(:ToolCall)
RETURN c, ht, t, p1, p2
```

The same run as a table, which reads better on stage:

```cypher
MATCH (t:ReasoningTrace)
WITH t ORDER BY t.started_at LIMIT 1
MATCH (t)-[:HAS_STEP]->(s:ReasoningStep)-[:USES_TOOL]->(tc:ToolCall)
RETURN s.step_number AS n,
       CASE WHEN s:Decision THEN 'decision: ' + s.question + ' -> ' + s.answer ELSE tc.tool_name END AS what,
       tc.status AS status, left(s.why, 90) AS why
ORDER BY s.step_number
```

Every judgment call across all runs, grouped by question. This is what becomes the skill's
decision steps:

```cypher
MATCH (d:Decision)
RETURN d.question AS question, collect(d.answer) AS answers, count(*) AS times
ORDER BY times DESC
```

## Beat 3: the distilled skill

Not a query: `skills/launch-email-blast/SKILL.md` is the artifact, and `skills/launch-email-blast/source/` holds
the SOP and the traces it was compiled from, plus `README.md` listing what was kept and dropped.

## Beat 4: the skill as a graph (aip db)

The published procedure: steps typed by kind, the edges between them, the questions each decision
asks.

```cypher
MATCH (n:Name {name: 'launch-email-blast'})-[:HAS_REVISION]->(s:Skill)-[:HAS_PROCEDURE]->(p:Procedure)
MATCH p1 = (p)-[:HAS_STEP]->(st:Step)
OPTIONAL MATCH p2 = (st)-[:INPUTS_TO|BRANCH]->(:Step)
OPTIONAL MATCH p3 = (st)-[:DECLARES_INPUT|ASKS]->()
RETURN n, s, p, p1, p2, p3
```

## Beat 5: the run (aip db)

Every run of the skill with the step it ran and the answers the decision model gave:

```cypher
MATCH (r:Run {name: 'launch-email-blast'})-[:OF_SKILL]->(s:Skill)
MATCH p1 = (r)-[:STEP_RUN]->(sr:StepRun)
OPTIONAL MATCH p2 = (sr)-[:NEXT]->(:StepRun)
OPTIONAL MATCH p3 = (sr)-[:OF_STEP]->(:Step)
OPTIONAL MATCH p4 = (sr)-[:ANSWERED]->(:Answer)-[:OF_QUESTION]->(:Question)
RETURN r, s, p1, p2, p3, p4
```

The inspector at http://localhost:8000/inspector/ shows the same thing with less squinting:
catalog (the step graph), run console, history, governance.
