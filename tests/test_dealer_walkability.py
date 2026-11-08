"""Leg 74: free shop counters must be vetoed before a MoveTo is authored."""

from dataclasses import replace

import pytest

from robots.adapters.native_navigation import MapCache, NoRoute, WalkMap
from robots.app import playing_runtime as runtime
from robots.app import scripts
from robots.app.agent_runtime import ManifestEntry, ScheduledAgent
from robots.app.playing_runtime import PlayingClient
from robots.app.scripts import ScriptStatus, _merchant_step
from robots.domain.actions import MoveTo
from robots.domain.model import BotState, Goal
from robots.society.models import Attitude, Playstyle, SocietyPersona
from tests.conftest import make_state
from tests.test_playing_runtime import Wire
from tests.test_sell_drive_rearm import _s00_brain

DEALER = (172, 130)
NEIGHBOURS = tuple(
    (172 + dx, 130 + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)
)


@pytest.fixture(autouse=True)
def _fresh_merchant_memo():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _client(blocked: tuple[tuple[int, int], ...] = ()) -> PlayingClient:
    tiles = bytearray(200 * 200)
    for x, y in blocked:
        tiles[x + y * 200] = 1
    return PlayingClient(Wire(), cache=MapCache((WalkMap("prt_in", 200, 200, bytes(tiles)),)))


def _stock_holder(**over: object) -> BotState:
    return make_state(
        name="s00_walkability",
        job="Novice",
        inventory_known=True,
        inventory={"511": 2, "905": 3, "906": 1},
        zeny=0,
        map_name="prt_in",
        x=169,
        y=127,
        nearby=(),
        **over,
    )


def test_runtime_vetoes_free_counter_before_authoring() -> None:
    client = _client(((171, 129),))
    outcome = _merchant_step(_stock_holder(), reachable=client.merchant_reachable)
    assert outcome is not None
    assert outcome.actions == (MoveTo(x=171, y=130),)


def test_s00_holds_when_only_walkable_neighbour_is_occupied_then_releases(caplog) -> None:
    free_counter_tiles = tuple(cell for cell in NEIGHBOURS if cell != (172, 129))
    client = _client(free_counter_tiles)
    state = _stock_holder(occupied_cells=((172, 129),))
    outcome = _merchant_step(state, reachable=client.merchant_reachable)
    assert outcome is not None
    assert outcome.status == ScriptStatus.ACTIVE
    assert outcome.actions == ()
    assert any(
        "hold dealer_occupied" in r.getMessage()
        and "free=7/8" in r.getMessage()
        and "walkable_free=0/8" in r.getMessage()
        for r in caplog.records
    )
    released = _merchant_step(
        replace(state, occupied_cells=()), reachable=client.merchant_reachable
    )
    assert released is not None
    assert released.actions == (MoveTo(x=172, y=129),)


def test_runtime_preserves_unknown_authority_and_cross_region_veto() -> None:
    client = _client(tuple((170, y) for y in range(200)))
    assert client.merchant_reachable("prt_in", (169, 127), (171, 129)) is False
    assert client.merchant_reachable("absent", (169, 127), (171, 129)) is None
    assert PlayingClient(Wire()).merchant_reachable("prt_in", (169, 127), (171, 129)) is None
    # Even an unknown source region must not author a known blocked target.
    assert client.merchant_reachable("prt_in", (170, 127), (170, 129)) is False


def test_walkable_cell_is_vetoed_when_move_pathfinder_reports_no_route(monkeypatch) -> None:
    client = _client()
    calls = []

    def no_route(grid, position, cell):
        assert grid.walkable(position)
        assert grid.walkable(cell)
        calls.append((position, cell))
        message = "shop counter blocks the path"
        raise NoRoute(message)

    monkeypatch.setattr(runtime, "shortest_path", no_route)
    assert client.merchant_reachable("prt_in", (169, 127), (171, 129)) is False
    assert calls == [((169, 127), (171, 129))]


def test_s00_holds_when_all_free_walkable_neighbours_have_no_path(monkeypatch, caplog) -> None:
    client = _client()

    def no_route(grid, position, cell):
        assert grid.walkable(cell)
        message = "shop counter blocks the path"
        raise NoRoute(message)

    monkeypatch.setattr(runtime, "shortest_path", no_route)
    outcome = _merchant_step(_stock_holder(), reachable=client.merchant_reachable)
    assert outcome is not None
    assert outcome.status == ScriptStatus.ACTIVE
    assert outcome.actions == ()
    taps = [r.getMessage() for r in caplog.records if "hold dealer_occupied" in r.getMessage()]
    assert len(taps) == 1
    assert "free=8/8" in taps[0]
    assert "reachable=0/8 walkable_free=0/8" in taps[0]


@pytest.mark.parametrize("has_path", [True, False])
def test_path_verdict_is_cached_per_map_position_cell_and_native_tick(
    monkeypatch, has_path
) -> None:
    client = _client()
    calls = []

    def path(grid, position, cell):
        calls.append((position, cell))
        if not has_path:
            message = "no path"
            raise NoRoute(message)
        return (position, cell)

    monkeypatch.setattr(runtime, "shortest_path", path)
    query = ("prt_in", (169, 127), (171, 129))
    assert client.merchant_reachable(*query) is has_path
    assert client.merchant_reachable(*query) is has_path
    assert len(calls) == 1
    assert client.merchant_reachable("prt_in", (168, 127), (171, 129)) is has_path
    assert client.merchant_reachable("prt_in", (169, 127), (171, 130)) is has_path
    assert len(calls) == 3
    monkeypatch.setattr(client, "_map_identity", lambda _name: "prt_in")
    client.build_native_state(Goal.GRIND)
    assert client.merchant_reachable(*query) is has_path
    assert len(calls) == 4


@pytest.mark.parametrize("goal", [Goal.GRIND, Goal.FARM_ITEM])
def test_session_binds_runtime_authority_before_brain_creates_scripts(monkeypatch, goal) -> None:
    client = _client(((171, 129),))
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
    monkeypatch.setattr(agent, "build_state", _stock_holder)
    agent._start_brain()
    script = brain._goal_script(goal, _stock_holder())
    assert script.step(_stock_holder()).actions == (MoveTo(x=171, y=130),)
