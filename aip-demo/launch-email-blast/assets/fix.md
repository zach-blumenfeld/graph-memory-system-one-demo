# Fix the draft: one pass only

Draft {draft_id} for **{brief[title]}** ({brief_id}) failed the compliance check. This is the only fix-up pass;
if the recheck fails again the run ends without scheduling and a human takes over.

Failures to fix, exactly as the checker named them:
{failures}

Current subject lines:
{subjects}

Current body:

{body}

Required disclaimer, word for word:
{required_disclaimer}

Brand guide, for reference. Voice rules: {brand[voice_rules]}. Banned words and claims: {brand[banned_claims]}.
Subject line rules: {brand[subject_line_rules]}. Approved claims for {product[name]}: {product[approved_claims]}.

Fix only what the failures name and anything the same rule would catch elsewhere in the draft. Keep the structure,
the single call to action ({brief[cta]}), the claims decisions already made, and the persona's tone
({persona[preferred_tone]}; avoid {persona[turn_offs]}).

Return JSON with `subjects` (a list of exactly three subject line strings) and `body` (the full revised markdown body).
Carry `claims_notes` forward unchanged unless a fix changed a claim; then say so in it.
