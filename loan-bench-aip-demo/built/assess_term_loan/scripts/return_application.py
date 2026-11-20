"""Ending: return. The application goes back to the applicant with what is missing.
Appends one line to returns.jsonl in the run's working directory."""

from ending import finish, read_payload

state, _ = read_payload()
items = state["missing_items"]
finish("returns.jsonl", "return", state["application_id"],
       failed_rules=[], missing=[item["name"] for item in items],
       reasons={"missing_items": items})
