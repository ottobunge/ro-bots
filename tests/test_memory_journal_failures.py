"""Regression cases from the independent durable-journal review."""

import json
import os
from typing import cast

import pytest

from robots.adapters.memory_journal import JsonlExperienceStore
from robots.society.memory import ExperienceNote, Memory, NoteKind, StubSummarizer


def test_invalid_note_is_rejected_before_journal_or_memory_ack(tmp_path) -> None:
    store = JsonlExperienceStore(tmp_path, "p-0")
    memory = Memory(StubSummarizer(), store=store)
    invalid = ExperienceNote(ts=1.0, kind=cast("NoteKind", "global"), text="not supported")
    try:
        with pytest.raises(ValueError, match="invalid"):
            memory.log.append(invalid)
        assert memory.log.notes() == ()
        assert store.path.read_bytes() == b""
    finally:
        memory.close()


def test_failed_sync_poison_blocks_further_reads_and_appends(tmp_path, monkeypatch) -> None:
    real_sync = os.fsync
    store = JsonlExperienceStore(tmp_path, "p-0")
    memory = Memory(StubSummarizer(), store=store)

    def fail_sync(_descriptor: int) -> None:
        msg = "sync failed"
        raise OSError(msg)

    monkeypatch.setattr("robots.adapters.memory_journal.os.fsync", fail_sync)
    try:
        with pytest.raises(OSError, match="sync failed"):
            memory.remember("chat", "uncertain first write")
        monkeypatch.setattr("robots.adapters.memory_journal.os.fsync", real_sync)
        uncertain = store.path.read_bytes()
        with pytest.raises(OSError, match="failed"):
            memory.remember("chat", "must not blindly retry")
        with pytest.raises(OSError, match="failed"):
            store.load()
        assert store.path.read_bytes() == uncertain
        assert memory.log.notes() == ()
    finally:
        memory.close()


@pytest.mark.parametrize("node", ["root", "file"])
def test_existing_readable_paths_are_rejected_before_private_writes(tmp_path, node: str) -> None:
    path = tmp_path / "p-0.jsonl"
    path.write_bytes(b"")
    path.chmod(0o600 if node == "root" else 0o644)
    if node == "root":
        tmp_path.chmod(0o755)
    with pytest.raises(PermissionError, match="private"):
        JsonlExperienceStore(tmp_path, "p-0").close()
    assert path.read_bytes() == b""


def test_symlink_ancestor_cannot_redirect_a_world_memory_root(tmp_path) -> None:
    actual = tmp_path / "other-world"
    (actual / "memory").mkdir(parents=True, mode=0o700)
    (tmp_path / "alias").symlink_to(actual, target_is_directory=True)
    with pytest.raises(OSError, match=r"directory|symbolic"):
        JsonlExperienceStore(tmp_path / "alias" / "memory", "p-0").close()
    assert not (actual / "memory" / "p-0.jsonl").exists()


def test_unterminated_record_is_not_accepted_or_concatenated(tmp_path) -> None:
    row = {"version": 1, "persona_id": "p-0", "note": {"ts": 1.0, "kind": "chat", "text": "tail"}}
    path = tmp_path / "p-0.jsonl"
    path.write_text(json.dumps(row), encoding="utf-8")
    path.chmod(0o600)
    before = path.read_bytes()
    store = JsonlExperienceStore(tmp_path, "p-0")
    try:
        with pytest.raises(ValueError, match="unterminated"):
            store.load()
        with pytest.raises(OSError, match="failed"):
            store.append(ExperienceNote(ts=2.0, kind="chat", text="must not merge with tail"))
        assert path.read_bytes() == before
    finally:
        store.close()


@pytest.mark.parametrize("version", [True, 1.0])
def test_schema_version_requires_an_integer(tmp_path, version) -> None:
    row = {"version": version, "persona_id": "p-0", "note": {"ts": 1, "kind": "chat", "text": "x"}}
    path = tmp_path / "p-0.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    path.chmod(0o600)
    store = JsonlExperienceStore(tmp_path, "p-0")
    try:
        with pytest.raises(ValueError, match="schema"):
            store.load()
    finally:
        store.close()


def test_short_write_is_not_acknowledged_and_poison_blocks_continuation(
    tmp_path, monkeypatch
) -> None:
    store = JsonlExperienceStore(tmp_path, "p-0")
    memory = Memory(StubSummarizer(), store=store)
    original = store._file.write

    def short_write(text: str) -> int:
        amount = len(text) // 2
        original(text[:amount])
        return amount

    monkeypatch.setattr(store._file, "write", short_write)
    try:
        with pytest.raises(OSError, match="incomplete"):
            memory.remember("chat", "partial write must not be acknowledged")
        assert memory.log.notes() == ()
        with pytest.raises(OSError, match="failed"):
            memory.remember("chat", "no continuation after partial write")
    finally:
        memory.close()
