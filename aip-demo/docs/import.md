# How the import works

The import is two commands and four files.

1. `tools/make_fixture.py` invents the Notion workspace and writes it to `data/notion/`: one JSON
   file per Notion database (products, personas, audience segments, campaign briefs, brand guide,
   channels, campaign log), each page shaped the way the Notion API returns it, plus the SOP page
   as `sop_email_blast.md`.
2. `src/blast/fixture.py` reads those files back and flattens Notion's property objects into plain
   dicts. The `blast` tools in step 2 read the same files.
3. `src/blast/importer.py` turns every page into an entity and every Notion relation into an edge.
   Entities go through the memory SDK, `long_term.add_entity(name, type, ...)`, which writes an
   `Entity` node and adds the type as a second label (`Campaign`, `Product`, `Claim`, `Persona`,
   `Segment`, `Brand`, `Playbook`), then the page's fields are set as plain properties (`brief_id`,
   `send_window`, the SOP's full `text`, ...). The SDK stores every relationship as one generic
   `RELATED_TO` edge with the real type in a property, which is unreadable in Browser, so the six
   domain edges are written with the Neo4j driver as real edge types: `PROMOTES`, `ASSERTS`,
   `TARGETS`, `REPRESENTS`, `CONSTRAINED_BY`, `FOLLOWS`.
4. `blast import` runs it and then counts what landed (`blast verify import` on its own does just
   the count): 42 entities, 75 edges. `blast reset --yes` wipes the database to start over.

No embeddings and no entity extraction are switched on: nothing in this demo needs similarity
search, and the graph stays exactly what was imported plus what the agent did.

To do this with a real Notion workspace, replace item 1. Pull the databases with the Notion API
(`POST /v1/databases/{id}/query` returns pages in the shape the fixture mimics) and drop the JSON
into `data/notion/`. `fixture.py` already reads Notion's property objects. If your databases have
different names or fields, `plan()` in `importer.py` is the one function that maps pages to
entities and edges.

To see it, in Neo4j Browser on the memory database:

```cypher
MATCH (c:Campaign {brief_id: 'brief-001'})
MATCH p = (c)-[]->(n)
OPTIONAL MATCH q = (n)-[:ASSERTS|REPRESENTS]-(m)
RETURN p, q
```

One campaign in the middle. One hop out: the product it promotes, the segment it targets, the
brand guide it must obey, the SOP page it follows. Two hops out: the product's approved claims,
and the persona who represents the segment. About 12 nodes, and each answers one of the questions
the agent must settle before it writes a word: what am I selling, what may I say about it, who am
I talking to, how must I sound, what is the process.

Labels are real, so Browser colours by class out of the box; set the caption to `name`. Change the
`brief_id` to `brief-013` for the live-demo brief, or drop the `{brief_id: ...}` filter and add
`WITH c LIMIT 3` after the first line for a few campaigns side by side. `queries.md` beat 1 has
the same query and the one that prints the SOP page.

