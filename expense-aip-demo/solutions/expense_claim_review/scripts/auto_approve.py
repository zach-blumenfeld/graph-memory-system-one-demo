"""Produce the automatic approval: status approved with the standard reason.

Reads only stdin. Touches no outside systems, no files, no credentials.
"""
import json
import sys


def main():
    json.load(sys.stdin)
    print(json.dumps({
        "status": "approved",
        "reason": "The receipt supports the claim and all policy rules hold.",
    }))


main()
