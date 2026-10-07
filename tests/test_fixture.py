from pmm.fixture import Fixture


def test_fixture_counts(fixture: Fixture):
    assert len(fixture.briefs()) == 13
    assert len(fixture.products()) == 4
    assert len(fixture.personas()) == 4
    assert len(fixture.segments()) == 6


def test_brief_references_resolve(fixture: Fixture):
    products = {p["Name"] for p in fixture.products()}
    for b in fixture.briefs():
        assert b["Product"] in products, b["id"]
        assert fixture.segment(b["Segment"][0])
        assert fixture.persona(b["Persona"][0])
        assert isinstance(b["Key messages"], list) and len(b["Key messages"]) == 3
        assert b["Campaign ID"].startswith("camp-")


def test_segments_filter_by_product(fixture: Fixture):
    segs = fixture.segments("riverbed")
    ids = {s["id"] for s in segs}
    assert {"seg-python-stream-devs", "seg-connector-maintainers", "seg-labs-newsletter"} <= ids
    assert "seg-mooring-early-adopters" not in ids


def test_brand_guide(fixture: Fixture):
    bg = fixture.brand_guide()
    assert "production-ready" in bg["Banned claims"]
    assert "community-supported" in bg["Required disclaimer"]
