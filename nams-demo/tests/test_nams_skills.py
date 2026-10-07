import io
import json
import zipfile

import httpx

from pmm import nams_skills as sk
from pmm.nams_rest import NamsRest


def make_zip(files: dict[str, str], prefix: str = "") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(prefix + name, content)
    return buf.getvalue()


SKILL_MD = """---
name: launch-email-blast
grounding-score: 1.00
procedure-format: graph
---
# Launch Email Blast
1. **Fetch the brief** _(tool: get_campaign_brief)_
   _evidence: 11111111-1111-1111-1111-111111111111_
2. **Classify** _(tool: classify_brief)_
   _evidence: 22222222-2222-2222-2222-222222222222, 33333333-3333-3333-3333-333333333333_
"""


def test_install_zip_flattens_top_folder(tmp_path):
    data = make_zip({"SKILL.md": SKILL_MD, "provenance.json": json.dumps({"claims": [{"groundedIn": ["44444444-4444-4444-4444-444444444444"]}]}), "references/procedures.md": "x"}, prefix="launch-email-blast/")
    dest = tmp_path / "skill"
    files = sk.install_zip(data, dest)
    assert sorted(files) == ["SKILL.md", "provenance.json", "references/procedures.md"]
    summary = sk.summarize_skill_dir(dest)
    assert summary["frontmatter"]["name"] == "launch-email-blast" and summary["steps"] == 2 and summary["claims"] == 1

    from pmm.verify import bound_tools, evidence_ids

    assert bound_tools(dest) == ["classify_brief", "get_campaign_brief"]
    assert len(evidence_ids(dest)) == 4


def test_run_outcome_and_skill_id():
    assert sk.run_outcome({"status": "running"}) is None
    assert sk.run_outcome({"outcome": "Created", "status": "completed"}) == "Created"
    assert sk.run_outcome({"status": "succeeded", "skillId": "sk-1", "groundingScore": 1}) == "Created"
    assert sk.run_outcome({"status": "succeeded"}) == "Withheld"
    assert sk.run_outcome({"status": "withheld", "failCode": "multi_procedure"}) == "Withheld"
    assert sk.run_outcome({"status": "failed"}) == "Failed"
    assert "failCode=multi_procedure" in sk.withhold_reason({"status": "withheld", "failCode": "multi_procedure", "suggestSplitJson": "[[1],[2]]"})
    assert sk.skill_id_of({"skillId": "sk_1"}) == "sk_1"
    assert sk.skill_id_of({"skill": {"id": "sk_2"}}) == "sk_2"
    assert "multi-procedure" in sk.withhold_reason({"outcome": "Withheld", "reason": "multi-procedure gate: 2 procedures"})


def test_distill_flow_against_fake_nams(tmp_path, monkeypatch):
    calls = []
    polls = {"n": 0}
    zip_bytes = make_zip({"SKILL.md": SKILL_MD, "provenance.json": "{}"})

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        assert request.headers["X-Workspace-Id"] == "ws-test"
        p = request.url.path
        if p == "/v1/skills/capabilities":
            return httpx.Response(200, json={"distillation": True})
        if p == "/v1/skills/generate":
            body = json.loads(request.content)
            rid = "run-ws" if body["scope"]["type"] == "workspace" else "run-conv"
            return httpx.Response(202, json={"runId": rid})
        if p.startswith("/v1/skills/runs/run-conv"):
            polls["n"] += 1
            if polls["n"] == 1:
                return httpx.Response(200, json={"status": "running", "stage": "synthesize"})
            return httpx.Response(200, json={"status": "completed", "outcome": "Created", "skillId": "sk_42"})
        if p.startswith("/v1/skills/runs/run-ws"):
            return httpx.Response(200, json={"status": "completed", "outcome": "Withheld", "reason": "scope contains 2 distinct procedures"})
        if p == "/v1/skills/sk_42":
            return httpx.Response(200, json={"id": "sk_42", "status": "in_review"})
        if p == "/v1/skills/sk_42/explain-provenance":
            return httpx.Response(200, json={"claims": 3})
        if p == "/v1/skills/sk_42/review":
            return httpx.Response(200, json={"status": "approved"})
        if p == "/v1/skills/sk_42/publish":
            return httpx.Response(200, json={"status": "published"})
        if p == "/v1/skills/sk_42/download":
            return httpx.Response(200, content=zip_bytes, headers={"content-type": "application/zip"})
        if p == "/v1/skills/sk_42/drift":
            return httpx.Response(200, json={"drifted": []})
        return httpx.Response(404, json={"error": f"unexpected {p}"})

    nams = NamsRest(base="https://nams.test", api_key="k", workspace_id="ws-test", transport=httpx.MockTransport(handler))
    meta = sk.distill(nams, ["c1", "c2"], fallback_ids=["c1"], log=lambda *_: None, out_dir=tmp_path / "ck", skill_dir=tmp_path / "skill")
    assert (tmp_path / "skill" / "SKILL.md").exists() and meta["skill_summary"]["steps"] == 2
    assert meta["result"] == "published" and meta["skill_id"] == "sk_42"
    labels = [a["label"] for a in meta["attempts"]]
    assert labels == ["clean-scope", "workspace-scope-demo"]
    assert meta["attempts"][1]["outcome"] == "Withheld" and "2 distinct procedures" in meta["attempts"][1]["reason"]
    assert ("POST", "/v1/skills/sk_42/review") in calls and ("POST", "/v1/skills/sk_42/publish") in calls
    assert (tmp_path / "ck" / "launch-email-blast.zip").exists() and (tmp_path / "ck" / "meta.json").exists()

