"""The swing lease: displacement sticks until the authoring combat swings (leg-137).

Leg-137 proved displacement-as-instant-release churns: the released slot was
re-contested by non-combat re-authorship (9,090 window field authorships)
before the swing landed - pending_walk rose 1,427 -> 2,092 while the economy
only improved at the margin. The lease reuses the disengage-step lease shape
(``CombatDisengage``'s engage/bounded-until/reset): the displacement ARMS a
bounded reservation, non-combat re-authors back off while it is live, and the
swing (or the honest horizon timeout) releases it. Combat's own approach and
the survival retreat are never leased out of their slot; the script-performed
MoveTo revoke stays exactly as pinned (scripts own engagement).
"""

import struct
from dataclasses import replace
from types import SimpleNamespace

from robots.adapters.native_gameplay import attack
from robots.app.swing_lease import SWING_LEASE_HORIZON_S, SwingLease
from robots.domain.actions import MoveTo
from robots.domain.farm import FarmPlan, MobInfo
from robots.domain.model import Goal
from tests.test_combat_displacement import _arm, _displacements
from tests.test_farm_combat_pump import _client as _pump_client
from tests.test_playing_runtime import monster, walk_ack

LEASE_HOLDER = "combat_approach"


def _taps(client) -> list[str]:
    return [str(row.get("tap")) for row in client.drain_swing_telemetry()]


def _reason(client) -> str | None:
    reason = client.last_move_outcome.get("reason")
    return None if reason is None else str(reason)


def _contested_lease(at: tuple[int, int] = (46, 37)):
    """A minted combat interaction that displaced a script walk: the lease is
    live, the authoring script walk is the displaced class, and the arrival is
    still unconfirmed (the leg-137 contest shape). The mob stands adjacent to
    the walked-to cell, so the mint swings instead of approaching."""
    client, wire, now = _pump_client(at=at)
    _arm(client)
    client.perform_native(MoveTo(45, 37))  # a real script walk holds the slot
    wire.add(walk_ack((42, 37), (45, 37)))  # in flight: arrival unproven
    client.drain_native_events()  # the contested sighting mints THROUGH the hold
    assert _displacements(client) == ["step"], "the contest must displace first"
    return client, wire, now


def _approach_lease():
    """The out-of-melee contest: the mint dispatches the combat approach walk
    (combat_approach holds the slot) with the lease serving it."""
    client, wire, now = _contested_lease(at=(47, 37))  # distance 2: approach phase
    assert client._pending_origin == "combat_approach", "the approach owns the slot"
    return client, wire, now


# -- pure lease unit -------------------------------------------------------------

def test_lease_expires_honestly_by_the_bounded_horizon():
    lease = SwingLease()
    assert lease.expiry(now=0.0, intent=None, map_name="prontera", resting=False, dead=False) is None
    lease.arm("step", intent := object(), "prontera", 5.0)
    assert lease.expiry(
        now=5.0 + SWING_LEASE_HORIZON_S - 0.1, intent=intent,
        map_name="prontera", resting=False, dead=False,
    ) is None
    assert (
        lease.expiry(
            now=5.0 + SWING_LEASE_HORIZON_S + 0.1, intent=intent,
            map_name="prontera", resting=False, dead=False,
        )
        == "timeout"
    ), "the horizon, not hope, ends the reservation"
    lease.release()
    assert lease.origin() is None


def test_lease_expiry_names_each_release_cause():
    lease = SwingLease()
    lease.arm("step", intent := object(), "prontera", 0.0)
    assert lease.expiry(now=1.0, intent=intent, map_name="prontera", resting=False, dead=False) is None
    assert lease.expiry(now=1.0, intent=object(), map_name="prontera", resting=False, dead=False) == "intent"
    assert lease.expiry(now=1.0, intent=intent, map_name="geffen", resting=False, dead=False) == "map"
    assert lease.expiry(now=1.0, intent=intent, map_name="prontera", resting=True, dead=False) == "rest"
    assert lease.expiry(now=1.0, intent=intent, map_name="prontera", resting=False, dead=True) == "dead"


# -- the back-off: displaced re-authors are refused while the lease is live ------

def test_displaced_reauthor_backs_off_while_the_combat_is_live():
    client, _wire, _now = _approach_lease()
    state = client.build_native_state(Goal.GRIND)
    client._perform_move(state, (44, 37))  # the displaced walk re-authors
    assert client.last_move_outcome["outcome"] == "refused"
    assert (_reason(client) or "").startswith("swing_lease_hold(")
    assert client._pending_origin == "combat_approach", "the slot stayed combat-owned"
    assert any(row.get("event") == "swing_lease_backoff" for row in client.drain_swing_telemetry())


def test_backoff_refusal_counts_each_attempt_and_names_the_holder():
    client, _wire, _now = _approach_lease()
    state = client.build_native_state(Goal.GRIND)
    client._perform_move(state, (44, 37))
    client._perform_move(state, (44, 37))
    attempts = getattr(client, "_swing_lease_reasons", ())
    assert len(attempts) == 2
    assert attempts[-1][2] == LEASE_HOLDER, "the receipt deque names the serving class"


def test_field_route_reauthor_backs_off_with_its_own_class_named():
    """The goal-travel pump's leg (the leg-137 9,090 class) backs off too."""
    client, _wire, now = _approach_lease()
    client._pending = None  # the approach released (the no-progress lane)
    now[0] = 2.2
    client._field_pump_at = 0.0
    client._field_intent = SimpleNamespace(plan=SimpleNamespace(map_name="prontera"))  # type: ignore[assignment]
    client.field_travel_actions = lambda _state: (MoveTo(41, 37),)  # type: ignore[method-assign,assignment]
    client._pump_field_travel()
    assert (_reason(client) or "").startswith("swing_lease_hold(")
    attempts = getattr(client, "_swing_lease_reasons", ())
    assert attempts[-1][1] == "field_route", "the refusal names the backing-off class"
    assert client.__dict__.get("_combat_intent") is not None


# -- the release contract --------------------------------------------------------

def test_the_swing_releases_the_lease_and_travel_resumes_next_tick():
    client, wire, now = _contested_lease()  # adjacent mob, arrival unconfirmed
    state = client.build_native_state(Goal.GRIND)
    client._perform_move(state, (44, 37))
    assert (_reason(client) or "").startswith("swing_lease_hold(")
    wire.add(walk_ack((45, 37), (45, 37)))  # standing truth: adjacent + confirmed
    now[0] = 2.2  # the combat pump cadence
    client._pump_farm_combat()  # the swing limb performs
    assert attack(123) in wire.sent, "the authoring combat swings"
    assert any("swing_lease_release(swing)" in tap for tap in _taps(client))
    assert client._swing_lease_held(state) is None, "the swing ends the reservation"
    client._perform_move(state, (44, 37))
    assert client.last_move_outcome["outcome"] == "dispatched", "travel resumes next tick"
    assert wire.moves[-1] == (44, 37)


def test_lease_timeout_expires_honestly_and_travel_resumes():
    client, _wire, now = _contested_lease()
    now[0] = 0.2 + SWING_LEASE_HORIZON_S + 0.1
    state = client.build_native_state(Goal.GRIND)
    client._perform_move(state, (44, 37))
    assert client.last_move_outcome["outcome"] == "dispatched", "the horizon frees the slot"
    assert "swing_lease_release(timeout)" in _taps(client)


def test_intent_loss_releases_the_lease():
    client, _wire, _now = _contested_lease()
    state = client.build_native_state(Goal.GRIND)
    client.authorize_farm_sightings(state, None, remaining_s=0)  # the plan drops
    assert client.__dict__.get("_combat_intent") is None
    client._perform_move(state, (44, 37))
    assert client.last_move_outcome["outcome"] == "dispatched"
    assert "swing_lease_release(intent)" in _taps(client)


def test_map_change_releases_the_lease():
    client, _wire, _now = _contested_lease()
    state = client.build_native_state(Goal.GRIND)
    moved = replace(state, map_name="prt_fild08")
    client._perform_move(moved, (44, 37))
    assert client.last_move_outcome["outcome"] == "dispatched"
    assert "swing_lease_release(map)" in _taps(client)


def test_rest_releases_the_lease():
    client, _wire, _now = _contested_lease()
    client._rest_seq = 5
    state = client.build_native_state(Goal.GRIND)
    client._perform_move(state, (44, 37))
    assert client.last_move_outcome["outcome"] == "dispatched"
    assert "swing_lease_release(rest)" in _taps(client)


def test_the_scripts_performed_move_still_revokes_and_the_lease_follows():
    """The pinned script contract is untouched: a non-intercept performed
    MoveTo kills the intent, and the lease dies with it (by identity)."""
    client, _wire, _now = _contested_lease()
    client.perform_native(MoveTo(41, 37))  # not the melee intercept
    assert client.__dict__.get("_combat_intent") is None, "the script revoke stays pinned"
    assert client.last_move_outcome["outcome"] == "dispatched", "travel resumed"
    assert any("swing_lease_release(" in tap for tap in _taps(client))


# -- combat's own walks are never leased out --------------------------------------

def test_combat_approach_dispatches_freely_during_the_lease():
    client, _wire, _now = _approach_lease()
    state = client.build_native_state(Goal.GRIND)
    client._perform_move(state, (46, 37), origin="combat_approach")
    assert client.last_move_outcome["outcome"] in ("dispatched", "pending"), (
        "the approach must not be lease-blocked: " + str(client.last_move_outcome)
    )
    assert client._pending_origin == "combat_approach"


def test_the_real_intercept_leg_still_dispatches_tagged_combat_approach():
    client, _wire, now = _pump_client(at=(45, 37))  # the intercept is (44, 37)
    _arm(client)
    client.drain_native_events()  # mint + approach dispatch
    assert client._pending_origin == "combat_approach"
    client._pending = None  # the approach released; intent + lease live
    now[0] = 2.2
    client._field_pump_at = 0.0
    client._field_intent = SimpleNamespace(plan=SimpleNamespace(map_name="prontera"))  # type: ignore[assignment]
    client.field_travel_actions = lambda _state: (MoveTo(44, 37),)  # type: ignore[method-assign,assignment]
    client._pump_field_travel()
    assert client.last_move_outcome["outcome"] == "dispatched"
    assert _reason(client) == "combat_approach", "the intercept keeps its class"
    state = client.build_native_state(Goal.GRIND)
    assert client._swing_lease_held(state) is not None, (
        "serving the intercept never lifts the lease early"
    )


# -- a free-slot mint leases the slot too (the churn was the release windows) -----

def test_mint_with_a_free_slot_still_reserves_until_the_swing():
    client, _wire, _now = _pump_client(at=(46, 37))
    _arm(client)
    client.drain_native_events()  # the sighting mints with no displacement
    assert _displacements(client) == []
    state = client.build_native_state(Goal.GRIND)
    assert client._swing_lease_held(state) is not None, "the mint reserves the slot"
    client._perform_move(state, (44, 37))
    assert (_reason(client) or "").startswith("swing_lease_hold(")


def test_intent_object_identity_gates_the_reservation():
    """A replaced intent (a new engagement) never inherits the old lease."""
    client, wire, _now = _contested_lease()
    state = client.build_native_state(Goal.GRIND)
    client.mob_db.catalog[1003] = MobInfo(1003, "Drops", 1)
    spawn = bytearray(monster(kind=5, aid=124, at=(47, 37)))
    struct.pack_into("<H", spawn, 23, 1003)  # the species word names the Drops
    wire.add(bytes(spawn))
    state = client.build_native_state(Goal.GRIND)  # the second body is received
    plan = FarmPlan(2, state.map_name, ("Drops",), 900, 1)
    client.authorize_farm_sightings(state, plan, remaining_s=900)
    client._pump_farm_sightings(state)  # a fresh mint for the other target
    fresh = client.__dict__.get("_combat_intent")
    assert fresh is not None and fresh.target_id == 124
    assert client._swing_lease_held(state) is not None, "the fresh mint re-reserves"
