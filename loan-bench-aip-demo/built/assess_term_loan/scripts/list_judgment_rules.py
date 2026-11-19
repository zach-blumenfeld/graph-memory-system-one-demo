"""Read the judgment rules out of the policy as a list, one item per rule, in the policy's order.

stdin:  {"assets": {"policy": <assets/policy.md>}}
stdout: judgment_rules   [{"id": "J1", "name": "Eligible purpose", "statement": <the rule's text>}, ...]

A rule added to the policy as another `### J<n> <name>` heading is another item in the list, and
the loop over the list judges it; nothing else changes.
"""

import json
import sys

import policy_text

payload = json.load(sys.stdin)
try:
    rules = policy_text.judgment_rules(payload["assets"]["policy"])
except policy_text.PolicyError as err:
    sys.exit(f"list_judgment_rules: assets/policy.md: {err}")
json.dump({"judgment_rules": rules}, sys.stdout)
