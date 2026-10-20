"""Actual-client synthetic vertical receipts; no native/model/spending acceptance."""

import json
import struct
from dataclasses import FrozenInstanceError, asdict
from functools import partial
from types import SimpleNamespace
from typing import Any

import pytest

from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app.playing_runtime import PlayingClient
from robots.domain.model import Goal
from tests.test_native_shop_selection import actual_clients, ready_shop
from tests.test_playing_runtime import map_frame, monster, position, walk_ack


@pytest.mark.parametrize("balance", [0, -7, 321])
def test_received_self_zeny_reaches_typed_state(monkeypatch, balance):
    _wire, client, receive, sent = actual_clients(monkeypatch)
    assert getattr(client.build_native_state(Goal.GRIND), "zeny", None) is None
    receive(struct.pack("<HHi", 0xB1, 20, balance))
    state = client.build_native_state(Goal.GRIND)
    assert getattr(state, "zeny", None) == balance
    assert len(sent) == 2


OFFER = struct.pack("<HHIIBH", 0xC6, 15, 73, 61, 4, 1201)


@pytest.mark.parametrize("during_send", [False, True])
def test_selected_offer_is_detached_once_and_not_purchase(monkeypatch, during_send):
    wire, client, receive, sent, action = ready_shop(monkeypatch)
    inventory = client.build_native_state(Goal.GRIND).inventory.copy()
    deadline = client._npc.absolute_deadline
    if during_send:

        def send(raw):
            sent.append(raw)
            receive(OFFER)

        monkeypatch.setattr(wire, "_send", send)
    client.perform_native(action)
    if not during_send:
        receive(OFFER)
    state = client.build_native_state(Goal.GRIND)
    offer = state.shop_offer
    assert offer is not None
    assert (offer.rows[0].price, offer.rows[0].discount_price, offer.rows[0].item_id) == (
        73,
        61,
        1201,
    )
    assert (offer.npc_id, offer.epoch, offer.map_name) == (123, 1, "prontera")
    assert offer.receipt_sequence > offer.prompt_sequence
    assert offer.observed_at == 100.0
    assert offer.deadline == 105.0
    with pytest.raises(FrozenInstanceError):
        offer.rows[0].__setattr__("price", 9)
    assert json.loads(json.dumps(asdict(state)))["shop_offer"]["rows"][0]["price"] == 73
    receive(struct.pack("<HHIIBH", 0xC6, 15, 999, 999, 4, 1201))
    assert not client.drain_native_events()
    assert client.build_native_state(Goal.GRIND).shop_offer is offer
    assert state.inventory == inventory
    assert not state.npc_instructions_received
    assert client._npc.deadline == 105.0
    assert client._npc.absolute_deadline == deadline
    assert len(sent) == 3


@pytest.mark.parametrize(
    "boundary",
    [
        "map",
        "vanish",
        "reuse",
        "entry",
        "new_c4",
        "death",
        "sit",
        "motion",
        "session",
        "socket",
        "reader",
        "controller",
        "expired",
        "gap",
    ],
)
def test_offer_loses_current_context_without_revival(monkeypatch, boundary):
    wire, client, receive, sent, action = ready_shop(monkeypatch)
    client.perform_native(action)
    receive(OFFER)
    historical = client.build_native_state(Goal.GRIND).shop_offer
    assert historical is not None
    npc = bytearray(monster(kind=6, aid=123))
    npc[59:62] = position(42, 37)
    if boundary == "map":
        receive(map_frame())
    elif boundary in ("vanish", "reuse"):
        receive(struct.pack("<HIB", 0x80, 123, 0))
        if boundary == "reuse":
            receive(bytes(npc), struct.pack("<HI", 0xC4, 123), OFFER)
    elif boundary == "entry":
        receive(bytes(npc), OFFER)
    elif boundary == "new_c4":
        receive(struct.pack("<HI", 0xC4, 123), OFFER)
    elif boundary == "death":
        receive(struct.pack("<HIB", 0x80, wire.aid, 1))
    elif boundary == "sit":
        raw = bytearray(34)
        struct.pack_into("<HII", raw, 0, 0x8C8, wire.aid, 0)
        raw[29] = 2
        receive(bytes(raw))
    elif boundary == "motion":
        receive(walk_ack((42, 37), (43, 37)))
    else:
        replace_offer_context(wire, client, boundary)
    if boundary == "gap":
        with pytest.raises(NativeTelemetryUnavailable):
            client.build_native_state(Goal.GRIND)
        assert client._shop_context.offer is None
    else:
        assert client.build_native_state(Goal.GRIND).shop_offer is None
    assert historical.rows[0].price == 73
    assert len(sent) == (4 if boundary == "map" else 3)


def replace_offer_context(wire: Any, client: PlayingClient, boundary: str) -> None:
    if boundary == "session":
        client._planning_session = object()
    elif boundary == "socket":
        wire.sock = object()
    elif boundary == "reader":
        wire.rx_thread = SimpleNamespace(is_alive=lambda: True)
    elif boundary == "controller":
        client._npc = type(client._npc)()
    elif boundary == "expired":
        client._now = lambda: 105.0
    else:
        wire._native_frames.clear()
        wire._native_frame_seq += 2000
        wire._native_frame_base = wire._native_frame_seq


@pytest.mark.parametrize(
    "case", ["unsolicited", "before_send", "foreign_owner", "malformed", "oversize", "late_receipt"]
)
def test_unattributable_offer_cannot_publish(monkeypatch, case):
    _wire, client, receive, sent, action = ready_shop(monkeypatch)
    if case in ("unsolicited", "before_send"):
        receive(OFFER)
        if case == "before_send":
            client.perform_native(action)
    elif case == "foreign_owner":
        _other_wire, other, other_receive, other_sent = actual_clients(monkeypatch)
        other.perform_native(action)
        other_receive(OFFER)
        assert other.build_native_state(Goal.GRIND).shop_offer is None
        assert len(other_sent) == 2
    else:
        client.perform_native(action)
        if case == "malformed":
            receive(struct.pack("<HHIIBH", 0xC6, 15, 73, 61, 4, 0))
        elif case == "oversize":
            receive(struct.pack("<HH", 0xC6, 719) + OFFER[4:] * 65)
        else:
            client._now = lambda: 105.0
            receive(OFFER)
    assert client.build_native_state(Goal.GRIND).shop_offer is None
    assert len(sent) in (2, 3)


@pytest.mark.parametrize(
    "origin", [OSError("failed"), KeyboardInterrupt("stop"), SystemExit("exit")]
)
def test_response_ring_before_failed_send_is_not_issued(monkeypatch, origin):
    wire, client, receive, sent, action = ready_shop(monkeypatch)
    attempts = []

    def fail(raw):
        attempts.append(raw)
        receive(OFFER)
        raise origin

    monkeypatch.setattr(wire, "_send", fail)
    with pytest.raises(type(origin)) as caught:
        client.perform_native(action)
    assert caught.value is origin
    assert client.build_native_state(Goal.GRIND).shop_offer is None
    client.perform_native(action)
    assert len(attempts) == 1
    assert len(sent) == 2


@pytest.mark.parametrize(
    "boundary", ["transport", "reader", "socket", "selection", "session", "gap", "epoch", "wire"]
)
def test_currency_clears_on_session_or_continuity_loss(monkeypatch, boundary):
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(struct.pack("<HHi", 0xB1, 20, 0))
    historical = client.build_native_state(Goal.GRIND)
    assert historical.zeny == 0
    if boundary == "transport":
        wire.running = False
    elif boundary == "reader":
        wire.rx_thread = SimpleNamespace(is_alive=lambda: True)
    elif boundary == "socket":
        wire.sock = object()
    elif boundary == "selection":
        wire.selected_character_snapshot = None
    elif boundary == "session":
        client._planning_session = object()
    elif boundary == "wire":
        other_wire, _other, _other_receive, _other_sent = actual_clients(monkeypatch)
        client.wire = other_wire
    elif boundary == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
        wire._native_frames.clear()
        wire._native_frame_base = wire._native_frame_seq
    else:
        wire._native_frames.clear()
        wire._native_frame_seq += 2000
        wire._native_frame_base = wire._native_frame_seq
    if boundary in ("transport", "selection", "gap", "epoch"):
        with pytest.raises(NativeTelemetryUnavailable):
            client.build_native_state(Goal.GRIND)
        assert client._shop_context.currency is None
    else:
        assert client.build_native_state(Goal.GRIND).zeny is None
    assert historical.zeny == 0
    assert len(sent) == 2


def test_no_response_keeps_original_wait_then_expires(monkeypatch):
    _wire, client, receive, sent, action = ready_shop(monkeypatch)
    client.perform_native(action)
    for now in (101.0, 104.9, 105.0, 108.0):
        client._now = partial(float, now)
        assert client.build_native_state(Goal.GRIND).shop_offer is None
        client.perform_native(action)
    receive(OFFER)
    assert client.build_native_state(Goal.GRIND).shop_offer is None
    assert client._npc.failed
    assert len(sent) == 3


@pytest.mark.parametrize("readiness", ["vitals", "progression"])
def test_missing_received_readiness_permanently_clears_offer(monkeypatch, readiness):
    wire, client, receive, _sent, action = ready_shop(monkeypatch)
    client.perform_native(action)
    receive(OFFER)
    assert client.build_native_state(Goal.GRIND).shop_offer is not None
    if readiness == "vitals":
        wire.status_params.clear()
    else:
        wire.class_fresh = False
    with pytest.raises(NativeTelemetryUnavailable):
        client.build_native_state(Goal.GRIND)
    assert client._shop_context.offer is None


def test_ordinary_warp_retains_historical_zeny_not_b0_balance(monkeypatch):
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(struct.pack("<HHi", 0xB0, 20, 99), struct.pack("<HHi", 0xB1, 21, 99))
    assert client.build_native_state(Goal.GRIND).zeny is None
    receive(struct.pack("<HHi", 0xB1, 20, -7))
    historical = client.build_native_state(Goal.GRIND).zeny_receipt
    receive(map_frame())
    state = client.build_native_state(Goal.GRIND)
    assert state.zeny == -7
    assert state.zeny_receipt is historical
    assert wire.native_epoch == wire.selection_epoch == wire.map_epoch == 1
    assert len(sent) == 3
