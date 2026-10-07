from pmm.record import claude_command, full_prompt, load_runs


def test_run_matrix_shape():
    runs = load_runs()["runs"]
    assert [r["id"] for r in runs] == [f"run-{i:02d}" for i in range(1, 13)]
    kinds = [r["kind"] for r in runs]
    assert kinds.count("clean") == 8 and kinds.count("anti-pattern") == 2 and kinds.count("escalation") == 1 and kinds.count("nurture") == 1
    assert len({r["brief"] for r in runs}) == 12


def test_claude_command_flags():
    cmd = claude_command("hi", "sid", "sonnet", "mcp__pmm-tools__*")
    assert cmd[:3] == ["claude", "-p", "hi"]
    for flag in ("--mcp-config", "--strict-mcp-config", "--allowedTools", "--output-format", "--session-id", "--model", "--permission-mode", "--tools"):
        assert flag in cmd
    assert cmd[cmd.index("--tools") + 1] == ""


def test_full_prompt_appends_house_rules():
    runs = load_runs()
    p = full_prompt(runs["runs"][0], runs["defaults"]["house_rules"])
    assert p.startswith("New brief in Notion: brief-001") and "House rules" in p


def test_clean_path_checker():
    from pmm.verify import clean_path_problems

    base = ["get_campaign_brief", "classify_brief", "get_audience_segments", "submit_draft", "check_brand_compliance", "score_subject_lines", "schedule_send", "log_campaign"]
    assert clean_path_problems(base) == []
    redraft = base[:6] + ["submit_draft", "check_brand_compliance", "score_subject_lines"] + base[6:]
    assert clean_path_problems(redraft) == []
    bad = base[:3] + ["submit_draft", "schedule_send!", "check_brand_compliance", "score_subject_lines", "schedule_send", "log_campaign"]
    assert any("failed calls" in p for p in clean_path_problems(bad))
    assert any("never called" in p for p in clean_path_problems(base[:-1]))


def test_anti_pattern_runs_skip_house_rules():
    runs = load_runs()
    by_id = {r["id"]: r for r in runs["runs"]}
    assert by_id["run-09"]["house_rules"] is False and by_id["run-10"]["house_rules"] is False
    assert "House rules" not in full_prompt(by_id["run-09"], runs["defaults"]["house_rules"])
    assert "House rules" in full_prompt(by_id["run-01"], runs["defaults"]["house_rules"])
