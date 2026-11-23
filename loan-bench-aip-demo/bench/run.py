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
DEFAULT_KEY_FILE = DEMO / ".env"
NETWORK, PROXY, PROXY_IMAGE = "loan-bench-net", "loan-bench-proxy", "python:3.12-slim"
# The arms. `aip` drives the procedure with the aip command, learned from the skill file;
# `aip-mcp` is handed aip as MCP tools (describe, run, resume) and has no other tool.
IMAGES = {"baseline": ("loan-bench-baseline", "Dockerfile.baseline"), "aip": ("loan-bench-aip", "Dockerfile.aip"),
          "aip-mcp": ("loan-bench-aip", "Dockerfile.aip")}
ALLOWED_HOSTS = {"baseline": ["api.anthropic.com"], "aip": ["api.anthropic.com", "api.typesafe.ai"],
                 "aip-mcp": ["api.anthropic.com", "api.typesafe.ai"]}
MCP_CONFIG = json.dumps({"mcpServers": {"aip": {"command": "aip", "args": ["mcp"], "env": {
    k: "${" + k + "}" for k in ("AIP_DECISION_MODEL_KEY", "AIP_HOME", "HTTPS_PROXY", "HTTP_PROXY", "PATH", "HOME")}}}})
TOOLS = {"baseline": ["--tools", "Read,Bash"], "aip": ["--tools", "Read,Bash"],
         "aip-mcp": ["--tools", "", "--mcp-config", MCP_CONFIG, "--strict-mcp-config", "--disallowedTools",
                     "mcp__aip__search,mcp__aip__compile,mcp__aip__agent,mcp__aip__pull,mcp__aip__publish"]}
AIP_CONFIG = pathlib.Path.home() / ".config" / "aip" / "config.json"
PROCEDURE = DEMO / "built" / "assess_term_loan"
AIP_ARMS = {"aip", "aip-mcp"}
RUN_TIMEOUT = 1200


def docker(*args, check=True, **kw):
    return subprocess.run(["docker", *args], check=check, capture_output=True, text=True, **kw)


def key(name, path):
    """A key from the environment, or else from its `NAME=value` line in the key file."""
    if os.environ.get(name):
        return os.environ[name]
    path = pathlib.Path(path)
    for line in path.read_text().splitlines() if path.exists() else []:
        if line.startswith(name + "="):
            return line.split("=", 1)[1].strip().strip("\"'")
    return None


def api_key(path):
    found = key("ANTHROPIC_API_KEY", path)
    if not found:
        raise SystemExit(f"no ANTHROPIC_API_KEY in the environment or in {path}")
    return found


def decision_model_key(path):
    """The decision model's key, which the AIP arm needs: a `Decide` cannot run without it."""
    found = key("AIP_DECISION_MODEL_KEY", path)
    if not found and AIP_CONFIG.exists():      # where `aip config --decision-model-key` keeps it
        found = (json.loads(AIP_CONFIG.read_text()).get("decision_model") or {}).get("api_key")
    if not found:
        raise SystemExit(f"no AIP_DECISION_MODEL_KEY in the environment, in {path} or in {AIP_CONFIG}")
    return found


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
    shutil.copy(app, d / "application.md")
    if arm in AIP_ARMS:                   # the procedure and the application; aip writes its run's files here
        shutil.copytree(PROCEDURE, d / PROCEDURE.name, ignore=shutil.ignore_patterns("__pycache__"))
        for path in [d, *d.rglob("*")]:
            path.chmod(0o777)
    else:                                 # the SOP, the policy and the application, read-only
        shutil.copy(DEMO / "source" / "sop.md", d / "sop.md")
        shutil.copy(DEMO / "source" / "policy.md", d / "policy.md")
        d.chmod(0o755)
    return d


def one_run(cell, app, repeat, keys, out):
    arm, model, effort = cell["arm"], cell["model"], cell["effort"]
    name = f"{arm}-{model}-{effort}"
    target = out / "runs" / name / f"{app.stem}.r{repeat}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    d = workdir(arm, app)
    command = [
        "docker", "run", "--rm", "--network", NETWORK,
        "-e", "ANTHROPIC_API_KEY",
        # aip keeps its run files under AIP_HOME; in the work folder they outlive the container
        *(["-e", "AIP_DECISION_MODEL_KEY", "-e", "AIP_HOME=/work/.aip"] if arm in AIP_ARMS else []),
        "-e", f"HTTPS_PROXY=http://{PROXY}:8080", "-e", f"HTTP_PROXY=http://{PROXY}:8080",
        "-e", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1", "-e", "DISABLE_AUTOUPDATER=1",
        "-v", f"{d}:/work" + ("" if arm in AIP_ARMS else ":ro"), "--tmpfs", "/tmp", "--memory", "900m",
        IMAGES[arm][0],
        "claude", "-p", (BENCH / f"prompt-{arm}.md").read_text().replace("{application}", app.read_text()),
        "--bare", "--model", model, "--effort", effort,
        *TOOLS[arm], "--dangerously-skip-permissions",
        "--output-format", "stream-json", "--verbose", "--json-schema", (BENCH / "result.schema.json").read_text(),
        "--no-session-persistence", "--max-budget-usd", str(cell.get("max_budget_usd", 5)),
    ]
    started = time.time()
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=RUN_TIMEOUT,
                           env={**os.environ, **keys})
        code, stdout, stderr = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        code, stdout, stderr = -1, e.stdout or "", "timeout"
    wall = time.time() - started
    if arm in AIP_ARMS:                   # what the procedure filed: the decisions, returns and queue lines
        filed = {f.name: f.read_text() for f in d.rglob("*.jsonl")}
        target.with_suffix(".filed.json").write_text(json.dumps(filed, indent=2) + "\n")
        # aip's own record of each run: every step it took, with what the step read and produced
        records = [json.loads(f.read_text()) for f in sorted((d / ".aip" / "runs").glob("*.json"))]
        target.with_suffix(".aip-runs.json").write_text(json.dumps(records, indent=2) + "\n")
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
    keys = {"ANTHROPIC_API_KEY": api_key(args.key_file)}
    apps = sorted(a for a in (DEMO / "applications").glob("*.md")
                  if fnmatch.fnmatch(a.stem, args.only or config.get("applications", "*")))
    cells = config["cell"]
    arms = {c["arm"] for c in cells}
    if arms & AIP_ARMS:
        keys["AIP_DECISION_MODEL_KEY"] = decision_model_key(args.key_file)
        if not (PROCEDURE / "procedure.aip").exists():
            raise SystemExit(f"no procedure at {PROCEDURE}: run bench/build.py first")
        import build
        build.build_image()
    for arm in arms - AIP_ARMS:
        image, dockerfile = IMAGES[arm]
        subprocess.run(["docker", "build", "-q", "-t", image, "-f", str(BENCH / dockerfile), str(BENCH)], check=True)
    out = BENCH / "results" / f"{config_path.stem}-{time.strftime('%Y%m%d-%H%M%S')}"
    out.mkdir(parents=True)
    shutil.copy(config_path, out / "config.toml")
    # Repeat by repeat, and within a repeat application by application across the cells, so a run
    # that is cut short still leaves every cell with the same applications done.
    jobs = [(c, a, r) for r in range(1, config.get("repeats", 1) + 1) for a in apps for c in cells]
    (out / "plan.json").write_text(json.dumps(
        [{"cell": f"{c['arm']}-{c['model']}-{c['effort']}", "application": a.stem, "repeat": r} for c, a, r in jobs]))
    print(f"{len(jobs)} runs, {config.get('concurrency', 8)} at a time -> {out}", flush=True)
    start_network({h for arm in arms for h in ALLOWED_HOSTS[arm]})
    try:
        with concurrent.futures.ThreadPoolExecutor(config.get("concurrency", 8)) as pool:
            list(pool.map(lambda j: one_run(*j, keys, out), jobs))
    finally:
        stop_network(out)
    print(out)


if __name__ == "__main__":
    main()
