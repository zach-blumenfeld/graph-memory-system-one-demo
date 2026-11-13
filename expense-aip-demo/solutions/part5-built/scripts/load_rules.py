'''Load the judgement rules from the policy asset.

Reads only the assets text given on stdin (assets/judgement_rules.json, a JSON list of rule
strings). Touches no files, no network and no credentials.
'''
import json
import sys

req = json.load(sys.stdin)
text = req.get('assets', {}).get('judgement_rules', '[]')
rules = json.loads(text)
print(json.dumps({'rules': [str(r) for r in rules]}))
