"""Public geometry tests; no sockets, SQL or private actor fixtures."""

import hashlib
import re
import struct
import subprocess
import zlib
from pathlib import Path

import pytest

from robots.adapters import native_navigation
from robots.adapters.native_gameplay import NativeGameplayTracker
from robots.adapters.native_navigation import (
    InvalidMapCache,
    MapCache,
    NoRoute,
    WalkMap,
    shortest_path,
    starter_route,
)

SOURCE = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source")


def cache_bytes(name: str, width: int, height: int, tiles: bytes) -> bytes:
    return packed_body(name.encode(), width, height, zlib.compress(tiles))


def packed_body(name: bytes, width: int, height: int, body: bytes) -> bytes:
    entry = struct.pack("<12shhi", name, width, height, len(body)) + body
    return struct.pack("<IH2x", 8 + len(entry), 1) + entry


@pytest.fixture(scope="module")
def public_cache():
    return MapCache.load(SOURCE / "db/map_cache.dat", SOURCE / "db/pre-re/map_cache.dat")


def test_compressed_public_geometry_routes_around_wall():
    cache = MapCache.from_bytes(cache_bytes("test", 3, 3, bytes([0, 1, 0] * 2 + [0, 0, 0])))
    assert shortest_path(cache.get("test"), (0, 0), (2, 0)) == (
        (0, 0),
        (0, 1),
        (0, 2),
        (1, 2),
        (2, 2),
        (2, 1),
        (2, 0),
    )


def test_source_backed_starter_warp_reachable(public_cache):
    plan = starter_route(public_cache, "prontera", (150, 154))
    assert plan.warp_tile == (156, 22)
    assert plan.trigger_rectangle == (153, 20, 159, 24)
    assert plan.destination_map == "prt_fild08"
    assert plan.destination == (170, 375)
    assert plan.path[0] == (150, 154)
    assert plan.path[-1] == plan.approach
    assert plan.next_waypoint == plan.path[1]
    assert plan.requires_map_change
    assert public_cache.get("prt_fild08").walkable(plan.destination)
    for left, right in zip(plan.path, plan.path[1:], strict=False):
        assert max(abs(left[0] - right[0]), abs(left[1] - right[1])) == 1
        assert public_cache.get("prontera").walkable(right)


def test_visible_blocked_preferred_trigger_uses_other_entry(public_cache):
    plan = starter_route(public_cache, "prontera", (150, 154), blocked_visible=((156, 24),))
    assert plan.approach != (156, 24)
    assert plan.requires_map_change


@pytest.mark.parametrize(
    ("tile", "walk", "shoot"),
    [
        (0, True, True),
        (1, False, False),
        (2, True, True),
        (3, True, True),
        (4, True, True),
        (5, False, True),
        (6, True, True),
        (255, False, False),
    ],
)
def test_source_gat_flags(tile, walk, shoot):
    grid = WalkMap("test", 1, 1, bytes([tile]))
    assert grid.walkable((0, 0)) is walk
    assert grid.shootable((0, 0)) is shoot


@pytest.mark.parametrize(
    "point", [(True, 0), (0, False), (-1, 0), (3, 0), (0, 3), (0.0, 0), (0,), [0, 0]]
)
def test_invalid_coordinate_explicit_failure(point):
    with pytest.raises(NoRoute):
        shortest_path(WalkMap("test", 3, 3, bytes(9)), point, (2, 2))


def test_diagonal_cannot_cut_static_corner():
    with pytest.raises(NoRoute):
        shortest_path(WalkMap("test", 2, 2, bytes([0, 1, 1, 0])), (0, 0), (1, 1))


def test_diagonal_cannot_cut_visible_corner():
    grid = WalkMap("test", 2, 2, bytes(4))
    assert len(shortest_path(grid, (0, 0), (1, 1), blocked_visible=((1, 0),))) == 3


def test_start_equals_target():
    assert shortest_path(WalkMap("test", 1, 1, bytes(1)), (0, 0), (0, 0)) == ((0, 0),)


@pytest.mark.parametrize("blocker", [(True, 0), (-1, 0), (2, 0)])
def test_invalid_visible_blockers(blocker):
    with pytest.raises(NoRoute):
        shortest_path(WalkMap("test", 2, 2, bytes(4)), (0, 0), (1, 1), blocked_visible=(blocker,))


def test_blocked_target_fails():
    with pytest.raises(NoRoute):
        shortest_path(WalkMap("test", 2, 2, bytes(4)), (0, 0), (1, 1), blocked_visible=((1, 1),))


@pytest.mark.parametrize(
    "data",
    [
        b"",
        bytes(7),
        struct.pack("<IH2x", 8, 1),
        struct.pack("<IH2x", 9, 0),
        struct.pack("<IH2x", 9, 0) + b"x",
    ],
)
def test_invalid_cache_header(data):
    with pytest.raises(InvalidMapCache):
        MapCache.from_bytes(data)


@pytest.mark.parametrize(
    ("width", "height", "tiles"),
    [(0, 1, b""), (-1, 1, b""), (32767, 32767, b""), (2, 2, bytes(3)), (2, 2, bytes(5))],
)
def test_invalid_dimensions_or_tile_length(width, height, tiles):
    with pytest.raises(InvalidMapCache):
        MapCache.from_bytes(cache_bytes("test", width, height, tiles))


@pytest.mark.parametrize(
    "body",
    [
        b"garbage",
        zlib.compress(bytes(4))[:-1],
        zlib.compress(bytes(4)) + b"tail",
        zlib.compress(bytes(4)) + zlib.compress(bytes(4)),
        zlib.compress(bytes(1000000)),
        b"",
    ],
)
def test_malformed_zlib_bounded(body):
    with pytest.raises(InvalidMapCache):
        MapCache.from_bytes(packed_body(b"test", 2, 2, body))


@pytest.mark.parametrize("name", [b"", b"\xff"])
def test_invalid_names(name):
    with pytest.raises(InvalidMapCache):
        MapCache.from_bytes(packed_body(name, 1, 1, zlib.compress(bytes(1))))


def test_exact_utf8_name_identity():
    cache = MapCache.from_bytes(cache_bytes("Tést.gat", 1, 1, bytes(1)))
    assert cache.get("Tést.gat").name == "Tést.gat"
    with pytest.raises(NoRoute):
        cache.get("tést")


def test_duplicate_name_rejected():
    entry = cache_bytes("test", 1, 1, bytes(1))[8:]
    with pytest.raises(InvalidMapCache):
        MapCache.from_bytes(struct.pack("<IH2x", 8 + 2 * len(entry), 2) + entry + entry)


def test_entry_header_truncation_rejected():
    data = cache_bytes("test", 1, 1, bytes(1))
    entry = data[8:]
    with pytest.raises(InvalidMapCache):
        MapCache.from_bytes(struct.pack("<IH2x", 8 + len(entry) + 1, 2) + entry + b"x")


def test_unknown_map_explicit(public_cache):
    with pytest.raises(NoRoute):
        public_cache.get("not-a-map")


def test_field_route_uses_only_caller_target(public_cache):
    plan = starter_route(public_cache, "prt_fild08", (170, 375), field_target=(170, 370))
    assert plan.path[-1] == (170, 370)
    assert not plan.requires_map_change
    idle = starter_route(public_cache, "prt_fild08", (170, 375))
    assert idle.next_waypoint is None


def test_already_in_trigger_has_no_synthetic_walk(public_cache):
    assert starter_route(public_cache, "prontera", (156, 24)).next_waypoint is None


def test_other_map_not_universal_route(public_cache):
    with pytest.raises(NoRoute):
        starter_route(public_cache, "prt_fild05", (100, 100))


def test_missing_field_explicit():
    with pytest.raises(NoRoute):
        starter_route(MapCache([WalkMap("prontera", 1, 1, bytes(1))]), "prontera", (0, 0))


def test_unwalkable_destination_explicit():
    field = WalkMap("prt_fild08", 400, 400, bytes([1]) * 160000)
    with pytest.raises(NoRoute):
        starter_route(MapCache([field]), "prt_fild08", (170, 375))


def test_no_reachable_trigger_explicit():
    town = WalkMap("prontera", 160, 25, bytes([1]) * 4000)
    field = WalkMap("prt_fild08", 400, 400, bytes(160000))
    with pytest.raises(NoRoute):
        starter_route(MapCache([town, field]), "prontera", (0, 0))


def test_invalid_starter_position_explicit(public_cache):
    with pytest.raises(NoRoute):
        starter_route(public_cache, "prontera", (True, 24))


def test_aggregate_tile_budget_rejected_before_expansion(monkeypatch):
    monkeypatch.setattr(native_navigation, "MAX_TOTAL_TILES", 3)
    with pytest.raises(InvalidMapCache, match="aggregate tile budget"):
        MapCache.from_bytes(cache_bytes("test", 2, 2, bytes(4)))


def test_cache_override_order(tmp_path):
    common = tmp_path / "common.dat"
    selected = tmp_path / "selected.dat"
    common.write_bytes(cache_bytes("test", 1, 1, bytes([1])))
    selected.write_bytes(cache_bytes("test", 1, 1, bytes([3])))
    assert MapCache.load(common, selected).get("test").walkable((0, 0))


def test_pinned_public_provenance():
    expected = {
        "db/map_cache.dat": "00d277d00e70f476ceef9608f0b45a2a85bfc5ebf1fabf92f46e86f63648282e",
        "db/pre-re/map_cache.dat": (
            "7a58a94bada98c5457fce3fc9bf950b4111fdf494d0488c54d716516707a8433"
        ),
        "npc/warps/cities/prontera.txt": (
            "434fe0daf761275cf731c343a501c02d88355a524b9c9a87d1f00c510ae3f4d7"
        ),
    }
    for relative, digest in expected.items():
        assert hashlib.sha256((SOURCE / relative).read_bytes()).hexdigest() == digest
    assert (
        "prontera,156,22,0\twarp\tprt001\t3,2,prt_fild08,170,375"
        in (SOURCE / "npc/warps/cities/prontera.txt").read_text()
    )


def test_compiled_pinned_native_struct_layout(tmp_path):
    source = (SOURCE / "src/tool/mapcache.cpp").read_text()
    structs = "\n".join(re.findall(r"struct (?:main_header|map_info) \{[^}]+\}", source))
    macros = (SOURCE / "src/common/mmo.hpp").read_text()
    match = re.search(r"#define MAP_NAME_LENGTH .*", macros)
    assert match is not None
    name_length = match.group()
    code = (
        "#include <cstdint>\n#include <cstddef>\n#include <cstdio>\n"
        "using uint32=uint32_t; using uint16=uint16_t; using int16=int16_t; using int32=int32_t;\n"
        + name_length
        + "\n"
        + structs.replace("}", "};")
        + '\nint main(){printf("%zu %zu %zu %zu %zu %zu %zu",sizeof(main_header),'
        "offsetof(main_header,map_count),sizeof(map_info),offsetof(map_info,name),"
        "offsetof(map_info,xs),offsetof(map_info,ys),offsetof(map_info,len));}"
    )
    cpp = tmp_path / "oracle.cpp"
    executable = tmp_path / "oracle"
    cpp.write_text(code)
    subprocess.run(["c++", str(cpp), "-o", str(executable)], check=True, timeout=20)
    result = subprocess.run(
        [str(executable)], check=True, capture_output=True, text=True, timeout=5
    )
    assert result.stdout == "8 4 20 0 12 14 16"


def test_mark_walkable_ground_corrects_cited_cells() -> None:
    """The map-cache tool has marked rathena warp cells blocked (tile 1) —
    the cited warp declaration proves them walkable on the live server
    (the players warp through (170,378) on prt_fild08). mark_walkable
    ground-corrects such cells so client-side pathfinding can route the
    merchant trip (the w65-69 no_route root cause)."""
    width, height = 4, 4
    tile_rows = bytearray([0] * width * height)
    tile_rows[3 * width + 3] = 1  # the cited warp cell: cached blocked
    tiles = bytes(tile_rows)
    cache = MapCache([WalkMap("prt_fild08", width, height, tiles)])
    assert not cache.get("prt_fild08").walkable((3, 3))

    cache.mark_walkable("prt_fild08", (3, 3))
    assert cache.get("prt_fild08").walkable((3, 3))


def test_mark_walkable_unknown_map_or_out_of_bounds_is_noop() -> None:
    cache = MapCache([WalkMap("m", 2, 2, bytes([0, 0, 0, 0]))])
    cache.mark_walkable("nope", (0, 0))  # no raise
    cache.mark_walkable("m", (9, 9))  # out of bounds: no raise
    assert cache.get("m").walkable((0, 0))


def test_tracker_0x0087_tracks_walk_destination() -> None:
    """A clientless client has no walk interpolation: the tracked position
    after a move-end (0x0087) must be the walk DESTINATION, not the
    from-cell — otherwise every approach recomputes from the stale start
    and re-walks the same first cell forever (the w65-78 crawl)."""
    tracker = NativeGameplayTracker(own_actor_id=999)
    entry = (
        struct.pack("<H", 0x02EB)
        + bytes(4)
        + bytes((167 >> 2, ((167 & 3) << 6) | ((352 >> 4) & 15), ((352 & 15) << 4)))
        + bytes(4)
    )
    # the move-end: the from (167,352) at 6..8, the to (168,352) in the raw[8:11]
    frm = bytes((167 >> 2, ((167 & 3) << 6) | ((352 >> 4) & 15), ((352 & 15) << 4) | (168 >> 6)))
    b = ((168 & 63) << 2) | ((352 >> 8) & 3)
    c = 352 & 255
    d = 352 & 255
    move_end = struct.pack("<H", 0x0087) + bytes(4) + frm + bytes([b, c, d])
    frames = ((1, 1.0, 0x02EB, entry), (2, 2.0, 0x0087, move_end))
    assert tracker.consume_snapshot(1, 0, frames) is True
    assert tracker._position is not None
    assert (tracker._position.x, tracker._position.y) == (
        168,
        352,
    ), "the tracked position must be the walk DESTINATION"
    assert tracker._arrival is False  # the walk is IN FLIGHT (from != to)
