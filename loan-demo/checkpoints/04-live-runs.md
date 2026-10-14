# Live runs of the published skill, 2026-10-13

`assess-business-loan` revision 1 (`63c33c7be679ea32`), aip server on localhost:8000 with TypeSafe Jev
as the decision model, fresh headless Claude Code sessions with the `aip-runtime` skill
(`claude -p "Assess application APP-1005 for Pell & Daughters Plumbing."`, recording hooks off so the
memory graph keeps exactly the five free-form traces). Raw wall-clock is the headless session's own
duration; no claim is made beyond it.

## APP-1005, twice (the held-back applicant)

| run | server run | turns | wall | cost | pauses | filed |
|---|---|---|---|---|---|---|
| 1 | af327cd0031948fc | 10 | 174 s | $0.96 | 1 (rationale) | DEC-APP-1005-01, approve, 1.0, revision "1 (63c33c7be679ea32)" |
| 2 | 2965cc7602b84e7f | 13 | 209 s | $1.47 | 1 (rationale) | DEC-APP-1005-02, approve, 1.0, same revision |

Both runs walked gather → hard-rules → by-rules → precedents → by-confidence → rationale → check →
gate → record → end: ten steps, the same ten. The policy returned auto_approve (coverage 1.4, exposure
$1,400,000 under the cap, the owner's 30% holding Wrenfield Mechanical with a current facility), so
the decision model was not asked. The check passed first time in both runs.

The two filed decisions match: same outcome (approve), same fired rules (none), the same 21 cited
keys (APP-1005, BUS-06, FAC-04, FAC-05, BUS-07, PER-09, KYC-BUS-06, NOTE-08, ACC-601, the twelve
Month keys of the coverage window). The second carries `PRECEDENT_FOR` from the first: `loan
precedents` found it and the rationale named it.

Before the first run, one server run (43091c1d509f4923) errored at `gather` with "unknown application
APP-1005": the server process, started days earlier from another folder, carried another demo's
`NEO4J_*` environment, which `loan` inherited. Fix: this folder's `.env` now overrides the
`NEO4J_*` variables (`src/loan/env.py`), so `loan` always talks to its own memory database wherever
it is launched from. The errored run stays in the aip database.

## APP-1004, the gray case

| run | server run | turns | wall | cost | pauses | filed |
|---|---|---|---|---|---|---|
| 1 | 80c5cf706c5848dc | 17 | 195 s | $1.63 | 1 (rationale) | DEC-APP-1004-02, approve, 0.6, revision "1 (63c33c7be679ea32)" |

Eleven steps: gather → hard-rules → by-rules → **assess** → precedents → by-confidence → rationale →
check → gate → record → end. The policy returned review (R3: coverage 1.15 against the 1.25 floor), so
the decision model was asked. Jev answered above every threshold, so the run did not pause for a
review:

| question | answer | confidence / probability |
|---|---|---|
| risk_tier | medium | 0.89 (medium 0.93, high 0.07, low 0.00) |
| connected_exposure_material | false | noul 0.07 (margin 0.43 from 0.5, threshold 0.3) |
| outcome | approve | 0.73 (approve 0.82, counter 0.12, decline 0.06) |

The plan expected this case to pause for a human. It did not: the decision model was confident, and
the evidence it saw (balances of $142,000 and $95,000 against total monthly payments of $10,506.80, a
rising twelve-month trend, a signed ten-year lease and 412 pre-sold founder memberships in the CRM
note) supports approve. G1 applies (7.3 years) but only gates a decline. The run is kept as it
happened. The filed confidence is 0.6, the threshold cleared; the probabilities above live on the
`Answer` nodes in the aip database (`queries.md` beat 6).

The stored input of the `assess` step (StepRun.input in the aip database) holds `figures`, `fired`,
`guidance`, `ownership_summary`, `tenure_years`, `kyc_status`, `crm_notes` and the scrubbed views;
it contains no date of birth and no person's name (checked for the owners' and the relationship
manager's names and birth years).

## APP-1001, revision 1 and revision 2 (the edit beat)

| run | revision | server run | turns | wall | cost | pauses | ended |
|---|---|---|---|---|---|---|---|
| rev 1 | 63c33c7be679ea32 (version "1") | 1daa215641134079 | 15 | 133 s | $1.35 | 1 (review at `assess`) | unfiled: decline on a 6-year customer, G1 |
| rev 2 | 1c4e170b79c08bb1 (version "2") | dea19c49f10944a8 | 13 | 115 s | $1.15 | 1 (review at `assess`) | unfiled: R7 connected exposure over the cap |

Both runs walked gather → hard-rules → by-rules → assess → precedents → by-confidence → end. Both
paused once, at `assess`, because Jev's risk-tier answer fell under the 0.6 threshold on this
application (rev 1: medium 0.60 / high 0.40, confidence 0.4; rev 2: medium 0.51 / high 0.48,
confidence 0.27). The other two answers were firm both times: connected exposure material (noul
0.97) and outcome decline (0.82 / 0.81). The agent answered the review (rev 1: overrode the tier to
high; rev 2: accepted medium).

What changed between them is the policy and one script:

- rev 1, before R7 existed: `fired` = [R5]; the assessed outcome was decline on a customer of 6
  years, so G1 sent it to a human and nothing was filed.
- rev 2, after `loan import --rules-only` added R7 and the procedure's `precedents.py` learned to
  honour a rule with effect `human`: `fired` = [R5, R7]; the run ended for a human because R7
  fired, whatever the judgment said. The note names the rule: "R7 connected_exposure_cap (300000.0
  vs 250000.0) fired".

The aip database holds both runs against their revisions (`queries.md` beat 8b). Neither filed a
Decision in memory, so beat 8's memory-side table shows only the free-form decisions on APP-1001;
the side-by-side is in the aip database.

## Every server run, in order

| server run | revision | application | steps | result |
|---|---|---|---|---|
| 43091c1d509f4923 | 1 | APP-1005 | gather (error) | `loan` inherited another demo's database from the server's environment; fixed in `env.py` |
| af327cd0031948fc | 1 | APP-1005 | 10 | DEC-APP-1005-01 approve 1.0 |
| 2965cc7602b84e7f | 1 | APP-1005 | 10 | DEC-APP-1005-02 approve 1.0, same cites and rules |
| 80c5cf706c5848dc | 1 | APP-1004 | 11 | DEC-APP-1004-02 approve 0.6, Jev confident |
| 1daa215641134079 | 1 | APP-1001 | 7 | unfiled, G1 (decline on a 6-year customer), one review pause |
| dea19c49f10944a8 | 2 | APP-1001 | 7 | unfiled, R7 (connected exposure over the cap), one review pause |
