"""Paths and environment. The only secret source is `.env` in this folder."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("LOAN_ROOT") or Path(__file__).resolve().parents[2])
DATA = ROOT / "data" / "bank"
SOP_FILE = DATA / "sop_assess_loan.md"
POLICY_FILE = DATA / "policy.md"
RUNS_FILE = ROOT / "prompts" / "runs.yaml"
CHECKPOINTS = ROOT / "checkpoints"
SKILL_DIR = ROOT / "skills" / "assess-business-loan"
SOURCE = SKILL_DIR / "source"
RUN_DIR = ROOT / ".run"
SESSIONS_DIR = RUN_DIR / "sessions"
RATIONALES_DIR = RUN_DIR / "rationales"
RECORDER_LOG = RUN_DIR / "recorder.log"
OVERRIDE = ("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD", "NEO4J_DATABASE")


def load_dotenv(path: Path | None = None) -> None:
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        # This folder's .env wins for the memory connection: a `loan` run by the aip server inherits the
        # server's environment, which may carry another demo's NEO4J_* values.
        if k and (k not in os.environ or k in OVERRIDE):
            os.environ[k] = v


def require(*keys: str) -> dict[str, str]:
    load_dotenv()
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"missing in .env: {', '.join(missing)}")
    return {k: os.environ[k] for k in keys}


def ensure_run_dirs() -> None:
    for d in (RUN_DIR, SESSIONS_DIR, RATIONALES_DIR, CHECKPOINTS):
        d.mkdir(parents=True, exist_ok=True)


def recording_enabled() -> bool:
    return os.environ.get("LOAN_RECORD", "1") not in ("0", "false", "no")
