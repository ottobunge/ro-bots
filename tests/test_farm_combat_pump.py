"""Offline combat continues through blocked decisions, using received walk truth."""

import struct
import threading
import time
from dataclasses import replace

import pytest

from robots.adapters.native_gameplay import attack
from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import playing_runtime
from robots.app.agent_runtime import ScheduledAgent
from robots.app.farm_combat import COMBAT_INTENT_SECONDS
from robots.app.playing_runtime import PlayingClient
from robots.app.scripts import GrindScript, _melee_action
from robots.domain.actions import Attack, GameAction, MoveTo, Rest, Say
from robots.domain.model import Goal
from tests.test_brain import base_answers, make_brain
from tests.test_playing_runtime import Wire, entry_at, map_frame_at, monster, walk_ack


def _client(at: tuple[int, int] = (43, 37)) -> tuple[PlayingClient, Wire, list[float]]:
    now = [0.0]
    wire = Wire()
    wire.frames = []
    wire.add(entry_at(42, 37), map_frame_at(42, 37), monster(at=at))
    client = PlayingClient(
        wire,
        cache=MapCache(
            tuple(WalkMap(name, 100, 100, bytes(10000)) for name in ("prontera", "prt_fild08"))
        ),
        monotonic=lambda: now[0],
    )
    return client, wire, now


def _authorize(client: PlayingClient) -> GameAction:
    state = client.build_native_state(Goal.GRIND)
    action = _melee_action(state.nearby_monsters[0], state)
    client.authorize_farm_actions(state, (action,))
    client.perform_native(action)
    return action


def test_follow_up_swings_do_not_need_another_brain_tick_and_are_paced():
    client, wire, now = _client()
    assert _authorize(client) == Attack(123)
    for second in (0, 1, 2, 2, 3, 4):
        now[0] = float(second)
        client._pump_farm_combat()
    assert wire.sent == [attack(123)] * 3  # authored, +2s, +4s
    rows = client.drain_swing_telemetry()
    assert sum(row["event"] == "attack_authored" for row in rows) == 2
    assert all("weapon_worn" in row for row in rows if row["event"] == "swing")


def test_approach_waits_for_terminal_walk_truth_then_swings_without_decides():
    client, wire, now = _client(at=(47, 37))
    move = _authorize(client)
    assert isinstance(move, MoveTo)
    assert (move.x, move.y) == (46, 37)
    assert wire.sent == []
    # The server's projected endpoint is not a standing acknowledgement.
    wire.add(walk_ack((42, 37), (46, 37)))
    now[0] = 2.0
    client._pump_farm_combat()
    assert wire.sent == []
    assert client._attack_gate_reasons[-1][1] == "pending_walk"
    now[0] = 4.0
    wire.add(walk_ack((46, 37), (46, 37)))
    client._pump_farm_combat()
    assert wire.sent == [attack(123)]
    assert client._pending is None


def test_moved_target_uses_fresh_intercept_and_disappearance_ends_intent():
    client, wire, now = _client(at=(47, 37))
    _authorize(client)
    wire.add(walk_ack((46, 37), (46, 37)), monster(at=(49, 37)))
    now[0] = 2.0
    client._pump_farm_combat()
    rows = client.drain_swing_telemetry()
    approach = next(row for row in rows if row["event"] == "combat_approach")
    assert approach["destination"] == [48, 37]
    wire.add(struct.pack("<HIB", 0x0080, 123, 1))
    now[0] = 4.0
    client._pump_farm_combat()
    assert client.__dict__["_combat_intent"] is None
    assert wire.sent == []
    assert client.drain_swing_telemetry()[-1]["tap"] == "farm_target_not_visible"


@pytest.mark.parametrize(
    "boundary",
    [
        "expiry",
        "clock_reverse",
        "epoch",
        "map",
        "dead",
        "low_hp",
        "rest",
        "npc",
        "merchant",
        "disabled",
    ],
)
def test_intent_is_bounded_and_yields_to_runtime_priorities(boundary, monkeypatch):
    client, wire, now = _client()
    _authorize(client)
    sent = list(wire.sent)
    now[0] = 2.0
    if boundary == "expiry":
        now[0] = COMBAT_INTENT_SECONDS
    elif boundary == "clock_reverse":
        now[0] = -1.0
    elif boundary == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    elif boundary == "map":
        wire.add(struct.pack("<H16sHH", 0x0091, b"prt_fild08", 42, 37))
    elif boundary == "dead":
        wire.add(struct.pack("<HIB", 0x0080, wire.aid, 1))
    elif boundary == "low_hp":
        wire.status_params[5] = 20
    elif boundary == "rest":
        client._rest_seq = 1
    elif boundary == "npc":
        client._npc.cancel_uncertain = True
    elif boundary == "merchant":
        monkeypatch.setattr(client, "_merchant_owns_travel", lambda _state: True)
    else:
        client.mechanical_recovery_allowed = False
    client._pump_farm_combat()
    assert wire.sent == sent
    assert client.__dict__["_combat_intent"] is None


def test_chat_preserves_intent_but_unrelated_move_and_rest_revoke_it():
    client, _wire, _now = _client()
    _authorize(client)
    state = client.build_native_state(Goal.GRIND)
    client._combat_action_boundary(state, Say("hi"))
    assert client._combat_intent is not None
    client.perform_native(MoveTo(50, 50))
    assert client.__dict__["_combat_intent"] is None
    client.authorize_farm_actions(state, (Attack(123),))
    client.perform_native(Rest())
    assert client.__dict__["_combat_intent"] is None


def test_patrol_destination_does_not_authorize_a_target():
    client, _wire, _now = _client()
    state = client.build_native_state(Goal.GRIND)
    client.authorize_farm_actions(state, (MoveTo(50, 50),))
    assert client.__dict__["_combat_intent"] is None
    # Map/epoch authorization cannot survive into a different native context.
    client.authorize_farm_actions(replace(state, map_name="elsewhere"), (Attack(123),))
    _now[0] = 2.0
    client._pump_farm_combat()
    assert client.__dict__["_combat_intent"] is None


def test_host_and_pump_serialize_received_state_mutations():
    client, _wire, _now = _client()
    _authorize(client)
    lock = client.__dict__["_gameplay_lock"]
    entered = threading.Event()
    done = threading.Event()

    def pump():
        entered.set()
        client._pump_farm_combat()
        done.set()

    with lock:
        thread = threading.Thread(target=pump)
        thread.start()
        assert entered.wait(timeout=1)
        assert not done.is_set()
    thread.join(timeout=1)
    assert done.is_set()


def test_keepalive_pump_continues_target_while_host_is_blocked(monkeypatch):
    client, wire, _now = _client()
    client._now = time.monotonic
    monkeypatch.setattr(playing_runtime, "COMBAT_PUMP_INTERVAL_S", 0.02)
    _authorize(client)
    follow_up = threading.Event()

    def capture(frame: bytes) -> None:
        wire.sent.append(frame)
        follow_up.set()

    monkeypatch.setattr(wire, "_send", capture)
    # No tick, script step or decision runs while this host waits. The real
    # independent daemon must perform the next hit, not just a tested helper.
    monkeypatch.setattr(wire, "close", lambda: None, raising=False)
    client._keepalive()
    try:
        assert follow_up.wait(timeout=1.0)
        assert wire.sent == [attack(123)] * 2
    finally:
        client.close()
    assert client._keepalive_thread is None
    assert client._closed
    assert client.__dict__["_combat_intent"] is None


def test_out_of_range_authored_attack_names_range_gate():
    client, wire, _now = _client(at=(47, 37))
    client.perform_native(Attack(123))
    assert wire.sent == []
    refusal = client.drain_swing_telemetry()[-1]
    assert refusal["reason"] == "out_of_melee_range"
    assert refusal["tap"] == "attack_gate_out_of_melee_range"


def test_host_script_authorizes_target_and_ended_plan_revokes_it():
    client, _wire, _now = _client()
    state = client.build_native_state(Goal.GRIND)
    brain = make_brain(base_answers(), spawn_species=lambda _map: ("Poring",))
    brain.start(state)
    brain._plan = None
    brain._script = GrindScript(allow_roam=False)
    agent = ScheduledAgent.__new__(ScheduledAgent)
    agent.client = client
    agent.brain = brain
    actions = brain.step_script(state).actions
    assert actions == (Attack(123),)
    agent._script_actions(state, actions)
    assert client._combat_intent is not None
    brain._script = None  # Expired plan or a goal transition has no combat author.
    agent._script_actions(state, ())
    assert client.__dict__["_combat_intent"] is None


def test_host_attack_and_pump_share_the_two_second_swing_cadence():
    client, wire, now = _client()
    _authorize(client)
    now[0] = 2.0
    client._pump_farm_combat()
    now[0] = 2.1
    _authorize(client)
    assert wire.sent == [attack(123)] * 2
    refusal = client.drain_swing_telemetry()[-1]
    assert refusal["tap"] == "attack_gate_cooldown"


def test_daemon_does_not_wait_on_host_gameplay_lock():
    client, _wire, _now = _client()
    _authorize(client)
    finished = threading.Event()

    def daemon_beat():
        client._pump_farm_combat_safely()
        finished.set()

    with client.__dict__["_gameplay_lock"]:
        thread = threading.Thread(target=daemon_beat)
        thread.start()
        assert finished.wait(timeout=1.0)
    thread.join(timeout=1.0)
    assert not thread.is_alive()
