"""Prepare private host files only; no SQL, containers or native startup."""

import argparse
import json
import os
import secrets
import stat
import sys
from dataclasses import fields, replace
from pathlib import Path
from typing import NoReturn

from robots.adapters import world_prepare
from robots.adapters.rathena_runtime_io import (
    close_owned,
    directory,
    literal_parts,
    stream_at,
    unique_object,
    write_at,
)
from robots.adapters.world_compose import WorldSelection
from robots.adapters.world_prepare import PreparationSettings

REPO_ROOT = Path(__file__).resolve().parents[3]
PENDING = ["volume-import-runtime-uid-10000", "verified-mariadb-reader-uid"]


class Parser(argparse.ArgumentParser):
    """Never echo unsupported arguments or private input values."""

    def error(self, message: str) -> NoReturn:
        del message
        self.exit(2, "world preparation: unsupported arguments\n")


def generated_settings() -> PreparationSettings:
    """Independent 128-bit service secrets fit all three native receivers."""
    return PreparationSettings(
        db_name="ragnarok",
        db_user="ro_bots",
        inter_user="world_server",
        db_password=secrets.token_urlsafe(16),
        inter_password=secrets.token_urlsafe(16),
        root_password=secrets.token_urlsafe(16),
    )


def read_settings(raw_path: str) -> PreparationSettings:
    """Read an operator-owned regular 0600 UTF-8 JSON file, at most 32 KiB."""
    literal_parts(raw_path)
    path = Path(raw_path)
    with directory(path.parent) as parent:
        leaf = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(leaf)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_size > 32768
            ):
                message = "private bounded regular settings required"
                raise ValueError(message)
            with stream_at(leaf, "rb") as stream:
                raw = stream.read(32769)
        finally:
            close_owned(leaf)
    return decode_settings(raw)


def decode_settings(raw: bytes) -> PreparationSettings:
    """Accept only exact dataclass field names and JSON scalar types."""
    if len(raw) > 32768:
        message = "bounded settings required"
        raise ValueError(message)
    data = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=unique_object)
    schema = {field.name: field.type for field in fields(PreparationSettings)}
    if not isinstance(data, dict) or any(
        key not in schema or type(value) is not schema[key] for key, value in data.items()
    ):
        message = "unsupported settings schema"
        raise ValueError(message)
    return PreparationSettings(**data)


def compose_inputs(
    target: Path, selection: WorldSelection, settings: PreparationSettings
) -> dict[str, str]:
    """Persist private input metadata, not image guesses or password values."""
    return {
        "WORLD_KIND": selection.world,
        "WORLD_PROJECT": selection.project,
        "WORLD_VOLUME": selection.volume,
        "WORLD_DB_NAME": settings.db_name,
        "WORLD_DB_USER": settings.db_user,
        "WORLD_SCHEMA_DIR": str(target / "sql"),
        "WORLD_DB_ROOT_SECRET_FILE": str(target / "secrets/db-root"),
        "WORLD_DB_USER_SECRET_FILE": str(target / "secrets/db-user"),
        "WORLD_LOGIN_PORT": str(settings.login_port),
        "WORLD_CHAR_PORT": str(settings.char_port),
        "WORLD_MAP_PORT": str(settings.map_port),
    }


def prepare(args: argparse.Namespace) -> dict[str, object]:
    selection = WorldSelection(args.world)
    settings = read_settings(args.settings_file) if args.settings_file else generated_settings()
    for role in ("login", "char", "map"):
        value = getattr(args, role + "_port")
        if value is not None:
            settings = replace(settings, **{role + "_port": value})
    world_prepare._validate(settings)
    if args.destination is None:
        target = REPO_ROOT / "run/worlds" / selection.world
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.parent.chmod(0o700)
    else:
        literal_parts(args.destination)
        target = Path(args.destination)
    summary = world_prepare.create(target, selection, settings)
    data = json.dumps(compose_inputs(target, selection, settings), sort_keys=True).encode("utf-8")
    with directory(target) as fd:
        write_at(fd, "compose-inputs.json", data + b"\n")
    return summary | {"stage": str(target), "prepared": True, "pending": PENDING}


def main(argv: list[str] | None = None) -> int:
    """Sanitized CLI errors; interrupted preparation can leave a private partial tree."""
    parser = Parser(description=__doc__)
    parser.add_argument("--world", required=True)
    parser.add_argument(
        "--settings-file", help="absolute private 0600 JSON settings (maximum 32 KiB)"
    )
    parser.add_argument("--destination", help="absolute new host stage (existing targets refused)")
    for role in ("login", "char", "map"):
        parser.add_argument("--" + role + "-port", type=int)
    args = parser.parse_args(argv)
    try:
        summary = prepare(args)
    except Exception as error:
        detail = (
            f"errno={error.errno}"
            if isinstance(error, OSError)
            else "input or preparation rejected"
        )
        sys.stderr.write(
            f"world preparation failed ({type(error).__name__}; {detail}); "
            "private details withheld\n"
        )
        return 2
    sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
