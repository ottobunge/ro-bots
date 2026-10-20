"""Source-only private-tree synchronization; no publication or admission authority."""

import os
import stat
import sys
from collections.abc import Iterator
from contextlib import contextmanager

from robots.adapters.rathena_runtime_io import close_owned as _close_owned

MAX_DEPTH = 32
MAX_ENTRIES = 8192

type _Snapshot = tuple[os.stat_result, dict[str, _Snapshot]]


def _bounded_names(fd: int) -> list[str]:
    names: list[str] = []
    scan = os.scandir(fd)
    try:
        for entry in scan:
            if len(names) >= MAX_ENTRIES:
                message = "private tree bound exceeded"
                raise ValueError(message)
            names.append(entry.name)
    finally:
        origin = sys.exception()
        try:
            scan.close()
        except BaseException:
            if origin is None:
                raise
            origin.add_note("Private tree directory scan cleanup failed; not retried.")
    return names


def _check(info: os.stat_result, *, directory: bool) -> None:
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    mode = 0o700 if directory else 0o600
    if not kind(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != mode:
        message = "private tree metadata rejected"
        raise ValueError(message)


def _same(current: os.stat_result, observed: os.stat_result) -> None:
    fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_uid",
        "st_gid",
        "st_size",
        "st_nlink",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(getattr(current, field) != getattr(observed, field) for field in fields):
        message = "private tree observation changed"
        raise ValueError(message)


@contextmanager
def _entry(parent: int, name: str, observed: os.stat_result) -> Iterator[int]:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    if stat.S_ISDIR(observed.st_mode):
        flags |= os.O_DIRECTORY
    child = os.open(name, flags, dir_fd=parent)
    try:
        _same(os.fstat(child), observed)
        yield child
        _same(os.fstat(child), observed)
        _same(os.stat(name, dir_fd=parent, follow_symlinks=False), observed)
    finally:
        _close_owned(child)


def _verify(fd: int, snapshot: _Snapshot) -> None:
    observed, children = snapshot
    _same(os.fstat(fd), observed)
    if set(_bounded_names(fd)) != children.keys():
        message = "private tree namespace changed"
        raise ValueError(message)
    for name, (info, _) in children.items():
        _same(os.stat(name, dir_fd=fd, follow_symlinks=False), info)


def _sync_files(fd: int, depth: int, budget: list[int]) -> _Snapshot:
    if depth > MAX_DEPTH:
        message = "private tree bound exceeded"
        raise ValueError(message)
    observed = os.fstat(fd)
    _check(observed, directory=True)
    children: dict[str, _Snapshot] = {}
    names = _bounded_names(fd)
    budget[0] += len(names)
    if budget[0] > MAX_ENTRIES:
        message = "private tree bound exceeded"
        raise ValueError(message)
    for name in names:
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        directory = stat.S_ISDIR(info.st_mode)
        _check(info, directory=directory)
        with _entry(fd, name, info) as child:
            if directory:
                children[name] = _sync_files(child, depth + 1, budget)
            else:
                os.fsync(child)
                children[name] = (info, {})
    snapshot = observed, children
    _verify(fd, snapshot)
    return snapshot


def _sync_directories(fd: int, snapshot: _Snapshot) -> None:
    _verify(fd, snapshot)
    for name, child_snapshot in snapshot[1].items():
        if stat.S_ISDIR(child_snapshot[0].st_mode):
            with _entry(fd, name, child_snapshot[0]) as child:
                _sync_directories(child, child_snapshot)
    _verify(fd, snapshot)
    os.fsync(fd)
    _verify(fd, snapshot)


def sync_private_tree(root_fd: int) -> None:
    """Return None only after files, nested directories and borrowed root acknowledge."""
    if not isinstance(root_fd, int) or isinstance(root_fd, bool):
        message = "private tree directory descriptor required"
        raise ValueError(message)
    try:
        snapshot = _sync_files(root_fd, 0, [0])
        _sync_directories(root_fd, snapshot)
    except OSError as error:
        message = "private tree synchronization syscall failed"
        error.strerror = message
        error.filename = None
        error.filename2 = None
        error.args = (error.errno, message) if error.errno is not None else (message,)
        raise
