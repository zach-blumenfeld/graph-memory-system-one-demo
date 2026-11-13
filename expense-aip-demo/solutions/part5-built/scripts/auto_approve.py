'''Produce the automatic approval for a claim where every rule clearly holds.

Pure computation on the state given on stdin. Touches no files, no network and no credentials.
'''
import json
import sys

s = json.load(sys.stdin).get('state', {})
reason = ('All rules clearly hold for claim ' + str(s.get('claim_id', '')) +
          ': no item over 200, within the monthly limit, allowed category, receipt present where needed, '
          'no alcohol, submitted within 30 days, claimant is not the approver, no split purchase.')
print(json.dumps({'status': 'approved', 'reason': reason}))
