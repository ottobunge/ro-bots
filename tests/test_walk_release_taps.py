"""The silent pending-walk release tap (leg 68 defect 2): the (226,317)
pocket's refusals name themselves.

Leg 68: s00 sealed at pay_fild04 (226,317) 88min - escalated_target_dead
x731 - and the receipt could only INFER "every far target was
server-refused": a walk the server refuses releases through
``_await_pending``'s no-progress branch after 1s with NO gate note. The
tap notes the release WITH its origin (step / direct / rerolled /
escalated) so the next receipt reads which walk class the server ate.
TAP-ONLY slice: the release behavior is unchanged - pending clears, the
step re-authors, the same 1s pacing applies.
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


def _client(
    tiles: bytes, size: int = 100, pos: tuple[int, int] = (42, 37)
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


def _reasons(client: runtime.PlayingClient) -> list[str]:
    return [reason for _, reason in getattr(client, "_move_gate_reasons", ())]


def test_step_walk_release_names_itself() -> None:
    """A normal paced step the server never confirms releases after 1s -
    the leg-68 silent branch - and the note names the step origin."""
    wire, client, now = _client(bytes(10000))
    client.perform_native(MoveTo(43, 37))
    assert wire.moves, "the step must be sent (behavior unchanged)"
    sent_before = len(wire.moves)
    now[0] += 2.0
    client.perform_native(MoveTo(43, 37))
    assert "walk_released_no_progress(step)" in _reasons(client)
    # the release behavior is unchanged: pending cleared, the step re-authors
    assert len(wire.moves) == sent_before + 1


def test_direct_send_release_names_direct_origin() -> None:
    """A no-route target direct-send whose walk the server never confirms:
    the release note carries the direct origin (the leg-28 fallback's own
    refusals become countable)."""
    tiles = bytearray(bytes(10000))
    tiles[37 * 100 + 50] = 1  # the target cell itself is a wall -> NoRoute
    wire, client, now = _client(bytes(tiles))
    client.perform_native(MoveTo(50, 37))
    assert wire.moves, "the direct send must go out (behavior unchanged)"
    now[0] += 2.0
    client.perform_native(MoveTo(50, 37))
    assert "walk_released_no_progress(direct)" in _reasons(client)


def test_escalated_release_names_escalated_origin() -> None:
    """The leg-39 escalation walk (the pocket's own escape attempt): its
    release names the escalated origin - the exact evidence leg 68 lacked
    when it could only infer the server had refused every far target."""
    size = 16
    tiles = bytearray([1]) * (size * size)
    for x in range(3, 8):
        for y in range(3, 8):  # the target's radius-2 pocket is unwalkable
            tiles[x + y * size] = 0 if (x, y) == (10, 10) else 1
    tiles[10 + 10 * size] = 0
    wire, client, now = _client(bytes(tiles), size=size, pos=(1, 1))
    for _ in range(runtime.NO_ROUTE_DIRECT_SENDS):
        client.perform_native(MoveTo(5, 5))
        client._pending = None
    client.perform_native(MoveTo(5, 5))  # the escalation send (10, 10)
    assert wire.moves[-1] == (10, 10)
    now[0] += 2.0
    client.perform_native(MoveTo(5, 5))
    assert "walk_released_no_progress(escalated)" in _reasons(client)


def test_rerolled_release_names_rerolled_origin() -> None:
    """The leg-37 reroll walk: its release names the rerolled origin."""
    size = 16
    tiles = bytearray([1]) * (size * size)
    tiles[5 + 5 * size] = 1  # the target cell is a wall -> NoRoute
    tiles[7 + 5 * size] = 0  # the radius-2 reroll alt
    wire, client, now = _client(bytes(tiles), size=size, pos=(1, 1))
    for _ in range(runtime.NO_ROUTE_DIRECT_SENDS):
        client.perform_native(MoveTo(5, 5))
        client._pending = None
    client.perform_native(MoveTo(5, 5))  # the reroll send (7, 5)
    assert wire.moves[-1] == (7, 5)
    now[0] += 2.0
    client.perform_native(MoveTo(5, 5))
    assert "walk_released_no_progress(rerolled)" in _reasons(client)


def test_progress_walks_still_wait_without_the_note() -> None:
    """A walk whose position frames ADVANCE is in flight, not refused: no
    release note (the note must name refusals, not normal pacing)."""
    wire, client, now = _client(bytes(10000))
    client.perform_native(MoveTo(43, 37))
    wire.add(walk_ack((42, 37), (43, 37)))
    now[0] += 2.0
    client.perform_native(MoveTo(43, 37))
    assert not any(reason.startswith("walk_released_no_progress(") for reason in _reasons(client))
