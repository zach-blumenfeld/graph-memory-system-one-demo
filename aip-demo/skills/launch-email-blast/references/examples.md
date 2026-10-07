# Worked examples from the recorded runs

Four agent runs of the SOP, read back from memory. Use these to calibrate claims rulings and body shape.

## Claims rulings that held up

| Brief key message | Approved list says | Ruling |
|---|---|---|
| "One pip install, no changes to existing pipelines" (riverbed 1.8) | No compatibility claim on the list | Keep the install command as the CTA (a factual instruction); drop "no changes to existing pipelines" (a compatibility promise). Log it so the product team can add it. |
| "New CLI command to inspect a checkpoint" (riverbed 1.8) | Not on the list, but a feature fact from the brief | Keep it; describe what it does, do not invent the command's name or syntax. |
| Approved benchmark "120k events/s per core" (riverbed) | On the list | Left out anyway: not a key message, and a throughput figure reads as hype in a short release email or a community digest. |
| "30 days of metrics in an embedded store, nothing else to run" (tidewatch 0.9) | "Stores 30 days of metrics in an embedded time-series store" | Keep the approved wording verbatim; drop "nothing else to run" (a no-dependencies promise). |
| "One command attaches the dashboard to a running riverbed pipeline" (tidewatch 0.9) | "Collects lag, throughput and error metrics from any riverbed pipeline with no code changes" | Show the `tidewatch attach` command because it is the CTA; pair it with the approved claim; do not assert "one command" as a selling point. |
| "No data loss, no config change" (riverbed 1.8.1 hotfix) | Nothing about data loss | Drop "no data loss" and state the approved checkpoint-resume claim instead; keep "no config change" and "drop-in pip install" as upgrade instructions. |
| Brief asks to link the quickstart and changelog, gives no URLs | Product record has docs and repo URLs only | Marked placeholders QUICKSTART_URL and CHANGELOG_URL, flagged in the log for a human to fill before the send. |
| CTA "share a screenshot" with no channel named | | Ask readers to reply to the email: one CTA, no invented community channel. |
| Tutorial topic names another Labs project (mooring) | No approved claims list for it | Name it only as the tutorial topic; make no capability claims about it. |

## A body that passed first time (tidewatch 0.9, pipeline operators, persona Teo the Platform Lead)

````markdown
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
````

Subject lines submitted with it, and the pick: "tidewatch 0.9: attach a dashboard to a running pipeline" (chosen:
names the release and the one thing the reader can do), "tidewatch 0.9 adds per-topic lag alerts" (specific but covers
one of three messages), "What is your riverbed pipeline doing right now?" (most curious, but reads as a teaser, which
this persona treats as hype).

## Subject line picks in the other runs

- Launch, developer persona: "riverbed 1.8: workers resume from a checkpoint" over "Restart a riverbed worker without
  reprocessing" (more curious, but hides the version number a developer scanning for upgrade news wants).
- Hotfix, developer persona: "riverbed 1.8.1 fixes a checkpoint retry bug in 1.8.0" over "Upgrade riverbed to 1.8.1
  today: checkpoint hotfix" ("today" is urgency language the persona dislikes) and "A checkpoint can be written twice
  in riverbed 1.8.0" (could alarm readers before they see the fix).
- Digest, community persona: "Three riverbed tutorials to try this month" (says what the email is, matches the digest
  format) over the checkpoint line (one tutorial only) and the first-pipeline line (skews to the developer persona).

## What the compliance check actually tests

Disclaimer present (first sentence, case-insensitive); none of the banned phrases in the body; no exclamation mark
anywhere in the body; a link or the brief's CTA words in the body; each subject line under 60 characters, no all-caps
word, no spam word. Naming a competitor and unpublished benchmark numbers are brand rules the checker does not test, so
they are on the writer.
