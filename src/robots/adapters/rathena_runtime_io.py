"""Private fd-anchored bundle I/O; failed builds retain their owned partial tree."""

import json
import os
import stat
import sys
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import BinaryIO, NoReturn, cast


class BundleRejectedError(ValueError):
    """Sanitized rejection with no private input attached."""


def reject(message: str) -> NoReturn:
    raise BundleRejectedError(message)


def literal_parts(path: Path | str) -> tuple[str, ...]:
    parts = str(path).split("/")
    if not str(path).startswith("/") or any(p in ("", ".", "..") for p in parts[1:]):
        reject("absolute literal path required")
    return tuple(parts[1:])


def close_owned(fd: int) -> None:
    """Attempt once; a close may have released its fd even when it raises."""
    origin = sys.exception()
    try:
        os.close(fd)
    except BaseException:
        if origin is None:
            raise
        origin.add_note("Owned descriptor cleanup also failed; not retried.")


@contextmanager
def directory(path: Path) -> Iterator[int]:
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in literal_parts(path):
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            previous, fd = fd, new
            close_owned(previous)
        yield fd
    finally:
        close_owned(fd)


@contextmanager
def stream_at(leaf: int, mode: str) -> Iterator[BinaryIO]:
    stream = cast(BinaryIO, os.fdopen(leaf, mode, closefd=False))
    try:
        yield stream.__enter__()
    finally:
        origin = sys.exception()
        try:
            stream.__exit__(
                type(origin) if origin else None, origin, origin.__traceback__ if origin else None
            )
        except BaseException:
            if origin is None:
                raise
            origin.add_note("Owned stream cleanup also failed.")


def check_output(info: os.stat_result, *, is_directory: bool = False) -> None:
    kind = stat.S_ISDIR if is_directory else stat.S_ISREG
    mode = 0o700 if is_directory else 0o600
    if not kind(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != mode:
        reject("private output metadata required")


def create_root(parent: int, world: str) -> int:
    os.mkdir(world, 0o700, dir_fd=parent)
    created = os.stat(world, dir_fd=parent, follow_symlinks=False)
    fd = os.open(world, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    try:
        opened = os.fstat(fd)
        check_output(opened, is_directory=True)
        if (opened.st_dev, opened.st_ino) != (created.st_dev, created.st_ino) or os.listdir(fd):
            reject("new private bundle root required")
    except BaseException:
        close_owned(fd)
        raise
    return fd


def restore_at(fd: int, origin: BaseException) -> None:
    try:
        with suppress(FileExistsError):
            write_at(fd, "INCOMPLETE", b"Owned failed publication. Never launch.\n")
    except BaseException:
        origin.add_note("Owned publication marker restoration failed; quarantine required.")


def restore_marker(destination: Path, owned: os.stat_result, origin: BaseException) -> None:
    """Reopen only a proven owned inode; never touch a substituted tree."""
    try:
        with directory(destination) as fd:
            current = os.fstat(fd)
            if (current.st_dev, current.st_ino) != (owned.st_dev, owned.st_ino):
                reject("failed publication root moved; no replacement touched")
            check_output(current, is_directory=True)
            restore_at(fd, origin)
    except BaseException:
        origin.add_note("Owned publication marker restoration failed; quarantine required.")


def verify_binding(
    destination: Path, parent_info: os.stat_result, root_info: os.stat_result
) -> None:
    with directory(destination.parent) as parent:
        current = os.fstat(parent)
        if (current.st_dev, current.st_ino) != (parent_info.st_dev, parent_info.st_ino):
            reject("requested parent binding changed")
        current = os.stat(destination.name, dir_fd=parent, follow_symlinks=False)
        check_output(current, is_directory=True)
        if (current.st_dev, current.st_ino) != (root_info.st_dev, root_info.st_ino):
            reject("requested root binding changed")


def verify_tree(fd: int) -> None:
    check_output(os.fstat(fd), is_directory=True)
    for name in os.listdir(fd):
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISDIR(info.st_mode):
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                verify_tree(child)
            finally:
                close_owned(child)
        else:
            read_at(fd, name, output=info)


def read_at(
    fd: int, name: str, *, private: bool = False, output: os.stat_result | None = None
) -> bytes:
    leaf = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        info = os.fstat(leaf)
        if output is not None:
            check_output(info)
            check_output(os.fstat(fd), is_directory=True)
            if (info.st_dev, info.st_ino) != (output.st_dev, output.st_ino):
                reject("owned output inode required")
        if not stat.S_ISREG(info.st_mode):
            reject("regular file required")
        if private and (
            info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) not in (0o400, 0o600)
        ):
            reject("owner-private input required")
        limit = 8192 if private else 64 * 1024 * 1024
        if info.st_size > limit:
            reject("bounded file required")
        with stream_at(leaf, "rb") as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            reject("bounded file required")
        return data
    finally:
        close_owned(leaf)


def read_path(path: Path, *, private: bool = False) -> bytes:
    literal_parts(path)
    with directory(path.parent) as fd:
        return read_at(fd, path.name, private=private)


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            reject("duplicate field")
        result[key] = value
    return result


def decode_input(raw: bytes) -> dict[str, object]:
    if len(raw) > 8192:
        reject("bounded input required")
    try:
        data: object = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=unique_object
        )
    except ValueError, UnicodeError:
        reject("private input rejected")
    if not isinstance(data, dict):
        reject("private schema rejected")
    return data


def write_at(root: int, relative: str, data: bytes) -> None:
    """Create exclusively and compare the exact owned file through retained fds."""
    parts = relative.split("/")
    if any(p in ("", ".", "..") for p in parts):
        reject("unsafe asset reference")
    fd = os.dup(root)
    try:
        for part in parts[:-1]:
            with suppress(FileExistsError):
                os.mkdir(part, 0o700, dir_fd=fd)
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            previous, fd = fd, new
            close_owned(previous)
            info = os.fstat(fd)
            if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
                reject("private bundle directory required")
        leaf = os.open(
            parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd
        )
        try:
            created = os.fstat(leaf)
            with stream_at(leaf, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            close_owned(leaf)
        if read_at(fd, parts[-1], output=created) != data:
            reject("bundle readback mismatch")
    finally:
        close_owned(fd)
