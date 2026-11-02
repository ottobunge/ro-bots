"""The mechanical loot path: a floor item dispatches the pickup mechanically.

Leg 61: hop 1 was live (39 ItemDrop world events surfaced) but the
decider's argmax starved the pickup (0 loot choices / 518 decides). The
fix is a loot win the argmax cannot lose: the runtime's mechanical layer
(the seam that owns the buy mint) authors the walk toward the drop when
it sits outside the server's pickup radius (Chebyshev>1 of the item's
cell) and dispatches the CZ_ITEM_PICKUP when within it - one attempt per
floor item (the memo clears when the item leaves the floor view), while
an in-melee Attack exchange is never interrupted. The decider's loot
choice (43b5cc2e) remains as an alternative trigger.
"""

import logging
import struct
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
for candidate in (str(REPO / "src"), str(REPO), str(REPO / "tests")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from robots.adapters.native_navigation import MapCache, WalkMap  # noqa: E402
from robots.app import playing_runtime as runtime  # noqa: E402
from robots.app.scripts import MELEE_RANGE  # noqa: E402
from robots.domain.actions import Attack, Loot, MoveTo  # noqa: E402
from robots.domain.model import Goal  # noqa: E402
from tests.test_playing_runtime import (  # noqa: E402
    Wire,
    entry_at,
    map_frame_at,
    monster,
)
from tests.test_zc_item_entry_floor import zc_item_entry  # noqa: E402

# CZ_ITEM_PICKUP 0x07E4 for floor item aid 321: the SERVED packetdb declares
# it var-len (clif_packetdb.hpp:1268 -1 row; the leg-63 session killer), so
# the frame is type(2) + len.W(total=8) + floor-item AID(4) - the 0xC6/0xC7
# var-len precedent.
PICKUP = bytes.fromhex("e407080041010000")


def walk_ack(start: tuple[int, int], end: tuple[int, int]) -> bytes:
    """Native WBUFPOS2 walk-end 0x0087: four packed 10-bit coordinates.

    Built with the same shift/mask construction the tracker decodes
    (destination at raw[8:11]) so the fixture's intent cannot drift from
    its bytes.
    """
    sx, sy = start
    tx, ty = end
    packed = (sx << 30) | (sy << 20) | (tx << 10) | ty
    return struct.pack("<HI", 0x0087, 123) + packed.to_bytes(5, "big") + b"\x88"


def _client_with_floor_at(
    x: int, y: int, *, blocked: tuple[int, int] | None = None
) -> runtime.PlayingClient:
    """A client standing at (42, 37) with one floor item at (x, y)."""
    wire = Wire()
    wire.frames = []
    wire.add(entry_at(42, 37), map_frame_at(42, 37), zc_item_entry(aid=321, item=909, x=x, y=y))
    tiles = bytearray(10000)
    if blocked is not None:
        tiles[blocked[0] + blocked[1] * 100] = 1
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(tiles)),))
    return runtime.PlayingClient(wire, cache=cache)


def test_floor_item_in_range_dispatches_one_pickup_mechanically() -> None:
    """Chebyshev<=1 of the item's cell: the pickup mints with no decide."""
    client = _client_with_floor_at(43, 38)
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (Loot(),)
    client.perform_native(Loot())
    assert client.wire.sent == [PICKUP]


def test_floor_item_out_of_range_mints_move_then_pickup_on_arrival() -> None:
    """Two-step: the mechanical layer authors the walk toward the drop
    once, and the pickup mints when the tracked cell is within the
    server's pickup radius (Chebyshev<=1)."""
    client = _client_with_floor_at(44, 40)
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (MoveTo(x=44, y=40),)
    # with the walk minted and the drop still out of range, the next tick
    # (well inside LOOT_WALK_REAUTH_S, real clock) authors no second loot
    # action - the re-author fires only on the bounded faster clock
    state = client.build_native_state(Goal.GRIND)
    assert not any(isinstance(a, Loot) for a in client.mechanical_actions(state, ()))
    # the walk ends adjacent to the drop (the tracked cell is the walk
    # destination) and the pickup mints
    client.wire.add(walk_ack((42, 37), (44, 39)))
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (Loot(),)
    client.perform_native(Loot())
    assert client.wire.sent == [PICKUP]


def test_melee_exchange_is_never_interrupted() -> None:
    """The leg-61 guard carries over: an authored Attack (an in-melee
    exchange) owns the tick even with a drop inside pickup range."""
    client = _client_with_floor_at(43, 38)
    state = client.build_native_state(Goal.GRIND)
    authored = (Attack(target_id=123),)
    assert client.mechanical_actions(state, authored) == authored


def test_pickup_memo_prevents_spam() -> None:
    """One pickup attempt per floor item: neither a repeated mechanical
    tick nor a repeated dispatch sends a second CZ_ITEM_PICKUP while the
    item stays on the floor."""
    client = _client_with_floor_at(43, 38)
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (Loot(),)
    client.perform_native(Loot())
    client.perform_native(Loot())  # e.g. the decider's loot choice, twice
    state = client.build_native_state(Goal.GRIND)
    assert not any(isinstance(a, Loot) for a in client.mechanical_actions(state, ()))
    assert client.wire.sent == [PICKUP]


def test_memo_clears_when_the_item_leaves_the_floor_view() -> None:
    """The memo is presence-keyed: once the drop is no longer on the floor
    view, the aid is free again - a later real drop at the same aid loots."""
    client = _client_with_floor_at(43, 38)
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (Loot(),)
    client.perform_native(Loot())
    # the item leaves (0x00A1) and the absence is observed on a tick
    client.wire.add(struct.pack("<HI", 0x00A1, 321))
    state = client.build_native_state(Goal.GRIND)
    assert not any(isinstance(a, Loot) for a in client.mechanical_actions(state, ()))
    # the aid is reused by a real new drop: it loots again
    client.wire.add(zc_item_entry(aid=321, item=909, x=43, y=38))
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (Loot(),)


def test_move_toward_an_unwalkable_drop_cell_reroutes_walkable() -> None:
    """Walkability-aware: the authored target is a walkable cell, never
    the blocked drop cell."""
    client = _client_with_floor_at(44, 40, blocked=(44, 40))
    state = client.build_native_state(Goal.GRIND)
    actions = client.mechanical_actions(state, ())
    loot_minted = [a for a in actions if isinstance(a, MoveTo)]
    assert len(loot_minted) == 1
    move = loot_minted[0]
    assert (move.x, move.y) != (44, 40)
    assert client.cache is not None
    assert client.cache.get("prontera").walkable((move.x, move.y))


def test_mechanical_loot_taps_name_the_dispatch_and_move(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The leg-62 log proves the mechanical path live: one line per
    move-toward mint and one per mechanical pickup dispatch."""
    client = _client_with_floor_at(44, 40)
    state = client.build_native_state(Goal.GRIND)
    with caplog.at_level(logging.WARNING):
        client.mechanical_actions(state, ())
        moved = [
            record.getMessage()
            for record in caplog.records
            if "move toward floor item" in record.getMessage()
        ]
        assert len(moved) == 1
        assert "fid=321" in moved[0]
        assert "nameid=909" in moved[0]
        assert "cell=(44,40)" in moved[0]
    client.wire.add(walk_ack((42, 37), (44, 39)))
    state = client.build_native_state(Goal.GRIND)
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        client.mechanical_actions(state, ())
        dispatched = [
            record.getMessage()
            for record in caplog.records
            if "mechanical pickup dispatched" in record.getMessage()
        ]
        assert len(dispatched) == 1
        assert "fid=321" in dispatched[0]
        assert "nameid=909" in dispatched[0]


# ---------------------------------------------------------------------
# The leg-63 slice: the loot pace (a bounded faster re-auth clock so the
# ~60s server floor TTL stops eating drops) + Otto's directive (the pickup
# fires only when the surroundings are safe - no attackable monster within
# ACTIVE_THREAT_RANGE, no in-flight Attack exchange).


def _clocked_client_with_floor_at(x: int, y: int) -> tuple[runtime.PlayingClient, list[float]]:
    """A client standing at (42, 37) with one floor item at (x, y) and a
    test-owned monotonic clock (pacing asserted on the clock, never sleeps)."""
    wire = Wire()
    wire.frames = []
    wire.add(entry_at(42, 37), map_frame_at(42, 37), zc_item_entry(aid=321, item=909, x=x, y=y))
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    now = [1000.0]
    client = runtime.PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    return client, now


def test_loot_walk_reauthors_once_on_the_faster_clock() -> None:
    """Leg 62: the one-shot move memo burned a drop's only walk on a
    pre-empting script MoveTo (move_gates await_pending 9207 in the
    receipt). The loot walk re-authors ONCE per item after
    LOOT_WALK_REAUTH_S - a bounded faster pacing constant inside the
    pending-walk lifecycle's own 1s no-progress release, never spam."""
    assert 0 < runtime.LOOT_WALK_REAUTH_S <= 1.0
    client, now = _clocked_client_with_floor_at(44, 40)
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (MoveTo(x=44, y=40),)
    client.perform_native(MoveTo(44, 40))
    assert len(client.wire.moves) == 1
    # before the clock elapses the memo still holds: no re-author
    now[0] += runtime.LOOT_WALK_REAUTH_S - 0.1
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == ()
    # past the clock: exactly ONE re-author, and its walk actually sends
    # (the pending lifecycle's 1s no-progress release has elapsed too)
    now[0] += 0.2
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (MoveTo(x=44, y=40),)
    client.perform_native(MoveTo(44, 40))
    assert len(client.wire.moves) == 2
    # bounded: never a third mint for the same item
    now[0] += 10.0
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == ()
    assert len(client.wire.moves) == 2


def test_pickup_dispatches_when_no_monster_is_an_active_threat() -> None:
    """The gate open (the control): in range, no monsters in view - the
    mechanical pickup dispatches and the CZ_ITEM_PICKUP send lands."""
    client = _client_with_floor_at(43, 38)
    state = client.build_native_state(Goal.GRIND)
    assert state.nearby_monsters == ()
    assert client.mechanical_actions(state, ()) == (Loot(),)
    client.perform_native(Loot())
    assert client.wire.sent == [PICKUP]


def test_attackable_within_active_threat_range_defers_the_pickup(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Otto's directive: an attackable monster within ACTIVE_THREAT_RANGE
    defers the loot path - no Loot minted, the defer tap names the nearest
    threat distance, and the send seam stays fail-closed against the
    decider's authored Loot too. The item may despawn: safety over loot."""
    client = _client_with_floor_at(43, 38)
    client.wire.add(monster(kind=5, aid=555, at=(43, 38)))  # Chebyshev 1
    state = client.build_native_state(Goal.GRIND)
    assert any(m.id == 555 for m in state.nearby_monsters)
    with caplog.at_level(logging.WARNING):
        assert client.mechanical_actions(state, ()) == ()
        deferred = [
            record.getMessage()
            for record in caplog.records
            if "pickup deferred (threat)" in record.getMessage()
        ]
        assert len(deferred) == 1
        assert "fid=321" in deferred[0]
        assert "nearest=1" in deferred[0]
    # bounded telemetry: the next threatened tick taps nothing new
    caplog.clear()
    state = client.build_native_state(Goal.GRIND)
    with caplog.at_level(logging.WARNING):
        assert client.mechanical_actions(state, ()) == ()
        assert not [
            record for record in caplog.records if "pickup deferred (threat)" in record.getMessage()
        ]
    client.perform_native(Loot())
    assert client.wire.sent == []


def test_threat_boundary_is_melee_range_plus_two() -> None:
    """The named constant: ACTIVE_THREAT_RANGE is the melee engagement
    distance +2 (the brain's _attackable_in_melee_range precedent); a
    monster AT the boundary defers, just outside it the pickup fires."""
    assert runtime.ACTIVE_THREAT_RANGE == MELEE_RANGE + 2
    at_boundary = _client_with_floor_at(43, 38)
    at_boundary.wire.add(monster(kind=5, aid=556, at=(45, 40)))  # Chebyshev 3
    state = at_boundary.build_native_state(Goal.GRIND)
    assert at_boundary.mechanical_actions(state, ()) == ()
    just_outside = _client_with_floor_at(43, 38)
    just_outside.wire.add(monster(kind=5, aid=557, at=(46, 41)))  # Chebyshev 4
    state = just_outside.build_native_state(Goal.GRIND)
    assert just_outside.mechanical_actions(state, ()) == (Loot(),)


def test_in_flight_attack_exchange_defers_the_loot_path() -> None:
    """The 43b5cc2e guard carries: an authored Attack (an in-flight
    exchange) owns the tick - the loot path authors nothing and the
    pickup send stays silent."""
    client = _client_with_floor_at(43, 38)
    state = client.build_native_state(Goal.GRIND)
    authored = (Attack(target_id=555),)
    assert client.mechanical_actions(state, authored) == authored
    client.perform_native(Attack(target_id=555))
    assert not any(frame == PICKUP for frame in client.wire.sent)


def test_pickup_fires_once_the_threat_walks_away() -> None:
    """The threat leaves (the 0x09FD move entry tracks the mob's
    destination): a later dispatch mints the pickup and the send lands."""
    client = _client_with_floor_at(43, 38)
    client.wire.add(monster(kind=5, aid=558, at=(43, 38)))
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == ()
    move = bytearray(110)
    struct.pack_into("<HHBII", move, 0, 0x09FD, 110, 5, 558, 77)
    packed = (43 << 30) | (38 << 20) | (60 << 10) | 60
    move[63:68] = packed.to_bytes(5, "big")
    client.wire.add(bytes(move))
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (Loot(),)
    client.perform_native(Loot())
    assert client.wire.sent == [PICKUP]
