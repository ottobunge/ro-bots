"""Offline private NPC journal append/replay through the existing store."""

import json
import subprocess
import sys
from pathlib import Path
from typing import cast, get_args

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.memory_journal import JsonlExperienceStore
from robots.app.brain import EventDrivenBrain
from robots.domain.events import NpcDialogueReceived
from robots.domain.model import Goal
from robots.society.memory import ExperienceNote, Memory, NoteKind, StubSummarizer
from tests.test_native_npc_guidance import MenuDecision, dialog, opened


def test_npc_dialogue_appends_and_replays_in_fresh_store_and_process(tmp_path: Path) -> None:
    note = ExperienceNote(123.5, "npc_dialogue", "received NPC#321: Ask trainer.")
    store = JsonlExperienceStore(tmp_path / "world", "p-0")
    try:
        try:
            store.append(note)
        except ValueError as error:
            pytest.fail(f"Dedicated received NPC kind rejected by durable append: {error}")
    finally:
        store.close()
    memory = Memory(
        StubSummarizer(max_chars=1000), store=JsonlExperienceStore(tmp_path / "world", "p-0")
    )
    try:
        assert memory.log.notes() == (note,)
        assert "npc_dialogue: received NPC#321: Ask trainer." in "\n".join(memory.view())
    finally:
        memory.close()
    reader = """
from pathlib import Path
import json, sys
from dataclasses import asdict
from robots.adapters.memory_journal import JsonlExperienceStore
store = JsonlExperienceStore(Path(sys.argv[1]), 'p-0')
try:
    print(json.dumps([asdict(note) for note in store.load()]))
finally:
    store.close()
"""
    result = subprocess.run(
        [sys.executable, "-c", reader, str(tmp_path / "world")],
        check=True,
        timeout=10,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == [{"ts": 123.5, "kind": "npc_dialogue", "text": note.text}]


def test_received_brain_pages_use_dedicated_private_durable_kind(tmp_path: Path) -> None:
    root = tmp_path / "world"
    store = JsonlExperienceStore(root, "p-0")
    memory = Memory(StubSummarizer(max_chars=1000), store=store)
    legacy = memory.remember("other", "received NPC#99: Old instruction stays other.", ts=10.0)
    prefix = store.path.read_bytes()
    peer = Memory(StubSummarizer(), store=JsonlExperienceStore(root, "p-1"))
    model = MenuDecision()
    brain = EventDrivenBrain(model, StaticChatGenerator(), memory=memory)
    wire, client = opened()
    wire.add(
        dialog(0xB4, "Guide: speak to the trainer."),
        dialog(0xB4, "Then return to me."),
        dialog(0xB7, "Help::Training"),
    )
    state = client.build_native_state(Goal.GRIND)
    event = next(e for e in client.drain_native_events() if isinstance(e, NpcDialogueReceived))
    try:
        brain.handle_event(state, event)
        notes = memory.log.notes()
        assert [note.kind for note in notes] == ["other", "npc_dialogue", "npc_dialogue"]
        assert notes[0] == legacy
        assert [note.ts for note in notes] == [10.0, 0.0, 0.0]
        for index, text in enumerate(("Guide: speak to the trainer.", "Then return to me."), 1):
            assert notes[index].text.endswith(text)
            assert "received NPC#321 epoch=1 map=prontera" in notes[index].text
            assert f"page={index} UI-seq=" in notes[index].text
            assert "opening=" in notes[index].text
        view = model.requests[-1]["state"]["memory_view"]
        assert "npc_dialogue:" in view
        assert "Guide: speak to the trainer." in view
        assert "Then return to me." in view
        assert "other: received NPC#99: Old instruction stays other." in view
        assert not peer.view()
        assert brain.handle_event(state, event).actions == ()
        assert memory.log.notes() == notes
        rows = [json.loads(line) for line in store.path.read_text().splitlines()]
        assert [row["note"]["kind"] for row in rows] == ["other", "npc_dialogue", "npc_dialogue"]
        assert all(row["persona_id"] == "p-0" and row["version"] == 1 for row in rows)
        assert store.path.read_bytes().startswith(prefix)
        assert root.stat().st_mode & 0o777 == 0o700
        assert store.path.stat().st_mode & 0o777 == 0o600
    finally:
        memory.close()
        peer.close()
    restored = Memory(StubSummarizer(max_chars=1000), store=JsonlExperienceStore(root, "p-0"))
    try:
        assert restored.log.notes() == notes
        assert "npc_dialogue:" in "\n".join(restored.view())
        assert "Old instruction stays other." in "\n".join(restored.view())
    finally:
        restored.close()


def test_all_old_kinds_replay_unchanged_without_rewriting(tmp_path: Path) -> None:
    old_kinds = ("chat", "combat", "party", "loot", "quest", "session", "reputation", "other")
    assert get_args(NoteKind) == (*old_kinds, "npc_dialogue")
    store = JsonlExperienceStore(tmp_path, "p-0")
    notes = tuple(ExperienceNote(12.5, cast("NoteKind", kind), f"old {kind}") for kind in old_kinds)
    try:
        for note in notes:
            store.append(note)
    finally:
        store.close()
    original = store.path.read_bytes()
    restored = JsonlExperienceStore(tmp_path, "p-0")
    try:
        assert restored.load() == notes
        assert restored.path.read_bytes() == original
    finally:
        restored.close()


def test_arbitrary_unknown_kind_append_still_rejects_without_write(tmp_path: Path) -> None:
    store = JsonlExperienceStore(tmp_path, "p-0")
    try:
        store.append(ExperienceNote(1.0, "npc_dialogue", "received instruction"))
        original = store.path.read_bytes()
        with pytest.raises(ValueError, match="invalid journal note values"):
            store.append(ExperienceNote(2.0, cast("NoteKind", "unknown_npc_kind"), "invalid"))
        assert store.path.read_bytes() == original
        assert len(store.load()) == 1
    finally:
        store.close()


@pytest.mark.parametrize("corruption", ["unknown_kind", "torn_tail"])
def test_corrupt_npc_journal_is_not_erased(tmp_path: Path, corruption: str) -> None:
    store = JsonlExperienceStore(tmp_path, "p-0")
    store.append(ExperienceNote(1.0, "npc_dialogue", "received instruction"))
    store.close()
    original = store.path.read_bytes()
    corrupted = (
        original.replace(b'"npc_dialogue"', b'"unknown_npc_kind"')
        if corruption == "unknown_kind"
        else original[:-1]
    )
    store.path.write_bytes(corrupted)
    with pytest.raises(ValueError, match=r"invalid journal note values|unterminated journal tail"):
        Memory(StubSummarizer(), store=JsonlExperienceStore(tmp_path, "p-0"))
    assert store.path.read_bytes() == corrupted
    retry = JsonlExperienceStore(tmp_path, "p-0")
    retry.close()  # failed restore released the actual writer lock


def test_npc_journal_refuses_foreign_persona_and_world_alias(tmp_path: Path) -> None:
    root = tmp_path / "world-a"
    store = JsonlExperienceStore(root, "p-0")
    store.append(ExperienceNote(1.0, "npc_dialogue", "private received instruction"))
    store.close()
    original = store.path.read_bytes()
    foreign = root / "p-1.jsonl"
    foreign.write_bytes(original)
    foreign.chmod(0o600)
    with pytest.raises(ValueError, match="owner"):
        Memory(StubSummarizer(), store=JsonlExperienceStore(root, "p-1"))
    assert foreign.read_bytes() == original
    (tmp_path / "world-b").symlink_to(root, target_is_directory=True)
    with pytest.raises(OSError, match=r"Not a directory|symbolic link"):
        JsonlExperienceStore(tmp_path / "world-b", "p-0")
    other = Memory(StubSummarizer(), store=JsonlExperienceStore(tmp_path / "world-c", "p-0"))
    try:
        assert not other.view()
        assert store.path.read_bytes() == original
    finally:
        other.close()
