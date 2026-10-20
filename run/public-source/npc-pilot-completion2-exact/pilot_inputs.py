"""Default conditional assembler. No implicit activation or credential discovery."""

import hashlib
import importlib.util
import json
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import guards


class Lock(Protocol):
    fd: int | None
    quarantined: bool

    def acquire(self) -> None: ...

    def release(self) -> None: ...


class ReviewedLauncher(Protocol):
    FixtureLock: Callable[[Path], Lock]


@dataclass(frozen=True)
class Inputs:
    config: dict[str, Any]
    manifest: dict[str, Any]
    location: dict[str, Any]
    authority: dict[str, Any]
    approval_path: Path

    def refresh(self, *, cleanup: bool = False) -> None:
        authority = guards.guard(self.approval_path, cleanup=cleanup)
        config, manifest = read_inputs(self.location, authority)
        if (authority, config, manifest) != (self.authority, self.config, self.manifest):
            msg = "fixture inputs changed"
            raise ValueError(msg)


def require_private_descriptor(fd: int) -> None:
    meta = os.fstat(fd)
    if not private_metadata(meta):
        msg = "fixture private permissions refused"
        raise ValueError(msg)


def private_metadata(meta: os.stat_result) -> bool:
    return bool(
        stat.S_ISREG(meta.st_mode)
        and meta.st_uid == os.getuid()
        and stat.S_IMODE(meta.st_mode) == 0o600
    )


def read_private(path: Path, expected: str) -> dict[str, Any]:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        require_private_descriptor(fd)
        with os.fdopen(fd, "rb", closefd=False) as handle:
            data = handle.read(65537)
        if len(data) > 65536 or hashlib.sha256(data).hexdigest() != expected:
            msg = "fixture private digest refused"
            raise ValueError(msg)
        document = json.loads(data)
        if not isinstance(document, dict):
            msg = "fixture private object refused"
            raise ValueError(msg)
        return document
    finally:
        os.close(fd)


def validate_private(config: dict[str, Any], manifest: dict[str, Any]) -> None:
    if (manifest.get("login_host"), manifest.get("login_port")) != ("127.0.0.1", 16900):
        msg = "fixture endpoint refused"
        raise ValueError(msg)
    rows, pairs = fixture_collections(manifest.get("accounts"), config.get("exact_pairs"))
    if any(not isinstance(row, dict) for row in rows):
        msg = "fixture row refused"
        raise ValueError(msg)
    if {row.get("persona_id") for row in rows} != set(pairs):
        msg = "fixture persona mapping refused"
        raise ValueError(msg)
    for row in rows:
        validate_row(row)
    validate_pairs(pairs)
    for key in ("account", "char_name"):
        if len({row[key] for row in rows}) != 2:
            msg = "fixture unique identity refused"
            raise ValueError(msg)


def fixture_collections(rows: Any, pairs: Any) -> tuple[list[Any], dict[str, Any]]:
    if not isinstance(rows, list) or not isinstance(pairs, dict):
        msg = "fixture count refused"
        raise ValueError(msg)
    if len(rows) != 2 or len(pairs) != 2:
        msg = "fixture count refused"
        raise ValueError(msg)
    return rows, pairs


def validate_pairs(pairs: dict[str, Any]) -> None:
    for pair in pairs.values():
        if (
            not isinstance(pair, list)
            or len(pair) != 2
            or any(type(value) is not int or value <= 1 for value in pair)
        ):
            msg = "fixture account mapping refused"
            raise ValueError(msg)
    if any(len({pair[index] for pair in pairs.values()}) != 2 for index in (0, 1)):
        msg = "fixture exact ownership refused"
        raise ValueError(msg)


def validate_row(row: dict[str, Any]) -> None:
    if any(
        type(row.get(key)) is not str or not row[key]
        for key in ("persona_id", "account", "password", "char_name", "pincode")
    ):
        msg = "fixture required value refused"
        raise ValueError(msg)
    pin = row["pincode"]
    if len(pin) != 4 or any(char not in "0123456789" for char in pin):
        msg = "fixture PIN shape refused"
        raise ValueError(msg)
    if any(key in row for key in ("login_host", "login_port", "create_char")):
        msg = "fixture endpoint override refused"
        raise ValueError(msg)


def read_inputs(
    location: dict[str, Any], authority: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    config, manifest = (
        read_private(Path(location[key]), authority["private_hashes"][key])
        for key in ("config", "host_manifest")
    )
    validate_private(config, manifest)
    return config, manifest


def reviewed_lock(path: Path) -> Lock:
    guards.verify_hashes({str(guards.LOCK_SOURCE): guards.LOCK_DIGEST})
    spec = importlib.util.spec_from_file_location("npc_pilot_reviewed_lock", guards.LOCK_SOURCE)
    if spec is None or spec.loader is None:
        msg = "reviewed lock import refused"
        raise ValueError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(ReviewedLauncher, module).FixtureLock(path)


def assemble_native(
    approval_path: Path = guards.AUTHORITY,
    location_path: Path = guards.ROOT / "run/reviews/scheduled-native-host-private-location.json",
) -> Inputs:
    authority = guards.guard(approval_path)
    location = guards.public_json(location_path)
    config, manifest = read_inputs(location, authority)
    # The host/providers are constructed only after lock and fresh preflight.
    return Inputs(config, manifest, location, authority, approval_path)
