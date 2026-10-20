"""Internal directory-publication primitive; no admission or durability authority."""

import ctypes
import errno
import os
import stat
import sys

# Verified against pinned devShell's <stdio.h>: RENAME_NOREPLACE (1 << 0).
_RENAME_NOREPLACE = 1


def _load_libc() -> ctypes.CDLL:
    return ctypes.CDLL(None, use_errno=True)


def _renameat2(
    source_parent_fd: int, source_name: bytes, destination_parent_fd: int, destination_name: bytes
) -> int:
    if sys.platform != "linux":
        message = "Linux nonreplacing rename unavailable"
        raise OSError(errno.ENOSYS, message)
    library = _load_libc()
    try:
        function = library.renameat2
    except AttributeError:
        message = "libc nonreplacing rename unavailable"
        raise OSError(errno.ENOSYS, message) from None
    function.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    function.restype = ctypes.c_int
    return int(
        function(
            source_parent_fd,
            source_name,
            destination_parent_fd,
            destination_name,
            _RENAME_NOREPLACE,
        )
    )


def _component(name: str) -> bytes:
    if (
        type(name) is not str
        or not 1 <= len(name) <= 255
        or name in {".", ".."}
        or any(not 32 <= ord(character) <= 126 or character == "/" for character in name)
    ):
        message = "expected one literal printable ASCII component (1..255 bytes)"
        raise ValueError(message)
    return name.encode("ascii")


def _directory_fd(fd: int) -> None:
    if type(fd) is not int or not 0 <= fd < 2 ** (ctypes.sizeof(ctypes.c_int) * 8 - 1):
        message = "expected a nonnegative integer directory descriptor"
        raise ValueError(message)
    if not stat.S_ISDIR(os.fstat(fd).st_mode):
        message = "descriptor is not a directory"
        raise OSError(errno.ENOTDIR, message)


def move_directory_noreplace(
    source_parent_fd: int, source_name: str, destination_parent_fd: int, destination_name: str
) -> None:
    """Acknowledge one Linux RENAME_NOREPLACE directory move, not durability.

    Borrowed directory fds remain caller-owned. Names must be exact built-in str
    values containing single printable ASCII components (1..255 bytes), not paths
    or world identities; string subclasses are rejected before overridable methods.
    No target
    precheck or replacing/copy/delete fallback exists. Kernel errno is retained;
    generated errors contain no supplied name/path or payload.

    Prerequisite: source namespace is controlled for the entire operation. The
    no-follow source kind check is NOT atomic inode/type binding: a same-UID
    mutator can replace it before rename. Retained parent fds anchor operations
    across parent path replacement, not pathname ownership, tree provenance,
    preparation, persistence, manager receipt, or launch/admission authority.
    """
    source_bytes = _component(source_name)
    destination_bytes = _component(destination_name)
    _directory_fd(source_parent_fd)
    _directory_fd(destination_parent_fd)
    try:
        source = os.stat(source_name, dir_fd=source_parent_fd, follow_symlinks=False)
    except OSError as error:
        message = "cannot inspect source directory entry"
        raise OSError(error.errno, message) from None
    if not stat.S_ISDIR(source.st_mode):
        message = "source entry is not a directory"
        raise OSError(errno.ENOTDIR, message)
    result = _renameat2(
        source_parent_fd,
        source_bytes,
        destination_parent_fd,
        destination_bytes,
    )
    if result != 0:
        message = "nonreplacing directory move failed"
        raise OSError(ctypes.get_errno(), message)
