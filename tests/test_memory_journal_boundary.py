"""Filesystem and syscall boundaries, not a power-loss simulation."""

import fcntl
import os
from pathlib import Path

import pytest

from robots.adapters import memory_journal
from robots.adapters.memory_journal import JsonlExperienceStore
from robots.society.memory import ExperienceNote


def test_new_ancestor_and_journal_entries_are_synced_before_ack(tmp_path, monkeypatch) -> None:
    root = tmp_path / "world" / "memory"
    events: list[tuple[str, Path]] = []
    real_mkdir, real_sync = os.mkdir, os.fsync

    def record_mkdir(path, mode=0o777, *, dir_fd=None) -> None:
        real_mkdir(path, mode, dir_fd=dir_fd)
        parent = Path(os.readlink(f"/proc/self/fd/{dir_fd}"))
        events.append(("mkdir", parent / path))

    def record_sync(descriptor: int) -> None:
        target = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
        real_sync(descriptor)
        events.append(("sync", target))

    monkeypatch.setattr("robots.adapters.memory_journal.os.mkdir", record_mkdir)
    monkeypatch.setattr("robots.adapters.memory_journal.os.fsync", record_sync)
    store = JsonlExperienceStore(root, "p-0")
    try:
        store.append(ExperienceNote(ts=1.0, kind="chat", text="acknowledged"))
        events.append(("ack", store.path))
        for directory in (tmp_path / "world", root):
            created = events.index(("mkdir", directory))
            synced = events.index(("sync", directory.parent), created + 1)
            assert created < synced < events.index(("ack", store.path))
        assert ("sync", root) in events  # persists the journal's directory entry
        assert events.index(("sync", store.path)) < events.index(("ack", store.path))
        assert store.load() == (ExperienceNote(ts=1.0, kind="chat", text="acknowledged"),)
    finally:
        store.close()


def _assert_closed(descriptors: list[int]) -> None:
    for descriptor in descriptors:
        with pytest.raises(OSError, match="Bad file descriptor"):
            os.fstat(descriptor)


@pytest.mark.parametrize("converted", [False, True])
def test_failed_conversion_preserves_exception_and_releases_fds_and_lock(
    tmp_path, monkeypatch, converted: bool
) -> None:
    real_open, real_fdopen = os.open, os.fdopen
    descriptors: list[int] = []
    origin = RuntimeError("conversion failed")

    def record_open(*args, **kwargs) -> int:
        descriptor = real_open(*args, **kwargs)
        descriptors.append(descriptor)
        return descriptor

    def fail_conversion(descriptor: int, *args, **kwargs):
        if converted:
            real_fdopen(descriptor, *args, **kwargs).close()
        raise origin

    with monkeypatch.context() as patch:
        patch.setattr("robots.adapters.memory_journal.os.open", record_open)
        patch.setattr("robots.adapters.memory_journal.os.fdopen", fail_conversion)
        with pytest.raises(RuntimeError, match="conversion failed") as caught:
            JsonlExperienceStore(tmp_path, "p-0")
        assert caught.value is origin
        _assert_closed(descriptors)
    reopened = JsonlExperienceStore(tmp_path, "p-0")
    try:
        reopened.append(ExperienceNote(ts=1.0, kind="chat", text="released lock"))
    finally:
        reopened.close()


@pytest.mark.parametrize("boundary", ["ancestor_sync", "journal_directory_sync"])
def test_failed_directory_sync_preserves_origin_despite_cleanup_error(
    tmp_path, monkeypatch, boundary: str
) -> None:
    root = tmp_path / "world" / "memory"
    target = tmp_path if boundary == "ancestor_sync" else root
    real_open, real_sync, real_close = os.open, os.fsync, os.close
    descriptors: list[int] = []
    origin = OSError("original directory sync failure")
    failed = False

    def record_open(*args, **kwargs) -> int:
        descriptor = real_open(*args, **kwargs)
        descriptors.append(descriptor)
        return descriptor

    def fail_sync(descriptor: int) -> None:
        nonlocal failed
        if Path(os.readlink(f"/proc/self/fd/{descriptor}")) == target:
            failed = True
            raise origin
        real_sync(descriptor)

    def fail_cleanup(descriptor: int) -> None:
        real_close(descriptor)
        if failed:
            msg = "secondary close failure"
            raise OSError(msg)

    with monkeypatch.context() as patch:
        patch.setattr("robots.adapters.memory_journal.os.open", record_open)
        patch.setattr("robots.adapters.memory_journal.os.fsync", fail_sync)
        patch.setattr("robots.adapters.memory_journal.os.close", fail_cleanup)
        with pytest.raises(OSError, match="original directory sync failure") as caught:
            JsonlExperienceStore(root, "p-0")
        assert caught.value is origin
        assert failed
        _assert_closed(descriptors)
    reopened = JsonlExperienceStore(root, "p-0")
    reopened.close()


def test_retry_syncs_ancestor_entry_left_by_failed_constructor(tmp_path, monkeypatch) -> None:
    root = tmp_path / "world" / "memory"
    real_sync = os.fsync
    origin = OSError("ancestor entry not yet synced")

    def fail_parent_sync(descriptor: int) -> None:
        if Path(os.readlink(f"/proc/self/fd/{descriptor}")) == tmp_path:
            raise origin
        real_sync(descriptor)

    with monkeypatch.context() as patch:
        patch.setattr("robots.adapters.memory_journal.os.fsync", fail_parent_sync)
        with pytest.raises(OSError, match="ancestor entry not yet synced") as caught:
            JsonlExperienceStore(root, "p-0")
        assert caught.value is origin
    assert (tmp_path / "world").is_dir()
    assert not (root / "p-0.jsonl").exists()
    synced: list[Path] = []

    def record_sync(descriptor: int) -> None:
        real_sync(descriptor)
        synced.append(Path(os.readlink(f"/proc/self/fd/{descriptor}")))

    with monkeypatch.context() as patch:
        patch.setattr("robots.adapters.memory_journal.os.fsync", record_sync)
        store = JsonlExperienceStore(root, "p-0")
        try:
            store.append(ExperienceNote(ts=1.0, kind="chat", text="safe explicit reopen"))
            assert tmp_path in synced
            assert synced.index(tmp_path) < synced.index(store.path)
        finally:
            store.close()


@pytest.mark.parametrize("cleanup_error", [False, True])
def test_close_failure_releases_owned_descriptors_and_preserves_origin(
    tmp_path, monkeypatch, cleanup_error: bool
) -> None:
    store = JsonlExperienceStore(tmp_path, "p-0")
    descriptors = [store._file.fileno(), store._directory_fd]
    real_file_close, real_close = store._file.close, os.close
    origin = RuntimeError("original text close failure")

    def fail_text_close() -> None:
        real_file_close()
        raise origin

    def close_descriptor(descriptor: int) -> None:
        real_close(descriptor)
        if cleanup_error:
            msg = "secondary descriptor close failure"
            raise OSError(msg)

    with monkeypatch.context() as patch:
        patch.setattr(store._file, "close", fail_text_close)
        patch.setattr("robots.adapters.memory_journal.os.close", close_descriptor)
        with pytest.raises(RuntimeError, match="original text close failure") as caught:
            store.close()
        assert caught.value is origin
        _assert_closed(descriptors)
    store.close()  # repeated cleanup must not close a reused descriptor
    reopened = JsonlExperienceStore(tmp_path, "p-0")
    try:
        store.close()
        assert reopened.load() == ()
    finally:
        reopened.close()


@pytest.mark.parametrize("boundary", ["file_open", "file_validation", "lock"])
def test_constructor_failure_releases_descriptors_and_writer_lock(
    tmp_path, monkeypatch, boundary: str
) -> None:
    real_open = os.open
    real_private = memory_journal._require_private
    real_flock = fcntl.flock
    descriptors: list[int] = []
    origin = OSError("injected constructor failure")

    def record_open(path, *args, **kwargs) -> int:
        if boundary == "file_open" and path == "p-0.jsonl":
            raise origin
        descriptor = real_open(path, *args, **kwargs)
        descriptors.append(descriptor)
        return descriptor

    def validate(info, *, directory=False) -> None:
        real_private(info, directory=directory)
        if boundary == "file_validation" and not directory:
            raise origin

    def lock(descriptor: int, operation: int) -> None:
        real_flock(descriptor, operation)
        if boundary == "lock":
            raise origin

    with monkeypatch.context() as patch:
        patch.setattr("robots.adapters.memory_journal.os.open", record_open)
        patch.setattr("robots.adapters.memory_journal._require_private", validate)
        patch.setattr("robots.adapters.memory_journal.fcntl.flock", lock)
        with pytest.raises(OSError, match="injected constructor failure") as caught:
            JsonlExperienceStore(tmp_path, "p-0")
        assert caught.value is origin
        _assert_closed(descriptors)
    reopened = JsonlExperienceStore(tmp_path, "p-0")
    reopened.close()


def test_append_sync_failure_keeps_lock_until_explicit_close(tmp_path, monkeypatch) -> None:
    store = JsonlExperienceStore(tmp_path, "p-0")
    descriptors = [store._file.fileno(), store._directory_fd]
    origin = OSError("original note sync failure")

    def fail_sync(_descriptor: int) -> None:
        raise origin

    try:
        with monkeypatch.context() as patch:
            patch.setattr("robots.adapters.memory_journal.os.fsync", fail_sync)
            with pytest.raises(OSError, match="original note sync failure") as caught:
                store.append(ExperienceNote(ts=1.0, kind="chat", text="uncertain outcome"))
            assert caught.value is origin
        uncertain = store.path.read_bytes()
        with pytest.raises(OSError, match="failed"):
            store.append(ExperienceNote(ts=2.0, kind="chat", text="no blind retry"))
        with pytest.raises(OSError, match="failed"):
            store.load()
        assert store.path.read_bytes() == uncertain
        with pytest.raises(BlockingIOError):
            JsonlExperienceStore(tmp_path, "p-0")
    finally:
        store.close()
    _assert_closed(descriptors)
    reopened = JsonlExperienceStore(tmp_path, "p-0")
    reopened.close()


def test_existing_hardlinked_journal_is_rejected_without_writing(tmp_path) -> None:
    path = tmp_path / "p-0.jsonl"
    path.touch(mode=0o600)
    alias = tmp_path / "other-persona.jsonl"
    os.link(path, alias)
    assert path.stat().st_nlink == 2
    with pytest.raises(PermissionError, match="link"):
        JsonlExperienceStore(tmp_path, "p-0").close()
    assert path.read_bytes() == alias.read_bytes() == b""
    alias.unlink()
    reopened = JsonlExperienceStore(tmp_path, "p-0")
    reopened.close()


def test_link_added_to_open_journal_is_rejected_before_append(tmp_path) -> None:
    store = JsonlExperienceStore(tmp_path, "p-0")
    alias = tmp_path / "other-persona.jsonl"
    os.link(store.path, alias)
    try:
        with pytest.raises(PermissionError, match="link"):
            store.append(ExperienceNote(ts=1.0, kind="chat", text="must not share"))
        assert store.path.read_bytes() == alias.read_bytes() == b""
        alias.unlink()
        with pytest.raises(OSError, match="failed"):
            store.append(ExperienceNote(ts=2.0, kind="chat", text="no implicit retry"))
        with pytest.raises(OSError, match="failed"):
            store.load()
    finally:
        store.close()
