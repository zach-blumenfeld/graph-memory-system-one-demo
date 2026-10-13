# Browser queries, in demo order

Paste each block into Neo4j Browser. The first comment line says which database: `memory` is the
agent-memory instance (`.env` in this folder), `aip` is the aip server's instance
(`~/.config/aip/server.toml`). Keep a Browser tab open on each. Labels are real, so Browser colours
by label out of the box; set the caption to `name`.

```cypher
// [memory] - 1 - the applicant's world: APP-1001 two hops out, the five systems colour-coded by label
MATCH (a:Application {key: 'APP-1001'})<-[:APPLIED]-(b:Business)
MATCH p1 = (b)-[:HOLDS|HAS_FACILITY|KYC|HAD|HAS_NOTE]->()
MATCH p2 = (b)<-[:OWNS]-(:Person)
OPTIONAL MATCH p3 = (b)<-[:COVERS]-(:RelationshipManager)
OPTIONAL MATCH p4 = (a)-[:SUBJECT_TO|FOLLOWS]->()
OPTIONAL MATCH p5 = (b)<-[:OWNS]-(:Person)-[:OWNS]->(:Business)-[:HAS_FACILITY]->(:Facility)
RETURN a, b, p1, p2, p3, p4, p5
```

Core banking (`Account`), loans (`Facility`, `Application`), compliance (`KycRecord`, `Rule`),
ownership (`Person`, the second business), CRM (`RelationshipManager`, `Note`): one business in the
middle, every system one hop out, and the owners' other business two hops out.

```cypher
// [memory] - 2 - the connected delinquency: the fact that lives in no single system
MATCH path = (a:Application {key: 'APP-1001'})<-[:APPLIED]-(:Business)<-[:OWNS]-(:Person)-[:OWNS]->(:Business)
             -[:HAS_FACILITY]->(:Facility)-[:HAS_PAYMENT]->(:Payment {status: 'missed'})
RETURN path
```

Same path as a table (one row: the 45% owner of the bakery holds 60% of Alder Logistics, whose
$300,000 facility has three missed payments):

```cypher
// [memory] - 2b - the same path as a table
MATCH (a:Application {key: 'APP-1001'})<-[:APPLIED]-(b)<-[o1:OWNS]-(p:Person)-[o2:OWNS]->(o:Business)
      -[:HAS_FACILITY]->(f:Facility)-[:HAS_PAYMENT]->(pay:Payment {status: 'missed'})
RETURN p.name AS owner, o1.pct AS pct_of_applicant, o.name AS other_business, o2.pct AS pct_of_other,
       f.key AS facility, f.principal AS principal, collect(pay.due) AS missed_due
```

```cypher
// [memory] - 3 - one recorded run as a connected subgraph: conversation, messages, trace, steps, tool calls
// (judgment calls carry the Decision label and stand out). LIMIT 5 for all five runs side by side.
MATCH (c:Conversation)-[ht:HAS_TRACE]->(t:ReasoningTrace)
WITH c, ht, t ORDER BY t.started_at LIMIT 1
MATCH p1 = (c)-[:HAS_MESSAGE]->(:Message)
MATCH p2 = (t)-[:HAS_STEP]->(:ReasoningStep)-[:USES_TOOL]->(:ToolCall)
RETURN c, ht, t, p1, p2
```

```cypher
// [memory] - 3b - the same run as a table, in order
MATCH (c:Conversation)-[:HAS_TRACE]->(t:ReasoningTrace)
WITH t ORDER BY t.started_at LIMIT 1
MATCH (t)-[:HAS_STEP]->(s:ReasoningStep)-[:USES_TOOL]->(tc:ToolCall)
RETURN s.step_number AS n,
       CASE WHEN s:Decision THEN 'decision: ' + s.question + ' -> ' + s.answer ELSE tc.tool_name END AS what,
       tc.status AS status, left(s.why, 90) AS why
ORDER BY s.step_number
```

```cypher
// [memory] - 4 - every judgment call across the five runs, grouped by question: the decision points of the procedure
MATCH (d:Decision:ReasoningStep) WHERE d.question IS NOT NULL
RETURN d.question AS question, collect(d.answer) AS answers, count(*) AS times
ORDER BY times DESC
```

```cypher
// [aip] - 5 - the skill as a graph: steps and the flow between them (13 steps, 17 edges; labels are the step kinds)
MATCH (:Name {name: 'assess-business-loan'})-[:HAS_REVISION]->(s:Skill)-[:HAS_PROCEDURE]->(:Procedure)-[:HAS_STEP]->(st:Step)
WITH s, st ORDER BY s.published_at DESC
OPTIONAL MATCH e = (st)-[:INPUTS_TO|BRANCH]->(:Step)
RETURN st, e
```

The whole published skill: name, every revision, procedure, steps, edges, declared inputs and questions:

```cypher
// [aip] - 5b - the whole skill, every revision
MATCH (n:Name {name: 'assess-business-loan'})-[:HAS_REVISION]->(s:Skill)-[:HAS_PROCEDURE]->(p:Procedure)
MATCH p1 = (p)-[:HAS_STEP]->(st:Step)
OPTIONAL MATCH p2 = (st)-[:INPUTS_TO|BRANCH]->(:Step)
OPTIONAL MATCH p3 = (st)-[:DECLARES_INPUT|ASKS]->()
RETURN n, s, p, p1, p2, p3
```

```cypher
// [aip] - 6 - one run of the skill: Run -> StepRun -> Answer -> Question, the latest run first
MATCH (r:Run {name: 'assess-business-loan'})-[:OF_SKILL]->(s:Skill)
WITH r, s ORDER BY r.started_at DESC LIMIT 1
MATCH p1 = (r)-[:STEP_RUN]->(sr:StepRun)
OPTIONAL MATCH p2 = (sr)-[:NEXT]->(:StepRun)
OPTIONAL MATCH p3 = (sr)-[:OF_STEP]->(:Step)
OPTIONAL MATCH p4 = (sr)-[:ANSWERED]->(:Answer)-[:OF_QUESTION]->(:Question)
RETURN r, s, p1, p2, p3, p4
```

```cypher
// [aip] - 6b - what the assess step received, and what the decision model answered with its probabilities
// (the stored input holds figures, fired rules, ownership as shares, tenure, KYC status, filtered notes: no dob, no names)
MATCH (r:Run {name: 'assess-business-loan'})-[:STEP_RUN]->(sr:StepRun {step: 'assess'})
RETURN r.id AS run, r.revision AS revision, sr.input AS input_the_model_saw, sr.result AS answers_with_probabilities
ORDER BY r.started_at DESC LIMIT 3
```

```cypher
// [aip] - 6c - every typed answer, and whether a human overrode it at a review pause
MATCH (r:Run {name: 'assess-business-loan'})-[:STEP_RUN]->(sr:StepRun {step: 'assess'})-[:ANSWERED]->(a:Answer)-[:OF_QUESTION]->(q:Question)
RETURN r.id AS run, left(r.revision, 8) AS revision, q.name AS question, a.value AS model_said, a.accepted AS accepted, a.overridden AS overridden
ORDER BY r.started_at, q.name
```

```cypher
// [memory] - 7 - the decision trace: Decision -> CITES -> the evidence, APPLIED_POLICY -> the rules, PRECEDENT_FOR
// (Month nodes left out of the picture; they are twelve of the cites)
MATCH (d:Decision:Filed)-[:ABOUT]->(a:Application {key: 'APP-1005'})
WITH d ORDER BY d.at DESC LIMIT 1
MATCH p1 = (d)-[:ABOUT]->(:Application)
OPTIONAL MATCH p2 = (d)-[:APPLIED_POLICY]->(:Rule)
OPTIONAL MATCH p3 = (d)-[:CITES]->(n) WHERE NOT n:Month
OPTIONAL MATCH p4 = (d)<-[:PRECEDENT_FOR]-(:Decision)
RETURN d, p1, p2, p3, p4
```

```cypher
// [memory] - 7b - every filed decision: outcome, confidence, revision, rules applied, cites, precedents
MATCH (d:Decision:Filed)-[:ABOUT]->(a:Application)
RETURN d.key AS decision, a.key AS application, d.outcome AS outcome, d.confidence AS confidence,
       d.skill_revision AS revision, [(d)-[:APPLIED_POLICY]->(r) | r.key] AS rules,
       size([(d)-[:CITES]->() | 1]) AS cites, [(p)-[:PRECEDENT_FOR]->(d) | p.key] AS precedents
ORDER BY d.at
```

```cypher
// [aip] - 8 - revision 1 and revision 2 on the same application (APP-1001), side by side:
// which revision ran, the steps it took, what the hard rules fired, and why it stopped for a human
MATCH (r:Run {name: 'assess-business-loan'})-[:STEP_RUN]->(sr:StepRun)
WITH r, sr ORDER BY sr.order
WITH r, collect(sr.step) AS steps,
     [s IN collect(sr) WHERE s.step = 'hard-rules' | s.result][0] AS rules,
     [s IN collect(sr) WHERE s.step = 'precedents' | s.result][0] AS routed
WHERE rules CONTAINS 'APP-1001'   // the hard-rules result names the application; precedents of other runs do not appear here
RETURN r.id AS run, r.revision AS revision, steps,
       [x IN apoc.text.regexGroups(rules, '"rule": "(R\\d)"') | x[1]] AS fired_rules,
       CASE WHEN routed CONTAINS 'R7 connected_exposure_cap' THEN 'stopped for a human: R7 connected exposure over the cap'
            WHEN routed CONTAINS 'NOT FILED' THEN 'stopped for a human: G1 decline on a long-standing customer'
            ELSE 'filed' END AS why_it_stopped
ORDER BY r.started_at
```

If APOC is not available, this plainer version shows the same two runs with the stop note:

```cypher
// [aip] - 8b - the same two runs: revision, steps, and the note the run ended with
MATCH (r:Run {name: 'assess-business-loan'})-[:STEP_RUN]->(sr:StepRun)
WITH r, sr ORDER BY sr.order
WITH r, collect(sr.step) AS steps,
     [s IN collect(sr) WHERE s.step = 'hard-rules' | s.result][0] AS rules,
     [s IN collect(sr) WHERE s.step = 'precedents' | s.result][0] AS routed
WHERE rules CONTAINS 'APP-1001'   // the hard-rules result names the application; precedents of other runs do not appear here
RETURN r.id AS run, r.revision AS revision, steps,
       CASE WHEN routed CONTAINS 'R7 connected_exposure_cap' THEN 'stopped for a human: R7 connected exposure over the cap'
            WHEN routed CONTAINS 'NOT FILED' THEN 'stopped for a human: G1 decline on a long-standing customer'
            ELSE 'filed' END AS why_it_stopped
ORDER BY r.started_at
```

```cypher
// [memory] - 8c - the policy itself now holds R7: the rule node every application is SUBJECT_TO
MATCH (a:Application)-[:SUBJECT_TO]->(r:Rule)
RETURN r.key AS rule, r.rule_name AS name, r.kind AS kind, r.threshold AS threshold, count(a) AS applications
ORDER BY r.key
```
