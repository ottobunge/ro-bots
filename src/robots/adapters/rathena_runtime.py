"""Offline private rAthena bundles. Identity labels confer no execution authority."""

import argparse
import ipaddress
import json
import os
import re
import subprocess  # nosec B404
import sys
from pathlib import Path
from typing import NoReturn

from robots.adapters.rathena_runtime_assets import (
    PACKAGE_NAR,
    REVISION,
    SOURCE_NAR,
    public_assets,
)
from robots.adapters.rathena_runtime_io import (
    close_owned,
    create_root,
    decode_input,
    directory,
    literal_parts,
    read_at,
    read_path,
    reject,
    restore_at,
    restore_marker,
    verify_binding,
    verify_tree,
    write_at,
)

MODE = "MAIN-pre-re-20180704"
BLOCKERS = [
    "Native login/char/map artifacts refuse all startup with exit 78 before initialization.",
    "No native full configuration, NPC script, database-body or mapcache parser acceptance.",
    "No SQL schema/bootstrap/interserver account or owned player accounts provisioned.",
    "No fresh read-only engine/network/database ownership and offline isolation proof.",
    "No exclusive world lock, authorization, or trusted isolated launch executor.",
]
STRINGS = {
    "server_mode",
    "db_host",
    "db_name",
    "db_user",
    "db_password",
    "inter_user",
    "inter_password",
    "bind_ip",
    "login_ip",
    "char_ip",
    "map_ip",
}
PORTS = {"db_port", "login_port", "char_port", "map_port"}


def validate(data: dict[str, object], world: str) -> None:
    if not re.fullmatch(r"(?:test|debug|prod-[A-Za-z0-9][A-Za-z0-9_-]{0,13})", world):
        reject("explicit safe world identity required")
    if set(data) != STRINGS | PORTS | {"pincode_enabled"}:
        reject("unsupported private schema")
    if data["server_mode"] != MODE:
        reject("unsupported server profile")
    for field in PORTS:
        port = data[field]
        if type(port) is not int or not 1 <= port <= 65535:
            reject("explicit valid TCP port required")
    validate_fields(data)
    validate_endpoints(data)
    if type(data["pincode_enabled"]) is not bool:
        reject("explicit PIN policy required")


def validate_fields(data: dict[str, object]) -> None:
    for field in STRINGS - {"server_mode"}:
        value = data[field]
        if not isinstance(value, str) or not re.fullmatch(
            r"[A-Za-z0-9_!@$%^&*+=.,?-]{1,253}", value
        ):
            reject("unsafe private field")
    for field in ("db_name", "db_user", "inter_user"):
        if not re.fullmatch(r"[A-Za-z0-9_]{1,23}", str(data[field])):
            reject("unsafe private identifier")
    for field, limit in (("db_password", 32), ("inter_password", 23)):
        if len(str(data[field])) > limit:
            reject("unsupported private field length")


def validate_endpoints(data: dict[str, object]) -> None:
    host = str(data["db_host"])
    if (
        not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}", host)
        or host.lower() == "localhost"
        or host.startswith("127.")
    ):
        reject("explicit non-native SQL hostname required")
    for field in ("bind_ip", "login_ip", "char_ip", "map_ip"):
        try:
            address = ipaddress.IPv4Address(str(data[field]))
        except ipaddress.AddressValueError:
            reject("explicit IPv4 endpoint required")
        if address.is_loopback or address.is_unspecified or address.is_multicast:
            reject("unsupported endpoint")


def serialize(values: dict[str, object]) -> bytes:
    return "".join(f"{key}: {value}\n" for key, value in values.items()).encode("ascii")


def private_configs(data: dict[str, object], world: str) -> dict[str, bytes]:
    inter: dict[str, object] = {"use_sql_db": "no", "inter_server_conf": "inter_server.yml"}
    for prefix in ("login_server", "ipban_db", "char_server", "map_server", "log_db", "web_server"):
        for suffix, field in (
            ("ip", "db_host"),
            ("port", "db_port"),
            ("id", "db_user"),
            ("pw", "db_password"),
            ("db", "db_name"),
        ):
            inter[f"{prefix}_{suffix}"] = data[field]
    communication = {
        "userid": data["inter_user"],
        "passwd": data["inter_password"],
        "bind_ip": data["bind_ip"],
    }
    login = {
        "bind_ip": data["bind_ip"],
        "login_port": data["login_port"],
        "new_account": "no",
        "use_web_auth_token": "no",  # nosec B105
        "import": "conf/inter_athena.conf",
    }
    char = communication | {
        "server_name": world,
        "login_ip": data["login_ip"],
        "login_port": data["login_port"],
        "char_ip": data["char_ip"],
        "char_port": data["char_port"],
        "db_path": "db",
        "pincode_enabled": "yes" if data["pincode_enabled"] else "no",
    }
    map_config = communication | {
        "char_ip": data["char_ip"],
        "char_port": data["char_port"],
        "map_ip": data["map_ip"],
        "map_port": data["map_port"],
        "db_path": "db",
        "use_grf": "no",
        "motd_txt": "conf/motd.txt",
        "charhelp_txt": "conf/charhelp.txt",
        "channel_conf": "conf/channels.conf",
    }
    map_raw = (
        serialize(map_config)
        + b"import: conf/maps_athena.conf\nimport: npc/pre-re/scripts_main.conf\n"
    )
    return {
        "conf/inter_athena.conf": serialize(inter),
        "conf/login_athena.conf": serialize(login),
        "conf/char_athena.conf": serialize(char),
        "conf/map_athena.conf": map_raw,
        "conf/log_athena.conf": (
            b"sql_logs: no\nenable_logs: 0\nlog_cash: no\nlog_commands: no\n"
            b"log_npc: no\nlog_feeding: 0\n"
        ),
        "conf/grf-files.txt": b"// Offline mapcache-only bundle; no external GRF paths.\n",
        "conf/subnet_athena.conf": b"// No inherited LAN endpoint overrides.\n",
    }


def build_bundle(world: str, destination: Path, secret_file: Path) -> dict[str, object]:
    return build_from_bytes(world, destination, read_path(secret_file, private=True))


def build_from_bytes(world: str, destination: Path, raw: bytes) -> dict[str, object]:
    data = decode_input(raw)
    validate(data, world)
    literal_parts(destination)
    if destination.name != world or str(destination).startswith("/nix/store/"):
        reject("world-bound private destination required")
    assets, report = public_assets()
    manifest: dict[str, object] = {
        "schema": 1,
        "world": world,
        "profile": MODE,
        "revision": REVISION,
        "source_nar": SOURCE_NAR,
        "package_nar": PACKAGE_NAR,
        "launchable": False,
        "launch_blockers": BLOCKERS,
        "runtime_obfuscation": "compiled out; no runtime switch invented",
        "pin_policy_explicit": True,
        **report,
    }
    files = assets | private_configs(data, world)
    marker_removed = False
    try:
        with directory(destination.parent) as parent:
            parent_info = os.fstat(parent)
            fd = create_root(parent, world)
            try:
                opened = os.fstat(fd)
                write_at(fd, "INCOMPLETE", b"Owned partial bundle. No execution authority.\n")
                for path, content in sorted(files.items()):
                    write_at(fd, path, content)
                manifest_raw = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
                write_at(fd, "manifest.json", manifest_raw)
                if json.loads(read_at(fd, "manifest.json")) != manifest:
                    reject("manifest readback mismatch")
                verify_tree(fd)
                verify_binding(destination, parent_info, opened)
                marker_removed = True
                os.unlink("INCOMPLETE", dir_fd=fd)
                os.fsync(fd)
                verify_binding(destination, parent_info, opened)
            except BaseException as origin:
                if marker_removed:
                    restore_at(fd, origin)
                    marker_removed = False
                raise
            finally:
                close_owned(fd)
        verify_binding(destination, parent_info, opened)
    except BaseException as origin:
        if marker_removed:
            restore_marker(destination, opened, origin)
        raise
    return manifest


class OfflineParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        del message
        self.exit(2, "unsupported offline bundle arguments\n")


def main() -> int:
    parser = OfflineParser(description="Offline private bundle only; no launch or SQL operations.")
    parser.add_argument("--world", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--secret-file", required=True)
    args = parser.parse_args()
    try:
        literal_parts(args.destination)
        if args.secret_file != "-":  # nosec B105
            literal_parts(args.secret_file)
        destination = Path(args.destination)
        if args.secret_file == "-":  # nosec B105
            manifest = build_from_bytes(args.world, destination, sys.stdin.buffer.read(8193))
        else:
            manifest = build_bundle(args.world, destination, Path(args.secret_file))
    except OSError, ValueError, UnicodeError, subprocess.TimeoutExpired:
        sys.stderr.write("offline bundle rejected; owned partial output may remain, never launch\n")
        return 2
    sys.stdout.write(
        json.dumps(
            {"world": manifest["world"], "launchable": False, "npc_files": manifest["npc_files"]}
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
