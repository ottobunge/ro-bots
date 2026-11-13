#!/usr/bin/env python3
"""Offline only: dump the committed pay_fild04 grid and compare server caches.

Run from repo root: uv run python scripts/diagnose_trip_grid.py
No sockets, credentials, database access, or character actions.
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

from robots.adapters.native_navigation import MapCache, shortest_path
from robots.app.trip_navigation import trip_chunk_cells

ROOTS = (
    Path("run/worlds/test-first-live-86e7c36895db/runtime"),
    Path("run/public-source/npc-pilot-host-data-exact"),
    Path("rathena"),
)
OUT = Path("wiki/evidence/trip-grid-100")


def load(root):
    return MapCache.load(root / "db/map_cache.dat", root / "db/pre-re/map_cache.dat").get(
        "pay_fild04"
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    grid = load(ROOTS[0])
    evidence = {
        "map": grid.name,
        "dimensions": [grid.width, grid.height],
        "tile_counts": dict(Counter(grid.tiles)),
        "sources": [],
        "routes": [],
        "server_limits": {"max_walk_path": 17, "obstructed_OFFICIAL_WALKPATH": 14},
        "corridor_y176": [
            {"x": x, "gat": grid.tiles[x + 176 * grid.width]}
            for x in (33, 125, 126, 150, 181, 182, 184, 185, 186, 190, 193, 194, 204)
        ],
    }
    for root in ROOTS:
        server = load(root)
        evidence["sources"].append({
            "root": str(root),
            "tiles_sha256": hashlib.sha256(server.tiles).hexdigest(),
            "different_cells": sum(a != b for a, b in zip(grid.tiles, server.tiles, strict=True)),
        })
    for start in ((204, 176), (244, 200), (194, 172)):
        path = shortest_path(grid, start, (17, 165))
        evidence["routes"].append({
            "start": start,
            "target": [17, 165],
            "cells": len(path) - 1,
            "old_chunk24": path[24],
            "new_first_chunk": path[trip_chunk_cells(grid, path)],
            "bounds": [[min(p[i] for p in path), max(p[i] for p in path)] for i in (0, 1)],
            "path": path,
        })
    (OUT / "diagnosis.json").write_text(json.dumps(evidence, indent=2) + "\n")
    symbols = {0: ".", 1: "#", 5: "~"}
    lines = ["pay_fild04 400x400; x increases right, y increases upward.",
             "GAT: .=0 walkable; #=1 wall; ~=5 non-walkable shootable gap."]
    for y in range(grid.height - 1, -1, -1):
        lines.append(f"{y:03d} " + "".join(symbols[t] for t in grid.tiles[y*grid.width:(y+1)*grid.width]))
    (OUT / "grid.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
