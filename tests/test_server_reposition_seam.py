"""The server-reposition seam (leg 69): the escalated-dead release.

Leg 69: s00's pocket RELEASED (226,317 -> 213,325) on the leg-28 direct
sends, then the once-per-position escalation latch (leg 39) turned every
later verdict into ``escalated_target_dead`` - x944 dead verdicts with
zero wire sends and zero TalkToNpc for the rest of the window, while the
server was still accepting walks out of the pocket. The seam: after
``ESCALATED_DEAD_DIRECT_BOUND`` consecutive escalated-dead verdicts at
the same position, the runtime releases a SERVER-REPOSITION direct send
at the nearest client-side walkable cell around the own position
(no_route_direct semantics - the server path-finds its own side);
``ESCALATED_DEAD_REPOSITIONS`` caps the repositions per position and a
server-confirmed position advance re-arms both budgets.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for candidate in (str(REPO / "src"), str(REPO), str(REPO / "tests")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from robots.adapters.native_navigation import MapCache, WalkMap  # noqa: E402
from robots.app import playing_runtime as runtime  # noqa: E402
from robots.domain.actions import MoveTo  # noqa: E402
from tests.test_playing_runtime import Wire, entry_at, map_frame_at, walk_ack  # noqa: E402

SIZE = 24
OWN = (1, 1)
TARGET = (5, 5)  # its whole radius-2 pocket is walled
WALK_A = (10, 10)  # the one walkable cell: ring 9 from OWN, ring 5 from TARGET


def _client(
    tiles: bytes, size: int = SIZE, pos: tuple[int, int] = OWN
) -> tuple[Wire, runtime.PlayingClient, list[float]]:
    wire = Wire()
    now = [0.0]
    client = runtime.PlayingClient(
        wire,
        cache=MapCache((WalkMap("prontera", size, size, bytes(tiles)),)),
        monotonic=lambda: now[0],
    )
    wire.frames = []
    wire.add(entry_at(*pos), map_frame_at(*pos))
    return wire, client, now


def _sealed_pocket_tiles(walkable: list[tuple[int, int]]) -> bytes:
    """An all-walled map with exactly the named walkable cells."""
    tiles = bytearray([1]) * (SIZE * SIZE)
    for x, y in walkable:
        tiles[x + y * SIZE] = 0
    return bytes(tiles)


def _reasons(client: runtime.PlayingClient) -> list[str]:
    return [reason for _, reason in getattr(client, "_move_gate_reasons", ())]


def _exhaust_to_dead_latch(client: runtime.PlayingClient) -> None:
    """Drive the existing machinery to the leg-39 latch: the bounded
    no-route direct sends, then the radius-12 escalation send."""
    for _ in range(runtime.NO_ROUTE_DIRECT_SENDS):
        client.perform_native(MoveTo(*TARGET))
        client._pending = None  # the drain released the slot
    client.perform_native(MoveTo(*TARGET))  # the escalation send
    assert any(reason == "target_unwalkable_escalated" for reason in _reasons(client))
    client._pending = None


def _dead_verdicts(client: runtime.PlayingClient) -> None:
    """Author moves at the latched position; the harness releases the
    pending slot each tick (the drain released it)."""
    for _ in range(runtime.ESCALATED_DEAD_DIRECT_BOUND):
        client.perform_native(MoveTo(*TARGET))
        client._pending = None


def test_escalated_dead_releases_a_server_reposition_direct_send() -> None:
    """After the bound of silent dead verdicts at the latched position the
    runtime walks OUT: a direct send at the nearest client-side walkable
    cell around the own position, paced on the pending lifecycle."""
    wire, client, _ = _client(_sealed_pocket_tiles([WALK_A]))
    _exhaust_to_dead_latch(client)
    sent = len(wire.moves)
    _dead_verdicts(client)
    assert len(wire.moves) == sent, "the bound of dead verdicts stays silent"
    client.perform_native(MoveTo(*TARGET))
    assert wire.moves[-1] == WALK_A, "the reposition walks at the walkable cell"
    assert "server_reposition_direct" in _reasons(client)
    assert client._pending_origin == "repositioned"
    assert client._pending is not None


def test_server_repositions_are_bounded_per_position() -> None:
    """A position whose repositions cannot move the char stops honestly
    again after ESCALATED_DEAD_REPOSITIONS sends - no infinite spin on a
    truly sealed pocket."""
    wire, client, _ = _client(_sealed_pocket_tiles([WALK_A]))
    _exhaust_to_dead_latch(client)
    _dead_verdicts(client)
    for _ in range(runtime.ESCALATED_DEAD_REPOSITIONS):
        client.perform_native(MoveTo(*TARGET))
        client._pending = None
    sent = len(wire.moves)
    client.perform_native(MoveTo(*TARGET))
    assert len(wire.moves) == sent, "the capped position stops honestly"
    assert _reasons(client)[-1] == "escalated_target_dead"


def test_a_position_advance_rearms_the_reposition_budget() -> None:
    """The budgets are per-position: a server-confirmed walk forward (the
    reposition moved the char, or any walk did) re-latches the fresh
    position through the normal machinery and re-arms the dead-verdict
    bound and the reposition cap - the walk-out loop keeps pacing."""
    wire, client, _ = _client(_sealed_pocket_tiles([WALK_A]))
    _exhaust_to_dead_latch(client)
    _dead_verdicts(client)
    for _ in range(runtime.ESCALATED_DEAD_REPOSITIONS):
        client.perform_native(MoveTo(*TARGET))
        client._pending = None
    client.perform_native(MoveTo(*TARGET))  # the capped honest stop
    client._pending = None
    # the server confirms a one-cell walk out of the pocket
    wire.add(walk_ack(OWN, (2, 2)))
    client.drain_native_events()
    # the fresh position escalates once (the leg-39 latch is per-position)
    client.perform_native(MoveTo(*TARGET))
    assert any(reason == "target_unwalkable_escalated" for reason in _reasons(client))
    client._pending = None
    sent = len(wire.moves)
    _dead_verdicts(client)
    assert len(wire.moves) == sent, "the fresh position's bound stays silent"
    client.perform_native(MoveTo(*TARGET))
    assert len(wire.moves) == sent + 1, "the re-arm releases a fresh reposition"
    assert "server_reposition_direct" in _reasons(client)


def test_reposition_stops_honestly_when_no_walkable_cell_is_in_range() -> None:
    """The escalation alt may sit beyond the own-anchored radius (leg 69's
    far dealer-side cells): when the own-position search finds nothing the
    verdict stays an honest stop - no wire flooding."""
    size = 32
    tiles = bytearray([1]) * (size * size)
    tiles[20 + 20 * size] = 0  # the only walkable cell: ring 19 from OWN
    wire, client, _ = _client(bytes(tiles), size=size)
    # the escalation fires (ring 6 from the target 14,14) and latches OWN
    for _ in range(runtime.NO_ROUTE_DIRECT_SENDS):
        client.perform_native(MoveTo(14, 14))
        client._pending = None
    client.perform_native(MoveTo(14, 14))
    assert wire.moves[-1] == (20, 20)
    client._pending = None
    _dead_verdicts(client)
    sent = len(wire.moves)
    client.perform_native(MoveTo(14, 14))
    assert len(wire.moves) == sent, "no walkable cell in range: no send"
    assert _reasons(client)[-1] == "escalated_target_dead"
