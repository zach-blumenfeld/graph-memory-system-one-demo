# The graph, in plain terms

This is NAMS's own schema. The SDK and the REST API write into it; we did not design it. Counts
are from the `system-one-demo` workspace after the import, the 12 runs and the distillation.

## Three layers, one graph

**Long-term memory: what the team knows.** Every product, claim, persona, segment, campaign and
brand rule is an `Entity` node. The `type` property says which ontology class it is (`Campaign`,
`Product`, `Claim`, ...). Edges between entities carry the meaning: `PROMOTES`, `ASSERTS`,
`TARGETS`, `CONSTRAINED_BY`, `USES_CHANNEL`, `REPRESENTS`. NAMS also adds its own
`RELATED_TO` edges (with a `predicate` property) when it extracts a relationship from text.

**Short-term memory: what was said.** A `Conversation` has `Message` nodes (`HAS_MESSAGE`), each
with a `role` and `content`. One conversation per recorded run.

**Reasoning memory: what the agent did.** A `Conversation` also has `AgentStep` nodes
(`HAS_STEP`), one per tool call the agent made, with the agent's `reasoning`, the `actionTaken`
and the `result`. Each step `USED_TOOL` a `ToolCall` node holding `toolName`, `input`, `output`,
`status` (`success` or `failure`) and `durationMs`. This is the raw material the skill is
distilled from.

**The skill: what was learned.** A `Skill` has `SkillVersion`s (`HAS_VERSION`). A version
`HAS_STEP` `SkillStep` nodes (the eight steps: `tool`, `inputs`, `outputs`, `expectStatus`,
`why`, `branchType`) and `HAS_COMPONENT` `SkillComponent` nodes (the prose: domain model,
exemplars, success criteria, anti-patterns). Every step and component is `GROUNDED_IN` the
messages, steps, tool calls or entities it was written from, and the version is `DISTILLED_FROM`
everything in its scope. A `DistillationRun` records the job (`DERIVED_BY`), its scores and status.

## How the layers connect

- `Message` and `ToolCall` nodes `MENTIONS` the entities found in their text.
- An `Entity` is `EXTRACTED_FROM` the message, step or tool call it was first seen in.
- An `AgentStep` `INFLUENCED` the entities its tool call touched.
- `GROUNDED_IN` and `DISTILLED_FROM` run from the skill back into all three memory layers. That is
  the provenance chain: skill step, to recorded tool call, to the conversation it happened in.

## Properties worth knowing on `Entity`

| property | meaning |
|---|---|
| `type` | the ontology class |
| `name`, `normName`, `canonicalName` | the name as written, normalised for matching, and the resolved canonical form |
| `sourceStage` | **who created the entity.** Absent (`NULL`) means it was written through the API, which in this repo means the Notion import. `llm` means NAMS's language-model extraction pulled it out of a message or tool call. `spacy` means the statistical named-entity pass found it. `alias` means it was created while resolving a name that matched an existing entity's alias. |
| `confidence` | how sure the extractor was (imported entities get a high default) |
| `mentionCount` | how many messages and tool calls mention it |
| `needsReview` | NAMS thinks it may be a duplicate; see `SAME_AS` |
| `systemAdded` | created by NAMS itself rather than from your content (3 nodes here) |
| `embedding`, `nameEmbedding` | 1024-float vectors for similarity search; this is why queries that return whole nodes are heavy |
| `ontologyVersionId` | which ontology version typed it |
| custom keys (`brief_id`, `campaign_id`, `size`, ...) | whatever the importer passed as properties |

Extracted entities also get extra labels: the ontology class as a label (`:Campaign`,
`:Product`, ...) and a POLE+O label (`:Person`, `:Organization`, `:Event`, `:Object`). Imported
entities only have `:Entity`, so always filter on `type`, not on labels.

## Entity resolution

Two entities NAMS thinks are the same get a `SAME_AS` edge and sit in a review queue; nothing is
merged automatically. `Alias` nodes (`ALIAS_OF` an entity) hold the alternative spellings it has
seen. 3 pairs after the import, 97 after the runs, mostly extracted duplicates of the fixture's
products and campaigns ("riverbed" seen in an email draft becomes a new `Product` until someone
confirms it is the same one).

## Why the graph grows during the runs

NAMS runs its extraction pipeline on every message and tool call that is written, under the
active ontology. So the 42 imported entities became 229 after 12 runs: the agent's drafts
produced new `Claim` entities, CI platforms named in briefs became `Channel`s, and so on. The
`extraction*` properties on `Message`, `AgentStep` and `ToolCall` record that pipeline's status
per node. Use `WHERE e.sourceStage IS NULL` to see only what you imported.

## Counts in this workspace (after everything)

| nodes | n | | relationships | n |
|---|---|---|---|---|
| Entity | 229 | | EXTRACTED_FROM | 1908 |
| AgentStep / ToolCall | 141 / 141 | | MENTIONS | 1461 |
| Alias | 113 | | GROUNDED_IN | 607 |
| Message | 28 | | DISTILLED_FROM | 542 |
| Conversation | 14 | | INFLUENCED | 447 |
| SkillStep / SkillComponent | 16 / 14 | | RELATED_TO | 257 |
| Skill / SkillVersion / DistillationRun | 2 / 2 / 2 | | SAME_AS | 97 |
