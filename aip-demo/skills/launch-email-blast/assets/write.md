# Write the email: three subject lines and a markdown body

Brief **{brief[title]}** ({brief_id}, campaign {campaign_id}), classified as a **{email_kind}** email.

- Goal: {brief[goal]}
- Key messages: {brief[key_messages]}
- Call to action: {brief[cta]}
- Notes from the brief: {brief[notes]}
- Send window: {brief[send_window]}

## Audience

Segment **{segment[name]}** ({segment[segment_id]}, {segment[size]} recipients): {segment[description]}
Persona **{persona[name]}**. Preferred tone: {persona[preferred_tone]}. Turn-offs: {persona[turn_offs]}.
Write in the tone the persona wants; the turn-offs are the words and moves to avoid.

## Product {product[name]} {product[version]}: {product[tagline]}

Approved claims (the only things the email may claim about the product):
{product[approved_claims]}

Docs: {product[docs_url]}  Repo: {product[repo_url]}

## Brand guide

Voice rules: {brand[voice_rules]}
Banned words and claims: {brand[banned_claims]}
Subject line rules: {brand[subject_line_rules]}
Required disclaimer, to appear in the body word for word:
{brand[required_disclaimer]}

## Rules

1. Only say what is on the approved claims list. Check each key message against it. A number, a comparison, or a
   promise about product behaviour ("no data loss", "no changes to existing pipelines", "nothing else to run") that is
   not on the list is left out, or replaced by the closest approved claim quoted word for word. A factual instruction
   (an install or attach command that is the call to action) and a plain feature fact from the brief (a new CLI command
   exists) are not claims; keep them, but do not invent syntax, names or numbers the brief does not give.
2. The body covers the key messages that survived rule 1, says it is a Tessera Labs project where relevant, and ends
   with exactly one call to action, the brief's. If the brief gives no channel or link for the CTA, use reply-to or the
   product docs URL; never invent a URL. Where the brief asks for a link it does not give, put a marked placeholder
   such as QUICKSTART_URL and record it in claims_notes.
3. Lead with what the reader can do now. One idea per sentence. No exclamation marks, no emoji, no superlatives.
   Prefer code blocks and concrete nouns. Keep it short.
4. The disclaimer appears verbatim, usually as the last paragraph.
5. Three subject lines, each under 60 characters, no all-caps words, none of the banned or spam words ("free",
   "act now", "last chance"). Make them different: one that names the release and what the reader can now do, one
   that leads with a specific feature, one more curious. None may read as a teaser or as urgency pressure.

For worked examples of claims rulings and a body that passed, load `references/examples.md`.

Return JSON with:

- `subjects`: a list of exactly three subject line strings, in order (the next step chooses first, second or third).
- `body`: the full email body in markdown, as one string.
- `claims_notes`: one short paragraph, for the campaign log, saying for each key message whether it was included as
  written, rephrased to an approved claim, or left out, and why; plus any placeholders or open items a human must
  resolve before the send.
