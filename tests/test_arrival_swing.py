"""Leg-124: received arrivals mint swings without a goal/decide step."""

import struct
import threading
import time

import pytest

from robots.adapters.native_gameplay import attack
from robots.app import playing_runtime
from robots.app.farm_combat import COMBAT_INTENT_SECONDS
from robots.app.scripts import _melee_action
from robots.domain.actions import MoveTo
from robots.domain.farm import FarmPlan, MobInfo
from robots.domain.model import Goal
from tests.test_city_field_travel import _brain
from tests.test_farm_combat_pump import _authorize, _client
from tests.test_playing_runtime import monster, walk_ack


@pytest.mark.parametrize("pump", ["drain", "keepalive"])
def test_terminal_arrival_mints_inside_combat_pump_interval(pump):
    client, wire, now = _client(at=(47, 37))
    assert isinstance(_authorize(client), MoveTo)
    intent = client._combat_intent
    wire.add(walk_ack((42, 37), (46, 37)))
    now[0] = 0.25
    client.drain_native_events()
    assert not wire.sent  # projected destination is still mid-walk
    wire.add(walk_ack((46, 37), (46, 37)))
    now[0] = 0.5
    if pump == "drain":
        client.drain_native_events()
    else:
        client._pump_farm_combat_safely()
    assert wire.sent == [attack(123)]
    assert client._pending is None
    assert client._combat_intent is intent
    assert intent is not None
    assert intent.until == COMBAT_INTENT_SECONDS
    rows = client.drain_swing_telemetry()
    assert any(row.get("tap") == "arrival_swing_minted" for row in rows)
    client.drain_native_events()
    client._pump_farm_combat_safely()
    assert wire.sent == [attack(123)]  # one handoff, ordinary swing cadence afterward


@pytest.mark.parametrize(
    ("boundary", "reason"),
    [
        ("gone", "target_not_visible"),
        ("moved", "out_of_melee_range"),
        ("unsafe", "no_survivability"),
        ("rest", "priority_yield"),
        ("expired", "intent_expired"),
        ("reverse", "invalid_clock"),
        ("cooldown", "cooldown"),
    ],
)
def test_arrival_rechecks_live_intent_and_names_deferral(boundary, reason):
    client, wire, now = _client(at=(47, 37))
    _authorize(client)
    now[0] = 0.5
    wire.add(walk_ack((46, 37), (46, 37)))
    if boundary == "gone":
        wire.add(struct.pack("<HIB", 0x80, 123, 1))
    elif boundary == "moved":
        wire.add(monster(at=(49, 37)))
    elif boundary == "unsafe":
        wire.status_params[5] = 35
    elif boundary == "rest":
        client._rest_seq = 1
    elif boundary == "expired":
        now[0] = COMBAT_INTENT_SECONDS
    elif boundary == "reverse":
        now[0] = -1
    else:
        client._farm_swing_at = 0.0
    client.drain_native_events()
    assert attack(123) not in wire.sent
    rows = client.drain_swing_telemetry()
    assert any(
        row.get("tap") == "arrival_swing_deferred" and row["reason"] == reason for row in rows
    )


def test_pending_timeout_cannot_mint_an_arrival_from_projected_position():
    client, wire, now = _client(at=(47, 37))
    _authorize(client)
    wire.add(walk_ack((42, 37), (46, 37)))
    client.drain_native_events()
    now[0] = 1.1
    client.drain_native_events()  # no-progress release is not proof of standing
    assert client._pending is None
    assert wire.sent == []
    assert not any(
        row.get("tap") == "arrival_swing_minted" for row in client.drain_swing_telemetry()
    )


def test_arrival_cooldown_deferral_resumes_on_next_paced_pump_without_renewal():
    client, wire, now = _client(at=(47, 37))
    _authorize(client)
    intent = client._combat_intent
    client._farm_swing_at = 0.0
    wire.add(walk_ack((46, 37), (46, 37)))
    now[0] = 0.5
    client.drain_native_events()
    assert wire.sent == []
    now[0] = 2.5
    client._pump_farm_combat_safely()
    assert wire.sent == [attack(123)]
    assert client._combat_intent is intent


@pytest.mark.parametrize("boundary", ["map", "epoch", "dead", "revoked"])
def test_arrival_cannot_resurrect_revoked_or_foreign_combat_authority(boundary):
    client, wire, now = _client(at=(47, 37))
    _authorize(client)
    wire.add(walk_ack((46, 37), (46, 37)))
    now[0] = 0.5
    if boundary == "map":
        wire.add(struct.pack("<H16sHH", 0x91, b"prt_fild08", 46, 37), monster(at=(47, 37)))
    elif boundary == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    elif boundary == "dead":
        wire.add(struct.pack("<HIB", 0x80, wire.aid, 1))
    else:
        client.perform_native(MoveTo(50, 50))
    client.drain_native_events()
    client._pump_farm_combat_safely()
    assert attack(123) not in wire.sent
    assert client._combat_intent is None


def test_field_pump_keeps_same_target_lease_and_converts_arrival():
    client, wire, now = _client(at=(47, 37))
    state = client.build_native_state(Goal.GRIND)
    planner = _brain()._field_travel
    assert planner is not None
    client.authorize_field_travel(state, (FarmPlan(1, "prt_fild08", ("Poring",), 900, 1), planner))
    client.mob_db.catalog[1002] = MobInfo(1002, "Poring", 1)
    wire.add(struct.pack("<H16sHH", 0x91, b"prt_fild08", 42, 37), monster(at=(47, 37)))
    client._pump_farm_combat_safely()
    intent = client._combat_intent
    assert intent is not None
    wire.add(walk_ack((42, 37), (46, 37)))
    now[0] = 2.0
    client._pump_farm_combat_safely()
    assert client._combat_intent is intent  # pump authoring cannot renew the deadline
    assert wire.sent == []
    wire.add(walk_ack((46, 37), (46, 37)))
    now[0] = 2.1
    client._pump_farm_combat_safely()
    assert wire.sent == [attack(123)]
    assert client._combat_intent is intent


def test_unrelated_walk_does_not_gain_arrival_attack_authority():
    client, wire, now = _client(at=(47, 37))
    state = client.build_native_state(Goal.GRIND)
    move = _melee_action(state.nearby_monsters[0], state)
    client.perform_native(move)  # no farm author, even though destination matches
    wire.add(walk_ack((46, 37), (46, 37)))
    now[0] = 0.5
    client.drain_native_events()
    assert wire.sent == []
    assert client._combat_intent is None


def test_independent_keepalive_thread_mints_arrival_while_host_waits(monkeypatch):
    client, wire, _now = _client(at=(47, 37))
    client._now = time.monotonic
    monkeypatch.setattr(playing_runtime, "COMBAT_PUMP_INTERVAL_S", 0.02)
    _authorize(client)
    wire.add(walk_ack((46, 37), (46, 37)))
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
