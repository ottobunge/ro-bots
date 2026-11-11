"""Leg-92 offline received-body replay on the pinned dealer-room geometry."""

import struct
from dataclasses import replace

import pytest

from robots.adapters.native_navigation import MapCache
from robots.app import scripts
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import MoveTo
from robots.domain.model import Goal
from tests.test_dealer_ring import _client, _step
from tests.test_native_navigation import SOURCE
from tests.test_shop_sell_loop import _dealer, _inv


@pytest.fixture(autouse=True)
def _fresh_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _received_arrival(x: int, y: int) -> bytes:
    move = bytes(
        (
            x >> 2,
            ((x & 3) << 6) | (y >> 4),
            ((y & 15) << 4) | (x >> 6),
            ((x & 63) << 2) | (y >> 8),
            y & 255,
            0,
        )
    )
    return struct.pack("<HI", 0x87, 0) + move


def _receive_bodies(
    client: PlayingClient, aid: int, positions: dict[int, tuple[int, int]], departed: set[int]
) -> None:
    for peer, point in positions.items():
        if peer == aid:
            continue
        if peer in departed:
            client.wire.add(struct.pack("<HIB", 0x80, peer, 0))
        else:
            body = bytearray(_dealer(point, npc_id=peer))
            body[4] = 0
            client.wire.add(bytes(body))


def test_sold_owner_and_three_waiters_clear_the_corridor_and_handover_within_five_minutes(
    caplog, record_property
):
    # Exact leg-92 post-sale positions; each client sees only received bodies.
    positions = {
        2200002: (169, 127),  # zeny_wing, Clover
        2200003: (170, 128),  # PipinWalker, Jellopy
        2200004: (171, 128),  # xXLunasongXx, already sold
        2200005: (169, 128),  # PoringMuffin14, Jellopy
    }
    clients = {aid: _client(name=str(aid), at=p, aid=aid) for aid, p in positions.items()}
    for client, _ in clients.values():
        client.cache = MapCache.load(
            SOURCE / "db/map_cache.dat", SOURCE / "db/pre-re/map_cache.dat"
        )
    clients[2200002][0].wire.add(_inv(((6, 705, 1), (7, 1201, 1))))
    sold = {2200004}
    sale_received = set()
    handed = {}
    departed: set[int] = set()
    for tick in range(150):
        for aid, (client, now) in clients.items():
            if aid in departed:
                continue
            now[0] = 100.0 + tick * 2
            client.wire.add(_received_arrival(*positions[aid]))
            _receive_bodies(client, aid, positions, departed)
            if aid in sold and aid not in sale_received:
                client.wire.add(struct.pack("<HHH", 0xAF, 6, 1))
                client._merchant_returning = True
                sale_received.add(aid)
            state = client.build_native_state(Goal.GRIND)
            if aid not in sold and max(abs(state.x - 172), abs(state.y - 130)) <= 1:
                handed[aid] = tick * 2
                # Model a received completed sale; shop authority has its own C4/C7 tests.
                sold.add(aid)
                continue
            actions = _step(client, state)
            for action in actions:
                if isinstance(action, MoveTo):
                    before = len(client.wire.moves)
                    client._move(state, (action.x, action.y))
                    if len(client.wire.moves) > before:
                        positions[aid] = client.wire.moves[-1]
            if aid in sold and positions[aid] == (168, 124):
                departed.add(aid)
        if len(handed) == 3:
            break
    assert set(handed) == {2200002, 2200003, 2200005}, (handed, positions, departed)
    record_property("handover_seconds", str(handed))
    assert max(handed.values()) < 300
    assert min(handed.values()) < 120
    assert 2200004 in departed
    messages = [record.getMessage() for record in caplog.records]
    assert any("dealer_queue_yield" in message for message in messages)
    assert any("dealer_ring_handover" in message for message in messages)


def test_dealer_dispatch_rechecks_the_received_corridor_before_sending():
    client, _ = _client(at=(169, 128))
    client.cache = MapCache.load(SOURCE / "db/map_cache.dat", SOURCE / "db/pre-re/map_cache.dat")
    state = client.build_native_state(Goal.GRIND)
    assert _step(client, state) == (MoveTo(172, 129),)
    blocked = replace(state, occupied_cells=((170, 128),))
    assert client._move(blocked, (172, 129)) == "staging_occupied"
    assert client.wire.moves == []
    assert client._move(state, (172, 129)) == "dispatched"
    assert client.wire.moves == [(170, 128)]
