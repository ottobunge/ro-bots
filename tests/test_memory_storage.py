"""Durable memory boundary: restore raw notes and write before acknowledgement."""

import json
import subprocess
import sys

import pytest

from robots.adapters.memory_journal import JsonlExperienceStore
from robots.society.memory import ExperienceNote, Memory, StubSummarizer


class NoteStoreDouble:
    def __init__(self, notes: tuple[ExperienceNote, ...] = ()) -> None:
        self.saved = list(notes)
        self.closed = False

    def load(self) -> tuple[ExperienceNote, ...]:
        return tuple(self.saved)

    def append(self, note: ExperienceNote) -> None:
        self.saved.append(note)

    def close(self) -> None:
        self.closed = True


def test_memory_restores_notes_and_persists_new_experience() -> None:
    earlier = ExperienceNote(ts=1.0, kind="party", text="Otto healed me")
    store = NoteStoreDouble((earlier,))
    memory = Memory(StubSummarizer(), store=store)
    assert memory.log.notes() == (earlier,)
    added = memory.remember("chat", "Otto returned", ts=2.0)
    restored = Memory(StubSummarizer(), store=store)
    assert restored.log.notes() == (earlier, added)
    assert "Otto returned" in "\n".join(restored.view())


@pytest.mark.parametrize("persona_id", ["p-0", "solo-1"])
def test_file_journal_restores_memory_after_reopen(tmp_path, persona_id: str) -> None:
    store = JsonlExperienceStore(tmp_path, persona_id)
    memory = Memory(StubSummarizer(), store=store)
    note = memory.remember("party", "Otto healed me,ありがとう", ts=123.5)
    memory.close()
    restored = Memory(StubSummarizer(), store=JsonlExperienceStore(tmp_path, persona_id))
    try:
        assert restored.log.notes() == (note,)
        assert "Otto healed me" in "\n".join(restored.view())
    finally:
        restored.close()


@pytest.mark.parametrize("persona_id", ["../other", "/absolute", "", ".", "a/b", "a\nother"])
def test_journal_rejects_non_identifier_paths(tmp_path, persona_id: str) -> None:
    with pytest.raises(ValueError, match="persona"):
        JsonlExperienceStore(tmp_path, persona_id)


def test_journal_rejects_second_writer_until_closed(tmp_path) -> None:
    owner = JsonlExperienceStore(tmp_path, "p-0")
    try:
        with pytest.raises(BlockingIOError):
            JsonlExperienceStore(tmp_path, "p-0")
    finally:
        owner.close()
    reopened = JsonlExperienceStore(tmp_path, "p-0")
    reopened.close()


def test_journal_file_is_owner_private(tmp_path) -> None:
    store = JsonlExperienceStore(tmp_path, "p-0")
    try:
        assert store.path.stat().st_mode & 0o777 == 0o600
    finally:
        store.close()


def test_journal_refuses_symlink_to_another_memory(tmp_path) -> None:
    other = tmp_path / "private.jsonl"
    other.write_text("do not touch", encoding="utf-8")
    (tmp_path / "p-0.jsonl").symlink_to(other)
    with pytest.raises(OSError, match="symbolic link"):
        JsonlExperienceStore(tmp_path, "p-0")
    assert other.read_text(encoding="utf-8") == "do not touch"


def test_memory_does_not_acknowledge_experience_when_fsync_fails(tmp_path, monkeypatch) -> None:
    def fail_sync(_descriptor: int) -> None:
        msg = "disk sync failed"
        raise OSError(msg)

    store = JsonlExperienceStore(tmp_path, "p-0")
    memory = Memory(StubSummarizer(), store=store)
    monkeypatch.setattr("robots.adapters.memory_journal.os.fsync", fail_sync)
    try:
        with pytest.raises(OSError, match="disk sync"):
            memory.remember("chat", "must not acknowledge this", ts=1.0)
        assert memory.log.notes() == ()
    finally:
        memory.close()


def test_journal_rejects_experiences_copied_from_other_persona(tmp_path) -> None:
    source = JsonlExperienceStore(tmp_path, "p-0")
    source.append(ExperienceNote(ts=1.0, kind="chat", text="p-0 private experience"))
    source.close()
    (tmp_path / "p-1.jsonl").write_bytes(source.path.read_bytes())
    (tmp_path / "p-1.jsonl").chmod(0o600)  # test row ownership, not public file permissions
    wrong_owner = JsonlExperienceStore(tmp_path, "p-1")
    try:
        with pytest.raises(ValueError, match="owner"):
            wrong_owner.load()
    finally:
        wrong_owner.close()


@pytest.mark.parametrize(
    "note",
    [
        {"ts": 1.0, "kind": "global", "text": "unsupported kind"},
        {"ts": "yesterday", "kind": "chat", "text": "not a timestamp"},
        {"ts": 1.0, "kind": "chat", "text": {"not": "text"}},
        {"ts": float("nan"), "kind": "chat", "text": "not finite"},
    ],
)
def test_journal_rejects_invalid_note_schema(tmp_path, note: dict) -> None:
    row = {"version": 1, "persona_id": "p-0", "note": note}
    (tmp_path / "p-0.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    (tmp_path / "p-0.jsonl").chmod(0o600)  # isolate record validation from permission checks
    store = JsonlExperienceStore(tmp_path, "p-0")
    try:
        with pytest.raises(ValueError, match="invalid"):
            store.load()
    finally:
        store.close()


def test_memory_survives_a_fresh_python_process(tmp_path) -> None:
    writer = """
from pathlib import Path
import sys
from robots.adapters.memory_journal import JsonlExperienceStore
from robots.society.memory import Memory, StubSummarizer
memory = Memory(StubSummarizer(), store=JsonlExperienceStore(Path(sys.argv[1]), 'p-0'))
memory.remember('session', 'played with Otto', ts=3.0)
memory.close()
"""
    reader = """
from pathlib import Path
import json, sys
from robots.adapters.memory_journal import JsonlExperienceStore
from robots.society.memory import Memory, StubSummarizer
memory = Memory(StubSummarizer(), store=JsonlExperienceStore(Path(sys.argv[1]), 'p-0'))
print(json.dumps([note.text for note in memory.log.notes()]))
memory.close()
"""
    subprocess.run([sys.executable, "-c", writer, str(tmp_path)], check=True, timeout=10)
    result = subprocess.run(
        [sys.executable, "-c", reader, str(tmp_path)],
        check=True,
        timeout=10,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == ["played with Otto"]


def test_journals_do_not_mix_between_world_directories(tmp_path) -> None:
    debug = JsonlExperienceStore(tmp_path / "debug", "p-0")
    debug.append(ExperienceNote(ts=1.0, kind="loot", text="debug-only item"))
    debug.close()
    test_world = JsonlExperienceStore(tmp_path / "test", "p-0")
    try:
        assert test_world.load() == ()
    finally:
        test_world.close()


def test_failed_memory_restore_releases_journal_writer_lock(tmp_path) -> None:
    row = {
        "version": 1,
        "persona_id": "other-owner",
        "note": {"ts": 1.0, "kind": "chat", "text": "wrong owner"},
    }
    (tmp_path / "p-0.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    (tmp_path / "p-0.jsonl").chmod(0o600)  # isolate record validation from permission checks
    store = JsonlExperienceStore(tmp_path, "p-0")
    with pytest.raises(ValueError, match="owner"):
        Memory(StubSummarizer(), store=store)
    retry = JsonlExperienceStore(tmp_path, "p-0")
    retry.close()
