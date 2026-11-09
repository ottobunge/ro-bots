"""Offline leg-81 contracts: staging allocation, bounded holds and warp evidence."""

import struct
from dataclasses import replace

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import scripts
from robots.app.playing_runtime import PlayingClient
from robots.app.scripts import MERCHANT_ROUTE, _merchant_step
from robots.domain.actions import GameAction, MoveTo
from robots.domain.model import ActorRef, BotState, Goal
from tests.test_native_navigation import SOURCE
from tests.test_playing_runtime import Wire, entry_at
from tests.test_population_runner_transport_reporting import RUNNER

STAGING = MERCHANT_ROUTE["prontera"]
RING = tuple((177 + dx, 221 + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)


@pytest.fixture(autouse=True)
def _fresh_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _client(
    *, cache: MapCache | None = None, name: str = "staging_seller"
) -> tuple[PlayingClient, BotState, list[float]]:
    wire = Wire()
    wire.char_name = name
    wire.frames = []
    wire.map_name = "prontera"
    wire.add(entry_at(174, 218), struct.pack("<H16sHH", 0x0091, b"prontera", 174, 218))
    if cache is None:
        cache = MapCache(
            tuple(
                WalkMap(m, 400, 400, bytes(400 * 400)) for m in ("prontera", "prt_fild08", "prt_in")
            )
        )
    now = [0.0]
    client = PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    state = client.build_native_state(Goal.GRIND)
    state = replace(state, inventory_known=True, inventory={"915": 1}, zeny=0)
    return client, state, now


def _step(client: PlayingClient, state: BotState) -> tuple[GameAction, ...]:
    # Same cached received state the host gives its runtime and brain; never re-observe.
    client._last_built_state = state
    outcome = _merchant_step(
        state, reachable=client.merchant_reachable, travel_target=client.merchant_travel_target
    )
    assert outcome is not None
    return outcome.actions


def test_staging_uses_the_same_nearest_free_approach_as_dealer():
    client, state, _ = _client()
    assert _step(client, state) == (MoveTo(176, 220),)
    assert _step(client, state) == ()


def test_two_concurrent_agents_choose_distinct_received_free_cells():
    client_a, state_a, _ = _client(name="a")
    client_b, state_b, _ = _client(name="b")
    # Both stand on different staging neighbours and perceive the other body.
    state_a = replace(state_a, x=176, y=220, occupied_cells=((177, 220),))
    state_b = replace(state_b, x=177, y=220, occupied_cells=((176, 220),))
    assert _step(client_a, state_a) == (MoveTo(176, 220),)
    assert _step(client_b, state_b) == (MoveTo(177, 220),)


def test_unwalkable_free_neighbour_is_skipped():
    tiles = bytearray(400 * 400)
    tiles[176 + 220 * 400] = 1
    cache = MapCache((WalkMap("prontera", 400, 400, bytes(tiles)),))
    client, state, _ = _client(cache=cache)
    assert _step(client, state) == (MoveTo(176, 221),)


def test_saturation_holds_once_and_releases_immediately_on_vacate(caplog):
    client, state, _ = _client()
    blocked = replace(state, occupied_cells=RING)
    for _ in range(21):
        assert _step(client, blocked) == ()
    taps = [r for r in caplog.records if "hold staging_occupied" in r.getMessage()]
    assert len(taps) == 1
    assert "free=0/8" in taps[0].getMessage()
    freed = replace(state, occupied_cells=tuple(p for p in RING if p != (176, 220)))
    assert _step(client, freed) == (MoveTo(176, 220),)
    assert _step(client, blocked) == ()
    assert len([r for r in caplog.records if "hold staging_occupied" in r.getMessage()]) == 2


def test_nearby_players_also_occupy_staging_cells():
    client, state, _ = _client()
    player = ActorRef(id=90, name="other", kind="player", distance=2, x=176, y=220)
    assert _step(client, replace(state, nearby=(player,))) == (MoveTo(176, 221),)


def test_staging_walk_reaffirms_every_fifth_evaluation_across_goal_flips():
    client, state, _ = _client()
    for tick in range(16):
        state = replace(state, goal=Goal.SOCIAL if tick % 2 else Goal.GRIND)
        assert _step(client, state) == ((MoveTo(176, 220),) if tick % 5 == 0 else ())


def test_hold_expires_into_independently_reachable_dealer_entry(caplog):
    client, state, now = _client()
    state = replace(state, occupied_cells=RING)
    assert _step(client, state) == ()
    now[0] = 899.0
    assert _step(client, state) == ()
    now[0] = 900.0
    (move,) = _step(client, state)
    assert isinstance(move, MoveTo)
    # Every cell in this inclusive rectangle activates the EXISTING prt05 entry.
    assert 175 <= move.x <= 179
    assert 219 <= move.y <= 223
    assert (move.x, move.y) not in RING
    assert _step(client, state) == ()
    assert (
        len([r for r in caplog.records if "staging_hold_expired_direct_dealer" in r.getMessage()])
        == 1
    )


def test_expiry_cannot_invent_a_route_through_a_sealed_local_block():
    client, state, now = _client()
    cage = tuple((state.x + dx, state.y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)
    state = replace(state, occupied_cells=cage)
    assert _step(client, state) == ()
    now[0] = 1800.0
    assert _step(client, state) == ()
    assert client.wire.moves == []


def test_map_or_epoch_change_starts_a_fresh_hold_window():
    client, state, now = _client()
    state = replace(state, occupied_cells=RING)
    assert _step(client, state) == ()
    now[0] = 899.0
    state = replace(state, native_epoch=2)
    assert _step(client, state) == ()
    now[0] = 900.0
    assert _step(client, state) == ()
    _step(client, replace(state, map_name="prt_fild08", x=170, y=375, occupied_cells=()))
    now[0] = 1800.0
    assert _step(client, state) == ()


def test_patience_and_saturation_do_not_trigger_mechanical_return_walk():
    client, state, _ = _client()
    assert _step(client, state)
    assert _step(client, state) == ()
    assert client.mechanical_actions(state, ()) == ()
    assert _step(client, replace(state, occupied_cells=RING)) == ()
    assert client.mechanical_actions(state, ()) == ()


def test_real_south_gate_path_avoids_received_bodies_and_the_return_warp():
    cache = MapCache.load(SOURCE / "db/map_cache.dat", SOURCE / "db/pre-re/map_cache.dat")
    client, state, _ = _client(cache=cache)
    client.wire.add(struct.pack("<H16sHH", 0x0091, b"prontera", 156, 26))
    state = replace(
        client.build_native_state(Goal.GRIND), inventory_known=True, inventory={"915": 1}, zeny=0
    )
    state = replace(state, occupied_cells=((155, 26), (156, 27), (157, 27)))
    actions = _step(client, state)
    assert actions
    assert isinstance(actions[0], MoveTo)
    # Use the SAME blockers at actual dispatch, including actors received after authoring.
    client._move(state, (actions[0].x, actions[0].y))
    assert client.wire.moves
    point = client.wire.moves[-1]
    assert point not in state.occupied_cells
    assert not (153 <= point[0] <= 159 and 20 <= point[1] <= 24)
    assert point != (155, 25), "a southward path would enter the return warp next"


def test_freshly_saturated_dispatch_is_refused_without_blind_send():
    client, state, _ = _client()
    (move,) = _step(client, state)
    assert isinstance(move, MoveTo)
    cage = tuple((state.x + dx, state.y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)
    blocked = replace(state, occupied_cells=cage)
    assert client._move(blocked, (move.x, move.y)) == "staging_occupied"
    assert client.wire.moves == []


def test_crossing_counter_counts_only_received_town_field_edges_per_client(caplog):
    client, _, _ = _client()
    other, _, _ = _client(name="other")
    for map_name in ("prontera", "prt_fild08", "prt_fild08", "prontera", "prt_fild08", "prontera"):
        client.wire.add(struct.pack("<H16sHH", 0x0091, map_name.encode(), 156, 26))
        client.build_native_state(Goal.GRIND)
        client.build_native_state(Goal.GRIND)
    assert client.merchant_warp_crossings == 4
    assert other.merchant_warp_crossings == 0
    assert len([r for r in caplog.records if "merchant_warp_ping_pong" in r.getMessage()]) == 1
    for map_name in ("prt_in", "prontera"):
        client.wire.add(struct.pack("<H16sHH", 0x0091, map_name.encode(), 172, 129))
        client.build_native_state(Goal.GRIND)
    assert client.merchant_warp_crossings == 4
    fresh, _, _ = _client()
    assert fresh.merchant_warp_crossings == 0


def test_receipt_names_the_passive_crossing_counter():
    assert (
        '"merchant_warp_crossings": getattr(client, "merchant_warp_crossings", None)'
        in RUNNER.read_text()
    )


def test_missing_geometry_preserves_existing_unknown_authority_behavior():
    client, state, _ = _client()
    client.cache = None
    assert _step(client, state) == (MoveTo(*STAGING),)


def test_a_new_window_resets_crossings_and_the_hold(monkeypatch):
    client, state, now = _client()
    state = replace(state, occupied_cells=RING)
    assert _step(client, state) == ()
    client.wire.add(struct.pack("<H16sHH", 0x0091, b"prt_fild08", 170, 375))
    client.build_native_state(Goal.GRIND)
    assert client.merchant_warp_crossings == 1
    monkeypatch.setattr(client.wire, "connect", lambda: None, raising=False)
    now[0] = 900.0
    client.connect()
    assert client.merchant_warp_crossings == 0
    assert _step(client, state) == ()


def test_completed_trip_releases_mechanical_return():
    client, state, _ = _client()
    sold = replace(state, inventory={"1201": 1})
    assert client.mechanical_actions(sold, ()) == (MoveTo(174, 217),)
