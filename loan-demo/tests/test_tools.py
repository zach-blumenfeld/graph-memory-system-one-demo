"""Step 3 tests. The policy facts run against the JSON fixture (always) and against the memory graph
(when .env points at an imported database); the lint test needs the graph for the cite lookup."""

from __future__ import annotations

import json
import os

import pytest

from loan.env import load_dotenv
from loan.fixture import EXPECTED, Fixture, FixtureRepo
from loan.policy import PROTECTED_WORDS, evaluate, figures

load_dotenv()


def _graph_ready() -> bool:
    if not all(os.environ.get(k) for k in ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")):
        return False
    try:
        from loan.memory import cypher

        return cypher("MATCH (a:Application) RETURN count(a) AS n")[0]["n"] == 5
    except Exception:
        return False


needs_graph = pytest.mark.skipif(not _graph_ready(), reason="memory database not imported (.env / loan import)")


@pytest.mark.parametrize("app_id", sorted(EXPECTED))
def test_policy_on_fixture(app_id):
    fx = Fixture()
    res = evaluate(figures(FixtureRepo(fx), app_id, fx.as_of()), fx.rules())
    assert res["outcome"] == EXPECTED[app_id]["outcome"]
    assert [f["rule"] for f in res["fired"]] == EXPECTED[app_id]["fired"]
    assert abs(res["figures"]["coverage_ratio"] - EXPECTED[app_id]["coverage"]) <= 0.02


@needs_graph
@pytest.mark.parametrize("app_id", sorted(EXPECTED))
def test_loan_policy_on_graph(app_id):
    from loan import tools

    res = tools.policy(app_id)
    assert res["outcome"] == EXPECTED[app_id]["outcome"]
    assert [f["rule"] for f in res["fired"]] == EXPECTED[app_id]["fired"]
    for f in res["fired"]:
        assert f["cites"], f"{f['rule']} fired without cites"


@needs_graph
def test_r5_only_through_ownership():
    from loan import tools

    own = tools.ownership("BUS-01")
    late = [(ob["business"]["name"], f["key"], f["late_days"]) for o in own["owners"] for ob in o["other_businesses"] for f in ob["facilities"]]
    assert late == [("Alder Logistics", "FAC-03", 90)]
    assert all(f["late_days"] == 0 for f in tools.facilities("BUS-01")["facilities"])


@needs_graph
def test_application_never_returns_dob():
    from loan import tools

    text = json.dumps(tools.application("APP-1001")) + json.dumps(tools.ownership("BUS-01"))
    assert "dob" not in text and "1968" not in text and "1975" not in text


@needs_graph
def test_check_rejects_fake_cite_invented_figure_and_protected_words(tmp_path, monkeypatch):
    from loan import tools

    monkeypatch.setattr(tools, "RATIONALES_DIR", tmp_path)
    sub = tools.submit_rationale("APP-1002", "approve", "Approve APP-1002 [cite: FAKE-999]. Coverage 1.9x, payment $9,999, the owner is 46 years old.")
    res = tools.check(sub["rationale_id"])
    checks = {f["check"] for f in res["failures"]}
    assert not res["passed"]
    assert checks == {"cite_exists", "figure_in_evidence", "no_protected_characteristics"}
    with pytest.raises(SystemExit):
        tools.record(sub["rationale_id"], "approve", 0.9, "test")


@needs_graph
def test_check_passes_a_cited_rationale(tmp_path, monkeypatch):
    from loan import tools

    monkeypatch.setattr(tools, "RATIONALES_DIR", tmp_path)
    pol = tools.policy("APP-1002")
    text = (f"Approve APP-1002 for $250,000 over 60 months [cite: APP-1002]. Coverage is {pol['figures']['coverage_ratio']}x against a proposed "
            f"payment of ${pol['figures']['proposed_monthly_payment']:,.0f} [cite: {pol['cites']['coverage'][0]}]. KYC is current [cite: KYC-BUS-02].")
    sub = tools.submit_rationale("APP-1002", "approve", text)
    res = tools.check(sub["rationale_id"])
    assert res["passed"], res["failures"]


def test_protected_words_do_not_match_ordinary_words():
    assert not PROTECTED_WORDS.search("coverage of 1.6x, the average, the manager, the bakery's second location")
    assert PROTECTED_WORDS.search("the owner, aged 58,")
