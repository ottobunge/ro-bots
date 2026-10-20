"""Exercise Taskfile/wrapper integration without changing engine resources."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs(tmp_path):
    env = dict(os.environ)
    for key in ("WORLD_DB_ROOT_SECRET_FILE", "WORLD_DB_USER_SECRET_FILE"):
        path = tmp_path / key
        path.write_text("x")
        path.chmod(0o600)
        env[key] = str(path)
    for key in ("RATHENA_IMAGE", "AGENT_IMAGE", "WORLDFEED_IMAGE", "DASHBOARD_IMAGE"):
        env[key] = "fixture/local:config-only"
    env["WORLD_DB_USER"] = "fixture_user"
    env["WORLD_SCHEMA_DIR"] = str(tmp_path)
    return env


def test_runner_type_contract_passes_configured_dead_code_gate():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "vulture",
            "src/robots/adapters/world_compose.py",
            "--min-confidence",
            "85",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, "Compose runner type interface fails dead-code gate"


def test_taskfile_offers_read_only_world_config():
    tasks = yaml.safe_load((REPO / "Taskfile.yml").read_text())["tasks"]
    assert "world:config" in tasks, "no selected-world Compose configuration task"
    assert tasks["world:config"]["env"]["WORLD"] == '{{.world | default "debug"}}'
    assert tasks["world:config"]["cmds"] == ['bash scripts/world.sh config --world "$WORLD"']


def test_wrapper_executes_real_read_only_compose_config(inputs):
    result = subprocess.run(
        ["bash", "scripts/world.sh", "config", "--world", "test"],
        cwd=REPO,
        env=inputs,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, "read-only Compose config wrapper failed"
    data = json.loads(result.stdout)
    assert data["project"] == "ro-bots-test"
    assert data["volumes"] == {"world-data": "ro-bots-world-test"}
    assert "environment" not in data
    assert "secrets" not in data


@pytest.mark.parametrize("role", ["login", "char", "map"])
def test_compose_selects_actual_role_binary_and_explicit_runtime(role):
    services = yaml.safe_load((REPO / "docker-compose.worlds.yml").read_text())["services"]
    service = services[f"rathena-{role}"]
    assert service.get("entrypoint") == [f"/libexec/rathena/{role}-server"]
    assert service["command"] == ["--runtime-root", "/world/runtime"]


@pytest.mark.parametrize(
    ("service", "variable", "default"),
    [
        ("rathena-login", "WORLD_LOGIN_PORT", "6900"),
        ("rathena-char", "WORLD_CHAR_PORT", "6121"),
        ("rathena-map", "WORLD_MAP_PORT", "5121"),
    ],
)
def test_native_published_ports_match_configurable_listening_ports(service, variable, default):
    services = yaml.safe_load((REPO / "docker-compose.worlds.yml").read_text())["services"]
    port = "${" + variable + ":-" + default + "}"
    assert services[service]["ports"] == [f"127.0.0.1:{port}:{port}"]


@pytest.mark.parametrize("world", ["debug", "test", "prod-blue"])
def test_actual_task_template_selects_requested_world(inputs, world):
    result = subprocess.run(
        ["task", "world:config", f"world={world}"],
        cwd=REPO,
        env=inputs,
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, "Taskfile configuration dispatch failed"
    data = json.loads(result.stdout)
    assert data["project"] == f"ro-bots-{world}"
    assert data["volumes"] == {"world-data": f"ro-bots-world-{world}"}


@pytest.mark.parametrize("operation", ["up", "down", "status", "wipe"])
def test_wrapper_plan_does_not_execute_lifecycle_operations(inputs, operation):
    result = subprocess.run(
        ["bash", "scripts/world.sh", operation, "--world", "test", "--plan"],
        cwd=REPO,
        env=inputs,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, "plan wrapper failed"
    route = json.loads(result.stdout)
    assert "ro-bots-test" in route[0]
    if operation == "wipe":
        assert route[-1] == ["docker", "volume", "rm", "ro-bots-world-test"]
