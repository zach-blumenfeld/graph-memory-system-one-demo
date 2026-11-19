"""Ending: escalate. The application is placed in the credit officer queue with the judgment
rules that did not hold and the answer given for each. Appends one line to
credit_officer_queue.jsonl in the run's working directory; the credit officer decides later,
outside this procedure, and nothing here waits for them."""

from ending import bar_mismatch, finish, judgments, read_payload

state, assets = read_payload()
judged, bar = judgments("escalate", state["judgment_rules"], state["verdicts"], assets["policy"])
did_not_hold = [j for j in judged if not j["cleared"]]
if not did_not_hold:
    bar_mismatch("escalate", bar, "every judgment rule cleared it")
finish("credit_officer_queue.jsonl", "escalate", state["application_id"],
       failed_rules=[j["rule"] for j in did_not_hold], missing=[],
       reasons={"loan": state["loan"], "judgment_rules_did_not_hold": did_not_hold,
                "judgment_rules_held": [j for j in judged if j["cleared"]], "probability_bar": bar},
       application=state["application"])
