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

1. `blast sop; echo ---HELP---; blast --help` → success: `"                                                        \n\u256d\u2500 Options \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u25`
2. `blast brief brief-001; echo ---BRAND---; blast brand; echo ---DRAFT HELP---; blast draft --help; echo ---DECIDE HELP---; blast decide --help; echo ---SCHEDULE HELP---; blast schedule --help; echo ---LOG HELP---; blast log --help; echo ---CHECK HELP---; blast check --help` → success: `"                                      \n Usage: blast log [OPTIONS] {campaign_id}                                       \n                                                                                \n Log the campaign in Notion.                                                    \n             `
3. `blast product riverbed; echo ---SEGMENTS---; blast segments riverbed` → success: `"{\n  \"name\": \"riverbed\",\n  \"tagline\": \"Stream processing for Python that fits in one file\",\n  \"version\": \"1.8.0\",\n  \"approved_claims\": [\n    \"Runs windowed aggregations over Kafka, Kinesis and local files with one API\",\n    \"Checkpoints pipeline state so a restarted worker res`
4. **Judgment** `What kind of email is brief-001 and how urgent is it?` → **A release launch (riverbed 1.8), normal urgency** (options: launch,update to an existing release,nurture or digest,event; normal,urgent same-day). Why: The goal is to announce a new version and drive upgrades. Nothing in the brief is a hotfix or security notice, so it goes out in the brief's send window, not same day.
5. **Judgment** `Does brief-001 need legal review before scheduling?` → **No legal review needed** (options: flag for legal,no legal review needed). Why: The brief has no pricing, partner, legal content or comparison with another product. The body names no competitor and quotes no numbers.
6. **Judgment** `Which segment should receive brief-001?` → **seg-python-stream-devs (Python streaming developers, 3700)** (options: seg-python-stream-devs,seg-connector-maintainers,seg-labs-newsletter). Why: The brief names this segment directly and the persona (Noor the Streaming Developer) matches it. The brief says developers only, which rules out the newsletter. Tone follows the persona notes: direct, technical, show the code, no fluff.
7. **Judgment** `Is the key message 'One pip install, no changes to existing pipelines' on the approved claims list?` → **Include only the install step; leave out 'no changes to existing pipelines'** (options: include as written,include only the install step,leave out entirely). Why: The install command is the CTA and a factual instruction, not a claim. 'No changes to existing pipelines' is a compatibility promise that is not on riverbed's approved claims list, and SOP rule 1 bans promises that are not on it. Dropped and logged here so the product team can add it to the list if they want it said.
8. **Judgment** `Can the email mention the new CLI command to inspect a checkpoint, which is in the brief but not on the approved claims list?` → **Include it without inventing a command name** (options: include it,leave it out,include it without inventing a command name). Why: It is a feature fact from the brief, not a number, comparison or promise, which is what rule 1 guards against. It is also the concrete detail this persona wants. The brief does not give the command's name, so the body describes what it does rather than fabricating syntax. The approved benchmark claim (120k events/s per core) was left out because the brief asks for a short, release-focused email and it is not a key message.
9. **Judgment** `The brief asks to link the quickstart and changelog but gives no URLs. What goes in the body?` → **Use marked placeholders (QUICKSTART_URL, CHANGELOG_URL) and flag them in the log and summary** (options: invent plausible URLs,omit the links,use marked placeholders and flag them). Why: Inventing URLs risks sending broken or wrong links. Omitting them ignores an explicit brief instruction. Placeholders keep the links in place and are easy to search for; the send is seven days out, which leaves time to fill them before 2026-10-14.
10. `blast draft camp-2026-10-001 --body-file /tmp/blast/brief-001-body.md --segment seg-python-stream-devs --subject riverbed 1.8: workers resume from a checkpoint --subject riverbed 1.8 checkpoints your pipeline state --subject Restart a riverbed worker without reprocessing` → success: `{"draft_id": "draft-camp-2026-10-001-01", "campaign_id": "camp-2026-10-001", "segment_id": "seg-python-stream-devs", "subject_lines": ["riverbed 1.8: workers resume from a checkpoint", "riverbed 1.8 checkpoints your pipeline state", "Restart a riverbed worker without reprocessing"], "body_chars": 73`
11. `blast check draft-camp-2026-10-001-01` → success: `{"draft_id": "draft-camp-2026-10-001-01", "passed": true, "failures": [], "required_disclaimer": "Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice."}`
12. **Judgment** `Which of the three subject lines goes out for brief-001?` → **riverbed 1.8: workers resume from a checkpoint** (options: riverbed 1.8: workers resume from a checkpoint,riverbed 1.8 checkpoints your pipeline state,Restart a riverbed worker without reprocessing). Why: Clearest for Noor the Streaming Developer: it names the release and states the one thing the reader can now do, with no adjectives. Option 2 says what the product does rather than what the reader gets. Option 3 is the most curious but hides the release number, which a developer scanning an inbox for upgrade news wants to see. None reads as spam; all are under 60 characters.
13. `blast schedule draft-camp-2026-10-001-01 --segment seg-python-stream-devs --at 2026-10-14T09:00Z --subject riverbed 1.8: workers resume from a checkpoint` → success: `{"send_id": "send-062156", "draft_id": "draft-camp-2026-10-001-01", "segment": "Python streaming developers", "recipients": 3700, "send_at": "2026-10-14T09:00Z", "subject_line": "riverbed 1.8: workers resume from a checkpoint", "status": "scheduled"}`
14. `blast log camp-2026-10-001 --draft draft-camp-2026-10-001-01 --scheduled --summary riverbed 1.8 release announcement (brief-001) to seg-python-stream-devs (3700 recipients), scheduled as send-062156 for 2026-10-14T09:00Z with subject 'riverbed 1.8: workers resume from a checkpoint'. Draft passed compliance on first check. Body covers checkpointed state (approved claim), the pip upgrade step, and the new checkpoint-inspection CLI command, ends with one CTA (upgrade and open the quickstart), and c` → success: `{"log_id": "log-0001", "campaign_id": "camp-2026-10-001", "draft_id": "draft-camp-2026-10-001-01", "scheduled": true}`

Agent's closing summary:

> The blast for brief-001 is drafted, checked, scheduled and logged. One item needs a human before the send date.
> 
> **What went out**
> 
> | Item | Value |
> |---|---|
> | Draft | draft-camp-2026-10-001-01 |
> | Segment | Python streaming developers, 3,700 recipients |
> | Send | 2026-10-14 at 09:00 UTC, send-062156 |
> | Subject | riverbed 1.8: workers resume from a checkpoint |
> | Compliance | Passed on the first check |
> | Log | log-0001 |
> 
> The body is at `/tmp/blast/brief-001-body.md`. It leads with what the reader can now do, shows the upgrade command as code, mentions the checkpoint-inspection CLI command, ends with a single call to action, and carries the Labs disclaimer word for word.
> 
> **Open item.** The brief asked me to link the quickstart and changelog but gave no URLs, and the product record has none either. Rather than invent addresses, I left two marked placeholders, QUICKSTART_URL and CHANGELOG_URL, in the body. Someone needs to fill them before 14 October. This is recorded in the campaign log.
> 
> **Judgment calls**, each logged with `blast decide`:
> 
> - **Email type and urgency.** A release launch at normal urgency. Nothing in the brief is a hotfix or security notice.
> - **Legal review.** Not needed. No pricing, partner, legal content or competitor comparison.
> - **Segment.** The brief named the Python streaming developers segment directly and said developers only, which also ruled out the newsletter list.
> - **Dropped an unapproved promise.** The key message "no changes to existing pipelines" is a compatibility promise that is not on riverbed's approved claims list. I kept the factual install step and left the promise out. The product team can add it to the list if they want it said.
> - **Kept the CLI command mention.** It is a feature fact from the brief, not a number or promise, and it is the concrete detail this persona wants. The brief gave no command name, so I described what it does rather than fabricating syntax.
> - **Left out the benchmark.** The 120k events per second claim is approved but is not a key message, and the brief asked for a short email.
> - **Subject line.** I chose the one that names the release and states what the reader gets. The second option described the product rather than the reader's gain. The third was the most curious but hid the version number, which a developer scanning for upgrade news wants to see.
> 
> One tool denial to note: the sandbox refused a shell loop I used to count subject-line characters, so I counted them by hand. All three are under the 60-character limit.

## run-02 (launch, brief-003)

Prompt:

> You are the marketing agent at Tessera Labs. Start by reading the team's page on how an email
> blast is done: run `blast sop`. The `blast` command is your only way to touch Notion, drafts,
> scheduling and the log (`blast --help` lists it). Write the email body to a file and submit it
> with `blast draft`. Finish with a short summary of what you did and the judgment calls you made.
> 
> New brief in Notion: brief-003, "tidewatch 0.9". Do the email blast for it to the pipeline
> operators, 2026-10-16 09:00 UTC.

1. `blast sop` → success: `{"name": "How we run an email blast", "source": "memory", "text": "# How we run an email blast\n\nOwner: Tessera Labs marketing. Last reviewed by the team. This is the page new people get\npointed at; it is how we expect every launch, update and digest email to be done.\n\n## What a blast is\n\nOne `
2. `blast brief brief-003` → success: `{"brief_id": "brief-003", "campaign_id": "camp-2026-10-003", "title": "tidewatch 0.9", "product": "tidewatch", "segment_ids": ["seg-pipeline-operators"], "persona_ids": ["persona-platform-lead"], "goal": "Announce the 0.9 release of the dashboard and get operators to run it once.", "key_messages": [`
3. `blast brand` → success: `{"voice_rules": ["Lead with what the developer can do now, not with adjectives", "One idea per sentence; no exclamation marks; no emoji in subject lines", "Say 'Tessera Labs project', 'experimental', 'community-supported' where relevant", "Prefer code and concrete nouns to superlatives", "Always inc`
4. `blast product tidewatch` → success: `{"name": "tidewatch", "tagline": "See every pipeline, lag and retry in one place", "version": "0.9.0", "docs_url": "https://tessera-labs.example/tidewatch/", "repo_url": "https://github.com/tessera-labs/tidewatch", "approved_claims": ["Collects lag, throughput and error metrics from any riverbed pip`
5. `blast segments tidewatch` → success: `{"product": "tidewatch", "segments": [{"segment_id": "seg-pipeline-operators", "name": "Pipeline operators", "size": 1300, "description": "People who run riverbed pipelines in a shared environment and asked about monitoring", "persona": [{"id": "persona-platform-lead", "name": "Teo the Platform Lead`
6. **Judgment** `What kind of email is brief-003 and how urgent is it?` → **Release announcement, normal urgency** (options: launch/release announcement (normal),update to existing release (normal),hotfix or security notice (urgent),digest or nurture (not scheduled by us)). Why: The goal is to announce the 0.9 release of the dashboard and get a first run. Nothing in the brief is a fix or a security notice, so it goes in the brief's send window rather than same day. It is a one-off send to a segment, not a digest, so we schedule it.
7. **Judgment** `Does brief-003 need legal review before scheduling?` → **No** (options: yes - flag for legal,no - schedule after compliance). Why: The brief mentions no pricing, legal terms, partner or competitor comparison. All three key messages are product capabilities, and the only external references are the product docs URL.
8. **Judgment** `Which segment should receive the tidewatch 0.9 email?` → **seg-pipeline-operators** (options: seg-pipeline-operators,seg-labs-newsletter). Why: The brief names the segment directly and the request confirms it. The persona (Teo the Platform Lead) matches: people who run riverbed pipelines and asked about monitoring. The newsletter segment is a digest audience and the newsletter team sends to it.
9. **Judgment** `Is 'nothing else to run' (key message 3) on the tidewatch approved claims list?` → **Leave it out** (options: include it as written,rephrase it,leave it out). Why: The approved claim is 'Stores 30 days of metrics in an embedded time-series store'. 'Nothing else to run' is a promise about having no other dependencies, which is not on the list, and the persona is put off by unverifiable claims. The email keeps the 30-day embedded store claim word for word and drops the rest.
10. **Judgment** `Is 'one command attaches the dashboard to a running riverbed pipeline' (key message 1) covered by the approved claims?` → **Show the command and use the approved wording** (options: state 'one command' as a benefit,show the attach command and use the approved 'no code changes' wording,leave it out). Why: The approved claim is 'collects lag, throughput and error metrics from any riverbed pipeline with no code changes'. The CTA itself is 'run tidewatch attach', so showing that single command is describing the CTA rather than making a new claim. The email does not assert 'one command' as a selling point and pairs the command with the approved claim verbatim.
11. **Judgment** `Where should operators share the screenshot the CTA asks for?` → **Reply to this email** (options: reply to this email,open a GitHub issue or discussion,no channel named). Why: The brief does not name a channel. Reply-to keeps it to exactly one call to action with no extra link, and does not commit the repo to a community channel the brief did not mention. Worth confirming with the owner for the next tidewatch send.
12. `blast draft camp-2026-10-003 --body-file /Users/zach/dev/graph-memory-systemone-demo/aip-demo/drafts/camp-2026-10-003-tidewatch-0.9.md --segment seg-pipeline-operators --subject tidewatch 0.9: attach a dashboard to a running pipeline --subject tidewatch 0.9 adds per-topic lag alerts --subject What is your riverbed pipeline doing right now?` → success: `{"draft_id": "draft-camp-2026-10-003-01", "campaign_id": "camp-2026-10-003", "segment_id": "seg-pipeline-operators", "subject_lines": ["tidewatch 0.9: attach a dashboard to a running pipeline", "tidewatch 0.9 adds per-topic lag alerts", "What is your riverbed pipeline doing right now?"], "body_chars`
13. `blast check draft-camp-2026-10-003-01` → success: `{"draft_id": "draft-camp-2026-10-003-01", "passed": true, "failures": [], "required_disclaimer": "Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice."}`
14. **Judgment** `Which subject line for the tidewatch 0.9 email?` → **tidewatch 0.9: attach a dashboard to a running pipeline** (options: tidewatch 0.9: attach a dashboard to a running pipeline,tidewatch 0.9 adds per-topic lag alerts,What is your riverbed pipeline doing right now?). Why: Clearest for Teo the Platform Lead: it names the release and the one thing the reader can do, which is what the CTA asks for. The lag-alerts line is specific but covers only one of three messages. The question line is the most curious but reads closest to a teaser, which this persona treats as hype. All three are under 60 characters with no caps words and no banned spam words.
15. `blast schedule draft-camp-2026-10-003-01 --segment seg-pipeline-operators --at 2026-10-16T09:00Z --subject tidewatch 0.9: attach a dashboard to a running pipeline` → success: `{"send_id": "send-064832", "draft_id": "draft-camp-2026-10-003-01", "segment": "Pipeline operators", "recipients": 1300, "send_at": "2026-10-16T09:00Z", "subject_line": "tidewatch 0.9: attach a dashboard to a running pipeline", "status": "scheduled"}`
16. `blast log camp-2026-10-003 --draft draft-camp-2026-10-003-01 --scheduled --summary tidewatch 0.9 release announcement (brief-003) scheduled to seg-pipeline-operators (1300 recipients) for 2026-10-16T09:00Z as send-064832, subject 'tidewatch 0.9: attach a dashboard to a running pipeline'. Draft draft-camp-2026-10-003-01 passed compliance first time. Classified as a normal-urgency release announcement; no legal review needed (no pricing, partner, legal or competitor content). Key messages 1 and 2 ` → success: `{"log_id": "log-0005", "campaign_id": "camp-2026-10-003", "draft_id": "draft-camp-2026-10-003-01", "scheduled": true}`

Agent's closing summary:

> The tidewatch 0.9 blast is drafted, checked, scheduled and logged.
> 
> **What went out**
> 
> | Item | Value |
> |---|---|
> | Draft | draft-camp-2026-10-003-01 |
> | Segment | Pipeline operators, 1300 recipients |
> | Send | 2026-10-16 09:00 UTC, send-064832 |
> | Subject | tidewatch 0.9: attach a dashboard to a running pipeline |
> | Compliance | passed first run |
> | Log | log-0005 |
> 
> The body is in `drafts/camp-2026-10-003-tidewatch-0.9.md`. It shows the attach command, covers lag alerts with per-topic thresholds and the 30-day embedded store, points to the docs, asks for one screenshot, says tidewatch is a Tessera Labs project, and carries the disclaimer word for word.
> 
> **Judgment calls, all logged with blast decide**
> 
> - **Email type and urgency.** Treated as a normal-urgency release announcement. Nothing in the brief is a hotfix or security notice, and it is not a digest, so we schedule it ourselves.
> - **Legal review.** Not needed. The brief has no pricing, partner, legal or competitor content.
> - **Segment.** Pipeline operators, as the brief and the request both name it. The persona notes fit the audience.
> - **Dropped claim.** Key message three included "nothing else to run". That is not on the approved claims list, so I left it out and kept the approved 30-day embedded store wording.
> - **"One command" wording.** Not asserted as a selling point. The email shows the attach command because the call to action is to run it, paired with the approved "no code changes" claim.
> - **Screenshot channel.** The brief named no channel, so the call to action asks readers to reply to the email. Worth confirming with the brief owner before the next tidewatch send.
> - **Subject line.** Chose the first line because it names the release and the one thing the reader can do. The question-style line was the most curious but reads as a teaser, which this persona dislikes.
> 
> One note on tooling: a shell loop I used to count subject line lengths was denied, so I counted the three lines by hand. All are under the 60-character limit and the compliance check confirmed the subject lines passed.

## run-03 (digest, brief-012)

Prompt:

> You are the marketing agent at Tessera Labs. Start by reading the team's page on how an email
> blast is done: run `blast sop`. The `blast` command is your only way to touch Notion, drafts,
> scheduling and the log (`blast --help` lists it). Write the email body to a file and submit it
> with `blast draft`. Finish with a short summary of what you did and the judgment calls you made.
> 
> Brief brief-012 is this month's Tessera Labs digest. Do the email blast work for it for the
> newsletter segment.

1. `blast sop; echo ---HELP---; blast --help` → success: `"                                                        \n\u256d\u2500 Options \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u25`
2. `blast brief brief-012; echo ---BRAND---; blast brand` → success: `"{\n  \"brief_id\": \"brief-012\",\n  \"campaign_id\": \"camp-2026-10-012\",\n  \"title\": \"Tessera Labs monthly digest: three tutorials on streaming\",\n  \"product\": \"riverbed\",\n  \"segment_ids\": [\n    \"seg-labs-newsletter\"\n  ],\n  \"persona_ids\": [\n    \"persona-community-organiser\"\`
3. `blast product riverbed; echo ---SEGMENTS---; blast segments riverbed; echo ---DRAFT HELP---; blast draft --help; echo ---DECIDE HELP---; blast decide --help; echo ---LOG HELP---; blast log --help; echo ---CHECK HELP---; blast check --help` → success: `"                                      \n Usage: blast log [OPTIONS] {campaign_id}                                       \n                                                                                \n Log the campaign in Notion.                                                    \n             `
4. `blast draft camp-2026-10-012 --body-file /tmp/blast-brief-012/body.md --segment seg-labs-newsletter --subject Three riverbed tutorials to try this month --subject What a riverbed checkpoint actually contains --subject Your first streaming pipeline, in one Python file` → success: `{"draft_id": "draft-camp-2026-10-012-01", "campaign_id": "camp-2026-10-012", "segment_id": "seg-labs-newsletter", "subject_lines": ["Three riverbed tutorials to try this month", "What a riverbed checkpoint actually contains", "Your first streaming pipeline, in one Python file"], "body_chars": 1528}`
5. `blast check draft-camp-2026-10-012-01` → success: `{"draft_id": "draft-camp-2026-10-012-01", "passed": true, "failures": [], "required_disclaimer": "Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice."}`
6. **Judgment** `What kind of email is brief-012 and how urgent is it?` → **Nurture digest, normal urgency** (options: launch,update to existing release,nurture or digest,event; urgent,normal). Why: The brief says monthly nurture digest, three tutorials, no release. Nothing is a hotfix or security notice, so it goes in the normal send window of 2026-10-31.
7. **Judgment** `Should this draft be scheduled by us?` → **Do not schedule** (options: schedule to seg-labs-newsletter for 2026-10-31 09:00 UTC,do not schedule and hand to the newsletter team). Why: SOP rule 5 says digests and nurture emails are not scheduled by marketing; the newsletter team sends them. The brief repeats this in the goal and notes. Draft, check and log only.
8. **Judgment** `Does brief-012 need legal review before it goes out?` → **No legal review needed** (options: flag for legal review,no legal review needed). Why: The brief has no pricing, no partner, no legal language and no comparison with another product. Mooring is referenced only as the name of a tutorial topic, not as a partner or competitor, and the body makes no capability claims about it.
9. **Judgment** `Which audience segment should receive this digest?` → **seg-labs-newsletter** (options: seg-labs-newsletter,seg-python-stream-devs,seg-connector-maintainers). Why: The brief names seg-labs-newsletter explicitly and its persona (Sam the Community Organiser) matches the persona id in the brief. The user instruction also asked for the newsletter segment. Tone written warm and story-driven to match Sam, avoiding anything that reads like a closed beta or sales demo.
10. **Judgment** `Which riverbed approved claims to use, and whether to include the 120k events per second benchmark?` → **Use the one-API windowed aggregation claim and the checkpoint-resume claim; omit the typed connectors claim and the benchmark number** (options: use all four approved claims,use only the claims relevant to the tutorials and omit the benchmark number,make no product claims). Why: Both claims used are word-for-word on the approved list and directly support tutorials 1 and 2. The 120k/sec figure is approved but a performance number does not fit a warm nurture digest for a community persona, and leaving it out removes any risk of it reading as hype. No claims were made about mooring because I have no approved claims list for it; the body only describes what the tutorial covers.
11. **Judgment** `Which subject line to recommend to the newsletter team?` → **Three riverbed tutorials to try this month** (options: Three riverbed tutorials to try this month,What a riverbed checkpoint actually contains,Your first streaming pipeline in one Python file). Why: It is the clearest for Sam the Community Organiser: it says exactly what the email is and matches the digest format readers expect. The checkpoint line is the most curious but describes only one of three tutorials. The first-pipeline line is concrete but skews toward Noor the Streaming Developer rather than the newsletter persona. All three are under 60 characters with no all-caps or spam words.
12. `blast log camp-2026-10-012 --draft draft-camp-2026-10-012-01 --not-scheduled --summary Monthly Tessera Labs digest (brief-012): three riverbed tutorials (first pipeline, inspecting checkpoints, schema evolution with mooring). Drafted for seg-labs-newsletter (8400, persona Sam the Community Organiser) in a warm, story-driven tone. Draft draft-camp-2026-10-012-01 passed compliance on first check with the Labs disclaimer verbatim and one CTA (Pick a tutorial and try it this week). NOT scheduled per` → success: `{"log_id": "log-0003", "campaign_id": "camp-2026-10-012", "draft_id": "draft-camp-2026-10-012-01", "scheduled": false}`

Agent's closing summary:

> The blast work for brief-012 is done: drafted, compliance-checked, logged, and deliberately not scheduled.
> 
> **What I did**
> 
> - Read the SOP, the brief, the brand guide, riverbed's approved claims, and the segment and persona notes.
> - Wrote the digest body for the Tessera Labs newsletter segment in a warm, story-driven tone for Sam the Community Organiser. It covers the three tutorials, ends with the single call to action from the brief, and carries the Labs disclaimer word for word.
> - Submitted it as draft `draft-camp-2026-10-012-01` with three subject lines, all under 60 characters with no spam words.
> - Ran the compliance check. It passed on the first attempt with no failures.
> - Logged six judgment calls and the campaign log entry `log-0003`, marked not scheduled.
> 
> **Judgment calls**
> 
> - **Email type and urgency.** Nurture digest, normal urgency. No release, no hotfix, so it goes in the normal 2026-10-31 window.
> - **Scheduling.** Not scheduled. SOP rule 5 and the brief both say the newsletter team sends digests. I stopped at draft, check and log.
> - **Legal review.** Not needed. No pricing, partner, legal or competitor content. Mooring appears only as a tutorial topic, and the body makes no capability claims about it since I have no approved claims list for it.
> - **Segment.** The brief's named segment and persona agree, so I used the newsletter segment as instructed.
> - **Claims.** I used two approved claims that directly support tutorials 1 and 2, and left out the typed connectors claim and the published benchmark number. A throughput figure does not fit a community digest and adds hype risk for no gain.
> - **Subject line.** I recommended "Three riverbed tutorials to try this month" as the clearest for the persona. The checkpoint line is the most curious but covers one tutorial. The first-pipeline line skews toward the developer persona.
> 
> **Next step for the newsletter team:** pick up the draft and send it to the newsletter segment on 2026-10-31. The body file is at `/tmp/blast-brief-012/body.md` if anyone wants to edit it before send.

## run-04 (hotfix, brief-009)

Prompt:

> You are the marketing agent at Tessera Labs. Start by reading the team's page on how an email
> blast is done: run `blast sop`. The `blast` command is your only way to touch Notion, drafts,
> scheduling and the log (`blast --help` lists it). Write the email body to a file and submit it
> with `blast draft`. Finish with a short summary of what you did and the judgment calls you made.
> 
> URGENT. Brief brief-009 ("riverbed 1.8.1 hotfix") has to go to the Python streaming developers
> this morning, 2026-10-07 10:00 UTC. Do the email blast for it now.

1. `blast sop; echo ---HELP---; blast --help` → success: `"                                                        \n\u256d\u2500 Options \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u25`
2. `blast brief brief-009; echo ---BRAND---; blast brand` → success: `"{\n  \"brief_id\": \"brief-009\",\n  \"campaign_id\": \"camp-2026-10-009\",\n  \"title\": \"riverbed 1.8.1 hotfix: checkpoint retry bug\",\n  \"product\": \"riverbed\",\n  \"segment_ids\": [\n    \"seg-python-stream-devs\"\n  ],\n  \"persona_ids\": [\n    \"persona-stream-dev\"\n  ],\n  \"goal\": \`
3. `blast product riverbed; echo ---SEGMENTS---; blast segments riverbed` → success: `"in one file\",\n  \"version\": \"1.8.0\",\n  \"docs_url\": \"https://tessera-labs.example/riverbed/\",\n  \"repo_url\": \"https://github.com/tessera-labs/riverbed\",\n  \"approved_claims\": [\n    \"Runs windowed aggregations over Kafka, Kinesis and local files with one API\",\n    \"Checkpoints pi`
4. **Judgment** `What kind of email is brief-009 and how urgent is it?` → **Update to an existing release (hotfix), urgent: same-day send** (options: launch,update to existing release,nurture or digest,event; normal or urgent). Why: The brief is a 1.8.1 hotfix for a checkpoint retry bug in 1.8.0. The SOP names a hotfix as urgent and same-day, and the brief notes say leadership wants it out this morning.
5. **Judgment** `Does brief-009 need legal review before scheduling?` → **No legal review needed** (options: flag for legal,no legal review needed). Why: The brief mentions nothing legal, no pricing, no partner, and no comparison with another product. It is a bug-fix notice for our own project.
6. **Judgment** `Which segment should brief-009 go to?` → **seg-python-stream-devs (Python streaming developers, 3700)** (options: seg-python-stream-devs,seg-connector-maintainers,seg-labs-newsletter). Why: The brief names this segment directly and it matches the persona (Noor the Streaming Developer). It is the group that installed riverbed and runs 1.8.0 pipelines. Connector maintainers are not the affected users and the newsletter is a digest list the newsletter team sends.
7. **Judgment** `Is the key message 'No data loss, no config change' on the riverbed approved claims list?` → **Drop 'no data loss'; keep 'no config change' as an upgrade instruction** (options: include both,include 'no config change' only,drop both). Why: 'No data loss' is a promise about product behaviour that is not on the approved claims list and nobody has verified it for us, so SOP rule 1 says leave it out and log it. The closest approved claim is that checkpoints let a restarted worker resume without reprocessing, which the email can state. 'No config change' and 'drop-in pip install' describe the upgrade procedure rather than a product claim, so they stay as instructions.
8. **Judgment** `What send time should brief-009 be scheduled for?` → **2026-10-07T10:00Z** (options: 09:00 UTC SOP default,10:00 UTC as requested). Why: The brief gives only the date 2026-10-07 and says 'this morning'. The request that triggered this blast named 10:00 UTC today, which is within the brief's window and still this morning, so I used that rather than the 09:00 default.
9. `blast draft camp-2026-10-009 --segment seg-python-stream-devs --body-file /Users/zach/dev/graph-memory-systemone-demo/aip-demo/drafts/brief-009-riverbed-1.8.1-hotfix.md --subject riverbed 1.8.1 fixes a checkpoint retry bug in 1.8.0 --subject Upgrade riverbed to 1.8.1 today: checkpoint hotfix --subject A checkpoint can be written twice in riverbed 1.8.0` → success: `{"draft_id": "draft-camp-2026-10-009-01", "campaign_id": "camp-2026-10-009", "segment_id": "seg-python-stream-devs", "subject_lines": ["riverbed 1.8.1 fixes a checkpoint retry bug in 1.8.0", "Upgrade riverbed to 1.8.1 today: checkpoint hotfix", "A checkpoint can be written twice in riverbed 1.8.0"],`
10. `blast check draft-camp-2026-10-009-01` → success: `{"draft_id": "draft-camp-2026-10-009-01", "passed": true, "failures": [], "required_disclaimer": "Tessera Labs projects are experimental and community-supported. They are not covered by support contracts and may change without notice."}`
11. **Judgment** `Which subject line for brief-009?` → **riverbed 1.8.1 fixes a checkpoint retry bug in 1.8.0** (options: riverbed 1.8.1 fixes a checkpoint retry bug in 1.8.0,Upgrade riverbed to 1.8.1 today: checkpoint hotfix,A checkpoint can be written twice in riverbed 1.8.0). Why: Clearest for Noor the Streaming Developer: it names the affected version, the bug, and the fix in one line, and reads as a technical notice rather than marketing. The second line is the most action-oriented but 'today' leans toward urgency language the persona dislikes. The third is the most curious but could alarm readers before they see the fix. None contain spam words, all-caps words, or exceed 60 characters.
12. `blast schedule draft-camp-2026-10-009-01 --segment seg-python-stream-devs --at 2026-10-07T10:00Z --subject riverbed 1.8.1 fixes a checkpoint retry bug in 1.8.0` → success: `{"send_id": "send-064217", "draft_id": "draft-camp-2026-10-009-01", "segment": "Python streaming developers", "recipients": 3700, "send_at": "2026-10-07T10:00Z", "subject_line": "riverbed 1.8.1 fixes a checkpoint retry bug in 1.8.0", "status": "scheduled"}`
13. `blast log camp-2026-10-009 --draft draft-camp-2026-10-009-01 --scheduled --summary riverbed 1.8.1 hotfix notice (brief-009). Draft draft-camp-2026-10-009-01 passed compliance on the first check and is scheduled as send-064217 to seg-python-stream-devs (3700 recipients) at 2026-10-07T10:00Z. Subject: 'riverbed 1.8.1 fixes a checkpoint retry bug in 1.8.0'. Body covers the double checkpoint write under retry in 1.8.0, the fix in 1.8.1, and the drop-in pip upgrade with no config change; one CTA (pip` → success: `{"log_id": "log-0004", "campaign_id": "camp-2026-10-009", "draft_id": "draft-camp-2026-10-009-01", "scheduled": true}`

Agent's closing summary:

> The blast for brief-009 is done and scheduled.
> 
> **What went out**
> 
> | Item | Value |
> |---|---|
> | Draft | draft-camp-2026-10-009-01 |
> | Send | send-064217, scheduled |
> | Segment | Python streaming developers (3,700 recipients) |
> | Send time | 2026-10-07 10:00 UTC |
> | Subject | riverbed 1.8.1 fixes a checkpoint retry bug in 1.8.0 |
> | Compliance | Passed on the first check |
> | Log | log-0004 |
> 
> The body is saved at `drafts/brief-009-riverbed-1.8.1-hotfix.md`. It covers the double checkpoint write under retry in 1.8.0, the fix in 1.8.1, and the drop-in pip upgrade with no config change. It has one call to action and carries the Labs disclaimer word for word.
> 
> **Judgment calls, all logged with `blast decide`**
> 
> - **Email type and urgency.** Classed as an urgent update to an existing release. The SOP treats a hotfix as same-day, and the brief says leadership wants it out this morning.
> - **Legal review.** Not needed. The brief has no legal, pricing, partner, or competitor-comparison content.
> - **Segment.** Took the segment the brief names. It matches the persona and is the group actually running 1.8.0.
> - **Dropped "no data loss."** This is the one place I departed from the brief. It is a promise about product behaviour that is not on the riverbed approved claims list, so rule 1 says leave it out. I replaced it with the approved claim that a restarted worker resumes without reprocessing. "No config change" and "drop-in pip install" stayed, since they describe the upgrade procedure rather than make a product claim. If leadership wants the data-loss reassurance in, someone needs to get it onto the approved claims list first.
> - **Send time.** The brief gives only the date and "this morning." I used the 10:00 UTC from your request rather than the SOP's 09:00 default, since both fall within the brief's window.
> - **Subject line.** Chose the clearest option for a direct, technical reader. The "Upgrade today" variant leaned on urgency language the persona dislikes, and the "written twice" variant could alarm readers before they see there is a fix.
> 
> One thing worth a glance: the persona wants "show me the code," so the body ends with the pip command in a code block as the CTA and includes a one-line version check. If the email programme strips code blocks, that closing CTA should be reviewed in the preview.
