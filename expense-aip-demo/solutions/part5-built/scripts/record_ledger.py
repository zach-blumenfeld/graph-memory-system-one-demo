'''Append one line for a decided claim to ledger.txt.

Appends a single line (claim id, claimant, amount, category, date, status) to ledger.txt in the
run's working directory (AIP_WORKDIR, or the current directory). The date is the claim's date.
Touches no other file, no network and no credentials.
'''
import json
import os
import sys


def first(d, keys):
    for k in keys:
        if k in d and d[k] not in (None, ''):
            return d[k]
    return None


def clean(v):
    if v is None:
        return 'unknown'
    return str(v).replace(',', ' ').replace('\n', ' ').strip()


def main():
    s = json.load(sys.stdin).get('state', {})
    claim = s.get('claim') if isinstance(s.get('claim'), dict) else {}
    fields = [
        clean(s.get('claim_id')),
        clean(first(claim, ('claimant', 'employee', 'submitted_by'))),
        clean(first(claim, ('amount', 'total', 'total_amount'))),
        clean(first(claim, ('category', 'type'))),
        clean(first(claim, ('date', 'claim_date', 'submitted', 'submitted_date', 'submitted_on'))),
        clean(s.get('status')),
    ]
    line = ', '.join(fields)
    path = os.path.join(os.environ.get('AIP_WORKDIR', '.'), 'ledger.txt')
    with open(path, 'a', encoding='utf-8') as f:
        f.write(line + '\n')
    print(json.dumps({'ledger_line': line}))


main()
