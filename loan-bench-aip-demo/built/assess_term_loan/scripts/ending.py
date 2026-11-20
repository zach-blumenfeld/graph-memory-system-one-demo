"""What the four endings share: filing one line of JSON under the run's working directory,
printing the step's result, and reading the judgment verdicts against the policy's bar."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import policy_text


def read_payload() -> tuple[dict, dict]:
    payload = json.load(sys.stdin)
    return payload["state"], payload.get("assets", {})


def finish(file: str, outcome: str, application_id: str, failed_rules: list, missing: list, reasons: dict, **also_filed) -> None:
    """Append the ending's line to `file` in the run's working directory, then print the step's
    Produce keys. The line holds the outcome and its reasons; `also_filed` goes on the line only."""
    line = {"application_id": application_id, "outcome": outcome, "failed_rules": failed_rules, "missing": missing,
            **reasons, **also_filed}
    if os.environ.get("AIP_RUN_ID"):
        line["run_id"] = os.environ["AIP_RUN_ID"]
    path = Path(os.environ.get("AIP_WORKDIR") or ".") / file
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    json.dump({"outcome": outcome, "failed_rules": failed_rules, "missing": missing, "reasons": reasons}, sys.stdout)


def judgments(step: str, rules: list, verdicts: list, policy: str) -> tuple[list[dict], float]:
    """One entry per judgment rule, in the policy's order, from the list of rules and the
    verdicts the loop collected for them, and the policy's probability bar.

    `answer` is the decision model's yes or no to "does this rule hold?", `probability_rule_holds`
    the probability it gave to yes, and `cleared` whether that is a yes with a probability above
    the bar, which is what an approval needs of every rule."""
    try:
        bar = policy_text.probability_bar(policy)
    except policy_text.PolicyError as err:
        sys.exit(f"{step}: assets/policy.md: {err}")
    if len(rules) != len(verdicts):
        sys.exit(f"{step}: {len(rules)} judgment rules but {len(verdicts)} verdicts")
    out = []
    for rule, verdict in zip(rules, verdicts):
        answer = (verdict or {}).get("holds")
        if not isinstance(answer, dict) or not isinstance(answer.get("value"), bool):
            sys.exit(f"{step}: no yes-or-no verdict for {rule['id']}")
        holds, p = answer["value"], answer.get("noul")
        cleared = holds and p is not None and p > bar
        if cleared:
            why = f"holds, with a probability of {p:.2f}, above the bar of {bar:g}"
        elif holds:
            why = (f"answered as holding, but with a probability of {p:.2f}, not above the bar of {bar:g}"
                   if p is not None else "answered as holding, but with no probability given")
        else:
            why = "does not hold" + (f": the probability that it holds is {p:.2f}" if p is not None else "")
        out.append({"rule": rule["id"], "name": rule["name"], "statement": rule["statement"],
                    "answer": "yes" if holds else "no", "probability_rule_holds": None if p is None else round(p, 4),
                    "cleared": cleared, "reading": why})
    return out, bar


def bar_mismatch(step: str, bar: float, saw: str) -> None:
    sys.exit(f"{step}: the Aggregate step sent this application here, but against the policy's probability bar "
             f"of {bar:g} {saw}. The bar written in procedure.aip (combine_verdicts) and the one in "
             f"assets/policy.md have come apart; make them the same and resume.")
