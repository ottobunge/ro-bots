"""The goal script's route is the door the agent's OWN interior can reach.

Leg 37: three agents woke up inside prt_in (a char logs in where it LOGGED
OUT - the char table's ``last_map``) and roamed their interior for the
whole window, 3510/3504/3514 MoveTo to 218/213/264 distinct random
targets, never the exit door.

The first fix named ONE door (prt05's 168,124). It could only have
released the two agents that woke up in THAT interior - xXLunasongXx woke
up in the prt03 interior, whose own door is (53,105), and
``shortest_path`` from (44,102) to (168,124) returns NoRoute. The door is
a property of the interior the agent stands in, so it is resolved by
REACHABILITY, live, from the agent's real position.

These tests pin the wiring: the brain hands the goal script a ROUTER, not
a baked plan, so the door is re-resolved as the agent moves.
"""

from __future__ import annotations

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app.brain import EventDrivenBrain
from robots.app.scripts import GrindScript
from robots.app.travel_routing import TravelRouter
from robots.domain.model import Goal
from tests.conftest import make_state
from tests.test_host_memory import memory_host  # the fixture hosts the brain


def walled_prt_in() -> MapCache:
    """The prt_in grid with each of the two real doors in its own room."""
    width, height = 300, 200
    tiles = bytearray([1]) * (width * height)
    rooms = {
        (53, 105): (40, 95, 60, 115),
        (168, 124): (160, 115, 175, 140),
    }
    for door, (x0, y0, x1, y1) in rooms.items():
        for y in range(y0, y1):
            for x in range(x0, x1):
                tiles[x + y * width] = 0
        assert tiles[door[0] + door[1] * width] == 0
    return MapCache((WalkMap("prt_in", width, height, bytes(tiles)),))


def _brain(tmp_path, resolver=None) -> EventDrivenBrain:
    host = memory_host(tmp_path)
    try:
        agent = next(iter(host.agents.values()))
        brain = agent.brain
        assert brain is not None
        assert isinstance(brain, EventDrivenBrain)
        if resolver is not None:
            brain._travel_resolver = resolver
        return brain
    finally:
        host.stop()


def test_the_goal_script_resolves_the_door_live(tmp_path) -> None:
    """The script carries a ROUTER, so the door is re-resolved as the agent
    moves - the plan is not a baked tuple any more."""
    brain = _brain(tmp_path)
    script = brain._goal_script(Goal.FARM_ITEM, make_state(map_name="prt_in"))
    assert isinstance(script, GrindScript)
    assert script._travel_resolver is None  # no resolver injected yet


def test_a_resolver_that_names_no_route_beats_the_seeded_plan(tmp_path) -> None:
    """The resolver is authoritative: if it names no way out, the seeded
    plan must NOT be substituted for it.

    The seeded prt_in plan names ONE door (168,124). From another interior
    that door cannot be reached at all, so falling back to it would walk
    the agent into a wall for the rest of the window - the leg-37 trap
    with the fix's face on."""
    brain = _brain(tmp_path, resolver=lambda *_args: None)
    script = brain._goal_script(Goal.FARM_ITEM, make_state(map_name="prt_in"))
    assert isinstance(script, GrindScript)
    assert script._travel_plan_for(make_state(map_name="prt_in", x=44, y=102)) == ()


def test_the_router_is_injected_and_resolves_per_agent_cell(tmp_path) -> None:
    """With the router wired, the leg is the door of the agent's OWN
    interior - the prt03 interior's door for the agent standing in it."""
    router = TravelRouter(walled_prt_in())
    brain = _brain(tmp_path, resolver=router.travel_plan)
    script = brain._goal_script(Goal.FARM_ITEM, make_state(map_name="prt_in"))
    assert isinstance(script, GrindScript)
    assert script._travel_resolver is not None
    assert script._travel_plan_for(make_state(map_name="prt_in", x=44, y=102)) == (
        ("prt_in", 53, 105),
        ("prontera", 156, 22),
        ("prt_fild08", 170, 375),
    )
    assert script._travel_plan_for(make_state(map_name="prt_in", x=166, y=137)) == (
        ("prt_in", 168, 124),
        ("prontera", 156, 22),
        ("prt_fild08", 170, 375),
    )
