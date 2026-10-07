# tidewatch 0.9 is out

You can now attach a tidewatch dashboard to a riverbed pipeline that is already running.

```
tidewatch attach <pipeline>
```

tidewatch collects lag, throughput and error metrics from any riverbed pipeline with no code changes.

## What is in 0.9

- Alerts on consumer lag with per-topic thresholds. Set a threshold on the topics you care about and leave the rest alone.
- 30 days of metrics in an embedded time-series store.

Docs: https://tessera-labs.example/tidewatch/

## Try it on one pipeline

Run `tidewatch attach` against one of your pipelines and reply to this email with a screenshot of the dashboard.

tidewatch is a Tessera Labs project.

Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice.
