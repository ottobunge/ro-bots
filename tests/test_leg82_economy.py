"""Leg-82 offline contracts for dealer allocation and received inventory deltas."""

import struct
from dataclasses import replace

import pytest

from robots.adapters.native_gameplay import NativeGameplayTracker
from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import scripts
from robots.app.playing_runtime import PlayingClient
from robots.app.scripts import MERCHANT_ROUTE, _merchant_step, merchant_drive_cell
from robots.domain.actions import GameAction, MoveTo
from robots.domain.model import BotState, Goal
from tests.test_merchant_staging import _client
from tests.test_native_gameplay_repairs import initial
from tests.test_native_shop_purchase import acquisition, known_facts, offered

DEALER = MERCHANT_ROUTE["prt_in"]
RING = tuple((172 + dx, 130 + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)


@pytest.fixture(autouse=True)
def _clear_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _dealer_selection(client: PlayingClient, state: BotState) -> tuple[GameAction, ...]:
    client._last_built_state = state
    result = _merchant_step(
        state, reachable=client.merchant_reachable, travel_target=client.merchant_travel_target
    )
    assert result is not None
    return result.actions


def test_two_dealer_agents_keep_distinct_talk_range_cells():
    a, state_a, _ = _client(name="a")
    b, state_b, _ = _client(name="b")
    state_a = replace(state_a, map_name="prt_in", x=168, y=128)
    state_b = replace(state_b, map_name="prt_in", x=168, y=129)
    first = _dealer_selection(a, state_a)
    assert len(first) == 1
    assert isinstance(first[0], MoveTo)
    first_cell = (first[0].x, first[0].y)
    second = _dealer_selection(b, replace(state_b, occupied_cells=(first_cell,)))
    assert len(second) == 1
    assert isinstance(second[0], MoveTo)
    assert first_cell != (second[0].x, second[0].y)
    assert first_cell in RING
    assert (second[0].x, second[0].y) in RING


def test_dealer_saturation_falls_outward_with_named_selection_and_releases(caplog):
    client, state, _ = _client()
    state = replace(state, map_name="prt_in", x=168, y=128, occupied_cells=RING)
    actions = _dealer_selection(client, state)
    assert len(actions) == 1
    assert isinstance(actions[0], MoveTo)
    cell = (actions[0].x, actions[0].y)
    assert 2 <= max(abs(cell[0] - 172), abs(cell[1] - 130)) <= 4
    assert "dealer_outer_fallback" in caplog.text
    assert "preferred_chebyshev<=1=unavailable" in caplog.text
    assert _dealer_selection(client, state) == ()
    assert caplog.text.count("dealer_outer_fallback") == 1
    freed = replace(state, occupied_cells=tuple(p for p in RING if p != (171, 129)))
    assert _dealer_selection(client, freed) == (MoveTo(171, 129),)


def test_dealer_inner_walkability_precedes_outward_selection(caplog):
    client, state, _ = _client()
    assert client.cache is not None
    grid = client.cache.get("prt_in")
    tiles = bytearray(grid.tiles)
    for cell in RING:
        if cell != (173, 131):
            tiles[cell[0] + cell[1] * grid.width] = 1
    client.cache = MapCache((WalkMap("prt_in", grid.width, grid.height, bytes(tiles)),))
    state = replace(state, map_name="prt_in", x=168, y=128)
    assert _dealer_selection(client, state) == (MoveTo(173, 131),)
    assert "dealer_outer_fallback" not in caplog.text


def _deletion(pid: int, index: int, amount: int) -> bytes:
    return (
        struct.pack("<HHH", pid, index, amount)
        if pid == 0xAF
        else struct.pack("<HHHH", pid, 6, index, amount)
    )


@pytest.mark.parametrize("pid", [0xAF, 0x7FA])
@pytest.mark.parametrize("amount", [1, 3])
def test_received_delete_keeps_exact_indexed_stock_and_replay_safety(pid, amount):
    tracker = NativeGameplayTracker(999)
    frames = (*initial(), (3, 3.0, 0xB0, struct.pack("<HHi", 0xB0, 24, 30)))
    assert tracker.consume_snapshot(1, 0, frames)
    assert tracker.indexed_inventory == ((2, 501, 3),)
    frames += ((4, 4.0, pid, _deletion(pid, 2, amount)),)
    assert tracker.consume_snapshot(1, 0, frames)
    expected = ((2, 501, 3 - amount),) if amount < 3 else ()
    assert tracker.indexed_inventory == expected
    assert tracker.consume_snapshot(1, 0, frames)
    assert tracker.indexed_inventory == expected


@pytest.mark.parametrize("pid", [0xAF, 0x7FA])
@pytest.mark.parametrize(("index", "amount"), [(2, 0), (2, 4), (1, 1), (9, 1)])
def test_unreconciled_delete_stays_unknown_after_weight(pid, index, amount):
    tracker = NativeGameplayTracker(999)
    assert tracker.consume_snapshot(1, 0, initial())
    tracker.ingest(3, 3.0, 0xB0, struct.pack("<HHi", 0xB0, 24, 30))
    tracker.ingest(4, 4.0, pid, _deletion(pid, index, amount))
    tracker.ingest(5, 5.0, 0xB0, struct.pack("<HHi", 0xB0, 24, 0))
    assert tracker.indexed_inventory is None


@pytest.mark.parametrize("pid", [0xAF, 0x7FA])
def test_real_received_inventory_delete_and_knife_offer_authorize_purchase(monkeypatch, pid):
    wire, client, receive, sent = offered(monkeypatch)
    # The received login equipment row has client index 9, quantity one.
    receive(_deletion(pid, 9, 1), struct.pack("<HHi", 0xB0, 24, 0))
    state = client.build_native_state(Goal.GRIND)
    assert state.inventory_known
    assert state.inventory == {}
    assert state.shop_offer is not None
    assert any(row.item_id == 1201 for row in state.shop_offer.rows)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61)
    assert action is not None
    client.perform_native(action)
    assert sent[-1] == bytes.fromhex("c80008000100b104")


def test_unknown_inventory_with_real_knife_offer_refuses_purchase(monkeypatch):
    wire, client, receive, sent = offered(monkeypatch)
    receive(_deletion(0x7FA, 77, 1), struct.pack("<HHi", 0xB0, 24, 0))
    assert not client.build_native_state(Goal.GRIND).inventory_known
    assert client.bind_shop_purchase_facts(known_facts(wire))
    assert client.npc_shop_purchase(maximum_zeny=61) is None
    assert len(sent) == 3


def test_selling_received_loot_keeps_the_received_knife_and_weapon_release(monkeypatch):
    _wire, client, receive, _sent = offered(monkeypatch)
    receive(acquisition(index=3, item=915, amount=2), struct.pack("<HHi", 0xB0, 24, 420))
    state = client.build_native_state(Goal.GRIND)
    assert state.inventory == {"915": 2, "1201": 1}
    receive(_deletion(0x7FA, 3, 2), struct.pack("<HHi", 0xB0, 24, 400))
    state = client.build_native_state(Goal.GRIND)
    assert state.inventory_known
    assert state.inventory == {"1201": 1}
    assert merchant_drive_cell(replace(state, map_name="prt_in")) is None
    # A map warp neither loses the complete baseline nor rearms unknown stock.
    receive(struct.pack("<H16sHH", 0x91, b"prt_in", 168, 128))
    state = client.build_native_state(Goal.GRIND)
    assert state.inventory_known
    assert state.inventory == {"1201": 1}


def test_all_dealer_cells_unwalkable_hold_with_named_preference(caplog):
    client, state, _ = _client()
    grid = WalkMap("prt_in", 400, 400, bytes([1]) * 400 * 400)
    client.cache = MapCache((grid,))
    state = replace(state, map_name="prt_in", x=168, y=128)
    assert _dealer_selection(client, state) == ()
    assert "hold dealer_occupied" in caplog.text
    assert "preferred_chebyshev<=1=unavailable" in caplog.text
    assert "dealer_outer_fallback" not in caplog.text
