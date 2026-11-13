"""Load the policy rules from assets/rules.json (passed in on stdin as assets.rules)
and print them as the `rules` list.

Touches: no outside systems, no files outside the working directory, no credentials.
"""
import json
import sys


def main():
    data = json.load(sys.stdin)
    rules = json.loads(data["assets"]["rules"])
    print(json.dumps({"rules": rules}))


main()
