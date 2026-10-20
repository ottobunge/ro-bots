"""Prepare a new private host tree, not a provisioned or launchable world.

Trusted-user filesystem only: no publication protocol, rollback or container
execution. Failed writes can leave a partial tree; the original error propagates.
"""

import ipaddress
import os
import re
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from robots.adapters.rathena_runtime import MODE, STRINGS, private_configs, validate_fields
from robots.adapters.rathena_runtime_assets import config_asset, public_assets
from robots.adapters.world_bootstrap_sql import initialization_sql
from robots.adapters.world_compose import WorldSelection

# The bridge-container listener is intentionally not the published host endpoint.
BIND_IP = "0.0.0.0"  # nosec B104


@dataclass(frozen=True, repr=False)
class PreparationSettings:
    """Private caller input. Display identity is separate from Compose identity."""

    db_name: str
    db_user: str
    db_password: str
    inter_user: str
    inter_password: str
    root_password: str
    display_name: str = "RO Bots"
    server_mode: str = MODE
    db_host: str = "mariadb"
    db_port: int = 3306
    bind_ip: str = BIND_IP
    login_host: str = "rathena-login"
    char_host: str = "rathena-char"
    advertised_char_ip: str = "127.0.0.1"
    advertised_map_ip: str = "127.0.0.1"
    login_port: int = 6900
    char_port: int = 6121
    map_port: int = 5121
    pincode_enabled: bool = True


def _native_data(settings: PreparationSettings) -> dict[str, object]:
    return {
        "server_mode": settings.server_mode,
        "db_host": settings.db_host,
        "db_port": settings.db_port,
        "db_name": settings.db_name,
        "db_user": settings.db_user,
        "db_password": settings.db_password,
        "inter_user": settings.inter_user,
        "inter_password": settings.inter_password,
        "bind_ip": settings.bind_ip,
        "login_ip": settings.login_host,
        "char_ip": settings.advertised_char_ip,
        "map_ip": settings.advertised_map_ip,
        "login_port": settings.login_port,
        "char_port": settings.char_port,
        "map_port": settings.map_port,
        "pincode_enabled": settings.pincode_enabled,
    }


def _validate(settings: PreparationSettings) -> None:
    data = _native_data(settings)
    if any(type(data[field]) is not str for field in STRINGS):
        message = "plain private strings required"
        raise ValueError(message)
    validate_fields(data)  # Receiver bounds only; old endpoint/world policy is NOT reused.
    _fixed_endpoints(settings)
    _ports(settings)
    if type(data["pincode_enabled"]) is not bool:
        message = "explicit boolean PIN policy required"
        raise ValueError(message)
    if type(settings.display_name) is not str or not re.fullmatch(
        r"[A-Za-z0-9 _.()-]{1,19}", settings.display_name
    ):
        message = "bounded ASCII display name required"
        raise ValueError(message)
    if type(settings.root_password) is not str or not re.fullmatch(
        r"[A-Za-z0-9_!@$%^&*+=.,?-]{1,32}", settings.root_password
    ):
        message = "safe bounded root secret required"
        raise ValueError(message)


def _fixed_endpoints(settings: PreparationSettings) -> None:
    expected = {
        "server_mode": MODE,
        "db_host": "mariadb",
        "bind_ip": BIND_IP,
        "login_host": "rathena-login",
        "char_host": "rathena-char",
    }
    if any(
        type(getattr(settings, key)) is not str or getattr(settings, key) != value
        for key, value in expected.items()
    ):
        message = "unsupported Compose profile or service endpoint"
        raise ValueError(message)
    _advertised_addresses(settings)


def _advertised_addresses(settings: PreparationSettings) -> None:
    for value in (settings.advertised_char_ip, settings.advertised_map_ip):
        try:
            address = ipaddress.IPv4Address(value)
        except ipaddress.AddressValueError:
            message = "explicit advertised host IPv4 required"
            raise ValueError(message) from None
        if (
            address.is_unspecified
            or address.is_multicast
            or address == ipaddress.IPv4Address("255.255.255.255")
        ):
            message = "explicit advertised host IPv4 required"
            raise ValueError(message)


def _ports(settings: PreparationSettings) -> None:
    ports = (settings.db_port, settings.login_port, settings.char_port, settings.map_port)
    if any(type(port) is not int or not 1 <= port <= 65535 for port in ports):
        message = "explicit integer TCP ports required"
        raise ValueError(message)
    if settings.db_port != 3306 or len(set(ports)) != len(ports):
        message = "standard DB port and distinct role ports required"
        raise ValueError(message)


def _role_configs(settings: PreparationSettings) -> dict[str, bytes]:
    data = _native_data(settings)
    files = private_configs(data, settings.display_name)
    # char_ip is an advertisement in the char role, but a peer in the map role.
    map_data = data | {"char_ip": settings.char_host}
    files["conf/map_athena.conf"] = private_configs(map_data, settings.display_name)[
        "conf/map_athena.conf"
    ]
    defaults: dict[str, bytes] = {}
    omitted: set[str] = set()
    for name in (
        "conf/inter_athena.conf",
        "conf/login_athena.conf",
        "conf/char_athena.conf",
        "conf/map_athena.conf",
    ):
        config_asset(name, defaults, omitted)
    for name, overrides in files.items():
        if name in defaults:
            files[name] = _merge_defaults(defaults.pop(name), overrides)
    return defaults | files


def _merge_defaults(defaults: bytes, overrides: bytes) -> bytes:
    """Preserve source import order; discard replaced public scalar values.

    Optional template imports were removed by config_asset. Exact duplicate
    imports already emitted by the private renderer are retained only there.
    GRF, subnet and logging controls never receive public defaults.
    """
    replaced = {line.split(b":", 1)[0] for line in overrides.splitlines() if b":" in line} - {
        b"import"
    }
    override_lines = set(overrides.splitlines())
    selected: list[bytes] = []
    for line in defaults.splitlines():
        if not line or line.startswith(b"//") or b":" not in line:
            continue
        key = line.split(b":", 1)[0]
        if key in replaced or line in override_lines:
            continue
        selected.append(line)
    return b"\n".join(selected) + b"\n" + overrides


def _directory(path: Path) -> None:
    path.mkdir(mode=0o700, exist_ok=True)
    path.chmod(0o700)


def _write(root: Path, name: str, content: bytes) -> None:
    path = root / name
    for parent in reversed(path.parents):
        if parent == root or root in parent.parents:
            _directory(parent)
    handle = path.open("xb")
    try:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(content)
    except BaseException:
        with suppress(BaseException):
            handle.close()
        raise
    else:
        handle.close()


def create(
    target: Path, selection: WorldSelection, settings: PreparationSettings
) -> dict[str, object]:
    """Write pinned assets, role configs and private bootstrap to a NEW path.

    Every existing target is refused, even empty. Ownership stays with the
    operator; a later importer must set runtime UID 10000 and SQL/DB permissions.
    """
    if type(selection) is not WorldSelection or type(settings) is not PreparationSettings:
        message = "typed world selection and preparation settings required"
        raise ValueError(message)
    _validate(settings)
    if os.path.lexists(target):
        message = "preparation requires a new target"
        raise FileExistsError(message)
    assets, report = public_assets()
    files = {"runtime/" + name: raw for name, raw in (assets | _role_configs(settings)).items()}
    files.update(
        {
            "sql/" + name: raw
            for name, raw in initialization_sql(
                settings.db_name, settings.inter_user, settings.inter_password
            ).items()
        }
    )
    files["secrets/db-root"] = settings.root_password.encode("ascii")
    files["secrets/db-user"] = settings.db_password.encode("ascii")
    target.mkdir(mode=0o700)
    target.chmod(0o700)
    for name, raw in sorted(files.items()):
        _write(target, name, raw)
    for name in ("runtime/log", "memory", "memory/agents", "logs"):
        _directory(target / name)
    return {
        "world": selection.world,
        "project": selection.project,
        "volume": selection.volume,
        "profile": MODE,
        "asset_files": len(assets),
        "npc_files": report["npc_files"],
        "mapcache_checked_maps": report["mapcache_checked_maps"],
        "container_paths": {
            "runtime": "/world/runtime",
            "sql": "/docker-entrypoint-initdb.d",
        },
        "provisioning": False,
        "native_parser_ran": False,
        "host_bind_mount_ready": False,
    }
