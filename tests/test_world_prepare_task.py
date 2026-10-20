"""Actual host preparation Task; no container or SQL execution."""

import json
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_actual_task_prepares_new_private_world_stage(tmp_path):
    stage = tmp_path / "stage"
    result = subprocess.run(
        ["task", "world:prepare", "world=test", f"stage={stage}"],
        cwd=REPO,
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, "host preparation Task failed"
    report = json.loads(result.stdout)
    assert report["world"] == "test"
    assert report["prepared"] is True
    assert report["provisioning"] is False
    assert report["host_bind_mount_ready"] is False
    inputs = stage / "compose-inputs.json"
    assert inputs.stat().st_mode & 0o777 == 0o600
    data = json.loads(inputs.read_text())
    assert data["WORLD_PROJECT"] == "ro-bots-test"
    assert data["WORLD_VOLUME"] == "ro-bots-world-test"
    assert (stage / "runtime/conf/map_athena.conf").is_file()
    assert (stage / "sql/50-interserver.sql").is_file()
