"""Admitted merchant walks converge without script evaluations or decisions."""

import struct

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import merchant_staging, scripts
from robots.domain.actions import MoveTo, NpcShopSellOpen, TalkToNpc
from robots.domain.model import Goal
from tests.test_dealer_ring import _client
from tests.test_dealer_walkability import NEIGHBOURS
from tests.test_merchant_travel_patience import _field_client
from tests.test_playing_runtime import walk_ack
from tests.test_shop_sell_loop import DEALER, _c4, _c7, _inv, _weight


@pytest.fixture(autouse=True)
def fresh_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def test_pump_walks_to_received_adjacency_with_a_decide_in_flight():
    client, now = _client(at=(168, 127))
    client.npc_recovery_hold = True
    for _ in range(8):
        client.drain_native_events()
        target = client.wire.moves[-1]
        state = client.last_built_state
        assert state is not None
        client.wire.add(walk_ack((state.x, state.y), target), walk_ack(target, target))
        now[0] += 0.1
        if target in NEIGHBOURS:
            break
    else:
        pytest.fail("merchant approach never acquired a ring cell")
    client.drain_native_events()
    moves = list(client.wire.moves)
    for _ in range(10):
        now[0] += 1.0
        client.drain_native_events()
    assert client.wire.moves == moves
    assert client.wire.sent == []  # The pump never authors a click or shop selection.
    state = client.build_native_state(Goal.GRIND)
    outcome = scripts._merchant_step(
        state, reachable=client.merchant_reachable, travel_target=client.merchant_travel_target
    )
    assert outcome is not None
    assert outcome.actions == (TalkToNpc(DEALER),)
    client.perform_native(outcome.actions[0])
    client.wire.add(_c4(DEALER))
    state = client.build_native_state(Goal.GRIND)
    actions = client.shop_actions(state, ())
    assert actions is not None
    assert len(actions) == 1
    assert isinstance(actions[0], NpcShopSellOpen)
    client.perform_native(actions[0])
    client.wire.add(_c7(((6, 12, 12),)))
    actions = client.shop_actions(client.build_native_state(Goal.GRIND), ())
    assert actions is not None
    client.perform_native(actions[0])
    assert client.wire.sent[-1] == struct.pack("<HHHH", 0xC9, 8, 6, 1)


def test_pending_walk_uses_progress_clock_instead_of_pump_or_decide_cadence():
    client, now = _client(at=(168, 127))
    client.drain_native_events()
    assert len(client.wire.moves) == 1
    first = client.wire.moves[0]
    now[0] += 0.9
    client.drain_native_events()
    assert client.wire.moves == [first]
    client.wire.add(walk_ack((168, 127), first))
    client.drain_native_events()  # Received progress refreshes the one-second clock.
    now[0] += 0.9
    client.drain_native_events()
    assert client.wire.moves == [first]
    now[0] += 0.1
    client.drain_native_events()
    assert len(client.wire.moves) == 2
    assert str(client.last_move_outcome["pending_reason"]).startswith("no_progress(")


def test_pump_never_replaces_an_existing_decide_walk():
    client, now = _client(at=(168, 127))
    client.perform_native(MoveTo(168, 126))
    for _ in range(5):
        now[0] += 0.1
        client.drain_native_events()
    assert client.wire.moves == [(168, 126)]


@pytest.mark.parametrize("barrier", ["pose", "one_hp", "passive", "grid", "ring", "cooldown"])
def test_pump_preserves_admission_and_actuation_barriers(barrier, monkeypatch):
    client, now = _client(at=(168, 127), blocked=NEIGHBOURS if barrier == "ring" else ())
    if barrier == "pose":
        raw = bytearray(34)
        struct.pack_into("<HI", raw, 0, 0x08C8, client.wire.aid)
        raw[29] = 2
        client.wire.add(bytes(raw))
    elif barrier == "passive":
        client.mechanical_recovery_allowed = False
    elif barrier == "one_hp":
        client.wire.status_params[5] = 1
    elif barrier == "grid":
        client.cache = None
    elif barrier == "cooldown":
        monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
        state = client.build_native_state(Goal.GRIND)
        assert scripts._merchant_trip_allows(state, scripts.MERCHANT_ROUTE["prt_in"])
        now[0] += 301.0
        assert not scripts._merchant_trip_allows(state, scripts.MERCHANT_ROUTE["prt_in"])
    client.drain_native_events()
    assert client.wire.moves == []
    assert client.wire.sent == []


def test_empty_stock_releases_outbound_pump_and_walks_toward_field():
    client, _ = _client(at=(168, 127))
    client.wire.add(struct.pack("<HHH", 0x00AF, 6, 1))
    client.drain_native_events()
    assert client.wire.moves
    assert client.wire.moves[-1][1] < 127
    assert not scripts.merchant_trip_active(client.wire.char_name)
    assert client.wire.sent == []


def test_keepalive_itself_uses_grid_ring_without_native_event_or_script_dispatch(monkeypatch):
    client, _ = _client(at=(172, 128))
    monkeypatch.setattr(merchant_staging, "_free_approach_cells", lambda *_: [])
    client.build_native_state(Goal.GRIND)
    client._keepalive()
    assert client.wire.moves == [(172, 129)]


def test_received_shop_contact_is_left_to_the_existing_chain():
    client, _ = _client(at=(172, 129))
    client.perform_native(TalkToNpc(DEALER))
    client.wire.add(_c4(DEALER))
    sent = list(client.wire.sent)
    client.drain_native_events()
    assert client.wire.moves == []
    assert client.wire.sent == sent


@pytest.mark.parametrize("stock", [1, 2])
def test_field_trip_waits_for_received_batch_before_pump_travel(stock):
    cache = MapCache((WalkMap("prt_fild08", 400, 400, bytes(400 * 400)),))
    client, _ = _field_client(cache, (169, 300))
    client.wire.add(_inv(((6, 909, stock), (7, 1201, 1))), _weight())
    client.drain_native_events()
    assert client.wire.moves == ([(169, 317)] if stock == 2 else [])
    assert scripts.merchant_trip_active(client.wire.char_name) is (stock == 2)
    if stock == 1:
        client.wire.add(_inv(((6, 909, 2), (7, 1201, 1))))
        client.drain_native_events()
        assert client.wire.moves == [(169, 317)]


def test_pump_obstructed_walk_keeps_the_server_fourteen_cell_limit():
    tiles = bytearray(400 * 400)
    for x in range(160, 179):
        tiles[x + 305 * 400] = 1
    cache = MapCache((WalkMap("prt_fild08", 400, 400, bytes(tiles)),))
    client, _ = _field_client(cache, (169, 300))
    client.wire.add(_inv(((6, 909, 2), (7, 1201, 1))), _weight())
    client.drain_native_events()
    assert len(client.wire.moves) == 1
    assert client.last_move_outcome["trip_leg_cells_sent"] == 14


def test_map_change_releases_old_walk_and_resolves_the_next_merchant_leg():
    cache = MapCache(
        WalkMap(name, 400, 400, bytes(400 * 400)) for name in ("prt_fild08", "prontera")
    )
    client, _ = _field_client(cache, (169, 300))
    client.wire.add(_inv(((6, 909, 2), (7, 1201, 1))), _weight())
    client.drain_native_events()
    assert client.wire.moves == [(169, 317)]
    client.wire.add(struct.pack("<H16sHH", 0x0091, b"prontera", 177, 225))
    client.drain_native_events()
    assert len(client.wire.moves) == 2
    assert client.wire.moves[-1] != (169, 317)
    state = client.last_built_state
    assert state is not None
    assert state.map_name == "prontera"


def test_stalled_admitted_trip_yields_to_existing_retry_cooldown(monkeypatch):
    client, now = _client(at=(172, 128))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    monkeypatch.setattr(client.wire, "keepalive", lambda: None, raising=False)
    client.drain_native_events()
    assert client.wire.moves == [(172, 129)]
    now[0] += 60.0
    client.drain_native_events()
    assert client.wire.moves == [(172, 129)]
    assert not scripts.merchant_trip_active(client.wire.char_name)
    now[0] += 119.0
    client.drain_native_events()
    assert len(client.wire.moves) == 1
    now[0] += 1.0
    client.drain_native_events()
    assert client.wire.moves == [(172, 129), (172, 129)]
