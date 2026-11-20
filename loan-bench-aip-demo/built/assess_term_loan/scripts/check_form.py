"""The form check: read the fields out of one application, check completeness, then every hard
rule H1 to H7. Arithmetic and lookups only; nothing here is a judgment.

stdin:  {"state": {"application_file": <the form's file, a path under the run's working directory>},
         "assets": {"policy": <assets/policy.md>}}
stdout: application      the form's text, exactly as the file holds it, for the steps that read it
        application_id   the id on the form ("" when the form has none)
        form_status      incomplete | failed | passed
        missing_items    what is missing, in the form's order then the policy's: {"name", "kind",
                         "written"}; kind is "empty field", "unreadable field" or "absent document"
        hard_rule_results  one {"rule", "name", "passed", "figure", "threshold"} per hard rule,
                         all seven even after one fails; empty when the application is incomplete,
                         because no other rule is applied to an incomplete application
        loan             {"amount_requested", "term_months", "quoted_monthly_payment"}

Every threshold and the list of required documents is read from the policy text. The layout of
the form (which fields sections 1 to 3 hold) is the form's, and is the table below.
"""

from __future__ import annotations

import datetime
import json
import re
import sys
from decimal import ROUND_HALF_UP, Decimal

import policy_text

# Sections 1 to 3 of the application form, in the form's order. {years} is the policy's
# bankruptcy window (H5): the form must ask about the window the policy rules on.
FORM_FIELDS = {
    1: ["Legal name", "Kind of business", "Operating since", "Annual revenue, last fiscal year",
        "Average monthly net income, last 12 months", "Existing monthly debt payments"],
    2: ["Amount requested", "Term in months", "Quoted monthly payment"],
    3: ["Guarantor credit score", "Bankruptcy in the last {years} years", "Unpaid tax liens",
        "Payments 30 or more days late in the last 12 months"],
}
HEADER_FIELDS = ["Application", "Received"]
DOCUMENTS_SECTION = 4
PLACEHOLDERS = {"n/a", "na", "tbd", "tbc"}
MONTHS = {name: i + 1 for i, name in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"])}
MONTHS.update({name[:3]: number for name, number in list(MONTHS.items())})


def key(text: str) -> str:
    """A label or a document name for comparison: case and spacing do not matter."""
    return " ".join(text.replace("*", "").split()).casefold().rstrip(".")


def is_empty(value: str) -> bool:
    """No value: nothing written, only punctuation (a dash, a line of underscores), or a placeholder."""
    return not re.sub(r"[\W_]+", "", value) or value.strip().casefold() in PLACEHOLDERS


# ------------------------------------------------------------------ reading the form

def split_sections(text: str) -> tuple[list[str], dict[int, list[str]]]:
    """The lines before the first numbered heading, and the lines under each `## <n>. <title>`."""
    preamble: list[str] = []
    sections: dict[int, list[str]] = {}
    current = preamble
    for line in text.splitlines():
        m = re.match(r"^\s{0,3}#{1,6}\s*(?:section\s+)?(\d+)\s*[.):]", line, re.I)
        if m:
            current = sections.setdefault(int(m.group(1)), [])
        elif re.match(r"^\s{0,3}#{1,6}\s", line):
            continue  # an unnumbered heading, such as the form's title
        else:
            current.append(line)
    return preamble, sections


def read_fields(lines: list[str]) -> dict[str, tuple[str, list[str]]]:
    """`Label: value` lines as {key(label): (label as written, [values])}, in the order written."""
    fields: dict[str, tuple[str, list[str]]] = {}
    for line in lines:
        m = re.match(r"^\s*(?:[-*]\s+)?([^:]+?)\s*:(.*)$", line)
        if not m:
            continue
        label = " ".join(m.group(1).replace("*", "").split())
        value = m.group(2).replace("*", "").strip()
        if label:
            fields.setdefault(key(label), (label, []))[1].append(value)
    return fields


def read_documents(lines: list[str]) -> set[str]:
    return {key(m.group(1)) for line in lines if (m := re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.+?)\s*$", line))}


# ------------------------------------------------------------------ reading one value

def money(value: str) -> Decimal | None:
    m = re.fullmatch(r"(-)?\s*(?:USD\s*)?\$?\s*(-)?\s*(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?", value.strip(), re.I)
    if not m:
        return None
    amount = Decimal(m.group(3).replace(",", "") + (m.group(4) or ""))
    return -amount if (m.group(1) or m.group(2)) else amount


def money_not_negative(value: str) -> Decimal | None:
    amount = money(value)
    return None if amount is None or amount < 0 else amount


def money_positive(value: str) -> Decimal | None:
    amount = money(value)
    return None if amount is None or amount <= 0 else amount


def whole_number(value: str) -> int | None:
    m = re.fullmatch(r"(\d+)(?:\s*months?)?", value.strip(), re.I)
    return int(m.group(1)) if m else None


def yes_no(value: str) -> bool | None:
    """Yes or no, alone or followed by a remark after punctuation ("no", "No.", "yes, in 2021")."""
    m = re.fullmatch(r"(yes|no|y|n)\s*(?:[.,;:(\-\u2013\u2014].*)?", value.strip(), re.I | re.S)
    return m.group(1).casefold().startswith("y") if m else None


def a_date(value: str) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        return None


def a_month(value: str) -> tuple[int, int, int | None] | None:
    """(year, month, day or None) from 2016-05, 2016-05-17, 05/2016 or May 2016."""
    v = value.strip()
    if (d := a_date(v)) is not None and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return d.year, d.month, d.day
    if m := re.fullmatch(r"(\d{4})[-/](\d{1,2})", v):
        year, month = int(m.group(1)), int(m.group(2))
    elif m := re.fullmatch(r"(\d{1,2})/(\d{4})", v):
        year, month = int(m.group(2)), int(m.group(1))
    elif (m := re.fullmatch(r"([A-Za-z]+)\.?,?\s+(\d{4})", v)) and m.group(1).casefold() in MONTHS:
        year, month = int(m.group(2)), MONTHS[m.group(1).casefold()]
    else:
        return None
    return (year, month, None) if 1 <= month <= 12 and year >= 1 else None


def text(value: str) -> str:
    return value


# ------------------------------------------------------------------ saying a figure

def dollars(amount: Decimal) -> str:
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    return f"{sign}${amount:,.0f}" if amount == amount.to_integral_value() else f"{sign}${amount:,.2f}"


def plain(number: Decimal) -> str:
    return f"{number:,f}" if number != number.to_integral_value() else f"{number:,.0f}"


def as_json_number(number: Decimal | int | None):
    if number is None or isinstance(number, int):
        return number
    return int(number) if number == number.to_integral_value() else float(number)


def shown(value: Decimal, threshold: Decimal, passes, at_least: int) -> Decimal:
    """`value` rounded for a person to read: to `at_least` decimals (or the threshold's own, if
    it has more), and to more when rounding would put it on the other side of the threshold,
    so a figure that fails by a hair is never shown as one that passes."""
    digits = max(at_least, -threshold.normalize().as_tuple().exponent)
    for more in range(8):
        rounded = value.quantize(Decimal(1).scaleb(-(digits + more)), rounding=ROUND_HALF_UP)
        if passes(rounded) == passes(value):
            return rounded
    return value


# ------------------------------------------------------------------ the check

def check(application: str, policy: str) -> dict:
    rules = policy_text.hard_rules(policy)
    required_documents = policy_text.required_documents(policy)
    years = plain(rules["H5"]["bankruptcy_years"])
    bankruptcy_label = FORM_FIELDS[3][1].format(years=years)

    readers = {
        "Application": text, "Received": a_date,
        "Legal name": text, "Kind of business": text, "Operating since": a_month,
        "Annual revenue, last fiscal year": money_not_negative,
        "Average monthly net income, last 12 months": money,
        "Existing monthly debt payments": money_not_negative,
        "Amount requested": money_not_negative, "Term in months": whole_number,
        "Quoted monthly payment": money_positive,
        "Guarantor credit score": whole_number, bankruptcy_label: yes_no, "Unpaid tax liens": yes_no,
        "Payments 30 or more days late in the last 12 months": text,
    }

    preamble, sections = split_sections(application)
    values: dict[str, object] = {}
    missing: list[dict] = []

    def take(label: str, found: dict[str, tuple[str, list[str]]]) -> None:
        """Read one expected field: note it as missing when it is absent, empty or unreadable."""
        written_label, written = found.get(key(label), (label, []))
        distinct = list(dict.fromkeys(v for v in written if not is_empty(v)))
        if not distinct:
            missing.append({"name": written_label, "kind": "empty field", "written": ""})
        elif len(distinct) > 1:
            missing.append({"name": written_label, "kind": "unreadable field", "written": " / ".join(distinct)})
        elif (value := readers[label](distinct[0])) is None:
            missing.append({"name": written_label, "kind": "unreadable field", "written": distinct[0]})
        else:
            values[label] = value

    # The fields are the `Label: value` lines above section 4: the form's head and sections 1
    # to 3. Sections 5 to 7 are the applicant's own words and are never read for fields.
    found = read_fields(preamble + [line for number in FORM_FIELDS for line in sections.get(number, [])])
    expected = HEADER_FIELDS + [label.format(years=years) for labels in FORM_FIELDS.values() for label in labels]
    for label in expected:
        take(label, found)
    known = {key(label) for label in expected}
    for k, (written_label, written) in found.items():  # a field the form has that the table above does not
        if k not in known and all(is_empty(v) for v in written):
            missing.append({"name": written_label, "kind": "empty field", "written": ""})
    listed = read_documents(sections.get(DOCUMENTS_SECTION, []))
    for document in required_documents:
        if key(document) not in listed:
            missing.append({"name": document, "kind": "absent document", "written": ""})

    out = {
        "application_id": values.get("Application", ""),
        "missing_items": missing,
        "hard_rule_results": [],
        "loan": {"amount_requested": as_json_number(values.get("Amount requested")),
                 "term_months": values.get("Term in months"),
                 "quoted_monthly_payment": as_json_number(values.get("Quoted monthly payment"))},
    }
    if missing:
        return {**out, "form_status": "incomplete"}

    amount: Decimal = values["Amount requested"]
    term: int = values["Term in months"]
    payment: Decimal = values["Quoted monthly payment"]
    revenue: Decimal = values["Annual revenue, last fiscal year"]
    income: Decimal = values["Average monthly net income, last 12 months"]
    debt: Decimal = values["Existing monthly debt payments"]
    score: int = values["Guarantor credit score"]
    bankrupt: bool = values[bankruptcy_label]
    liens: bool = values["Unpaid tax liens"]
    received: datetime.date = values["Received"]
    since_year, since_month, since_day = values["Operating since"]

    results = []

    def rule(name: str, passed: bool, figure: str, threshold: str) -> None:
        results.append({"rule": name, "name": rules[name]["name"], "passed": bool(passed), "figure": figure, "threshold": threshold})

    r = rules["H1"]
    rule("H1", r["min_amount"] <= amount <= r["max_amount"],
         f"amount requested {dollars(amount)}", f"from {dollars(r['min_amount'])} to {dollars(r['max_amount'])}")

    r = rules["H2"]
    rule("H2", r["min_months"] <= term <= r["max_months"],
         f"term {term} months", f"from {plain(r['min_months'])} to {plain(r['max_months'])} months")

    # Whole months in business on the day the application was received. The form gives the
    # start as a month, so a business that started in the month 24 months back has 24.
    months = (received.year - since_year) * 12 + (received.month - since_month)
    if since_day is not None and received.day < since_day:
        months -= 1
    r = rules["H3"]
    since = f"{since_year:04d}-{since_month:02d}" + (f"-{since_day:02d}" if since_day else "")
    rule("H3", months >= r["min_months"],
         f"{months} months in business (operating since {since}, received {received.isoformat()})",
         f"{plain(r['min_months'])} months or more")

    r = rules["H4"]
    rule("H4", score >= r["min_score"], f"guarantor credit score {score}", f"{plain(r['min_score'])} or higher")

    rule("H5", not bankrupt and not liens,
         f"bankruptcy in the last {years} years: {'yes' if bankrupt else 'no'}; unpaid tax liens: {'yes' if liens else 'no'}",
         f"no bankruptcy in the last {years} years and no unpaid tax liens")

    # Coverage: income / (debt + payment) >= ratio, tested without dividing so that a figure
    # exactly on the threshold passes.
    r = rules["H6"]
    payments = debt + payment
    ratio = shown(income / payments, r["min_ratio"], lambda x: x >= r["min_ratio"], 2)
    rule("H6", income >= r["min_ratio"] * payments,
         f"coverage {ratio}: average monthly net income {dollars(income)} divided by {dollars(payments)} "
         f"(existing monthly debt payments {dollars(debt)} plus quoted monthly payment {dollars(payment)})",
         f"{plain(r['min_ratio'])} or higher")

    # Size: amount <= percent of revenue, tested the same way.
    r = rules["H7"]
    most = r["max_percent"] * revenue / 100
    if revenue > 0:
        share = f"{shown(amount * 100 / revenue, r['max_percent'], lambda x: x <= r['max_percent'], 1)}%"
    else:
        share = "more than any share"
    rule("H7", amount * 100 <= r["max_percent"] * revenue,
         f"amount requested {dollars(amount)} is {share} of annual revenue {dollars(revenue)}",
         f"{plain(r['max_percent'])}% or less of annual revenue ({dollars(most)} or less)")

    failed = [x for x in results if not x["passed"]]
    return {**out, "hard_rule_results": results, "form_status": "failed" if failed else "passed"}


def main() -> None:
    payload = json.load(sys.stdin)
    # The application arrives as a file, not as text someone typed into the run, so the form is
    # read exactly as it was written. A relative path is the run's working directory's.
    name = payload["state"]["application_file"]
    if not isinstance(name, str) or not name.strip():
        sys.exit("check_form: application_file is not a file name")
    try:
        with open(name.strip(), encoding="utf-8") as f:
            application = f.read()
    except OSError as err:
        sys.exit(f"check_form: cannot read the application file {name!r}: {err.strerror}")
    try:
        result = check(application, payload["assets"]["policy"])
    except policy_text.PolicyError as err:
        sys.exit(f"check_form: assets/policy.md: {err}")
    json.dump({"application": application, **result}, sys.stdout)


if __name__ == "__main__":
    main()
