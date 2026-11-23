"""Admitted merchant walks converge without script evaluations or decisions."""

import logging
import struct

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import merchant_staging, scripts
from robots.app.merchant_trip import MERCHANT_RETRY_COOLDOWN_S
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
    if barrier == "cooldown":
        # The retry clock limits outbound trips, never the farm-side return.
        assert client.wire.moves == [(168, 126)]
    else:
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


def test_stalled_admitted_trip_escalates_then_returns_during_retry_cooldown(monkeypatch, caplog):
    """A stalled dealer approach is re-routed, then released, then walks home.

    Leg-119 reconciliation of the 60 s route release: on the dealer map the
    contact ladder owns the lease (reroute -> counter-cell -> release), so
    the route bound alone no longer returns the agent mid-approach; the
    ladder's release lands in the same retry cooldown and the return leg.
    """
    caplog.set_level(logging.WARNING)
    client, now = _client(at=(172, 128))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    monkeypatch.setattr(client.wire, "keepalive", lambda: None, raising=False)
    bot = client.wire.char_name
    client.drain_native_events()
    assert client.wire.moves == [(172, 129)]
    now[0] += 60.0
    client.drain_native_events()
    assert scripts.merchant_trip_active(bot)  # inside the ladder bound: no release
    assert "contact_walk_escalated" not in caplog.text
    now[0] += 90.0
    client.drain_native_events()
    assert scripts.merchant_trip_active(bot)  # rerouted, not released
    assert "step=reroute" in caplog.text
    now[0] += 180.0
    client.drain_native_events()
    assert "step=counter_cell" in caplog.text  # second escalation window
    assert scripts.merchant_trip_active(bot)  # the ladder still owns the lease
    now[0] += 120.0
    client.drain_native_events()
    assert "merchant-drive: contact_walk_released_farm" in caplog.text
    assert not scripts.merchant_trip_active(bot)  # ladder exhausted: released to farm
    assert client.wire.moves[-1][1] < 129  # the pump walks home during the cooldown


DEALER_CELL = (172, 130)


def _dealer_chebyshev(cell: tuple[int, int]) -> int:
    return max(abs(cell[0] - DEALER_CELL[0]), abs(cell[1] - DEALER_CELL[1]))


def _quiet_keepalive(client) -> None:
    """Minutes of pumped wall clock: the 6-byte keepalive send stays silent."""
    client.wire.keepalive = lambda: None


def _stall(client, now, until: float, step: float = 10.0) -> None:
    """Advance the wall clock without any walk feedback: the approach stalls."""
    while now[0] < until:
        now[0] += step
        client.drain_native_events()


def test_stalled_contact_walk_escalates_reroute_at_bounded_timeout(caplog):
    """Leg-119 named hop: the dealer approach is wall-clock bounded, never free.

    pending_walk 2216 holds vs 0 authored contacts - the approach walked in
    place all window. Inside the bound nothing escalates; past it the pump
    names the escalation (contact_walk_escalated step=reroute) and clears the
    approach memos so the next allocation is fresh.
    """
    caplog.set_level(logging.WARNING)
    client, now = _client(at=(168, 126))
    _quiet_keepalive(client)
    client.drain_native_events()
    assert client.wire.moves
    assert scripts.merchant_trip_active(client.wire.char_name)
    bound_t = now[0]
    for _ in range(8):  # 80 s of stall: still inside the bound
        now[0] += 10.0
        client.drain_native_events()
        assert "contact_walk_escalated" not in caplog.text
    _stall(client, now, bound_t + 90.5)
    assert "merchant-drive: contact_walk_escalated" in caplog.text
    assert "step=reroute" in caplog.text


def test_contact_walk_progress_renews_the_bound_instead_of_escalating(caplog):
    """A converging approach never escalates: received progress re-arms the clock."""
    caplog.set_level(logging.WARNING)
    client, now = _client(at=(168, 127))
    _quiet_keepalive(client)
    client.drain_native_events()
    for _ in range(8):
        target = client.wire.moves[-1]
        state = client.last_built_state
        assert state is not None
        client.wire.add(walk_ack((state.x, state.y), target), walk_ack(target, target))
        now[0] += 15.0  # slower than the bound would allow a stalled walk
        client.drain_native_events()
        if target in NEIGHBOURS:
            break
    else:
        pytest.fail("converging approach never acquired a ring cell")
    assert "contact_walk_escalated" not in caplog.text


def test_contact_ladder_falls_back_to_counter_cell_then_releases_to_farm(monkeypatch, caplog):
    """The ladder is reroute -> counter-cell -> release; no permanent park.

    A stalled approach is re-routed, then walks the staging's outer counter
    cell, then the arm releases through the trip retry cooldown and the pump
    walks the agent home. After the cooldown a fresh trip re-admits (leg-117's
    lesson: a recovery must never end in a permanent parking lot).
    """
    caplog.set_level(logging.WARNING)
    client, now = _client(at=(168, 126))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    client._zeny_seed = 80  # the buy budget re-admits a fresh trip on the field
    _quiet_keepalive(client)
    client.drain_native_events()
    bound_t = now[0]
    _stall(client, now, bound_t + 90.5)
    assert "step=reroute" in caplog.text
    _stall(client, now, bound_t + 180.5)
    assert "step=counter_cell" in caplog.text
    # the fallback walk targeted the staging's OUTER counter cell, not the ring
    wire_target = client.last_move_outcome.get("wire_target")
    assert isinstance(wire_target, tuple)
    assert _dealer_chebyshev(wire_target) >= 2
    _stall(client, now, bound_t + 270.5)
    assert "merchant-drive: contact_walk_released_farm" in caplog.text
    bot = client.wire.char_name
    assert not scripts.merchant_trip_active(bot)  # released through the retry cooldown
    now[0] += 10.0
    client.drain_native_events()
    assert client.wire.moves[-1][1] < 126  # the pump walks home, no parking
    assert client.wire.sent == []  # an escalation never authors a contact
    # Received field arrival releases the return latch; past the cooldown the
    # buy budget re-admits a fresh trip (leg-117: never a permanent release).
    state = client.last_built_state
    assert state is not None
    while (state.x, state.y) != (168, 124):
        target = client.wire.moves[-1]
        client.wire.add(walk_ack((state.x, state.y), target), walk_ack(target, target))
        now[0] += 1.0
        client.drain_native_events()
        state = client.last_built_state
        assert state is not None
    cache = client.cache
    assert cache is not None
    client.cache = MapCache((cache.get("prt_in"), WalkMap("prt_fild08", 400, 400, bytes(160000))))
    client.wire.add(struct.pack("<H16sHH", 0x0091, b"prt_fild08", 169, 300))
    now[0] += MERCHANT_RETRY_COOLDOWN_S
    client.drain_native_events()
    assert scripts.merchant_trip_active(bot)  # a fresh trip re-admits after cooldown


def test_progress_after_reroute_preserves_the_spent_escalation_budget(monkeypatch, caplog):
    client, now = _client(at=(168, 126))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    _quiet_keepalive(client)
    client.drain_native_events()
    now[0] += 90.0
    client.drain_native_events()
    assert "step=reroute" in caplog.text
    client.wire.add(walk_ack((168, 126), (169, 127)), walk_ack((169, 127), (169, 127)))
    now[0] += 1.0
    client.drain_native_events()
    caplog.clear()
    now[0] += 90.0
    client.drain_native_events()
    assert "step=counter_cell" in caplog.text
    assert "step=reroute" not in caplog.text


def test_contact_progress_at_deadline_renews_the_route_lease(monkeypatch, caplog):
    client, now = _client(at=(168, 126))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    _quiet_keepalive(client)
    client.drain_native_events()
    # Progress need not shorten the obstacle-aware route distance; it still
    # renews the contact clock and must beat the generic trip timeout.
    monkeypatch.setattr(client, "_merchant_route_distance", lambda _: (172, 130, 4))
    client.wire.add(walk_ack((168, 126), (169, 127)), walk_ack((169, 127), (169, 127)))
    now[0] += 90.0
    client.drain_native_events()
    assert scripts.merchant_trip_active(client.wire.char_name)
    assert "merchant_trip_released_no_progress" not in caplog.text
    assert "contact_walk_escalated" not in caplog.text


def test_counter_fallback_remains_the_target_until_received_arrival(monkeypatch):
    client, now = _client(at=(168, 126))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    _quiet_keepalive(client)
    targets = []
    perform = client._perform_move

    def record(state, target):
        targets.append(target)
        perform(state, target)

    monkeypatch.setattr(client, "_perform_move", record)
    client.drain_native_events()
    for _ in range(2):
        now[0] += 90.0
        client.drain_native_events()
    fallback = targets[-1]
    assert _dealer_chebyshev(fallback) >= 2
    now[0] += 2.0
    client.drain_native_events()
    assert targets[-1] == fallback
    client.wire.add(walk_ack((168, 126), fallback), walk_ack(fallback, fallback))
    now[0] += 1.0
    client.drain_native_events()
    assert targets[-1] in NEIGHBOURS


def test_nonconverging_walk_frames_cannot_hold_the_pump_forever(monkeypatch, caplog):
    client, now = _client(at=(168, 126))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    _quiet_keepalive(client)
    client.npc_recovery_hold = True  # pending cognition does not gate movement
    client.drain_native_events()
    first = client.wire.moves[-1]
    client.wire.add(walk_ack((168, 126), first))
    now[0] += 1.0
    client.drain_native_events()
    for _ in range(9):
        # Fresh walk frames refresh the pending clock, but no received cell
        # approaches the dealer. The contact timeout must still reroute.
        client.wire.add(walk_ack((168, 126), first))
        now[0] += 10.0
        client.drain_native_events()
        state = client.last_built_state
        assert state is not None
        client._perform_move(state, first)  # refused authorship cannot steal ownership
    assert "step=reroute" in caplog.text
    assert len(client.wire.moves) >= 2
    for _ in range(19):
        client.wire.add(walk_ack((168, 126), client.wire.moves[-1]))
        now[0] += 10.0
        client.drain_native_events()
    assert "step=counter_cell" in caplog.text
    assert "contact_walk_released_farm" in caplog.text
    state = client.last_built_state
    assert state is not None
    now[0] += 1.0
    client.drain_native_events()
    assert client.wire.moves[-1][1] < state.y
    assert not scripts.merchant_trip_active(client.wire.char_name)
    assert client.wire.sent == []


def test_escalation_preserves_an_unrelated_authored_walk(monkeypatch, caplog):
    client, now = _client(at=(168, 126))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    _quiet_keepalive(client)
    client.perform_native(MoveTo(168, 125))
    point = client.wire.moves[-1]
    client.wire.add(walk_ack((168, 126), point))
    client.drain_native_events()
    for _ in range(9):
        now[0] += 10.0
        client.wire.add(walk_ack((168, 126), point))
        client.drain_native_events()
    assert "step=reroute" in caplog.text
    assert client.wire.moves == [point]


def test_leaving_dealer_map_discards_contact_fallback(monkeypatch):
    client, now = _client(at=(168, 126))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    _quiet_keepalive(client)
    client.drain_native_events()
    for _ in range(2):
        now[0] += 90.0
        client.drain_native_events()
    fallback = client._contact_fallback_target
    assert fallback is not None
    cache = client.cache
    assert cache is not None
    client.cache = MapCache((cache.get("prt_in"), WalkMap("prontera", 400, 400, bytes(160000))))
    client.wire.add(struct.pack("<H16sHH", 0x0091, b"prontera", 177, 225))
    client.drain_native_events()
    assert client._contact_fallback_target is None
    assert client._contact_approach.identity is None


@pytest.mark.parametrize("cadence", [0.25, 13.6, 14.6, 91.0])
def test_contact_escalation_is_paced_by_elapsed_seconds(cadence, monkeypatch, caplog):
    client, now = _client(at=(168, 126))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    _quiet_keepalive(client)
    client.drain_native_events()
    start = now[0]
    while now[0] + cadence < start + 90.0:
        now[0] += cadence
        client.drain_native_events()
        assert "contact_walk_escalated" not in caplog.text
    now[0] = max(now[0] + cadence, start + 90.0)
    client.drain_native_events()
    assert "step=reroute" in caplog.text
