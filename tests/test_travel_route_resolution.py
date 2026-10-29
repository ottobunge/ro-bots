"""The travel route's exit door is the one the agent's OWN interior can reach.

Leg 37's second patrol-forever trap: ``prt_in`` is not one room. It is 26
disconnected building interiors, each with its own door cell (the pinned
warp declarations in ``npc/warps/cities/prontera.txt`` give 15 of them a
door straight to prontera). A char logs in where it LOGGED OUT
(``last_map``), so three agents woke up inside prt_in - two in the prt05
interior (door 168,124) and one in the prt03 interior (door 53,105).

A single hard-coded door therefore rescues only the agents that happen to
share that interior: the third agent's own door is unreachable from where
it stands, so the route it was handed had no path at all. The door must be
resolved by REACHABILITY from the agent's real position, on the client
grid, before the route is handed out.
"""

from __future__ import annotations

from robots.adapters.native_navigation import MapCache, WalkMap, reachable_exit
from robots.app.travel_routing import seeded_plan, travel_plan_for
from robots.knowledge.travel_routes import EXIT_CELLS, TRAVEL_ROUTES


def split_interiors() -> MapCache:
    """The prt_in grid, walled so each door sits in its OWN interior.

    This reproduces what the live map cache shows: prt_in's interiors are
    separate regions, so a door on the far side of a wall is unreachable
    from the near side. The grid is otherwise solid rock with a small
    room cut around each of the two doors the test cares about, so the
    ONLY reachable door from a room is the one inside it.
    """
    width, height = 300, 200
    tiles = bytearray([1]) * (width * height)  # 1 = not walkable
    rooms = {
        (53, 105): (40, 95, 60, 115),
        (168, 124): (160, 115, 175, 140),
    }
    for door, (x0, y0, x1, y1) in rooms.items():
        for y in range(y0, y1):
            for x in range(x0, x1):
                tiles[x + y * width] = 0  # 0 = walkable
        assert tiles[door[0] + door[1] * width] == 0
    return MapCache((WalkMap("prt_in", width, height, bytes(tiles)),))


def test_reachable_exit_is_the_door_in_the_agents_own_interior() -> None:
    """The flood over the agent's own interior finds ITS door, not the
    nearest door on the sheet."""
    cache = split_interiors()
    grid = cache.get("prt_in")
    doors = EXIT_CELLS["prt_in"]
    assert (53, 105) in doors
    assert (168, 124) in doors
    assert reachable_exit(grid, (44, 102), doors) == (53, 105)
    assert reachable_exit(grid, (166, 137), doors) == (168, 124)


def test_reachable_exit_is_none_when_no_door_is_reachable() -> None:
    cache = split_interiors()
    grid = cache.get("prt_in")
    assert reachable_exit(grid, (44, 102), ()) is None
    assert reachable_exit(grid, (44, 102), ((299, 199),)) is None


def test_travel_plan_uses_the_reachable_prt_in_door() -> None:
    """The plan the brain hands out names the door of the interior the agent
    actually stands in - the one it can walk to."""
    cache = split_interiors()
    assert travel_plan_for(cache, "prt_in", (44, 102)) == (
        ("prt_in", 53, 105),
        ("prontera", 156, 22),
        ("prt_fild08", 170, 375),
    )
    assert travel_plan_for(cache, "prt_in", (166, 137)) == (
        ("prt_in", 168, 124),
        ("prontera", 156, 22),
        ("prt_fild08", 170, 375),
    )


def test_travel_plan_of_a_map_without_doors_is_none() -> None:
    """A map with no exit cells has no route to resolve (the field itself)."""
    cache = split_interiors()
    assert travel_plan_for(cache, "prt_fild08", (170, 375)) is None


def test_seeded_plan_is_the_fallback_without_a_grid() -> None:
    """A world whose client grid does not carry the map keeps the static
    route rather than losing the route altogether."""
    assert seeded_plan("prontera") == TRAVEL_ROUTES["prontera"]
    assert seeded_plan("prt_fild08") is None
