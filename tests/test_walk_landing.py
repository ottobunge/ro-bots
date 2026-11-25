"""Dispatched walks must make received progress, even with changing targets."""

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import MoveTo
from robots.domain.model import Goal
from tests.test_playing_runtime import Wire, blocked_map, entry_at, map_frame_at, monster, walk_ack


def _client(*, blocked: bool = False) -> tuple[PlayingClient, Wire, list[float]]:
    wire = Wire()
    wire.frames = []
    wire.add(entry_at(2, 2), map_frame_at(2, 2))
    now = [0.0]
    client = PlayingClient(
        wire,
        cache=blocked_map((2, 2) if blocked else (9, 9)),
        monotonic=lambda: now[0],
        keepalive_interval_s=1000,
    )
    return client, wire, now


def _walk(client: PlayingClient, now: list[float], target: tuple[int, int] = (7, 7)) -> None:
    client.perform_native(MoveTo(*target))
    now[0] += 1.1
    client.drain_native_events()


@pytest.mark.parametrize("blocked", [False, True])
@pytest.mark.parametrize("ack", ["silent", "stationary", "projected"])
def test_no_landing_recovers_then_stops_across_changing_targets(blocked, ack):
    client, wire, now = _client(blocked=blocked)
    for i in range(5):
        client.perform_native(MoveTo(6 + i % 2, 7))
        if ack != "silent":
            # 0x0087's destination is a projection. Repeated from-cells
            # prove no actual landing even when the projected to-cell moves.
            end = (2, 2) if ack == "stationary" else wire.moves[-1]
            wire.add(walk_ack((2, 2), end))
            client.drain_native_events()
        now[0] += 1.1
        client.drain_native_events()
    _walk(client, now)
    assert wire.moves[-1] == (1, 1)
    assert client.last_move_outcome.get("reason") == "stuck_cell_detected"
    _walk(client, now)
    assert wire.moves[-1] != (1, 1)
    assert client.last_move_outcome.get("reason") == "stuck_cell_escalated"
    sent = len(wire.moves)
    for i in range(20):
        _walk(client, now, (4 + i % 4, 7))
    assert len(wire.moves) == sent == 7
    assert client.last_move_outcome.get("reason") == "stuck_cell_exhausted"


def test_blocked_own_cell_is_not_rewritten_as_walkable():
    client, wire, now = _client(blocked=True)
    _walk(client, now)
    assert wire.moves == [(7, 7)]  # retain the bounded leg-28 direct lane
    assert client.cache is not None
    assert not client.cache.get("prontera").walkable((2, 2))


@pytest.mark.parametrize("received", ["walk", "map"])
def test_any_received_cell_change_rearms_exhausted_budget(received):
    client, wire, now = _client()
    for _ in range(9):
        _walk(client, now)
    assert len(wire.moves) == 7
    wire.add(walk_ack((3, 2), (3, 2)) if received == "walk" else map_frame_at(3, 2))
    client.drain_native_events()
    assert client._stuck_epochs == 0
    assert any(reason == "stuck_cell_reset" for _, reason in client._move_gate_reasons)
    _walk(client, now)
    assert len(wire.moves) == 8
    assert client.last_move_outcome.get("reason") == "step"


def test_healthy_walks_and_idle_ticks_never_trigger_recovery():
    client, wire, now = _client()
    for i in range(20):
        point = (2 + i % 2, 3)
        client.perform_native(MoveTo(*point))
        wire.add(walk_ack(point, point))
        client.drain_native_events()
        now[0] += 1.1
    for _ in range(20):
        client.drain_native_events()
    assert client._stuck_epochs == 0
    assert not any(
        reason.startswith("stuck_cell_detected")
        for _, reason in getattr(client, "_move_gate_reasons", ())
    )


def test_pending_ticks_do_not_consume_epochs_and_clients_do_not_share_budget():
    client, wire, now = _client()
    other, _, _ = _client()
    for _ in range(5):
        _walk(client, now)
    _walk(client, now)
    assert client.last_move_outcome.get("reason") == "stuck_cell_detected"
    other.perform_native(MoveTo(7, 7))
    for _ in range(30):
        other.perform_native(MoveTo(7, 7))
    assert other._stuck_epochs == 0
    assert len(wire.moves) == 6
    assert other.build_native_state(Goal.GRIND).x == 2


def test_recovery_skips_received_occupied_cells():
    client, wire, now = _client()
    for _ in range(5):
        _walk(client, now)
    wire.add(monster(kind=0, at=(1, 1)))
    _walk(client, now)
    assert wire.moves[-1] != (1, 1)
    assert client.last_move_outcome.get("reason") == "stuck_cell_detected"


@pytest.mark.parametrize("escape", [None, (8, 8)])
def test_sealed_near_ring_escalates_once_then_exhausts(escape):
    client, wire, now = _client()
    tiles = bytearray([1]) * 100
    if escape is not None:
        tiles[escape[0] + escape[1] * 10] = 0
    client.cache = MapCache((WalkMap("prontera", 10, 10, bytes(tiles)),))
    for _ in range(5):
        _walk(client, now)
    _walk(client, now)
    assert client.last_move_outcome.get("reason") == "stuck_cell_detected"
    assert len(wire.moves) == 5  # no invented walkable neighbor
    _walk(client, now)
    assert client.last_move_outcome.get("reason") == "stuck_cell_escalated"
    if escape is not None:
        assert wire.moves[-1] == escape
    sent = len(wire.moves)
    for _ in range(10):
        _walk(client, now)
    assert len(wire.moves) == sent
    assert client.last_move_outcome.get("reason") == "stuck_cell_exhausted"


def test_same_cell_map_and_session_receipts_do_not_rearm_budget():
    client, wire, now = _client()
    for _ in range(5):
        _walk(client, now)
    wire.add(map_frame_at(2, 2))
    client.drain_native_events()
    assert client._stuck_epochs == 5
    wire.native_epoch += 1
    wire.selection_epoch = wire.map_epoch = wire.native_epoch
    client.drain_native_events()
    assert client._stuck_epochs == 5
    _walk(client, now)
    assert client.last_move_outcome.get("reason") == "stuck_cell_detected"
