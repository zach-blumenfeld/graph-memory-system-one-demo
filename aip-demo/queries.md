# Browser queries, in demo order

Paste each block into Neo4j Browser. The first comment line says which database: `memory` is the
agent-memory Aura instance (`.env` in this folder), `aip` is the aip server's instance
(`~/.config/aip/server.toml`). Keep a Browser tab open on each.

```cypher
// [memory] - 0 - one campaign and everything the agent needs to run it (brief-001)
MATCH (c:Campaign {brief_id: 'brief-001'})
MATCH p = (c)-[]->(n)
OPTIONAL MATCH q = (n)-[:ASSERTS|REPRESENTS]-(m)
RETURN p, q
```

```cypher
// [memory] - 1 - the SOP page the agent reads (what `blast sop` runs)
MATCH (p:Playbook) RETURN p.name, p.text
```

```cypher
// [memory] - 2 - one recorded run: conversation, messages, trace, steps, tool calls (Decision steps stand out by label)
MATCH (c:Conversation)-[ht:HAS_TRACE]->(t:ReasoningTrace)
WITH c, ht, t ORDER BY t.started_at LIMIT 1
MATCH p1 = (c)-[:HAS_MESSAGE]->(:Message)
MATCH p2 = (t)-[:HAS_STEP]->(:ReasoningStep)-[:USES_TOOL]->(:ToolCall)
RETURN c, ht, t, p1, p2
```

```cypher
// [memory] - 3 - the same run as a table, in order
MATCH (c:Conversation)-[:HAS_TRACE]->(t:ReasoningTrace)
WITH t ORDER BY t.started_at LIMIT 1
MATCH (t)-[:HAS_STEP]->(s:ReasoningStep)-[:USES_TOOL]->(tc:ToolCall)
RETURN s.step_number AS n,
       CASE WHEN s:Decision THEN 'decision: ' + s.question + ' -> ' + s.answer ELSE tc.tool_name END AS what,
       tc.status AS status, left(s.why, 90) AS why
ORDER BY s.step_number
```

```cypher
// [memory] - 4 - every judgment call across all runs, grouped by question: the decision points of the procedure
MATCH (d:Decision)
RETURN d.question AS question, collect(d.answer) AS answers, count(*) AS times
ORDER BY times DESC
```

```cypher
// [aip] - 5 - the whole published skill: name, revision, procedure, steps, edges, inputs, questions
MATCH (n:Name {name: 'launch-email-blast'})-[:HAS_REVISION]->(s:Skill)-[:HAS_PROCEDURE]->(p:Procedure)
MATCH p1 = (p)-[:HAS_STEP]->(st:Step)
OPTIONAL MATCH p2 = (st)-[:INPUTS_TO|BRANCH]->(:Step)
OPTIONAL MATCH p3 = (st)-[:DECLARES_INPUT|ASKS]->()
RETURN n, s, p, p1, p2, p3
```

```cypher
// [aip] - 6 - just the steps and the flow between them (13 steps, 18 edges; labels are the step kinds)
MATCH (:Name {name: 'launch-email-blast'})-[:HAS_REVISION]->(:Skill)-[:HAS_PROCEDURE]->(:Procedure)-[:HAS_STEP]->(st:Step)
OPTIONAL MATCH e = (st)-[:INPUTS_TO|BRANCH]->(:Step)
RETURN st, e
```

```cypher
// [aip] - 7 - every run of the skill, step by step, with the answers the decision model gave
MATCH (r:Run {name: 'launch-email-blast'})-[:OF_SKILL]->(s:Skill)
MATCH p1 = (r)-[:STEP_RUN]->(sr:StepRun)
OPTIONAL MATCH p2 = (sr)-[:NEXT]->(:StepRun)
OPTIONAL MATCH p3 = (sr)-[:OF_STEP]->(:Step)
OPTIONAL MATCH p4 = (sr)-[:ANSWERED]->(:Answer)-[:OF_QUESTION]->(:Question)
RETURN r, s, p1, p2, p3, p4
```

Swap `launch-email-blast` for `billing-support` in 5 and 6 to draw the small example skill.
