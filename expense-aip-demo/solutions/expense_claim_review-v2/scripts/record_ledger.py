"""Append one ledger line (claim id, claimant, amount, category, date, status) to
ledger.txt in the working directory. Append only; the file is never overwritten.

Touches only ledger.txt in the run's working directory (AIP_WORKDIR, which is where the
script starts). No outside systems, no credentials.
"""
import json
import os
import sys


def clean(value):
    return str(value).replace("\r", " ").replace("\n", " ").replace(",", ";").strip()


def main():
    state = json.load(sys.stdin)["state"]
    status = str(state.get("status", "")).strip().lower()
    if status not in ("approved", "declined"):
        sys.stderr.write("status must be approved or declined, got: %r\n" % status)
        sys.exit(1)
    fields = [
        state.get("claim_id"),
        state.get("claimant"),
        state.get("amount"),
        state.get("category"),
        state.get("date"),
        status,
    ]
    line = ",".join(clean(f) for f in fields)
    path = os.path.join(os.environ.get("AIP_WORKDIR", "."), "ledger.txt")
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(json.dumps({"ledger_line": line}))


main()
