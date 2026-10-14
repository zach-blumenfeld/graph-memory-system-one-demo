# Fix the rationale {rationale_id} for {application_id}: one pass only

The check failed. This is the only fix pass; if the recheck fails again the run ends unfiled and a human
takes over. Outcome stays **{outcome}**.

Failures to fix, exactly as the check named them:
{failures_md}

What each check wants:
- `has_cites` / `cite_exists`: every figure and fact carries `[cite: KEY]` in square brackets, and KEY is one of
  the keys in the evidence. Allowed keys: {cite_keys}
- `figure_in_evidence`: the number named is not in the evidence. Remove it or replace it with the figure the
  evidence holds (the interest rate as a percentage and any derived number are the usual culprits).
- `outcome_stated`: the first paragraph (no heading before it) must say the outcome word: "Outcome: {outcome}."
  No line labelled outcome, decision or recommendation may name a different outcome.
- `no_protected_characteristics`: remove the word the check named and anything about a person rather than the business.

Current rationale:

{rationale}

The evidence, for reference:

{evidence_md}

Fix only what the failures name and anything the same check would catch elsewhere. Keep the structure, the
outcome, the cites that were accepted, and the precedent reasoning.

Return JSON with `rationale` (the full revised markdown string). Carry `precedents_note` forward unchanged unless a
fix changed the precedent reasoning.
