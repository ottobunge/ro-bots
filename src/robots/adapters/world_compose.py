"""Ordinary Compose project/volume selection; no runtime provisioning manager."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess  # nosec B404
import sys
from abc import abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from robots.adapters.rathena_runtime_io import decode_input, literal_parts, read_path


class Runner(Protocol):
    """Replace only execution for routing tests; production uses subprocess.run."""

    @abstractmethod
    def __call__(
        self,
        args: list[str],
        *,
        env: dict[str, str],
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        del args, env, capture_output, text, timeout, check
        raise NotImplementedError


def dispatch(
    selection: WorldSelection,
    operation: str,
    inputs: Mapping[str, str],
    *,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    """Execute a narrow route; never relay raw Compose output or provider stderr."""
    route = commands(selection, operation)
    env = environment(selection, inputs)
    results = [_execute(command, env, operation, runner) for command in route]
    result = results[-1]
    if operation == "config":
        return safe_config(json.loads(result.stdout))
    if operation == "status":
        return {"project": selection.project, "containers": _status_records(result.stdout)}
    return {"project": selection.project, "operation": operation, "returncode": 0}


def _execute(
    command: list[str], env: dict[str, str], operation: str, runner: Runner
) -> subprocess.CompletedProcess[str]:
    result = runner(command, env=env, capture_output=True, text=True, timeout=60, check=False)
    if result.returncode:
        message = f"world {operation} failed (exit {result.returncode}); raw output withheld"
        raise RuntimeError(message)
    return result


def _status_records(output: str) -> list[dict[str, Any]]:
    records = [json.loads(line) for line in output.splitlines() if line.strip()]
    if len(records) == 1 and isinstance(records[0], list):
        records = records[0]
    return [{key: record.get(key) for key in ("Name", "Service", "State")} for record in records]


def safe_config(config: dict[str, Any]) -> dict[str, Any]:
    """The config view contains only project, volume/network names and volume mounts."""
    return {
        "project": config["name"],
        "volumes": {key: value["name"] for key, value in config.get("volumes", {}).items()},
        "networks": {key: value["name"] for key, value in config.get("networks", {}).items()},
        "mounts": {
            service: [
                {key: mount[key] for key in ("type", "source", "target")}
                for mount in value.get("volumes", [])
                if mount["type"] == "volume"
            ]
            for service, value in config["services"].items()
        },
    }


REQUIRED = (
    "RATHENA_IMAGE",
    "AGENT_IMAGE",
    "WORLDFEED_IMAGE",
    "DASHBOARD_IMAGE",
    "WORLD_DB_USER",
    "WORLD_SCHEMA_DIR",
    "WORLD_DB_ROOT_SECRET_FILE",
    "WORLD_DB_USER_SECRET_FILE",
)
PORTS = {
    "WORLD_LOGIN_PORT": "6900",
    "WORLD_CHAR_PORT": "6121",
    "WORLD_MAP_PORT": "5121",
    "WORLD_FEED_PORT": "8400",
    "WORLD_DASHBOARD_PORT": "8401",
}


def environment(selection: WorldSelection, inputs: Mapping[str, str]) -> dict[str, str]:
    """Validate explicit inputs without reading or returning secret file contents."""
    env = {key: value for key, value in inputs.items() if not key.startswith("COMPOSE_")}
    _required_inputs(env)
    _ports(env)
    _secret_files(env)
    schema = Path(env["WORLD_SCHEMA_DIR"])
    if not schema.is_absolute() or not schema.is_dir():
        message = "WORLD_SCHEMA_DIR must name an existing absolute prepared SQL directory"
        raise ValueError(message)
    env.setdefault("WORLD_DB_NAME", "ragnarok")
    env.update(
        WORLD_KIND=selection.world, WORLD_PROJECT=selection.project, WORLD_VOLUME=selection.volume
    )
    return env


def _required_inputs(env: dict[str, str]) -> None:
    for key in REQUIRED:
        value = env.get(key)
        if type(value) is not str or not value:
            message = f"{key} is required"
            raise ValueError(message)


def _ports(env: dict[str, str]) -> None:
    for key, default in PORTS.items():
        value = env.get(key, default)
        if (
            type(value) is not str
            or not re.fullmatch(r"[0-9]+", value)
            or not 1 <= int(value) <= 65535
        ):
            message = f"{key} must be an ASCII port from 1 to 65535"
            raise ValueError(message)
        env[key] = value


def _secret_files(env: dict[str, str]) -> None:
    for key in ("WORLD_DB_ROOT_SECRET_FILE", "WORLD_DB_USER_SECRET_FILE"):
        path = Path(env[key])
        if not path.is_absolute() or not path.is_file() or path.stat().st_mode & 0o077:
            message = f"{key} must name an existing private absolute file"
            raise ValueError(message)


COMPOSE_FILE = Path(__file__).resolve().parents[3] / "docker-compose.worlds.yml"
OPERATIONS = {
    "config": ["config", "--format", "json"],
    "up": ["up", "-d", "--no-build", "--pull", "never"],
    "down": ["down"],
    "status": ["ps", "--format", "json"],
}


def commands(selection: WorldSelection, operation: str) -> list[list[str]]:
    """Build argument arrays; wipe never forces removal or removes other volumes."""
    if operation == "wipe-test":
        if selection.world != "test":
            message = "wipe-test requires exactly the test world"
            raise ValueError(message)
        return [commands(selection, "down")[0], ["docker", "volume", "rm", selection.volume]]
    if operation not in OPERATIONS:
        message = "unknown world operation"
        raise ValueError(message)
    return [
        [
            "docker",
            "compose",
            "--env-file",
            "/dev/null",
            "-f",
            str(COMPOSE_FILE),
            "-p",
            selection.project,
            *OPERATIONS[operation],
        ]
    ]


@dataclass(frozen=True)
class WorldSelection:
    """A literal world identity, with one documented production alias."""

    world: str = "debug"

    def __post_init__(self) -> None:
        if (
            type(self.world) is not str
            or not re.fullmatch(r"(?:debug|test|prod|prod-[a-z0-9]+(?:-[a-z0-9]+)*)", self.world)
            or len(self.world) > 63
        ):
            message = "invalid world: use debug, test, prod or prod-NAME (lowercase ASCII)"
            raise ValueError(message)
        if self.world == "prod":
            object.__setattr__(self, "world", "prod-default")

    @property
    def project(self) -> str:
        return f"ro-bots-{self.world}"

    @property
    def volume(self) -> str:
        return f"ro-bots-world-{self.world}"


def load_inputs(raw_path: str, selection: WorldSelection) -> dict[str, str]:
    """Load private saved world metadata; never mix another world's input paths."""
    literal_parts(raw_path)
    data = decode_input(read_path(Path(raw_path), private=True))
    identities = {
        "WORLD_KIND": selection.world,
        "WORLD_PROJECT": selection.project,
        "WORLD_VOLUME": selection.volume,
    }
    expected = set(identities) | {
        "WORLD_DB_NAME",
        "WORLD_DB_USER",
        "WORLD_SCHEMA_DIR",
        "WORLD_DB_ROOT_SECRET_FILE",
        "WORLD_DB_USER_SECRET_FILE",
        "WORLD_LOGIN_PORT",
        "WORLD_CHAR_PORT",
        "WORLD_MAP_PORT",
    }
    if set(data) != expected or any(type(value) is not str for value in data.values()):
        message = "invalid saved world input schema"
        raise ValueError(message)
    if any(data[key] != value for key, value in identities.items()):
        message = "saved inputs do not match selected world"
        raise ValueError(message)
    return cast(dict[str, str], data)


def main(
    argv: list[str] | None = None,
    *,
    inputs: Mapping[str, str] | None = None,
    runner: Runner = subprocess.run,
) -> int:
    """CLI defaults read-only selection to debug; mutations need explicit world."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=[*OPERATIONS, "wipe-test"])
    parser.add_argument("--world")
    parser.add_argument("--inputs-file", help="private saved per-world Compose input JSON")
    parser.add_argument("--plan", action="store_true", help="print validated argument arrays only")
    args = parser.parse_args(argv)
    try:
        if args.world is None and args.operation not in ("config", "status"):
            message = "effectful operations require explicit --world"
            raise ValueError(message)
        selection = WorldSelection(args.world if args.world is not None else "debug")
        source = dict(os.environ if inputs is None else inputs)
        if args.inputs_file:
            source.update(load_inputs(args.inputs_file, selection))
        route = commands(selection, args.operation)
        if args.plan:
            environment(selection, source)
            result: Any = route
        else:
            result = dispatch(selection, args.operation, source, runner=runner)
        sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
    except (ValueError, RuntimeError) as error:
        sys.stderr.write(f"{error}\n")
        return 2
    except OSError, subprocess.TimeoutExpired:
        sys.stderr.write("world command unavailable or timed out; raw output withheld\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
