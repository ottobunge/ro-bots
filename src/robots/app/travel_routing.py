"""The travel route: the exit the agent can actually WALK to, resolved live.

Leg 37's second patrol-forever trap: ``prt_in`` is not one room. It is 26
disconnected building interiors, each with its own exit door (the pinned
warp declarations in ``npc/warps/cities/prontera.txt`` give 15 of them a
door straight to prontera). A char logs in where it LOGGED OUT
(``last_map``), so three agents woke up inside prt_in - two in the prt05
interior (door 168,124) and one in the prt03 interior (door 53,105).

A route table keyed by MAP NAME therefore hands every one of them the same
door, and for the agent in the prt03 interior that door is not merely far
away - it is unreachable, in another component of the map. The exit is a
property of the interior the agent stands in, so it is resolved here, by
REACHABILITY from the agent's real position, on the client grid.

The resolution is a composition, not a new layer: the pinned exit cells and
the internal warp hops are knowledge (``robots.knowledge.travel_routes``),
the reachability is navigation (``robots.adapters.native_navigation``), and
this module is the app-layer seam that joins them for the brain and the
goal scripts.

The per-map region index is computed once (the client grid is immutable for
a world) and every later query is a set lookup, so the live resolution
costs nothing per step.
"""

from __future__ import annotations

from typing import Any

from robots.adapters.native_navigation import (
    MapCache,
    WalkMap,
    exit_in_region,
    walkable_region,
)
from robots.knowledge.travel_routes import EXIT_CELLS, INTERNAL_WARPS, TRAVEL_ROUTES

Point = tuple[int, int]
Leg = tuple[str, int, int]

ONWARD: dict[str, tuple[Leg, ...]] = {
    "prt_in": (("prontera", 156, 22), ("prt_fild08", 170, 375)),
    "prontera": (("prt_fild08", 170, 375),),
}
"""The route that follows an exit of each map (pinned public warp bytes).

- ``prontera,156,22,0  warp  prt001  3,2,prt_fild08,170,375`` -
  ``npc/warps/cities/prontera.txt:24``;
- ``prt_in``'s doors all lead to prontera, and prontera's field warp leads
  to the field - the same two legs the merchant return cites
  (prontera.txt:24 and :40).
"""


class TravelRouter:
    """The exit cell of the map the agent stands on, resolved by reachability.

    One router per world (the client grid is immutable for a world); the
    per-map region index is built on first use.
    """

    def __init__(self, cache: MapCache) -> None:
        self._cache = cache
        self._regions: dict[str, dict[Point, frozenset[Point]]] = {}

    def _grid(self, map_name: str) -> WalkMap | None:
        try:
            return self._cache.get(map_name)
        except Exception:
            return None

    def knows(self, map_name: str) -> bool:
        """Whether the client grid carries this map at all."""
        return self._grid(map_name) is not None

    def _region_of(self, grid: WalkMap, map_name: str, cell: Point) -> frozenset[Point]:
        """The walkable region of ``cell``, memoized per (map, cell).

        Every cell of a region shares that region (a region IS a connected
        component), so the flood is memoized for all of them: one flood per
        component, and the map's whole walkable area costs one index.
        """
        per_map = self._regions.setdefault(map_name, {})
        found = per_map.get(cell)
        if found is None:
            found = walkable_region(grid, cell)
            for member in found:
                per_map.setdefault(member, found)
        return found

    def exit_target(self, map_name: str, position: Point) -> Point | None:
        """The exit cell the agent can walk to from ``position``, or None.

        A map with SEVERAL exits (prt_in's building interiors) resolves to
        the exit in the agent's OWN region: the interiors are genuinely
        disconnected, on the server's grid as well as the client's, so
        only one of the fifteen doors is the agent's way out.

        A map with ONE exit (prontera's field warp) resolves to that exit
        UNCONDITIONALLY. The client grid is a lossy picture of the
        server's, and the server path-finds its own side (the leg-28
        direct-send path) - so a client-side "unreachable" here would
        veto a walk the server would happily make.
        """
        grid = self._grid(map_name)
        if grid is None:
            return None
        exits = EXIT_CELLS.get(map_name)
        if not exits:
            return None
        walkable = tuple(cell for cell in exits if grid.walkable(cell))
        if not walkable:
            return None
        if len(walkable) == 1:
            return walkable[0]
        return exit_in_region(self._region_of(grid, map_name, position), walkable)

    def reachable(self, map_name: str, position: Point, cell: Point) -> bool | None:
        """Whether ``cell`` is walkable in ``position``'s own region.

        leg 37's merchant half: the pinned dealer/return cells sit in ONE
        interior (prt05), and an agent in another component cannot walk to
        them. None when the grid does not carry the map — no authority, the
        caller keeps its pinned leg (fail-open; the client grid is a lossy
        picture of the server's, so only an explicit False vetoes a leg).
        """
        grid = self._grid(map_name)
        if grid is None:
            return None
        region = self._region_of(grid, map_name, position)
        if not region:
            return None
        return cell in region

    def hop_target(self, map_name: str, position: Point) -> Point | None:
        """The internal warp cell the agent can walk to, when one leads out.

        Four of prt_in's interiors have no door of their own: they reach
        prontera through a warp INSIDE prt_in (the prt15/prt16/prt17/prt18/
        prt19/prt20 hops in ``npc/warps/cities/prontera.txt``). The hop cell
        is the way out of such an interior; the door beyond it is the next
        component's business, resolved when the agent stands there.
        """
        grid = self._grid(map_name)
        if grid is None:
            return None
        hops = INTERNAL_WARPS.get(map_name)
        if not hops:
            return None
        region = self._region_of(grid, map_name, position)
        if not region:
            return None
        for source, destination in hops:
            if not grid.walkable(source):
                continue
            if source not in region:
                continue
            # The hop is only a way out if the component it DELIVERS to has
            # a door of its own; otherwise it is a hop between two dead
            # interiors.
            delivered = self._region_of(grid, map_name, destination)
            if any(
                grid.walkable(exit_cell) and exit_cell in delivered
                for exit_cell in EXIT_CELLS.get(map_name, ())
            ):
                return source
        return None

    def travel_plan(self, map_name: str, x: int, y: int) -> tuple[Leg, ...] | None:
        """The ordered warp legs from the agent's cell to the field, or None.

        The first leg is the exit the agent can WALK to from where it stands
        (its own interior's door); the rest is the route that follows every
        exit of that map. The signature is the resolver protocol's
        ``(map_name, x, y)``.
        """
        exits = EXIT_CELLS.get(map_name)
        if not exits:
            return None
        position = (x, y)
        target = self.exit_target(map_name, position)
        if target is None:
            target = self.hop_target(map_name, position)
        if target is None:
            return None
        return ((map_name, target[0], target[1]), *ONWARD.get(map_name, ()))


def travel_router(cache: MapCache) -> TravelRouter:
    """The router for a world (one per client grid)."""
    return TravelRouter(cache)


def travel_plan_for(cache: MapCache, map_name: str, position: Point) -> tuple[Leg, ...] | None:
    """The travel plan for a position, resolved against the world's grid."""
    return travel_router(cache).travel_plan(map_name, position[0], position[1])


def seeded_plan(map_name: str) -> tuple[Leg, ...] | None:
    """The seeded route for a map, with no grid to resolve against.

    The fallback for a world whose client grid does not carry the map: the
    static table is still better than no route, and the agent's own interior
    is the common case (the prt05 interior, whose door the table cites).
    """
    return TRAVEL_ROUTES.get(map_name)


def plan_factory(router: TravelRouter) -> Any:
    """The resolver callable the brain asks for a route.

    ``(map_name, x, y) -> plan | None``. A map the grid does not carry
    falls back to the seeded table; a map it DOES carry but from which no
    exit is reachable gets no route at all - a named wrong door is worse
    than no door, because the walk to it can never arrive.
    """

    def resolve(map_name: str, x: int, y: int) -> tuple[Leg, ...] | None:
        plan = router.travel_plan(map_name, x, y)
        if plan is not None:
            return plan
        if router.knows(map_name):
            return None
        return seeded_plan(map_name)

    return resolve
