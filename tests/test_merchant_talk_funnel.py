"""Leg-113 merchant contact and overlapping fallback parking, entirely offline."""

import struct
import threading

import pytest

from robots.adapters.playing_backends import PlayingBackendError
from robots.app import scripts
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import MoveTo, Say
from robots.domain.events import Heartbeat
from robots.domain.model import Goal
from tests.test_dealer_queue_handover import _received_arrival
from tests.test_dealer_ring import _client, _host, _step
from tests.test_dealer_walkability import NEIGHBOURS
from tests.test_sell_conversion_recovery import _answer_sale
from tests.test_shop_sell_loop import DEALER, _dealer


@pytest.fixture(autouse=True)
def _fresh_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _pump_client(
    at: tuple[int, int] = (173, 130),
) -> tuple[PlayingClient, list[float]]:
    client, now = _client(at=at)
    client._keepalive_thread = threading.current_thread()
    client.wire.keepalive = lambda: None
    return client, now


def test_adjacent_seller_opens_and_sells_on_pump_while_only_chat_is_dispatched():
    client, now = _pump_client()
    _answer_sale(client)
    for _ in range(4):
        client.drain_native_events()
        client.perform_native(Say("still chatting"))
        now[0] += 1
    frames = [raw for raw in client.wire.sent if isinstance(raw, bytes) and raw[:2] != b"\x98\x09"]
    assert [int.from_bytes(raw[:2], "little") for raw in frames] == [0x90, 0xC5, 0xC9]
    state = client.build_native_state(Goal.GRIND)
    assert state.zeny == 92
    assert "909" not in state.inventory
    assert state.npc_dialogue is None


def test_unanswered_fresh_contact_is_not_reclicked_on_each_pump():
    client, now = _pump_client()
    for _ in range(5):
        client.drain_native_events()
        now[0] += 0.1
    assert client.wire.sent == [struct.pack("<HIB", 0x90, DEALER, 1)]


@pytest.mark.parametrize(
    "barrier",
    [
        "stock",
        "unknown_stock",
        "poison",
        "cancel",
        "passive",
        "planner",
        "pose",
        "pending",
        "lease",
    ],
)
def test_contact_pump_preserves_admission_and_actuation_barriers(barrier):
    client, now = _pump_client()
    if barrier == "stock":
        client.wire.add(struct.pack("<HHH", 0xAF, 6, 1))
    elif barrier == "unknown_stock":
        client.wire.add(struct.pack("<HHH", 0xAF, 99, 1))
    elif barrier == "poison":
        client._npc.failed = True
        client._npc.deny_origin = "malformed"
    elif barrier == "cancel":
        client._npc.cancel_uncertain = True
    elif barrier == "passive":
        client.mechanical_recovery_allowed = False
    elif barrier == "planner":
        client.npc_recovery_hold = True
    elif barrier == "pose":
        client._rest_seq = 1
    elif barrier == "pending":
        client.perform_native(MoveTo(173, 129))
    elif barrier == "lease":
        now[0] += 181
    client.drain_native_events()
    assert not any(raw[:2] == b"\x90\x00" for raw in client.wire.sent)


def _queued_client(*, overlap: bool) -> tuple[PlayingClient, list[float]]:
    client, now = _pump_client(at=(168, 128))
    points = (*NEIGHBOURS, (168, 128)) if overlap else NEIGHBOURS
    for actor_id, point in enumerate(points, 100):
        peer = bytearray(_dealer(point, npc_id=actor_id))
        peer[4] = 0
        client.wire.add(bytes(peer))
    return client, now


def test_overlapping_fallback_body_cannot_park_a_seller_without_a_counter_lease():
    client, _ = _queued_client(overlap=True)
    state = client.build_native_state(Goal.GRIND)
    assert client._counter_lease.reason is None
    (move,) = _step(client, state)
    assert isinstance(move, MoveTo)
    assert (move.x, move.y) != (state.x, state.y)
    client.perform_native(move)
    assert client.last_move_outcome["outcome"] == "dispatched"
    assert client.wire.moves


def test_unoccupied_fallback_cell_keeps_an_honest_queue_hold():
    client, _ = _queued_client(overlap=False)
    state = client.build_native_state(Goal.GRIND)
    assert _step(client, state) == (MoveTo(168, 128),)


def test_expired_counter_still_requires_received_parking_and_rejoin_delay():
    client, now = _pump_client(at=(172, 129))
    now[0] += 181
    client.drain_native_events()
    assert client._counter_lease.reason == "expired"
    assert not any(raw[:2] == b"\x90\x00" for raw in client.wire.sent)
    target = client.merchant_travel_target("prt_in", (172, 129), (172, 130))
    assert target is not None
    # Only the actual off-counter parking target starts the existing cooldown.
    state = client.build_native_state(Goal.GRIND)
    assert client.cache is not None
    parking = client._merchant_staging.yield_target(client.cache.get("prt_in"), state)
    assert parking is not None
    client.wire.add(_received_arrival(*parking))
    client.drain_native_events()
    now[0] += 29
    client.drain_native_events()
    assert client._counter_lease.reason == "expired"
    assert not any(raw[:2] == b"\x90\x00" for raw in client.wire.sent)
    now[0] += 1
    client.drain_native_events()
    assert client._counter_lease.reason is None


def test_capped_chat_event_cannot_starve_the_pre_decide_seller_contact(monkeypatch):
    client, _ = _pump_client()
    agent = _host(client, monkeypatch)
    drain = agent._drain_events

    def events():
        return (*drain(), Heartbeat(seq=1))

    def capped(*_args, **_kwargs):
        message = "synthetic capped event decision"
        raise PlayingBackendError(message)

    monkeypatch.setattr(agent, "_drain_events", events)
    monkeypatch.setattr(agent, "deliver_event", capped)
    with pytest.raises(PlayingBackendError, match="synthetic capped"):
        agent.tick()
    assert client.wire.sent == [struct.pack("<HIB", 0x90, DEALER, 1)]


def test_failed_contact_send_keeps_poison_barrier_on_later_pumps():
    client, now = _pump_client()

    def failed(_raw):
        message = "synthetic contact send failure"
        raise OSError(message)

    client.wire._send = failed
    with pytest.raises(OSError, match="synthetic contact"):
        client.drain_native_events()
    assert client._npc.failed
    assert client._npc.deny_origin == "send_failure"
    client.wire._send = client.wire.sent.append
    for _ in range(3):
        now[0] += 2
        client.drain_native_events()
    assert client.wire.sent == []
