"""Real owned-filesystem tests; no worlds, credentials, or runtime integration."""

import ctypes
import errno
import multiprocessing
import os
import sys
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest

from robots.adapters import runtime_publication_io as publication


@pytest.fixture
def workspace():
    scratch = Path(os.environ["TMPDIR"]).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="publication-io-", dir=scratch) as root:
        base = Path(root)
        source = base / "source"
        destination = base / "destination"
        source.mkdir(mode=0o700)
        destination.mkdir(mode=0o700)
        source_fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        destination_fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            yield base, source, destination, source_fd, destination_fd
        finally:
            os.close(destination_fd)
            os.close(source_fd)


def record_calls(calls: list[tuple[object, ...]]) -> Callable[..., int]:
    def record(*args: object) -> int:
        calls.append(args)
        return 0

    return record


def prepare(source: Path) -> Path:
    stage = source / "stage"
    stage.mkdir(mode=0o700)
    (stage / "foo").write_bytes(b"public fixture")
    return stage


def test_moves_real_directory_and_retains_borrowed_descriptors(workspace):
    _, source, destination, source_fd, destination_fd = workspace
    stage = prepare(source)
    root_fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY)
    try:
        identity = os.fstat(root_fd)
        publication.move_directory_noreplace(source_fd, "stage", destination_fd, "final")
        assert not stage.exists()
        assert (destination / "final").stat().st_ino == identity.st_ino
        assert os.fstat(root_fd).st_ino == identity.st_ino
        assert os.fstat(source_fd).st_ino == source.stat().st_ino
        assert os.fstat(destination_fd).st_ino == destination.stat().st_ino
        assert (destination / "final" / "foo").read_bytes() == b"public fixture"
    finally:
        os.close(root_fd)


def snapshot(path: Path) -> tuple[int, int, int, int, object]:
    info = path.lstat()
    content: object
    if path.is_symlink():
        content = os.readlink(path)
    elif path.is_dir():
        content = tuple((child.name, snapshot(child)) for child in sorted(path.iterdir()))
    else:
        content = path.read_bytes()
    return info.st_dev, info.st_ino, info.st_mode, info.st_uid, content


@pytest.mark.parametrize("kind", ["empty", "sentinel", "file", "symlink"])
def test_existing_destination_is_never_replaced(workspace, kind):
    _, source, destination, source_fd, destination_fd = workspace
    stage = prepare(source)
    final = destination / "final"
    if kind in {"empty", "sentinel"}:
        final.mkdir(mode=0o700)
        if kind == "sentinel":
            (final / "sentinel").write_bytes(b"public sentinel")
    elif kind == "file":
        final.write_bytes(b"public sentinel")
    else:
        final.symlink_to(stage, target_is_directory=True)
    before = snapshot(stage), snapshot(final)
    with pytest.raises(OSError, match=r"directory|rename") as error:
        publication.move_directory_noreplace(source_fd, "stage", destination_fd, "final")
    assert error.value.errno == errno.EEXIST
    assert (snapshot(stage), snapshot(final)) == before


@pytest.mark.parametrize("kind", ["file", "symlink"])
def test_source_must_be_directory_without_following_leaf(workspace, kind):
    _, source, destination, source_fd, destination_fd = workspace
    stage = source / "stage"
    if kind == "file":
        stage.write_bytes(b"public fixture")
    else:
        stage.symlink_to(destination, target_is_directory=True)
    before = snapshot(stage)
    with pytest.raises(OSError, match=r"directory|rename") as error:
        publication.move_directory_noreplace(source_fd, "stage", destination_fd, "final")
    assert error.value.errno == errno.ENOTDIR
    assert snapshot(stage) == before
    assert not (destination / "final").exists()


@pytest.mark.parametrize("name", ["", ".", "..", "a/b", "a\x00b", "a\nb", "é", "x" * 256, "\x7f"])
@pytest.mark.parametrize("side", ["source", "destination"])
def test_invalid_literal_names_refused_before_mutation(workspace, name, side, monkeypatch):
    _, source, destination, source_fd, destination_fd = workspace
    prepare(source)
    before = snapshot(source), snapshot(destination)
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(publication, "_renameat2", record_calls(calls))
    source_name = name if side == "source" else "stage"
    destination_name = name if side == "destination" else "final"
    with pytest.raises(ValueError, match="literal printable ASCII"):
        publication.move_directory_noreplace(
            source_fd, source_name, destination_fd, destination_name
        )
    assert not calls
    assert (snapshot(source), snapshot(destination)) == before


@pytest.mark.parametrize("value", [True, False, -1, 2**64, "3", None])
@pytest.mark.parametrize("side", ["source", "destination"])
def test_invalid_descriptor_refused_before_native_call(workspace, value, side, monkeypatch):
    _, source, destination, source_fd, destination_fd = workspace
    prepare(source)
    before = snapshot(source), snapshot(destination)
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(publication, "_renameat2", record_calls(calls))
    first = value if side == "source" else source_fd
    second = value if side == "destination" else destination_fd
    with pytest.raises((ValueError, OSError)):
        publication.move_directory_noreplace(first, "stage", second, "final")
    assert not calls
    assert (snapshot(source), snapshot(destination)) == before


@pytest.mark.parametrize("side", ["source", "destination"])
def test_regular_file_descriptor_is_rejected(workspace, side, monkeypatch):
    base, source, destination, source_fd, destination_fd = workspace
    prepare(source)
    file = base / "file"
    file.write_bytes(b"public fixture")
    fd = os.open(file, os.O_RDONLY)
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(publication, "_renameat2", record_calls(calls))
    try:
        with pytest.raises(OSError, match=r"directory|rename") as error:
            publication.move_directory_noreplace(
                fd if side == "source" else source_fd,
                "stage",
                fd if side == "destination" else destination_fd,
                "final",
            )
        assert error.value.errno == errno.ENOTDIR
        assert not calls
        assert os.fstat(fd).st_ino == file.stat().st_ino
        assert (source / "stage").is_dir()
        assert not (destination / "final").exists()
    finally:
        os.close(fd)


@pytest.mark.parametrize(
    "code", [errno.EINVAL, errno.ENOSYS, errno.EOPNOTSUPP, errno.EXDEV, errno.EIO]
)
def test_native_errno_is_refused_without_fallback(workspace, code, monkeypatch):
    _, source, destination, source_fd, destination_fd = workspace
    prepare(source)
    before = snapshot(source), snapshot(destination)
    calls = []

    class NativeFailure:
        argtypes: list[type]
        restype: type

        def __call__(self, *args):
            calls.append(args)
            ctypes.set_errno(code)
            return -1

    native = NativeFailure()
    library = SimpleNamespace(renameat2=native)
    monkeypatch.setattr(publication, "_load_libc", lambda: library, raising=False)

    def fallback(*args, **kwargs):
        pytest.fail("fallback reached")

    for operation in ("rename", "replace", "link", "unlink", "rmdir"):
        monkeypatch.setattr(os, operation, fallback)
    with pytest.raises(OSError, match=r"directory|rename") as error:
        publication.move_directory_noreplace(source_fd, "stage", destination_fd, "final")
    assert error.value.errno == code
    assert error.value.filename is None
    assert calls == [(source_fd, b"stage", destination_fd, b"final", 1)]
    assert native.argtypes == [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    assert native.restype is ctypes.c_int
    assert (snapshot(source), snapshot(destination)) == before


def test_missing_symbol_refuses_without_import_failure(workspace, monkeypatch):
    _, source, destination, source_fd, destination_fd = workspace
    prepare(source)
    before = snapshot(source), snapshot(destination)
    monkeypatch.setattr(publication, "_load_libc", SimpleNamespace, raising=False)
    with pytest.raises(OSError, match=r"directory|rename") as error:
        publication.move_directory_noreplace(source_fd, "stage", destination_fd, "final")
    assert error.value.errno == errno.ENOSYS
    assert "stage" not in str(error.value)
    assert (snapshot(source), snapshot(destination)) == before


def test_non_linux_refuses_before_loading_library(workspace, monkeypatch):
    _, source, destination, source_fd, destination_fd = workspace
    prepare(source)
    monkeypatch.setattr(sys, "platform", "unsupported")
    calls = []
    monkeypatch.setattr(publication, "_load_libc", lambda: calls.append(True), raising=False)
    with pytest.raises(OSError, match=r"directory|rename") as error:
        publication.move_directory_noreplace(source_fd, "stage", destination_fd, "final")
    assert error.value.errno == errno.ENOSYS
    assert not calls
    assert (source / "stage").is_dir()
    assert not (destination / "final").exists()


def test_syscall_wrapper_origin_exception_identity_is_preserved(workspace, monkeypatch):
    _, source, destination, source_fd, destination_fd = workspace
    prepare(source)
    origin = KeyboardInterrupt()
    calls = []

    def interrupted(*args):
        calls.append(args)
        raise origin

    monkeypatch.setattr(publication, "_renameat2", interrupted)
    with pytest.raises(KeyboardInterrupt) as error:
        publication.move_directory_noreplace(source_fd, "stage", destination_fd, "final")
    assert error.value is origin
    assert len(calls) == 1
    assert (source / "stage").is_dir()
    assert not (destination / "final").exists()


def test_retained_parent_fds_anchor_original_directories_after_path_replacement(workspace):
    base, source, destination, source_fd, destination_fd = workspace
    stage = prepare(source)
    source_inode = stage.stat().st_ino
    source.rename(base / "retained-source")
    destination.rename(base / "retained-destination")
    source.mkdir(mode=0o700)
    destination.mkdir(mode=0o700)
    prepare(source)
    (destination / "final").mkdir(mode=0o700)
    foreign = snapshot(source), snapshot(destination)
    publication.move_directory_noreplace(source_fd, "stage", destination_fd, "final")
    assert (base / "retained-destination" / "final").stat().st_ino == source_inode
    assert not (base / "retained-source" / "stage").exists()
    assert (snapshot(source), snapshot(destination)) == foreign


def test_competitor_creates_destination_at_reached_native_barrier(workspace, monkeypatch):
    _, source, destination, source_fd, destination_fd = workspace
    prepare(source)
    # Positive control reaches the real binding before the competitor scenario.
    publication.move_directory_noreplace(source_fd, "stage", destination_fd, "control")
    prepare(source)
    before = snapshot(source)
    arrived = threading.Event()
    finished = threading.Event()
    competitor_errors = []

    def competitor():
        try:
            assert arrived.wait(5)
            (destination / "final").mkdir(mode=0o700)
            (destination / "final" / "sentinel").write_bytes(b"public sentinel")
        except BaseException as error:
            competitor_errors.append(error)
        finally:
            finished.set()

    native = publication._renameat2
    calls = []
    replacement = []

    def barrier(*args):
        calls.append(args)
        arrived.set()
        assert finished.wait(5)
        replacement.append(snapshot(destination / "final"))
        return native(*args)

    monkeypatch.setattr(publication, "_renameat2", barrier)
    thread = threading.Thread(target=competitor)
    thread.start()
    try:
        with pytest.raises(OSError, match=r"directory|rename") as error:
            publication.move_directory_noreplace(source_fd, "stage", destination_fd, "final")
        assert error.value.errno == errno.EEXIST
    finally:
        arrived.set()
        thread.join(5)
    assert not thread.is_alive()
    assert not competitor_errors
    assert len(calls) == 1
    assert snapshot(source) == before
    assert snapshot(destination / "final") == replacement[0]


def race_worker(source_fd, destination_fd, name, barrier, connection):
    try:
        barrier.wait(timeout=5)
        try:
            publication.move_directory_noreplace(source_fd, name, destination_fd, "final")
        except OSError as error:
            connection.send((name, error.errno))
        else:
            connection.send((name, 0))
    finally:
        connection.close()
        os.close(source_fd)
        os.close(destination_fd)


def test_two_processes_one_destination_exactly_one_winner(workspace):
    _, source, destination, source_fd, destination_fd = workspace
    prepare(source).rename(source / "first")
    prepare(source).rename(source / "second")
    before = {name: snapshot(source / name) for name in ("first", "second")}
    context = multiprocessing.get_context("fork")
    barrier = context.Barrier(3)
    processes = []
    connections = []
    try:
        for name in ("first", "second"):
            parent, child = context.Pipe(duplex=False)
            process = context.Process(
                target=race_worker, args=(source_fd, destination_fd, name, barrier, child)
            )
            process.start()
            child.close()
            processes.append(process)
            connections.append(parent)
        barrier.wait(timeout=5)
        assert all(connection.poll(5) for connection in connections)
        outcomes = [connection.recv() for connection in connections]
        assert sorted(code for _, code in outcomes) == [0, errno.EEXIST]
        winner = next(name for name, code in outcomes if code == 0)
        loser = next(name for name, code in outcomes if code == errno.EEXIST)
        assert snapshot(destination / "final") == before[winner]
        assert snapshot(source / loser) == before[loser]
        assert not (source / winner).exists()
        assert os.fstat(source_fd).st_ino == source.stat().st_ino
        assert os.fstat(destination_fd).st_ino == destination.stat().st_ino
    finally:
        for process in processes:
            process.join(5)
            if process.is_alive():
                process.terminate()
                process.join(5)
            assert process.exitcode == 0
        for connection in connections:
            connection.close()


def test_literal_name_bounds_are_not_normalized(workspace):
    _, source, destination, source_fd, destination_fd = workspace
    name = " " + "x" * 253 + " "
    prepare(source).rename(source / name)
    inode = (source / name).stat().st_ino
    publication.move_directory_noreplace(source_fd, name, destination_fd, name)
    assert (destination / name).stat().st_ino == inode
    assert not (destination / name.strip()).exists()


def test_every_ascii_control_and_separator_is_refused(workspace, monkeypatch):
    _, source, destination, source_fd, destination_fd = workspace
    prepare(source)
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(publication, "_renameat2", record_calls(calls))
    for character in [*(chr(value) for value in range(32)), chr(127), "/"]:
        with pytest.raises(ValueError, match="literal printable ASCII"):
            publication.move_directory_noreplace(
                source_fd, "stage", destination_fd, f"a{character}b"
            )
    assert not calls
    assert not list(destination.iterdir())


def test_missing_source_reports_sanitized_errno(workspace):
    _, _, _, source_fd, destination_fd = workspace
    with pytest.raises(OSError, match="cannot inspect source directory") as error:
        publication.move_directory_noreplace(source_fd, "missing", destination_fd, "final")
    assert error.value.errno == errno.ENOENT
    assert error.value.filename is None
    assert "missing" not in str(error.value)
    assert error.value.__suppress_context__


@pytest.mark.parametrize("side", ["source", "destination"])
def test_closed_descriptor_is_refused_without_mutation(workspace, side):
    _, source, destination, source_fd, destination_fd = workspace
    prepare(source)
    closed = os.dup(source_fd)
    os.close(closed)
    with pytest.raises(OSError, match="Bad file descriptor") as error:
        publication.move_directory_noreplace(
            closed if side == "source" else source_fd,
            "stage",
            closed if side == "destination" else destination_fd,
            "final",
        )
    assert error.value.errno == errno.EBADF
    assert (source / "stage").is_dir()
    assert not list(destination.iterdir())
