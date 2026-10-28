"""Stop-and-swing: the attack fires only from a STANDING, true position.

The live probe proved the pinned server silently drops out-of-range swings
(no 0x0139 feedback). The tracked position updates only at walk-end, so an
attack fired mid-walk reads a phantom adjacency and is silently refused -
leg 19: 24 pooled attacks, zero exp. The attack gate therefore requires the
pending walk to be finished (self._pending is None): the walk completes, the
tracked position becomes server-truth, and the next tick's evaluation swings
from the real adjacency."""

from __future__ import annotations

from robots.app.playing_runtime import PlayingClient
from robots.domain.model import ActorRef, BotState
from tests.conftest import make_state


class _RecordingWire:
    char_name = "probe"

    def __init__(self) -> None:
        self.sent: list[object] = []

    def _send(self, frame: object) -> None:
        self.sent.append(frame)


def _runtime(pending: object) -> tuple[PlayingClient, _RecordingWire]:
    wire = _RecordingWire()
    runtime = PlayingClient.__new__(PlayingClient)  # the gate is the unit
    runtime.wire = wire
    runtime._now = lambda: 0.0  # type: ignore[method-assign]
    runtime._pending = pending  # type: ignore[assignment]
    runtime._rest_seq = None
    runtime._attack_ready = lambda *_a, **_k: True  # type: ignore[method-assign]
    return runtime, wire


def _state() -> BotState:
    return make_state(nearby=(ActorRef(id=42, name="Poring", kind="monster", distance=1.0),))


def test_attack_suppressed_while_a_walk_is_pending() -> None:
    runtime, wire = _runtime(pending=((100, 100), 0, 0.0, 1))
    state = _state()
    # the target stands in the state's nearby so the pre-gate passes; the
    # pending walk must suppress the send anyway
    runtime._attack(state, 42)
    assert wire.sent == []


def test_attack_fires_when_standing() -> None:
    runtime, wire = _runtime(pending=None)
    state = _state()
    runtime._attack(state, 42)
    assert len(wire.sent) == 1


def test_a_suppressed_attack_names_its_gate() -> None:
    """Leg 33: 516 approaches produced 6 swings and no telemetry could say
    why. Every suppressed attack records its drop reason on the client for
    the runner sample to lift into the receipt (`attack_gates`)."""
    runtime, wire = _runtime(pending=((100, 100), 0, 0.0, 1))
    state = _state()
    runtime._attack(state, 42)
    reasons = {reason: 1 for _, reason in getattr(runtime, "_attack_gate_reasons", ())}
    assert reasons.get("pending_walk") == 1
    assert wire.sent == []


def test_an_invisible_target_names_the_visibility_gate() -> None:
    runtime, wire = _runtime(pending=None)
    state = make_state(nearby=())  # no monsters in view
    runtime._attack(state, 42)
    reasons = {reason: 1 for _, reason in getattr(runtime, "_attack_gate_reasons", ())}
    assert reasons.get("target_not_visible") == 1
    assert wire.sent == []
