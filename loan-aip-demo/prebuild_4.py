#!/usr/bin/env python3
"""Part 4's first `aip agent`, done once before the demo, and recorded.

    make prebuild-4            # wipes the empty server's store, then runs this against it

Runs the README's part-4 task with `aip agent --progress` against AIP_SERVER (the empty server,
http://127.0.0.1:8301 by default), times it, and writes `solutions/part4.md`: the session id, how
long it took, what it built (the procedure's name and steps), the runs of the session and the
outcome. The session id alone goes to `solutions/part4.session`, so the README's part 4 can
`export AIP_SESSION=$(cat solutions/part4.session)` and carry the same session on live; the name it
published goes to `solutions/part4.name` (`make check-4`). Stdlib only.
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
SHIPPED = {"assist", "build_procedure", "edit_procedure", "make_procedure"}
TASK = ("Assess loan application APP-1004 under Lantern Mutual's lending policy and SOP in ./source "
        "(policy.md and sop_assess_loan.md; the bank's five systems are the JSON files there). Report "
        "approve, refer or decline, with the rules that fired and a short rationale. If no procedure in "
        "the catalog does this, build one from ./source and write it under ./built, then run it.")


def get(server: str, path: str):
    req = urllib.request.Request(server.rstrip("/") + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def aip_json(*args: str, env: dict) -> object:
    out = subprocess.run(["aip", *args], capture_output=True, text=True, env=env)
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def main() -> int:
    server = os.environ.get("AIP_SERVER") or "http://127.0.0.1:8301"
    env = {k: v for k, v in os.environ.items() if k != "AIP_SESSION"}     # a new session, never a continued one
    env["AIP_SERVER"] = server
    out_md, out_session = HERE / "solutions" / "part4.md", HERE / "solutions" / "part4.session"

    before = {p["name"] for p in (aip_json("list", "--json", env=env) or [])}
    if before - SHIPPED:
        print(f"the server at {server} already holds {sorted(before - SHIPPED)}; run `make prebuild-4` (it wipes the empty store first)", file=sys.stderr)
        return 2
    version = subprocess.run(["aip", "--version"], capture_output=True, text=True).stdout.strip()
    print(f"aip agent on {server} ({version}), session new; the task:\n  {TASK}\n", flush=True)

    started = datetime.now(timezone.utc)
    t0 = time.monotonic()
    proc = subprocess.Popen(["aip", "agent", "--progress", TASK], cwd=HERE, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        lines.append(line)
        print(f"  {time.monotonic() - t0:6.1f}s  {line[:160]}", flush=True)
    stderr = proc.stderr.read() if proc.stderr else ""
    code = proc.wait()
    seconds = time.monotonic() - t0
    print(f"\nexit {code} after {seconds:.0f} s", flush=True)
    for l in stderr.splitlines():
        print(f"  stderr: {l}", flush=True)

    final: dict = {}
    for line in reversed(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and ("done" in obj or "paused" in obj or "error" in obj):
            final = obj
            break
    session = final.get("session") or (re.search(r"session: (\S+)", stderr) or [None, None])[1]
    if not session:
        print("no session id in the output; nothing recorded", file=sys.stderr)
        return 1
    out_session.write_text(session + "\n")

    after = {p["name"] for p in (aip_json("list", "--json", env=env) or [])}
    built = sorted(after - before)
    (HERE / "solutions" / "part4.name").write_text((built[0] if built else "") + "\n")
    runs = aip_json("runs", "--session", session, "--json", "--limit", "100", env=env) or []
    runs = sorted(runs, key=lambda r: r.get("started") or "")
    answers = sum(1 for p in lines if '"event": "answer"' in p)

    md = [f"# Part 4, pre-built: the first `aip agent` on the empty server",
          "",
          f"Run {started.strftime('%Y-%m-%d %H:%M')} UTC by `make prebuild-4` ({version}) against `{server}`, whose catalog held only "
          f"the four shipped procedures ({', '.join(sorted(SHIPPED))}). The README's part 4 continues this session live.",
          "",
          f"Session: `{session}`  (also in `solutions/part4.session`)",
          "",
          f"Took: **{seconds:.0f} seconds** ({seconds / 60:.1f} minutes), exit {code}, {answers} model answers, {len(runs)} runs in the session.",
          "",
          "## The task, verbatim",
          "",
          f"> {TASK}",
          "",
          "## What it built",
          ""]
    if not built:
        md.append("Nothing was published under a new name.")
    for name in built:
        try:
            cat = get(server, f"/catalog/{name}")
        except Exception as exc:
            md.append(f"`{name}`: could not read the catalog entry ({exc})")
            continue
        md += [f"`{name}@{cat.get('revision')}` (bundle `{str(cat.get('bundle_id', ''))[:12]}`): {cat.get('description', '')}",
               "",
               f"Inputs: {json.dumps(cat.get('inputs'))}. Result: {json.dumps(cat.get('result'))}.",
               "",
               "| Step | Kind | What |", "|---|---|---|"]
        for s in cat.get("steps", []):
            md.append(f"| `{s.get('name')}` | {s.get('kind')} | {str(s.get('description', '')).replace('|', '/')} |")
        md.append("")
    md += ["## The runs of the session", "", "| Run | Procedure | Rev | Status | Started | Finished |", "|---|---|---|---|---|---|"]
    for r in runs:
        md.append(f"| `{r.get('run_id')}` | {r.get('name')} | {'draft' if r.get('draft') else r.get('revision')} | {r.get('status')} | "
                  f"{str(r.get('started', ''))[11:19]} | {str(r.get('finished') or '')[11:19]} |")
    md += ["", "## The outcome", ""]
    for r in runs:
        if r.get("name") in built and r.get("status") == "done":
            try:
                rec = get(server, f"/runs/{r['run_id']}")
                res = rec.get("result") or {}
                outcome = res.get("outcome")
                if isinstance(outcome, dict):
                    outcome = outcome.get("value")
                md.append(f"Run `{r['run_id']}` of `{r['name']}`: application {res.get('application_id')}, outcome **{outcome}**, rules fired {json.dumps(res.get('rules_fired'))}.")
                md.append("")
            except Exception as exc:
                md.append(f"Run `{r['run_id']}`: could not read its record ({exc})")
    note = (final.get("result") or {}).get("note") if isinstance(final.get("result"), dict) else None
    if final.get("done"):
        md += ["`assist` finished. Its note:", "", f"> {str(note).replace(chr(10), chr(10) + '> ')}"]
    elif final.get("paused"):
        md += [f"`assist` was left paused at `{final.get('step')}` (the model gave up; see stderr below)."]
    elif final.get("error"):
        md += [f"`assist` failed: `{final.get('error')}` at `{final.get('step')}`: {final.get('message')}"]
    else:
        md += ["No final object was printed; the lines below are what came out."]
    md += ["", "## Live, from here", "",
           "```sh", "export AIP_SERVER=http://127.0.0.1:8301", "export AIP_SESSION=$(cat solutions/part4.session)",
           "aip runs --session $AIP_SESSION", "```", "",
           "## stderr", "", "```", stderr.strip(), "```", "", "## The final object", "", "```json", json.dumps(final, indent=2), "```", ""]
    out_md.write_text("\n".join(md))
    print(f"\nwrote {out_md.relative_to(HERE)} and {out_session.relative_to(HERE)}; session {session}; built {built or 'nothing'}", flush=True)
    return 0 if final.get("done") else 1


if __name__ == "__main__":
    raise SystemExit(main())
