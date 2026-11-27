"""Stop-and-swing: the attack fires only from a STANDING, true position.

The live probe proved the pinned server silently drops out-of-range swings
(no 0x0139 feedback). The tracked position updates only at walk-end, so an
attack fired mid-walk reads a phantom adjacency and is silently refused -
leg 19: 24 pooled attacks, zero exp. Leg-136 routed the refinement: the
attack gate still waits on COMBAT-owned holds (the approach walk the very
attack serves - the benign self-paced 4%), while a NON-COMBAT walk holding
the slot is released for the attack exactly as `_await_pending` releases on
no-progress, counting ``walk_displaced_for_combat(<origin>)``."""

from __future__ import annotations

from robots.app.combat_disengage import CombatDisengage
from robots.app.playing_runtime import ObservedMobDatabase, PlayingClient
from robots.domain.model import ActorRef, BotState
from tests.conftest import make_state


class _RecordingWire:
    char_name = "probe"

    def __init__(self) -> None:
        self.sent: list[object] = []

    def _send(self, frame: object) -> None:
        self.sent.append(frame)


def _runtime(
    pending: object, origin: str = "combat_approach"
) -> tuple[PlayingClient, _RecordingWire]:
    wire = _RecordingWire()
    runtime = PlayingClient.__new__(PlayingClient)  # the gate is the unit
    runtime.wire = wire
    runtime._now = lambda: 0.0
    runtime._pending = pending  # type: ignore[assignment]
    runtime._pending_origin = origin
    runtime._rest_seq = None
    runtime._disengage = CombatDisengage()
    runtime.mob_db = ObservedMobDatabase()
    runtime._attack_ready = lambda *_a, **_k: True  # type: ignore[method-assign]
    return runtime, wire


def _state() -> BotState:
    return make_state(nearby=(ActorRef(id=42, name="Poring", kind="monster", distance=1.0),))


def test_attack_suppressed_while_the_own_approach_walk_is_pending() -> None:
    """The approach walk the very attack serves keeps the slot (leg-136's
    benign self-paced pacing): the swing waits for its arrival handoff."""
    runtime, wire = _runtime(pending=((100, 100), 0, 0.0, 1), origin="combat_approach")
    state = _state()
    # the target stands in the state's nearby so the pre-gate passes; the
    # combat approach must suppress the send anyway
    runtime._attack(state, 42)
    assert wire.sent == []


def test_attack_releases_a_noncombat_walk_and_fires() -> None:
    """Leg-136: a NON-COMBAT walk holding the slot (field-route leg, trip
    leg, movement step) releases it for the authored attack - the gate is a
    release, not a refusal (96% of the pending_walk loss)."""
    runtime, wire = _runtime(pending=((100, 100), 0, 0.0, 1), origin="step")
    state = _state()
    runtime._attack(state, 42)
    assert len(wire.sent) == 1
    displacements = getattr(runtime, "_walk_displacement_reasons", ())
    assert [reason for _, reason in displacements] == ["step"]


def test_attack_fires_when_standing() -> None:
    runtime, wire = _runtime(pending=None)
    state = _state()
    runtime._attack(state, 42)
    assert len(wire.sent) == 1


def test_a_suppressed_attack_names_its_gate() -> None:
    """Leg 33: 516 approaches produced 6 swings and no telemetry could say
    why. Every suppressed attack records its drop reason on the client for
    the runner sample to lift into the receipt (`attack_gates`); leg-136
    adds the displacement counter for the holds the gate now releases."""
    runtime, wire = _runtime(pending=((100, 100), 0, 0.0, 1), origin="combat_approach")
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
