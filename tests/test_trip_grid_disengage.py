"""Leg-100 offline regressions using committed geometry and received wire frames."""

import hashlib
import struct
from pathlib import Path

import pytest

from robots.adapters.native_navigation import MapCache, Point, WalkMap, shortest_path
from robots.app import scripts
from robots.app.scripts import GrindScript
from robots.domain.actions import Attack, Rest
from robots.domain.model import Goal
from tests.test_playing_runtime import monster, walk_ack
from tests.test_roam_trip_priority import hit
from tests.test_trip_pacing_survival import setup


@pytest.fixture(autouse=True)
def clean_trips():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


@pytest.fixture(scope="module")
def field():
    root = Path("run/worlds/test-first-live-86e7c36895db/runtime/db")
    return MapCache.load(root / "map_cache.dat", root / "pre-re/map_cache.dat").get("pay_fild04")


def server_clear(grid: WalkMap, start: Point, end: Point) -> bool:
    """Independent integer-line oracle: pinned path.cpp path_search_long."""
    x, y = start
    tx, ty = end
    if tx < x:
        x, y, tx, ty = tx, ty, x, y
    dx, dy = tx - x, ty - y
    weight = max(dx, abs(dy))
    wx = wy = 0
    while (x, y) != (tx, ty):
        wx += dx
        wy += dy
        if wx >= weight:
            wx -= weight
            x += 1
        if wy >= weight:
            wy -= weight
            y += 1
        elif wy < 0:
            wy += weight
            y -= 1
        if (x, y) != (tx, ty) and not grid.walkable((x, y)):
            return False
    return True


def test_committed_server_grid_requires_the_east_north_detour(field):
    server = MapCache.load(
        Path("rathena/db/map_cache.dat"), Path("rathena/db/pre-re/map_cache.dat")
    )
    assert field.tiles == server.get("pay_fild04").tiles
    assert hashlib.sha256(field.tiles).hexdigest() == (
        "007763bf7128951bcbff84a6b863599f8deb203fbfd40e5bae1eebaf5d5e6a71"
    )
    assert not field.walkable((190, 176))  # GAT 5, a non-walkable gap
    assert not field.walkable((150, 176))  # GAT 1, non-walkable ground
    path = shortest_path(field, (204, 176), (17, 165))
    assert len(path) - 1 == 435
    assert path[24] == (228, 177)
    assert max(y for _, y in path) == 338


@pytest.mark.parametrize("start", [(204, 176), (244, 200)])
def test_real_grid_trip_chunks_converge_under_official_server_limits(field, start, monkeypatch):
    wire, client, now = setup(start)
    client.cache = MapCache((field,))
    inventory = bytearray(28)
    struct.pack_into("<HHHH", inventory, 0, 0x0991, 28, 2, 511)
    struct.pack_into("<h", inventory, 9, 19)
    wire.add(bytes(inventory), struct.pack("<HHi", 0x00B0, 24, 19))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    farm = GrindScript(merchant_travel_target=client.merchant_travel_target)
    distances = []
    sent = []
    last_position = None
    for tick in range(200):
        now[0] = tick * 2.3
        client.drain_native_events()
        state = client.build_native_state(Goal.GRIND)
        assert state.inventory_known
        assert state.inventory == {"511": 19}
        position = (state.x, state.y)
        if position != last_position:
            distances.append(len(shortest_path(field, position, (17, 165))) - 1)
            last_position = position
        if position == (17, 165):
            break
        before = len(wire.moves)
        for action in farm.step(state).actions:
            client.perform_native(action)
        if len(wire.moves) != before:
            endpoint = wire.moves[-1]
            path = shortest_path(field, position, endpoint)
            cells = len(path) - 1
            assert cells <= 14 or server_clear(field, position, endpoint)
            assert cells <= 17
            sent.append(endpoint)
            # Each author tick is 11.5s apart; all <=17-cell legs finish first.
            wire.add(walk_ack(position, endpoint))
    assert position == (17, 165)
    assert distances == sorted(set(distances), reverse=True)
    assert sent[-1][0] < start[0]
    assert now[0] < 435
    assert not scripts._MERCHANT_TRIPS[state.name].retry_at


@pytest.mark.parametrize("trigger", ["species_hit", "hp_floor"])
def test_engaged_target_disengages_at_wire_and_without_another_attack(trigger, caplog):
    wire, client, now = setup((100, 165))
    wire.add(monster(at=(101, 165)))
    client.perform_native(Attack(123))
    assert wire.sent[-1] == bytes.fromhex("37047b00000000")
    if trigger == "species_hit":
        wire.add(hit(source=123, target=999, amount=31))
        client.perform_native(Attack(123))
    else:
        wire.status_params[5] = 39
        client.drain_native_events()  # HP floor must work even if script authors Rest/empty
    assert wire.moves
    assert wire.moves[-1][0] < 100  # away from the engaged target at (101,165)
    assert "disengage_" in caplog.text
    # A new attack on a safe actor cannot steal an active disengage.
    wire.add(monster(aid=456, at=(99, 165)))
    count = len([raw for raw in wire.sent if isinstance(raw, bytes) and raw[:2] == b"\x37\x04"])
    client.perform_native(Attack(456))
    assert (
        len([raw for raw in wire.sent if isinstance(raw, bytes) and raw[:2] == b"\x37\x04"])
        == count
    )
    # Expiry never re-arms from the old engagement alone.
    now[0] = 9.0
    client.drain_native_events()
    count = len(wire.moves)
    now[0] = 20.0
    client.drain_native_events()
    assert len(wire.moves) == count


def test_refusing_an_unengaged_target_does_not_disengage():
    wire, client, _ = setup((100, 165))
    wire.add(monster(at=(101, 165)), hit(source=123, target=999, amount=31))
    client.perform_native(Attack(123))
    assert not wire.moves


@pytest.mark.parametrize("boundary", ["warp", "death", "rest", "one_hp"])
def test_disengage_preserves_recovery_and_session_boundaries(boundary):
    wire, client, _ = setup((100, 165))
    wire.add(monster(at=(101, 165)))
    client.perform_native(Attack(123))
    if boundary == "warp":
        wire.add(struct.pack("<H16sHH", 0x0091, b"pay_fild04", 100, 165))
    elif boundary == "death":
        wire.add(struct.pack("<HIB", 0x0080, 999, 1))
    elif boundary == "rest":
        client.perform_native(Rest())
    else:
        wire.status_params[5] = 1
    wire.status_params[5] = 1 if boundary == "one_hp" else 39
    client.drain_native_events()
    assert not wire.moves


def test_disengage_uses_the_engaged_targets_latest_position():
    wire, client, _ = setup((100, 165))
    wire.add(monster(at=(101, 165)))
    client.perform_native(Attack(123))
    wire.add(monster(at=(99, 165)), hit(source=123, target=999, amount=31))
    client.drain_native_events()
    assert wire.moves[-1][0] > 100


@pytest.mark.parametrize("boundary", ["stale", "vanished"])
def test_old_engagement_cannot_trigger_a_new_disengage(boundary):
    wire, client, now = setup((100, 165))
    wire.add(monster(at=(101, 165)))
    client.perform_native(Attack(123))
    if boundary == "stale":
        now[0] = 31.0
    else:
        wire.add(struct.pack("<HIB", 0x0080, 123, 0))
    wire.status_params[5] = 39
    client.drain_native_events()
    assert not wire.moves


def test_active_disengage_retains_last_known_position_after_target_leaves_view():
    wire, client, now = setup((100, 165))
    wire.add(monster(at=(101, 165)))
    client.perform_native(Attack(123))
    wire.status_params[5] = 39
    client.drain_native_events()
    assert wire.moves[-1] == (99, 165)
    wire.add(walk_ack((100, 165), (99, 165)), struct.pack("<HIB", 0x0080, 123, 0))
    now[0] = 1.0
    client.drain_native_events()
    now[0] = 2.1
    client.drain_native_events()
    assert wire.moves[-1][0] < 99
