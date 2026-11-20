"""Ending: approve. The decision is filed with the amount, the term and the quoted payment.
Appends one line to decisions.jsonl in the run's working directory."""

from ending import bar_mismatch, finish, judgments, read_payload

state, assets = read_payload()
judged, bar = judgments("approve", state["judgment_rules"], state["verdicts"], assets["policy"])
short = [j["rule"] for j in judged if not j["cleared"]]
if short:
    bar_mismatch("approve", bar, f"{', '.join(short)} did not clear it")
finish("decisions.jsonl", "approve", state["application_id"],
       failed_rules=[], missing=[],
       reasons={"loan": state["loan"], "hard_rules_passed": state["hard_rule_results"],
                "judgment_rules_held": judged, "probability_bar": bar})
