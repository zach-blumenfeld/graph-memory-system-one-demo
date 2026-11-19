"""Run the benchmark a config describes: every cell (arm, model, effort) on every application,
each run in its own container that holds one application and can reach only the Anthropic API.

    python3 bench/run.py bench/configs/floor-ceiling.toml [--key-file PATH]

Results go to bench/results/<config name>-<time>/: one JSON file per run (what Claude Code
returned, its usage, the wall time) beside its transcript (`.transcript.jsonl`, every message,
thought summary and tool call), `egress.log` (every connection the containers attempted)
and `config.toml`. `bench/watch.py` shows the runs as they finish; `bench/score.py <that folder>` scores them. The expected outcomes are read
only by the scorer, on the host; nothing here mounts them.
"""
import argparse
import concurrent.futures
import fnmatch
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time
import tomllib

BENCH = pathlib.Path(__file__).resolve().parent
DEMO = BENCH.parent
DEFAULT_KEY_FILE = DEMO.parent / "loan-aip-demo" / ".env"
NETWORK, PROXY, PROXY_IMAGE = "loan-bench-net", "loan-bench-proxy", "python:3.12-slim"
IMAGES = {"baseline": ("loan-bench-baseline", "Dockerfile.baseline")}
ALLOWED_HOSTS = {"baseline": ["api.anthropic.com"]}
RUN_TIMEOUT = 1200


def docker(*args, check=True, **kw):
    return subprocess.run(["docker", *args], check=check, capture_output=True, text=True, **kw)


def api_key(path):
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    for line in pathlib.Path(path).read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit(f"no ANTHROPIC_API_KEY in the environment or in {path}")


def start_network(hosts, network=NETWORK, proxy=PROXY):
    """An internal network (no route out) and the proxy that is its one exit, to `hosts` only."""
    docker("rm", "-f", proxy, check=False)
    docker("network", "rm", network, check=False)
    docker("network", "create", "--internal", network)
    docker("run", "-d", "--name", proxy, "-v", f"{BENCH / 'proxy.py'}:/proxy.py:ro",
           PROXY_IMAGE, "python", "-u", "/proxy.py", *sorted(hosts))
    docker("network", "connect", network, proxy)
    time.sleep(1)


def stop_network(out, network=NETWORK, proxy=PROXY):
    (out / "egress.log").write_text(docker("logs", proxy, check=False).stdout)
    docker("rm", "-f", proxy, check=False)
    docker("network", "rm", network, check=False)


def workdir(arm, app):
    """The files one run sees, and nothing else."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="loan-bench-", dir="/tmp"))
    d.chmod(0o755)
    shutil.copy(DEMO / "source" / "sop.md", d / "sop.md")
    shutil.copy(DEMO / "source" / "policy.md", d / "policy.md")
    shutil.copy(app, d / "application.md")
    return d


def one_run(cell, app, repeat, key, out):
    arm, model, effort = cell["arm"], cell["model"], cell["effort"]
    name = f"{arm}-{model}-{effort}"
    target = out / "runs" / name / f"{app.stem}.r{repeat}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    d = workdir(arm, app)
    command = [
        "docker", "run", "--rm", "--network", NETWORK,
        "-e", "ANTHROPIC_API_KEY",
        "-e", f"HTTPS_PROXY=http://{PROXY}:8080", "-e", f"HTTP_PROXY=http://{PROXY}:8080",
        "-e", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1", "-e", "DISABLE_AUTOUPDATER=1",
        "-v", f"{d}:/work:ro", "--tmpfs", "/tmp", "--memory", "900m",
        IMAGES[arm][0],
        "claude", "-p", (BENCH / f"prompt-{arm}.md").read_text(),
        "--bare", "--model", model, "--effort", effort,
        "--tools", "Read,Bash", "--dangerously-skip-permissions",
        "--output-format", "stream-json", "--verbose", "--json-schema", (BENCH / "result.schema.json").read_text(),
        "--no-session-persistence", "--max-budget-usd", str(cell.get("max_budget_usd", 5)),
    ]
    started = time.time()
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=RUN_TIMEOUT,
                           env={**os.environ, "ANTHROPIC_API_KEY": key})
        code, stdout, stderr = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        code, stdout, stderr = -1, e.stdout or "", "timeout"
    wall = time.time() - started
    shutil.rmtree(d, ignore_errors=True)
    # stdout is the run's transcript, one JSON event per line; the last `result` event is the answer.
    target.with_suffix(".transcript.jsonl").write_text(stdout)
    claude = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            claude = event
    record = {"cell": name, "arm": arm, "model": model, "effort": effort, "application": app.stem,
              "repeat": repeat, "wall_seconds": round(wall, 2), "exit_code": code, "claude": claude,
              "stdout": None if claude is not None else stdout[-4000:], "stderr": stderr[-2000:]}
    target.write_text(json.dumps(record, indent=2) + "\n")
    ok = claude is not None and not claude.get("is_error")
    print(f"{'ok  ' if ok else 'FAIL'} {name:28} {app.stem} r{repeat} {wall:6.1f}s", flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    parser.add_argument("--key-file", default=DEFAULT_KEY_FILE)
    parser.add_argument("--only", help="run only this application id, for a smoke test")
    args = parser.parse_args()
    config_path = pathlib.Path(args.config)
    config = tomllib.loads(config_path.read_text())
    key = api_key(args.key_file)
    apps = sorted(a for a in (DEMO / "applications").glob("*.md")
                  if fnmatch.fnmatch(a.stem, args.only or config.get("applications", "*")))
    cells = config["cell"]
    arms = {c["arm"] for c in cells}
    for arm in arms:
        image, dockerfile = IMAGES[arm]
        subprocess.run(["docker", "build", "-q", "-t", image, "-f", str(BENCH / dockerfile), str(BENCH)], check=True)
    out = BENCH / "results" / f"{config_path.stem}-{time.strftime('%Y%m%d-%H%M%S')}"
    out.mkdir(parents=True)
    shutil.copy(config_path, out / "config.toml")
    jobs = [(c, a, r) for c in cells for a in apps for r in range(1, config.get("repeats", 1) + 1)]
    (out / "plan.json").write_text(json.dumps(
        [{"cell": f"{c['arm']}-{c['model']}-{c['effort']}", "application": a.stem, "repeat": r} for c, a, r in jobs]))
    print(f"{len(jobs)} runs, {config.get('concurrency', 8)} at a time -> {out}", flush=True)
    start_network({h for arm in arms for h in ALLOWED_HOSTS[arm]})
    try:
        with concurrent.futures.ThreadPoolExecutor(config.get("concurrency", 8)) as pool:
            list(pool.map(lambda j: one_run(*j, key, out), jobs))
    finally:
        stop_network(out)
    print(out)


if __name__ == "__main__":
    main()
