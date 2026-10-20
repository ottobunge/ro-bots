"""Offline received-frame patrol contracts; no native world or hidden actors."""

import random
import struct
from dataclasses import replace

import pytest

from robots.adapters.native_navigation import MapCache, NoRoute, WalkMap
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import Attack, GameAction, Rest
from robots.domain.model import Goal
from tests.test_playing_runtime import Wire, entry, walk_ack


class PatrolRng(random.Random):
    def __init__(self) -> None:
        super().__init__(0)
        self.calls = 0

    def randint(self, a: int, b: int) -> int:
        assert (a, b) == (-8, 8)
        self.calls += 1
        return 4 if self.calls <= 32 else 6


def field_frame(x: int = 170, y: int = 375) -> bytes:
    return struct.pack("<H16sHH", 0x0091, b"prt_fild08", x, y)


def setup() -> tuple[Wire, PlayingClient, list[float], PatrolRng]:
    wire = Wire()
    wire.frames = []
    wire.add(entry(), field_frame())
    now = [0.0]
    client = PlayingClient(
        wire,
        cache=MapCache((WalkMap("prt_fild08", 400, 400, bytes(160000)),)),
        monotonic=lambda: now[0],
    )
    rng = PatrolRng()
    client._rng = rng
    return wire, client, now, rng


def test_field_destination_is_committed_across_advance_observations():
    wire, client, _, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    client.mechanical_actions(state, ())
    target = client._field_target(state)
    assert target is not None
    wire.add(walk_ack((171, 376), (171, 376)))
    advanced = client.build_native_state(Goal.GRIND)
    client.mechanical_actions(advanced, ())
    assert client._field_target(advanced) == target == (174, 379)
    assert rng.calls == 32
    assert not wire.moves


def test_field_destination_belongs_only_to_one_client():
    _, first, _, first_rng = setup()
    _, second, _, second_rng = setup()
    first._field_target(first.build_native_state(Goal.GRIND))
    assert second_rng.calls == 0
    second._field_target(second.build_native_state(Goal.GRIND))
    assert first_rng.calls == second_rng.calls == 32


def test_legacy_state_without_native_epoch_keeps_same_leg():
    _, client, _, rng = setup()
    state = replace(client.build_native_state(Goal.GRIND), native_epoch=None)
    target = client._field_target(state)
    assert target is not None
    assert client._field_target(replace(state, x=171)) == target
    assert rng.calls == 32


def test_only_fresh_matching_received_arrival_completes_leg():
    wire, client, _, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    target = client._field_target(state)
    assert target is not None
    wire.add(walk_ack(target, target))
    arrived = client.build_native_state(Goal.GRIND)
    assert client._field_target(arrived) == (180, 385)
    assert rng.calls == 64


@pytest.mark.parametrize("receipt", ["destination", "wrong", "stale", "no_snapshot"])
def test_nonarrival_evidence_keeps_leg(receipt):
    wire, client, _, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    target = client._field_target(state)
    assert target is not None
    if receipt == "destination":
        wire.add(walk_ack((170, 375), target))
        state = client.build_native_state(Goal.GRIND)
    elif receipt == "wrong":
        wire.add(walk_ack((171, 376), (171, 376)))
        state = client.build_native_state(Goal.GRIND)
    elif receipt == "stale":
        assert client._tracker is not None
        client._tracker._arrival = True
        pos = client._tracker.view.position
        assert pos is not None
        client._tracker._position = replace(pos, x=target[0], y=target[1])
    else:
        client._tracker = None
    assert client._field_target(replace(state, x=target[0], y=target[1])) == target
    assert rng.calls == 32


@pytest.mark.parametrize(
    "boundary", ["map_refresh", "epoch", "connect", "close", "goal", "map", "cache"]
)
def test_lifecycle_invalidates_held_destination(boundary, monkeypatch):
    wire, client, _, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    client._field_target(state)
    if boundary == "map_refresh":
        wire.add(field_frame())
        state = client.build_native_state(Goal.GRIND)
    elif boundary == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
        wire.frames = []
        wire.add(entry(), field_frame())
        state = client.build_native_state(Goal.GRIND)
    elif boundary in ("connect", "close"):
        marker = object()
        monkeypatch.setattr(wire, boundary, lambda: marker, raising=False)
        assert getattr(client, boundary)() is marker
    elif boundary == "goal":
        client.mechanical_actions(replace(state, goal=Goal.SOCIAL), ())
    elif boundary == "map":
        assert client._field_target(replace(state, map_name="prontera")) is None
    else:
        client.cache = None
        assert client._field_target(state) is None
        return
    assert client._patrol is None
    assert client._field_target(state) == (176, 381)
    assert rng.calls == 64


def test_goal_switch_replans_without_changing_pending_move():
    _, client, _, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    client._field_target(state)
    pending = ((171, 376), 2, 0.0, 0)
    client._pending = pending
    assert client._field_target(replace(state, goal=Goal.FARM_ITEM)) == (176, 381)
    assert client._pending == pending
    assert rng.calls == 64


def test_deadline_replans_without_inventing_arrival():
    _, client, now, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    target = client._field_target(state)
    assert target is not None
    now[0] = 119.9
    assert client._field_target(state) == target
    now[0] = 120.0
    assert client._field_target(state) == (176, 381)
    assert rng.calls == 64
    assert client._tracker is not None
    pos = client._tracker.view.position
    assert pos is not None
    assert (pos.x, pos.y) == (170, 375) != target


def test_expired_leg_cannot_discard_unconfirmed_movement():
    wire, client, now, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    target = client._field_target(state)
    assert target is not None
    client._move(state, target)
    pending = client._pending
    now[0] = 120.0
    assert client._field_target(state) == target
    assert client._pending == pending
    assert rng.calls == 32
    client._move(state, target)
    assert wire.moves == [(171, 376), (171, 376)]


def test_arrival_cannot_bypass_unmatched_pending_target():
    wire, client, _, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    target = client._field_target(state)
    assert target is not None
    client._pending = ((171, 376), 2, 0.0, 0)
    wire.add(walk_ack(target, target))
    arrived = client.build_native_state(Goal.GRIND)
    assert client._field_target(arrived) == target
    assert rng.calls == 32


def test_matching_pending_final_arrival_allows_next_leg_without_clearing_pending():
    wire, client, _, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    target = client._field_target(state)
    assert target is not None
    pending = (target, 2, 0.0, 0)
    client._pending = pending
    wire.add(walk_ack(target, target))
    arrived = client.build_native_state(Goal.GRIND)
    assert client._field_target(arrived) == (180, 385)
    assert client._pending == pending
    client._move(arrived, (180, 385))
    assert wire.moves == [(175, 380)]
    assert rng.calls == 64


@pytest.mark.parametrize("planner", ["mechanical", "move"])
def test_unreachable_public_destination_invalidates_for_bounded_replan(planner):
    _, client, _, rng = setup()
    tiles = bytearray([1]) * 160000
    tiles[170 + 375 * 400] = 0
    tiles[174 + 379 * 400] = 0
    client.cache = MapCache((WalkMap("prt_fild08", 400, 400, bytes(tiles)),))
    state = client.build_native_state(Goal.GRIND)
    target = client._field_target(state)
    assert target is not None
    if planner == "mechanical":
        assert client.mechanical_actions(state, ()) == ()
    else:
        client._move(state, target)
    assert client._patrol is None
    assert rng.calls == 32


def test_held_destination_does_not_bypass_public_cache_identity():
    _, client, _, _ = setup()
    state = client.build_native_state(Goal.GRIND)
    client._field_target(state)
    client.cache = MapCache(())
    with pytest.raises(NoRoute):
        client._field_target(state)


def test_received_steps_finish_one_leg_before_sampling_another():
    wire, client, _, rng = setup()
    for point in ((171, 376), (172, 377), (173, 378), (174, 379)):
        state = client.build_native_state(Goal.GRIND)
        actions = client.mechanical_actions(state, ())
        assert len(actions) == 1
        client.perform_native(actions[0])
        assert wire.moves[-1] == point
        assert client._patrol is not None
        assert client._patrol.target == (174, 379)
        assert rng.calls == 32
        wire.add(walk_ack(point, point))
    state = client.build_native_state(Goal.GRIND)
    client.mechanical_actions(state, ())
    assert client._patrol is not None
    assert client._patrol.target == (180, 385)
    assert rng.calls == 64


@pytest.mark.parametrize("missing", ["tracker", "position"])
def test_expiry_with_pending_and_missing_observation_cannot_replan(missing):
    _, client, now, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    target = client._field_target(state)
    pending = ((171, 376), 2, 0.0, 0)
    client._pending = pending
    if missing == "tracker":
        client._tracker = None
    else:
        assert client._tracker is not None
        client._tracker._position = None
    now[0] = 120.0
    assert client._field_target(state) == target
    assert client._pending == pending
    assert rng.calls == 32


def test_failed_unrelated_move_preserves_patrol():
    _, client, _, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    client._field_target(state)
    client._move(state, (-1, -1))
    assert client._patrol is not None
    assert client._patrol.target == (174, 379)
    assert rng.calls == 32


def test_unreachable_patrol_retains_unconfirmed_pending():
    _, client, _, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    client._field_target(state)
    pending = ((171, 376), 2, 0.0, 0)
    client._pending = pending
    client.cache = MapCache((WalkMap("prt_fild08", 400, 400, bytes([1]) * 160000),))
    assert client.mechanical_actions(state, ()) == ()
    assert client._pending == pending
    assert client._patrol is not None
    assert rng.calls == 32


def test_no_walkable_sample_is_bounded_and_not_a_committed_leg():
    _, client, _, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    client.cache = MapCache((WalkMap("prt_fild08", 400, 400, bytes([1]) * 160000),))
    assert client._field_target(state) is None
    assert client._patrol is None
    assert rng.calls == 32


@pytest.mark.parametrize("interrupt", ["rest", "fight", "death"])
def test_script_interrupt_does_not_complete_patrol(interrupt):
    wire, client, _, rng = setup()
    state = client.build_native_state(Goal.GRIND)
    target = client._field_target(state)
    assert target is not None
    held = client._patrol
    wire.add(walk_ack(target, target))
    arrived = client.build_native_state(Goal.GRIND)
    actions: tuple[GameAction, ...] = (Rest(),) if interrupt == "rest" else (Attack(123),)
    if interrupt == "death":
        arrived = replace(arrived, alive=False)
        actions = ()
    assert client.mechanical_actions(arrived, actions) == actions
    assert client._patrol is held
    assert rng.calls == 32
