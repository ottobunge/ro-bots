"""Offline source-shaped short-page contracts; no native sessions or rewards."""

import struct
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.memory_journal import JsonlExperienceStore
from robots.app import agent_runtime
from robots.app.brain import EventDrivenBrain
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import Attack, NpcClose, NpcNext, NpcSelect, TalkToNpc
from robots.domain.events import NpcDialogueReceived
from robots.domain.model import Goal
from robots.society.memory import ExperienceNote, Memory, StubSummarizer
from tests.test_native_npc_close_framing import packet_module
from tests.test_native_npc_guidance import dialog, field_map, npc_wire, opened
from tests.test_playing_runtime import monster


def native_opened() -> tuple[Any, PlayingClient]:
    """Real BotClient dispatcher/snapshot with an offline send sink only."""
    factory: Any = cast("Any", agent_runtime)._BotClient
    assert factory is not None
    wire = factory("offline", "unused", "WireNovice", verbose=False)
    baseline = npc_wire()
    for name in (
        "aid",
        "gid",
        "native_epoch",
        "selection_epoch",
        "map_epoch",
        "class_fresh",
        "selected_character_snapshot",
        "status_params",
        "running",
        "connected_map",
    ):
        setattr(wire, name, getattr(baseline, name))
    wire.sent = []
    wire.sock = SimpleNamespace(sendall=wire.sent.append)
    wire.rx_thread = SimpleNamespace(is_alive=lambda: True)

    def receive(*raws: bytes) -> None:
        for raw in raws:
            wire._dispatch(int.from_bytes(raw[:2], "little"), raw)

    wire.add = receive
    receive(*(frame[3] for frame in baseline.frames))
    assert wire.sent == [b"\x7d\x00"]
    wire.sent.clear()
    client = PlayingClient(wire, monotonic=lambda: 0.0)
    client.perform_native(TalkToNpc(321))
    return wire, client


def receive_brain(wire: Any, client: PlayingClient, brain: EventDrivenBrain, *raws: bytes):
    wire.add(*raws)
    state = client.build_native_state(Goal.GRIND)
    events = client.drain_native_events()
    for event in events:
        brain.handle_event(state, event)
    return state, events


def test_twenty_short_pages_reach_received_close_and_private_memory(tmp_path):
    root = tmp_path / "private"
    memory = Memory(StubSummarizer(max_chars=10000), store=JsonlExperienceStore(root, "p-0"))
    peer = Memory(StubSummarizer())
    brain = EventDrivenBrain(ScriptedDecisionModel(), StaticChatGenerator(), memory=memory)
    wire, client = native_opened()
    original = client.build_native_state(Goal.GRIND)
    try:
        # Shape only: short B4 lines, nexts, two menus, received B6. Not a live capture.
        for index in range(1, 21):
            state, events = receive_brain(
                wire, client, brain, dialog(0xB4, f"Received line {index}")
            )
            assert state.npc_dialogue is not None
            assert len(state.npc_dialogue.pages) == index, f"page {index} was not retained"
            assert not bool(client._npc.failed)
            assert len(memory.log.notes()) == index
            for event in events:
                if isinstance(event, NpcDialogueReceived):
                    brain.handle_event(state, event)
            assert len(memory.log.notes()) == index
            if index in (6, 9, 11, 16, 20):
                state, _ = receive_brain(wire, client, brain, dialog(0xB5))
                actions = brain.step_script(state).actions
                assert actions == (NpcNext(321),)
                client.perform_native(actions[0])
            if index in (11, 16):
                wire.add(dialog(0xB7, "A:B:C:D"))
                client.build_native_state(Goal.GRIND)
                client.perform_native(NpcSelect(321, 2 if index == 11 else 4))
        state, _ = receive_brain(wire, client, brain, dialog(0xB6))
        assert brain.step_script(state).actions == (NpcClose(321),)
        client.perform_native(NpcClose(321))
        closed = client.build_native_state(Goal.GRIND)
        assert closed.npc_dialogue is not None
        assert closed.npc_dialogue.stage == "close_requested"
        assert closed.npc_instructions_received
        assert not client._npc.actuation_blocked
        assert wire.sent[-1] == struct.pack("<HI", 0x146, 321)
        assert len(wire.sent) == 9
        assert closed.inventory == original.inventory == {}
        assert closed.job == original.job
        assert closed.base_level == original.base_level
        notes = memory.log.notes()
        assert len({note.text for note in notes}) == 20
        assert all(note.kind == "npc_dialogue" for note in notes)
        assert "page=17 " in notes[16].text
        assert "page=20 " in notes[-1].text
        assert not peer.view()
        assert_post_close_continuation(wire, client, brain, memory, notes)
    finally:
        memory.close()
    replay_private_notes(root, notes)


def replay_private_notes(root: Path, notes: tuple[ExperienceNote, ...]) -> None:
    restored = Memory(StubSummarizer(max_chars=10000), store=JsonlExperienceStore(root, "p-0"))
    try:
        assert restored.log.notes() == notes
        assert "Received line 20" in "\n".join(restored.view())
    finally:
        restored.close()


def assert_post_close_continuation(
    wire: Any,
    client: PlayingClient,
    brain: EventDrivenBrain,
    memory: Memory,
    notes: tuple[ExperienceNote, ...],
) -> None:
    # The continuation scene grinds on the field (window 30): prontera
    # staging would be the merchant return legs' claim instead.
    wire.add(field_map(), monster(at=(42, 38)))
    state = client.build_native_state(Goal.GRIND)
    for _ in range(5):
        assert brain.step_script(state).actions == (Attack(123),)
    assert memory.log.notes() == notes


@pytest.mark.parametrize("count", [32, 33])
def test_exact_page_boundary_independent_of_other_budgets(count):
    wire, client = native_opened()
    pages = tuple(f"Short {index}" for index in range(count))
    assert sum(len(text.encode()) for text in pages) < 4096
    wire.add(*(dialog(0xB4, text) for text in pages))
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert len(state.npc_dialogue.pages) == 32
    assert client._npc.presentations == count < 64
    assert client._npc.requests == 1
    assert client._npc.failed == (count == 33)
    assert state.npc_dialogue.stage == ("text" if count == 32 else "blocked")
    wire.add(dialog(0xB6))
    client.perform_native(NpcClose(321))
    assert len(wire.sent) == (2 if count == 32 else 1)


@pytest.mark.parametrize("parts", [("é" * 2048,), ("é" * 1024, "é" * 1024)])
def test_exact_utf8_boundary_then_valid_multibyte_overflow(parts):
    wire, client = native_opened()
    assert sum(len(text.encode()) for text in parts) == 4096
    assert max(len(dialog(0xB4, text)) for text in parts) <= 4105
    wire.add(*(dialog(0xB4, text) for text in parts))
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.pages == parts
    assert not bool(client._npc.failed)
    wire.add(dialog(0xB4, "é"))
    rejected = client.build_native_state(Goal.GRIND).npc_dialogue
    assert rejected is not None
    assert rejected.pages == parts
    assert rejected.stage == "blocked"
    assert client._npc.failed


def test_exact_utf8_budget_still_allows_received_close():
    wire, client = native_opened()
    raw = dialog(0xB4, "é" * 2048)
    assert len(raw) == 4105
    wire.add(raw, dialog(0xB6))
    client.perform_native(NpcClose(321))
    assert wire.sent[-1] == struct.pack("<HI", 0x146, 321)
    assert client._npc.instructions_received


@pytest.mark.parametrize("text", ["x" * 4097, "é" * 2049])
def test_single_utf8_overflow_still_fails_closed(text):
    wire, client = native_opened()
    wire.add(dialog(0xB4, text), dialog(0xB6))
    client.perform_native(NpcClose(321))
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.pages == ()
    assert state.npc_dialogue.stage == "blocked"
    assert wire.sent == [struct.pack("<HIB", 0x90, 321, 1)]


def test_presentation_limit_remains_exactly_64_with_32_pages():
    wire, client = native_opened()
    wire.add(*(dialog(0xB4, "short") for _ in range(32)))
    wire.add(*(dialog(0xB5) for _ in range(32)))
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert len(state.npc_dialogue.pages) == 32
    assert state.npc_dialogue.stage == "next"
    assert client._npc.presentations == 64
    assert not bool(client._npc.failed)
    wire.add(dialog(0xB6))
    client.perform_native(NpcClose(321))
    assert client._npc.presentations == 65
    assert client._npc.failed
    assert len(wire.sent) == 1


def test_request_limit_remains_exactly_32():
    wire, client = native_opened()
    wire.add(*(dialog(0xB4, "short") for _ in range(32)))
    for _ in range(31):
        wire.add(dialog(0xB5))
        client.perform_native(NpcNext(321))
    assert client._npc.requests == len(wire.sent) == 32
    assert not bool(client._npc.failed)
    wire.add(dialog(0xB6))
    client.perform_native(NpcClose(321))
    assert client._npc.requests == len(wire.sent) == 32
    assert client._npc.failed
    assert not client._npc.instructions_received


def test_absolute_lifetime_remains_120_despite_short_page_receipts():
    now = [0.0]
    wire, client = opened(now)
    for at in range(4, 120, 4):
        now[0] = float(at)
        wire.add(dialog(0xB4, "short"))
        state = client.build_native_state(Goal.GRIND)
        assert state.npc_dialogue is not None
        assert state.npc_dialogue.stage == "text"
    assert client._npc.absolute_deadline == 120.0
    now[0] = 120.0
    wire.add(dialog(0xB6))
    client.perform_native(NpcClose(321))
    assert client._npc.failed
    assert len(wire.sent) == 1


@pytest.mark.parametrize("npc_id", [0, 0xFFFFFFFF, 0x100000000, True])
def test_unknown_or_invalid_uint32_identity_cannot_open(npc_id):
    other = PlayingClient(npc_wire(), monotonic=lambda: 0.0)
    other.wire.add(struct.pack("<HII24s24s", 0x0ADF, 0xFFFFFFFF, 0, b"Nelliorde", b""))
    other.perform_native(TalkToNpc(npc_id))
    assert other.build_native_state(Goal.GRIND).npc_dialogue is None
    assert not other.wire.sent


@pytest.mark.parametrize("mode", ["coalesced", "bytewise", "every_split"])
def test_twenty_page_stream_and_received_close_preserve_exact_framing(mode):
    frames = [*(dialog(0xB4, f"Short {index}") for index in range(20)), dialog(0xB6)]
    stream = b"".join(frames)
    expected = [(int.from_bytes(raw[:2], "little"), raw) for raw in frames]
    module = packet_module()
    if mode == "every_split":
        for split in range(len(stream) + 1):
            first, pending = module.parse_stream(stream[:split])
            second, tail = module.parse_stream(pending + stream[split:])
            assert first + second == expected
            assert tail == b""
        return
    chunks = [stream] if mode == "coalesced" else [bytes([byte]) for byte in stream]
    wire, client = native_opened()
    pending = b""
    for chunk in chunks:
        ready, pending = module.parse_stream(pending + chunk)
        wire.add(*(raw for _, raw in ready))
    assert pending == b""
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert len(state.npc_dialogue.pages) == 20
    assert state.npc_dialogue.stage == "close"
    client.perform_native(NpcClose(321))
    assert wire.sent[-1] == struct.pack("<HI", 0x146, 321)
