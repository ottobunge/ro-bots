import errno
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from threading import Event, Thread

import pytest

from robots.adapters import runtime_publication_journal as journal


@pytest.fixture
def private_root(tmp_path):
    root = tmp_path / "journal-root"
    root.mkdir(mode=0o700)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        yield root, fd
    finally:
        os.close(fd)


def test_create_append_readback_reopen_is_historical(private_root):
    root, fd = private_root
    log = journal.PublicationJournal(fd)
    generation = log.generation
    for event in ("intent", "prepared", "committed"):
        log.append("tx-1", "test", event, "none")
    assert log.acknowledged_in_this_generation("tx-1")
    assert [record.event for record in log.records] == ["intent", "prepared", "committed"]
    assert stat.S_IMODE((root / journal.BASENAME).stat().st_mode) == 0o600
    log.close()
    assert stat.S_ISDIR(os.fstat(fd).st_mode)
    reopened = journal.PublicationJournal(fd)
    try:
        assert reopened.generation != generation
        assert len(reopened.records) == 3
        assert not reopened.acknowledged_in_this_generation("tx-1")
    finally:
        reopened.close()


def test_two_process_writer_lock_and_real_restart(private_root):
    root, fd = private_root
    log = journal.PublicationJournal(fd)
    code = """
import os, sys
from robots.adapters.runtime_publication_journal import PublicationJournal
fd = os.open(sys.argv[1], os.O_RDONLY | os.O_DIRECTORY)
try:
    log = PublicationJournal(fd)
except BlockingIOError:
    print('locked')
else:
    print(log.generation, len(log.records), log.acknowledged_in_this_generation('tx-1'))
    log.close()
finally:
    os.close(fd)
"""

    def child() -> str:
        return subprocess.run(
            [sys.executable, "-c", code, str(root)],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()

    try:
        assert child() == "locked"
        for event in ("intent", "prepared", "committed"):
            log.append("tx-1", "test", event, "none")
    finally:
        log.close()
    generation, count, acknowledged = child().split()
    assert generation != log.generation
    assert count == "3"
    assert acknowledged == "False"


class AlteredString(str):
    def encode(self, *args, **kwargs):
        return b"escaped"


@pytest.mark.parametrize(
    ("transaction", "world", "event", "reason"),
    [
        (AlteredString("tx"), "test", "intent", "none"),
        ("tx", AlteredString("test"), "intent", "none"),
        ("tx", "test", AlteredString("intent"), "none"),
        ("tx", "test", "intent", AlteredString("none")),
        ("../tx", "test", "intent", "none"),
        ("x" * 65, "test", "intent", "none"),
        ("tx", "test-" + "x" * 15, "intent", "none"),
        ("tx", "prod", "intent", "none"),
        ("tx", "test", "unknown", "none"),
        ("tx", "test", "intent", "secret text"),
        ("tx", "test", "committed", "none"),
    ],
)
def test_invalid_append_has_no_disk_or_memory_mutation(
    private_root, transaction, world, event, reason
):
    root, fd = private_root
    log = journal.PublicationJournal(fd)
    before = (root / journal.BASENAME).read_bytes()
    try:
        with pytest.raises(ValueError, match=r"journal|private output"):
            log.append(transaction, world, event, reason)
        assert (root / journal.BASENAME).read_bytes() == before
        assert log.records == ()
        assert not log.acknowledged_in_this_generation("tx")
    finally:
        log.close()


def test_phase_identity_and_old_transaction_reservation(private_root):
    _, fd = private_root
    log = journal.PublicationJournal(fd)
    try:
        log.append("tx", "debug", "intent", "none")
        for event, world in (("intent", "debug"), ("prepared", "test")):
            with pytest.raises(ValueError, match=r"journal|private output"):
                log.append("tx", world, event, "none")
        log.append("tx", "debug", "prepared", "none")
        log.append("tx", "debug", "committed", "none")
        log.append("tx", "debug", "quarantined", "cleanup_failure")
    finally:
        log.close()
    log = journal.PublicationJournal(fd)
    try:
        with pytest.raises(ValueError, match=r"journal|private output"):
            log.append("tx", "debug", "intent", "none")
        log.append("new", "prod-" + "x" * 14, "intent", "none")
        log.append("new", "prod-" + "x" * 14, "uncertain", "io_failure")
    finally:
        log.close()


@pytest.mark.parametrize(
    "damage",
    [
        "torn",
        "duplicate",
        "unknown",
        "bool",
        "float",
        "nan",
        "phase",
        "generation",
        "whitespace",
        "oversize",
        "utf16",
    ],
)
def test_malformed_history_is_never_repaired(private_root, damage):
    root, fd = private_root
    log = journal.PublicationJournal(fd)
    log.append("tx", "test", "intent", "none")
    log.close()
    path = root / journal.BASENAME
    raw = path.read_bytes()
    data = json.loads(raw)
    if damage == "torn":
        raw = raw[:-1]
    elif damage == "duplicate":
        raw = raw.replace(b"{", b'{"version":1,', 1)
    elif damage == "unknown":
        data["extra"] = "unknown"
    elif damage in ("bool", "float", "nan"):
        data["version"] = {"bool": True, "float": 1.0, "nan": float("nan")}[damage]
    elif damage == "phase":
        raw += raw
    elif damage == "generation":
        data["event"] = "prepared"
        data["generation"] = "a" * 32
        raw += (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
    elif damage == "whitespace":
        raw = b" " + raw
    elif damage == "oversize":
        raw = b"x" * 4096 + b"\n"
    else:
        raw = raw.decode().encode("utf-16")
    if damage in ("unknown", "bool", "float", "nan"):
        raw = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(raw)
    with pytest.raises(ValueError, match=r"journal|private output"):
        journal.PublicationJournal(fd)
    assert path.read_bytes() == raw


@pytest.mark.parametrize("damage", ["root_mode", "file_mode", "symlink", "hardlink", "fifo"])
def test_private_metadata_rejection(private_root, damage):
    root, fd = private_root
    path = root / journal.BASENAME
    if damage == "root_mode":
        root.chmod(0o750)
    elif damage == "symlink":
        foreign = root / "foreign"
        foreign.write_bytes(b"foreign")
        path.symlink_to(foreign)
    elif damage == "fifo":
        os.mkfifo(path, 0o600)
    else:
        path.write_bytes(b"")
        path.chmod(0o640 if damage == "file_mode" else 0o600)
        if damage == "hardlink":
            os.link(path, root / "alias")
    with pytest.raises((ValueError, OSError)):
        journal.PublicationJournal(fd)


@pytest.mark.parametrize("damage", ["file_replace", "root_fd_rebind", "root_mode", "file_mode"])
def test_live_binding_loss_poison_refuses_foreign_write(private_root, damage):
    root, fd = private_root
    log = journal.PublicationJournal(fd)
    log.append("tx", "test", "intent", "none")
    path = root / journal.BASENAME
    if damage == "file_replace":
        path.rename(root / "old")
        path.write_bytes(b"foreign")
        path.chmod(0o600)
    elif damage == "root_fd_rebind":
        replacement = root / "replacement"
        replacement.mkdir(mode=0o700)
        other = os.open(replacement, os.O_RDONLY | os.O_DIRECTORY)
        os.dup2(other, fd)
        os.close(other)
    elif damage == "root_mode":
        root.chmod(0o750)
    else:
        path.chmod(0o640)
    before = path.read_bytes()
    try:
        with pytest.raises(ValueError, match=r"journal|private output"):
            log.append("tx", "test", "prepared", "none")
        assert not log.acknowledged_in_this_generation("tx")
        assert path.read_bytes() == before
        with pytest.raises(ValueError, match=r"journal|private output"):
            log.append("new", "test", "intent", "none")
    finally:
        log.close()


@pytest.mark.parametrize(
    "fault", ["short", "write", "file_sync", "directory_sync", "readback", "interrupt"]
)
def test_reached_append_failure_poison_and_historical_only(private_root, monkeypatch, fault):
    root, fd = private_root
    log = journal.PublicationJournal(fd)
    log.append("tx", "test", "intent", "none")
    log.append("tx", "test", "prepared", "none")
    confirmed = log.records
    original_write, original_sync, original_read = os.write, os.fsync, os.pread
    origin = (
        KeyboardInterrupt()
        if fault == "interrupt"
        else OSError(errno.EIO, "synthetic", "private-name")
    )
    reached = []
    written = []

    def write(opened, raw):
        if opened == log._fd:
            written.append(opened)
            if fault == "short":
                reached.append(fault)
                return original_write(opened, raw[:-1])
            if fault in ("write", "interrupt"):
                reached.append(fault)
                raise origin
        return original_write(opened, raw)

    def sync(opened):
        if (fault == "file_sync" and opened == log._fd) or (
            fault == "directory_sync" and opened == fd
        ):
            reached.append(fault)
            raise origin
        return original_sync(opened)

    def read(opened, size, offset):
        if fault == "readback" and opened == log._fd and written:
            reached.append(fault)
            raise origin
        return original_read(opened, size, offset)

    with monkeypatch.context() as patch:
        patch.setattr(os, "write", write)
        patch.setattr(os, "fsync", sync)
        patch.setattr(os, "pread", read)
        with pytest.raises(BaseException, match=r"journal|^$") as caught:
            log.append("tx", "test", "committed", "none")
        if fault != "short":
            assert caught.value is origin
            assert any(
                frame.name in {"write", "sync", "read"}
                for frame in __import__("traceback").extract_tb(origin.__traceback__)
            )
            if isinstance(origin, OSError):
                assert origin.errno == errno.EIO
                assert "private-name" not in str(origin)
        assert reached == [fault]
        assert log.records == confirmed
        assert not log.acknowledged_in_this_generation("tx")
        with pytest.raises(ValueError, match=r"journal|private output"):
            log.append("other", "test", "intent", "none")
        assert len(written) == 1
        with pytest.raises(BlockingIOError):
            journal.PublicationJournal(fd)
    log.close()
    check_failed_append_history(root, fd, fault)


def check_failed_append_history(root: Path, fd: int, fault: str) -> None:
    if fault == "short":
        before = (root / journal.BASENAME).read_bytes()
        with pytest.raises(ValueError, match=r"journal|private output"):
            journal.PublicationJournal(fd)
        assert (root / journal.BASENAME).read_bytes() == before
    else:
        reopened = journal.PublicationJournal(fd)
        try:
            assert not reopened.acknowledged_in_this_generation("tx")
            assert len(reopened.records) == (2 if fault in ("write", "interrupt") else 3)
        finally:
            reopened.close()


def test_append_close_thread_interleaving_is_serialized(private_root, monkeypatch):
    _, fd = private_root
    log = journal.PublicationJournal(fd)
    entered, release, closing, closed = Event(), Event(), Event(), Event()
    errors = []
    original = os.fsync

    def sync(opened):
        if opened == log._fd:
            entered.set()
            assert release.wait(5)
        return original(opened)

    def append():
        try:
            log.append("tx", "test", "intent", "none")
        except BaseException as error:
            errors.append(error)

    def close():
        closing.set()
        log.close()
        closed.set()

    monkeypatch.setattr(os, "fsync", sync)
    writer = Thread(target=append)
    closer = Thread(target=close)
    writer.start()
    assert entered.wait(5)
    closer.start()
    assert closing.wait(5)
    try:
        assert not closed.wait(0.1)
    finally:
        release.set()
        writer.join(5)
        closer.join(5)
    assert not writer.is_alive()
    assert not closer.is_alive()
    assert not errors
    assert closed.is_set()
    assert not log.acknowledged_in_this_generation("tx")


@pytest.mark.parametrize("world", ["test", "debug", "prod-a_b-x", "prod-" + "x" * 14])
def test_existing_world_tokens_preserved_exactly(private_root, world):
    _, fd = private_root
    log = journal.PublicationJournal(fd)
    try:
        log.append("tx", world, "intent", "none")
        assert log.records[0].world == world
    finally:
        log.close()


def test_constructor_interruption_cleanup_origin_and_released_close(private_root, monkeypatch):
    _, fd = private_root
    origin = KeyboardInterrupt()
    original_close = os.close
    released = []

    def read(opened, size, offset):
        raise origin

    def close(opened):
        original_close(opened)
        released.append(opened)
        raise OSError(errno.EIO, "synthetic cleanup")

    with monkeypatch.context() as patch:
        patch.setattr(os, "pread", read)
        patch.setattr(os, "close", close)
        with pytest.raises(KeyboardInterrupt) as caught:
            journal.PublicationJournal(fd)
    assert caught.value is origin
    assert len(released) == 1
    assert origin.__notes__ == ["Owned descriptor cleanup also failed; not retried."]
    assert stat.S_ISDIR(os.fstat(fd).st_mode)
    log = journal.PublicationJournal(fd)
    log.close()


def test_bounded_append_rejects_before_io(private_root, monkeypatch):
    root, fd = private_root
    log = journal.PublicationJournal(fd)

    def unexpected(*args, **kwargs):
        pytest.fail("rejected append reached a syscall")

    with monkeypatch.context() as patch:
        patch.setattr(journal, "MAX_RECORDS", 0)
        patch.setattr(os, "pread", unexpected)
        patch.setattr(os, "write", unexpected)
        with pytest.raises(ValueError, match=r"journal|private output"):
            log.append("tx", "test", "intent", "none")
    assert (root / journal.BASENAME).read_bytes() == b""
    log.close()


@pytest.mark.parametrize("release", [False, True])
def test_owned_close_fault_attempted_once_and_borrowed_root_survives(
    private_root, monkeypatch, release
):
    _, fd = private_root
    log = journal.PublicationJournal(fd)
    log.append("tx", "test", "intent", "none")
    original = os.close
    opened = log._fd
    calls = []
    origin = OSError(errno.EIO, "synthetic", "private-name")

    def close(target):
        calls.append(target)
        if release:
            original(target)
        raise origin

    with monkeypatch.context() as patch:
        patch.setattr(os, "close", close)
        with pytest.raises(OSError, match="journal") as caught:
            log.close()
        assert caught.value is origin
        log.close()
        assert not log.acknowledged_in_this_generation("tx")
    assert calls == [opened]
    assert stat.S_ISDIR(os.fstat(fd).st_mode)
    if not release:
        original(opened)


def test_acknowledgement_rejects_str_subclass(private_root):
    _, fd = private_root
    log = journal.PublicationJournal(fd)
    try:
        log.append("tx", "test", "intent", "none")
        with pytest.raises(ValueError, match="journal"):
            log.acknowledged_in_this_generation(AlteredString("tx"))
    finally:
        log.close()


def test_synthetic_wrong_uid_rejected_before_file_allocation(private_root, monkeypatch):
    root, fd = private_root
    actual = os.geteuid()
    monkeypatch.setattr(os, "geteuid", lambda: actual + 1)
    with pytest.raises(ValueError, match="private output"):
        journal.PublicationJournal(fd)
    assert not (root / journal.BASENAME).exists()
