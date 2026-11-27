"""Plan sightings mint finite combat leases in the receive/pump budget."""

import struct
import threading
import time
from dataclasses import replace

import pytest

from robots.adapters.native_gameplay import attack
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app import playing_runtime
from robots.app.agent_runtime import ScheduledAgent
from robots.app.farm_combat import COMBAT_INTENT_SECONDS
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import MoveTo, Rest
from robots.domain.farm import FarmPlan, MobInfo
from robots.domain.model import Goal
from tests.test_brain import base_answers, make_brain
from tests.test_farm_combat_pump import _client
from tests.test_playing_runtime import monster, walk_ack


def _arm(
    client: PlayingClient, *, targets: tuple[str, ...] = ("Poring",), duration: float = 900
) -> FarmPlan:
    state = client.build_native_state(Goal.GRIND)
    client.mob_db.catalog[1002] = MobInfo(1002, "Poring", 1)
    plan = FarmPlan(1, state.map_name, targets, duration, 1)
    client.authorize_farm_sightings(state, plan, remaining_s=duration)
    return plan


@pytest.mark.parametrize("pump", ["drain", "keepalive"])
def test_sighting_swings_in_observation_budget_without_decide(pump):
    client, wire, _now = _client()
    _arm(client)
    if pump == "drain":
        events = client.drain_native_events()
        assert any(type(event).__name__ == "MonsterSpotted" for event in events)
    else:
        client._pump_farm_combat_safely()
    assert wire.sent == [attack(123)]
    intent = client.__dict__["_combat_intent"]
    assert intent is not None
    assert intent.until == COMBAT_INTENT_SECONDS
    assert any(row.get("tap") == "sighting_swing_minted" for row in client.drain_swing_telemetry())
    client.drain_native_events()
    client._pump_farm_combat_safely()
    assert wire.sent == [attack(123)]
    assert client._combat_intent is intent


@pytest.mark.parametrize("pump", ["drain", "keepalive"])
def test_roam_walk_sighting_displaces_the_hold_and_arrival_still_owns_swing(pump):
    """Leg-136: the contested roam hold releases at the mint (the tap names
    it) instead of parking the sighting; the approach dispatches as the
    combat approach and the swing still waits for its own arrival."""
    client, wire, now = _client(at=(47, 37))
    _arm(client)
    client.perform_native(MoveTo(45, 37))  # ordinary PLAN-ROAM, no combat author
    assert client._combat_intent is None
    wire.add(walk_ack((42, 37), (45, 37)))
    client.drain_native_events()
    intent = client.__dict__.get("_combat_intent")
    assert intent is not None
    assert intent.target_id == 123
    assert client._pending_origin == "combat_approach"
    assert client._pending is not None
    assert client._pending[0] == (46, 37)  # the lease approaches the intercept
    rows = client.drain_swing_telemetry()
    assert any(row.get("tap") == "walk_displaced_for_combat(step)" for row in rows)
    assert any(row.get("tap") == "sighting_swing_minted" for row in rows)
    assert wire.sent == []  # still two cells away: the approach serves the lease
    wire.add(walk_ack((46, 37), (46, 37)))
    now[0] = 0.5
    if pump == "drain":
        client.drain_native_events()
    else:
        client._pump_farm_combat_safely()
    assert wire.sent == [attack(123)]
    assert client._combat_intent is intent
    assert any(row.get("tap") == "arrival_swing_minted" for row in client.drain_swing_telemetry())


def test_displaced_hold_spends_the_sighting_lease_at_the_displacement():
    """Leg-136: a held sighting mints THROUGH the displacement with its full
    budget (named by the tap) instead of parking behind the walk; the spent
    lease still ends honestly at expiry."""
    client, wire, now = _client(at=(46, 37))
    client._keepalive_interval_s = 1000
    _arm(client)
    client.perform_native(MoveTo(45, 37))
    wire.add(walk_ack((42, 37), (45, 37)))
    client.drain_native_events()
    intent = client.__dict__.get("_combat_intent")
    assert intent is not None
    assert intent.until == COMBAT_INTENT_SECONDS  # fresh budget at the displacement
    rows = client.drain_swing_telemetry()
    assert any(row.get("tap") == "walk_displaced_for_combat(step)" for row in rows)
    assert wire.sent == []  # the arrival gate still owns the swing
    now[0] = COMBAT_INTENT_SECONDS + 1
    wire.add(walk_ack((45, 37), (45, 37)))
    client._pump_farm_combat_safely()
    assert client._combat_intent is None
    assert wire.sent == []


@pytest.mark.parametrize("boundary", ["vanished", "expired", "revoked", "species"])
def test_displaced_sighting_rechecks_live_authority_on_continuation(boundary):
    """The displacement-minted lease is a full lease: every continuation
    tick still rechecks the LIVE authority (vanish, plan expiry, revoke,
    species change) and ends it without a send."""
    client, wire, now = _client(at=(46, 37))
    _arm(client, duration=1)
    client.perform_native(MoveTo(45, 37))
    wire.add(walk_ack((42, 37), (45, 37)))
    client.drain_native_events()
    assert client.__dict__.get("_combat_intent") is not None
    if boundary == "vanished":
        wire.add(struct.pack("<HIB", 0x80, 123, 0))
    elif boundary == "expired":
        now[0] = 1.0
    elif boundary == "revoked":
        client.authorize_farm_sightings(client.build_native_state(Goal.GRIND), None, remaining_s=0)
    else:
        raw = bytearray(monster(at=(46, 37)))
        struct.pack_into("<H", raw, 23, 1063)
        client.mob_db.catalog[1063] = MobInfo(1063, "Lunatic", 1)
        wire.add(bytes(raw))
    wire.add(walk_ack((45, 37), (45, 37)))
    now[0] = 2.0  # the continuation cadence
    client._pump_farm_combat_safely()
    assert client._combat_intent is None
    assert wire.sent == []


def test_standing_sighting_approaches_then_arrival_swings():
    client, wire, now = _client(at=(47, 37))
    _arm(client)
    client.drain_native_events()
    assert client._pending is not None
    assert client._pending[0] == (43, 37)
    wire.add(walk_ack((46, 37), (46, 37)))
    now[0] = 0.1
    client.drain_native_events()
    assert wire.sent == [attack(123)]


@pytest.mark.parametrize("targets", [(), ("Lunatic",)])
def test_only_declared_plan_species_can_mint(targets):
    client, wire, _now = _client()
    _arm(client, targets=targets)
    client.drain_native_events()
    assert client._combat_intent is None
    assert wire.sent == []


@pytest.mark.parametrize(
    "boundary", ["merchant", "loot", "npc", "rest", "dead", "unsafe", "disabled"]
)
def test_sighting_yields_to_existing_priorities(boundary, monkeypatch):
    client, wire, _now = _client()
    _arm(client)
    if boundary == "merchant":
        monkeypatch.setattr(client, "_merchant_owns_travel", lambda _state: True)
    elif boundary == "loot":
        monkeypatch.setattr(client, "_pickup_outranks_trip", lambda _state: True)
    elif boundary == "npc":
        client._npc.cancel_uncertain = True
    elif boundary == "rest":
        client._rest_seq = 1
    elif boundary == "dead":
        wire.add(struct.pack("<HIB", 0x80, wire.aid, 1))
    elif boundary == "unsafe":
        wire.status_params[5] = 35
    else:
        client.mechanical_recovery_allowed = False
    client.drain_native_events()
    assert client._combat_intent is None
    assert attack(123) not in wire.sent
    assert any(
        row.get("tap") == "sighting_swing_deferred" for row in client.drain_swing_telemetry()
    )


@pytest.mark.parametrize("boundary", ["expiry", "reverse", "map", "epoch", "drop", "rest", "move"])
def test_sighting_cannot_resurrect_expired_or_revoked_lease(boundary):
    client, wire, now = _client()
    _arm(client)
    client.drain_native_events()
    sent = list(wire.sent)
    if boundary == "expiry":
        now[0] = COMBAT_INTENT_SECONDS
    elif boundary == "reverse":
        now[0] = -1
    elif boundary == "map":
        wire.add(struct.pack("<H16sHH", 0x91, b"prt_fild08", 42, 37), monster())
    elif boundary == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    elif boundary == "drop":
        client.authorize_farm_sightings(client.build_native_state(Goal.GRIND), None, remaining_s=0)
    elif boundary == "rest":
        client.perform_native(Rest())
    else:
        client.perform_native(MoveTo(50, 50))
    if boundary in ("reverse", "expiry"):
        # Reverse time fails the keepalive lane before the combat lane; the
        # independent pump must still expire the lease without sending.
        if boundary == "reverse":
            with pytest.raises(NativeTelemetryUnavailable):
                client.drain_native_events()
    else:
        client.drain_native_events()
    client._pump_farm_combat_safely()
    assert wire.sent.count(attack(123)) == sent.count(attack(123))
    assert client._combat_intent is None


def test_cooldown_keeps_sighting_lease_for_paced_pump():
    client, wire, now = _client()
    _arm(client)
    client._farm_swing_at = 0.0
    client.drain_native_events()
    intent = client.__dict__["_combat_intent"]
    assert intent is not None
    assert wire.sent == []
    assert any(
        row.get("tap") == "sighting_swing_deferred" and row["reason"] == "cooldown"
        for row in client.drain_swing_telemetry()
    )
    now[0] = 2.0
    client._pump_farm_combat_safely()
    assert wire.sent == [attack(123)]
    assert client._combat_intent is intent


def test_projected_roam_timeout_never_authorizes_midwalk_swing():
    client, wire, now = _client(at=(47, 37))
    _arm(client)
    client.perform_native(MoveTo(46, 37))
    wire.add(walk_ack((42, 37), (46, 37)))
    client.drain_native_events()
    now[0] = 2.0
    client._pump_farm_combat_safely()
    assert wire.sent == []


def test_plan_authority_is_bounded_and_sync_does_not_extend_it():
    client, wire, now = _client()
    plan = _arm(client, duration=1)
    now[0] = 1.0
    client.authorize_farm_sightings(client.build_native_state(Goal.GRIND), plan, remaining_s=1)
    client.drain_native_events()
    assert wire.sent == []
    assert client._combat_intent is None


def test_wrong_map_plan_does_not_mint():
    client, wire, _now = _client()
    plan = _arm(client)
    state = client.build_native_state(Goal.GRIND)
    client.authorize_farm_sightings(state, replace(plan, map_name="prt_fild08"), remaining_s=900)
    client.drain_native_events()
    assert wire.sent == []


def test_host_sync_binds_and_revokes_current_plan():
    client, wire, _now = _client()
    state = client.build_native_state(Goal.GRIND)
    client.mob_db.catalog[1002] = MobInfo(1002, "Poring", 1)
    brain = make_brain(base_answers(), spawn_species=lambda _map: ("Poring",))
    brain.start(state)
    agent = ScheduledAgent.__new__(ScheduledAgent)
    agent.client, agent.brain = client, brain
    agent._sync_farm_travel(state)
    client.drain_native_events()
    assert wire.sent == [attack(123)]
    brain._plan = None
    agent._sync_farm_travel(state)
    assert client._combat_intent is None


def test_live_species_change_revokes_sighting_target():
    client, wire, now = _client()
    _arm(client)
    client.drain_native_events()
    wire_frame = bytearray(monster(at=(43, 37)))
    struct.pack_into("<H", wire_frame, 23, 1063)
    client.mob_db.catalog[1063] = MobInfo(1063, "Lunatic", 1)
    wire.add(bytes(wire_frame))
    now[0] = 2.0
    client._pump_farm_combat_safely()
    assert wire.sent == [attack(123)]
    assert client._combat_intent is None


def test_plan_expiry_ends_existing_sighting_lease():
    client, wire, now = _client()
    _arm(client, duration=1)
    client.drain_native_events()
    now[0] = 2.0
    client._pump_farm_combat_safely()
    assert wire.sent == [attack(123)]
    assert client._combat_intent is None


def test_pump_sighting_does_not_consume_host_monster_event():
    client, wire, _now = _client()
    _arm(client)
    client._pump_farm_combat_safely()
    events = client.drain_native_events()
    assert any(type(event).__name__ == "MonsterSpotted" for event in events)
    assert wire.sent == [attack(123)]


def test_independent_keepalive_converts_first_sighting_without_host_tick(monkeypatch):
    client, wire, _now = _client()
    client._now = time.monotonic
    _arm(client)
    monkeypatch.setattr(playing_runtime, "COMBAT_PUMP_INTERVAL_S", 0.02)
    swung = threading.Event()

    def capture(frame):
        wire.sent.append(frame)
        swung.set()

    monkeypatch.setattr(wire, "_send", capture)
    monkeypatch.setattr(wire, "close", lambda: None, raising=False)
    client._keepalive()
    try:
        assert swung.wait(timeout=1.0)
        assert wire.sent == [attack(123)]
    finally:
        client.close()
    assert client._farm_sightings is None


def test_shared_intercepts_do_not_make_plan_sighting_ambiguous():
    client, wire, _now = _client()
    _arm(client)
    wire.add(monster(aid=124, at=(43, 37)))
    client.drain_native_events()
    assert wire.sent == [attack(123)]


def test_sighting_disappearance_names_deferral_and_ends_lease():
    client, wire, now = _client()
    _arm(client)
    client.drain_native_events()
    wire.add(struct.pack("<HIB", 0x80, 123, 1))
    now[0] = 2.0
    client._pump_farm_combat_safely()
    assert wire.sent == [attack(123)]
    assert client._combat_intent is None
    assert any(
        row.get("tap") == "sighting_swing_deferred" and row["reason"] == "target_not_visible"
        for row in client.drain_swing_telemetry()
    )


def test_failed_sighting_pump_releases_plan_authority(monkeypatch):
    client, _wire, _now = _client()
    _arm(client)

    def fail(*_args):
        message = "offline test send failure"
        raise OSError(message)

    monkeypatch.setattr(client, "_continue_farm_target", fail)
    client._pump_farm_combat_safely()
    assert client._combat_intent is None
    assert client._farm_sightings is None


@pytest.mark.parametrize("boundary", ["expired", "recovery"])
def test_host_revokes_spent_or_recovering_plan(boundary):
    client, wire, _now = _client()
    state = client.build_native_state(Goal.GRIND)
    client.mob_db.catalog[1002] = MobInfo(1002, "Poring", 1)
    brain = make_brain(base_answers(), spawn_species=lambda _map: ("Poring",))
    brain.start(state)
    agent = ScheduledAgent.__new__(ScheduledAgent)
    agent.client, agent.brain = client, brain
    agent._sync_farm_travel(state)
    client.drain_native_events()
    assert wire.sent == [attack(123)]
    if boundary == "expired":
        brain._plan_chat_deadline = 0
    else:
        brain._recovering = True
    agent._sync_farm_travel(state)
    assert client._combat_intent is None
    assert client._farm_sightings is None
