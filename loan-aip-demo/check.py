#!/usr/bin/env python3
"""Right or wrong, at a glance: every run of assess_business_loan on the demo server, its outcome
beside the expected outcome, and a tick or a cross. One screen.

    python check.py            # the known outcomes under policy revision 1
    python check.py --v2       # runs on the newest revision are held to the part-3 policy (APP-1004 approves)
    python check.py --name NAME   # a procedure published under another name (part 4's agent-built one)

The server is AIP_SERVER (default http://127.0.0.1:8300). Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

# What the material gives under policy revision 1 (R1 to R7 as source/policy.md has them).
#   APP-1001  refer    R5 (connected facility 90 days late) and R7 (connected exposure $300,000) fire; R7 goes to a person.
#   APP-1002  approve  no rule fires.
#   APP-1003  decline  R1 (KYC overdue) and R2 (fraud event 4 months ago).
#   APP-1004  refer    R3 (coverage 1.15, review band): the decision model's call. TypeSafe is not sure
#                      (confidence 0.26 to 0.55 across trials, leaning decline), so the procedure refers it, as the
#                      SOP says to. The loan-demo's "approve" was a chat model's judgment, not this model's.
#   APP-1005  refer    R7: the owner holds 30% of a business with a $950,000 facility. The loan-demo's "approve"
#                      predates R7 (added 2026-10-13), which the copied policy carries.
EXPECTED_V1 = {"APP-1001": "refer", "APP-1002": "approve", "APP-1003": "decline", "APP-1004": "refer", "APP-1005": "refer"}
# Part 3: R3's coverage floor moves from 1.25 to 1.10; APP-1004's 1.15 is now an automatic approve, no judgment.
# (Moving the decline line instead, to 1.20, flips nothing visible: G1 sends a decline on a 7-year customer to a person.)
EXPECTED_V2 = {**EXPECTED_V1, "APP-1004": "approve"}

TICK, CROSS, DASH = "\u2713", "\u2717", "\u2013"


def get(server: str, path: str):
    req = urllib.request.Request(server.rstrip("/") + path, headers={"Accept": "application/json"})
    token = os.environ.get("AIP_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2", action="store_true", help="hold runs on the newest revision to the part-3 expectations")
    ap.add_argument("--name", default="assess_business_loan")
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()
    server = os.environ.get("AIP_SERVER") or "http://127.0.0.1:8300"
    if server in ("local", "none"):
        server = "http://127.0.0.1:8300"
    try:
        rows = get(server, f"/runs?name={args.name}&limit={args.limit}")
    except Exception as exc:
        print(f"could not list runs of {args.name} on {server}: {exc}", file=sys.stderr)
        return 2
    newest = None
    try:
        catalog = get(server, f"/catalog/{args.name}")
        newest = catalog.get("revision")
    except Exception:
        pass
    print(f"{args.name} on {server}: {len(rows)} run(s)" + (f", newest revision {newest}" if newest else "") + (" (--v2 expectations on the newest revision)" if args.v2 else ""))
    print(f"{'RUN':16}  {'REV':4}  {'AGENT':10}  {'SESSION':22}  {'STATUS':7}  {'APP':9}  {'OUTCOME':8}  {'EXPECTED':8}  ")
    right = wrong = 0
    for row in sorted(rows, key=lambda r: r.get("started") or "", reverse=True):
        try:
            run = get(server, f"/runs/{row['run_id']}")
        except Exception:
            run = {}
        state = run.get("state") or {}
        result = run.get("result") or {}
        app = result.get("application_id") or state.get("application_id") or "?"
        outcome = result.get("outcome") or (state.get("outcome") if row.get("status") == "done" else None)
        if isinstance(outcome, dict):            # a procedure whose outcome is a choice answers {"value": ...}
            outcome = outcome.get("value")
        rev = row.get("revision")
        known_table = EXPECTED_V2 if (args.v2 and newest is not None and str(rev) == str(newest)) else EXPECTED_V1
        known = known_table.get(app, "?")
        if row.get("status") != "done" or outcome is None:
            mark = DASH
        elif outcome == known:
            mark, right = TICK, right + 1
        else:
            mark, wrong = CROSS, wrong + 1
        ident = row.get("identity") or {}
        print(f"{row['run_id']:16}  {('draft' if row.get('draft') else str(rev)):4}  {str(ident.get('agent') or '-')[:10]:10}  {str(ident.get('session') or '-')[:22]:22}  "
              f"{row.get('status', '?'):7}  {app:9}  {str(outcome or '-'):8}  {known:8}  {mark}")
    print(f"\n{right} right, {wrong} wrong, {len(rows) - right - wrong} not finished")
    return 0 if wrong == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
