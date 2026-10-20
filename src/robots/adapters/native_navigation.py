"""Read-only public rAthena geometry; plans are NOT movement/arrival receipts.

Use one MapCache per world, loading common then pre-re overrides with ``load``.
``shortest_path(cache.get(map_name), received_position, target)`` includes start
and target; send only its next cell, await native position feedback, then replan.
No TCP, SQL, inference, hidden actors or spawn locations are consulted.

Binary layout: pinned e985 src/map/map.cpp and src/tool/mapcache.cpp, compiler
sizeof/offsetof oracle: main=8/count@4, entry=20/name@0/xs@12/ys@14/len@16.
GAT flags and row-major addressing: map.cpp map_gat2cell/map_readfromcache.
"""

import struct
import zlib
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Self

Point = tuple[int, int]
MAX_TILES = 512 * 512  # pinned map.hpp MAX_MAP_SIZE
MAX_CACHE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_TILES = 256 * 1024 * 1024  # whole-world memory budget, public cache uses ~107MB
HEADER = struct.Struct("<IH2x")
ENTRY = struct.Struct("<12shhi")
WALKABLE = frozenset((0, 2, 3, 4, 6))
SHOOTABLE = WALKABLE | {5}


class InvalidMapCacheError(ValueError):
    """Malformed or oversized public geometry."""


class NoRouteError(ValueError):
    """Unknown map, invalid position or unreachable target; no invented route."""


InvalidMapCache = InvalidMapCacheError
NoRoute = NoRouteError


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidMapCache(message)


@dataclass(frozen=True, slots=True)
class WalkMap:
    """Immutable GAT tiles, preserving declared name and dimensions exactly."""

    name: str
    width: int
    height: int
    tiles: bytes

    def __post_init__(self) -> None:
        _require(type(self.name) is str and bool(self.name), "invalid map name")
        _require(type(self.width) is int and type(self.height) is int, "invalid dimensions")
        _require(self.width > 0 and self.height > 0, "invalid dimensions")
        _require(self.width * self.height <= MAX_TILES, "map exceeds MAX_MAP_SIZE")
        _require(type(self.tiles) is bytes, "tiles must be immutable bytes")
        _require(len(self.tiles) == self.width * self.height, "tile count mismatch")

    def contains(self, point: Point) -> bool:
        return (
            type(point) is tuple
            and len(point) == 2
            and type(point[0]) is int
            and type(point[1]) is int
            and 0 <= point[0] < self.width
            and 0 <= point[1] < self.height
        )

    def walkable(self, point: Point) -> bool:
        return self.contains(point) and self.tiles[point[0] + point[1] * self.width] in WALKABLE

    def shootable(self, point: Point) -> bool:
        return self.contains(point) and self.tiles[point[0] + point[1] * self.width] in SHOOTABLE


def _decode(body: bytes, size: int) -> bytes:
    decoder = zlib.decompressobj()
    try:
        tiles = decoder.decompress(body, size + 1)
    except zlib.error as error:
        msg = "invalid compressed tiles"
        raise InvalidMapCache(msg) from error
    _require(len(tiles) == size, "decompressed dimensions mismatch")
    _require(decoder.eof, "truncated or oversized compressed tiles")
    _require(not decoder.unused_data and not decoder.unconsumed_tail, "trailing compressed data")
    return tiles


def _read_entry(data: bytes, offset: int, remaining_tiles: int) -> tuple[WalkMap, int]:
    _require(offset + ENTRY.size <= len(data), "truncated entry header")
    raw_name, width, height, length = ENTRY.unpack_from(data, offset)
    name_bytes = raw_name.split(b"\0", 1)[0]
    try:
        name = name_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        msg = "map name is not UTF-8"
        raise InvalidMapCache(msg) from error
    _require(bool(name), "empty map name")
    _require(width > 0 and height > 0, "invalid dimensions")
    _require(width * height <= MAX_TILES, "map exceeds MAX_MAP_SIZE")
    _require(width * height <= remaining_tiles, "aggregate tile budget exceeded")
    start = offset + ENTRY.size
    _require(0 < length <= MAX_CACHE_BYTES and start + length <= len(data), "invalid body length")
    return (
        WalkMap(name, width, height, _decode(data[start : start + length], width * height)),
        start + length,
    )


class MapCache:
    """World-owned immutable maps; no normalization or unknown-map fallback."""

    def __init__(self, maps: Iterable[WalkMap]) -> None:
        self.maps = MappingProxyType({item.name: item for item in maps})

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        _require(HEADER.size <= len(data) <= MAX_CACHE_BYTES, "invalid cache size")
        declared_size, count = HEADER.unpack_from(data)
        _require(declared_size == len(data), "declared file size mismatch")
        _require(count <= (len(data) - HEADER.size) // ENTRY.size, "impossible map count")
        maps: dict[str, WalkMap] = {}
        offset = HEADER.size
        remaining = MAX_TOTAL_TILES
        for _ in range(count):
            item, offset = _read_entry(data, offset, remaining)
            remaining -= len(item.tiles)
            _require(item.name not in maps, "duplicate map name")
            maps[item.name] = item
        _require(offset == len(data), "trailing cache data")
        return cls(maps.values())

    @classmethod
    def load(cls, *paths: Path) -> Self:
        """Load ordered public caches; later pre-re maps override common maps."""
        maps: dict[str, WalkMap] = {}
        for path in paths:
            with path.open("rb") as stream:
                _require(path.stat().st_size <= MAX_CACHE_BYTES, "cache exceeds size limit")
                cache = cls.from_bytes(stream.read(MAX_CACHE_BYTES + 1))
            maps.update(cache.maps)
            _require(
                sum(len(item.tiles) for item in maps.values()) <= MAX_TOTAL_TILES,
                "aggregate tile budget exceeded",
            )
        return cls(maps.values())

    def get(self, name: str) -> WalkMap:
        try:
            return self.maps[name]
        except KeyError as error:
            msg = f"unknown public map: {name}"
            raise NoRoute(msg) from error


def _neighbors(grid: WalkMap, point: Point, blocked: frozenset[Point]) -> Iterable[Point]:
    x, y = point
    for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
        candidate = (x + dx, y + dy)
        if not grid.walkable(candidate) or candidate in blocked:
            continue
        if dx and dy:
            sides = ((x + dx, y), (x, y + dy))
            if any(not grid.walkable(side) or side in blocked for side in sides):
                continue
        yield candidate


def _reconstruct(parents: dict[Point, Point], start: Point, target: Point) -> tuple[Point, ...]:
    path = [target]
    while path[-1] != start:
        path.append(parents[path[-1]])
    return tuple(reversed(path))


def _validated_blockers(
    grid: WalkMap, start: Point, target: Point, visible: Iterable[Point]
) -> frozenset[Point]:
    points = tuple(visible)
    if any(not grid.contains(point) for point in points):
        msg = "invalid visible blocked coordinate"
        raise NoRoute(msg)
    blocked = frozenset(points)
    if any(not grid.walkable(point) or point in blocked for point in (start, target)):
        msg = "invalid or blocked route endpoint"
        raise NoRoute(msg)
    return blocked


def shortest_path(
    grid: WalkMap, start: Point, target: Point, *, blocked_visible: Iterable[Point] = ()
) -> tuple[Point, ...]:
    """Shortest 8-neighbor cell-count path, no corner cutting; bounded by map area.

    Dynamic blockers must come ONLY from this bot's received visible stream.
    Invalid endpoints/blockers and exhausted searches raise NoRoute explicitly.
    """
    blocked = _validated_blockers(grid, start, target, blocked_visible)
    frontier = deque((start,))
    parents = {start: start}
    while frontier:
        current = frontier.popleft()
        if current == target:
            return _reconstruct(parents, start, target)
        for neighbor in _neighbors(grid, current, blocked):
            if neighbor not in parents:
                parents[neighbor] = current
                frontier.append(neighbor)
    msg = "no walkable route"
    raise NoRoute(msg)


@dataclass(frozen=True, slots=True)
class StarterRoute:
    """One current-map leg. Warp completion requires received native map change."""

    map_name: str
    path: tuple[Point, ...]
    approach: Point
    requires_map_change: bool
    warp_tile: Point = (156, 22)
    trigger_rectangle: tuple[int, int, int, int] = (153, 20, 159, 24)
    destination_map: str = "prt_fild08"
    destination: Point = (170, 375)

    @property
    def next_waypoint(self) -> Point | None:
        return self.path[1] if len(self.path) > 1 else None


def starter_route(
    cache: MapCache,
    map_name: str,
    start: Point,
    *,
    blocked_visible: Iterable[Point] = (),
    field_target: Point | None = None,
) -> StarterRoute:
    """Prontera southern exit; use actual received start, never a fixture origin.

    Pinned npc/warps/cities/prontera.txt line24 SHA256
    434fe0daf761275cf731c343a501c02d88355a524b9c9a87d1f00c510ae3f4d7:
    prontera,156,22,0 warp prt001 3,2,prt_fild08,170,375.
    Inclusive trigger bounds follow npc.cpp npc_touch_areanpc. On the field,
    field_target is a caller-selected visible-region roam point, NOT a mob spawn.
    Already inside the trigger returns no next waypoint: await native feedback.
    """
    grid = cache.get(map_name)
    field = cache.get("prt_fild08")
    if not field.walkable((170, 375)):
        msg = "public warp destination is not walkable"
        raise NoRoute(msg)
    if map_name == "prt_fild08":
        target = start if field_target is None else field_target
        path = shortest_path(grid, start, target, blocked_visible=blocked_visible)
        return StarterRoute(map_name, path, target, False)
    if map_name != "prontera":
        msg = "starter route supports only prontera and prt_fild08"
        raise NoRoute(msg)
    return _trigger_route(grid, start, tuple(blocked_visible))


def _trigger_route(grid: WalkMap, start: Point, visible: tuple[Point, ...]) -> StarterRoute:
    """Stop at FIRST trigger entry; subsequent cells may belong to another map."""
    blocked = visible
    candidates = ((x, y) for y in range(24, 19, -1) for x in range(153, 160))
    for candidate in candidates:
        if not grid.walkable(candidate) or candidate in blocked:
            continue
        try:
            path = shortest_path(grid, start, candidate, blocked_visible=blocked)
        except NoRoute:
            continue
        for index, (x, y) in enumerate(path):
            if 153 <= x <= 159 and 20 <= y <= 24:
                leg = path[: index + 1]
                return StarterRoute(grid.name, leg, leg[-1], True)
    msg = "no reachable public warp trigger"
    raise NoRoute(msg)
