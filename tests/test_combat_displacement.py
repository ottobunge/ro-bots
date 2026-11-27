"""Combat authorship releases a NON-COMBAT-held pending walk slot (leg-136).

The leg-136 attribution proved 96.0% of the 1,427 ``pending_walk`` attack
gates sit behind NON-COMBAT movement walks (field-route legs 32.7%, phantom
trip legs 25.8%, movement holds 21.5%, contested roam holds 16.0%) while
combat's own approach pacing is only 4.0%. The fix shape (c): when combat
authorship arrives (authored Attack, sighting mint, pump swing, or the
combat approach dispatch) and the pending slot is held by a NON-COMBAT
walk, the slot releases exactly as ``_await_pending`` releases on
no-progress, noting ``walk_displaced_for_combat(<origin>)`` in trace +
receipt. Combat's own approach (and combat-survival retreat) walks are
NEVER displaced: the benign self-paced approach keeps its slot.
"""

from types import SimpleNamespace

import pytest

from robots.adapters.native_gameplay import attack
from robots.app.combat_disengage import CombatDisengage
from robots.app.farm_combat import COMBAT_INTENT_SECONDS, CombatIntent
from robots.app.playing_runtime import ObservedMobDatabase, PlayingClient
from robots.domain.actions import Attack, MoveTo
from robots.domain.farm import FarmPlan, MobInfo
from robots.domain.model import ActorRef, Goal
from tests.test_farm_combat_pump import _client as _pump_client
from tests.test_playing_runtime import Wire, walk_ack

#: Every NON-COMBAT dispatch origin the runtime assigns (playing_runtime
#: ``_pending_origin``): field-route legs, merchant trip legs and their
#: arrival probes, movement steps and direct sends, loot probes, stuck
#: recovery walks -- plus the field-route tag this slice adds.
NON_COMBAT_ORIGINS = [
    "step",
    "direct",
    "trip_leg",
    "trip_arrival_confirmation",
    "loot_arrival_confirmation",
    "escalated",
    "rerolled",
    "repositioned",
    "stuck_cell_detected",
    "stuck_cell_escalated",
    "field_route",
]

#: Combat-authored walks: the melee-intercept approach the combat pipeline
#: dispatched, and the combat-survival retreat step. Never displaced.
COMBAT_ORIGINS = ["combat_approach", "disengage_step"]


def _displacements(client: PlayingClient) -> list[str]:
    return [reason for _, reason in getattr(client, "_walk_displacement_reasons", ())]


def _taps(client: PlayingClient) -> list[str]:
    return [str(row.get("tap")) for row in client.drain_swing_telemetry()]


def _arm(
    client: PlayingClient, *, targets: tuple[str, ...] = ("Poring",), duration: float = 900
) -> FarmPlan:
    state = client.build_native_state(Goal.GRIND)
    client.mob_db.catalog[1002] = MobInfo(1002, "Poring", 1)
    plan = FarmPlan(1, state.map_name, targets, duration, 1)
    client.authorize_farm_sightings(state, plan, remaining_s=duration)
    return plan


# -- the rule: each origin class -------------------------------------------------


@pytest.mark.parametrize("origin", NON_COMBAT_ORIGINS)
def test_noncombat_hold_yields_to_the_authored_attack(origin):
    """Every non-combat dispatch origin releases the slot when an authored
    Attack arrives, and the attack proceeds through the freed gate."""
    client, wire, _now = _pump_client(at=(43, 37))  # the mob stands adjacent
    state = client.build_native_state(Goal.GRIND)
    client._pending_origin = origin
    client._pending = ((50, 37), 1, client._now(), 0)
    client._attack(state, 123)
    assert wire.sent == [attack(123)]
    assert _displacements(client) == [origin]
    assert f"walk_displaced_for_combat({origin})" in _taps(client)


@pytest.mark.parametrize("origin", COMBAT_ORIGINS)
def test_combat_walks_are_never_displaced(origin):
    """The combat approach and the survival retreat keep their slot: the
    attack it serves waits for them (the benign self-paced 4%)."""
    client, wire, _now = _pump_client(at=(43, 37))
    state = client.build_native_state(Goal.GRIND)
    client._pending_origin = origin
    client._pending = ((46, 37), 1, client._now(), 0)
    client._attack(state, 123)
    assert wire.sent == []
    assert client._pending is not None, "the combat walk must keep the slot"
    reasons = [reason for _, reason in getattr(client, "_attack_gate_reasons", ())]
    assert reasons[-1] == "pending_walk"
    assert _displacements(client) == []
    assert not any(
        str(row.get("event")) == "walk_displaced_for_combat"
        for row in client.drain_swing_telemetry()
    )


def test_free_slot_passes_through_without_displacement_notes():
    """A free slot needs no displacement: the authored attack simply fires
    and the counter stays silent (the gate is a release, not a toll)."""
    client, wire, _now = _pump_client(at=(43, 37))
    state = client.build_native_state(Goal.GRIND)
    client._attack(state, 123)
    assert wire.sent == [attack(123)]
    assert getattr(client, "_walk_displacement_reasons", None) is None
    assert not any("walk_displaced_for_combat" in tap for tap in _taps(client))


# -- the release contract ---------------------------------------------------------


def test_displacement_release_matches_the_no_progress_contract():
    """The release is `_await_pending`'s no-progress contract verbatim: the
    retention record rides the next perform, the walk epoch completes, the
    slot clears plain."""
    client, _wire, _now = _pump_client(at=(43, 37))
    client.perform_native(MoveTo(45, 37))  # a real script walk holds the slot
    assert client._pending is not None
    assert client._pending_origin == "step"
    client._stuck_walk_pending = True
    client._stuck_epochs = 2
    state = client.build_native_state(Goal.GRIND)
    client._attack(state, 123)
    assert client.__dict__["_pending"] is None
    assert not client.__dict__["_stuck_walk_pending"]
    assert client.__dict__["_stuck_epochs"] == 3, "_complete_walk_epoch ran like no-progress"
    release = client._move_pending_release
    assert release["pending_outcome"] == "pending-cancelled"
    assert release["pending_reason"] == "combat_displacement(step)"
    assert release["pending_target"] == (43, 37)
    client.perform_native(MoveTo(44, 37))
    assert client.last_move_outcome["pending_reason"] == "combat_displacement(step)"


# -- combat authorship tagging ------------------------------------------------------


def test_authored_melee_intercept_dispatches_as_combat_approach():
    """An authored approach continuation (the melee intercept of the live
    intent) dispatches tagged combat_approach -- never displaceable."""
    client, _wire, _now = _pump_client(at=(47, 37))
    _arm(client)
    client.drain_native_events()  # free slot: the mint approaches the intercept
    assert isinstance(client.__dict__.get("_combat_intent"), CombatIntent)
    assert client._pending_origin == "combat_approach"
    assert client._pending is not None


def test_script_move_without_a_live_intent_stays_step():
    """An ordinary script walk (no live combat intent surviving the boundary)
    dispatches with the movement origin: displaceable by later combat."""
    client, _wire, _now = _pump_client(at=(43, 37))
    client.perform_native(MoveTo(45, 37))
    assert client._pending_origin == "step"


def test_field_travel_dispatch_tags_field_route():
    """The goal-travel pump's legs (mechanism 1: re-aimed every 2 s) dispatch
    tagged field_route, so the counter names the leg-136 32.7% class."""
    client, _wire, now = _pump_client()
    client._field_pump_at = 0.0
    now[0] = 2.0  # the 2 s field-pump cadence
    client._field_intent = SimpleNamespace(plan=SimpleNamespace(map_name="prontera"))  # type: ignore[assignment]
    client.field_travel_actions = lambda _state: (MoveTo(50, 37),)  # type: ignore[method-assign,assignment]
    client._pump_field_travel()
    assert client._pending_origin == "field_route"
    assert client.last_move_outcome["reason"] == "field_route"
    assert any(row.get("tap") == "goal_field_routed" for row in client.drain_swing_telemetry())


def test_disengage_step_dispatches_as_combat_survival():
    """The retreat step the disengage owns dispatches combat-class: a swing
    never displaces the walk that is saving its own life."""
    client, wire, _now = _pump_client(at=(43, 37))
    client._disengage.source = lambda _state, _db, _now: (44, 37)  # type: ignore[method-assign,assignment]
    client._perform_disengage(client.build_native_state(Goal.GRIND))
    assert wire.moves, "the retreat step must be sent"
    assert client._pending_origin == "disengage_step"


# -- the mint seam ------------------------------------------------------------------


def test_mint_displaces_a_noncombat_hold_and_the_approach_owns_the_slot():
    """A contested sighting (mechanism 3: the roam/travel hold) mints through
    the displacement instead of deferring -- the approach dispatches tagged
    combat_approach and owns the slot."""
    client, wire, _now = _pump_client(at=(47, 37))
    _arm(client)
    client.perform_native(MoveTo(45, 37))  # a script walk contests the sighting
    wire.add(walk_ack((42, 37), (45, 37)))  # moving walkok: held, arrival unproven
    client.drain_native_events()  # the contested sighting mints THROUGH the hold
    assert client.__dict__.get("_combat_intent") is not None
    taps = client.drain_swing_telemetry()
    assert any(row.get("tap") == "walk_displaced_for_combat(step)" for row in taps)
    assert any(row.get("tap") == "farm_target_authored" for row in taps)
    assert client._pending_origin == "combat_approach"
    assert client._pending is not None
    assert wire.sent == []  # still out of range: the approach serves the lease


def test_mint_yields_to_the_combat_approach_hold():
    """A sighting mint never displaces the approach walk already serving an
    earlier lease of its own pipeline."""
    client, _wire, _now = _pump_client(at=(47, 37))
    _arm(client)
    client.drain_native_events()  # mint + approach dispatch (combat_approach)
    assert client._pending_origin == "combat_approach"
    state = client.build_native_state(Goal.GRIND)
    client.authorize_farm_sightings(state, None, remaining_s=0)  # drop authority
    client.__dict__["_combat_intent"] = None
    client._sighting_intent = None
    client.mob_db.catalog[1002] = MobInfo(1002, "Poring", 1)
    plan = FarmPlan(1, state.map_name, ("Poring",), 900, 1)
    client.authorize_farm_sightings(state, plan, remaining_s=900)
    client._pump_farm_sightings(state)
    assert client.__dict__.get("_combat_intent") is None, "own approach defers the mint"
    assert getattr(client, "_walk_displacement_reasons", None) is None
    assert client._pending_origin == "combat_approach"


# -- the swing seam -----------------------------------------------------------------


def _swing_fixture() -> tuple[PlayingClient, Wire, CombatIntent]:
    """A pump-minted sighting intent, an in-flight non-combat walk holding
    the slot, and the unconfirmed arrival of a far walkok."""
    runtime = PlayingClient.__new__(PlayingClient)  # the seam is the unit
    wire = Wire()
    runtime.wire = wire
    runtime._now = lambda: 0.0
    runtime._pending = ((50, 37), 1, 0.0, 0)
    runtime._pending_origin = "step"
    runtime._rest_seq = None
    runtime._disengage = CombatDisengage()
    runtime.mob_db = ObservedMobDatabase()
    runtime._attack_ready = lambda *_a, **_k: True  # type: ignore[method-assign]
    intent = CombatIntent(123, 1, "prontera", COMBAT_INTENT_SECONDS)
    runtime.__dict__["_sighting_intent"] = intent
    runtime._combat_intent = intent
    runtime._tracker = SimpleNamespace(view=SimpleNamespace(arrival_confirmed=False))  # type: ignore[assignment]
    runtime._farm_swing_at = float("-inf")
    runtime._arrival_intent = None
    return runtime, wire, intent


def test_swing_gate_displaces_the_hold_but_arrival_still_owns_the_swing():
    """The pump swing limb releases a non-combat hold (both limbs feed the
    same fix) and still refuses on the unconfirmed arrival -- the
    arrival_confirmed separation stays intact."""
    runtime, wire, intent = _swing_fixture()
    actor = ActorRef(id=123, name="Poring", kind="monster", distance=1.0)
    runtime._continue_farm_swing(intent, actor, Attack(123))
    assert wire.sent == [], "the unconfirmed arrival still refuses the swing"
    assert _displacements(runtime) == ["step"]
    reasons = [reason for _, reason in getattr(runtime, "_attack_gate_reasons", ())]
    assert reasons[-1] == "pending_walk"
    assert "walk_displaced_for_combat(step)" in _taps(runtime)


def test_swing_gate_yields_to_the_combat_approach_hold():
    """The pump swing limb never displaces the approach walk serving the very
    swing (the benign own-approach pacing)."""
    runtime, wire, intent = _swing_fixture()
    runtime._pending_origin = "combat_approach"
    actor = ActorRef(id=123, name="Poring", kind="monster", distance=1.0)
    runtime._continue_farm_swing(intent, actor, Attack(123))
    assert wire.sent == []
    assert _displacements(runtime) == []
    assert runtime._pending is not None


# -- the approach-dispatch seam -------------------------------------------------------


def test_combat_approach_dispatch_displaces_a_noncombat_hold():
    """The approach dispatch (the `_move_gate` await_pending seam) releases a
    non-combat hold instead of refusing await_pending -- the 213 blocked
    approaches behind non-combat walks unblock."""
    client, wire, _now = _pump_client(at=(43, 37))
    client.perform_native(MoveTo(45, 37))  # a script walk holds the slot
    assert client._pending is not None
    state = client.build_native_state(Goal.GRIND)
    client._perform_move(state, (46, 37), origin="combat_approach")
    assert _displacements(client) == ["step"]
    assert client._pending_origin == "combat_approach"
    assert client._pending is not None
    assert client._pending[0] == (43, 37)  # the one-step dispatch toward the target
    assert wire.moves == [(43, 37), (43, 37)]


def test_approach_dispatch_yields_to_the_own_approach_hold():
    """A second approach dispatch never displaces the first approach walk:
    it waits await_pending like today."""
    client, wire, _now = _pump_client(at=(43, 37))
    state = client.build_native_state(Goal.GRIND)
    client._perform_move(state, (46, 37), origin="combat_approach")
    assert client._pending_origin == "combat_approach"
    client._perform_move(state, (47, 37), origin="combat_approach")
    assert _displacements(client) == []
    assert client._pending is not None
    assert client._pending[0] == (43, 37)
    assert wire.moves == [(43, 37)]
    reasons = [reason for _, reason in getattr(client, "_move_gate_reasons", ())]
    assert reasons[-1] == "await_pending"


def test_script_dispatch_never_displaces():
    """Ordinary script walks keep queueing behind the held slot (the
    displacement authority is combat authorship only)."""
    client, wire, _now = _pump_client(at=(43, 37))
    client.perform_native(MoveTo(45, 37))
    held = client._pending
    client.perform_native(MoveTo(46, 37))
    assert client._pending is held, "the hold survives a script re-author"
    assert getattr(client, "_walk_displacement_reasons", None) is None
    assert wire.moves == [(43, 37)]


# -- counters shape ---------------------------------------------------------------------


def test_displacement_counter_names_each_origin_class():
    """The receipt counter (the deque the runner lifts) carries the origin
    class per event, like the other gate taps."""
    client, _wire, _now = _pump_client(at=(43, 37))
    state = client.build_native_state(Goal.GRIND)
    for origin in ("field_route", "trip_leg"):
        client._pending_origin = origin
        client._pending = ((50, 37), 1, client._now(), 0)
        client._attack(state, 123)
        client.drain_swing_telemetry()
    assert _displacements(client) == ["field_route", "trip_leg"]
