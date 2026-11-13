#!/usr/bin/env python3
"""Part 5, the general loop, done once before the demo and recorded.

    make prebuild-5            # wipes the empty server's store, then runs this against it

Two `aip agent --progress` tasks against AIP_SERVER (the empty server, http://127.0.0.1:8311 by
default), in one session. The first reviews C-1003 on a catalog that holds only aip's shipped
procedures, so `assist` searches, finds nothing, builds a procedure, publishes it and runs it. The
second, in the same session, reviews C-1001: `assist` finds the procedure and runs it. Each is timed.
A third task in the same session is the person's answer, for any run left waiting on a person.
All three run in ./part5 (its ./claims links to the folder's claims). Writes `solutions/part5.md` (the record), `solutions/part5.session` (the session id) and
`solutions/part5.name` (the name it published, for `make check-5`). Stdlib only.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = HERE / "part5"          # its own working directory: ./claims links to ../claims, and its ledger.txt is its own
SHIPPED = {"assist", "build_procedure", "edit_procedure", "make_procedure"}
POLICY = ("no single item over 200, no more than 1000 a month, only travel, meals, software and equipment, "
          "a receipt for anything over 25, no alcohol, submitted within 30 days of the receipt date (the claim's "
          "date is the day it was submitted), the claimant cannot be the approver named on the claim, and no "
          "splitting one purchase into several claims, judged from the claim and its receipt alone. If every rule "
          "clearly holds, approve it; if anything fails or is doubtful, a person decides with a one-line reason. "
          "Every decided claim gets a line (claim id, claimant, amount, category, date, status) in ledger.txt in "
          "the working directory. Report the status, approved or declined, and the reason.")
TASKS = [
    ("C-1003", "Review expense claim C-1003: the claim and its receipt are the files under ./claims (C-1003.json "
               "and the receipt text file it names). Approve or decline it under our policy: " + POLICY),
    ("C-1001", "Review expense claim C-1001 the same way: the claim and its receipt are the files under ./claims "
               "(C-1001.json and the receipt text file it names). Approve or decline it under our policy: " + POLICY),
    ("person", "I am the person who decides expense claims. If a claim's run is waiting for me: C-1003 is declined, "
               "the 236.00 monitor arm is over the 200 single-item limit; C-1001 is approved, the receipt matches "
               "the claim and every rule holds. Finish each run and report each claim's status."),
]


def get(server: str, path: str):
    req = urllib.request.Request(server.rstrip("/") + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def aip_json(*args: str, env: dict):
    out = subprocess.run(["aip", *args], capture_output=True, text=True, env=env)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def agent(task: str, env: dict) -> tuple[dict, str, float, int, list[str]]:
    """One `aip agent --progress`: its final object, stderr, seconds, exit code and lines."""
    t0 = time.monotonic()
    proc = subprocess.Popen(["aip", "agent", "--progress", task], cwd=WORK, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        lines.append(line)
        print(f"  {time.monotonic() - t0:6.1f}s  {line[:160]}", flush=True)
    stderr = proc.stderr.read() if proc.stderr else ""
    code = proc.wait()
    final: dict = {}
    for line in reversed(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and ("done" in obj or "paused" in obj or "error" in obj):
            final = obj
            break
    return final, stderr, time.monotonic() - t0, code, lines


def main() -> int:
    server = os.environ.get("AIP_SERVER") or "http://127.0.0.1:8311"
    env = {k: v for k, v in os.environ.items() if k != "AIP_SESSION"}     # a new session for the first task
    env["AIP_SERVER"] = server
    before = {p["name"] for p in (aip_json("list", "--json", env=env) or [])}
    if before - SHIPPED:
        print(f"the server at {server} already holds {sorted(before - SHIPPED)}; run `make prebuild-5` (it wipes the empty store first)", file=sys.stderr)
        return 2
    version = subprocess.run(["aip", "--version"], capture_output=True, text=True).stdout.strip()
    model = os.environ.get("AIP_AGENT_MODEL_NAME", "?")
    started = datetime.now(timezone.utc)
    record = []
    session = None
    for claim, task in TASKS:
        print(f"\naip agent on {server} ({version}), session {session or 'new'}, model {model}: {claim}", flush=True)
        if session:
            env["AIP_SESSION"] = session
        final, stderr, seconds, code, lines = agent(task, env)
        session = session or final.get("session") or (re.search(r"session: (\S+)", stderr) or [None, None])[1]
        print(f"exit {code} after {seconds:.0f} s; session {session}", flush=True)
        for l in stderr.splitlines()[-10:]:
            print(f"  stderr: {l}", flush=True)
        record.append({"claim": claim, "task": task, "final": final, "stderr": stderr, "seconds": seconds, "code": code,
                       "answers": sum(1 for p in lines if '"event": "answer"' in p)})
        if not session:
            print("no session id in the output; stopping", file=sys.stderr)
            break
    if not session:
        return 1
    (HERE / "solutions" / "part5.session").write_text(session + "\n")
    built = sorted({p["name"] for p in (aip_json("list", "--json", env=env) or [])} - before)
    (HERE / "solutions" / "part5.name").write_text((built[0] if built else "") + "\n")
    runs = sorted(aip_json("runs", "--session", session, "--json", "--limit", "100", env=env) or [], key=lambda r: r.get("started") or "")

    md = ["# Part 5, pre-built: the general loop on the empty server", "",
          f"Run {started.strftime('%Y-%m-%d %H:%M')} UTC by `make prebuild-5` ({version}, model `{model}`) against "
          f"`{server}`, whose catalog held only the shipped procedures ({', '.join(sorted(SHIPPED))}).", "",
          f"Session: `{session}` (also in `solutions/part5.session`).", ""]
    for r in record:
        f = r["final"]
        res = f.get("result") if isinstance(f.get("result"), dict) else {}
        if f.get("done"):
            state = "done"
        elif f.get("paused"):
            state = f"left paused at `{f.get('step')}`"
        elif f.get("error"):
            state = f"failed: `{f.get('error')}` {f.get('message', '')}"
        else:
            state = "no final object"
        md += [f"## {r['claim']}: {r['seconds']:.0f} seconds ({r['seconds'] / 60:.1f} minutes), exit {r['code']}, "
               f"{r['answers']} model answers, {state}", "", f"> {r['task']}", ""]
        if res:
            md += ["`assist` said:", "", "> " + str(res.get("note") or json.dumps(res)).replace("\n", "\n> "), ""]
        if r["stderr"].strip():
            md += ["```", r["stderr"].strip()[-3000:], "```", ""]
    md += ["## What it built", ""]
    if not built:
        md.append("Nothing was published under a new name.")
    for name in built:
        try:
            cat = get(server, f"/catalog/{name}")
        except Exception as exc:
            md.append(f"`{name}`: could not read the catalog entry ({exc})")
            continue
        md += [f"`{name}@{cat.get('revision')}` (bundle `{str(cat.get('bundle_id', ''))[:12]}`): {cat.get('description', '')}", "",
               f"Inputs: {json.dumps(cat.get('inputs'))}.", "", "| Step | Kind | What |", "|---|---|---|"]
        for s in cat.get("steps", []):
            md.append(f"| `{s.get('name')}` | {s.get('kind')} | {str(s.get('description', '')).replace('|', '/')} |")
        md.append("")
    md += ["## The runs of the session", "", "| Run | Procedure | Rev | Status | Started | Finished | Result |", "|---|---|---|---|---|---|---|"]
    for r in runs:
        result = ""
        if r.get("name") in built and r.get("status") == "done":
            try:
                result = json.dumps(get(server, f"/runs/{r['run_id']}").get("result"))[:160].replace("|", "/")
            except Exception:
                pass
        md.append(f"| `{r.get('run_id')}` | {r.get('name')} | {'draft' if r.get('draft') else r.get('revision')} | {r.get('status')} | "
                  f"{str(r.get('started', ''))[11:19]} | {str(r.get('finished') or '')[11:19]} | {result} |")
    md += ["", "## Live, from here", "", "```sh", f"export AIP_SERVER={server}", "export AIP_SESSION=$(cat solutions/part5.session)",
           "cd part5", "aip runs --session $AIP_SESSION", "```", ""]
    (HERE / "solutions" / "part5.md").write_text("\n".join(md))
    print(f"\nwrote solutions/part5.md; session {session}; built {built or 'nothing'}", flush=True)
    return 0 if all(r["final"].get("done") for r in record) else 1


if __name__ == "__main__":
    raise SystemExit(main())
