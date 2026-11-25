"""Small generated subset of the pinned runtime GAT caches for population seeding.

See robots.popgen's module docstring for regeneration and validation commands.
The index uses the native cache layout, preserving dimensions and every GAT flag;
common maps load first, then pre-renewal overrides, exactly as playing.build_host.
"""

import logging
import zlib
from collections.abc import Sequence
from functools import cache
from pathlib import Path

from robots.adapters.native_navigation import ENTRY, HEADER, MapCache, Point, nearest_walkable

logger = logging.getLogger(__name__)
INDEX_PATH = Path(__file__).with_name("popgen_map_cache.dat")
SEED_SEARCH_RADIUS = 32  # Chebyshev rings; leg-130's sealed pocket needs 19.


def build_seed_index(source: Path, names: Sequence[str]) -> bytes:
    """Derive a deterministic native-cache subset; no inferred or patched cells."""
    maps = MapCache.load(source / "db/map_cache.dat", source / "db/pre-re/map_cache.dat")
    entries = []
    for name in sorted(set(names)):
        grid = maps.get(name)
        body = zlib.compress(grid.tiles)
        entries.append(ENTRY.pack(name.encode(), grid.width, grid.height, len(body)) + body)
    payload = b"".join(entries)
    return HEADER.pack(HEADER.size + len(payload), len(entries)) + payload


@cache
def seed_cache() -> MapCache:
    """Load only packaged seed maps; missing/corrupt data fails closed."""
    return MapCache.load(INDEX_PATH)


def seed_point(map_name: str, point: Point, *, owner: str, role: str) -> Point:
    """Verify a seed or move to its nearest walkable ring within a fixed bound."""
    grid = seed_cache().maps.get(map_name)
    result = None if grid is None else nearest_walkable(grid, point, radius=SEED_SEARCH_RADIUS)
    if result is None:
        msg = f"no walkable seed within {SEED_SEARCH_RADIUS}: {owner} {role} {map_name} {point}"
        raise ValueError(msg)
    if result != point:
        logger.warning(
            "popgen_seed_relocated owner=%s role=%s map=%s from=%s to=%s radius=%s",
            owner,
            role,
            map_name,
            point,
            result,
            SEED_SEARCH_RADIUS,
        )
    return result
