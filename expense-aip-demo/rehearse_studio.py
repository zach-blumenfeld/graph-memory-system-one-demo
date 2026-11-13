#!/usr/bin/env python3
"""Part 1 without a browser: drive the console's Studio endpoints as the page does.

    python3 rehearse_studio.py build            # open a Studio, paste the brief, save the draft
    python3 rehearse_studio.py run C-1001       # run the saved draft on a claim; the model answers, the person's step is ours
    python3 rehearse_studio.py publish          # publish the saved draft
    python3 rehearse_studio.py edit "<instruction>"   # part 3: one chat message on the same draft, then save it

It talks to the console on AIP_DEMO_CONSOLE_PORT (4283). The console must have been started with
.env loaded (`make console`), or its chat has no model. State between calls is kept in
.aip/studio.json (workspace, session, bundle). Stdlib only. Rehearsal only: on stage the presenter
uses the page.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = os.environ.get("AIP_DEMO_CONSOLE_PORT", "4283")
BASE = f"http://localhost:{PORT}"
STATE = HERE / ".aip" / "studio.json"
NAME = "expense_claim_review"
BRIEF = (HERE / "brief.txt").read_text().strip()


def post(path: str, body: dict, stream: bool = False):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Origin": BASE})
    r = urllib.request.urlopen(req, timeout=3600)
    return r if stream else json.load(r)


def sse(resp, t0: float, log: list) -> tuple[dict | None, dict | None]:
    """Print each line as it comes; return the final object and the exit event."""
    final = exit_ = None
    event = None
    for raw in resp:
        line = raw.decode().rstrip("\n")
        if line.startswith("event: "):
            event = line[7:]
            continue
        if not line.startswith("data: "):
            if not line:
                event = None
            continue
        data = line[6:]
        log.append({"t": round(time.monotonic() - t0, 1), "event": event, "data": data})
        try:
            obj = json.loads(data)
        except json.JSONDecodeError:
            obj = None
        if event == "exit":
            exit_ = obj
        elif event is None and isinstance(obj, dict) and obj.get("event") is None and any(k in obj for k in ("paused", "done", "error")):
            final = obj
        print(f"  {time.monotonic() - t0:6.1f}s  {(event or '')[:8]:8} {data[:200]}", flush=True)
    return final, exit_


def load() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def save_state(s: dict) -> None:
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(s, indent=2))


def build() -> int:
    session = f"studio-{time.strftime('%H%M%S')}"
    ws = post("/console/studio/open", {"name": NAME})["workspace"]
    print(f"workspace {ws}  session {session}\nbrief: {BRIEF[:120]}...", flush=True)
    t0 = time.monotonic()
    log: list = []
    final, exit_ = sse(post("/console/studio/build", {"workspace": ws, "brief": BRIEF, "title": NAME, "session": session}, stream=True), t0, log)
    secs = time.monotonic() - t0
    s = {"workspace": ws, "session": session, "build_seconds": round(secs), "build_final": final, "build_exit": exit_}
    save_state(s)
    (HERE / ".aip" / "studio-build.log.json").write_text(json.dumps(log, indent=1))
    print(f"\nbuild ended after {secs:.0f} s", flush=True)
    if final and "paused" in final:
        print("THE BUILD ASKED (paused at %s):" % final.get("step"), json.dumps(final, indent=1)[:4000], flush=True)
        return 3
    if not final or not final.get("done"):
        print("the build did not finish:", json.dumps(final)[:2000], json.dumps(exit_)[:2000], flush=True)
        return 1
    read = post("/console/studio/read", {"workspace": ws})
    print(f"folder {read['name']}: compiles {read['ok']}; files {sorted(read['files'])}", flush=True)
    saved = post("/console/studio/save", {"workspace": ws, "source": read["source"], "publish": False})
    s.update(bundle_id=saved.get("bundle_id"), name=read["name"], saved=saved)
    save_state(s)
    print(f"saved draft: bundle {saved.get('bundle_id')} runnable {saved.get('runnable')}", flush=True)
    print("review:\n" + json.dumps((final.get("result") or {}), indent=1)[:6000], flush=True)
    return 0


def claim_inputs(claim_id: str) -> dict:
    c = json.loads((HERE / "claims" / f"{claim_id}.json").read_text())
    c["receipt"] = (HERE / "claims" / c.pop("receipt_file")).read_text()
    return c


def person_step(s: dict) -> str:
    """The step a person answers: the Task_Agent whose name says person (each build names it its own way)."""
    import re
    read = post("/console/studio/read", {"workspace": s["workspace"]})
    names = re.findall(r"^\s*Task_Agent\s+(\w+)", read["source"], re.M)
    hits = [n for n in names if "person" in n or "human" in n or "review" in n]
    if not hits:
        raise SystemExit(f"no person's step among the Task_Agents {names}")
    return hits[0]


def map_inputs(s: dict, claim: dict) -> dict:
    """The claim under the names this build gave its inputs, as a person fills the Run form."""
    import re
    source = post("/console/studio/read", {"workspace": s["workspace"]})["source"]
    block = re.search(r"^Start\b.*?\{(.*?)\n\s*Next_Step", source, re.S | re.M)
    names = re.findall(r"^\s*(\w+):", block.group(1), re.M) if block else list(claim)
    out = {}
    for n in names:
        key = n if n in claim else ("receipt" if "receipt" in n else "date" if "date" in n else "claim_id" if n.endswith("id") else n)
        if key in claim:
            out[n] = claim[key]
    return out


def run(claim_id: str, person: str, answer: str) -> int:
    s = load()
    if person == "auto":
        person = person_step(s)
    claim = claim_inputs(claim_id)
    inputs = map_inputs(s, claim)
    t0 = time.monotonic()
    log: list = []
    print(f"run bundle:{s['bundle_id']} on {claim_id}; person's step {person}", flush=True)
    final, exit_ = sse(post("/console/agent", {"ref": f"bundle:{s['bundle_id']}", "inputs": inputs, "person": [person],
                                               "studio": True, "session": s["session"]}, stream=True), t0, log)
    while final and "paused" in final and final.get("step") == person:
        print(f"\nTHE PERSON'S STEP: {json.dumps(final)[:3000]}", flush=True)
        answers = json.loads(answer)
        final, exit_ = sse(post("/console/resume", {"run_id": final["run_id"], "answers": answers, "person": [person],
                                                    "studio": True, "session": s["session"], "workspace": s["workspace"]}, stream=True), t0, log)
    print(f"\nrun ended after {time.monotonic() - t0:.0f} s: {json.dumps(final)[:3000]}", flush=True)
    s.setdefault("runs", []).append({"claim": claim_id, "final": final, "seconds": round(time.monotonic() - t0)})
    save_state(s)
    return 0 if final and final.get("done") else 1


def publish() -> int:
    s = load()
    read = post("/console/studio/read", {"workspace": s["workspace"]})
    out = post("/console/studio/save", {"workspace": s["workspace"], "source": read["source"], "publish": True})
    print(json.dumps({k: out.get(k) for k in ("name", "revision", "bundle_id")}), flush=True)
    return 0


def edit(instruction: str) -> int:
    s = load()
    t0 = time.monotonic()
    log: list = []
    print(f"edit workspace {s['workspace']}: {instruction}", flush=True)
    final, exit_ = sse(post("/console/studio/edit", {"workspace": s["workspace"], "instruction": instruction, "session": s["session"]}, stream=True), t0, log)
    secs = time.monotonic() - t0
    print(f"\nedit ended after {secs:.0f} s", flush=True)
    if not final or not final.get("done"):
        print("the edit did not finish:", json.dumps(final)[:3000], json.dumps(exit_)[:2000], flush=True)
        return 1
    print(json.dumps(final.get("result"), indent=1)[:6000], flush=True)
    read = post("/console/studio/read", {"workspace": s["workspace"]})
    saved = post("/console/studio/save", {"workspace": s["workspace"], "source": read["source"], "publish": False})
    s.update(bundle_id=saved.get("bundle_id"), edit_seconds=round(secs), edit_final=final)
    save_state(s)
    print(f"compiles {read['ok']}; saved draft: bundle {saved.get('bundle_id')}", flush=True)
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        raise SystemExit(build())
    if cmd == "run":
        raise SystemExit(run(sys.argv[2], sys.argv[3], sys.argv[4]))
    if cmd == "edit":
        raise SystemExit(edit(sys.argv[2]))
    if cmd == "publish":
        raise SystemExit(publish())
    print(__doc__)
    raise SystemExit(2)
