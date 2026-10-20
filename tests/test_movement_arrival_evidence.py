"""Offline movement smoke regressions; fake transport, never native game/SQL."""

import importlib.util
import struct
import sys
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import pytest

SPIKE = Path(__file__).resolve().parents[1] / "spikes" / "003-clientless-limbs"
sys.path.insert(0, str(SPIKE))
spec = importlib.util.spec_from_file_location("movement_harness", SPIKE / "test_limbs.py")
assert spec is not None
assert spec.loader is not None
limbs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(limbs)


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def walk_ack(start: tuple[int, int], end: tuple[int, int]) -> bytes:
    # Native WBUFPOS2: four packed 10-bit coordinates, then subcell 8/8.
    sx, sy = start
    tx, ty = end
    packed = (sx << 30) | (sy << 20) | (tx << 10) | ty
    return struct.pack("<HI", 0x0087, 123) + packed.to_bytes(5, "big") + b"\x88"


def test_fresh_zero_length_native_self_ack_proves_target():
    entry = (1.0, 0x0087, walk_ack((150, 151), (150, 151)))
    assert limbs.movement_arrival_evidence([entry], set(), (150, 151))


def test_announced_destination_without_self_ack_cannot_pass(monkeypatch):
    clock = Clock()
    peer = SimpleNamespace(actors={})
    sent: list[tuple[int, int]] = []

    def move(x: int, y: int) -> None:
        sent.append((x, y))
        peer.actors[11] = {"gid": 11, "x": x, "y": y, "from": (150, 150)}

    actor = SimpleNamespace(x=150, y=150, aid=11, raw_log=deque(), move=move)
    monkeypatch.setattr(limbs, "connect_pair", lambda *_: (actor, peer))
    budget = limbs.Budget(20, clock=clock.monotonic, sleep=clock.sleep)
    assert limbs.limb_move([], budget).startswith("FAIL")
    assert sent == [(150, 151), (150, 151)]
    assert clock.now <= 6


@pytest.mark.parametrize("target", [(0, 0), (1023, 1023), (0, 1023), (1023, 0), (255, 256)])
def test_native_bit_boundaries(target: tuple[int, int]):
    entry = (1.0, 0x0087, walk_ack(target, target))
    assert limbs.movement_arrival_evidence([entry], set(), target)


@pytest.mark.parametrize(
    ("start", "end"),
    [((150, 150), (150, 151)), ((150, 151), (150, 150)), ((151, 151), (151, 151))],
)
def test_start_and_end_must_both_equal_target(start, end):
    entry = (1.0, 0x0087, walk_ack(start, end))
    assert not limbs.movement_arrival_evidence([entry], set(), (150, 151))


def test_stale_matching_ack_and_unrelated_frames_are_not_arrival():
    stale = (1.0, 0x0087, walk_ack((150, 151), (150, 151)))
    other = (2.0, 0x09FD, stale[2])
    initial = (3.0, 0x0087, walk_ack((150, 150), (150, 151)))
    records = deque([stale, other, initial], maxlen=4)
    assert not limbs.movement_arrival_evidence(records, {id(stale)}, (150, 151))
    records.append((4.0, 0x0087, walk_ack((150, 151), (150, 151))))
    assert limbs.movement_arrival_evidence(records, {id(stale)}, (150, 151))


@pytest.mark.parametrize("corruption", ["short", "long", "header"])
def test_malformed_relevant_ack_fails_closed(corruption):
    raw = walk_ack((150, 151), (150, 151))
    if corruption == "short":
        raw = raw[:-1]
    elif corruption == "long":
        raw += b"\0"
    else:
        raw = b"\x88\0" + raw[2:]
    with pytest.raises(ValueError, match="malformed native"):
        limbs.movement_arrival_evidence([(1.0, 0x0087, raw)], set(), (150, 151))


@pytest.mark.parametrize(
    "case",
    ["fast", "delayed", "initial", "stale", "wrong-target", "peer-stream", "no-peer"],
)
def test_same_target_confirmation_is_once_and_bound_to_mover(monkeypatch, case):
    clock = Clock()
    peer = SimpleNamespace(actors={}, raw_log=deque())
    actor = SimpleNamespace(x=150, y=150, aid=11, raw_log=deque(maxlen=8))
    sent: list[tuple[int, int]] = []
    arrived = walk_ack((150, 151), (150, 151))

    def move(x: int, y: int) -> None:
        sent.append((x, y))
        if case != "no-peer":
            peer.actors[11] = {"gid": 11, "x": x, "y": y, "from": (150, 150)}
        if len(sent) == 1 or case == "fast":
            actor.raw_log.append((clock.now, 0x0087, arrived))
        elif case == "initial":
            # Even a cached self position equal to target is not native arrival.
            actor.x, actor.y = x, y
            actor.raw_log.append((clock.now, 0x0087, walk_ack((150, 150), (x, y))))
        elif case == "wrong-target":
            actor.raw_log.append((clock.now, 0x0087, walk_ack((151, 151), (151, 151))))
        elif case == "peer-stream":
            peer.raw_log.append((clock.now, 0x0087, arrived))

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        if case == "delayed" and len(sent) == 2 and clock.now >= 0.15:
            actor.raw_log.append((clock.now, 0x0087, arrived))

    actor.move = move
    monkeypatch.setattr(limbs, "connect_pair", lambda *_: (actor, peer))
    budget = limbs.Budget(20, clock=clock.monotonic, sleep=sleep)
    deadline = budget.deadline
    result = limbs.limb_move([], budget)
    assert result.startswith("OK") == (case in {"fast", "delayed"})
    assert sent == [(150, 151)] * (1 if case == "no-peer" else 2)
    assert budget.deadline == deadline
    assert clock.now <= 6


def test_confirmation_wait_obeys_remaining_overall_budget(monkeypatch):
    clock = Clock()
    peer = SimpleNamespace(actors={})
    actor = SimpleNamespace(x=150, y=150, aid=11, raw_log=deque())
    sent: list[tuple[int, int]] = []

    def move(x: int, y: int) -> None:
        sent.append((x, y))
        peer.actors[11] = {"gid": 11, "x": x, "y": y}

    actor.move = move
    monkeypatch.setattr(limbs, "connect_pair", lambda *_: (actor, peer))
    budget = limbs.Budget(0.1, clock=clock.monotonic, sleep=clock.sleep)
    with pytest.raises(TimeoutError, match="overall deadline"):
        limbs.limb_move([], budget)
    assert sent == [(150, 151), (150, 151)]
    assert clock.now == budget.deadline
