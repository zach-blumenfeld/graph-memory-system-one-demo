# Fix the draft: one pass only

Draft {draft_id} for **{brief[title]}** ({brief_id}) failed the compliance check. This is the only fix-up pass:
the fixed draft is stored and checked once more, and the run ends either way with a note in the campaign log.

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
the single call to action ({brief[cta]}), the claims decisions already made ({claims_notes}), and the persona's tone
({persona[preferred_tone]}; avoid {persona[turn_offs]}). Subject lines: under 60 characters, no all-caps words, no
spam words. Body: the disclaimer verbatim, no exclamation marks, none of the banned phrases, a link or the brief's
call to action present.

Return JSON with:

- `fixed_subjects`: a list of exactly three subject line strings (unchanged ones repeated as they were).
- `fixed_body`: the full revised markdown body.
- `fix_notes`: one or two sentences saying what was changed and why.
