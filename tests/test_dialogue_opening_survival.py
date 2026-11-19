"""Leg-116 offline twins: buffered dealer replies precede opening expiry."""

import struct
import threading

import pytest

from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app import scripts
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import NpcShopSellOpen, TalkToNpc
from robots.domain.model import Goal
from tests.test_dealer_ring import _client
from tests.test_sell_conversion_recovery import _answer_sale
from tests.test_shop_sell_loop import DEALER, _c4


@pytest.fixture(autouse=True)
def _fresh_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _opening() -> tuple[PlayingClient, list[float]]:
    client, now = _client(at=(173, 129))
    client._keepalive_thread = threading.current_thread()
    client._keepalive_interval_s = 1.0
    client.wire.keepalive = lambda: None
    client.perform_native(TalkToNpc(DEALER))
    return client, now


def _receive(client: PlayingClient, at: float, *raws: bytes) -> None:
    client.wire.add(*raws)
    for index in range(len(client.wire.frames) - len(raws), len(client.wire.frames)):
        seq, _, pid, raw = client.wire.frames[index]
        client.wire.frames[index] = (seq, at, pid, raw)


def test_buffered_c4_is_consumed_before_host_opening_expiry():
    client, now = _opening()
    # The actual wire timestamps dispatch. Host ticks were 17-19s apart in leg 116.
    _receive(client, 100.1, struct.pack("<HHi", 0xB0, 7, 20), _c4(DEALER))
    now[0] = 117.0
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == "unsupported_shop"
    assert not client._npc.failed
    (selection,) = client.mechanical_actions(state, ())
    assert isinstance(selection, NpcShopSellOpen)
    client.perform_native(selection)
    assert client.wire.sent[-1] == struct.pack("<HIB", 0xC5, DEALER, 1)
    assert sum(f[:2] == b"\x90\x00" for f in client.wire.sent) == 1


def test_c4_delivered_inside_click_send_is_already_armed():
    client, _now = _client(at=(173, 129))

    def send(raw):
        client.wire.sent.append(raw)
        assert client._npc.view is not None
        assert client._npc.view.stage == "opening"
        _receive(client, 100.0, _c4(DEALER))
        client.build_native_state(Goal.GRIND)

    client.wire._send = send
    client.perform_native(TalkToNpc(DEALER))
    assert client._npc.view is not None
    assert client._npc.view.stage == "unsupported_shop"
    assert client._npc.requests == 1


def test_blocked_opening_retries_then_consumes_buffered_c4_and_sells_on_pump():
    client, now = _opening()
    now[0] = 106.0
    client.build_native_state(Goal.GRIND)
    assert client._npc.deny_origin == "timeout"
    _answer_sale(client)
    send = client.wire._send

    def answer(raw):
        send(raw)
        if raw[:2] == b"\x90\x00":
            seq, _, pid, frame = client.wire.frames[-1]
            client.wire.frames[-1] = (seq, now[0], pid, frame)

    client.wire._send = answer
    client.drain_native_events()  # timeout-only recovery closes and re-clicks
    budget = client._npc_retries
    now[0] = 123.0
    client.drain_native_events()
    assert client.wire.sent[-1] == struct.pack("<HIB", 0xC5, DEALER, 1)
    assert client._npc_retries == budget
    for _ in range(2):
        now[0] += 2
        client.drain_native_events()
    assert client._npc.view is None
    assert client.build_native_state(Goal.GRIND).zeny == 92
    assert sum(f[:2] == b"\xc9\x00" for f in client.wire.sent) == 1


@pytest.mark.parametrize("received_at", [99.0, 105.0, 118.0])
def test_expired_or_invalid_c4_cannot_rescue_opening(received_at):
    client, now = _opening()
    _receive(client, received_at, _c4(DEALER))
    now[0] = 117.0
    client.build_native_state(Goal.GRIND)
    assert client._npc.failed
    assert client._npc.deny_origin == "timeout"
    assert len(client.wire.sent) == 1


@pytest.mark.parametrize("barrier", ["poison", "send_failure", "cancel"])
def test_buffered_c4_preserves_poison_and_cancel_barriers(barrier):
    client, now = _opening()
    _receive(client, 100.1, _c4(DEALER))
    if barrier == "cancel":
        client._npc.cancel_uncertain = True
    else:
        client._npc._deny(barrier)
    now[0] = 117.0
    client.build_native_state(Goal.GRIND)
    assert client._npc.actuation_blocked
    assert client._npc.view is not None
    assert client._npc.view.stage != "unsupported_shop"
    assert len(client.wire.sent) == 1


def test_drop_inside_opening_reconnects_to_fresh_pump_contact():
    client, now = _opening()
    _receive(client, 100.1, _c4(DEALER))
    now[0] = 102.0
    client._keepalive_failed = True
    with pytest.raises(NativeTelemetryUnavailable):
        client.build_native_state(Goal.GRIND)
    assert not client._npc.active
    # A rebuild supplies a fresh selected session; old C4 is no authority.
    replacement, _ = _client(at=(173, 129))
    client.wire = replacement.wire
    client.wire.native_epoch = client.wire.selection_epoch = client.wire.map_epoch = 2
    client.wire.keepalive = lambda: None
    _receive(
        client,
        103.0,
        struct.pack("<HII24s24s", 0xADF, DEALER, 0, b"Weapon Dealer#prt", b""),
    )
    client.wire.connect = lambda: None
    client.connect()
    client._keepalive_thread = threading.current_thread()
    now[0] = 103.0
    client.drain_native_events()
    assert client._npc.view is not None
    assert client._npc.view.stage == "opening"
    assert client._npc.view.epoch == 2
    assert client.wire.sent[-1] == struct.pack("<HIB", 0x90, DEALER, 1)
    _receive(client, 103.1, _c4(DEALER))
    now[0] = 120.0
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is not None
    assert state.npc_dialogue.stage == "unsupported_shop"


@pytest.mark.parametrize("boundary", ["absolute", "death", "map", "foreign", "malformed"])
def test_buffered_opening_c4_keeps_received_context_and_absolute_barriers(boundary):
    client, now = _opening()
    if boundary == "death":
        _receive(client, 100.05, struct.pack("<HIB", 0x80, client.wire.aid, 1))
    elif boundary == "map":
        _receive(client, 100.05, struct.pack("<H16sHH", 0x91, b"prt_in", 173, 129))
    raw = _c4(9999 if boundary == "foreign" else DEALER)
    if boundary == "malformed":
        raw += b"extra"
    _receive(client, 100.1, raw)
    now[0] = 220.0 if boundary == "absolute" else 117.0
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is None or state.npc_dialogue.stage != "unsupported_shop"
    assert len(client.wire.sent) == 1
