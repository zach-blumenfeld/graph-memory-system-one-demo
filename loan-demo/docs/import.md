# How the import works

Two commands and five files.

1. `tools/make_fixture.py` invents Lantern Mutual's five systems and writes them to `data/bank/`,
   one JSON file per system (`core_banking`, `loans`, `compliance`, `ownership`, `crm`), each
   `{"system": ..., "as_of": "2026-10-13", "records": {Type: [flat records]}}`, plus the credit team's
   page `sop_assess_loan.md` and the policy as prose `policy.md`. Deterministic: fixed seed, fixed
   dates, generated against the example's "today" (`AS_OF` in `src/loan/policy.py`). Cash flow is
   generated so each business's trailing-twelve-month average net hits its target coverage exactly.
2. `src/loan/fixture.py` reads those files back with typed accessors. `loan verify fixture` runs the
   shared policy engine over the JSON and checks the five expected outcomes.
3. `src/loan/importer.py` turns every record into an entity and every foreign key into an edge.
   Entities go through the memory SDK, `long_term.add_entity(name, type, ...)`, which writes an
   `Entity` node with the type as a second label (`Business`, `Account`, `Month`, `Facility`,
   `Payment`, `Application`, `KycRecord`, `Rule`, `FraudEvent`, `Person`, `RelationshipManager`,
   `Note`, `Playbook`), then the record's fields are set as plain properties with the driver, plus a
   stable `key` (`BUS-01`, `FAC-03`, `MON-101-2026-09`, ...) that every tool cites. The SDK stores
   relationships as one generic `RELATED_TO` edge, so the twelve domain edges are written with the
   driver as real edge types: `OWNS {pct, since}`, `HOLDS`, `HAS_CASHFLOW`, `HAS_FACILITY`,
   `HAS_PAYMENT`, `APPLIED`, `KYC`, `HAD`, `SUBJECT_TO`, `COVERS {since}`, `HAS_NOTE`, `FOLLOWS`.
   One wrinkle: the SDK capitalises the type (`KycRecord` lands as `Kycrecord`), so the importer
   restores the intended label afterwards.
4. `loan import` runs it and counts what landed: 450 entities, 482 edges, and one proof query that
   walks from the application through its owners to another business's missed payments.
   `loan reset --yes` wipes the memory labels to start over. `loan import --rules-only` (step 7)
   updates the `Rule` nodes in place and adds any new rule, keeping every edge earlier decisions made
   to the existing rules.

Decision nodes are not imported. `loan record` creates them when a rationale is filed, and those
are what the next run's `loan precedents` reads.

Two things are imported on purpose that the judgment step must never see: `Person.dob`, and one
CRM note that mentions an owner's age. The procedure's declared inputs exclude
them, and `loan check` rejects a rationale that repeats them.

To see it, in Neo4j Browser on the memory database:

```cypher
MATCH (a:Application {key: 'APP-1001'})<-[:APPLIED]-(b:Business)
MATCH p = (b)-[:HOLDS|HAS_FACILITY|KYC|HAD|HAS_NOTE]->()
MATCH q = (b)<-[:OWNS]-(:Person)-[:OWNS]->(:Business)-[:HAS_FACILITY]->(:Facility)-[:HAS_PAYMENT]->(:Payment {status: 'missed'})
OPTIONAL MATCH r = (:RelationshipManager)-[:COVERS]->(b)
RETURN a, b, p, q, r
```

One application in the middle; one hop out, the five systems' records about the business; two hops
out through `OWNS`, the fact that lives in no single system: an owner's other business and its
missed payments. `queries.md` query 1 has the full version.
