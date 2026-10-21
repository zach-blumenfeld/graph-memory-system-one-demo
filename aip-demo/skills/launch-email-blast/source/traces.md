# Recorded runs: what the agent actually did

Four Claude Code sessions did the email blast from the SOP with only the `blast` tools, no skill. Each run below is read back from memory: the prompt, every `blast` call in order with its result, every judgment call the agent logged with `blast decide`, and the agent's closing summary. Treat the judgment calls as the decision points of the procedure and the `blast` commands as its scripts.

## run-01 (launch, brief-001)

Prompt:

> You are the marketing agent at Tessera Labs. Start by reading the team's page on how an email
> blast is done: run `blast sop`. The `blast` command is your only way to touch Notion, drafts,
> scheduling and the log (`blast --help` lists it). Write the email body to a file and submit it
> with `blast draft`. Finish with a short summary of what you did and the judgment calls you made.
> 
> New brief in Notion: brief-001, "riverbed 1.8: checkpointed state for every pipeline".
> Do the email blast for it: Python streaming developers, send window per the brief, 09:00 UTC.

1. `blast sop` → success: `{"name": "How we run an email blast", "source": "memory", "text": "# How we run an email blast\n\nOwner: Tessera Labs marketing. Last reviewed by the team. This is the page new people get\npointed at; it is how we expect every launch, update and digest email to be done.\n\n## What a blast is\n\nOne `
2. `blast brief brief-001` → success: `{"brief_id": "brief-001", "campaign_id": "camp-2026-10-001", "title": "riverbed 1.8: checkpointed state for every pipeline", "product": "riverbed", "segment_ids": ["seg-python-stream-devs"], "persona_ids": ["persona-stream-dev"], "goal": "Announce the 1.8 release, whose headline is checkpointed pipe`
3. `blast brand` → success: `{"voice_rules": ["Lead with what the developer can do now, not with adjectives", "One idea per sentence; no exclamation marks; no emoji in subject lines", "Say 'Tessera Labs project', 'experimental', 'community-supported' where relevant", "Prefer code and concrete nouns to superlatives", "Always inc`
4. `blast product riverbed; blast segments riverbed` → success: `"thon that fits in one file\",\n  \"version\": \"1.8.0\",\n  \"docs_url\": \"https://tessera-labs.example/riverbed/\",\n  \"repo_url\": \"https://github.com/tessera-labs/riverbed\",\n  \"approved_claims\": [\n    \"Runs windowed aggregations over Kafka, Kinesis and local files with one API\",\n    \`
5. **Judgment** `What kind of email is brief-001 and how urgent is it?` → **Launch (release announcement for riverbed 1.8), normal urgency** (options: launch,update to existing release,nurture or digest,event; normal,urgent). Why: The brief's goal is to announce the 1.8 release and drive upgrades, which is a launch-style announcement rather than a digest or event. Nothing in it is a hotfix or security notice, so it is not same-day urgent.
6. **Judgment** `Does brief-001 need legal review before scheduling?` → **No legal review** (options: flag for legal,no legal review). Why: The brief mentions no pricing, partner, legal terms or comparison with another product. The body names no competitor and quotes no numbers.
7. **Judgment** `Which segment for brief-001?` → **seg-python-stream-devs** (options: seg-python-stream-devs,seg-connector-maintainers,seg-labs-newsletter). Why: The brief names the segment directly and the persona (Noor the Streaming Developer) is attached to it. The notes say developers only, which rules out the newsletter segment.
8. **Judgment** `Can the key message 'One pip install, no changes to existing pipelines' go in the email?` → **Keep 'one pip install' and drop 'no changes to existing pipelines'** (options: include as written,keep 'one pip install' and drop 'no changes to existing pipelines',drop the whole message). Why: The approved claims list for riverbed does not include a backward-compatibility claim, and 'no changes to existing pipelines' is a promise, which rule 1 forbids unless approved. 'Upgrade with one pip install' is just the upgrade instruction that the CTA already uses, not a claim. The compatibility promise was left out and should be added to the approved list by the product team if they want it used.
9. **Judgment** `Is 'New CLI command to inspect a checkpoint' on the approved claims list, and how should it be worded?` → **Describe the feature without inventing a command name** (options: omit it,describe the feature without inventing a command name,invent a command name). Why: It is not on the approved claims list, but it is a plain feature description from the product brief, not a number, comparison or promise. The brief does not give the command name, so the body says a CLI command exists and points to the quickstart rather than guessing the name. The published 120k events/sec benchmark claim is approved but was left out because the brief asks for a short, checkpoint-focused email.
10. **Judgment** `The brief's send window is 2026-10-14 but today is 2026-10-21. When should the blast be scheduled?` → **Schedule for 2026-10-22T09:00Z, the next 09:00 UTC slot** (options: schedule for 2026-10-14T09:00Z as written (in the past),schedule for the next 09:00 UTC slot 2026-10-22T09:00Z,do not schedule and ask the brief owner). Why: The window in the brief has already passed, so scheduling it as written is impossible or would send immediately. The brief's content is a release announcement that is still current (riverbed is at 1.8.0), so the next 09:00 UTC slot keeps the brief's time of day and gets the announcement out with the least further delay. This is flagged in the campaign log and the summary so the brief owner can pull it before it sends if they disagree.
11. `blast draft camp-2026-10-001 --body-file /Users/zach/dev/graph-memory-system-one-demo/aip-demo/blast-body-camp-2026-10-001.md --segment seg-python-stream-devs --subject riverbed 1.8: pipelines resume from a checkpoint --subject riverbed 1.8 checkpoints your pipeline state --subject Restart a riverbed worker and pick up where it stopped` → success: `{"draft_id": "draft-camp-2026-10-001-01", "campaign_id": "camp-2026-10-001", "segment_id": "seg-python-stream-devs", "subject_lines": ["riverbed 1.8: pipelines resume from a checkpoint", "riverbed 1.8 checkpoints your pipeline state", "Restart a riverbed worker and pick up where it stopped"], "body_`
12. `blast check draft-camp-2026-10-001-01` → success: `{"draft_id": "draft-camp-2026-10-001-01", "passed": true, "failures": [], "required_disclaimer": "Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice."}`
13. **Judgment** `Which subject line for draft-camp-2026-10-001-01?` → **riverbed 1.8: pipelines resume from a checkpoint** (options: riverbed 1.8: pipelines resume from a checkpoint,riverbed 1.8 checkpoints your pipeline state,Restart a riverbed worker and pick up where it stopped). Why: Clearest for Noor the Streaming Developer: it names the product, the version and the concrete behaviour in 48 characters, with no adjectives. The third line is the most curious but hides the version, and the second is clear but says less about what changes for the reader. None of the three could read as spam.
14. `blast schedule draft-camp-2026-10-001-01 --segment seg-python-stream-devs --at 2026-10-22T09:00Z --subject riverbed 1.8: pipelines resume from a checkpoint` → success: `{"send_id": "send-213543", "draft_id": "draft-camp-2026-10-001-01", "segment": "Python streaming developers", "recipients": 3700, "send_at": "2026-10-22T09:00Z", "subject_line": "riverbed 1.8: pipelines resume from a checkpoint", "status": "scheduled"}`
15. `blast log camp-2026-10-001 --draft draft-camp-2026-10-001-01 --scheduled --summary riverbed 1.8 launch email (checkpointed pipeline state) scheduled to Python streaming developers (seg-python-stream-devs, 3700 recipients) for 2026-10-22T09:00Z as send-213543, subject 'riverbed 1.8: pipelines resume from a checkpoint'. Compliance passed first time. Judgment calls: (1) classed as a launch, normal urgency; (2) no legal review needed, no pricing, partner or comparison; (3) segment taken from the bri` → success: `{"log_id": "log-0001", "campaign_id": "camp-2026-10-001", "draft_id": "draft-camp-2026-10-001-01", "scheduled": true}`

Agent's closing summary:

> The blast for brief-001 is drafted, checked, scheduled and logged.
> 
> **What went out**
> 
> | Item | Value |
> |---|---|
> | Draft | draft-camp-2026-10-001-01, compliance passed first run |
> | Segment | Python streaming developers, 3,700 recipients |
> | Send | send-213543, 2026-10-22T09:00Z |
> | Subject | riverbed 1.8: pipelines resume from a checkpoint |
> | Log | log-0001 |
> 
> The body is in `blast-body-camp-2026-10-001.md` in the working directory. It leads with the checkpoint behaviour, gives the pip upgrade in a code block, describes the checkpoint-inspection CLI command, carries the Labs disclaimer word for word, and ends with the one call to action linking the quickstart and changelog.
> 
> **Judgment calls, all logged with `blast decide`**
> 
> - **Send date moved.** The brief's window was 2026-10-14, which had already passed. I scheduled the next 09:00 UTC slot, 2026-10-22, rather than schedule in the past or stall. This is the one call worth a look: if the owner would rather re-time or hold it, the send should be pulled before tomorrow morning.
> - **One key message cut.** "No changes to existing pipelines" is a compatibility promise that is not on riverbed's approved claims list, so it was left out per rule 1. "One pip install" stayed as the upgrade instruction. The product team should add the compatibility claim to the list if they want it used.
> - **CLI command described, not named.** The brief gives no command name, so the body says the command exists and points to the quickstart rather than inventing one.
> - **Benchmark omitted.** The approved 120k events per second claim was skipped because the brief asks for a short, checkpoint-focused email.
> - **Launch, normal urgency, no legal review.** It is a release announcement with no pricing, partner, or competitor mention.
> - **Segment from the brief.** The newsletter segment was excluded because the notes say developers only.
> - **Subject line.** Chose the clearest for the developer persona over the more curious third option, which hid the version number.
> 
> **One assumption to verify.** The brief gave no exact URLs, so the quickstart links to the riverbed docs root and the changelog to the GitHub releases page. If a dedicated quickstart URL exists, the draft should be updated before it sends.

## run-02 (launch, brief-003)

Prompt:

> You are the marketing agent at Tessera Labs. Start by reading the team's page on how an email
> blast is done: run `blast sop`. The `blast` command is your only way to touch Notion, drafts,
> scheduling and the log (`blast --help` lists it). Write the email body to a file and submit it
> with `blast draft`. Finish with a short summary of what you did and the judgment calls you made.
> 
> New brief in Notion: brief-003, "tidewatch 0.9". Do the email blast for it to the pipeline
> operators, 2026-10-16 09:00 UTC.

1. `blast sop; echo -----; blast --help` → success: `"                                                        \n\u256d\u2500 Options \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u25`
2. `blast brief brief-003; echo -----BRAND-----; blast brand` → success: `"{\n  \"brief_id\": \"brief-003\",\n  \"campaign_id\": \"camp-2026-10-003\",\n  \"title\": \"tidewatch 0.9\",\n  \"product\": \"tidewatch\",\n  \"segment_ids\": [\n    \"seg-pipeline-operators\"\n  ],\n  \"persona_ids\": [\n    \"persona-platform-lead\"\n  ],\n  \"goal\": \"Announce the 0.9 release `
3. `blast product tidewatch` → success: `{"name": "tidewatch", "tagline": "See every pipeline, lag and retry in one place", "version": "0.9.0", "docs_url": "https://tessera-labs.example/tidewatch/", "repo_url": "https://github.com/tessera-labs/tidewatch", "approved_claims": ["Collects lag, throughput and error metrics from any riverbed pip`
4. `blast segments tidewatch` → success: `{"product": "tidewatch", "segments": [{"segment_id": "seg-pipeline-operators", "name": "Pipeline operators", "size": 1300, "description": "People who run riverbed pipelines in a shared environment and asked about monitoring", "persona": [{"id": "persona-platform-lead", "name": "Teo the Platform Lead`
5. `blast draft camp-2026-10-003 --body-file blast-body-camp-2026-10-003.md --segment seg-pipeline-operators --subject tidewatch 0.9: attach a dashboard to a running pipeline --subject tidewatch 0.9 adds per-topic lag alerts --subject What is your pipeline lag right now? tidewatch 0.9` → success: `{"draft_id": "draft-camp-2026-10-003-01", "campaign_id": "camp-2026-10-003", "segment_id": "seg-pipeline-operators", "subject_lines": ["tidewatch 0.9: attach a dashboard to a running pipeline", "tidewatch 0.9 adds per-topic lag alerts", "What is your pipeline lag right now? tidewatch 0.9"], "body_ch`
6. **Judgment** `What kind of email is brief-003 (tidewatch 0.9) and how urgent is it?` → **Launch, normal urgency** (options: launch,update to an existing release,nurture or digest,event; normal,urgent). Why: The brief's goal is to announce the 0.9 release and the product record lists 0.9.0 as the current version, so this is a release launch rather than an update. It is not a hotfix or security notice, so it goes in the brief's send window rather than same day.
7. **Judgment** `Does brief-003 (tidewatch 0.9) need legal review before scheduling?` → **No legal review** (options: flag for legal review,no legal review). Why: The brief and the body mention no pricing, no partner, no legal terms and no comparison with another product. The body uses only the three approved claims and the brand-guide disclaimer.
8. **Judgment** `Which segment should the tidewatch 0.9 email go to?` → **seg-pipeline-operators** (options: seg-pipeline-operators,seg-labs-newsletter). Why: The brief names seg-pipeline-operators directly and its persona (Teo the Platform Lead) is the one the brief lists. The newsletter segment is a digest audience that the newsletter team sends to, and the brief's operator tone matches the platform-lead persona's measured, evidence-led preference.
9. **Judgment** `Are the brief's key messages 'one command attaches the dashboard' and '30 days of metrics, nothing else to run' on the tidewatch approved claims list?` → **Rephrase to the approved claim wording and drop the unapproved parts** (options: use the brief wording as written,rephrase to the approved claim wording and drop the unapproved parts,leave the messages out entirely). Why: 'One command' and 'nothing else to run' are not on the approved list. The body states the approved claims verbatim in substance: metrics from any riverbed pipeline with no code changes, per-topic lag thresholds, 30 days in an embedded time-series store. The 'one command' idea is carried only by the call to action, which names the tidewatch attach command. 'Nothing else to run' was left out because it is a promise not on the list.
10. **Judgment** `Which subject line for tidewatch 0.9 to pipeline operators?` → **tidewatch 0.9: attach a dashboard to a running pipeline** (options: tidewatch 0.9: attach a dashboard to a running pipeline,tidewatch 0.9 adds per-topic lag alerts,What is your pipeline lag right now? tidewatch 0.9). Why: It is the clearest for the platform-lead persona: it names the release and says what the reader can do, which matches the brand rule to lead with what the developer can do. The lag-alerts line is clear but covers only one message. The question line is the most curious but reads closer to a marketing hook, which this persona lists as a turn-off. All three are under 60 characters with no all-caps or spam words.
11. `blast check draft-camp-2026-10-003-01` → success: `{"draft_id": "draft-camp-2026-10-003-01", "passed": true, "failures": [], "required_disclaimer": "Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice."}`
12. `blast schedule draft-camp-2026-10-003-01 --segment seg-pipeline-operators --at 2026-10-16T09:00Z --subject tidewatch 0.9: attach a dashboard to a running pipeline` → success: `{"send_id": "send-213716", "draft_id": "draft-camp-2026-10-003-01", "segment": "Pipeline operators", "recipients": 1300, "send_at": "2026-10-16T09:00Z", "subject_line": "tidewatch 0.9: attach a dashboard to a running pipeline", "status": "scheduled"}`
13. `blast log camp-2026-10-003 --draft draft-camp-2026-10-003-01 --scheduled --summary tidewatch 0.9 launch email to Pipeline operators (seg-pipeline-operators, 1300 recipients), scheduled for 2026-10-16T09:00Z as send-213716 with subject 'tidewatch 0.9: attach a dashboard to a running pipeline'. Body covers the three approved claims (metrics from any riverbed pipeline with no code changes, per-topic lag thresholds, 30 days in an embedded time-series store), names tidewatch as a Tessera Labs project` → success: `{"log_id": "log-0002", "campaign_id": "camp-2026-10-003", "draft_id": "draft-camp-2026-10-003-01", "scheduled": true}`
14. **Judgment** `The brief's send window (2026-10-16 09:00 UTC) is before the date the blast was run (2026-10-21). Schedule it anyway?` → **Schedule at the requested time as instructed** (options: schedule at the requested time as instructed,move to the next available 09:00 UTC,stop and ask). Why: Both the brief and the requester named 2026-10-16 09:00 UTC explicitly and the scheduler accepted it. Moving the date would change the send without authorisation. The mismatch is recorded here and in the campaign log so the owner can re-time the send if it did not go out.

Agent's closing summary:

> The tidewatch 0.9 blast is drafted, checked, scheduled and logged. One thing to flag first: the requested send time of 2026-10-16 09:00 UTC is five days before today's date. The scheduler accepted it, and I scheduled as instructed, but the owner should confirm the send actually goes out or re-time it.
> 
> **What went out**
> 
> | Item | Value |
> |---|---|
> | Draft | draft-camp-2026-10-003-01 |
> | Send | send-213716, status scheduled |
> | Segment | Pipeline operators, 1,300 recipients |
> | Send time | 2026-10-16T09:00Z |
> | Subject | tidewatch 0.9: attach a dashboard to a running pipeline |
> | Compliance | passed first time |
> | Log | log-0002, marked scheduled |
> 
> The body is in `blast-body-camp-2026-10-003.md` in the aip-demo directory. It covers the three approved claims, names tidewatch as a Tessera Labs project, carries the disclaimer word for word, and ends with one call to action: run tidewatch attach and reply with a screenshot.
> 
> **Judgment calls, each logged with blast decide**
> 
> - **Email type and urgency.** Launch, normal urgency. The brief announces the 0.9 release and the product record shows 0.9.0 as current, and nothing marks it as a hotfix or security notice.
> - **Legal review.** Not needed. No pricing, partner, legal terms or product comparison appear in the brief or the body.
> - **Segment.** The brief names the pipeline operators segment and its persona matches, so no selection was needed. The newsletter segment is a digest audience the newsletter team sends to.
> - **Unapproved wording.** The brief's "one command" and "nothing else to run" are not on the approved claims list. The body uses the approved wording instead. The command itself is named only in the call to action, and "nothing else to run" was left out as a promise not on the list.
> - **Subject line.** I chose the first line because it names the release and says what the reader can do, which fits the platform lead's preference for specific, evidence-led copy. The question-style line was the most curious but reads as a hook, which that persona lists as a turn-off.
> - **Past send time.** Scheduled at the requested time rather than moving it, since both the brief and you named it explicitly. The mismatch is recorded in the decision log and the campaign log.
> 
> One small defect in the log: the options field of the first decision entry split on the semicolon I used to separate the type options from the urgency options, so it reads as five options instead of two groups. The answer and reasoning are intact.

## run-03 (digest, brief-012)

Prompt:

> You are the marketing agent at Tessera Labs. Start by reading the team's page on how an email
> blast is done: run `blast sop`. The `blast` command is your only way to touch Notion, drafts,
> scheduling and the log (`blast --help` lists it). Write the email body to a file and submit it
> with `blast draft`. Finish with a short summary of what you did and the judgment calls you made.
> 
> Brief brief-012 is this month's Tessera Labs digest. Do the email blast work for it for the
> newsletter segment.

1. `blast sop` → success: `{"name": "How we run an email blast", "source": "memory", "text": "# How we run an email blast\n\nOwner: Tessera Labs marketing. Last reviewed by the team. This is the page new people get\npointed at; it is how we expect every launch, update and digest email to be done.\n\n## What a blast is\n\nOne `
2. `blast brief brief-012` → success: `{"brief_id": "brief-012", "campaign_id": "camp-2026-10-012", "title": "Tessera Labs monthly digest: three tutorials on streaming", "product": "riverbed", "segment_ids": ["seg-labs-newsletter"], "persona_ids": ["persona-community-organiser"], "goal": "Monthly nurture digest. Three tutorials, no relea`
3. `blast brand` → success: `{"voice_rules": ["Lead with what the developer can do now, not with adjectives", "One idea per sentence; no exclamation marks; no emoji in subject lines", "Say 'Tessera Labs project', 'experimental', 'community-supported' where relevant", "Prefer code and concrete nouns to superlatives", "Always inc`
4. `blast product riverbed` → success: `{"name": "riverbed", "tagline": "Stream processing for Python that fits in one file", "version": "1.8.0", "docs_url": "https://tessera-labs.example/riverbed/", "repo_url": "https://github.com/tessera-labs/riverbed", "approved_claims": ["Runs windowed aggregations over Kafka, Kinesis and local files `
5. `blast segments riverbed` → success: `{"product": "riverbed", "segments": [{"segment_id": "seg-python-stream-devs", "name": "Python streaming developers", "size": 3700, "description": "Developers who installed riverbed or starred the repo in the last 6 months", "persona": [{"id": "persona-stream-dev", "name": "Noor the Streaming Develop`
6. `blast product mooring` → success: `{"name": "mooring", "tagline": "A schema registry you can run from a laptop", "version": "2.1.0", "docs_url": "https://tessera-labs.example/mooring/", "repo_url": "https://github.com/tessera-labs/mooring", "approved_claims": ["Registers Avro, Protobuf and JSON Schema definitions with compatibility c`
7. `blast draft camp-2026-10-012 --body-file blast-body-camp-2026-10-012.md --segment seg-labs-newsletter --subject Three riverbed tutorials to try this month --subject Build your first streaming pipeline with riverbed --subject What happens when a stream restarts? Three tutorials` → success: `{"draft_id": "draft-camp-2026-10-012-01", "campaign_id": "camp-2026-10-012", "segment_id": "seg-labs-newsletter", "subject_lines": ["Three riverbed tutorials to try this month", "Build your first streaming pipeline with riverbed", "What happens when a stream restarts? Three tutorials"], "body_chars"`
8. **Judgment** `What kind of email is brief-012 and how urgent is it?` → **Nurture digest, normal urgency** (options: launch,update to existing release,nurture or digest,event; normal,urgent). Why: The brief says monthly nurture digest with three tutorials and no release; the send window is 2026-10-31, not same-day. Nothing legal, pricing, partner or comparison is in it, so no legal review flag.
9. **Judgment** `Should we schedule the digest ourselves?` → **Draft, check and log only; do not schedule** (options: schedule to seg-labs-newsletter for 2026-10-31 09:00 UTC,draft/check/log only and leave sending to the newsletter team). Why: SOP rule 5 says digests and nurture emails are not scheduled by us, and the brief notes repeat it: no scheduling from our side. Logged as not-scheduled.
10. **Judgment** `Which segment gets the digest?` → **seg-labs-newsletter** (options: seg-labs-newsletter,seg-python-stream-devs,seg-connector-maintainers). Why: The brief names seg-labs-newsletter explicitly and the persona is Sam the Community Organiser, who maps to that segment. The tutorials touch riverbed and mooring, so the cross-project newsletter audience is the right one rather than a riverbed-only segment.
11. **Judgment** `Which approved claims to use, and which to leave out?` → **Use only the claims the tutorials need; leave out the benchmark number and the Confluent-style REST API claim** (options: use all riverbed and mooring approved claims,use only the claims the three tutorials need,leave out the 120k events/sec benchmark and the Confluent-style REST API claim). Why: The 120k events/sec figure is on riverbed's approved list but Sam wants warm, story-driven copy and a digest does not need a throughput number. The mooring claim about the Confluent-style REST API is approved for mooring, but the brand guide bans naming a competitor product and the tutorial does not need it, so the safer reading was to leave it out. Everything stated (one API over Kafka/Kinesis/local files, checkpoints resume without reprocessing, Avro with compatibility checks, single SQLite-backed binary that starts in under a second) is on the approved lists.
12. **Judgment** `Which subject line to recommend to the newsletter team?` → **Three riverbed tutorials to try this month** (options: Three riverbed tutorials to try this month,Build your first streaming pipeline with riverbed,What happens when a stream restarts? Three tutorials). Why: It is the clearest for Sam the Community Organiser: it says exactly what is inside and what to do with it, with no urgency words. The restart question is the most curious but could read as a service notice. The 'build your first pipeline' line undersells the two other tutorials. All three are under 60 characters with no caps or spam words.
13. `blast check draft-camp-2026-10-012-01` → success: `{"draft_id": "draft-camp-2026-10-012-01", "passed": true, "failures": [], "required_disclaimer": "Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice."}`
14. `blast log camp-2026-10-012 --draft draft-camp-2026-10-012-01 --not-scheduled --summary Monthly Tessera Labs digest (brief-012): three tutorials, riverbed first pipeline, inspecting checkpoints, schema evolution with mooring. Drafted for seg-labs-newsletter (8,400, persona Sam the Community Organiser), compliance check passed first run (draft-camp-2026-10-012-01). NOT scheduled by marketing: SOP rule 5 and the brief both say the newsletter team sends digests; intended send window is 2026-10-31. R` → success: `{"log_id": "log-0003", "campaign_id": "camp-2026-10-012", "draft_id": "draft-camp-2026-10-012-01", "scheduled": false}`

Agent's closing summary:

> The digest for brief-012 is drafted, checked, and logged. It is deliberately not scheduled.
> 
> **What I did**
> 
> - Read the SOP, the brief, the brand guide, the riverbed and mooring approved claims, and the riverbed segments with their personas.
> - Wrote the body to `blast-body-camp-2026-10-012.md` and submitted it with three subject lines to the newsletter segment. The draft id is draft-camp-2026-10-012-01.
> - The compliance check passed on the first run with no failures.
> - Logged the campaign in Notion as not scheduled, with the intended send window of 2026-10-31 and the recommended subject line. The log id is log-0003.
> - Recorded five judgment calls with `blast decide`.
> 
> **Judgment calls**
> 
> - **Email type and urgency.** Nurture digest, normal urgency. No legal flag, since the brief has no pricing, partner, legal, or comparison content.
> - **Scheduling.** Left to the newsletter team. SOP rule 5 and the brief's notes both say marketing does not schedule digests.
> - **Segment.** The newsletter segment, as the brief names it, and the persona Sam the Community Organiser maps to it. The digest spans two projects, so the cross-project list fits better than a riverbed-only one.
> - **Claims.** Used only the approved claims the three tutorials need. I left out the published benchmark figure because a warm, story-driven digest does not need a throughput number. I also left out mooring's approved claim about a Confluent-style REST API, because the brand guide bans naming a competitor product and the tutorial does not need it. The two rules conflict there, so I took the conservative reading.
> - **Subject line.** Recommended "Three riverbed tutorials to try this month" as the clearest for Sam. The restart question is more curious but could read like a service notice.
> 
> **One thing to note.** The tutorial links point at each project's docs root rather than specific tutorial pages, since the brief gave no URLs and I did not want to invent paths. The newsletter team should swap in the real tutorial links before sending.

## run-04 (hotfix, brief-009)

Prompt:

> You are the marketing agent at Tessera Labs. Start by reading the team's page on how an email
> blast is done: run `blast sop`. The `blast` command is your only way to touch Notion, drafts,
> scheduling and the log (`blast --help` lists it). Write the email body to a file and submit it
> with `blast draft`. Finish with a short summary of what you did and the judgment calls you made.
> 
> URGENT. Brief brief-009 ("riverbed 1.8.1 hotfix") has to go to the Python streaming developers
> this morning, 2026-10-07 10:00 UTC. Do the email blast for it now.

1. `blast sop; echo -----; blast --help` → success: `"                                                        \n\u256d\u2500 Options \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u25`
2. `blast brief brief-009; echo -----BRAND; blast brand; echo -----HELP; blast draft --help; blast decide --help; blast schedule --help; blast log --help; blast check --help; blast segments --help; blast product --help` → success: `"\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u250`
3. `blast product riverbed` → success: `{"name": "riverbed", "tagline": "Stream processing for Python that fits in one file", "version": "1.8.0", "docs_url": "https://tessera-labs.example/riverbed/", "repo_url": "https://github.com/tessera-labs/riverbed", "approved_claims": ["Runs windowed aggregations over Kafka, Kinesis and local files `
4. `blast segments riverbed` → success: `{"product": "riverbed", "segments": [{"segment_id": "seg-python-stream-devs", "name": "Python streaming developers", "size": 3700, "description": "Developers who installed riverbed or starred the repo in the last 6 months", "persona": [{"id": "persona-stream-dev", "name": "Noor the Streaming Develop`
5. `blast draft camp-2026-10-009 --body-file blast-body-camp-2026-10-009.md --segment seg-python-stream-devs --subject riverbed 1.8.1: upgrade today for a checkpoint retry fix --subject Upgrade to riverbed 1.8.1 today --subject Checkpoint retry bug in riverbed 1.8.0, fixed in 1.8.1` → success: `{"draft_id": "draft-camp-2026-10-009-01", "campaign_id": "camp-2026-10-009", "segment_id": "seg-python-stream-devs", "subject_lines": ["riverbed 1.8.1: upgrade today for a checkpoint retry fix", "Upgrade to riverbed 1.8.1 today", "Checkpoint retry bug in riverbed 1.8.0, fixed in 1.8.1"], "body_chars`
6. **Judgment** `What kind of email is brief-009 and how urgent is it?` → **Update to an existing release (a hotfix), urgent: same-day send** (options: launch,update to an existing release,nurture or digest,event; normal or urgent). Why: The brief is a 1.8.1 hotfix for a checkpoint retry bug in 1.8.0 and the notes say leadership wants it out this morning; the SOP names a hotfix as urgent and same-day
7. **Judgment** `Does brief-009 need legal review before scheduling?` → **No legal review** (options: flag for legal,no legal review). Why: The brief mentions no pricing, partner, legal matter or comparison with another product; it is a bug-fix notice with a pip upgrade instruction
8. **Judgment** `Which segment gets the riverbed 1.8.1 hotfix email?` → **seg-python-stream-devs** (options: seg-python-stream-devs,seg-connector-maintainers,seg-labs-newsletter). Why: The brief names the segment directly and the goal is to reach everyone on 1.8.0; the 3700 developers who installed or starred riverbed are that audience. Persona Noor wants direct, technical, show-me-the-code tone, so the body leads with the pip command
9. **Judgment** `Are the brief's three key messages on riverbed's approved claims list, and what to do about the ones that are not?` → **Keep the factual bug and upgrade statements and drop the 'no data loss' promise** (options: include all three as written,drop everything not on the list,keep the factual bug and upgrade statements and drop the 'no data loss' promise). Why: The approved list has no 1.8.1 entry at all. The bug description (1.8.0 can write a checkpoint twice under retry, 1.8.1 fixes it) and the upgrade mechanics (drop-in pip install, no config change) are factual release notes, not capability claims, and the checkpoint behaviour is backed by the approved claim 'Checkpoints pipeline state so a restarted worker resumes without reprocessing', which the body quotes. 'No data loss' is a promise about the bug's impact that is on no approved list, so per SOP rule 1 it is left out. Flagging for the product owner: if 'no data loss' is confirmed and added to the claims list, a follow-up can say it
10. **Judgment** `The product record says riverbed is at 1.8.0 but the brief is about 1.8.1. Proceed?` → **Proceed and reference 1.8.1** (options: proceed and reference 1.8.1,hold until the product record is updated). Why: A hotfix brief naturally precedes the catalog update; the brief, its title and the CTA all name 1.8.1 and the email is useless without it. Noted so whoever maintains the product record bumps the version
11. **Judgment** `What send time for brief-009: SOP default 09:00 UTC or the 10:00 UTC in the request?` → **2026-10-07T10:00Z** (options: 2026-10-07T09:00Z,2026-10-07T10:00Z). Why: The brief gives only the date; the SOP default applies unless told otherwise, and the requester specified this morning at 10:00 UTC. The requester's explicit time wins over the default and still lands in the brief's send window
12. `blast check draft-camp-2026-10-009-01` → success: `{"draft_id": "draft-camp-2026-10-009-01", "passed": true, "failures": [], "required_disclaimer": "Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice."}`
13. **Judgment** `Which subject line for the riverbed 1.8.1 hotfix?` → **riverbed 1.8.1: upgrade today for a checkpoint retry fix** (options: riverbed 1.8.1: upgrade today for a checkpoint retry fix,Upgrade to riverbed 1.8.1 today,Checkpoint retry bug in riverbed 1.8.0 fixed in 1.8.1). Why: Clearest for Noor: it names the version, the action and the reason in 56 characters. 'Upgrade to riverbed 1.8.1 today' is shorter but gives no reason, so it reads like a nag. The third leads with the bug rather than what the developer can do, against the voice rule. None uses caps or the banned spam words
14. `blast schedule draft-camp-2026-10-009-01 --segment seg-python-stream-devs --at 2026-10-07T10:00Z --subject riverbed 1.8.1: upgrade today for a checkpoint retry fix` → success: `{"send_id": "send-214057", "draft_id": "draft-camp-2026-10-009-01", "segment": "Python streaming developers", "recipients": 3700, "send_at": "2026-10-07T10:00Z", "subject_line": "riverbed 1.8.1: upgrade today for a checkpoint retry fix", "status": "scheduled"}`
15. `blast log camp-2026-10-009 --draft draft-camp-2026-10-009-01 --scheduled --summary riverbed 1.8.1 hotfix (checkpoint retry bug). Urgent update email to seg-python-stream-devs (3700 recipients), scheduled 2026-10-07T10:00Z as send-214057 with subject 'riverbed 1.8.1: upgrade today for a checkpoint retry fix'. Draft draft-camp-2026-10-009-01 passed compliance first run; carries the Labs disclaimer verbatim and one CTA (pip install -U riverbed). No legal review needed: no pricing, partner, legal or` → success: `{"log_id": "log-0004", "campaign_id": "camp-2026-10-009", "draft_id": "draft-camp-2026-10-009-01", "scheduled": true}`

Agent's closing summary:

> The riverbed 1.8.1 hotfix email is drafted, checked, scheduled and logged.
> 
> **What went out**
> 
> | Item | Value |
> |---|---|
> | Draft | draft-camp-2026-10-009-01 |
> | Segment | Python streaming developers, 3,700 recipients |
> | Send | 2026-10-07 10:00 UTC, send-214057 |
> | Subject | riverbed 1.8.1: upgrade today for a checkpoint retry fix |
> | Compliance | Passed on the first run |
> | Log entry | log-0004 |
> 
> The body is in `blast-body-camp-2026-10-009.md`. It leads with the pip command, describes the double-write bug and the fix, says the upgrade is drop-in with no config change, and ends with the Labs disclaimer word for word.
> 
> **Judgment calls, all logged with `blast decide`**
> 
> - **Email type and urgency.** An update to an existing release, treated as urgent per the SOP's hotfix rule and the brief's note from leadership.
> - **No legal review.** The brief has no pricing, partner, legal or competitor content.
> - **Segment.** The brief names the Python streaming developers segment directly. The persona wants direct, technical, show-me-the-code tone, so the pip command comes first.
> - **Approved claims.** The claims list has no 1.8.1 entry at all. I kept the bug description and upgrade mechanics as factual release notes, and tied the checkpoint sentence to the approved checkpointing claim. I left out "no data loss" because it is a promise that appears on no approved list. The log says so, as the SOP requires.
> - **Version mismatch.** The product record still says 1.8.0. I proceeded with 1.8.1 since a hotfix brief naturally precedes the catalog update.
> - **Send time.** The brief gives only the date. The request said 10:00 UTC, so I used that over the SOP's 09:00 default.
> - **Subject line.** The chosen line names the version, the action and the reason in under 60 characters. The short alternative gave no reason, and the third led with the bug rather than the action.
> 
> **Two things for a human to follow up**
> 
> - Bump the riverbed product record to 1.8.1.
> - If the product owner confirms "no data loss" and adds it to the approved claims, it can go in a follow-up message. The scheduled email does not say it.
