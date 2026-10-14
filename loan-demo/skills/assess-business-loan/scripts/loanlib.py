"""Shared helpers for the assess-business-loan scripts: call `loan`, scrub the state, log judgments.

Every script runs with cwd = this folder, one JSON object on stdin
({"currentState": ..., "assets": ..., "expects": ...}) and one JSON object on stdout.
Standard library only: `loan` is reached with subprocess, never imported.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

JSON = dict[str, Any]


def read_state() -> JSON:
    return json.load(sys.stdin)["currentState"]


def write(result: JSON) -> None:
    json.dump(result, sys.stdout)


def loan(*args: str) -> Any:
    """Run `loan <args>` and parse its JSON. A non-zero exit fails the step with loan's message."""
    proc = subprocess.run(["loan", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr.strip() or proc.stdout.strip())[:2000]
        raise SystemExit(f"loan {' '.join(args[:2])} failed (exit {proc.returncode}): {detail}")
    out = proc.stdout.strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        raise SystemExit(f"loan {' '.join(args[:2])} returned non-JSON output: {out[:500]}")


def decide(question: str, options: list[str], answer: str, why: str) -> None:
    """SOP "Judgment calls": log every judgment with `loan decide`. Options are comma-separated, so strip commas."""
    opts = ",".join(o.replace(",", ";") for o in options)
    loan("decide", "--question", question, "--options", opts, "--answer", answer, "--why", why)


# ------------------------------------------------------------------ protected characteristics
# The same word list `loan check` uses. A CRM note that matches is dropped before the judgment step
# ever sees the state; a rationale that repeats one of these words fails the check.
PROTECTED_WORDS = re.compile(
    r"\b(dob|date of birth|born|years old|aged|age|sex|gender|ethnicit\w*|ethnic|race|racial|religio\w*|"
    r"national origin|nationality|marital|married|divorced|disabilit\w*|disabled|pregnan\w*)\b", re.I)

# Keys that never enter the state: dates of birth (the tools do not return them; strip anyway) and the
# name of whoever submitted the application (a person).
DROP_KEYS = {"dob", "date_of_birth", "birth_date", "birthdate", "requested_by"}


def person_labels(application: JSON, ownership: JSON) -> dict[str, str]:
    """Map every person's name the tools returned to a role label: owners by position, the RM by role.

    The labels are what the state carries instead of names: "owner 1" is the first owner in
    `ownership_summary.owners`, so a redacted note still ties back to a share.
    """
    labels: dict[str, str] = {}
    for i, o in enumerate(ownership.get("owners", []), start=1):
        name = (o.get("person") or {}).get("name") or o.get("name")
        if name:
            labels[name] = f"owner {i}"
    for o in application.get("owners", []):
        if o.get("name") and o["name"] not in labels:
            labels[o["name"]] = f"owner {len(labels) + 1}"
    rm = (application.get("relationship_manager") or {}).get("name")
    if rm:
        labels[rm] = "the relationship manager"
    if application.get("application", {}).get("requested_by"):
        labels.setdefault(application["application"]["requested_by"], "a person")
    return labels


def _name_patterns(labels: dict[str, str]) -> list[tuple[re.Pattern[str], str]]:
    """Full names first, then first names on their own. Surnames alone are left: they can be part of a
    business name (an owner's surname in the name of the business they hold)."""
    pats: list[tuple[re.Pattern[str], str]] = []
    for name, label in sorted(labels.items(), key=lambda kv: -len(kv[0])):
        pats.append((re.compile(r"\b" + re.escape(name) + r"\b"), label))
    for name, label in labels.items():
        first = name.split()[0]
        if len(first) >= 3:
            pats.append((re.compile(r"\b" + re.escape(first) + r"\b"), label))
    return pats


def redact(text: str, labels: dict[str, str]) -> str:
    for pat, label in _name_patterns(labels):
        text = pat.sub(label, text)
    return text


def mentions_personal_characteristic(text: str, labels: dict[str, str]) -> bool:
    """The check's word list, plus the way an annual-review note records an age: a person's name followed
    by a bracketed number ("Priya (58) is thinking about succession")."""
    if PROTECTED_WORDS.search(text):
        return True
    for name in labels:
        for tok in {name, name.split()[0]}:
            if len(tok) >= 3 and re.search(r"\b" + re.escape(tok) + r"\b\s*\(\s*\d{1,3}\s*\)", text):
                return True
    return False


def scrub(obj: Any, labels: dict[str, str]) -> Any:
    """Remove dates of birth and people's names from any tool output, recursively.

    - keys in DROP_KEYS are removed
    - `name` is removed from a person record (one whose `key` starts with PER- or RM-)
    - `owner` holding a person's name (policy's `connected[].owner`) is replaced by the role label
    - every remaining string has names replaced by role labels
    """
    if isinstance(obj, dict):
        out: JSON = {}
        is_person = str(obj.get("key", "")).startswith(("PER-", "RM-"))
        for k, v in obj.items():
            if k in DROP_KEYS or (is_person and k == "name"):
                continue
            if k == "owner" and isinstance(v, str) and v in labels:
                out[k] = labels[v]
                continue
            out[k] = scrub(v, labels)
        return out
    if isinstance(obj, list):
        return [scrub(v, labels) for v in obj]
    if isinstance(obj, str):
        return redact(obj, labels)
    return obj


def filter_notes(notes: list[JSON], labels: dict[str, str]) -> tuple[list[JSON], int]:
    """CRM notes the judgment step may see: drop any that mention a personal characteristic, redact names
    in the rest. Returns (kept, dropped_count)."""
    kept: list[JSON] = []
    dropped = 0
    for n in notes:
        text = str(n.get("text", ""))
        if mentions_personal_characteristic(text, labels):
            dropped += 1
            continue
        kept.append({"key": n.get("key"), "date": n.get("date"), "text": redact(text, labels)})
    return kept, dropped


# ------------------------------------------------------------------ the skill's own revision
def skill_version() -> str:
    """`metadata.version` from this skill's SKILL.md frontmatter (../SKILL.md relative to this script)."""
    path = Path(__file__).resolve().parent.parent / "SKILL.md"
    try:
        text = path.read_text()
    except OSError:
        return "unknown"
    fm = text.split("---", 2)
    head = fm[1] if len(fm) >= 3 else text
    in_meta = False
    for line in head.splitlines():
        if re.match(r"^metadata:\s*$", line):
            in_meta = True
            continue
        if in_meta and not line.startswith((" ", "\t")):
            in_meta = False
        m = re.match(r"^\s+version:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", line)
        if in_meta and m:
            return m.group(1).strip()
    return "unknown"


def skill_revision() -> str:
    """The version, plus the published revision hash when the server runs this skill from its cache
    (`<cache>/<name>@<hash>/<name>/scripts/`): "1 (a1b2c3...)". Locally it is just the version."""
    version = skill_version()
    parents = Path(__file__).resolve().parents
    if len(parents) > 2 and "@" in parents[2].name:
        return f"{version} ({parents[2].name.split('@', 1)[1]})"
    return version


# ------------------------------------------------------------------ cite keys
def collect_cites(*sources: Any) -> list[str]:
    """Every node key under a `cites` field in the given objects, plus bare keys, de-duplicated and sorted."""
    keys: set[str] = set()

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "cites":
                    if isinstance(v, list):
                        keys.update(str(c) for c in v)
                    elif isinstance(v, dict):
                        for vv in v.values():
                            keys.update(str(c) for c in (vv or []))
                elif k == "key" and isinstance(v, str):
                    keys.add(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    for s in sources:
        walk(s)
    return sorted(keys)
