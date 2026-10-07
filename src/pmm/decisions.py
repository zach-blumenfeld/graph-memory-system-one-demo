"""System One decisions: TypeSafe Jev behind three typed questions sets.

No heuristic fallback exists. If TYPESAFE_API_KEY is missing or Jev is unreachable the caller
gets an exception; the MCP server surfaces it as a tool error. Tests inject a `FakeSystemOne`.

Thresholds follow AIP's defaults: a noul is flagged for review when |p - 0.5| < 0.15; a choice or
score is flagged when the model's confidence < 0.6.
"""

from __future__ import annotations

import os
from typing import Any, Protocol

from pydantic import BaseModel, Field

NOUL_MARGIN = 0.15
MIN_CONFIDENCE = 0.6


class SystemOne(Protocol):
    def system_one(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]: ...


class JevUnavailable(RuntimeError):
    pass


class TypeSafeSystemOne:
    """Thin adapter over typesafe_sdk.TypeSafeClient that returns plain JSON."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key or os.environ.get("TYPESAFE_API_KEY")
        if not key:
            raise JevUnavailable("TYPESAFE_API_KEY is not set; the PMM tools require TypeSafe Jev (no fallback)")
        from typesafe_sdk import TypeSafeClient  # imported lazily so tests never need the SDK online

        self._client = TypeSafeClient(api_key=key, model=model)

    def system_one(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        from typesafe_sdk import TypeSafeError

        try:
            result = self._client.system_one(state=state, questions=questions)
        except TypeSafeError as exc:  # pragma: no cover - network
            raise JevUnavailable(f"TypeSafe Jev call failed: {exc}") from exc
        return result.model_dump(mode="json")


# --------------------------------------------------------------------------- typed answers
class NoulAnswer(BaseModel):
    type: str = "noul"
    noul: float = Field(description="Probability that the statement holds, 0..1")
    verdict: bool = Field(description="noul >= 0.5")
    review: bool = Field(description="True when |noul - 0.5| < NOUL_MARGIN")


class ChoiceAnswer(BaseModel):
    type: str = "choice"
    choice: str
    confidence: float
    probabilities: dict[str, float]
    review: bool = Field(description="True when confidence < MIN_CONFIDENCE")


class ScoreAnswer(BaseModel):
    type: str = "score"
    score: float = Field(description="Expected level on a 1..5 scale")
    level: int = Field(description="Most likely level, 1..5")
    confidence: float
    probabilities: dict[str, float] = Field(description="Probability per level label (1..5)")
    review: bool = Field(description="True when confidence < MIN_CONFIDENCE")


class ReviewItem(BaseModel):
    question: str
    type: str
    reason: str
    value: float


def _noul(raw: dict[str, Any]) -> NoulAnswer:
    p = float(raw["noul"])
    return NoulAnswer(noul=p, verdict=p >= 0.5, review=abs(p - 0.5) < NOUL_MARGIN)


def _choice(raw: dict[str, Any]) -> ChoiceAnswer:
    conf = float(raw["confidence"])
    return ChoiceAnswer(choice=raw["choice"], confidence=conf, probabilities={k: float(v) for k, v in raw["probabilities"].items()}, review=conf < MIN_CONFIDENCE)


def _score(raw: dict[str, Any]) -> ScoreAnswer:
    # Jev returns a 0-indexed legend; the demo talks in 1..5 levels.
    conf = float(raw["confidence"])
    probs = {str(int(k) + 1): float(v) for k, v in raw["probabilities"].items()}
    best = max(probs, key=probs.get)
    return ScoreAnswer(score=float(raw["score"]) + 1.0, level=int(best), confidence=conf, probabilities=probs, review=conf < MIN_CONFIDENCE)


def review_items(answers: dict[str, NoulAnswer | ChoiceAnswer | ScoreAnswer]) -> list[ReviewItem]:
    items: list[ReviewItem] = []
    for name, a in answers.items():
        if not a.review:
            continue
        if isinstance(a, NoulAnswer):
            items.append(ReviewItem(question=name, type="noul", reason=f"within {NOUL_MARGIN} of 0.5", value=a.noul))
        else:
            items.append(ReviewItem(question=name, type=a.type, reason=f"confidence below {MIN_CONFIDENCE}", value=a.confidence))
    return items


# --------------------------------------------------------------------------- question sets
def _q(kind: str, instructions: str, criteria: Any = None) -> dict[str, Any]:
    q: dict[str, Any] = {"type": kind, "instructions": instructions}
    if criteria is not None:
        q["criteria"] = criteria
    return q


CAMPAIGN_TYPES = {
    "launch": "announces a new release, version, feature or product that people can use now",
    "update": "informs existing users about a change to something they already use (hotfix, deprecation, migration)",
    "nurture": "educational or editorial content with no release to act on (digest, tutorial roundup, essay)",
    "event": "promotes a webinar, meetup, conference talk or office hours",
}

URGENCY_LEVELS = [
    "1: no deadline, can go out whenever the calendar has room",
    "2: should go out this month",
    "3: should go out this week",
    "4: should go out within two days",
    "5: must go out today",
]

SCORE_LEVELS = {
    "clarity": [
        "1: the reader cannot tell what the email is about",
        "2: vague, needs the body to make sense",
        "3: understandable but generic",
        "4: clear subject, specific product or action",
        "5: instantly clear what it is and why it matters",
    ],
    "curiosity": [
        "1: no reason to open",
        "2: mildly interesting",
        "3: some pull for the target persona",
        "4: a specific hook the persona cares about",
        "5: compelling, the persona would open it first",
    ],
    "spam_risk": [
        "1: reads like a note from a colleague",
        "2: slightly promotional wording",
        "3: marketing-ish, some trigger words",
        "4: salesy, caps or urgency words, likely filtered",
        "5: obvious spam pattern",
    ],
}


class Decisions:
    """The three Jev-backed decision sets used by the PMM tools."""

    def __init__(self, system_one: SystemOne) -> None:
        self.system_one = system_one

    # 3. classify_brief
    def classify(self, brief: dict[str, Any]) -> dict[str, Any]:
        state = {
            "brief_title": brief["Name"],
            "goal": brief["Goal"],
            "product": brief["Product"],
            "key_messages": brief["Key messages"],
            "call_to_action": brief["CTA"],
            "send_window": brief["Send window"],
            "notes": brief["Notes"],
            "today": "2026-10-06",
        }
        questions = {
            "campaign_type": _q("choice", "Which kind of email campaign does this brief describe?", CAMPAIGN_TYPES),
            "urgency": _q("score", "How urgent is this campaign, given the send window, the notes and today's date?", URGENCY_LEVELS),
            "needs_legal_review": _q(
                "noul",
                "Does this brief need legal review before anything is sent? Say yes if it contains unpublished "
                "numbers, comparisons that name other products, claims about support or guarantees, or anything "
                "legal has not seen.",
            ),
        }
        result = self.system_one.system_one(state, questions)
        raw = result["answers"]
        answers = {"campaign_type": _choice(raw["campaign_type"]), "urgency": _score(raw["urgency"]), "needs_legal_review": _noul(raw["needs_legal_review"])}
        return {"answers": answers, "review_required": review_items(answers), "model": self._model(result)}

    # 5. check_brand_compliance
    def compliance(self, draft: dict[str, Any], brand: dict[str, Any], product: dict[str, Any]) -> dict[str, Any]:
        body = draft["body_md"]
        disclaimer_present = brand["Required disclaimer"].split(".")[0].lower() in body.lower()
        state = {
            "subject_lines": draft["subject_lines"],
            "body_markdown": body,
            "brand_voice_rules": brand["Voice rules"],
            "banned_claims": brand["Banned claims"],
            "approved_claims_for_product": product["Approved claims"],
            "approved_claims_note": "Approved claims are published and vetted; quoting them (with their numbers) is allowed.",
            "required_disclaimer": brand["Required disclaimer"],
            "disclaimer_text_found_verbatim": disclaimer_present,
        }
        questions = {
            "on_brand_voice": _q("noul", "Does the draft follow the brand voice rules (direct, concrete, no superlatives, no exclamation marks, Labs framing)?"),
            "no_unapproved_claims": _q(
                "noul",
                "Is the draft free of unapproved claims? Every statement in approved_claims_for_product is approved and may "
                "be quoted or paraphrased, including its numbers and citations. Flag only: a banned claim from banned_claims, "
                "a number or comparison that is NOT in the approved list, a claim naming a competitor, or a support/SLA/guarantee claim.",
            ),
            "has_clear_cta": _q("noul", "Does the draft contain exactly one clear call to action telling the reader what to do next?"),
            "has_labs_disclaimer": _q("noul", "Does the draft include the required Tessera Labs disclaimer (experimental, community-supported, not covered by support contracts)?"),
        }
        result = self.system_one.system_one(state, questions)
        raw = result["answers"]
        answers = {k: _noul(raw[k]) for k in questions}
        return {"answers": answers, "review_required": review_items(answers), "model": self._model(result), "disclaimer_text_found_verbatim": disclaimer_present}

    # 6. score_subject_lines
    def score_lines(self, lines: list[str], persona: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
        state = {
            "subject_lines": {f"line_{i + 1}": s for i, s in enumerate(lines)},
            "persona": {"name": persona["Name"], "role": persona["Role"], "cares_about": persona["Cares about"], "turn_offs": persona["Turn-offs"], "preferred_tone": persona["Preferred tone"]},
            "campaign": {"title": brief["Name"], "goal": brief["Goal"]},
        }
        questions: dict[str, Any] = {}
        for i in range(len(lines)):
            for dim, levels in SCORE_LEVELS.items():
                questions[f"line_{i + 1}_{dim}"] = _q("score", f"Rate subject line line_{i + 1} on {dim.replace('_', ' ')} for this persona.", levels)
        result = self.system_one.system_one(state, questions)
        raw = result["answers"]
        answers = {k: _score(raw[k]) for k in questions}
        return {"answers": answers, "review_required": review_items(answers), "model": self._model(result)}

    @staticmethod
    def _model(result: dict[str, Any]) -> str:
        return str(result.get("model") or "unknown")


class FakeSystemOne:
    """Deterministic test double. Noul probability and confidence can be steered per question name."""

    def __init__(self, nouls: dict[str, float] | None = None, confidence: float = 0.9, choice: str = "launch", level: int = 3) -> None:
        self.nouls = nouls or {}
        self.confidence = confidence
        self.choice = choice
        self.level = level
        self.calls: list[dict[str, Any]] = []

    def system_one(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        self.calls.append({"state": state, "questions": questions})
        answers: dict[str, Any] = {}
        for name, q in questions.items():
            if q["type"] == "noul":
                answers[name] = {"type": "noul", "noul": self.nouls.get(name, 0.92)}
            elif q["type"] == "choice":
                opts = list(q["criteria"])
                pick = self.choice if self.choice in opts else opts[0]
                probs = {o: (self.confidence if o == pick else round((1 - self.confidence) / max(1, len(opts) - 1), 4)) for o in opts}
                answers[name] = {"type": "choice", "choice": pick, "confidence": self.confidence, "probabilities": probs}
            else:
                n = len(q["criteria"])
                idx = min(self.level - 1, n - 1)
                probs = {str(i): (self.confidence if i == idx else round((1 - self.confidence) / max(1, n - 1), 4)) for i in range(n)}
                answers[name] = {"type": "score", "score": float(idx), "confidence": self.confidence, "legend": {str(i): c for i, c in enumerate(q["criteria"])}, "probabilities": probs}
        return {"model": "fake-jev", "usage": {"input_tokens": 0, "output_tokens": 0}, "answers": answers}
