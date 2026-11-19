"""Received-body FIFO and sequential shop conversions, with no decisions/world."""

import struct
import threading

import pytest

from robots.adapters.native_navigation import MapCache
from robots.app import scripts
from robots.app.merchant_counter_lease import COUNTER_LEASE_SECONDS
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import MoveTo, TalkToNpc
from robots.domain.model import Goal
from tests.test_dealer_queue_handover import _receive_bodies, _received_arrival
from tests.test_dealer_ring import _client
from tests.test_native_navigation import SOURCE
from tests.test_sell_conversion_recovery import _answer_sale
from tests.test_shop_sell_loop import DEALER, _cb


@pytest.fixture(autouse=True)
def _fresh_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _fleet() -> tuple[dict[int, tuple[PlayingClient, list[float]]], dict[int, tuple[int, int]]]:
    positions = {300: (171, 128), 100: (168, 124)}
    clients = {aid: _client(str(aid), at=p, aid=aid) for aid, p in positions.items()}
    for aid, (client, _) in clients.items():
        client.cache = MapCache.load(
            SOURCE / "db/map_cache.dat", SOURCE / "db/pre-re/map_cache.dat"
        )
        client._keepalive_thread = threading.current_thread()
        client.wire.keepalive = lambda: None
        _receive_bodies(client, aid, positions, set())
        client.build_native_state(Goal.GRIND)
    # The lower-ID seller joins later, closer to the dealer. Arrival wins.
    positions[100] = (173, 128)
    for aid, (client, _) in clients.items():
        client.wire.add(_received_arrival(*positions[aid]))
        _receive_bodies(client, aid, positions, set())
        client.build_native_state(Goal.GRIND)
    return clients, positions


def _turn(client: PlayingClient, aid: int, positions: dict[int, tuple[int, int]]) -> None:
    client.wire.add(_received_arrival(*positions[aid]))
    _receive_bodies(client, aid, positions, set())
    client.drain_native_events()
    if client.wire.moves:
        positions[aid] = client.wire.moves[-1]


def test_arrival_order_admits_only_one_seller_even_with_multiple_free_counter_cells():
    clients, _ = _fleet()
    targets = {}
    for aid, (client, _) in clients.items():
        state = client.build_native_state(Goal.GRIND)
        targets[aid] = client.merchant_travel_target("prt_in", (state.x, state.y), (172, 130))
    assert targets[300] in ((172, 129), (171, 129))
    assert targets[100] is not None
    assert max(abs(targets[100][0] - 172), abs(targets[100][1] - 130)) >= 2


def test_two_queued_sellers_convert_in_order_in_one_window_without_decides():
    clients, positions = _fleet()
    for client, _ in clients.values():
        _answer_sale(client)
    conversions = []
    for tick in range(60):
        for aid, (client, now) in clients.items():
            now[0] = 102.0 + tick * 2
            _turn(client, aid, positions)
            if aid not in conversions and client.build_native_state(Goal.GRIND).zeny == 92:
                conversions.append(aid)
        if len(conversions) == 2:
            break
    assert conversions == [300, 100], (conversions, positions)
    assert tick * 2 < COUNTER_LEASE_SECONDS
    for client, _ in clients.values():
        assert sum(raw[:2] == b"\xc9\x00" for raw in client.wire.sent) == 1


def test_timed_out_holder_yields_and_next_seller_converts_on_the_pump():
    clients, positions = _fleet()
    _answer_sale(clients[300][0], respond=False)
    _answer_sale(clients[100][0])
    for tick in range(140):
        for aid, (client, now) in clients.items():
            now[0] = 102.0 + tick * 2
            _turn(client, aid, positions)
        if clients[100][0].build_native_state(Goal.GRIND).zeny == 92:
            break
    owner = clients[300][0]
    assert clients[100][0].build_native_state(Goal.GRIND).zeny == 92, positions
    assert owner._counter_lease.reason in ("expired", "retry_exhausted")
    assert owner._npc.view is None
    assert not any(raw[:2] == b"\xc9\x00" for raw in owner.wire.sent)
    assert tick * 2 < COUNTER_LEASE_SECONDS + 60


def test_completed_sale_does_not_rejoin_after_parking_cooldown():
    client, now = _client(at=(172, 129))
    client._keepalive_thread = threading.current_thread()
    client.wire.keepalive = lambda: None
    _answer_sale(client)
    for _ in range(5):
        client.drain_native_events()
        now[0] += 2
    assert client.build_native_state(Goal.GRIND).zeny == 92
    assert client.cache is not None
    state = client.build_native_state(Goal.GRIND)
    parked = client._merchant_staging.yield_target(client.cache.get("prt_in"), state)
    assert parked is not None
    client.wire.add(_received_arrival(*parked))
    client.shop_actions(client.build_native_state(Goal.GRIND), ())
    now[0] += 31
    actions = client.shop_actions(client.build_native_state(Goal.GRIND), ())
    assert actions == (MoveTo(168, 124),)
    assert client._counter_lease.reason == "completed"
    assert sum(raw[:2] == b"\x90\x00" for raw in client.wire.sent) == 1
    client.wire.add(_received_arrival(168, 124))
    assert client.shop_actions(client.build_native_state(Goal.GRIND), ()) == ()


def test_bound_sale_refusal_releases_visit_without_retrying_a_server_failure():
    client, now = _client(at=(172, 129))
    client._keepalive_thread = threading.current_thread()
    client.wire.keepalive = lambda: None
    _answer_sale(client)
    send = client.wire._send

    def refuse(raw):
        if raw[:2] == b"\xc9\x00":
            client.wire.sent.append(raw)
            client.wire.add(_cb(1))
        else:
            send(raw)

    client.wire._send = refuse
    for _ in range(5):
        client.drain_native_events()
        now[0] += 2
    assert client._counter_lease.reason == "failed"
    assert client._npc.view is None
    assert client.shop_actions(client.build_native_state(Goal.GRIND), ()) == (MoveTo(168, 124),)
    assert client.wire.moves
    assert sum(raw[:2] == struct.pack("<H", 0x90) for raw in client.wire.sent) == 1


def test_retained_walk_and_talk_cannot_bypass_the_queue():
    clients, _ = _fleet()
    client = clients[100][0]
    state = client.build_native_state(Goal.GRIND)
    assert client._move(state, (173, 129)) == "staging_occupied"
    client.perform_native(TalkToNpc(DEALER))
    assert client.wire.moves == []
    assert client.wire.sent == []


def test_received_counter_body_blocks_retained_walk_into_another_free_band_cell():
    client, _ = _client(at=(173, 128))
    _receive_bodies(client, 999, {999: (173, 128), 100: (173, 129)}, set())
    state = client.build_native_state(Goal.GRIND)
    assert client._move(state, (172, 129)) == "staging_occupied"
    assert client.wire.moves == []


def test_batched_frames_preserve_arrival_order_across_self_and_peer_movement():
    client, _ = _client(at=(168, 124), aid=500)
    _receive_bodies(client, 500, {300: (170, 128)}, set())
    client.wire.add(_received_arrival(171, 128))
    _receive_bodies(client, 500, {100: (173, 128)}, set())
    state = client.build_native_state(Goal.GRIND)
    target = client.merchant_travel_target("prt_in", (state.x, state.y), (172, 130))
    assert target is not None
    assert max(abs(target[0] - 172), abs(target[1] - 130)) >= 2
    # Removing the first arrival leaves SELF ahead of the later lower-ID peer.
    client.wire.add(struct.pack("<HIB", 0x80, 300, 0))
    state = client.build_native_state(Goal.GRIND)
    target = client.merchant_travel_target("prt_in", (state.x, state.y), (172, 130))
    assert target is not None
    assert max(abs(target[0] - 172), abs(target[1] - 130)) == 1


def test_preexisting_crowded_band_yields_extra_holder_immediately():
    client, _ = _client(at=(173, 129), aid=200)
    _receive_bodies(client, 200, {100: (172, 129)}, set())
    state = client.build_native_state(Goal.GRIND)
    assert client._counter_lease.reason == "rotation"
    actions = client.shop_actions(state, ())
    assert actions
    assert isinstance(actions[0], MoveTo)
    assert max(abs(actions[0].x - 172), abs(actions[0].y - 130)) > 4
