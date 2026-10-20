"""Offline safety contracts, not live world/volume or gameplay acceptance."""

import importlib.util
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import Mock

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def set_path(mapping: Any, path: tuple[str | int, ...], value: Any) -> None:
    for part in path[:-1]:
        mapping = mapping[part]
    mapping[path[-1]] = value


def load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    run_id = "a" * 32
    config = {
        "allow_isolated_plan": True,
        "world": "test",
        "project": "ro-bots-test",
        "volume": "ro-bots-world-test",
        "route": {"kind": "compose-exec", "service": "mariadb", "database": "ragnarok"},
        "run_id": run_id,
    }
    observed = {
        "world": "test",
        "project": "ro-bots-test",
        "volume": "ro-bots-world-test",
        "volume_labels": {"ro-bots.world": "test", "ro-bots.project": "ro-bots-test"},
        "database_identity": {"world": "test", "run_id": run_id},
        "db_container": {
            "id": "b" * 64,
            "service": "mariadb",
            "project": "ro-bots-test",
            "world": "test",
            "mounts": [
                {"type": "volume", "source": "ro-bots-world-test", "target": "/var/lib/mysql"}
            ],
            "published_ports": [],
            "network": "ro-bots-test-world-local",
        },
        "game_services": {
            "rathena-login": "stopped",
            "rathena-char": "stopped",
            "rathena-map": "stopped",
        },
        "volume_users": [],
    }
    manifest = {
        "world": "test",
        "project": "ro-bots-test",
        "volume": "ro-bots-world-test",
        "run_id": run_id,
        "accounts": [
            {
                "account_id": 2100000,
                "account": "e2e_aaaaaaaaaaaa_0",
                "char_id": 160000,
                "char_name": "Fixture0",
            }
        ],
    }
    database = {
        "accounts": [{"account_id": 2100000, "account": "e2e_aaaaaaaaaaaa_0", "online": False}],
        "characters": [
            {"account_id": 2100000, "char_id": 160000, "char_name": "Fixture0", "online": False}
        ],
    }
    return config, observed, manifest, database


def test_cleanup_plan_is_exact_and_retains_unrelated_accounts():
    script = load_script("seed_test_agents")
    config, observed, manifest, database = fixture()
    database["accounts"].append({"account_id": 2100001, "account": "human", "online": False})
    database["characters"].append(
        {"account_id": 2100001, "char_id": 160001, "char_name": "Human", "online": False}
    )
    assert hasattr(script, "cleanup_plan"), "missing exact manifest-owned cleanup planner"
    plan = script.cleanup_plan(config, observed, manifest, database)
    assert plan == (
        (
            (
                "DELETE FROM `char` WHERE `account_id` = %s AND `char_id` = %s "
                "AND `name` = %s AND `online` = 0"
            ),
            (2100000, 160000, "Fixture0"),
        ),
        (
            "DELETE FROM `login` WHERE `account_id` = %s AND `userid` = %s",
            (2100000, "e2e_aaaaaaaaaaaa_0"),
        ),
    )
    assert 2100001 not in [value for _, params in plan for value in params]
    assert all(">=" not in sql and "LIKE" not in sql for sql, _ in plan)


@pytest.mark.parametrize(
    ("target", "path", "value"),
    [
        (0, ("allow_isolated_plan",), False),
        (0, ("allow_isolated_plan",), 1),
        *[(0, ("world",), world) for world in [None, "unknown", "world", "debug", "prod-default"]],
        (0, ("project",), "ro-bots-debug"),
        (0, ("volume",), "ro-bots-world-debug"),
        (0, ("route", "kind"), "native-socket"),
        (0, ("route", "kind"), "tcp"),
        (0, ("route", "socket"), "run/mysql.sock"),
        (0, ("route", "service"), "shared-db"),
        (0, ("run_id",), "../debug"),
        (1, ("db_container", "published_ports"), [3306]),
        (1, ("db_container", "network"), "host"),
        (1, ("db_container", "project"), "ro-bots-debug"),
        (1, ("db_container", "world"), "debug"),
        (1, ("db_container", "id"), ""),
        (1, ("db_container", "mounts", 0, "source"), "ro-bots-world-debug"),
        (1, ("db_container", "mounts", 0, "type"), "bind"),
        (1, ("volume_labels", "ro-bots.world"), "debug"),
        (1, ("database_identity", "world"), "debug"),
        (1, ("database_identity", "run_id"), "c" * 32),
        (1, ("game_services", "rathena-login"), "running"),
        (1, ("game_services", "rathena-map"), "unknown"),
        (2, ("world",), "debug"),
        (2, ("run_id",), "c" * 32),
        (2, ("accounts", 0, "account"), "e2e_reused"),
        (2, ("accounts", 0, "account_id"), True),
        (2, ("accounts", 0, "char_name"), "x'; DELETE FROM login; --"),
        (3, ("accounts", 0, "account"), "human"),
        (3, ("accounts", 0, "online"), True),
        (3, ("characters", 0, "online"), True),
        (3, ("characters", 0, "char_name"), "Human"),
        (3, ("characters", 0, "account_id"), 2100001),
        (3, ("accounts",), []),
        (3, ("characters",), []),
    ],
)
def test_invalid_ownership_or_routing_is_rejected_before_any_action(
    target, path, value, monkeypatch
):
    script = load_script("seed_test_agents")
    values = fixture()
    set_path(values[target], path, value)
    process = Mock(side_effect=AssertionError("planner must not start processes"))
    write = Mock(side_effect=AssertionError("planner must not write manifests"))
    monkeypatch.setattr(script.subprocess, "run", process)
    monkeypatch.setattr(Path, "write_text", write)
    with pytest.raises(RuntimeError, match="blocked"):
        script.cleanup_plan(*values[:2], values[2], values[3])
    process.assert_not_called()
    write.assert_not_called()


@pytest.mark.parametrize(
    "kind", ["extra-character", "duplicate-account", "duplicate-character", "name-collision"]
)
def test_ambiguous_account_ownership_refuses_cleanup(kind):
    script = load_script("seed_test_agents")
    config, observed, manifest, database = fixture()
    if kind == "extra-character":
        database["characters"].append(
            {"account_id": 2100000, "char_id": 160001, "char_name": "Human", "online": False}
        )
    elif kind == "duplicate-account":
        manifest["accounts"].append(deepcopy(manifest["accounts"][0]))
    elif kind == "duplicate-character":
        database["characters"].append(deepcopy(database["characters"][0]))
    else:
        database["characters"].append(
            {"account_id": 2100001, "char_id": 160001, "char_name": "Fixture0", "online": False}
        )
    with pytest.raises(RuntimeError, match="blocked"):
        script.cleanup_plan(config, observed, manifest, database)


def test_reset_plan_only_removes_exact_owned_stopped_container_and_named_test_volume(monkeypatch):
    script = load_script("e2e_runner")
    config, observed, _, _ = fixture()
    observed["db_container"]["state"] = "stopped"
    observed["volume_users"] = [
        {"id": "b" * 64, "project": "ro-bots-test", "service": "mariadb", "state": "stopped"}
    ]
    process = Mock(side_effect=AssertionError("reset planning must not execute"))
    monkeypatch.setattr(script.subprocess, "run", process)
    assert hasattr(script, "reset_plan"), "missing owned exact test-volume reset planner"
    assert script.reset_plan(config, observed) == (
        ("docker", "container", "rm", "b" * 64),
        ("docker", "volume", "rm", "ro-bots-world-test"),
        (
            "docker",
            "volume",
            "create",
            "--label",
            "ro-bots.world=test",
            "--label",
            "ro-bots.project=ro-bots-test",
            "ro-bots-world-test",
        ),
    )
    process.assert_not_called()


@pytest.mark.parametrize(
    "kind",
    [
        "running-db",
        "running-volume-user",
        "debug-user",
        "unknown-user",
        "unknown-label",
        "wrong-volume",
        "wrong-world",
    ],
)
def test_reset_plan_refuses_nonexclusive_or_unknown_world(kind, monkeypatch):
    script = load_script("e2e_runner")
    config, observed, _, _ = fixture()
    observed["db_container"]["state"] = "stopped"
    observed["volume_users"] = [
        {"id": "b" * 64, "project": "ro-bots-test", "service": "mariadb", "state": "stopped"}
    ]
    if kind == "running-db":
        observed["db_container"]["state"] = "running"
    elif kind == "running-volume-user":
        observed["volume_users"][0]["state"] = "running"
    elif kind == "debug-user":
        observed["volume_users"][0]["project"] = "ro-bots-debug"
    elif kind == "unknown-user":
        observed["volume_users"].append({"id": "c" * 64, "project": "other", "state": "stopped"})
    elif kind == "unknown-label":
        observed["volume_labels"] = {}
    elif kind == "wrong-volume":
        config["volume"] = "ro-bots-world-debug"
    else:
        config["world"] = "prod-default"
    process = Mock(side_effect=AssertionError("invalid reset must not execute"))
    monkeypatch.setattr(script.subprocess, "run", process)
    assert hasattr(script, "reset_plan"), "missing reset validator"
    with pytest.raises(RuntimeError, match="blocked"):
        script.reset_plan(config, observed)
    process.assert_not_called()


@pytest.mark.parametrize("world", ["test", "debug", "prod-default", "unknown", "world"])
@pytest.mark.parametrize("command", ["wipe", "up", "down"])
def test_world_shell_requires_explicit_selection_despite_environment_optins(
    world, command, tmp_path
):
    marker = tmp_path / "docker-called"
    fake = tmp_path / "docker"
    fake.write_text('#!/bin/sh\nprintf called >> "$DOCKER_SPY"\nexit 0\n')
    fake.chmod(0o700)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "DOCKER_SPY": str(marker),
        "WORLD_KIND": world,
        "FORCE": "1",
        "ALLOW_ISOLATED": "1",
    }
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "world.sh"), command],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "explicit --world" in result.stderr.lower()
    assert not marker.exists(), "implicit world selection reached Docker"


def test_compose_requires_secret_files_and_never_publishes_the_database():
    text = (ROOT / "docker-compose.worlds.yml").read_text()
    assert "MARIADB_ROOT_PASSWORD: ragnarok" not in text
    assert "MARIADB_PASSWORD: ragnarok" not in text
    assert "MARIADB_ROOT_PASSWORD_FILE: /run/secrets/world-db-root" in text
    assert "MARIADB_PASSWORD_FILE: /run/secrets/world-db-user" in text
    assert "${WORLD_DB_ROOT_SECRET_FILE:?" in text
    assert "${WORLD_DB_USER_SECRET_FILE:?" in text
    assert "127.0.0.1:3306:3306" not in text


def test_database_route_is_pinned_to_verified_container_not_host_socket_or_tcp(monkeypatch):
    script = load_script("seed_test_agents")
    config, observed, _, _ = fixture()
    observed["db_container"]["state"] = "running"
    process = Mock(side_effect=AssertionError("routing plan is inert"))
    monkeypatch.setattr(script.subprocess, "run", process)
    assert hasattr(script, "database_route"), "missing immutable container route"
    assert script.database_route(config, observed) == ("container-exec", "b" * 64, "ragnarok")
    process.assert_not_called()


@pytest.mark.parametrize("state", [None, "stopped", "unknown"])
def test_database_route_refuses_unavailable_container_without_fallback(state, monkeypatch):
    script = load_script("seed_test_agents")
    config, observed, _, _ = fixture()
    observed["db_container"]["state"] = state
    process = Mock(side_effect=AssertionError("no fallback command allowed"))
    monkeypatch.setattr(script.subprocess, "run", process)
    assert hasattr(script, "database_route"), "missing container route validator"
    with pytest.raises(RuntimeError, match="blocked"):
        script.database_route(config, observed)
    process.assert_not_called()


@pytest.mark.parametrize("socket", [None, "run/mysql.sock", "/tmp/mysql.sock", "127.0.0.1:3306"])
def test_direct_sql_is_blocked_for_every_unverified_routing(socket, monkeypatch):
    script = load_script("seed_test_agents")
    process = Mock(side_effect=AssertionError("arbitrary SQL must never execute"))
    monkeypatch.setattr(script.subprocess, "run", process)
    with pytest.raises(RuntimeError, match="blocked"):
        script.apply_sql("SELECT 1;", socket)
    process.assert_not_called()


@pytest.mark.parametrize("name", ["e2e_runner", "seed_test_agents"])
def test_explicit_cli_config_or_environment_cannot_forge_execution_authority(
    name, monkeypatch, capsys
):
    script = load_script(name)
    monkeypatch.setenv("ALLOW_ISOLATED", "1")
    monkeypatch.setenv("WORLD_KIND", "test")
    monkeypatch.setenv("FORCE", "1")
    monkeypatch.setattr("sys.argv", [name, "--verified-config", "/does/not/exist"])
    process = Mock(side_effect=AssertionError("no configuration-only execution bypass"))
    read = Mock(side_effect=AssertionError("entrypoint must not read a supplied config"))
    monkeypatch.setattr(script.subprocess, "run", process)
    monkeypatch.setattr(Path, "read_text", read)
    assert script.main() == 2
    assert "blocked" in capsys.readouterr().err
    process.assert_not_called()
    read.assert_not_called()


def test_e2e_shell_entrypoint_blocks_without_external_interpreter(tmp_path):
    marker = tmp_path / "python-called"
    fake = tmp_path / "python3"
    fake.write_text('#!/bin/sh\nprintf called >> "$PYTHON_SPY"\nexit 0\n')
    fake.chmod(0o700)
    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "PYTHON_SPY": str(marker),
        "ALLOW_ISOLATED": "1",
        "KEEP": "1",
    }
    text = (ROOT / "scripts" / "e2e.sh").read_text()
    assert "exec" not in text, "unverified E2E wrapper still launches an interpreter"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "e2e.sh")],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "blocked" in result.stderr.lower()
    assert not marker.exists()


def test_compose_uses_ordinary_project_scoped_bridge_without_host_network():
    config = yaml.safe_load((ROOT / "docker-compose.worlds.yml").read_text())
    assert config["name"] == "${WORLD_PROJECT:?derived world project required}"
    assert "networks" not in config
    assert all("network_mode" not in service for service in config["services"].values())
