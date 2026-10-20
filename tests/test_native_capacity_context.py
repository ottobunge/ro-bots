"""Synthetic vertical SELF receipts, not native acceptance or spending authority."""

import json
import struct
from dataclasses import FrozenInstanceError, asdict, replace
from types import SimpleNamespace

import pytest

from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.domain.model import Goal
from tests.test_native_shop_selection import actual_clients
from tests.test_playing_runtime import entry, map_frame


def capacity_frames(weight: int = 210, maximum: int = 20000) -> tuple[bytes, bytes]:
    return struct.pack("<HHi", 0xB0, 24, weight), struct.pack("<HHi", 0xB0, 25, maximum)


@pytest.mark.parametrize(
    ("weight", "maximum"), [(0, 0), (210, 20000), (210, 100), (-1, 100), (1, -1)]
)
def test_received_values_and_detached_provenance(monkeypatch, weight, maximum):
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(*capacity_frames(weight, maximum))
    state = client.build_native_state(Goal.GRIND)
    assert (state.weight, state.max_weight) == (weight, maximum)
    receipt = state.capacity_receipt
    assert receipt is not None
    assert receipt.complete
    assert receipt.nonnegative == (weight >= 0 and maximum >= 0)
    assert (receipt.epoch, receipt.character, receipt.account_id, receipt.character_id) == (
        1,
        wire.char_name,
        999,
        77,
    )
    assert receipt.weight is not None
    assert receipt.max_weight is not None
    assert receipt.weight.receipt_sequence < receipt.max_weight.receipt_sequence
    assert receipt.weight.observed_at == receipt.sampled_at == 100.0
    assert (receipt.selection_epoch, receipt.map_epoch) == (1, 1)
    with pytest.raises(FrozenInstanceError):
        receipt.weight.__setattr__("value", 1)
    assert json.loads(json.dumps(asdict(state)))["capacity_receipt"]["weight"]["value"] == weight
    assert 24 not in wire.status_params
    assert 25 not in wire.status_params
    assert len(sent) == 2


def test_partial_latest_receipts_and_repeated_observation(monkeypatch):
    _wire, client, receive, sent = actual_clients(monkeypatch)
    initial = client.build_native_state(Goal.GRIND)
    assert initial.weight == 10
    assert initial.max_weight is None
    assert initial.capacity_receipt is not None
    assert not initial.capacity_receipt.complete
    receive(struct.pack("<HHi", 0xB0, 25, 100))
    after = client.build_native_state(Goal.GRIND)
    receive(struct.pack("<HHi", 0xB0, 24, 0))
    current = client.build_native_state(Goal.GRIND)
    assert (current.weight, current.max_weight) == (0, 100)
    assert current.capacity_receipt is not None
    assert after.capacity_receipt is not None
    assert current.capacity_receipt.max_weight is after.capacity_receipt.max_weight
    assert client.build_native_state(Goal.GRIND).capacity_receipt == current.capacity_receipt
    assert after.weight == 10
    assert len(sent) == 2


@pytest.mark.parametrize(
    "boundary",
    ["socket", "reader", "session", "selection", "wire", "epoch", "transport", "gap", "reconnect"],
)
def test_owner_and_session_invalidation_never_replays_old_capacity(monkeypatch, boundary):
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(*capacity_frames())
    historical = client.build_native_state(Goal.GRIND)
    if boundary == "socket":
        wire.sock = object()
    elif boundary == "reader":
        wire.rx_thread = SimpleNamespace(is_alive=lambda: True)
    elif boundary == "session":
        client._planning_session = object()
    elif boundary == "selection":
        wire.selected_character_snapshot = replace(wire.selected_character_snapshot)
    elif boundary == "wire":
        client.wire, _other, receive, _sent = actual_clients(monkeypatch)
    elif boundary == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
        wire._native_frames.clear()
        wire._native_frame_base = wire._native_frame_seq
    elif boundary == "transport":
        wire.running = False
    elif boundary == "reconnect":
        monkeypatch.setattr(wire, "connect", lambda: None)
        client.connect()
    else:
        wire._native_frames.clear()
        wire._native_frame_seq += 2000
        wire._native_frame_base = wire._native_frame_seq
    if boundary in ("epoch", "transport", "gap"):
        with pytest.raises(NativeTelemetryUnavailable):
            client.build_native_state(Goal.GRIND)
    else:
        state = client.build_native_state(Goal.GRIND)
        assert (state.weight, state.max_weight, state.capacity_receipt) == (None, None, None)
    assert client._capacity.receipt is None
    assert historical.weight == 210
    assert historical.max_weight == 20000
    assert len(sent) == 2


@pytest.mark.parametrize(
    "bad",
    [
        "seq_bool",
        "pid_bool",
        "epoch_bool",
        "at_bool",
        "at_nan",
        "at_future",
        "short",
        "out_of_order",
        "seq_negative",
        "seq_string",
        "pid_float",
        "epoch_none",
        "base_bool",
    ],
)
def test_malformed_received_metadata_invalidates_known_capacity(monkeypatch, bad):
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(*capacity_frames())
    assert client.build_native_state(Goal.GRIND).max_weight == 20000
    receive(struct.pack("<HHi", 0xB0, 24, 999))
    seq, at, pid, raw = wire._native_frames[-1]
    if bad in ("epoch_bool", "epoch_none"):
        wire.native_epoch = True if bad == "epoch_bool" else None
    elif bad == "base_bool":
        wire._native_frame_base = True
    elif bad == "out_of_order":
        wire._native_frames[-1], wire._native_frames[-2] = (
            wire._native_frames[-2],
            wire._native_frames[-1],
        )
    else:
        seq = {"seq_bool": True, "seq_negative": -1, "seq_string": "wrong"}.get(bad, seq)
        pid = {"pid_bool": True, "pid_float": float(pid)}.get(bad, pid)
        at = {"at_bool": True, "at_nan": float("nan"), "at_future": 101.0}.get(bad, at)
        raw = raw[:-1] if bad == "short" else raw
        wire._native_frames[-1] = (seq, at, pid, raw)
    if bad == "at_future":
        state = client.build_native_state(Goal.GRIND)
        assert state.capacity_receipt is None
    else:
        with pytest.raises(NativeTelemetryUnavailable):
            client.build_native_state(Goal.GRIND)
        assert client._tracker is not None
        assert not client._tracker.view.inventory_known
    assert client._capacity.receipt is None
    assert len(sent) == 2


@pytest.mark.parametrize("clock", [True, float("nan"), float("inf"), -1.0, 99.0])
def test_invalid_current_observation_clock_clears_capacity(monkeypatch, clock):
    _wire, client, receive, sent = actual_clients(monkeypatch)
    receive(*capacity_frames())
    assert client.build_native_state(Goal.GRIND).weight == 210
    client._now = lambda: clock
    state = client.build_native_state(Goal.GRIND)
    assert (state.weight, state.max_weight, state.capacity_receipt) == (None, None, None)
    assert client._capacity.receipt is None
    assert len(sent) == 2


@pytest.mark.parametrize("replacement", ["selection", "epoch"])
def test_fresh_received_capacity_after_lifecycle_boundary(monkeypatch, replacement):
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(*capacity_frames())
    historical = client.build_native_state(Goal.GRIND)
    if replacement == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
        wire._native_frames.clear()
        wire._native_frame_seq = wire._native_frame_base = 0
        receive(entry(), map_frame(), *capacity_frames(0, 100))
    else:
        wire.selected_character_snapshot = replace(wire.selected_character_snapshot)
        assert client.build_native_state(Goal.GRIND).capacity_receipt is None
        receive(*capacity_frames(0, 100))
    state = client.build_native_state(Goal.GRIND)
    assert (state.weight, state.max_weight) == (0, 100)
    assert state.capacity_receipt is not None
    assert state.capacity_receipt.epoch == wire.native_epoch
    assert historical.max_weight == 20000
    assert len(sent) == (3 if replacement == "epoch" else 2)


@pytest.mark.parametrize("readiness", ["vitals", "class"])
def test_capacity_fact_is_independent_of_spending_readiness(monkeypatch, readiness):
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(*capacity_frames())
    historical = client.build_native_state(Goal.GRIND).capacity_receipt
    if readiness == "vitals":
        wire.status_params.clear()
    else:
        wire.class_fresh = False
    with pytest.raises(NativeTelemetryUnavailable):
        client.build_native_state(Goal.GRIND)
    assert client._capacity.receipt == historical
    assert len(sent) == 2


def test_warp_preserves_history_and_inventory_change_marks_freshness(monkeypatch):
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(*capacity_frames())
    historical = client.build_native_state(Goal.GRIND).capacity_receipt
    receive(map_frame())
    state = client.build_native_state(Goal.GRIND)
    assert state.capacity_receipt == historical
    assert wire.native_epoch == 1
    receive(struct.pack("<HHH", 0xAF, 9, 1), struct.pack("<HHi", 0xB0, 24, 0))
    state = client.build_native_state(Goal.GRIND)
    assert not state.inventory_known
    assert state.inventory == {}
    assert state.weight == 0
    assert state.max_weight == 20000
    assert state.capacity_receipt is not None
    assert state.capacity_receipt.inventory_changed_sequence is not None
    assert historical is not None
    assert historical.weight is not None
    assert historical.weight.value == 210
    assert len(sent) == 3


@pytest.mark.parametrize("boundary", ["selection", "session", "socket", "reader", "wire"])
def test_owner_replacement_cannot_keep_or_replay_complete_inventory(monkeypatch, boundary):
    """Reached independent post-GREEN failures, promoted as repair regressions."""
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(struct.pack("<HHi", 0xB0, 25, 20000))
    before = client.build_native_state(Goal.GRIND)
    assert before.inventory_known
    assert before.inventory == {"1201": 1}
    assert before.capacity_receipt is not None
    assert before.capacity_receipt.complete
    original_sent = len(sent)
    replacement_sent = None
    if boundary == "selection":
        wire.selected_character_snapshot = replace(wire.selected_character_snapshot)
    elif boundary == "session":
        client._planning_session = object()
    elif boundary == "socket":
        wire.sock = object()
    elif boundary == "reader":
        wire.rx_thread = SimpleNamespace(is_alive=lambda: True)
    else:
        other_wire, _other, _receive, replacement_sent = actual_clients(monkeypatch)
        client.wire = other_wire
    try:
        after = client.build_native_state(Goal.GRIND)
    except NativeTelemetryUnavailable:
        assert client._capacity.receipt is None
        assert client._tracker is not None
        assert not client._tracker.view.inventory_known
    else:
        assert after.capacity_receipt is None
        assert not after.inventory_known
        assert after.inventory == {}
    assert before.inventory_known
    assert before.inventory == {"1201": 1}
    assert len(sent) == original_sent
    if replacement_sent is not None:
        assert len(replacement_sent) == 2
