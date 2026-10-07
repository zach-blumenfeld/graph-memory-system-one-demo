"""Paths and environment. The only secret source is `.env` in this folder."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("BLAST_ROOT") or Path(__file__).resolve().parents[2])
DATA = ROOT / "data" / "notion"
SOP_FILE = DATA / "sop_email_blast.md"
RUNS_FILE = ROOT / "prompts" / "runs.yaml"
CHECKPOINTS = ROOT / "checkpoints"
SKILL_DIR = ROOT / "skills" / "launch-email-blast"
SOURCE = SKILL_DIR / "source"
RUN_DIR = ROOT / ".run"
SESSIONS_DIR = RUN_DIR / "sessions"
DRAFTS_DIR = RUN_DIR / "drafts"
RECORDER_LOG = RUN_DIR / "recorder.log"


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
        if k and k not in os.environ:
            os.environ[k] = v


def require(*keys: str) -> dict[str, str]:
    load_dotenv()
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"missing in .env: {', '.join(missing)}")
    return {k: os.environ[k] for k in keys}


def ensure_run_dirs() -> None:
    for d in (RUN_DIR, SESSIONS_DIR, DRAFTS_DIR, CHECKPOINTS):
        d.mkdir(parents=True, exist_ok=True)


def recording_enabled() -> bool:
    return os.environ.get("BLAST_RECORD", "1") not in ("0", "false", "no")
