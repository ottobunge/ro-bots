"""LEG-87: consecutive starvation across decisions, through the native swing seam.

Offline contracts only; leg-86's receipt is the live baseline, not evidence
that the historical leg-34 injection is absent from today's source.
"""

import logging
import struct
from dataclasses import replace

import pytest

from robots.adapters.native_gameplay import attack
from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app.playing_runtime import PlayingClient
from robots.app.scripts import MELEE_RANGE, TARGET_WIDEN_STEPS, FarmScript
from robots.domain.actions import Attack, Loot, MoveTo
from robots.domain.events import Heartbeat, ItemDrop, PlanExpired
from robots.domain.model import ActorRef, Goal
from tests.conftest import make_state
from tests.test_brain import base_answers, make_brain
from tests.test_loot_priority import walk_ack
from tests.test_playing_runtime import Wire, entry_at, map_frame_at, monster
from tests.test_zc_item_entry_floor import zc_item_entry


def _answers(target: str = "Pupa") -> dict:
    answers = base_answers()
    answers["farm_target"]["choice"] = target
    return answers


def _farm(brain) -> FarmScript:
    script = brain.current_script()
    assert isinstance(script, FarmScript)
    return script


@pytest.mark.parametrize("steps_per_review", [1, 5, 19])
def test_twenty_starved_steps_widen_under_heartbeat_reauthoring(steps_per_review: int) -> None:
    brain = make_brain(_answers(), spawn_species=lambda _map: ("Pupa",))
    state = make_state(
        name=f"leg87-cadence-{steps_per_review}",
        nearby=(ActorRef(87, "Poring", "monster", 1.0, 120, 75),),
    )
    brain.start(state)
    for step in range(TARGET_WIDEN_STEPS):
        if step % steps_per_review == 0:
            previous = _farm(brain)
            brain.handle_event(state, Heartbeat(seq=step + 1))
            replacement = _farm(brain)
            assert replacement.plan.plan_id != previous.plan.plan_id
            assert replacement._starved == step
        actions = brain.step_script(state).actions
        if step < TARGET_WIDEN_STEPS - 1:
            assert len(actions) == 1
            assert isinstance(actions[0], MoveTo)
        else:
            assert actions == (Attack(87),)
    assert _farm(brain).plan.target_mobs == ("Pupa",)
    # Seeing the plan species honestly resets even an already widened script.
    preferred = replace(state, nearby=(ActorRef(88, "Pupa", "monster", 1.0, 120, 75),))
    assert brain.step_script(preferred).actions == (Attack(88),)
    brain.handle_event(state, Heartbeat(seq=99))
    assert _farm(brain)._starved == 0
    assert isinstance(brain.step_script(state).actions[0], MoveTo)


def test_reordered_target_set_keeps_the_nonzero_streak() -> None:
    species = ["Pupa", "Lunatic"]
    brain = make_brain(_answers("unknown"), spawn_species=lambda _map: tuple(species))
    state = make_state(nearby=())
    brain.start(state)
    for _ in range(7):
        brain.step_script(state)
    species.reverse()
    brain.handle_event(state, Heartbeat(seq=1))
    assert _farm(brain).plan.target_mobs == ("Lunatic", "Pupa")
    assert _farm(brain)._starved == 7


@pytest.mark.parametrize("change", ["species", "map", "leave_farming", "epoch", "expiry"])
@pytest.mark.parametrize("intervening_step", [False, True])
def test_returning_to_old_plan_cannot_resurrect_its_starvation(change, intervening_step) -> None:
    brain = make_brain(_answers(), spawn_species=lambda _map: ("Pupa", "Lunatic"))
    state = make_state(name=f"leg87-reset-{change}-{intervening_step}", nearby=())
    brain.start(state)
    for _ in range(TARGET_WIDEN_STEPS - 1):
        brain.step_script(state)
    assert _farm(brain)._starved == TARGET_WIDEN_STEPS - 1

    changed_state = state
    if change == "species":
        brain._run_review(state, _answers("Lunatic"), [])
    elif change == "expiry":
        brain.handle_event(state, PlanExpired(plan_id=_farm(brain).plan.plan_id))
    else:
        changed_states = {
            "map": replace(state, map_name="pay_fild04"),
            "leave_farming": replace(state, goal=Goal.SOCIAL),
            "epoch": replace(state, native_epoch=(state.native_epoch or 0) + 1),
        }
        changed_state = changed_states[change]
        brain.handle_event(changed_state, Heartbeat(seq=1))
    if intervening_step:
        brain.step_script(changed_state)
    # Epoch stays new: return to the same target/map in the new session.
    returned = replace(state, native_epoch=changed_state.native_epoch)
    brain.handle_event(returned, Heartbeat(seq=2))
    assert _farm(brain)._starved == int(change == "epoch" and intervening_step)
    other = replace(returned, nearby=(ActorRef(87, "Poring", "monster", 1.0, 120, 75),))
    assert isinstance(brain.step_script(other).actions[0], MoveTo)


@pytest.mark.parametrize("distance", [9, 14])
def test_widened_approach_reaches_adjacency_and_waits_for_walk_end(distance: int) -> None:
    wire = Wire()
    wire.frames = []
    wire.add(entry_at(42, 37), map_frame_at(42, 37), monster(at=(42 + distance, 37)))
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    client = PlayingClient(wire, cache=cache, monotonic=lambda: 0.0)
    brain = make_brain(_answers(), spawn_species=lambda _map: ("Pupa",))
    state = client.build_native_state(Goal.GRIND)
    brain.start(state)
    for step in range(TARGET_WIDEN_STEPS):
        brain.handle_event(state, Heartbeat(seq=step + 1))
        outcome = brain.step_script(state)
    move = outcome.actions[0]
    assert isinstance(move, MoveTo)
    assert (move.x, move.y) == (41 + distance, 37)
    # The runtime owns routing and can send only one route cell at a time.
    # Feed received arrivals back through fresh heartbeat-authored scripts.
    while state.x < move.x - 1:
        client.perform_native(move)
        sent_cell = wire.moves[-1]
        assert state.x < sent_cell[0] <= move.x
        wire.add(walk_ack(sent_cell, sent_cell))
        advanced = client.build_native_state(Goal.GRIND)
        assert advanced.x > state.x
        state = advanced
        brain.handle_event(state, Heartbeat(seq=50 + state.x))
        next_action = brain.step_script(state).actions[0]
        assert next_action == move
    client.perform_native(move)
    assert wire.moves[-1] == (move.x, move.y)
    pending = client._pending
    assert pending is not None

    wire.add(walk_ack((state.x, state.y), (move.x, move.y)))
    approaching = client.build_native_state(Goal.GRIND)
    assert max(abs(approaching.x - (42 + distance)), abs(approaching.y - 37)) == MELEE_RANGE
    brain.handle_event(approaching, Heartbeat(seq=99))
    swing = brain.step_script(approaching).actions
    assert swing == (Attack(123),)
    client.perform_native(swing[0])
    assert wire.sent == []
    assert client._attack_gate_reasons[-1][1] == "pending_walk"

    wire.add(walk_ack((move.x, move.y), (move.x, move.y)))
    client.drain_native_events()
    arrived = client.build_native_state(Goal.GRIND)
    assert client._pending is None
    brain.handle_event(arrived, Heartbeat(seq=100))
    assert brain.step_script(arrived).actions == swing
    client.perform_native(swing[0])
    assert wire.sent == [attack(123)]


@pytest.mark.parametrize("mechanical", [False, True])
def test_own_kill_drop_refusal_names_the_threat_precondition(caplog, mechanical) -> None:
    wire = Wire()
    wire.frames = []
    wire.add(entry_at(42, 37), map_frame_at(42, 37), monster(at=(43, 37)))
    client = PlayingClient(wire)
    client.perform_native(Attack(123))
    assert wire.sent == [attack(123)]
    # Offline own-attack -> target death -> drop sequence; another live
    # monster remains an active threat. Ownership is not inferred on wire.
    wire.add(
        struct.pack("<HIB", 0x0080, 123, 1),
        zc_item_entry(aid=321, item=909, x=43, y=37),
        monster(aid=555, at=(43, 38)),
    )
    assert any(isinstance(event, ItemDrop) for event in client.drain_native_events())
    state = client.build_native_state(Goal.GRIND)
    with caplog.at_level(logging.WARNING):
        if mechanical:
            assert client.mechanical_actions(state, ()) == ()
        else:
            client.perform_native(Loot())
    assert wire.sent == [attack(123)]
    assert "pickup deferred (threat) (fid=321 nearest=1)" in caplog.text
    assert 321 not in client._loot_pickup_tried
