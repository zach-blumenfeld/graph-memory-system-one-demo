'''Run the exact checks on one expense claim and its receipt.

Pure computation on the claim fields and receipt text given on stdin: no single item over 200,
monthly total no more than 1000, category allowed, receipt present for amounts over 25, claim
date within 30 days of the receipt date, claimant not the approver. Anything that cannot be
established is reported as doubtful. Touches no files, no network and no credentials.
'''
import json
import re
import sys
from datetime import date, datetime

CATEGORIES = ('travel', 'meals', 'software', 'equipment')
FORMATS = ('%Y-%m-%d', '%d %B %Y', '%d %b %Y', '%B %d, %Y', '%b %d, %Y', '%B %d %Y', '%b %d %Y')
MONTH_KEYS = ('monthly_total', 'month_total', 'month_to_date', 'monthly_total_so_far', 'month_to_date_total')


def first(d, keys):
    for k in keys:
        if k in d and d[k] not in (None, ''):
            return d[k]
    return None


def num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        return num(first(v, ('amount', 'value', 'total')))
    if isinstance(v, str):
        cleaned = re.sub('[^0-9.-]', '', v)
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def parse_date(v):
    if not isinstance(v, str):
        return None
    m = re.search('[0-9]{4}-[0-9]{2}-[0-9]{2}', v)
    if m:
        try:
            return date.fromisoformat(m.group(0))
        except ValueError:
            return None
    s = v.replace('.', '').strip()
    for f in FORMATS:
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def find_date(text):
    d = parse_date(text)
    if d:
        return d
    for pat in ('[0-9]{1,2} [A-Za-z]{3,9}[.]? [0-9]{4}', '[A-Za-z]{3,9}[.]? [0-9]{1,2},? [0-9]{4}'):
        m = re.search(pat, text)
        if m:
            d = parse_date(m.group(0))
            if d:
                return d
    return None


def main():
    state = json.load(sys.stdin).get('state', {})
    claim = state.get('claim') or {}
    text = state.get('receipt_text') or ''
    issues = []
    if state.get('load_problems'):
        issues.append('doubtful: ' + str(state['load_problems']))
    if not claim:
        issues.append('doubtful: no claim data could be read')
        print(json.dumps({'exact_ok': False, 'exact_notes': '; '.join(issues)}))
        return

    amount = num(first(claim, ('amount', 'total', 'total_amount')))
    items = claim.get('items') or claim.get('line_items') or []
    item_amounts = []
    if isinstance(items, list):
        for it in items:
            a = num(first(it, ('amount', 'price', 'cost', 'total')) if isinstance(it, dict) else it)
            if a is not None:
                item_amounts.append(a)
    if not item_amounts and amount is not None:
        item_amounts = [amount]

    # (a) no single item over 200
    if amount is None and not item_amounts:
        issues.append('doubtful: claim amount is missing')
    elif item_amounts and max(item_amounts) > 200:
        issues.append('fails: an item of ' + str(max(item_amounts)) + ' is over 200')

    # (b) monthly total no more than 1000
    month = num(first(claim, MONTH_KEYS))
    if amount is not None and amount > 1000:
        issues.append('fails: the claim alone is ' + str(amount) + ', over the 1000 monthly limit')
    elif month is None:
        issues.append('doubtful: the monthly total cannot be established from the claim and receipt alone')
    elif month > 1000:
        issues.append('fails: the monthly total ' + str(month) + ' is over 1000')

    # (c) category
    cat = first(claim, ('category', 'type'))
    if not isinstance(cat, str):
        issues.append('doubtful: category is missing')
    elif cat.strip().lower() not in CATEGORIES:
        issues.append('fails: category ' + cat + ' is not travel, meals, software or equipment')

    # (d) receipt for anything over 25
    if amount is not None and amount > 25 and not text.strip():
        issues.append('fails: no receipt for an amount over 25')

    # (e) submitted within 30 days of the receipt date
    claim_date = parse_date(first(claim, ('date', 'claim_date', 'submitted', 'submitted_date', 'submitted_on')))
    receipt_date = parse_date(first(claim, ('receipt_date', 'purchase_date')))
    if receipt_date is None and text:
        receipt_date = find_date(text)
    if claim_date is None or receipt_date is None:
        issues.append('doubtful: the claim date or the receipt date cannot be established')
    else:
        days = (claim_date - receipt_date).days
        if days > 30:
            issues.append('fails: submitted ' + str(days) + ' days after the receipt date')
        elif days < 0:
            issues.append('doubtful: the receipt is dated after the claim')

    # (f) claimant is not the approver
    claimant = first(claim, ('claimant', 'employee', 'submitted_by'))
    approver = first(claim, ('approver', 'approved_by'))
    if not isinstance(claimant, str) or not isinstance(approver, str):
        issues.append('doubtful: the claimant or the approver is not named')
    elif claimant.strip().lower() == approver.strip().lower():
        issues.append('fails: the claimant is the approver')

    print(json.dumps({'exact_ok': not issues,
                      'exact_notes': '; '.join(issues) if issues else 'all exact checks hold'}))


main()
