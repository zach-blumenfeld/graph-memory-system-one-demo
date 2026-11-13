You are reading an expense claim's receipt.

Claim id: {claim_id}
Claimed amount: {amount}
Claimed category: {category}
Claim submitted on: {date}
Claimant: {claimant}

Receipt text (may be messy, a photo transcription):

{receipt}

From the receipt text only, find:
- vendor: the merchant name, or an empty string if it cannot be found.
- receipt_date: the date on the receipt as YYYY-MM-DD, or an empty string if it cannot be found or read.
- receipt_total: the receipt's total as a number, or -1 if no total can be found.
- line_items: a list of objects, each with description (string) and amount (number, or -1 if unreadable). Use an empty list if there are no readable items.
- receipt_why: a short explanation of whether the receipt supports the claim: does the total match the claimed amount, and do the vendor and items fit the claimed category? If the vendor, date or total cannot be found, or they disagree with the claim, say the receipt is not clearly supporting.

Do not guess values that are not in the text. Answer with exactly the keys vendor, receipt_date, receipt_total, line_items and receipt_why.
