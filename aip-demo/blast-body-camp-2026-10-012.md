Hi there,

This month's digest is three tutorials you can work through in an afternoon. No release, no sign-up, nothing to wait for. Each one starts from a blank file and ends with something running on your laptop.

## Tutorial 1: your first riverbed pipeline

riverbed is a Tessera Labs project for stream processing in Python that fits in one file. In this tutorial you read events from a local file, run a windowed aggregation over them, and point the same code at Kafka or Kinesis with one API. By the end you have a pipeline you can read top to bottom.

Start here: https://tessera-labs.example/riverbed/

## Tutorial 2: inspecting checkpoints

What does a stream processor remember when it stops? riverbed checkpoints pipeline state, so a restarted worker resumes without reprocessing. This tutorial opens a checkpoint, walks through what is inside it, and then kills a worker mid-stream to watch it pick up where it left off.

Start here: https://tessera-labs.example/riverbed/

## Tutorial 3: schema evolution with mooring

Schemas change, and streams keep flowing. mooring is a Tessera Labs schema registry you can run from a laptop. It is a single binary backed by SQLite and starts in under a second. In this tutorial you register an Avro schema, add a field, and let the compatibility check tell you whether old readers will still work. Then you wire it into the riverbed pipeline from tutorial 1.

Start here: https://tessera-labs.example/mooring/

## One thing to do this week

Pick a tutorial and try it this week. If you get stuck or find a better way, tell us in the community channel. Both projects are experimental and community-supported, so the people who answer are the people who build them.

Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice.
