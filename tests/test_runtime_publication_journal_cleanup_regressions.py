"""Cleanup observations are not descriptor retry authority; synthetic roots only."""

import errno
import os
import select
import subprocess
import sys
import traceback
from pathlib import Path

import pytest

from robots.adapters import runtime_publication_journal as journal

PROBE = """
import os, sys
from robots.adapters.runtime_publication_journal import PublicationJournal
root = os.open(sys.argv[1], os.O_RDONLY | os.O_DIRECTORY)
try:
    try:
        log = PublicationJournal(root)
    except BlockingIOError:
        sys.exit(3)
    log.close()
finally:
    os.close(root)
"""


def probe(root: Path) -> int:
    result = subprocess.run(
        [sys.executable, "-c", PROBE, str(root)],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode in (0, 3), result.stderr.decode()
    return result.returncode


@pytest.mark.parametrize("release", [False, True])
@pytest.mark.parametrize("kind", [OSError, KeyboardInterrupt])
def test_close_retains_explicit_cleanup_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, release: bool, kind: type[BaseException]
) -> None:
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    borrowed = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    log = journal.PublicationJournal(borrowed)
    log.append("tx", "test", "intent", "none")
    assert log.acknowledged_in_this_generation("tx")
    assert probe(root) == 3
    opened = log._fd
    original_close = os.close
    origin = kind(errno.EIO, "synthetic") if kind is OSError else kind()
    calls: list[int] = []

    def fault_close(fd: int) -> None:
        assert fd == opened
        calls.append(fd)
        if release:
            original_close(fd)
        raise origin

    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "close", fault_close)
            with pytest.raises(kind) as caught:
                log.close()
            assert caught.value is origin
            log.close()
        assert calls == [opened]
        if release:
            with pytest.raises(OSError, match="Bad file descriptor") as missing:
                os.fstat(opened)
            assert missing.value.errno == errno.EBADF
        else:
            os.fstat(opened)
        assert probe(root) == (0 if release else 3)
        boundary = getattr(log, "cleanup_ownership", None)
        assert boundary is not None, "live cleanup owner/status disappeared after one attempt"
        assert isinstance(boundary, journal.JournalCleanupOwnership)
        assert boundary.owner_pid == os.getpid()
        assert boundary.descriptor == opened
        assert boundary.close_attempted is True
        assert boundary.status == ("released_observed" if release else "unresolved")
        assert boundary.observation == ("descriptor_absent" if release else "descriptor_present")
        assert log.acknowledged_in_this_generation("tx") is False
        with pytest.raises(ValueError, match="journal"):
            log.append("next", "test", "intent", "none")
        assert any(
            frame.name == "fault_close" for frame in traceback.extract_tb(origin.__traceback__)
        )
        os.fstat(borrowed)
    finally:
        # Harness disposal only, NOT production recovery of the unresolved owner.
        if not release:
            original_close(opened)
        original_close(borrowed)


@pytest.mark.parametrize("release", [False, True])
@pytest.mark.parametrize("interrupted", [False, True])
def test_constructor_retains_owner_on_original_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, release: bool, interrupted: bool
) -> None:
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    borrowed = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    journal.PublicationJournal(borrowed).close()
    assert probe(root) == 0
    origin: BaseException = KeyboardInterrupt() if interrupted else OSError(errno.EIO, "synthetic")
    secondary: BaseException = (
        OSError(errno.EIO, "synthetic") if interrupted else KeyboardInterrupt()
    )
    original_close = os.close
    calls: list[int] = []
    reached: list[str] = []

    def fault_read(fd: int, size: int, offset: int) -> bytes:
        os.fstat(fd)
        reached.append("pread")
        raise origin

    def fault_close(fd: int) -> None:
        calls.append(fd)
        if release:
            original_close(fd)
        raise secondary

    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "pread", fault_read)
            patch.setattr(os, "close", fault_close)
            with pytest.raises(type(origin)) as caught:
                journal.PublicationJournal(borrowed)
        assert caught.value is origin
        assert reached == ["pread"]
        assert len(calls) == 1
        assert probe(root) == (0 if release else 3)
        if not release:
            os.fstat(calls[0])
        boundary = getattr(origin, "journal_cleanup_ownership", None)
        assert boundary is not None, "constructor lost supported ownership handoff"
        assert isinstance(boundary, journal.JournalCleanupOwnership)
        assert boundary.owner_pid == os.getpid()
        assert boundary.descriptor == calls[0]
        assert boundary.close_attempted
        assert boundary.status == ("released_observed" if release else "unresolved")
        assert boundary.expected_identity is not None
        assert any(
            frame.name == "fault_read" for frame in traceback.extract_tb(origin.__traceback__)
        )
        if isinstance(origin, OSError):
            assert origin.errno == errno.EIO
            assert origin.filename is None
        assert all("synthetic" not in note for note in origin.__notes__)
        os.fstat(borrowed)
    finally:
        # Test-only disposal after the lock assertions, not the supported handoff.
        if calls and not release:
            original_close(calls[0])
        original_close(borrowed)


@pytest.mark.parametrize("diagnostic", [False, True])
def test_failed_constructor_before_identity_keeps_conservative_handoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, diagnostic: bool
) -> None:
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    borrowed = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    original_stat = os.fstat
    original_close = os.close
    calls: list[int] = []
    origin = OSError(errno.EIO, "synthetic", "private-name")
    visits = 0

    def fault_stat(fd: int) -> os.stat_result:
        nonlocal visits
        if fd != borrowed:
            visits += 1
            if visits == 1:
                raise origin
            if diagnostic:
                raise SystemExit()
        return original_stat(fd)

    def fault_close(fd: int) -> None:
        calls.append(fd)
        raise KeyboardInterrupt()

    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "fstat", fault_stat)
            patch.setattr(os, "close", fault_close)
            with pytest.raises(OSError, match="journal") as caught:
                journal.PublicationJournal(borrowed)
        assert caught.value is origin
        assert origin.errno == errno.EIO
        assert origin.filename is None
        assert visits == 2
        assert len(calls) == 1
        original_stat(calls[0])
        assert probe(root) == 3
        boundary = getattr(origin, "journal_cleanup_ownership", None)
        assert isinstance(boundary, journal.JournalCleanupOwnership)
        assert boundary.expected_identity is None
        assert boundary.status == "unresolved"
        assert boundary.observation == ("diagnostic_failed" if diagnostic else "identity_unknown")
        assert any(
            frame.name == "fault_stat" for frame in traceback.extract_tb(origin.__traceback__)
        )
        assert all("private-name" not in note for note in origin.__notes__)
        original_stat(borrowed)
    finally:
        if calls:
            original_close(calls[0])
        original_close(borrowed)


@pytest.mark.parametrize("diagnostic", [OSError, GeneratorExit])
def test_close_diagnostic_failure_does_not_mask_release_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, diagnostic: type[BaseException]
) -> None:
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    borrowed = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    log = journal.PublicationJournal(borrowed)
    opened = log._fd
    original_close = os.close
    original_stat = os.fstat
    origin = KeyboardInterrupt()
    calls: list[int] = []

    def fault_close(fd: int) -> None:
        calls.append(fd)
        original_close(fd)
        raise origin

    def fault_stat(fd: int) -> os.stat_result:
        if fd == opened:
            raise diagnostic()
        return original_stat(fd)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "close", fault_close)
            patch.setattr(os, "fstat", fault_stat)
            with pytest.raises(KeyboardInterrupt) as caught:
                log.close()
            log.close()
        assert caught.value is origin
        assert calls == [opened]
        assert log.cleanup_ownership.status == "unresolved"
        assert log.cleanup_ownership.observation == "diagnostic_failed"
        assert probe(root) == 0  # Actual release is separate from unavailable observation.
        original_stat(borrowed)
    finally:
        original_close(borrowed)


@pytest.mark.parametrize("same_inode", [False, True])
def test_reused_descriptor_never_grants_retry_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, same_inode: bool
) -> None:
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    borrowed = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    log = journal.PublicationJournal(borrowed)
    opened = log._fd
    original_close = os.close
    replacement: list[int] = []
    initial = log.cleanup_ownership
    assert initial.status == "active"
    assert initial.close_attempted is False

    def replace_descriptor(fd: int) -> None:
        original_close(fd)
        if same_inode:
            replacement.append(os.open(journal.BASENAME, os.O_RDWR, dir_fd=borrowed))
        else:
            replacement.append(os.open(root, os.O_RDONLY | os.O_DIRECTORY))
        assert replacement == [opened]

    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "close", replace_descriptor)
            log.close()
            log.close()
        assert log.cleanup_ownership.status == "unresolved"
        assert log.cleanup_ownership.observation == (
            "descriptor_present" if same_inode else "descriptor_reused"
        )
        os.fstat(replacement[0])
        assert probe(root) == 0
    finally:
        for fd in replacement:
            original_close(fd)
        original_close(borrowed)


WORKER = """
import os, sys
from robots.adapters.runtime_publication_journal import PublicationJournal
root = os.open(sys.argv[1], os.O_RDONLY | os.O_DIRECTORY)
log = PublicationJournal(root)
log.append('tx', 'test', 'intent', 'none')
assert log.acknowledged_in_this_generation('tx')
constructor = sys.argv[2] == 'constructor'
if constructor:
    log.close()
def fault_close(fd):
    raise KeyboardInterrupt()
def fault_read(fd, size, offset):
    raise OSError(5, 'synthetic')
os.close = fault_close
if constructor:
    os.pread = fault_read
    try:
        PublicationJournal(root)
    except OSError as error:
        pending = error.journal_cleanup_ownership
else:
    try:
        log.close()
    except KeyboardInterrupt:
        pending = log.cleanup_ownership
assert pending.owner_pid == os.getpid()
assert pending.status == 'unresolved'
assert pending.close_attempted
os.fstat(pending.descriptor)
print('unresolved', flush=True)
sys.stdin.readline()
# No manual close: the kernel closes descriptors when this owned worker exits.
"""


@pytest.mark.parametrize("route", ["close", "constructor"])
def test_owned_process_teardown_releases_unresolved_writer(tmp_path: Path, route: str) -> None:
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    worker = subprocess.Popen(
        [sys.executable, "-u", "-c", WORKER, str(root), route],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert worker.stdout is not None
        ready, _, _ = select.select([worker.stdout], [], [], 10)
        assert ready, "owned worker did not reach unresolved handoff"
        assert worker.stdout.readline().strip() == "unresolved"
        assert worker.poll() is None
        assert probe(root) == 3
        _, errors = worker.communicate("exit\n", timeout=10)
        assert worker.returncode == 0, errors
        assert probe(root) == 0
    finally:
        if worker.poll() is None:
            worker.terminate()  # Only the synthetic test-owned child.
            worker.communicate(timeout=10)
