"""Copy a trusted prepared stage into one existing empty volume.

No engine calls, SQL execution, rollback or durable-publication claims. A failed
copy may leave partial output; nonempty output must never be imported again.
"""

import argparse
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Never

SQL_NAMES = (
    "10-main.sql",
    "20-logs.sql",
    "30-web.sql",
    "40-roulette.sql",
    "50-interserver.sql",
)
TREES = ("runtime", "memory", "logs")
SECRETS = ("db-root", "db-user")
NATIVE_FILES = frozenset(f"runtime/bin/{role}-server" for role in ("login", "char", "map"))


def real_roots(source: Path, destination: Path) -> None:
    for root in (source, destination):
        if any(path.is_symlink() for path in (root, *root.parents)):
            message = "symlink path refused"
            raise ValueError(message)
        if not stat.S_ISDIR(root.lstat().st_mode):
            message = "real directory required"
            raise ValueError(message)
    if any(destination.iterdir()):
        message = "existing empty destination required"
        raise FileExistsError(message)


def preflight(source: Path, destination: Path, owners: tuple[int, ...]) -> None:
    if any(type(owner) is not int or not 0 <= owner < 4294967295 for owner in owners):
        message = "invalid owner configuration"
        raise ValueError(message)
    real_roots(source, destination)
    source_directories(source)
    source_file_sets(source)
    files = regular_source_files(source)
    required_sources(source, files)


def source_directories(source: Path) -> None:
    if any(path.is_symlink() for path in source.iterdir()):
        message = "symlink source refused"
        raise ValueError(message)
    for name in (*TREES, "runtime/conf", "runtime/log", "memory/agents", "sql", "secrets"):
        if not stat.S_ISDIR((source / name).lstat().st_mode):
            message = "prepared directory required"
            raise ValueError(message)


def source_file_sets(source: Path) -> None:
    for name, expected in (("sql", SQL_NAMES), ("secrets", SECRETS)):
        if {path.name for path in (source / name).iterdir()} != set(expected):
            message = "unexpected prepared file set"
            raise ValueError(message)


def regular_source_files(source: Path) -> list[Path]:
    paths = [path for name in (*TREES, "sql", "secrets") for path in (source / name).rglob("*")]
    files = []
    for path in paths:
        mode = path.lstat().st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            message = "only regular files and directories supported"
            raise ValueError(message)
        if stat.S_ISREG(mode):
            with path.open("rb") as incoming:
                if (
                    incoming.read(4) == b"\x7fELF"
                    and path.relative_to(source).as_posix() not in NATIVE_FILES
                ):
                    message = "native binaries belong in immutable images"
                    raise ValueError(message)
            files.append(path)
    return files


def required_sources(source: Path, files: list[Path]) -> None:
    required_files = [source / "sql" / name for name in SQL_NAMES]
    required_files.extend(source / "secrets" / name for name in SECRETS)
    if any(not stat.S_ISREG(path.lstat().st_mode) for path in required_files):
        message = "regular SQL and secret files required"
        raise ValueError(message)
    if not any(source / "runtime" in path.parents for path in files):
        message = "prepared runtime files required"
        raise ValueError(message)


class PrivateArgumentParser(argparse.ArgumentParser):
    """Never echo rejected caller values."""

    def error(self, message: str) -> Never:
        del message
        self.exit(2, "invalid import arguments\n")


def directory(path: Path, uid: int, gid: int) -> None:
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    os.chown(path, uid, gid)


def copy_file(source: Path, target: Path, uid: int, gid: int) -> None:
    with source.open("rb") as incoming:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as outgoing:
            os.fchmod(outgoing.fileno(), 0o600)
            os.fchown(outgoing.fileno(), uid, gid)
            shutil.copyfileobj(incoming, outgoing)


def import_stage(
    source: Path,
    destination: Path,
    *,
    runtime_uid: int,
    runtime_gid: int,
    mysql_uid: int,
    mysql_gid: int,
) -> dict[str, int]:
    preflight(source, destination, (runtime_uid, runtime_gid, mysql_uid, mysql_gid))
    counts = {"runtime_files": 0, "memory_files": 0, "logs_files": 0}
    for name in TREES:
        directory(destination / name, runtime_uid, runtime_gid)
        for path in sorted((source / name).rglob("*")):
            if path.relative_to(source).as_posix() in NATIVE_FILES:
                continue
            target = destination / path.relative_to(source)
            if path.is_dir():
                directory(target, runtime_uid, runtime_gid)
            else:
                copy_file(path, target, runtime_uid, runtime_gid)
                counts[name + "_files"] += 1
    directory(destination / "db", mysql_uid, mysql_gid)
    directory(destination / "secrets", mysql_uid, mysql_gid)
    for name in SECRETS:
        copy_file(source / "secrets" / name, destination / "secrets" / name, mysql_uid, mysql_gid)
    for name in SQL_NAMES:
        copy_file(source / "sql" / name, destination / name, mysql_uid, mysql_gid)
    os.chown(destination, os.geteuid(), os.getegid())
    # MariaDB's non-root init hook lists this directory before processing SQL.
    # Only entry names are readable; files stay 0600 and private subtrees stay 0700.
    destination.chmod(0o755)
    return counts | {"sql_files": len(SQL_NAMES), "secret_files": len(SECRETS)}


def main(argv: list[str] | None = None) -> int:
    parser = PrivateArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("/prepared"))
    parser.add_argument("--destination", type=Path, default=Path("/world"))
    parser.add_argument("--runtime-uid", type=int, default=10000)
    parser.add_argument("--runtime-gid", type=int, default=10000)
    parser.add_argument("--mysql-uid", type=int, default=999)
    parser.add_argument("--mysql-gid", type=int, default=999)
    args = parser.parse_args(argv)
    try:
        counts = import_stage(**vars(args))
    except Exception as error:
        sys.stderr.write(f"import failed: {type(error).__name__}; partial output may remain\n")
        return 1
    sys.stdout.write(json.dumps(counts, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
