"""Compute the exact facts about an expense claim: amounts against the 200, 1000 and 25
thresholds, the day difference between receipt date and claim date, whether the category
is allowed, whether the receipt text is usable, whether the approver differs from the
claimant, and whether the receipt total matches the claim.

Reads only the JSON on stdin. Touches no outside systems, no files, no credentials.
"""
import json
import sys
from datetime import datetime

FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%d.%m.%Y"]
ALLOWED = {"travel", "meals", "software", "equipment"}


def parse_date(value):
    text = str(value or "").strip()
    if not text:
        return None
    candidates = [text, text[:10]]
    for cand in candidates:
        for fmt in FORMATS:
            try:
                return datetime.strptime(cand, fmt).date()
            except ValueError:
                pass
    return None


def to_number(value):
    try:
        if isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def main():
    state = json.load(sys.stdin)["state"]
    amount = to_number(state.get("amount"))
    total = to_number(state.get("receipt_total"))
    if total is not None and total < 0:
        total = None
    receipt = str(state.get("receipt") or "")
    claimant = str(state.get("claimant") or "").strip().lower()
    approver = str(state.get("approver") or "").strip().lower()
    category = str(state.get("category") or "").strip().lower()

    claim_date = parse_date(state.get("date"))
    receipt_date = parse_date(state.get("receipt_date"))
    days = None
    if claim_date and receipt_date:
        days = (claim_date - receipt_date).days

    items = state.get("line_items")
    amounts = []
    clear = isinstance(items, list) and len(items) > 0
    if clear:
        for item in items:
            raw = item.get("amount") if isinstance(item, dict) else item
            num = to_number(raw)
            if num is None or num < 0:
                clear = False
            else:
                amounts.append(num)
    items_sum = round(sum(amounts), 2) if amounts else None

    usable = len(receipt.strip()) >= 10 and any(ch.isdigit() for ch in receipt)

    facts = {
        "claim_amount": amount,
        "receipt_total": total,
        "claim_over_200": amount is not None and amount > 200,
        "items_over_200": [a for a in amounts if a > 200],
        "line_items_clear": clear,
        "line_items_sum": items_sum,
        "amount_over_1000": amount is not None and amount > 1000,
        "total_over_1000": total is not None and total > 1000,
        "category_allowed": category in ALLOWED,
        "receipt_required": amount is not None and amount > 25,
        "receipt_text_usable": usable,
        "receipt_date_readable": receipt_date is not None,
        "days_between": days,
        "within_30_days": (days is not None and 0 <= days <= 30) if days is not None else None,
        "approver_differs": bool(approver) and approver != claimant,
        "total_matches_claim": (total is not None and amount is not None and abs(total - amount) < 0.005),
        "receipt_total_exceeds_claim": (total is not None and amount is not None and total - amount > 0.005),
    }
    print(json.dumps({"facts": facts}))


main()
