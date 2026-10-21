tidewatch 0.9 is out. You can attach it to a riverbed pipeline you already run and see its lag, throughput and errors without changing the pipeline.

**Attach it to a running pipeline.** Run `tidewatch attach` against a riverbed pipeline and it collects lag, throughput and error metrics from that pipeline with no code changes.

**Set lag thresholds per topic.** tidewatch alerts on consumer lag with per-topic thresholds, so a slow topic raises an alert without the quiet ones adding noise.

**Keep 30 days of history.** Metrics are stored for 30 days in an embedded time-series store.

tidewatch is a Tessera Labs project. It is experimental and community-supported. The source is at https://github.com/tessera-labs/tidewatch and the docs are at https://tessera-labs.example/tidewatch/.

Run `tidewatch attach` on one of your pipelines and share a screenshot of the dashboard by replying to this email.

Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice.
