"""Have Claude build the AIP procedure from the SOP and the policy, alone in a container.

    python3 bench/build.py [--model fable] [--effort high]

The container holds the SOP, the policy, the two development applications (applications-dev/,
which are not in the benchmark), the aip command and its skill. It does not hold the benchmark's
applications, the expected outcomes or the scorer, and it can reach only the Anthropic API and
the decision model. What it writes under ./built is copied to <demo>/built/ when it finishes;
the transcript, the final report and the egress log go to bench/results/build-<time>/.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time

from run import BENCH, DEFAULT_KEY_FILE, DEMO, api_key, decision_model_key, start_network, stop_network

AIP_CHECKOUT = pathlib.Path(os.environ.get("AIP_CHECKOUT", pathlib.Path.home() / "dev" / "aip-0.9"))
IMAGE, NETWORK, PROXY = "loan-bench-aip", "loan-bench-build-net", "loan-bench-build-proxy"
HOSTS = ["api.anthropic.com", "api.typesafe.ai"]
TIMEOUT = 90 * 60


def build_image():
    """The aip wheel from the local checkout and the aip skill, then the image over them."""
    context = BENCH / ".context"
    shutil.rmtree(context, ignore_errors=True)
    subprocess.run(["uv", "build", "--wheel", "-o", str(context / "wheels")], cwd=AIP_CHECKOUT, check=True,
                   capture_output=True)
    shutil.copytree(AIP_CHECKOUT / "skills" / "aip", context / "skill")
    subprocess.run(["docker", "build", "-q", "-t", IMAGE, "-f", str(BENCH / "Dockerfile.aip"), str(BENCH)], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="fable")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--max-budget-usd", default="40")
    parser.add_argument("--key-file", default=DEFAULT_KEY_FILE)
    args = parser.parse_args()
    keys = {"ANTHROPIC_API_KEY": api_key(args.key_file), "AIP_DECISION_MODEL_KEY": decision_model_key()}
    build_image()
    out = BENCH / "results" / f"build-{time.strftime('%Y%m%d-%H%M%S')}"
    out.mkdir(parents=True)
    work = pathlib.Path(tempfile.mkdtemp(prefix="loan-bench-build-", dir="/tmp"))
    work.chmod(0o777)
    shutil.copytree(DEMO / "source", work / "source")
    shutil.copytree(DEMO / "applications-dev", work / "examples")
    (work / "built").mkdir()
    (work / "built").chmod(0o777)
    prompt = (BENCH / "prompt-build.md").read_text()
    shutil.copy(BENCH / "prompt-build.md", out / "prompt.md")
    command = [
        "docker", "run", "--rm", "--network", NETWORK,
        "-e", "ANTHROPIC_API_KEY", "-e", "AIP_DECISION_MODEL_KEY",
        "-e", f"HTTPS_PROXY=http://{PROXY}:8080", "-e", f"HTTP_PROXY=http://{PROXY}:8080",
        "-e", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1", "-e", "DISABLE_AUTOUPDATER=1",
        "-v", f"{work}:/work", "--tmpfs", "/tmp", "--memory", "2g",
        IMAGE,
        "claude", "-p", prompt, "--bare", "--model", args.model, "--effort", args.effort,
        "--tools", "Read,Write,Edit,Bash", "--dangerously-skip-permissions",
        "--output-format", "stream-json", "--verbose",
        "--no-session-persistence", "--max-budget-usd", args.max_budget_usd,
    ]
    print(f"building with {args.model} at {args.effort} -> {out}", flush=True)
    start_network(HOSTS, NETWORK, PROXY)
    started = time.time()
    try:
        with open(out / "transcript.jsonl", "w") as transcript:
            code = subprocess.run(command, stdout=transcript, stderr=subprocess.PIPE, text=True, timeout=TIMEOUT,
                                  env={**os.environ, **keys}).returncode
    except subprocess.TimeoutExpired:
        code = -1
    finally:
        stop_network(out, NETWORK, PROXY)
    result = None
    for line in (out / "transcript.jsonl").read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            result = event
    (out / "result.json").write_text(json.dumps({"exit_code": code, "wall_seconds": round(time.time() - started, 1),
                                                 "model": args.model, "effort": args.effort, "claude": result}, indent=2) + "\n")
    shutil.copytree(work / "built", out / "built")
    shutil.copytree(work, out / "workdir", ignore=shutil.ignore_patterns("built"))
    if any((work / "built").iterdir()):
        shutil.rmtree(DEMO / "built", ignore_errors=True)
        shutil.copytree(work / "built", DEMO / "built")
    shutil.rmtree(work, ignore_errors=True)
    if result:
        (out / "report.md").write_text(str(result.get("result", "")) + "\n")
        print(result.get("result", ""))
        print(f"\n{result.get('num_turns')} turns, {round((result.get('duration_ms') or 0) / 60000, 1)} minutes, "
              f"${round(result.get('total_cost_usd') or 0, 2)}")
    print(out)


if __name__ == "__main__":
    main()
