"""Leg-103: grid-owned dealer geometry and an explicit eligible buy arm."""

import logging
from dataclasses import replace

import pytest

from robots.app import merchant_staging, scripts
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import MoveTo, NpcShopBuySelection, TalkToNpc
from robots.domain.model import Goal
from tests.test_dealer_ring import _client, _step
from tests.test_dealer_walkability import NEIGHBOURS
from tests.test_shop_sell_loop import DEALER, _c4, _inv


@pytest.fixture(autouse=True)
def fresh_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _buyer(inventory: tuple[tuple[int, int, int], ...] = (), zeny: int = 100) -> PlayingClient:
    template, now = _client(at=(172, 129))
    wire = template.wire
    wire.frames = [
        (seq, at, pid, _inv(inventory) if pid == 0x991 else raw)
        for seq, at, pid, raw in wire.frames
    ]
    client = PlayingClient(wire, cache=template.cache, monotonic=lambda: now[0])
    client._zeny_seed = zeny
    client.build_native_state(Goal.GRIND)
    client._npc_names[DEALER] = "Weapon Dealer#prt"
    return client


def test_ring_inventory_is_derived_from_grid_without_script_compass(monkeypatch):
    client, _ = _client(at=(172, 128), blocked=((171, 129), (171, 130), (171, 131)))
    state = client.build_native_state(Goal.GRIND)
    # Script occupancy helpers have no walkability authority. The runtime must
    # enumerate its grid even when a script's preference inventory is empty.
    monkeypatch.setattr(merchant_staging, "_free_approach_cells", lambda *_: [])
    assert _step(client, state) == (MoveTo(172, 129),)


def test_unwalkable_cells_never_enter_matching_candidates(monkeypatch):
    client, _ = _client(at=(172, 128), blocked=((171, 129), (171, 130), (171, 131)))
    state = client.build_native_state(Goal.GRIND)
    original = merchant_staging._ring_allocation
    seen = []

    def allocate(grid, position, cells, blocked, origins):
        seen.extend(cells)
        assert all(grid.walkable(cell) for cell in cells)
        return original(grid, position, cells, blocked, origins)

    monkeypatch.setattr(merchant_staging, "_ring_allocation", allocate)
    assert _step(client, state) == (MoveTo(172, 129),)
    assert set(seen) == set(NEIGHBOURS) - {(171, 129), (171, 130), (171, 131)}


def test_missing_walkable_ring_refuses_instead_of_parking_at_range_two(caplog):
    client, _ = _client(at=(172, 128), blocked=NEIGHBOURS)
    assert _step(client, client.build_native_state(Goal.GRIND)) == ()
    assert "dealer_ring_unwalkable" in caplog.text
    assert "dealer_outer_fallback" not in caplog.text


def test_ring_uses_received_dealer_position_not_only_route_hint():
    client, _ = _client(at=(171, 129))
    state = client.build_native_state(Goal.GRIND)
    # The script accepts this received dealer within one of the route hint.
    # Its west ring must not be allocated: that would be range two to the NPC.
    state = replace(
        state,
        nearby=tuple(replace(a, x=173) if a.id == DEALER else a for a in state.nearby),
    )
    (move,) = _step(client, state)
    assert isinstance(move, MoveTo)
    assert max(abs(move.x - 173), abs(move.y - 130)) <= 1
    assert (move.x, move.y) != (173, 130)


def test_idle_eligible_buy_arm_authors_click_then_received_c4_selection(caplog):
    caplog.set_level(logging.WARNING)
    client = _buyer()
    state = client.build_native_state(Goal.GRIND)
    assert scripts.merchant_admission_refusal(state) is None
    assert client.shop_actions(state, ()) == (TalkToNpc(DEALER),)
    assert "buy_armed" in caplog.text
    client.perform_native(TalkToNpc(DEALER))
    client.wire.add(_c4(DEALER))
    state = client.build_native_state(Goal.GRIND)
    actions = client.shop_actions(state, ())
    assert actions
    assert isinstance(actions[0], NpcShopBuySelection)
    assert "buy_authored" in caplog.text
    client.perform_native(actions[0])
    assert client.wire.sent[-1][:2] == b"\xc5\x00"
    assert client.wire.sent[-1][-1] == 0


@pytest.mark.parametrize(("inventory", "zeny"), [(((7, 1201, 1),), 140), ((), 49)])
def test_buy_arm_keeps_weapon_release_and_wallet_refusals(inventory, zeny):
    client = _buyer(inventory, zeny)
    state = client.build_native_state(Goal.GRIND)
    assert scripts.merchant_admission_refusal(state) is not None
    assert client.shop_actions(state, ()) is None
    assert client.wire.sent == []


def test_counter_wall_does_not_give_distant_waiter_the_only_remaining_slot():
    from robots.adapters.native_navigation import MapCache  # noqa: PLC0415
    from tests.test_native_navigation import SOURCE  # noqa: PLC0415

    grid = MapCache.load(SOURCE / "db/map_cache.dat", SOURCE / "db/pre-re/map_cache.dat").get(
        "prt_in"
    )
    # Matching has one slot left. The west waiter looks closer across the
    # counter, but its real route is much longer than the east waiter's.
    assert merchant_staging._ring_allocation(
        grid,
        (173, 128),
        {(172, 131)},
        {(172, 130), (169, 131)},
        (((169, 131), False), ((173, 128), True)),
    ) == (172, 131)


def test_missing_client_grid_refuses_with_named_telemetry(caplog):
    client, _ = _client(at=(172, 128))
    client.cache = None
    assert _step(client, client.build_native_state(Goal.GRIND)) == ()
    assert "dealer_ring_grid_unavailable" in caplog.text


def test_walkable_but_disconnected_ring_names_geometry_refusal(caplog):
    client, _ = _client(at=(169, 128), blocked=tuple((170, y) for y in range(200)))
    assert _step(client, client.build_native_state(Goal.GRIND)) == ()
    assert "dealer_ring_unreachable" in caplog.text
    assert "dealer_outer_fallback" not in caplog.text


def test_named_received_overlap_requires_a_different_walkable_cell():
    from robots.domain.model import ActorRef  # noqa: PLC0415

    client, _ = _client(at=(172, 129))
    state = client.build_native_state(Goal.GRIND)
    state = replace(
        state,
        nearby=(*state.nearby, ActorRef(99, "peer", "player", 0.0, x=172, y=129)),
    )
    (move,) = _step(client, state)
    assert isinstance(move, MoveTo)
    assert (move.x, move.y) != (172, 129)


def test_counter_lease_uses_the_same_received_dealer_ring():
    from robots.app.merchant_counter_lease import MerchantCounterLease  # noqa: PLC0415

    client, _ = _client(at=(174, 130))
    state = client.build_native_state(Goal.GRIND)
    state = replace(
        state,
        nearby=tuple(replace(a, x=173) if a.id == DEALER else a for a in state.nearby),
    )
    lease = MerchantCounterLease()
    lease.observe(state, 100.0)
    lease.observe(state, 281.0)
    assert lease.reason == "expired"
