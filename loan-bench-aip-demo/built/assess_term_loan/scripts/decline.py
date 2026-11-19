"""Ending: decline. The decision is filed with every failed hard rule, its figure and its
threshold. Appends one line to decisions.jsonl in the run's working directory."""

from ending import finish, read_payload

state, _ = read_payload()
failed = [r for r in state["hard_rule_results"] if not r["passed"]]
finish("decisions.jsonl", "decline", state["application_id"],
       failed_rules=[r["rule"] for r in failed], missing=[],
       reasons={"failed_hard_rules": failed})
