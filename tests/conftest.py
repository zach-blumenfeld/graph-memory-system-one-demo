import os
import tempfile
from pathlib import Path

import pytest

# Tests never touch the real .run/ tree or the network.
_tmp = tempfile.mkdtemp(prefix="pmm-tests-")
os.environ["PMM_RECORD"] = "0"
os.environ.setdefault("PMM_TEST_RUN_DIR", _tmp)

import pmm.env as env  # noqa: E402

env.RUN_DIR = Path(_tmp)
env.SESSIONS_DIR = env.RUN_DIR / "sessions"
env.DRAFTS_DIR = env.RUN_DIR / "drafts"
env.RECORDER_LOG = env.RUN_DIR / "recorder.log"

import pmm.fixture as fx  # noqa: E402
import pmm.recorder as rc  # noqa: E402

fx.RUN_DIR = env.RUN_DIR
rc.SESSIONS_DIR = env.SESSIONS_DIR
rc.RECORDER_LOG = env.RECORDER_LOG


@pytest.fixture
def fixture():
    return fx.Fixture()


@pytest.fixture
def drafts_dir(tmp_path):
    return tmp_path / "drafts"
