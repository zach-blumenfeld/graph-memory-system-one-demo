# Stage 3 vs Stage 5 comparison

Generated 2026-10-07T04:01:00+00:00 from `checkpoints/03-runs.json` and `checkpoints/05-skill-run.json`.

| group | runs | avg tool calls | avg turns | avg wall | avg cost |
|---|---|---|---|---|---|
| Stage 3 clean launches (System Two improvising) | 8 | 11.0 | 12.0 | 94s | $0.48 |
| Stage 5 skill runs (distilled SKILL.md loaded) | 2 | 9.0 | 14.5 | 65s | $0.66 |

## Every run

| run | stage | kind | brief | model | calls | turns | wall | cost | tool path |
|---|---|---|---|---|---|---|---|---|---|
| run-01 | 3 (no skill) | clean | brief-001 | default | 11 | 12 | 77s | $0.60 | get_campaign_brief > get_audience_segments > classify_brief > submit_draft > check_brand_compliance > score_subject_lines > submit_draft > check_brand_compliance > score_subject_lines > schedule_send > log_campaign |
| run-02 | 3 (no skill) | clean | brief-002 | default | 11 | 12 | 77s | $0.48 | get_campaign_brief > get_audience_segments > classify_brief > submit_draft > check_brand_compliance > score_subject_lines > submit_draft > check_brand_compliance > score_subject_lines > schedule_send > log_campaign |
| run-03 | 3 (no skill) | clean | brief-003 | default | 11 | 12 | 71s | $0.44 | get_campaign_brief > classify_brief > get_audience_segments > submit_draft > check_brand_compliance > score_subject_lines > submit_draft > check_brand_compliance > score_subject_lines > schedule_send > log_campaign |
| run-04 | 3 (no skill) | clean | brief-004 | default | 11 | 12 | 99s | $0.43 | get_campaign_brief > classify_brief > get_audience_segments > submit_draft > check_brand_compliance > score_subject_lines > submit_draft > check_brand_compliance > score_subject_lines > schedule_send > log_campaign |
| run-05 | 3 (no skill) | clean | brief-005 | default | 11 | 12 | 70s | $0.44 | get_campaign_brief > classify_brief > get_audience_segments > submit_draft > check_brand_compliance > score_subject_lines > submit_draft > check_brand_compliance > score_subject_lines > schedule_send > log_campaign |
| run-06 | 3 (no skill) | clean | brief-006 | default | 11 | 12 | 138s | $0.52 | get_campaign_brief > classify_brief > get_audience_segments > submit_draft > check_brand_compliance > score_subject_lines > submit_draft > check_brand_compliance > score_subject_lines > schedule_send > log_campaign |
| run-07 | 3 (no skill) | clean | brief-007 | default | 11 | 12 | 148s | $0.50 | get_campaign_brief > classify_brief > get_audience_segments > submit_draft > check_brand_compliance > score_subject_lines > submit_draft > check_brand_compliance > score_subject_lines > schedule_send > log_campaign |
| run-08 | 3 (no skill) | clean | brief-008 | default | 11 | 12 | 75s | $0.46 | get_campaign_brief > classify_brief > get_audience_segments > submit_draft > check_brand_compliance > score_subject_lines > submit_draft > check_brand_compliance > score_subject_lines > schedule_send > log_campaign |
| run-11 | 3 (no skill) | escalation | brief-011 | default | 11 | 12 | 223s | $0.61 | get_campaign_brief > classify_brief > get_audience_segments > submit_draft > check_brand_compliance > score_subject_lines > submit_draft > check_brand_compliance > score_subject_lines > schedule_send > log_campaign |
| run-12 | 3 (no skill) | nurture | brief-012 | default | 8 | 9 | 60s | $0.33 | get_campaign_brief > get_audience_segments > classify_brief > submit_draft > check_brand_compliance > submit_draft > check_brand_compliance > log_campaign |
| run-10 | 3 (no skill) | anti-pattern | brief-010 | default | 8 | 9 | 102s | $0.34 | get_campaign_brief > get_audience_segments > submit_draft > check_brand_compliance > submit_draft > check_brand_compliance > schedule_send > log_campaign |
| run-09 | 3 (no skill) | anti-pattern | brief-009 | default | 8 | 9 | 60s | $0.34 | get_campaign_brief > submit_draft > schedule_send! > check_brand_compliance > submit_draft > check_brand_compliance > schedule_send > log_campaign |
| skill-run-brief-013-default | 5 (skill) | skill-run | brief-013 | default | 10 | 16 | 84s | $1.11 | get_campaign_brief > get_audience_segments > classify_brief > submit_draft > check_brand_compliance > submit_draft > check_brand_compliance > score_subject_lines > schedule_send > log_campaign |
| skill-run-brief-013-sonnet | 5 (skill) | skill-run | brief-013 | sonnet | 8 | 13 | 46s | $0.21 | get_campaign_brief > classify_brief > get_audience_segments > submit_draft > check_brand_compliance > submit_draft > check_brand_compliance > score_subject_lines |

Failed calls are marked with `!`. Wall time includes Claude Code startup, the MCP server's Jev startup ping, and NAMS writes (each tool call waits up to 8 s for its record to land).
