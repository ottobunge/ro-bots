"""Offline synthetic frames through actual native construction/framing/dispatch."""

import importlib.util
import struct
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from robots.adapters.native_progression import SelectedCharacterSnapshot
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import NpcShopBuySelection, TalkToNpc
from robots.domain.model import Goal
from tests.test_native_equipment import frame as equipment_frame
from tests.test_native_equipment import row as equipment_row
from tests.test_playing_runtime import entry, map_frame, monster, position, walk_ack

ROOT = Path(__file__).resolve().parents[1]


def actual_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Any, PlayingClient, Callable[..., None], list[bytes]]:
    spec = importlib.util.spec_from_file_location(
        "novice_equipment_actual_wire", ROOT / "spikes/003-clientless-limbs/client.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.time, "monotonic", lambda: 100.0)
    # Public dummy construction, never connection, session start or close.
    wire = module.BotClient(
        "offline-synthetic", "unused-not-a-real-secret", "WireNovice", verbose=False
    )
    wire.aid, wire.gid = 999, 77
    wire.running = wire.connected_map = True
    wire.sock = object()  # Metadata sentinel only, no real socket.
    wire.rx_thread = SimpleNamespace(is_alive=lambda: True)
    wire.native_epoch = wire.selection_epoch = wire.map_epoch = 1
    wire.class_fresh = True
    wire.selected_character_snapshot = SelectedCharacterSnapshot(77, 0, 10, 10, 0, 0)
    wire.map_name = "prontera"
    sent: list[bytes] = []
    monkeypatch.setattr(wire, "_send", sent.append)  # Only primitive send replaced.
    client = PlayingClient(wire, monotonic=lambda: 100.0)

    def receive(*frames: bytes) -> None:
        parsed, pending = module.pdb.parse_stream(b"".join(frames))
        assert pending == b"", "public synthetic frame geometry failed"
        assert len(parsed) == len(frames)
        for pid, raw in parsed:
            wire._dispatch(pid, raw)  # Actual wire world dispatch + ring retention.

    npc = bytearray(monster(kind=6, aid=123))
    npc[59:62] = position(42, 37)  # Perceived near NPC, no backend shop-name seed.
    receive(
        entry(),
        map_frame(),
        bytes(npc),
        *(struct.pack("<HHi", 0xB0, p, v) for p, v in ((5, 100), (6, 100), (7, 20), (8, 20))),
        struct.pack("<HH", 0x0991, 4),
        equipment_frame(equipment_row(0)),
        struct.pack("<HHi", 0xB0, 24, 10),
    )
    state = client.build_native_state(Goal.GRIND)
    assert state.alive is True
    assert state.inventory_known
    assert state.inventory == {"1201": 1}
    assert state.nearby[0].kind == "npc"
    assert state.nearby[0].distance == 0
    client.perform_native(TalkToNpc(123))
    assert sent == [struct.pack("<H", 0x7D), struct.pack("<HIB", 0x90, 123, 1)]
    assert client._npc.view is not None
    assert client._npc.view.stage == "opening"
    return wire, client, receive, sent


def ready_shop(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Any, PlayingClient, Callable[..., None], list[bytes], NpcShopBuySelection]:
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(struct.pack("<HI", 0xC4, 123))
    client.drain_native_events()
    action = client.npc_shop_buy_selection()
    assert action is not None
    return wire, client, receive, sent, action


def test_actual_buy_selection_consumes_marker_once(monkeypatch):
    _wire, client, _receive, sent, action = ready_shop(monkeypatch)
    dialog = client._npc.view
    assert dialog is not None
    assert (action.npc_id, action.epoch, action.prompt_sequence) == (123, 1, dialog.sequence)
    assert (action.map_name, action.opened_sequence) == (dialog.map_name, dialog.opened_sequence)
    deadline = client._npc.absolute_deadline
    client.perform_native(action)
    assert sent == [
        struct.pack("<H", 0x7D),
        struct.pack("<HIB", 0x90, 123, 1),
        struct.pack("<HIB", 0xC5, 123, 0),
    ]
    assert client._npc.requests == 2
    assert client._npc.view is not None
    assert client._npc.view.stage == "waiting"
    assert client._npc.deadline == 105.0
    assert client._npc.absolute_deadline == deadline
    for _ in range(3):
        client.perform_native(action)
        client.build_native_state(Goal.GRIND)
        assert client.npc_shop_buy_selection() is None
    assert len(sent) == 3
    assert not client._npc.instructions_received


def test_equivalent_foreign_wrapper_cannot_dispatch(monkeypatch):
    _wire, client, _receive, sent, action = ready_shop(monkeypatch)
    _other_wire, other, _other_receive, other_sent, other_action = ready_shop(monkeypatch)
    assert other_action == action
    other.perform_native(action)
    assert len(other_sent) == 2
    client.perform_native(action)
    assert len(sent) == 3


@pytest.mark.parametrize(
    "boundary",
    [
        "map",
        "epoch",
        "vanish",
        "reuse",
        "entry",
        "death",
        "sit",
        "motion",
        "transport",
        "gap",
        "far",
        "kind",
        "map_spelling",
    ],
)
def test_current_received_guards_deny_before_send(monkeypatch, boundary):
    wire, client, receive, sent, action = ready_shop(monkeypatch)
    before = len(sent)
    if boundary == "map":
        receive(map_frame())
        before = len(sent)  # Actual map dispatch has its independent 007D ACK.
    elif boundary == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    elif boundary in ("vanish", "reuse"):
        receive(struct.pack("<HIB", 0x80, 123, 0))
        if boundary == "reuse":
            npc = bytearray(monster(kind=6, aid=123))
            npc[59:62] = position(42, 37)
            receive(bytes(npc), struct.pack("<HI", 0xC4, 123))
    elif boundary in ("entry", "far", "kind"):
        npc = bytearray(monster(kind=0 if boundary == "kind" else 6, aid=123))
        npc[59:62] = position(50 if boundary == "far" else 42, 37)
        receive(bytes(npc))
    elif boundary == "death":
        receive(struct.pack("<HIB", 0x80, wire.aid, 1))
    elif boundary == "sit":
        raw = bytearray(34)
        struct.pack_into("<HII", raw, 0, 0x8C8, wire.aid, 0)
        raw[29] = 2
        receive(bytes(raw))
    elif boundary == "motion":
        receive(walk_ack((42, 37), (43, 37)))
    elif boundary == "transport":
        wire.running = False
    elif boundary == "gap":
        wire._native_frames.clear()
        wire._native_frame_seq += 2000
        wire._native_frame_base = wire._native_frame_seq
    else:
        wire.map_name = "unknown_map"
    client.perform_native(action)
    client.perform_native(action)
    assert len(sent) == before
    assert client._npc.requests <= 1


@pytest.mark.parametrize("replacement", ["session", "wire", "sock", "reader"])
def test_owner_local_references_must_remain_identical(monkeypatch, replacement):
    wire, client, _receive, sent, action = ready_shop(monkeypatch)
    other_sent: list[bytes] = []
    if replacement == "session":
        client._planning_session = object()
    elif replacement == "wire":
        other_wire, _other, _other_receive, other_sent, _other_action = ready_shop(monkeypatch)
        client.wire = other_wire
    elif replacement == "sock":
        wire.sock = object()
    else:
        wire.rx_thread = SimpleNamespace(is_alive=lambda: True)
    client.perform_native(action)
    assert len(sent) == 2
    if replacement == "wire":
        assert len(other_sent) == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("npc_id", True),
        ("npc_id", 999),
        ("epoch", True),
        ("prompt_sequence", 1),
        ("opened_sequence", False),
        ("map_name", "unknown_map"),
    ],
)
def test_malformed_current_action_has_no_fallback(monkeypatch, field, value):
    _wire, client, _receive, sent, action = ready_shop(monkeypatch)
    object.__setattr__(action, field, value)
    client.perform_native(action)
    assert len(sent) == 2
    assert client._npc.requests == 1


@pytest.mark.parametrize("change", ["foreign", "newer", "malformed", "expired"])
def test_ui_drift_cannot_reauthorize_old_selection(monkeypatch, change):
    _wire, client, receive, sent, action = ready_shop(monkeypatch)
    if change == "foreign":
        receive(struct.pack("<HI", 0xC4, 999))
        # A foreign frame does not consume the current matching marker.
        client.perform_native(action)
        assert len(sent) == 3
        return
    if change == "newer":
        receive(struct.pack("<HI", 0xC4, 123))
    elif change == "malformed":
        receive(struct.pack("<HHIH", 0xB4, 10, 123, 0))
    else:
        client._now = lambda: 115.0
        receive(struct.pack("<HI", 0xC4, 123))
    client.perform_native(action)
    assert len(sent) == 2
    if change == "expired":
        assert client._npc.failed
        assert client.npc_shop_buy_selection() is None


@pytest.mark.parametrize(
    "origin",
    [
        OSError("selection failed"),
        KeyboardInterrupt("selection interrupted"),
        SystemExit("selection exited"),
    ],
)
def test_sender_failure_retains_exact_origin_without_retry(monkeypatch, origin):
    wire, client, _receive, sent, action = ready_shop(monkeypatch)
    attempts = []

    def fail(raw):
        attempts.append(raw)
        raise origin

    monkeypatch.setattr(wire, "_send", fail)
    with pytest.raises(type(origin)) as caught:
        client.perform_native(action)
    assert caught.value is origin
    assert client._npc.failed
    assert client.local_npc_dispatch is None
    assert not client._npc.instructions_received
    client.perform_native(action)
    assert client.npc_shop_buy_selection() is None
    assert attempts == [struct.pack("<HIB", 0xC5, 123, 0)]
    assert len(sent) == 2


def test_offer_receipt_is_neither_purchase_nor_progress(monkeypatch):
    _wire, client, receive, sent, action = ready_shop(monkeypatch)
    inventory = client.build_native_state(Goal.GRIND).inventory
    client.perform_native(action)
    receive(struct.pack("<HHIIBH", 0xC6, 15, 73, 61, 4, 1201))
    events = client.drain_native_events()
    state = client.build_native_state(Goal.GRIND)
    assert not events
    assert state.inventory == inventory
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == "waiting"
    assert not state.npc_instructions_received
    assert len(sent) == 3


@pytest.mark.parametrize("limit", ["requests", "absolute"])
def test_existing_limits_are_not_reset(monkeypatch, limit):
    _wire, client, _receive, sent, action = ready_shop(monkeypatch)
    if limit == "requests":
        client._npc.requests = 32
    else:
        client._npc.absolute_deadline = 100.0
    client.perform_native(action)
    assert len(sent) == 2


@pytest.mark.parametrize("clock", [float("nan"), float("inf"), True])
def test_invalid_dispatch_clock_denies_without_effect(monkeypatch, clock):
    _wire, client, _receive, sent, action = ready_shop(monkeypatch)
    client._now = lambda: clock
    client.perform_native(action)
    assert len(sent) == 2
