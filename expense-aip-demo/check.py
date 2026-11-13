#!/usr/bin/env python3
"""Right or wrong, at a glance: every run of expense_claim_review on this folder's server, its
status beside the expected one, and a tick or a cross. One screen.

    python3 check.py            # the known outcomes under the policy as briefed
    python3 check.py --v2       # runs on the newest revision are held to the part-3 rule
    python3 check.py --name N   # another procedure name

The server is AIP_SERVER (default http://127.0.0.1:8310). Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request

# The six claims and what the policy gives. "person" means a rule fails, so a person decides;
# in every rehearsal the person declined.
#   C-1001  approved  meals 48.60, The Copper Kettle, receipt total 48.60, no alcohol. Every rule holds.
#   C-1002  approved  software 129.00, Gridline Apps licence, receipt total 129.00. Every rule holds.
#   C-1003  declined  equipment 236.00, one monitor arm at 236.00: a single item over 200. Person.
#   C-1004  declined  meals 86.40, a bottle of Chianti on the bill: alcohol. Person.
#   C-1005  declined  travel 64.00, no receipt, over 25. Person.
#   C-1006  declined  equipment 180.00, the receipt is one 540.00 order of three items: a split. Person.
EXPECTED_V1 = {"C-1001": "approved", "C-1002": "approved", "C-1003": "declined",
               "C-1004": "declined", "C-1005": "declined", "C-1006": "declined"}
# Part 3: the single-item limit moves from 200 to 250. C-1003's 236.00 item now holds; it approves.
EXPECTED_V2 = {**EXPECTED_V1, "C-1003": "approved"}

TICK, CROSS, DASH = "✓", "✗", "–"


def get(server: str, path: str):
    req = urllib.request.Request(server.rstrip("/") + path, headers={"Accept": "application/json"})
    token = os.environ.get("AIP_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def value(v):
    """A choice answers {"value": ...}; anything else is itself."""
    return v.get("value") if isinstance(v, dict) and "value" in v else v


def find(d: dict, keys: tuple[str, ...]):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return value(d[k])
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2", action="store_true", help="hold runs on the newest revision to the part-3 rule")
    ap.add_argument("--name", default="expense_claim_review")
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()
    server = os.environ.get("AIP_SERVER") or "http://127.0.0.1:8310"
    try:
        rows = get(server, f"/runs?name={args.name}&limit={args.limit}")
    except Exception as exc:
        print(f"could not list runs of {args.name} on {server}: {exc}", file=sys.stderr)
        return 2
    newest = None
    try:
        newest = get(server, f"/catalog/{args.name}").get("revision")
    except Exception:
        pass
    print(f"{args.name} on {server}: {len(rows)} run(s)" + (f", newest revision {newest}" if newest else "")
          + (" (--v2 expectations on the newest revision)" if args.v2 else ""))
    print(f"{'RUN':16}  {'REV':5}  {'AGENT':10}  {'SESSION':22}  {'STATUS':7}  {'CLAIM':7}  {'OUTCOME':9}  {'EXPECTED':9}")
    right = wrong = 0
    for row in sorted(rows, key=lambda r: r.get("started") or "", reverse=True):
        try:
            run = get(server, f"/runs/{row['run_id']}")
        except Exception:
            run = {}
        state = run.get("state") or {}
        result = run.get("result") or {}
        claim = find(result, ("claim_id", "id")) or find(state, ("claim_id", "id"))
        if not claim:                            # a build that takes the claim's file path instead
            m = re.search(r"C-\d{4}", json.dumps(state.get("claim_path") or state.get("claim") or ""))
            claim = m.group(0) if m else "?"
        outcome = find(result, ("status",)) if row.get("status") == "done" else None
        rev = row.get("revision")
        table = EXPECTED_V2 if (args.v2 and newest is not None and str(rev) == str(newest) and not row.get("draft")) else EXPECTED_V1
        known = table.get(str(claim), "?")
        if row.get("status") != "done" or outcome is None:
            mark = DASH
        elif outcome == known:
            mark, right = TICK, right + 1
        else:
            mark, wrong = CROSS, wrong + 1
        ident = row.get("identity") or {}
        print(f"{row['run_id']:16}  {('draft' if row.get('draft') else str(rev)):5}  {str(ident.get('agent') or '-')[:10]:10}  "
              f"{str(ident.get('session') or '-')[:22]:22}  {row.get('status', '?'):7}  {str(claim):7}  {str(outcome or '-'):9}  {known:9}  {mark}")
    print(f"\n{right} right, {wrong} wrong, {len(rows) - right - wrong} not finished")
    return 0 if wrong == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
