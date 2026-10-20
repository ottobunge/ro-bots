"""Reached cleanup-control-flow regressions on private, test-owned journals."""

import errno
import os
import traceback
from pathlib import Path

import pytest

from robots.adapters import runtime_publication_journal as journal
from tests.test_runtime_publication_journal_cleanup_regressions import probe


class JournalCancelled(BaseException):
    """Non-Exception cancellation used only at the reached diagnostic seam."""


def has_frame(error: BaseException, name: str) -> bool:
    return any(frame.name == name for frame in traceback.extract_tb(error.__traceback__))


def assert_physical_state(root: Path, borrowed: int, opened: int, release: bool) -> None:
    assert probe(root) == (0 if release else 3)
    if release:
        with pytest.raises(OSError, match="Bad file descriptor") as absent:
            os.fstat(opened)
        assert absent.value.errno == errno.EBADF
    else:
        os.fstat(opened)
    os.fstat(borrowed)


def assert_constructor_snapshot(origin: BaseException, opened: int, seam: str) -> None:
    boundary = getattr(origin, "journal_cleanup_ownership", None)
    assert isinstance(boundary, journal.JournalCleanupOwnership)
    assert boundary.descriptor == opened
    assert boundary.owner_pid == os.getpid()
    assert (boundary.expected_identity is None) == (seam == "file_stat")
    assert boundary.close_attempted is True
    assert boundary.status == "unresolved"
    assert boundary.observation == "diagnostic_failed"


@pytest.mark.parametrize(
    "kind", [KeyboardInterrupt, SystemExit, GeneratorExit, JournalCancelled, OSError]
)
def test_sole_diagnostic_preserves_control_flow_after_real_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: type[BaseException]
) -> None:
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    borrowed = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    log = journal.PublicationJournal(borrowed)
    opened = log.cleanup_ownership.descriptor
    original_stat = os.fstat
    origin = kind(errno.EIO, "synthetic") if kind is OSError else kind()
    reached: list[int] = []
    caught: BaseException | None = None
    try:
        log.append("tx", "test", "intent", "none")
        assert log.acknowledged_in_this_generation("tx") is True
        original_stat(opened)
        assert probe(root) == 3

        def fault_diagnostic(fd: int) -> os.stat_result:
            if fd == opened:
                reached.append(fd)
                with pytest.raises(OSError, match="Bad file descriptor") as absent:
                    original_stat(fd)
                assert absent.value.errno == errno.EBADF
                raise origin
            return original_stat(fd)

        with monkeypatch.context() as patch:
            patch.setattr(os, "fstat", fault_diagnostic)
            try:
                log.close()  # Unpatched os.close: actual normal release first.
            except BaseException as error:
                caught = error
            log.close()
        assert reached == [opened]
        with pytest.raises(OSError, match="Bad file descriptor") as absent:
            original_stat(opened)
        assert absent.value.errno == errno.EBADF
        assert probe(root) == 0
        original_stat(borrowed)
        assert log.cleanup_ownership.status == "unresolved"
        assert log.cleanup_ownership.observation == "diagnostic_failed"
        assert log.cleanup_ownership.close_attempted is True
        assert log.acknowledged_in_this_generation("tx") is False
        with pytest.raises(ValueError, match="journal"):
            log.append("next", "test", "intent", "none")
        assert has_frame(origin, "fault_diagnostic")
        assert caught is (None if kind is OSError else origin)
    finally:
        log.close()
        os.close(borrowed)


@pytest.mark.parametrize("release", [False, True])
@pytest.mark.parametrize("primary_kind", [OSError, KeyboardInterrupt])
@pytest.mark.parametrize(
    "diagnostic_kind", [KeyboardInterrupt, SystemExit, GeneratorExit, JournalCancelled]
)
def test_primary_close_failure_survives_secondary_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    release: bool,
    primary_kind: type[BaseException],
    diagnostic_kind: type[BaseException],
) -> None:
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    borrowed = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    log = journal.PublicationJournal(borrowed)
    opened = log.cleanup_ownership.descriptor
    original_close, original_stat = os.close, os.fstat
    origin = primary_kind(errno.EIO, "synthetic") if primary_kind is OSError else primary_kind()
    secondary = diagnostic_kind()
    calls: list[int] = []
    diagnostics: list[int] = []

    def fault_close(fd: int) -> None:
        assert fd == opened
        calls.append(fd)
        if release:
            original_close(fd)
        raise origin

    def fault_diagnostic(fd: int) -> os.stat_result:
        if fd == opened:
            diagnostics.append(fd)
            raise secondary
        return original_stat(fd)

    try:
        log.append("tx", "test", "intent", "none")
        assert log.acknowledged_in_this_generation("tx") is True
        assert probe(root) == 3
        with monkeypatch.context() as patch:
            patch.setattr(os, "close", fault_close)
            patch.setattr(os, "fstat", fault_diagnostic)
            with pytest.raises(primary_kind) as caught:
                log.close()
            log.close()
        assert caught.value is origin
        assert calls == diagnostics == [opened]
        assert has_frame(origin, "fault_close")
        assert has_frame(secondary, "fault_diagnostic")
        if isinstance(origin, OSError):
            assert origin.errno == errno.EIO
        assert log.cleanup_ownership.status == "unresolved"
        assert log.cleanup_ownership.observation == "diagnostic_failed"
        assert log.acknowledged_in_this_generation("tx") is False
        assert_physical_state(root, borrowed, opened, release)
    finally:
        if not release:
            original_close(opened)  # Disposal of this known test allocation only.
        original_close(borrowed)


@pytest.mark.parametrize("kind", [KeyboardInterrupt, SystemExit])
def test_process_identity_interrupt_precedes_writer_allocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: type[BaseException]
) -> None:
    control = tmp_path / "control"
    control.mkdir(mode=0o700)
    control_root = os.open(control, os.O_RDONLY | os.O_DIRECTORY)
    try:
        positive = journal.PublicationJournal(control_root)
        positive.append("tx", "test", "intent", "none")
        assert positive.acknowledged_in_this_generation("tx") is True
        assert probe(control) == 3
        positive.close()
        assert probe(control) == 0
    finally:
        os.close(control_root)
    root = tmp_path / "fault"
    root.mkdir(mode=0o700)
    borrowed = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    original_open, original_close = os.open, os.close
    allocated: list[int] = []
    reached: list[str] = []
    origin = kind()

    def observe_open(path: str, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        fd = original_open(path, flags, mode, dir_fd=dir_fd)
        if path == journal.BASENAME and dir_fd == borrowed:
            os.fstat(fd)
            allocated.append(fd)
        return fd

    def fault_getpid() -> int:
        reached.append("getpid")
        raise origin

    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "open", observe_open)
            patch.setattr(os, "getpid", fault_getpid)
            with pytest.raises(kind) as caught:
                journal.PublicationJournal(borrowed)
        assert caught.value is origin
        assert reached == ["getpid"]
        assert has_frame(origin, "fault_getpid")
        os.fstat(borrowed)
        assert allocated == [], "process identity was fetched after a real writer allocation"
        assert not (root / journal.BASENAME).exists()
        assert getattr(origin, "journal_cleanup_ownership", None) is None
    finally:
        # Only an old-source leaked allocation captured by this delegating observer.
        for fd in allocated:
            original_close(fd)
        original_close(borrowed)


@pytest.mark.parametrize("seam", ["file_stat", "pread"])
@pytest.mark.parametrize("primary_kind", [OSError, KeyboardInterrupt])
@pytest.mark.parametrize("release", [False, True])
@pytest.mark.parametrize("diagnostic_kind", [OSError, SystemExit])
def test_allocated_constructor_keeps_first_origin_and_diagnostic_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    seam: str,
    primary_kind: type[BaseException],
    release: bool,
    diagnostic_kind: type[BaseException],
) -> None:
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    borrowed = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    original_close, original_stat = os.close, os.fstat
    origin = (
        primary_kind(errno.EIO, "private", "private-name")
        if primary_kind is OSError
        else primary_kind()
    )
    diagnostic = (
        diagnostic_kind(errno.EIO, "synthetic") if diagnostic_kind is OSError else diagnostic_kind()
    )
    reached: list[str] = []
    calls: list[int] = []

    def fault_stat(fd: int) -> os.stat_result:
        if fd != borrowed:
            if reached:
                reached.append("diagnostic")
                raise diagnostic
            if seam == "file_stat":
                original_stat(fd)
                reached.append(seam)
                raise origin
        return original_stat(fd)

    def fault_read(fd: int, size: int, offset: int) -> bytes:
        original_stat(fd)
        reached.append("pread")
        raise origin

    def fault_close(fd: int) -> None:
        calls.append(fd)
        if release:
            original_close(fd)
        raise GeneratorExit()

    try:
        with monkeypatch.context() as patch:
            patch.setattr(os, "fstat", fault_stat)
            patch.setattr(os, "pread", fault_read)
            patch.setattr(os, "close", fault_close)
            with pytest.raises(primary_kind) as caught:
                journal.PublicationJournal(borrowed)
        assert caught.value is origin
        assert reached == [seam, "diagnostic"]
        assert len(calls) == 1
        assert has_frame(origin, "fault_stat" if seam == "file_stat" else "fault_read")
        assert_constructor_snapshot(origin, calls[0], seam)
        if isinstance(origin, OSError):
            assert origin.errno == errno.EIO
            assert origin.filename is None
        assert_physical_state(root, borrowed, calls[0], release)
    finally:
        if calls and not release:
            original_close(calls[0])  # Known synthetic allocation, not recovery.
        original_close(borrowed)
