"""A live screen for a benchmark run: every run's five measures as it finishes, and the running
averages for each cell.

    python3 bench/watch.py [results folder] [--once]

With no folder it follows the newest one under bench/results. Each run is five marks, in the
order outcome, failed rules, missing, customer message, officer message.
"""
import json
import pathlib
import re
import sys
import time

import score

RESULTS = pathlib.Path(__file__).resolve().parent / "results"
GREEN, RED, DIM, BOLD, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"
COLUMNS = [("outcome", "outcome"), ("failed_rules", "rules"), ("missing", "missing"), ("customer_message", "customer"),
           ("officer_message", "officer"), ("all_five", "all 5"), ("tokens_total", "tokens"), ("tokens_output", "out tok"), ("tokens_thinking", "thinking"),
           ("cost_usd", "$/run"), ("turns", "turns"), ("seconds_mean", "sec avg"), ("seconds_max", "sec max")]


def screen(folder):
    plan = json.loads((folder / "plan.json").read_text()) if (folder / "plan.json").exists() else []
    rows = score.load(folder)
    done = {(r["cell"], r["application"], r["repeat"]): r for r in rows}
    cells = sorted({j["cell"] for j in plan} | {r["cell"] for r in rows})
    apps = sorted({j["application"] for j in plan} | {r["application"] for r in rows})
    repeats = sorted({j["repeat"] for j in plan} | {r["repeat"] for r in rows})
    started = folder.stat().st_birthtime if hasattr(folder.stat(), "st_birthtime") else folder.stat().st_ctime
    last = max((p.stat().st_mtime for p in (p for p in folder.glob("runs/*/*.json") if re.search(r"\.r\d+\.json$", p.name))), default=time.time())
    finished = bool(plan) and len(done) >= len(plan)
    elapsed = int((last if finished else time.time()) - started)
    lines = [f"{BOLD}{folder.name}{OFF}   {len(done)}/{len(plan) or len(done)} runs   "
             f"{elapsed // 60}:{elapsed % 60:02d}   {'finished' if finished else 'running'}", ""]
    summary = score.summarize(rows) if rows else {}
    lines.append(f"{'cell':26}{'done':>7}" + "".join(f"{label:>9}" for _, label in COLUMNS))
    for cell in cells:
        total = sum(1 for j in plan if j["cell"] == cell)
        s = summary.get(cell)
        values = "".join(f"{s[key]:>9}" for key, _ in COLUMNS) if s else ""
        lines.append(f"{cell:26}{(str(s['runs']) if s else '0') + '/' + str(total):>7}{values}")
    lines += ["", f"{DIM}each run: outcome, rules, missing, customer, officer{OFF}",
              f"{'':26}" + "".join(f"{a.replace('APP-', ''):>7}" for a in apps)]
    for cell in cells:
        for repeat in repeats:
            marks = ""
            for app in apps:
                r = done.get((cell, app, repeat))
                if r is None:
                    marks += f"  {DIM}·····{OFF}"
                elif not r["answered"]:
                    marks += f"  {RED}error{OFF}"
                else:
                    marks += "  " + "".join(f"{GREEN}✓{OFF}" if r[m] else f"{RED}✗{OFF}" for m in score.MEASURES)
            lines.append(f"{cell + (f' r{repeat}' if len(repeats) > 1 else ''):26}{marks}")
    wrong = [r for r in rows if not all(r[m] for m in score.MEASURES)]
    if wrong:
        lines += ["", "missed:"]
        for r in wrong[-12:]:
            missed = ", ".join(m for m in score.MEASURES if not r[m])
            lines.append(f"  {r['cell']:26} {r['application']} expected {r['expected']}, got {r['got'] or 'no answer'} "
                         f"[{r['got_failed_rules']}]  {missed}  {DIM}{r['message_failures']}{OFF}")
    return "\n".join(lines), finished


def newest():
    folders = sorted((p for p in RESULTS.iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime) if RESULTS.exists() else []
    return folders[-1] if folders else None


def main():
    args = [a for a in sys.argv[1:] if a != "--once"]
    once = "--once" in sys.argv
    while True:
        folder = pathlib.Path(args[0]) if args else newest()
        text, finished = screen(folder) if folder else ("waiting for a run to start", False)
        sys.stdout.write(("" if once else "\033[2J\033[H") + text + "\n")
        sys.stdout.flush()
        if once or (finished and args):
            return
        time.sleep(2)


if __name__ == "__main__":
    main()
