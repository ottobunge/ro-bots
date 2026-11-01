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
from robots.domain.actions import Attack, Loot, MoveTo  # noqa: E402
from robots.domain.model import Goal  # noqa: E402
from tests.test_playing_runtime import (  # noqa: E402
    Wire,
    entry_at,
    map_frame_at,
)
from tests.test_zc_item_entry_floor import zc_item_entry  # noqa: E402

# CZ_ITEM_PICKUP 0x07E4 for floor item aid 321 (clif_parse_TakeItem, pinned
# MAIN 20180704): type(2) + floor-item AID(4), no len.W (fixed-size frame).
PICKUP = bytes.fromhex("e40741010000")


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
    # one move per item: with the walk minted and the drop still out of
    # range, the next tick authors no second loot action
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
