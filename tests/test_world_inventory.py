"""Fixed-scope engine reads are inventory, never world mutation authority."""

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from robots.adapters import world_inventory
from robots.adapters.world_inventory import InventoryError, inventory_test_world


def test_absent_world_reads_only_and_returns_no_authorization() -> None:
    calls: list[tuple[str, ...]] = []

    def run(command: tuple[str, ...]) -> str:
        calls.append(command)
        assert command[:4] in {
            ("docker", "container", "ls", "--all"),
            ("docker", "volume", "ls", "--quiet"),
        }
        return ""

    result = inventory_test_world(run)
    assert result == {
        "world": "test",
        "volume_exists": False,
        "containers": [],
        "volume_users": [],
        "inventory_stable": True,
        "mutation_authorized": False,
    }
    assert len(calls) == 6


def test_inventory_import_has_no_engine_effects() -> None:
    # Import above must succeed without an engine call; all execution is explicit.
    assert callable(inventory_test_world)


def test_present_world_discovers_foreign_volume_users_without_authorizing() -> None:
    own, foreign = "a" * 64, "b" * 64
    calls: list[tuple[str, ...]] = []

    def run(command: tuple[str, ...]) -> str:
        calls.append(command)
        if command[1:3] == ("container", "ls"):
            return own if command[-1].startswith("label=") else f"{own}\n{foreign}"
        if command[1:3] == ("volume", "ls"):
            return "ro-bots-world-test"
        if command[1:3] == ("volume", "inspect"):
            return json.dumps(
                {"name": "ro-bots-world-test", "world": "test", "project": "ro-bots-test"}
            )
        assert command[1:3] == ("container", "inspect")
        return json.dumps(
            {
                "id": command[-1],
                "state": "exited",
                "project": "ro-bots-test" if command[-1] == own else "foreign-sensitive-label",
                "service": "mariadb" if command[-1] == own else "other",
                "mounts": [
                    {
                        "Type": "volume",
                        "Name": "ro-bots-world-test",
                        "Destination": "/var/lib/mysql",
                    }
                ],
            }
        )

    result = inventory_test_world(run)
    assert result["volume_exists"] is True
    assert result["volume_labels_match"] is True
    assert result["volume_users"] == [own, foreign]
    assert result["foreign_volume_users"] == [foreign]
    assert result["mutation_authorized"] is False
    assert "foreign-sensitive-label" not in json.dumps(result)
    assert result["containers"][0] == {
        "id": own,
        "state": "exited",
        "test_project": True,
        "database_service": True,
        "test_volume_mounted": True,
        "database_mount": True,
    }
    assert all(
        c[1:3]
        in {("container", "ls"), ("volume", "ls"), ("container", "inspect"), ("volume", "inspect")}
        for c in calls
    )


@pytest.mark.parametrize(
    "invalid",
    [
        "abc",
        "A" * 64,
        "--all",
        "a" * 64 + "\n" + "a" * 64,
        "\n".join(f"{i:064x}" for i in range(65)),
    ],
)
def test_bad_or_excessive_container_ids_rejected_before_inspection(invalid: str) -> None:
    def run(command: tuple[str, ...]) -> str:
        assert command[2] == "ls", "unsafe identifier reached inspect"
        return invalid if command[1] == "container" else ""

    with pytest.raises(InventoryError, match="inventory"):
        inventory_test_world(run)


def test_foreign_volume_name_rejected_before_inspection() -> None:
    def run(command: tuple[str, ...]) -> str:
        assert command[2] == "ls"
        return "ro-bots-world-prod-default" if command[1] == "volume" else ""

    with pytest.raises(InventoryError, match="inventory"):
        inventory_test_world(run)


def _with_container(raw: str, volume_raw: str | None = None) -> Callable[[tuple[str, ...]], str]:
    identity = "a" * 64

    def run(command: tuple[str, ...]) -> str:
        if command[1:3] == ("container", "ls"):
            return identity
        if command[1:3] == ("volume", "ls"):
            return "ro-bots-world-test"
        if command[1:3] == ("volume", "inspect"):
            return volume_raw or json.dumps(
                {"name": "ro-bots-world-test", "world": "test", "project": "ro-bots-test"}
            )
        return raw

    return run


def _container_data() -> dict[str, Any]:
    return {
        "id": "a" * 64,
        "state": "exited",
        "project": "ro-bots-test",
        "service": "mariadb",
        "mounts": [
            {"Type": "volume", "Name": "ro-bots-world-test", "Destination": "/var/lib/mysql"}
        ],
    }


@pytest.mark.parametrize(
    "bad",
    ["not-json-sensitive-content", "[]", "{}", "x" * 262145],
    ids=["bad-json", "not-object", "missing-fields", "oversized"],
)
def test_malformed_inspection_is_sanitized(bad: str) -> None:
    with pytest.raises(InventoryError, match="inventory") as error:
        inventory_test_world(_with_container(bad))
    assert "sensitive-content" not in str(error.value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "b" * 64),
        ("state", "private-content"),
        ("mounts", None),
        ("mounts", ["invalid"]),
        ("project", {}),
    ],
)
def test_inspection_identity_and_shape_must_match(field: str, value: object) -> None:
    data = _container_data()
    data[field] = value
    with pytest.raises(InventoryError, match="inventory"):
        inventory_test_world(_with_container(json.dumps(data)))


def test_exact_volume_inspection_cannot_substitute_production() -> None:
    other = json.dumps(
        {"name": "ro-bots-world-prod-default", "world": "test", "project": "ro-bots-test"}
    )
    with pytest.raises(InventoryError, match="inventory"):
        inventory_test_world(_with_container(json.dumps(_container_data()), other))


def test_membership_filter_and_inspected_mount_must_agree() -> None:
    data = _container_data()
    data["mounts"] = []
    with pytest.raises(InventoryError, match="inventory"):
        inventory_test_world(_with_container(json.dumps(data)))


def test_owned_filter_and_inspected_project_must_agree() -> None:
    data = _container_data()
    data["project"] = "foreign"
    with pytest.raises(InventoryError, match="inventory"):
        inventory_test_world(_with_container(json.dumps(data)))


def test_snapshot_drift_never_returns_success() -> None:
    reads = 0

    def run(command: tuple[str, ...]) -> str:
        nonlocal reads
        if command[1:3] == ("volume", "ls"):
            reads += 1
            return "ro-bots-world-test" if reads == 2 else ""
        if command[1:3] == ("volume", "inspect"):
            return json.dumps(
                {"name": "ro-bots-world-test", "world": "test", "project": "ro-bots-test"}
            )
        return ""

    with pytest.raises(InventoryError, match="changed"):
        inventory_test_world(run)


def test_cli_returns_real_inventory_not_authorization(capsys: pytest.CaptureFixture[str]) -> None:
    assert world_inventory.main(lambda _: "") == 0
    assert json.loads(capsys.readouterr().out)["mutation_authorized"] is False


def test_cli_sanitizes_failed_observation(capsys: pytest.CaptureFixture[str]) -> None:
    def failing(_: tuple[str, ...]) -> str:
        msg = "private fixture details"
        raise InventoryError(msg)

    assert world_inventory.main(failing) == 2
    captured = capsys.readouterr()
    assert "private fixture" not in captured.err + captured.out
    assert "unavailable" in captured.err


def test_engine_runs_only_allowlisted_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(command: tuple[str, ...], **options: Any) -> SimpleNamespace:
        assert command == world_inventory._QUERIES[0]
        assert options == {
            "capture_output": True,
            "text": True,
            "check": False,
            "shell": False,
            "timeout": 10,
        }
        return SimpleNamespace(returncode=0, stdout="captured", stderr="")

    monkeypatch.setattr(subprocess, "run", fake)
    assert world_inventory.run_engine(world_inventory._QUERIES[0]) == "captured"


def test_engine_cannot_execute_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        pytest.fail("mutation reached engine")

    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(InventoryError):
        world_inventory.run_engine(("docker", "volume", "rm", "ro-bots-world-test"))


@pytest.mark.parametrize("mode", ["exit", "missing", "timeout"])
def test_engine_failures_are_sanitized(mode: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(command: tuple[str, ...], **_kwargs: Any) -> SimpleNamespace:
        if mode == "missing":
            msg = "private fixture details"
            raise FileNotFoundError(msg)
        if mode == "timeout":
            raise subprocess.TimeoutExpired(command, 10, output="private fixture details")
        return SimpleNamespace(returncode=1, stdout="", stderr="private fixture details")

    monkeypatch.setattr(subprocess, "run", failing)
    with pytest.raises(InventoryError) as error:
        world_inventory.run_engine(world_inventory._QUERIES[0])
    assert "private fixture" not in str(error.value)


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_real_engine_decoding_failure_is_sanitized_through_cli(
    stream: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    real_run = subprocess.run
    calls: list[tuple[str, ...]] = []
    decoding_failures: list[str] = []

    def local_fixture(command: tuple[str, ...], **options: Any) -> subprocess.CompletedProcess[str]:
        assert command == world_inventory._QUERIES[0]
        assert options == {
            "capture_output": True,
            "text": True,
            "check": False,
            "shell": False,
            "timeout": 10,
        }
        calls.append(command)
        # Substitute only this exact read with a local child, never an engine.
        fixture = (
            sys.executable,
            "-c",
            f"import sys; sys.{stream}.buffer.write(b'private-fixture\\xff')",
        )
        try:
            return real_run(fixture, **options)
        except UnicodeDecodeError:
            decoding_failures.append(stream)
            raise

    monkeypatch.setattr(subprocess, "run", local_fixture)
    assert world_inventory.main() == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "test-world inventory unavailable; no mutation authorized\n"
    assert "private-fixture" not in captured.out + captured.err
    assert '"mutation_authorized": true' not in captured.out + captured.err
    assert calls == [world_inventory._QUERIES[0]]
    assert decoding_failures == [stream]

    with pytest.raises(InventoryError, match=r"^engine inventory read failed$") as error:
        world_inventory.run_engine(world_inventory._QUERIES[0])
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__ is True
    assert calls == [world_inventory._QUERIES[0]] * 2
    assert decoding_failures == [stream] * 2


def test_inventory_task_is_fixed_scope_and_read_only() -> None:
    path = Path(__file__).resolve().parents[1] / "Taskfile.yml"
    task = yaml.safe_load(path.read_text())["tasks"].get("world:inventory")
    assert task is not None, "fixed-scope inventory task missing"
    assert "Read-only" in task["desc"]
    assert task["cmds"] == ["uv run python -m robots.adapters.world_inventory"]


def test_volume_users_with_absent_volume_are_inconsistent() -> None:
    original = _with_container(json.dumps(_container_data()))

    def run(command: tuple[str, ...]) -> str:
        return "" if command[1:3] == ("volume", "ls") else original(command)

    with pytest.raises(InventoryError, match="inventory"):
        inventory_test_world(run)
