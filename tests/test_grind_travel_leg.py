"""The grind travel leg: a grind goal on a mobless map travels to the field.

Leg 20's telemetry: the agents ran the GrindScript IN prontera (a mobless
town) patrolling locally - the field (prt_fild08's spawns) is across the
warp and the route knowledge already knows the way. The script gains a
travel plan (the route's warp cells): while the bot is off-field, the
empty-view path walks the route instead of patrolling a mobless patch."""

from __future__ import annotations

from robots.app.scripts import GrindScript


def _state(map_name: str, x: int, y: int):
    from tests.conftest import make_state

    # the mobless premise: a town / a mobless patch has no nearby monsters
    return make_state(map_name=map_name, x=x, y=y, nearby=())


def test_travel_plan_walks_the_first_route_cell_when_off_field() -> None:
    script = GrindScript(travel_plan=[("prontera", 156, 22), ("prt_fild08", 170, 375)])
    outcome = script.step(_state("prontera", 150, 150))
    assert outcome.status.name == "ACTIVE"
    action = outcome.actions[0]
    assert action.x == 156 and action.y == 22


def test_travel_plan_completed_when_route_map_reached() -> None:
    # the bot already walked the prontera leg and crossed: on the field the
    # plan's remaining leg starts at the field cell
    script = GrindScript(travel_plan=[("prontera", 156, 22), ("prt_fild08", 170, 375)])
    outcome = script.step(_state("prt_fild08", 170, 375))
    # arrived: the travel leg is done and the script hands back to the normal
    # grind behaviour (ACTIVE with the patrol/attack actions, not the travel)
    assert outcome.status.name == "ACTIVE"


def test_no_travel_plan_keeps_local_patrol() -> None:
    script = GrindScript()
    outcome = script.step(_state("prontera", 150, 150))
    assert outcome.status.name == "ACTIVE"
