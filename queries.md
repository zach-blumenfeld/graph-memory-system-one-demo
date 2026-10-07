# Cypher for the talk, one section per beat

Run these in Neo4j Browser against the workspace database, in the NAMS console query view, or
through `uv run pmm cypher "<query>"` (REST `/v1/query`, read-only). Notes under each query say
what came back when it was run during the build (2026-10-07, Tessera Labs fixture).

Schema in brief (NAMS's own schema; the SDK writes to it when `backend="nams"`):

```
(Conversation)-[:HAS_MESSAGE]->(Message)
(Conversation)-[:HAS_STEP]->(AgentStep)-[:USED_TOOL]->(ToolCall)
(Entity {type})-[:TARGETS|PROMOTES|USES_CHANNEL|CONSTRAINED_BY|ASSERTS|REPRESENTS]->(Entity)
(Skill)-[:HAS_VERSION]->(SkillVersion)-[:HAS_STEP]->(SkillStep)-[:GROUNDED_IN]->(AgentStep|ToolCall)
```

Entities carry the ontology class in `type` (`Campaign`, `Persona`, `Product`, `AudienceSegment`,
`Channel`, `BrandGuideline`, `Claim`) plus the Notion properties the importer copied
(`campaign_id`, `brief_id`, `segment_id`, `size`, `version`, `approved`, ...).

## 1. Memory: the PMM ontology as a graph (beat 1)

The whole long-term layer, as paths so Browser draws it:

```cypher
MATCH p = (c:Entity {type:'Campaign'})-[:PROMOTES|TARGETS|USES_CHANNEL|CONSTRAINED_BY]->(:Entity)
WHERE c.sourceStage IS NULL
OPTIONAL MATCH q = (:Entity {type:'Product'})-[:ASSERTS]->(cl:Entity {type:'Claim'})
WHERE cl.sourceStage IS NULL
OPTIONAL MATCH r = (:Entity {type:'Persona'})-[:REPRESENTS]->(:Entity {type:'AudienceSegment'})
RETURN p, q, r
```

13 campaigns in a ring around 4 products, 6 segments and 4 personas, one Email channel, one brand
guideline that every campaign and product is `CONSTRAINED_BY`, and 13 approved claims hanging off
the products. Set the `Entity` caption to `name` and colour by `type`.

Two sets of counts, because the long-term layer keeps growing after the import. The 42 fixture
entities have no `sourceStage`; everything NAMS extracted from the recorded conversations and tool
calls carries one (`llm`, `alias` or `spacy`):

```cypher
MATCH (e:Entity)
RETURN e.type AS class,
       sum(CASE WHEN e.sourceStage IS NULL THEN 1 ELSE 0 END) AS imported,
       sum(CASE WHEN e.sourceStage IS NOT NULL THEN 1 ELSE 0 END) AS extracted,
       count(*) AS total
ORDER BY total DESC
```

| class | imported | extracted | total after the 12 runs |
|---|---|---|---|
| Claim | 13 | 52 | 65 |
| Campaign | 13 | 46 | 59 |
| Product | 4 | 47 | 51 |
| AudienceSegment | 6 | 12 | 18 |
| Persona | 4 | 10 | 14 |
| Channel | 1 | 13 | 14 |
| BrandGuideline | 1 | 4 | 5 |
| organization / concept / person | 0 | 3 | 3 |

The extracted column is the automatic entity extraction at work: every message and tool I/O the
agent produced was read under the PMM ontology, so "GitHub Actions" became a `Channel`, each email
draft's claims became `Claim` entities, and "riverbed" was re-created as a `Product` many times
over. That is a talking point for beat 1 (memory builds itself from the traces) and a caveat
(entity resolution is a review queue, not a merge): 3 `SAME_AS` pairs right after import, 97 after
the runs. Filter with `WHERE e.sourceStage IS NULL` whenever a query should see only the fixture.

What a campaign is allowed to say, derived from the graph rather than from the brief text:

```cypher
MATCH (c:Entity {type:'Campaign', brief_id:'brief-013'})-[:PROMOTES]->(p:Entity)-[:ASSERTS]->(cl:Entity)
WHERE cl.sourceStage IS NULL
MATCH (c)-[:CONSTRAINED_BY]->(bg:Entity {type:'BrandGuideline'})
RETURN c.name AS campaign, p.name AS product, collect(cl.name) AS approved_claims,
       bg.required_disclaimer AS disclaimer
```

The entity-resolution pairs NAMS flagged on import (names that look alike):

```cypher
MATCH (a:Entity)-[s:SAME_AS]->(b:Entity)
RETURN a.name, b.name, a.type, b.type, s
```

Three pairs right after import, all campaigns of the same product with similar titles; 97 pairs
after the 12 runs, mostly extracted duplicates of the fixture's products and campaigns. They sit in
the review queue; nothing was merged.

## 2. Traces: every run as a path of tool calls (beat 2)

Failed calls are marked with `!`. Conversation metadata carries `runKind`, `runId`, `briefId`,
`product`, `segmentId`, `model`.

```cypher
MATCH (c:Conversation)-[:HAS_STEP]->(s:AgentStep)-[:USED_TOOL]->(t:ToolCall)
WITH c, s, t ORDER BY s.createdAt, t.createdAt
WITH c, collect(t.toolName + CASE t.status WHEN 'failure' THEN '!' ELSE '' END) AS path
RETURN c.metadata AS run, size(path) AS calls,
       reduce(p = '', x IN path | p + CASE p WHEN '' THEN '' ELSE ' > ' END + x) AS tool_path
ORDER BY run
```

Observed: 15 conversations (12 Stage 3 runs and 3 Stage 5 skill runs), 159 tool calls. All eight
clean runs share `brief > classify > segments > draft > comply > score > draft > comply > score >
schedule > log`; run-02 looped five times on the claims check; run-10 is the anti-pattern
(`… draft > schedule! > comply > draft > comply > schedule > log`); run-12 (nurture) has no
classify, scoring or schedule.

The transition graph the distiller clusters (consecutive tool pairs, weighted by how many runs
took that edge):

```cypher
MATCH (c:Conversation)-[:HAS_STEP]->(s:AgentStep)-[:USED_TOOL]->(t:ToolCall)
WITH c, s, t ORDER BY s.createdAt, t.createdAt
WITH c, collect(t.toolName) AS seq
UNWIND range(0, size(seq)-2) AS i
WITH seq[i] AS from_tool, seq[i+1] AS to_tool, count(*) AS runs
RETURN from_tool, to_tool, runs ORDER BY runs DESC, from_tool
```

Observed: `submit_draft > check_brand_compliance` 32, `check_brand_compliance > score_subject_lines`
25, `score_subject_lines > submit_draft` 16 (the redraft loop), `schedule_send > log_campaign` 12,
`score_subject_lines > schedule_send` 10; the detours `check_brand_compliance > schedule_send` 2 and
`check_brand_compliance > log_campaign` 1 belong to the anti-pattern and nurture runs.

The anti-pattern moment: the failed `schedule_send` and what the agent did next.

```cypher
MATCH (c:Conversation)-[:HAS_STEP]->(bad:AgentStep)-[:USED_TOOL]->(t:ToolCall {status:'failure'})
MATCH (c)-[:HAS_STEP]->(next:AgentStep) WHERE next.createdAt > bad.createdAt
WITH c, bad, t, next ORDER BY next.createdAt
WITH c, bad, t, head(collect(next)) AS next
RETURN c.metadata AS run, t.toolName AS failed_tool, t.output AS error, next.actionTaken AS next_action
```

Observed: run-10's `schedule_send` failed with "Brand compliance has not passed for
draft-camp-2026-10-010-05 (status: unchecked)" and the very next action was
`check_brand_compliance`. The second row is a Sonnet skill run that called `score_subject_lines`
before any draft existed.

One trace as a graph, with the typed I/O on the `ToolCall` nodes (set the caption to `toolName`):

```cypher
MATCH trace = (c:Conversation)-[:HAS_STEP]->(a:AgentStep)-[:USED_TOOL]->(t:ToolCall)
WHERE c.metadata CONTAINS 'run-01'
OPTIONAL MATCH msgs = (c)-[:HAS_MESSAGE]->(:Message)
RETURN trace, msgs
```

## 4. System One: where Jev lives, as recorded (beat 4)

Jev's typed answers are inside `ToolCall.output` of the three decision tools. Pull the
classification of every brief out of the recorded JSON:

```cypher
MATCH (c:Conversation)-[:HAS_STEP]->(:AgentStep)-[:USED_TOOL]->(t:ToolCall {toolName:'classify_brief', status:'success'})
WITH c.metadata AS run, apoc.convert.fromJsonMap(t.output) AS o
RETURN run, o.campaign_type.choice AS type, o.campaign_type.confidence AS type_conf,
       o.urgency.level AS urgency, o.needs_legal_review.noul AS p_legal,
       size(o.review_required) AS review_items
ORDER BY run
```

(Without APOC, `RETURN run, t.output` and read the JSON.) Which compliance checks failed, how often:

```cypher
MATCH (:AgentStep)-[:USED_TOOL]->(t:ToolCall {toolName:'check_brand_compliance', status:'success'})
WITH t.output AS o
RETURN CASE WHEN o CONTAINS '"passed": true' THEN 'passed' ELSE 'failed' END AS verdict, count(*) AS n
```

Observed: 18 failed, 15 passed. Every first draft failed `has_labs_disclaimer`; every second draft
passed. System One told System Two exactly what was missing.

The escalations: every decision call where Jev asked a human (or the System Two model) to decide.

```cypher
MATCH (c:Conversation)-[:HAS_STEP]->(s:AgentStep)-[:USED_TOOL]->(t:ToolCall)
WHERE t.toolName IN ['classify_brief','check_brand_compliance','score_subject_lines']
  AND t.status = 'success' AND NOT t.output CONTAINS '"review_required": []'
RETURN c.metadata AS run, t.toolName AS tool, s.result AS observation
ORDER BY run
```

## 3. Distillation: from a skill step back to the moment it came from (beat 3)

```cypher
MATCH (sk:Skill)-[:HAS_VERSION]->(v:SkillVersion)-[:HAS_STEP]->(st:SkillStep)
OPTIONAL MATCH (st)-[:GROUNDED_IN]->(g)
OPTIONAL MATCH (c:Conversation)-[:HAS_STEP]->(g)
RETURN sk.name AS skill, sk.status AS status, st.position + 1 AS n, st.name AS step, st.tool AS bound_tool,
       st.expectStatus AS expected, labels(g)[0] AS grounded_in, c.metadata AS source_run
ORDER BY skill, n
```

What each distillation run saw and decided (Created vs Withheld), straight from the graph:

```cypher
MATCH (r:DistillationRun)
RETURN r.id AS run, r.status AS status, r.scopeJson AS scope, r.groundingScore AS grounding,
       r.coverageScore AS coverage, r.error AS error, r.completedAt AS at
ORDER BY at
```

Three runs on 2026-10-06: the trial on run-01 alone, the clean 8-conversation scope (published) and
the workspace scope (in review). All three `succeeded` with grounding 1.0 and coverage 1.0; the
multi-procedure gate did not fire for this workspace (see BUILD-LOG.md item 5). The
`SkillVersion` node also carries `coherenceScore`, `coherenceClusterConvIds`,
`procedureDegradeReason`, `qualityReport`, `piiScanStatus`, `specLintStatus` and the `skillMd`
text itself.

The published skill grounded in its evidence, as a graph (Skill in the middle, steps and
components around it, each with a `GROUNDED_IN` edge into the recorded trace):

```cypher
MATCH p = (sk:Skill {status:'published'})-[:HAS_VERSION]->(:SkillVersion)
          -[:HAS_STEP|HAS_COMPONENT]->(part)-[:GROUNDED_IN]->(evidence)
OPTIONAL MATCH q = (evidence)-[:USED_TOOL]->(:ToolCall)
OPTIONAL MATCH r = (:Conversation)-[:HAS_STEP|HAS_MESSAGE]->(evidence)
RETURN p, q, r
```

Drift check: does every bound step still agree with what the tool actually did?

```cypher
MATCH (sk:Skill)-[:HAS_VERSION]->(v:SkillVersion)-[:HAS_STEP]->(st:SkillStep)-[:GROUNDED_IN]->(t:ToolCall)
RETURN sk.name AS skill, st.position + 1 AS n, st.name AS step, st.tool AS tool,
       st.expectStatus AS expected, t.status AS recorded,
       CASE WHEN st.expectStatus = t.status THEN 'ok' ELSE 'CONTRADICTED' END AS verdict
ORDER BY verdict DESC, n
```

Observed: all eight published steps expect `success` and every grounding `ToolCall` recorded
`success`; no contradictions. The governance route (`GET /v1/skills/governance`) additionally
flags the three skills as duplicates (shared-source overlap 1.0 and 0.86).

## 5. Run it: the skill run next to the runs it was learned from (beat 5)

```cypher
MATCH (c:Conversation)-[:HAS_STEP]->(s:AgentStep)-[:USED_TOOL]->(t:ToolCall)
WITH c, s, t ORDER BY s.createdAt, t.createdAt
WITH c, collect(t.toolName + CASE t.status WHEN 'failure' THEN '!' ELSE '' END) AS path
RETURN CASE WHEN c.metadata CONTAINS 'skill-run' THEN 'stage 5 (with skill)' ELSE 'stage 3 (no skill)' END AS stage,
       c.metadata AS run, size(path) AS calls,
       reduce(p = '', x IN path | p + CASE p WHEN '' THEN '' ELSE ' > ' END + x) AS tool_path
ORDER BY stage DESC, run
```

Which recorded runs the published skill would have covered exactly (successful calls only):

```cypher
MATCH (sk:Skill {status:'published'})-[:HAS_VERSION]->(v:SkillVersion)-[:HAS_STEP]->(st:SkillStep)
WITH v, st ORDER BY st.position
WITH collect(st.tool) AS skill_tools
MATCH (c:Conversation)-[:HAS_STEP]->(s:AgentStep)-[:USED_TOOL]->(t:ToolCall) WHERE t.status = 'success'
WITH skill_tools, c, s, t ORDER BY s.createdAt
WITH skill_tools, c, collect(DISTINCT t.toolName) AS used
RETURN c.metadata AS run, size([x IN skill_tools WHERE x IN used]) AS covered, size(skill_tools) AS skill_steps,
       [x IN skill_tools WHERE NOT x IN used] AS missing, [x IN used WHERE NOT x IN skill_tools] AS extra
ORDER BY covered DESC, run
```

Observed: all eight clean runs, the escalation run and the completed skill run cover all 8 steps;
the nurture run covers 5 (no classify, scoring or schedule); the Sonnet skill runs cover 6 (they
stopped at the legal-review escalation before scheduling).
