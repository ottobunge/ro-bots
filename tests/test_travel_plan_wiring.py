"""The brain builds the grind script with the travel plan on a routed map."""

from __future__ import annotations

from robots.app.brain import EventDrivenBrain
from robots.app.scripts import GrindScript
from robots.domain.model import Goal
from tests.conftest import make_state
from tests.test_host_memory import memory_host  # the fixture hosts the brain


def _brain(tmp_path) -> EventDrivenBrain:

    host = memory_host(tmp_path)
    try:
        agent = next(iter(host.agents.values()))
        brain = agent.brain
        assert brain is not None
        assert isinstance(brain, EventDrivenBrain)
        return brain
    finally:
        host.stop()


def test_grind_on_a_routed_map_gets_the_travel_plan(tmp_path) -> None:
    brain = _brain(tmp_path)
    script = brain._goal_script(Goal.GRIND, make_state(map_name="prontera"))
    assert isinstance(script, GrindScript)
    assert script._travel_plan == (
        ("prontera", 156, 22),
        ("prt_fild08", 170, 375),
    )


def test_grind_on_an_unrouted_map_keeps_the_plain_script(tmp_path) -> None:
    brain = _brain(tmp_path)
    script = brain._goal_script(Goal.GRIND, make_state(map_name="prt_fild08"))
    assert isinstance(script, GrindScript)
    assert script._travel_plan == ()


def test_farm_item_on_a_routed_town_gets_the_travel_plan(tmp_path) -> None:
    """Leg 36: a farm_item goal on prontera patrolled a mobless town forever.

    _setup_farm_plan returns None on a town map (no spawn declaration), so the
    goal script was the ONLY path to the field - and the route was handed out
    for Goal.GRIND only. 6 of 7 agents burned ~21k MoveTos with zero swings.
    The route belongs to ANY farming goal, not the goal's name."""
    brain = _brain(tmp_path)
    script = brain._goal_script(Goal.FARM_ITEM, make_state(map_name="prontera"))
    assert isinstance(script, GrindScript)
    assert script._travel_plan == (
        ("prontera", 156, 22),
        ("prt_fild08", 170, 375),
    )


def test_farm_item_on_the_field_keeps_the_plain_script(tmp_path) -> None:
    brain = _brain(tmp_path)
    script = brain._goal_script(Goal.FARM_ITEM, make_state(map_name="prt_fild08"))
    assert isinstance(script, GrindScript)
    assert script._travel_plan == ()


def test_farming_goal_in_the_shop_interior_gets_the_exit_route(tmp_path) -> None:
    """Leg 37: three agents logged in on prt_in and roamed it forever.

    A char logs in where it LOGGED OUT (last_map), not at its Kafra save
    point: the merchant trip of an earlier leg left three of them inside
    the prontera interior, so every later leg opened them on prt_in. That
    map has no spawn declaration (no plan) and no TRAVEL_ROUTES entry (no
    route) - the goal script's plain GrindScript then patrolled the
    interior at random for the whole window (leg 37: 117 distinct random
    MoveTo targets, never the exit door).

    The route table is the general mechanism for "a farming goal on a map
    whose spawns are elsewhere", and prt_in is exactly such a map. Its
    pinned exit door is prt_in,168,124 (warp prt05-1 -> prontera,174,218),
    the same cell the merchant return leg already cites; the route then
    continues through the prontera field warp to prt_fild08."""
    brain = _brain(tmp_path)
    script = brain._goal_script(Goal.FARM_ITEM, make_state(map_name="prt_in"))
    assert isinstance(script, GrindScript)
    assert script._travel_plan == (
        ("prt_in", 168, 124),
        ("prontera", 156, 22),
        ("prt_fild08", 170, 375),
    )


def test_grind_in_the_shop_interior_gets_the_exit_route(tmp_path) -> None:
    """The interior is no different for Goal.GRIND: both farming goals
    need a way out of a spawnless map."""
    brain = _brain(tmp_path)
    script = brain._goal_script(Goal.GRIND, make_state(map_name="prt_in"))
    assert isinstance(script, GrindScript)
    assert script._travel_plan == (
        ("prt_in", 168, 124),
        ("prontera", 156, 22),
        ("prt_fild08", 170, 375),
    )
