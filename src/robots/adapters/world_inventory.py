"""Read-only inventory of the exact test world; not mutation authority."""

import json
import re

# Read-only CLI boundary: exact command allowlist, no shell, no mutation verbs.
import subprocess  # nosec B404
import sys
from collections.abc import Callable
from typing import Any, cast

TEST_VOLUME = "ro-bots-world-test"
_QUERIES = (
    (
        "docker",
        "container",
        "ls",
        "--all",
        "--quiet",
        "--no-trunc",
        "--filter",
        "label=com.docker.compose.project=ro-bots-test",
    ),
    (
        "docker",
        "container",
        "ls",
        "--all",
        "--quiet",
        "--no-trunc",
        "--filter",
        f"volume={TEST_VOLUME}",
    ),
    ("docker", "volume", "ls", "--quiet", "--filter", f"name=^{TEST_VOLUME}$"),
)


class InventoryError(RuntimeError):
    """Inventory cannot be reported coherently; no mutation is permitted."""


_CONTAINER_FORMAT = (
    '{"id":{{json .Id}},"state":{{json .State.Status}},'
    '"project":{{json (index .Config.Labels "com.docker.compose.project")}},'
    '"service":{{json (index .Config.Labels "com.docker.compose.service")}},'
    '"mounts":{{json .Mounts}}}'
)
_VOLUME_FORMAT = (
    '{"name":{{json .Name}},"world":{{json (index .Labels "ro-bots.world")}},'
    '"project":{{json (index .Labels "ro-bots.project")}}}'
)


def _container_ids(text: str) -> list[str]:
    tokens = text.split()
    valid = all(re.fullmatch(r"[0-9a-f]{64}", t) for t in tokens)
    if not valid or len(tokens) > 64 or len(set(tokens)) != len(tokens):
        msg = "invalid container inventory"
        raise InventoryError(msg)
    return tokens


def _object(raw: str, fields: set[str]) -> dict[str, Any]:
    if len(raw) > 262144:
        msg = "oversized inventory response"
        raise InventoryError(msg)
    try:
        data = json.loads(raw)
    except ValueError:
        msg = "malformed inventory response"
        raise InventoryError(msg) from None
    if not isinstance(data, dict) or not fields.issubset(data):
        msg = "invalid inventory shape"
        raise InventoryError(msg)
    return cast(dict[str, Any], data)


def _labels_valid(data: dict[str, Any], fields: tuple[str, ...]) -> None:
    if any(data[f] is not None and not isinstance(data[f], str) for f in fields):
        msg = "invalid inventory labels"
        raise InventoryError(msg)


def _container(run: Callable[[tuple[str, ...]], str], identity: str) -> dict[str, Any]:
    raw = run(("docker", "container", "inspect", "--format", _CONTAINER_FORMAT, identity))
    data = _object(raw, {"id", "state", "project", "service", "mounts"})
    _labels_valid(data, ("project", "service"))
    states = ("created", "running", "paused", "restarting", "removing", "exited", "dead")
    if data["id"] != identity or data["state"] not in states:
        msg = "inconsistent container inventory"
        raise InventoryError(msg)
    mounts = data["mounts"]
    if not isinstance(mounts, list) or any(not isinstance(m, dict) for m in mounts):
        msg = "invalid inventory mounts"
        raise InventoryError(msg)
    selected = [m for m in mounts if m.get("Type") == "volume" and m.get("Name") == TEST_VOLUME]
    return {
        "id": identity,
        "state": data["state"],
        "test_project": data["project"] == "ro-bots-test",
        "database_service": data["service"] == "mariadb",
        "test_volume_mounted": bool(selected),
        "database_mount": any(m.get("Destination") == "/var/lib/mysql" for m in selected),
    }


def _volume_labels(run: Callable[[tuple[str, ...]], str]) -> bool:
    raw = run(("docker", "volume", "inspect", "--format", _VOLUME_FORMAT, TEST_VOLUME))
    data = _object(raw, {"name", "world", "project"})
    _labels_valid(data, ("world", "project"))
    if data["name"] != TEST_VOLUME:
        msg = "inconsistent volume inventory"
        raise InventoryError(msg)
    return bool(data["world"] == "test" and data["project"] == "ro-bots-test")


def _check_membership(owned: list[str], users: list[str], containers: list[dict[str, Any]]) -> None:
    mounted = {c["id"] for c in containers if c["test_volume_mounted"]}
    projects = {c["id"] for c in containers if c["test_project"]}
    if mounted != set(users) or not set(owned).issubset(projects):
        msg = "inconsistent inventory filters"
        raise InventoryError(msg)


def _snapshot(run: Callable[[tuple[str, ...]], str]) -> dict[str, Any]:
    owned = _container_ids(run(_QUERIES[0]))
    users = _container_ids(run(_QUERIES[1]))
    volumes = run(_QUERIES[2]).split()
    if volumes not in ([], [TEST_VOLUME]) or (users and not volumes):
        msg = "invalid volume inventory"
        raise InventoryError(msg)
    containers = [_container(run, identity) for identity in sorted(set(owned + users))]
    _check_membership(owned, users, containers)
    result: dict[str, Any] = {
        "world": "test",
        "volume_exists": TEST_VOLUME in volumes,
        "containers": containers,
        "volume_users": sorted(users),
        "inventory_stable": True,
        "mutation_authorized": False,
    }
    if result["volume_exists"]:
        result["volume_labels_match"] = _volume_labels(run)
        result["foreign_volume_users"] = [
            c["id"] for c in containers if c["id"] in users and not c["test_project"]
        ]
    return result


def inventory_test_world(run: Callable[[tuple[str, ...]], str]) -> dict[str, Any]:
    """Collect twice; this is not an exclusive lock or mutation authorization."""
    first, second = _snapshot(run), _snapshot(run)
    if first != second:
        msg = "inventory changed during observation"
        raise InventoryError(msg)
    return second


def run_engine(command: tuple[str, ...]) -> str:
    """Run only an exact allowlisted inventory command."""
    if not _allowed_command(command):
        msg = "inventory command is not allowed"
        raise InventoryError(msg)
    try:
        # _allowed_command checks the complete tuple and full hexadecimal ID.
        result = subprocess.run(
            command,  # nosec B603
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=10,
        )
    except OSError, subprocess.TimeoutExpired, UnicodeError:
        msg = "engine inventory read failed"
        raise InventoryError(msg) from None
    if result.returncode != 0:
        msg = "engine inventory read failed"
        raise InventoryError(msg)
    return result.stdout


def _allowed_command(command: tuple[str, ...]) -> bool:
    if command in _QUERIES:
        return True
    if len(command) != 6:
        return False
    if command == ("docker", "volume", "inspect", "--format", _VOLUME_FORMAT, TEST_VOLUME):
        return True
    return bool(re.fullmatch(r"[0-9a-f]{64}", command[-1])) and command == (
        "docker",
        "container",
        "inspect",
        "--format",
        _CONTAINER_FORMAT,
        command[-1],
    )


def main(run: Callable[[tuple[str, ...]], str] | None = None) -> int:
    """Print sanitized inventory; never start or authorize a world."""
    try:
        result = inventory_test_world(run or run_engine)
    except InventoryError:
        sys.stderr.write("test-world inventory unavailable; no mutation authorized\n")
        return 2
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
