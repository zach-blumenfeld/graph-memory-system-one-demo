import json

from pmm import report


def test_report_builds_from_checkpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(report, "CHECKPOINTS", tmp_path)
    monkeypatch.setattr(report, "REPORTS", tmp_path / "reports")
    (tmp_path / "03-runs.json").write_text(json.dumps({"runs": {
        "run-01": {"kind": "clean", "brief": "brief-001", "model": "default", "tool_path": ["get_campaign_brief", "log_campaign"], "num_turns": 10, "wall_ms": 90000, "cost_usd": 1.2},
        "run-09": {"kind": "anti-pattern", "brief": "brief-009", "model": "default", "tool_path": ["schedule_send!", "log_campaign"], "num_turns": 12, "wall_ms": 100000, "cost_usd": 1.0},
    }}))
    (tmp_path / "05-skill-run.json").write_text(json.dumps({"runs": [
        {"run_id": "skill-run-brief-013-sonnet", "kind": "skill-run", "brief": "brief-013", "model": "sonnet", "tool_path": ["get_campaign_brief"] * 8, "num_turns": 9, "wall_ms": 60000, "cost_usd": 0.3},
    ]}))
    text = report.build()
    assert "| Stage 3 clean launches" in text and "| 1 | 2.0 | 10.0 | 90s | $1.20 |" in text
    assert "Stage 5 skill runs" in text and "$0.30" in text
    p = report.write()
    assert p.exists() and p.read_text() == text
