"""Cross-layer recovery replays: synthetic wire only, never native gameplay."""

import struct

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app.agent_runtime import ScheduledAgent
from robots.app.brain import EventDrivenBrain
from robots.app.playing_runtime import PlayingClient
from robots.app.timers import TimerSet
from robots.domain.actions import Attack, MoveTo, Rest
from robots.domain.model import ActorRef, BotState, Goal
from tests.test_agent_host import FakeClock, ScriptedDecisionModel, make_entry, make_roster
from tests.test_native_pose_recovery import PoseWire, pose, setup
from tests.test_playing_runtime import entry, map_frame, monster, walk_ack


def replay() -> tuple[
    PoseWire,
    PlayingClient,
    list[float],
    ScriptedDecisionModel,
    EventDrivenBrain,
    ScheduledAgent,
]:
    wire, client, now = setup()
    model = ScriptedDecisionModel(
        {
            "react_damage": {"choice": "rest"},
            "react_monster": {"choice": "attack"},
            "change_goal": {"choice": "keep"},
        }
    )
    brain = EventDrivenBrain(model, StaticChatGenerator())
    agent = ScheduledAgent(
        make_roster().personas["Doramir-01"],
        make_entry("Doramir-01"),
        brain=brain,
        client=client,
        tick_clock=FakeClock(),
        threaded=False,
    )
    return wire, client, now, model, brain, agent


def damage(wire: PoseWire) -> None:
    raw = bytearray(34)
    struct.pack_into("<HII", raw, 0, 0x08C8, 123, 999)
    struct.pack_into("<i", raw, 22, 5)
    wire.add(bytes(raw))


def test_damage_rest_suspends_same_and_next_tick_attack():
    wire, _, _, model, brain, agent = replay()
    wire.status_params[5] = 30  # Explicit REST above the script's 25% threshold.
    damage(wire)
    agent.tick()
    assert wire.sent
    assert set(wire.sent) == {"sit"}
    calls = model.calls
    wire.add(pose())
    agent.tick()
    assert set(wire.sent) == {"sit"}
    assert model.calls == calls
    assert brain.step_script(agent.build_state()).actions == (Rest(),)


def test_script_rest_latches_through_rebound_until_received_health_boundary():
    wire, _, _, _, brain, agent = replay()
    wire.status_params.update({5: 19, 6: 86})
    agent.tick()
    suspended = brain.current_script()
    wire.status_params[5] = 22
    agent.tick()
    assert all(item == "sit" for item in wire.sent)
    wire.status_params.update({5: 74, 6: 100})
    agent.tick()
    assert all(item == "sit" for item in wire.sent)
    wire.status_params[5] = 75
    agent.tick()
    assert wire.sent[-1] == "stand"
    # The latch has released at the received-health boundary; an in-range
    # attackable now engages the goal script (attack dispatch below).
    wire.add(monster(at=(42, 38)))
    wire.add(pose(kind=3))
    agent.tick()
    assert wire.sent[-1] == bytes.fromhex("37047b00000000")
    assert brain.current_script() is suspended


def test_recovery_waits_for_self_stand_and_low_health_resit_is_paced():
    wire, _, now, _, brain, agent = replay()
    wire.status_params[5] = 19
    damage(wire)
    agent.tick()
    wire.add(pose())
    agent.tick()
    assert wire.sent == ["sit"]
    wire.add(pose(kind=3))  # Damage forced stand is NOT health recovery.
    agent.tick()
    assert wire.sent == ["sit"]
    now[0] = 1.0
    agent.tick()
    assert wire.sent == ["sit", "sit"]
    wire.add(pose())
    wire.status_params[5] = 75
    agent.tick()
    assert wire.sent == ["sit", "sit", "stand"]
    assert brain.is_recovering
    wire.add(pose(123, 3))
    agent.tick()
    assert wire.sent[-1] == "stand"
    wire.add(monster(at=(42, 38)))  # in-range attackable engages the resumed script
    wire.add(pose(kind=3))
    agent.tick()
    assert wire.sent[-1] == bytes.fromhex("37047b00000000")
    assert not brain.is_recovering


def test_native_attack_requires_standing_for_eligible_live_target():
    wire, client, _ = setup()
    wire.add(pose())
    client.perform_native(Attack(321))
    assert not wire.sent  # Unseen target must not even request standing.
    client.perform_native(Attack(123))
    assert wire.sent == ["stand"]
    client.perform_native(Attack(123))
    assert wire.sent == ["stand"]
    wire.add(pose(kind=3))
    client.perform_native(Attack(123))
    assert wire.sent[-1] == bytes.fromhex("37047b00000000")


def test_attack_cannot_bypass_pending_movement_arrival():
    wire, client, now = setup()
    client.perform_native(MoveTo(43, 37))
    client.perform_native(Attack(123))
    assert not wire.sent
    wire.add(walk_ack((42, 37), (43, 37)))
    now[0] = 1.0
    client.perform_native(Attack(123))
    assert not wire.sent
    wire.add(walk_ack((43, 37), (43, 37)))
    # the stop-and-swing contract: the arrival release clears the pending
    # walk (the per-tick _await_pending does this in production) before the
    # attack fires - the mid-walk swings are silently dropped by the server
    # (the attack_fail_probe evidence)
    client._pending = None
    client.perform_native(Attack(123))
    assert wire.sent == [bytes.fromhex("37047b00000000")]


def test_explicit_flee_preempts_rest_until_received_escape_arrival():
    wire, _, _, model, brain, agent = replay()
    wire.status_params[5] = 19
    damage(wire)
    agent.tick()
    model._answers["react_damage"] = {"choice": "flee"}
    damage(wire)
    agent.tick()
    assert wire.moves == [(42, 38)]
    sent = list(wire.sent)
    agent.tick()
    assert wire.sent == sent
    assert brain.is_recovering
    for y in range(38, 42):
        wire.add(walk_ack((42, y), (42, y)))
        agent.tick()
    assert wire.moves == [(42, y) for y in range(38, 42)]
    assert wire.sent == sent  # Same clock: no sit flood after arrival.
    assert brain.is_recovering


def test_explicit_rest_at_high_health_still_requires_fresh_standing_receipt():
    wire, _, _, _, brain, agent = replay()
    wire.status_params[5] = 80
    damage(wire)
    agent.tick()
    assert wire.sent == ["sit", "stand"]
    assert brain.is_recovering
    wire.add(monster(at=(42, 38)))  # in-range attackable engages the resumed script
    wire.add(pose(kind=3))
    agent.tick()
    assert wire.sent[-1] == bytes.fromhex("37047b00000000")


def test_native_low_health_attack_during_rest_cannot_request_stand():
    wire, client, _ = setup()
    wire.status_params[5] = 19
    client.perform_native(Rest())
    wire.add(pose())
    client.perform_native(Attack(123))
    assert wire.sent == ["sit"]


def test_new_session_epoch_clears_old_brain_hold_and_native_pacing():
    wire, _, _, _, brain, agent = replay()
    wire.status_params[5] = 30
    damage(wire)
    agent.tick()
    wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    wire.frames = []
    wire.add(entry(), map_frame(), monster(at=(42, 38)))
    agent.tick()
    assert not brain.is_recovering
    assert wire.sent[-1] == bytes.fromhex("37047b00000000")


def test_close_denies_stale_actions_and_clears_recovery_timers(monkeypatch):
    wire, client, _ = setup()
    monkeypatch.setattr(wire, "close", lambda: None, raising=False)
    client.perform_native(Rest())
    client.close()
    with pytest.raises(NativeTelemetryUnavailable):
        client.perform_native(Attack(123))
    assert client._rest_at is None
    assert client._rest_seq is None
    assert client._pending is None


def test_received_sit_cancels_pending_intent_without_claiming_arrival():
    wire, client, _ = setup()
    client.perform_native(MoveTo(43, 37))
    wire.add(pose())
    state = client.build_native_state(Goal.GRIND)
    assert client._pending is None
    assert (state.x, state.y) == (42, 37)


def test_idle_recovery_drains_keepalives_without_tick_cognition(monkeypatch):
    wire, _, now, model, brain, agent = replay()
    pulses: list[float] = []
    monkeypatch.setattr(wire, "keepalive", lambda: pulses.append(now[0]), raising=False)
    wire.status_params[5] = 19
    damage(wire)
    agent.tick()
    wire.add(pose())
    calls = model.calls
    suspended = brain.current_script()
    for instant in range(1, 92):
        now[0] = float(instant)
        agent.tick()
    assert pulses == [20.0, 40.0, 60.0, 80.0]
    assert wire.sent == ["sit"]
    assert not wire.moves
    assert model.calls == calls
    assert brain.current_script() is suspended


def test_empty_standing_recovery_never_becomes_floor_loot_or_patrol():
    wire, _, _, _, brain, agent = replay()
    wire.status_params[5] = 19
    damage(wire)
    agent.tick()
    wire.add(pose(), struct.pack("<HIB", 0x0080, 123, 0))
    wire.add(struct.pack("<HIHHBhhBBh", 0x0ADD, 321, 501, 0, 1, 42, 37, 0, 0, 3) + bytes(3))
    wire.status_params[5] = 75
    agent.tick()
    agent.tick()
    assert wire.sent == ["sit", "stand"]
    assert not wire.moves
    assert brain.is_recovering


@pytest.mark.parametrize("ack", [pose(123, 3), pose(999, 3, 999), pose(999, 0)])
def test_attack_standing_retries_ignore_peer_and_nonpose_receipts(ack):
    wire, client, now = setup()
    wire.add(pose())
    client.perform_native(Attack(123))
    wire.add(ack)
    for instant in (0.5, 1.0, 2.0, 3.0, 100.0):
        now[0] = instant
        client.perform_native(Attack(123))
    # w65: the recovery re-arms a doubling epoch (never permanently silent),
    # so deep-time ticks keep retrying at a bounded rate (1 per epoch).
    assert wire.sent[:3] == ["stand"] * 3
    assert len(wire.sent) <= 8


@pytest.mark.parametrize("parameters", [{}, {5: 0, 6: 0}, {5: 19, 6: True}, {5: -1, 6: 100}])
def test_unknown_invalid_received_health_cannot_resume(parameters):
    wire, _, _, _, brain, agent = replay()
    wire.status_params[5] = 19
    damage(wire)
    agent.tick()
    sent = list(wire.sent)
    wire.status_params = parameters
    agent.tick()
    assert brain.is_recovering
    assert wire.sent == sent


def test_rest_flee_same_tick_does_not_resit_after_standing_escape_request():
    wire, _, _, model, brain, agent = replay()
    wire.status_params[5] = 19
    model._answers["react_monster"] = {"choice": "flee"}
    damage(wire)
    agent.tick()
    assert wire.moves == [(42, 38)]
    assert not wire.sent
    assert brain.is_recovering
    agent.tick()
    assert not wire.sent


def test_late_sit_receipt_cannot_reset_recovery_stand_budget():
    wire, _, now, _, brain, agent = replay()
    wire.status_params[5] = 80
    damage(wire)
    agent.tick()
    wire.add(pose())
    for instant in (1.0, 2.0, 3.0, 4.0):
        now[0] = instant
        agent.tick()
    assert wire.sent == ["sit", "stand", "stand", "stand"]
    assert brain.is_recovering


def test_rest_on_already_received_sitting_still_blocks_native_attack():
    wire, client, _ = setup()
    wire.status_params[5] = 19
    wire.add(pose())
    client.perform_native(Rest())
    client.perform_native(Attack(123))
    assert not wire.sent


def test_native_recovery_rechecks_received_health_not_standing_alone():
    wire, client, _ = setup()
    wire.status_params[5] = 19
    client.perform_native(Rest())
    wire.add(pose(kind=3))
    assert not client.recovery_ready()
    client.perform_native(Attack(123))
    assert wire.sent == ["sit"]


def test_pause_keeps_real_heartbeat_clock_event_calls_not_per_tick(monkeypatch):
    wire, _, now, model, brain, agent = replay()
    clock = FakeClock()
    agent._tick_clock = clock
    agent.timers = TimerSet(clock)
    agent.timers.add_periodic("idle_review", 30.0, 30.0)
    monkeypatch.setattr(wire, "keepalive", lambda: None, raising=False)
    wire.status_params[5] = 19
    damage(wire)
    agent.tick()
    wire.add(pose())
    calls = model.calls
    suspended = brain.current_script()
    for instant in range(1, 92):
        now[0] = clock.now = float(instant)
        agent.tick()
    assert model.calls == calls + 3
    assert brain.decision_count == model.calls
    assert agent.heartbeat_seq == 3
    assert brain.current_script() is suspended
    assert wire.sent == ["sit"]


def test_resurrection_does_not_authorize_attack_until_fresh_standing():
    wire, client, _ = setup()
    wire.add(struct.pack("<HIB", 0x0080, 999, 1), struct.pack("<HIH", 0x0148, 999, 0))
    client.perform_native(Attack(123))
    assert wire.sent == ["stand"]
    wire.add(pose(kind=3))
    client.perform_native(Attack(123))
    assert wire.sent[-1] == bytes.fromhex("37047b00000000")


# ---------------------------------------------------------- recovery latch rules
# Live findings (w34/w35 + run/reviews/rest-farm-balance.json): a dead agent's
# HP presents as 1 forever, so the recovery latch held and Rest() spammed while
# perform_native refused every send (2,387 rests vs 32 attacks in w35); and a
# hurt-but-able agent kept resting while an attackable stood in melee range.


def _recovery_state(hp: int, max_hp: int, *, alive: bool | None = True, monsters: tuple = ()):

    return BotState(
        name="Doramir-01",
        job="Novice",
        base_level=1,
        hp=hp,
        max_hp=max_hp,
        sp=10,
        max_sp=20,
        map_name="prt_fild08",
        x=167,
        y=352,
        goal=Goal.GRIND,
        in_party=False,
        nearby=monsters,
        inventory={},
        pending_invites=(),
        recent_chat=(),
        alive=alive,
    )


def _in_range_monster(gid: int = 110015577) -> ActorRef:
    return ActorRef(id=gid, name="monster#1002", kind="monster", distance=1.0, x=167, y=352)


def test_dead_received_stops_rest_dispatch():
    _wire, _, _, _, brain, _ = replay()
    brain._recovering = True
    state = _recovery_state(1, 86, alive=False)

    outcome = brain._step_recovery(state, can_resume=True)

    assert outcome is not None
    assert all(not isinstance(action, Rest) for action in outcome.actions)
    assert brain._recovering is False
    assert brain.is_recovering is False


def test_in_range_attackable_breaks_rest_above_rest_floor():
    _wire, _, _, _, brain, _ = replay()
    brain._recovering = True
    state = _recovery_state(30, 86, monsters=(_in_range_monster(),))
    assert state.hp_ratio >= 0.25

    outcome = brain._step_recovery(state, can_resume=True)

    assert outcome is None, "in-range attackable above the rest floor must hand the step back"
    assert brain._recovering is False


# ------------------------------------------------- staged-monster revision note
# The three pacing tests above previously staged an in-range monster to pin the
# old contract (rest ignores in-range monsters until the 75% boundary). Window
# 35 (run/reviews/playing-grind-operator-live-window35.json) superseded that
# contract: rest-dominance while an attackable stands in melee range starved
# the farm (2,387 rests vs 32 attacks, no kills), so the recovery latch now
# breaks at hp >= REST_BREAK_HP_FLOOR with an attackable in range
# (test_in_range_attackable_breaks_rest_above_rest_floor). The pacing tests
# stage no monster: they pin pure recovery pacing, which needs none.
