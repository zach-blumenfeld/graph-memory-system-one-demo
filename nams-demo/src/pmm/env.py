"""Paths and environment loading. The only secret source is `.env` at the repo root."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(os.environ.get("PMM_ROOT") or Path(__file__).resolve().parents[2])
DATA = ROOT / "data" / "notion"
ONTOLOGY_FILE = ROOT / "ontology" / "pmm.json"
RUNS_FILE = ROOT / "prompts" / "runs.yaml"
CHECKPOINTS = ROOT / "checkpoints"
REPORTS = ROOT / "reports"
RUN_DIR = ROOT / ".run"
SESSIONS_DIR = RUN_DIR / "sessions"
DRAFTS_DIR = RUN_DIR / "drafts"
RECORDER_LOG = RUN_DIR / "recorder.log"
SKILL_DIR = ROOT / ".claude" / "skills" / "launch-email-blast"

REQUIRED_KEYS = (
    "MEMORY_API_KEY",
    "MEMORY_ENDPOINT",
    "MEMORY_WORKSPACE_ID",
    "NEO4J_URI",
    "NEO4J_USERNAME",
    "NEO4J_PASSWORD",
    "TYPESAFE_API_KEY",
)


def load_dotenv(path: Path | None = None, *, override: bool = False) -> dict[str, str]:
    """Minimal .env loader (KEY=VALUE, # comments, optional quotes). Never logs values."""
    path = path or ROOT / ".env"
    loaded: dict[str, str] = {}
    if not path.exists():
        return loaded
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if override or key not in os.environ:
            os.environ[key] = value
        loaded[key] = value
    return loaded


class MissingSecret(RuntimeError):
    pass


def require(*keys: str) -> dict[str, str]:
    """Return the requested env values, raising a clear error naming (not printing) what is missing."""
    load_dotenv()
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise MissingSecret(f"missing required environment variables: {', '.join(missing)} (set them in .env)")
    return {k: os.environ[k] for k in keys}


def nams_base_url() -> str:
    """NAMS host without the /v1 suffix (MEMORY_ENDPOINT includes /v1)."""
    load_dotenv()
    endpoint = os.environ.get("MEMORY_ENDPOINT", "https://memory.neo4jlabs.com/v1").rstrip("/")
    return endpoint[:-3] if endpoint.endswith("/v1") else endpoint


def recording_enabled() -> bool:
    return os.environ.get("PMM_RECORD", "1") not in ("0", "false", "no", "")


def ensure_run_dirs() -> None:
    for d in (RUN_DIR, SESSIONS_DIR, DRAFTS_DIR, RUN_DIR / "notion", RUN_DIR / "runs", RUN_DIR / "schedule"):
        d.mkdir(parents=True, exist_ok=True)
