"""Persisted private per-world inputs; configuration only, no engine mutation."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from robots.adapters import world_compose, world_prepare_cli
from tests.test_world_task_integration import REPO


def metadata(tmp_path: Path, world: str = "test") -> tuple[Path, dict[str, str]]:
    selection = world_compose.WorldSelection(world)
    values = world_prepare_cli.compose_inputs(
        tmp_path, selection, world_prepare_cli.generated_settings()
    )
    path = tmp_path / "compose-inputs.json"
    path.write_text(json.dumps(values))
    path.chmod(0o600)
    return path, values


def test_task_config_reads_prepared_stage_inputs(tmp_path, capsys):
    stage = tmp_path / "stage"
    assert world_prepare_cli.main(["--world", "test", "--destination", str(stage)]) == 0
    capsys.readouterr()
    env = dict(os.environ)
    for key in ("RATHENA_IMAGE", "AGENT_IMAGE", "WORLDFEED_IMAGE", "DASHBOARD_IMAGE"):
        env[key] = "fixture/local:config-only"
    for key in world_prepare_cli.compose_inputs(
        stage, world_compose.WorldSelection("test"), world_prepare_cli.generated_settings()
    ):
        env.pop(key, None)
    result = subprocess.run(
        ["task", "world:config", "world=test", f"stage={stage}"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, "saved-stage Task config failed"
    data = json.loads(result.stdout)
    assert data["project"] == "ro-bots-test"
    assert data["volumes"] == {"world-data": "ro-bots-world-test"}


def test_saved_inputs_load_without_password_values(tmp_path):
    path, expected = metadata(tmp_path)
    assert hasattr(world_compose, "load_inputs"), "saved world input loader missing"
    assert world_compose.load_inputs(str(path), world_compose.WorldSelection("test")) == expected


@pytest.mark.parametrize("key", ["WORLD_KIND", "WORLD_PROJECT", "WORLD_VOLUME"])
def test_saved_inputs_refuse_cross_world_selection(tmp_path, key):
    path, values = metadata(tmp_path)
    values[key] = "different-world"
    path.write_text(json.dumps(values))
    assert hasattr(world_compose, "load_inputs"), "saved world input loader missing"
    with pytest.raises(ValueError, match="selected world"):
        world_compose.load_inputs(str(path), world_compose.WorldSelection("test"))


def test_saved_input_file_must_remain_private(tmp_path):
    path, _ = metadata(tmp_path)
    path.chmod(0o644)
    assert hasattr(world_compose, "load_inputs"), "saved world input loader missing"
    with pytest.raises(ValueError, match="private"):
        world_compose.load_inputs(str(path), world_compose.WorldSelection("test"))
