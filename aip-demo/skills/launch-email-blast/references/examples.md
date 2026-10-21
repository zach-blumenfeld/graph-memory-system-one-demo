# Worked examples from the recorded runs

Four agent runs of the SOP, read back from memory. Use these to calibrate claims rulings and the shape of the body.

## Claims rulings that held up

| Brief key message | Approved list says | Ruling |
|---|---|---|
| "One pip install, no changes to existing pipelines" (riverbed 1.8) | No compatibility claim on the list | Keep the install command as the call to action (a factual instruction); drop "no changes to existing pipelines" (a compatibility promise). Log it so the product team can add it. |
| "New CLI command to inspect a checkpoint" (riverbed 1.8) | Not on the list, but a feature fact from the brief | Keep it; say the command exists and what it does, point to the quickstart, do not invent its name or syntax. |
| Approved benchmark "120k events/s" (riverbed) | On the list | Left out anyway: not a key message, and a throughput figure reads as hype in a short release email or a community digest. |
| "30 days of metrics in an embedded store, nothing else to run" (tidewatch 0.9) | "Stores 30 days of metrics in an embedded time-series store" | Keep the approved wording; drop "nothing else to run" (a no-dependencies promise). |
| "One command attaches the dashboard to a running riverbed pipeline" (tidewatch 0.9) | "Collects lag, throughput and error metrics from any riverbed pipeline with no code changes" | Show the `tidewatch attach` command because it is the call to action; pair it with the approved claim; do not assert "one command" as a selling point. |
| "No data loss, no config change" (riverbed 1.8.1 hotfix) | Nothing about data loss; no 1.8.1 entry at all | Drop "no data loss" and state the approved checkpoint-resume claim instead; keep the bug description and "drop-in pip install, no config change" as factual release notes. |
| Product record says 1.8.0, brief is about the 1.8.1 hotfix | | Proceed and reference 1.8.1; a hotfix brief naturally precedes the catalog update. Say so in claims_notes so the record gets bumped. |
| Brief asks to link the quickstart and changelog, gives no URLs | Product record has docs and repo URLs only | Link the docs root and the repo releases page; say in claims_notes that a dedicated quickstart URL should replace it if one exists. |
| CTA "share a screenshot" with no channel named | | Ask readers to reply to the email: one CTA, no invented community channel. |
| Tutorial topic names another Labs project (mooring) | mooring has its own list, which mentions a "Confluent-style REST API" | Name mooring as the tutorial topic and use only its approved claims; leave out the one that names a competitor, since the brand guide bans that. |

## A body that passed first time (tidewatch 0.9, pipeline operators, persona Teo the Platform Lead)

````markdown
tidewatch 0.9 is out. You can attach it to a riverbed pipeline you already run and see its lag, throughput and errors without changing the pipeline.

**Attach it to a running pipeline.** Run `tidewatch attach` against a riverbed pipeline and it collects lag, throughput and error metrics from that pipeline with no code changes.

**Set lag thresholds per topic.** tidewatch alerts on consumer lag with per-topic thresholds, so a slow topic raises an alert without the quiet ones adding noise.

**Keep 30 days of history.** Metrics are stored for 30 days in an embedded time-series store.

tidewatch is a Tessera Labs project. It is experimental and community-supported. The source is at https://github.com/tessera-labs/tidewatch and the docs are at https://tessera-labs.example/tidewatch/.

Run `tidewatch attach` on one of your pipelines and share a screenshot of the dashboard by replying to this email.

Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice.
````

Subject lines submitted with it, and the pick: "tidewatch 0.9: attach a dashboard to a running pipeline" (chosen:
names the release and the one thing the reader can do), "tidewatch 0.9 adds per-topic lag alerts" (clear but covers
one of three messages), "What is your pipeline lag right now? tidewatch 0.9" (most curious, but reads as a marketing
hook, which this persona lists as a turn-off).

## Subject line picks in the other runs

- Launch, developer persona (Noor): "riverbed 1.8: pipelines resume from a checkpoint" (48 characters, names the
  product, the version and the concrete behaviour) over "Restart a riverbed worker and pick up where it stopped"
  (more curious, but hides the version) and "riverbed 1.8 checkpoints your pipeline state" (clear but says less
  about what changes for the reader).
- Hotfix, developer persona (Noor): "riverbed 1.8.1: upgrade today for a checkpoint retry fix" (the version, the
  action and the reason in 56 characters) over "Upgrade to riverbed 1.8.1 today" (no reason, reads like a nag) and
  "Checkpoint retry bug in riverbed 1.8.0, fixed in 1.8.1" (leads with the bug rather than what the developer can do).
- Digest, community persona (Sam): "Three riverbed tutorials to try this month" (says exactly what is inside and what
  to do with it) over "What happens when a stream restarts? Three tutorials" (could read as a service notice) and
  "Build your first streaming pipeline with riverbed" (undersells the two other tutorials).

## What the compliance check actually tests

The disclaimer's first sentence present (case-insensitive); none of the banned phrases in the body
(production-ready, enterprise-grade, officially supported, SLA, guaranteed, 100%, best-in-class, unlimited); no
exclamation mark anywhere in the body; a link or most of the brief's call-to-action words in the body; each subject
line under 60 characters, no all-caps word of three letters or more, no "free", "act now" or "last chance". Naming a
competitor and unpublished benchmark numbers are brand rules the checker does not test, so they are on the writer.
