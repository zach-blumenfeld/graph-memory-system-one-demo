from pmm import decisions as dec


def test_noul_review_band():
    assert dec._noul({"noul": 0.5}).review is True
    assert dec._noul({"noul": 0.64}).review is True
    assert dec._noul({"noul": 0.66}).review is False
    assert dec._noul({"noul": 0.2}).verdict is False


def test_score_shifts_to_one_based_levels():
    s = dec._score({"score": 2.75, "confidence": 0.71, "probabilities": {"0": 0, "1": 0, "2": 0.29, "3": 0.66, "4": 0.05}})
    assert s.level == 4 and abs(s.score - 3.75) < 1e-9
    assert set(s.probabilities) == {"1", "2", "3", "4", "5"}
    assert s.review is False


def test_choice_low_confidence_is_flagged():
    c = dec._choice({"choice": "launch", "confidence": 0.55, "probabilities": {"launch": 0.6, "update": 0.4}})
    assert c.review is True
    items = dec.review_items({"campaign_type": c})
    assert items[0].question == "campaign_type" and "confidence" in items[0].reason


def test_fake_system_one_round_trip():
    d = dec.Decisions(dec.FakeSystemOne(nouls={"needs_legal_review": 0.52}, confidence=0.55))
    brief = {"Name": "x", "Goal": "g", "Product": "mooring", "Key messages": ["a"], "CTA": "c", "Send window": "2026-10-10", "Notes": ""}
    r = d.classify(brief)
    flagged = {i.question for i in r["review_required"]}
    assert flagged == {"campaign_type", "urgency", "needs_legal_review"}
    assert r["model"] == "fake-jev"


def test_typesafe_adapter_requires_key(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    try:
        dec.TypeSafeSystemOne()
    except dec.JevUnavailable as exc:
        assert "TYPESAFE_API_KEY" in str(exc)
    else:
        raise AssertionError("expected JevUnavailable")
