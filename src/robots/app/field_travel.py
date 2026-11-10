"""Local spawn/warp knowledge joined to the existing travel reachability seam."""

from collections.abc import Mapping, Sequence
from heapq import heappop, heappush
from typing import Protocol

from robots.app.travel_routing import Leg, TravelRouter

Warp = tuple[str, int, int, str, str, int, int]


class FieldTravel(Protocol):
    """Choose a field and resolve its warp chain from the agent's current cell."""

    def nearest(self, map_name: str, x: int, y: int) -> str | None: ...

    def route(self, map_name: str, x: int, y: int, destination: str) -> tuple[Leg, ...]: ...


class FieldTravelPlanner:
    """Dijkstra over declared warp landings; no live census or shared decisions.

    Cost is walking distance (Chebyshev cells) plus one per warp. It is a
    knowledge-level estimate, not a claim about the server's path length.
    The router vetoes disconnected interiors; the runtime still owns every
    authored MoveTo's walkability and the nearest-walkable re-roll.
    """

    def __init__(
        self,
        species: Mapping[str, tuple[str, ...]],
        warps: Sequence[Warp],
        router: TravelRouter,
    ) -> None:
        self._fields = frozenset(name for name, mobs in species.items() if mobs)
        self._router = router
        self._edges: dict[str, list[Warp]] = {}
        for edge in warps:
            self._edges.setdefault(edge[0], []).append(edge)

    def nearest(self, map_name: str, x: int, y: int) -> str | None:
        plan = self._search((map_name, x, y), self._fields - {map_name})
        return plan[-1][0] if plan else None

    def route(self, map_name: str, x: int, y: int, destination: str) -> tuple[Leg, ...]:
        if map_name == destination:
            return ()
        return self._search((map_name, x, y), frozenset((destination,)))

    def _search(self, start: Leg, destinations: frozenset[str]) -> tuple[Leg, ...]:
        pending: list[tuple[int, Leg, tuple[Leg, ...]]] = [(0, start, ())]
        costs = {start: 0}
        while pending:
            cost, position, legs = heappop(pending)
            if cost != costs[position]:
                continue
            if position[0] in destinations:
                return (*legs, position)
            for edge in self._edges.get(position[0], ()):
                target = (edge[1], edge[2])
                if self._router.reachable(position[0], position[1:], target) is False:
                    continue
                landing = (edge[4], edge[5], edge[6])
                total = cost + max(abs(position[1] - target[0]), abs(position[2] - target[1])) + 1
                if total >= costs.get(landing, float("inf")):
                    continue
                costs[landing] = total
                heappush(pending, (total, landing, (*legs, (position[0], *target))))
        return ()
