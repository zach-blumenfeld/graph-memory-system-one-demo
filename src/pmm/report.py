"""Stage 5 report: compare the Stage 3 runs with the skill runs from the recorded traces."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pmm.env import CHECKPOINTS, REPORTS
from pmm.nams_rest import NamsRest
from pmm.record import tool_path_of


def _fmt_ms(ms: Any) -> str:
    try:
        return f"{int(ms) / 1000:.0f}s"
    except (TypeError, ValueError):
        return "?"


def _fmt_usd(v: Any) -> str:
    try:
        return f"${float(v):.2f}"
    except (TypeError, ValueError):
        return "?"


def build(nams: NamsRest | None = None) -> str:
    runs3 = json.loads((CHECKPOINTS / "03-runs.json").read_text())["runs"] if (CHECKPOINTS / "03-runs.json").exists() else {}
    runs5 = json.loads((CHECKPOINTS / "05-skill-run.json").read_text())["runs"] if (CHECKPOINTS / "05-skill-run.json").exists() else []
    rows: list[dict[str, Any]] = []
    for rid, r in runs3.items():
        rows.append({"run": rid, "stage": "3 (no skill)", "kind": r.get("kind"), "brief": r.get("brief"), "model": r.get("model", "default"), "calls": len(r.get("tool_path") or []), "turns": r.get("num_turns"), "wall": r.get("wall_ms"), "cost": r.get("cost_usd"), "path": r.get("tool_path") or []})
    for r in runs5:
        rows.append({"run": r.get("run_id", "skill-run"), "stage": "5 (skill)", "kind": r.get("kind"), "brief": r.get("brief"), "model": r.get("model", "default"), "calls": len(r.get("tool_path") or []), "turns": r.get("num_turns"), "wall": r.get("wall_ms"), "cost": r.get("cost_usd"), "path": r.get("tool_path") or []})
    if nams is not None:
        for row in rows:
            cid = (runs3.get(row["run"]) or {}).get("conversation_id") or next((x.get("conversation_id") for x in runs5 if x.get("run_id") == row["run"]), None)
            if cid and not row["path"]:
                try:
                    row["path"] = tool_path_of(nams.trace(cid))
                    row["calls"] = len(row["path"])
                except Exception:
                    pass

    def avg(xs: list[Any]) -> float | None:
        vals = [float(x) for x in xs if x is not None]
        return sum(vals) / len(vals) if vals else None

    clean3 = [r for r in rows if r["stage"].startswith("3") and r["kind"] == "clean"]
    skill5 = [r for r in rows if r["stage"].startswith("5")]
    lines = [f"# Stage 3 vs Stage 5 comparison", "", f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} from `checkpoints/03-runs.json` and `checkpoints/05-skill-run.json`.", ""]
    lines += ["| group | runs | avg tool calls | avg turns | avg wall | avg cost |", "|---|---|---|---|---|---|"]
    for label, group in (("Stage 3 clean launches (System Two improvising)", clean3), ("Stage 5 skill runs (distilled SKILL.md loaded)", skill5)):
        if group:
            lines.append(f"| {label} | {len(group)} | {avg([r['calls'] for r in group]):.1f} | {avg([r['turns'] for r in group]) or 0:.1f} | {_fmt_ms(avg([r['wall'] for r in group]))} | {_fmt_usd(avg([r['cost'] for r in group]))} |")
    lines += ["", "## Every run", "", "| run | stage | kind | brief | model | calls | turns | wall | cost | tool path |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['run']} | {r['stage']} | {r['kind']} | {r['brief']} | {r['model']} | {r['calls']} | {r['turns'] or '?'} | {_fmt_ms(r['wall'])} | {_fmt_usd(r['cost'])} | {' > '.join(r['path'])} |")
    lines += ["", "Failed calls are marked with `!`. Wall time includes Claude Code startup, the MCP server's Jev startup ping, and NAMS writes (each tool call waits up to 8 s for its record to land).", ""]
    return "\n".join(lines)


def write(nams: NamsRest | None = None, path: Path | None = None) -> Path:
    REPORTS.mkdir(exist_ok=True)
    path = path or REPORTS / "comparison.md"
    path.write_text(build(nams))
    return path
