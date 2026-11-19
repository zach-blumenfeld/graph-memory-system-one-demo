"""Read Lantern Mutual's term-loan policy (assets/policy.md) into data.

Every number the procedure's scripts use comes out of the policy text through this module: the
required documents, the threshold of each hard rule, the judgment rules and the probability bar.
Nothing here has a default. When the policy no longer says a thing where this module looks for
it, the script stops with a message naming what it could not find, instead of assessing an
application against a number the policy does not contain.
"""

from __future__ import annotations

import re
from decimal import Decimal

NUMBER = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"


class PolicyError(Exception):
    """The policy text does not say something a script needs, where it is expected."""


def _number(text: str) -> Decimal:
    return Decimal(text.replace(",", ""))


def section(policy: str, title: str) -> str:
    """The body under the `## <title>` heading, up to the next heading of that level or higher."""
    lines = policy.splitlines()
    wanted = title.casefold()
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m and m.group(2).casefold() == wanted:
            level = len(m.group(1))
            body = []
            for later in lines[i + 1:]:
                n = re.match(r"^(#{1,6})\s", later)
                if n and len(n.group(1)) <= level:
                    break
                body.append(later)
            return "\n".join(body)
    raise PolicyError(f'the policy has no "{title}" section')


def required_documents(policy: str) -> list[str]:
    """The documents the Completeness section lists, as the policy writes them."""
    documents = [m.group(1).strip() for m in re.finditer(r"^\s*[-*]\s+(.+?)\s*$", section(policy, "Completeness"), re.M)]
    if not documents:
        raise PolicyError('the "Completeness" section lists no required documents')
    return documents


# What each hard rule's "Passes when" cell must say for its numbers to be read. The script that
# applies the rules knows what each number is compared with; the numbers themselves are here.
_HARD_RULE_NUMBERS = {
    "H1": (rf"from \$?({NUMBER}) to \$?({NUMBER})", ("min_amount", "max_amount")),
    "H2": (rf"from ({NUMBER}) to ({NUMBER}) months", ("min_months", "max_months")),
    "H3": (rf"for ({NUMBER}) months or more", ("min_months",)),
    "H4": (rf"is ({NUMBER}) or higher", ("min_score",)),
    "H5": (rf"bankruptcy in the last ({NUMBER}) years and no unpaid tax liens", ("bankruptcy_years",)),
    "H6": (rf"is ({NUMBER}) or higher", ("min_ratio",)),
    "H7": (rf"is ({NUMBER})\s*% or less", ("max_percent",)),
}


def hard_rules(policy: str) -> dict[str, dict]:
    """`{"H1": {"name", "passes_when", <its numbers as Decimal>}, ...}` from the hard-rule table."""
    rules: dict[str, dict] = {}
    for line in section(policy, "Hard rules").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not re.fullmatch(r"H\d+", cells[0]):
            continue
        rule, name, passes_when = cells[0], cells[1], cells[2]
        if rule in rules:
            raise PolicyError(f"the hard-rule table has two rows for {rule}")
        rules[rule] = {"name": name, "passes_when": passes_when}
    known, found = set(_HARD_RULE_NUMBERS), set(rules)
    if found - known:
        raise PolicyError(f"the policy has hard rules the form check does not know how to apply: {sorted(found - known)}")
    if known - found:
        raise PolicyError(f"the hard-rule table is missing {sorted(known - found)}")
    for rule, (pattern, names) in _HARD_RULE_NUMBERS.items():
        m = re.search(pattern, rules[rule]["passes_when"], re.I)
        if not m:
            raise PolicyError(f'cannot read the threshold of {rule} from "{rules[rule]["passes_when"]}"')
        for name, text in zip(names, m.groups()):
            rules[rule][name] = _number(text)
    return rules


def judgment_rules(policy: str) -> list[dict]:
    """`[{"id": "J1", "name": ..., "statement": ...}, ...]`: one per `### J<n> <name>` heading
    of the Judgment rules section, in the policy's order, the statement being the text under it."""
    rules: list[dict] = []
    current: dict | None = None
    for line in section(policy, "Judgment rules").splitlines():
        m = re.match(r"^###\s+(J\d+)\s+(.+?)\s*$", line)
        if m:
            current = {"id": m.group(1), "name": m.group(2), "lines": []}
            rules.append(current)
        elif current is not None:
            current["lines"].append(line.strip())
    out = []
    for rule in rules:
        paragraphs = [" ".join(p.split()) for p in "\n".join(rule["lines"]).split("\n\n")]
        statement = "\n\n".join(p for p in paragraphs if p)
        if not statement:
            raise PolicyError(f"judgment rule {rule['id']} has no statement")
        out.append({"id": rule["id"], "name": rule["name"], "statement": statement})
    if not out:
        raise PolicyError('the "Judgment rules" section has no "### J<n> <name>" rule')
    ids = [r["id"] for r in out]
    if len(set(ids)) != len(ids):
        raise PolicyError(f"the policy has two judgment rules with one id: {ids}")
    return out


def probability_bar(policy: str) -> float:
    """The probability every judgment rule must be above for an approval."""
    found = {m.group(1) for m in re.finditer(r"probability above (\d*\.?\d+)", section(policy, "How the outcome is formed"), re.I)}
    if len(found) != 1:
        raise PolicyError(f'expected one "probability above <number>" in "How the outcome is formed", found {sorted(found)}')
    return float(found.pop())
