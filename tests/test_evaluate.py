import json
import os
import subprocess
import sys
from pathlib import Path


def test_failed_offline_extractions_retain_reproduction_context(tmp_path):
    out = tmp_path / "failure.json"
    env = dict(
        os.environ,
        HF_HUB_OFFLINE="1",
        HF_HOME=str(tmp_path / "empty-home"),
        HF_HUB_CACHE=str(tmp_path / "empty-cache"),
    )
    run = subprocess.run(
        [sys.executable, "scripts/evaluate.py", "--output", str(out)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert run.returncode != 0
    record = json.loads(out.read_text())
    assert record["errors"] == 3
    for row in record["results"]:
        assert len(row["model"]["revision"]) == 40
        assert row["settings"]["threads"] > 0
        assert row["elapsed_seconds"] >= 0
