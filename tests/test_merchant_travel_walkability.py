"""Leg 79 prep: merchant travel uses the same path authority as its counter."""

import struct
from dataclasses import replace
from unittest.mock import patch

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap, nearest_walkable, shortest_path
from robots.app import playing_runtime as runtime
from robots.app import scripts
from robots.app.agent_runtime import ManifestEntry, ScheduledAgent
from robots.app.playing_runtime import PlayingClient
from robots.app.scripts import (
    MERCHANT_ROUTE,
    MERCHANT_ROUTE_RETURN,
    ScriptOutcome,
    ScriptStatus,
    TravelResolver,
    _merchant_step,
)
from robots.app.travel_routing import TravelRouter
from robots.domain.actions import MoveTo
from robots.domain.model import BotState, Goal
from robots.knowledge.travel_routes import TRAVEL_ROUTES
from robots.society.models import Attitude, Playstyle, SocietyPersona
from tests.conftest import make_state
from tests.test_merchant_drive import _plan
from tests.test_native_navigation import SOURCE
from tests.test_playing_runtime import Wire, entry_at, walk_ack
from tests.test_sell_drive_rearm import _answers, _s00_brain

BAD_DEST = (170, 378)
SAFE_DEST = (169, 377)


@pytest.fixture(autouse=True)
def _fresh_merchant_memo():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


@pytest.fixture(scope="module")
def public_cache():
    # Audit the raw cache, before any runtime ground correction.
    return MapCache.load(SOURCE / "db/map_cache.dat", SOURCE / "db/pre-re/map_cache.dat")


@pytest.mark.parametrize(
    ("direction", "map_name", "cell"),
    [
        (direction, map_name, cell)
        for direction, route in (("outbound", MERCHANT_ROUTE), ("return", MERCHANT_ROUTE_RETURN))
        for map_name, cell in route.items()
    ],
)
def test_every_merchant_waypoint_is_walkable(public_cache, direction, map_name, cell):
    assert public_cache.get(map_name).walkable(cell), (direction, map_name, cell)


def test_corrected_field_cell_still_enters_the_cited_warp(public_cache):
    cell = MERCHANT_ROUTE["prt_fild08"]
    assert cell == SAFE_DEST
    assert 167 <= cell[0] <= 173
    assert 376 <= cell[1] <= 380
    assert shortest_path(public_cache.get("prt_fild08"), (170, 375), cell)[-1] == cell
    assert ("prt_fild08", *cell) in TRAVEL_ROUTES["pay_fild04"]


def _client(map_name="prt_fild08", *, open_cells=None) -> PlayingClient:
    tiles = bytearray([1]) * (400 * 400)
    if open_cells is None:
        open_cells = [(x, y) for x in range(166, 174) for y in range(372, 380)]
        open_cells.remove(BAD_DEST)
    for x, y in open_cells:
        tiles[x + y * 400] = 0
    wire = Wire()
    wire.frames = []
    wire.map_name = map_name
    wire.add(
        entry_at(168, 374),
        struct.pack("<H16sHH", 0x0091, map_name.encode(), 168, 374),
    )
    return PlayingClient(wire, cache=MapCache((WalkMap(map_name, 400, 400, bytes(tiles)),)))


def _seller(**over: object) -> BotState:
    base: dict[str, object] = {
        "name": "travel_seller",
        "job": "Novice",
        "inventory_known": True,
        "inventory": {"915": 2},
        "zeny": 0,
        "map_name": "prt_fild08",
        "x": 168,
        "y": 374,
        "nearby": (),
    }
    return make_state(**(base | over))


def _step(
    client: PlayingClient, state: BotState, resolver: TravelResolver | None = None
) -> ScriptOutcome:
    outcome = _merchant_step(
        state,
        resolver=resolver,
        reachable=client.merchant_reachable,
        travel_target=client.merchant_travel_target,
    )
    assert outcome is not None
    return outcome


def test_unwalkable_field_seller_rerolls_once_and_sends_a_path_step(monkeypatch):
    monkeypatch.setitem(MERCHANT_ROUTE, "prt_fild08", BAD_DEST)
    client = _client()
    state = _seller()

    # The ordinary travel resolver heads home; a bad outbound cell must not
    # send this seller backwards to that field-entry cell.
    def resolver(_map, _x, _y):
        return (("prt_fild08", 170, 375),)

    with patch.object(runtime, "nearest_walkable", wraps=nearest_walkable) as nearest:
        outcome = _step(client, state, resolver)
        assert outcome is not None
        assert outcome.actions == (MoveTo(*SAFE_DEST),)
        client.perform_native(outcome.actions[0])
        assert client.wire.moves == [(168, 375)]
        assert client._no_route_attempts == 0
        # Received movement advances the trip and per-tick path caches reset.
        client.wire.add(walk_ack((168, 374), (168, 375)))
        received = client.build_native_state(Goal.GRIND)
        assert (received.x, received.y) == (168, 375)
        advanced = replace(state, x=168, y=375)
        assert _step(client, advanced, resolver).actions == (MoveTo(*SAFE_DEST),)
        assert nearest.call_count == 1
    assert client.cache is not None
    assert client.cache.get("prt_fild08").walkable(BAD_DEST) is False


def test_reroll_skips_walkable_but_unreachable_nearest_candidate(monkeypatch):
    monkeypatch.setitem(MERCHANT_ROUTE, "prt_fild08", BAD_DEST)
    # (169,377) is the primitive's first candidate, in a disconnected pocket.
    # (171,377) has a path down the right-hand corridor from the seller.
    cells = [
        SAFE_DEST,
        (168, 374),
        (169, 374),
        (170, 374),
        (171, 374),
        (171, 375),
        (171, 376),
        (171, 377),
    ]
    client = _client(open_cells=cells)
    assert _step(client, _seller()).actions == (MoveTo(171, 377),)


def test_walkable_but_path_blocked_dest_is_also_rerolled(monkeypatch):
    monkeypatch.setitem(MERCHANT_ROUTE, "prt_fild08", BAD_DEST)
    client = _client(open_cells=[BAD_DEST, (168, 374), (168, 375), (168, 376)])
    assert _step(client, _seller()).actions == (MoveTo(168, 376),)


def test_fully_blocked_dest_holds_and_taps_only_once_across_ticks(monkeypatch, caplog):
    monkeypatch.setitem(MERCHANT_ROUTE, "prt_fild08", BAD_DEST)
    client = _client(open_cells=[(168, 374)])
    with patch.object(runtime, "nearest_walkable", wraps=nearest_walkable) as nearest:
        for _ in range(4):
            client.build_native_state(Goal.GRIND)
            outcome = _step(client, _seller())
            assert outcome is not None
            assert outcome.status == ScriptStatus.ACTIVE
            assert outcome.actions == ()
        assert nearest.call_count == 1
    holds = [
        r.getMessage()
        for r in caplog.records
        if "travel dest unwalkable (170,378)" in r.getMessage()
    ]
    assert len(holds) == 1
    assert "prt_fild08" in holds[0]
    assert client.wire.moves == []


@pytest.mark.parametrize(
    ("map_name", "cell"),
    [(name, cell) for name, cell in MERCHANT_ROUTE.items() if name != "prt_in"]
    + list(MERCHANT_ROUTE_RETURN.items()),
)
def test_each_travel_waypoint_is_validated_at_use_time(map_name, cell):
    calls = []

    def hold(map_name, position, cell) -> None:
        calls.append((map_name, position, cell))

    returning = cell == MERCHANT_ROUTE_RETURN.get(map_name)
    state = _seller(
        map_name=map_name, inventory={} if returning else {"915": 2}, merchant_returning=returning
    )
    if not returning and map_name in MERCHANT_ROUTE_RETURN:
        # The outbound prontera leg is a separate entry from its return leg.
        assert cell == MERCHANT_ROUTE[map_name]
    outcome = _merchant_step(state, travel_target=hold)
    assert outcome is not None
    assert outcome.actions == ()
    assert calls == [(map_name, (state.x, state.y), cell)]


def test_unknown_grid_keeps_the_script_destination():
    client = PlayingClient(Wire())
    assert client.merchant_travel_target("prt_fild08", (168, 374), BAD_DEST) == BAD_DEST
    client = _client()
    assert client.merchant_travel_target("absent", (1, 1), (2, 2)) == (2, 2)


def test_field_travel_still_releases_previous_dealer_approach_memos():
    state = _seller()
    scripts._DEALER_OCCUPANCY_TAPPED[state.name] = "previous hold"
    scripts._DEALER_APPROACH_WALKS[state.name] = ("prt_in", (171, 129), 3)
    scripts._DEALER_QUEUE_WAITS[state.name] = ((), 3)
    _step(_client(), state)
    assert state.name not in scripts._DEALER_OCCUPANCY_TAPPED
    assert state.name not in scripts._DEALER_APPROACH_WALKS
    assert state.name not in scripts._DEALER_QUEUE_WAITS


def test_reroll_memo_is_per_client_map_and_destination():
    client = _client()
    assert client.merchant_travel_target("prt_fild08", (168, 374), BAD_DEST) == SAFE_DEST
    other = _client(open_cells=[(168, 374)])
    assert other.merchant_travel_target("prt_fild08", (168, 374), BAD_DEST) is None
    assert client.merchant_travel_target("prt_fild08", (168, 374), (171, 378)) == (171, 378)


@pytest.mark.parametrize("goal", [Goal.GRIND, Goal.FARM_ITEM, Goal.SOCIAL])
def test_session_binds_target_authority_for_scripts_and_brain_rearm(monkeypatch, goal):
    monkeypatch.setitem(MERCHANT_ROUTE, "prt_fild08", BAD_DEST)
    client = _client()
    brain = _s00_brain()
    persona = SocietyPersona("one", "one", Playstyle.MELEE, Attitude.GRINDER, 0.5, (1, 1))
    agent = ScheduledAgent(
        persona,
        ManifestEntry("one", "dummy", "dummy", "WireNovice"),
        brain=brain,
        client=client,
        threaded=False,
    )
    monkeypatch.setattr(agent, "_wait_for_telemetry", lambda: None)
    monkeypatch.setattr(agent, "build_state", _seller)
    agent._start_brain()
    state = _seller(goal=goal)
    rearm = brain._sell_drive_rearm(state)
    assert rearm is not None
    assert rearm.actions == (MoveTo(*SAFE_DEST),)
    assert brain._goal_script(Goal.GRIND, state).step(state).actions == (MoveTo(*SAFE_DEST),)
    monkeypatch.setattr(brain, "_setup_farm_plan", lambda *_args: _plan())
    brain._run_review(state, _answers("grind"), [])
    assert isinstance(brain._script, scripts.FarmScript)
    assert brain._script.step(state).actions == (MoveTo(*SAFE_DEST),)


def test_foreign_interior_exit_is_validated_before_authoring():
    from tests.test_merchant_route_reachability import walled_prt_in  # noqa: PLC0415

    cache = walled_prt_in()
    client = PlayingClient(Wire(), cache=cache)
    router = TravelRouter(cache)
    state = _seller(map_name="prt_in", x=44, y=102)
    assert _step(client, state, router.travel_plan).actions == (MoveTo(53, 105),)
