"""Trip distances and endpoint limits from the public client/server geometry."""

from robots.adapters.native_navigation import Point, WalkMap, route_distances


def clear_walk_line(grid: WalkMap, start: Point, target: Point) -> bool:
    """Pinned path.cpp path_search_long integer line, excluding endpoints.

    unit.cpp OFFICIAL_WALKPATH rejects paths longer than 14 cells unless this
    line is clear. The server still path-follows; this is an admission limit.
    """
    if target[0] < start[0]:
        start, target = target, start
    dx, dy = target[0] - start[0], target[1] - start[1]
    weight = max(dx, abs(dy))
    return all(
        grid.walkable((start[0] + dx * step // weight, start[1] + dy * step // weight))
        for step in range(1, weight)
    )


def trip_chunk_cells(grid: WalkMap, path: tuple[Point, ...]) -> int:
    # conf/battle/client.conf:42 and battle.cpp: max_walk_path defaults to 17.
    cells = min(17, len(path) - 1)
    if cells > 14 and not clear_walk_line(grid, path[0], path[cells]):
        return 14
    return cells


class TripNavigation:
    """One reverse distance field per current destination, rebuilt on grid edits."""

    def __init__(self) -> None:
        self._key: tuple[str, bytes, Point] | None = None
        self._distances: dict[Point, int] = {}

    def distance(self, grid: WalkMap, position: Point, target: Point) -> int | None:
        key = (grid.name, grid.tiles, target)
        if key != self._key:
            self._distances = route_distances(grid, target)
            self._key = key
        return self._distances.get(position)
