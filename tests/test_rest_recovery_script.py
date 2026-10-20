"""Mechanical recovery policy; offline state fixtures, no model per tick."""

from dataclasses import replace

import pytest

from robots.domain.actions import Attack, Rest
from robots.domain.events import DamageTaken, Heartbeat, MonsterSpotted, PlanExpired
from robots.domain.farm import MobInfo
from tests.test_brain import FakeMobDB, base_answers, make_brain, poring


def test_recovery_keep_preserves_exact_suspended_farm_script_and_plan(state):
    answers = base_answers()
    answers["react_damage"] = {"choice": "rest"}
    answers["react_monster"] = {"choice": "attack"}
    brain = make_brain(answers, mob_db=FakeMobDB({"Poring": MobInfo(1002, "Poring", 1)}))
    state = replace(state, hp=19, max_hp=86, nearby=(poring(),))
    brain.start(state)
    script, plan = brain.current_script(), brain.current_plan
    brain.handle_event(state, DamageTaken(5, 1))
    brain.handle_event(state, MonsterSpotted(poring()))
    brain.handle_event(state, Heartbeat(1))
    assert brain.current_script() is script
    assert brain.current_plan is plan
    assert brain.step_script(replace(state, hp=22)).actions == (Rest(),)
    assert brain.step_script(replace(state, hp=65)).actions == (Attack(1),)
    assert brain.current_script() is script
    assert brain.current_plan is plan


def test_expired_suspended_farm_is_not_resurrected(state):
    answers = base_answers()
    answers["react_damage"] = {"choice": "rest"}
    brain = make_brain(answers, mob_db=FakeMobDB({"Poring": MobInfo(1002, "Poring", 1)}))
    brain.start(state)
    old = brain.current_script()
    brain.handle_event(state, DamageTaken(5, 1))
    plan = brain.current_plan
    assert plan is not None
    brain.handle_event(state, PlanExpired(plan.plan_id))
    brain.step_script(state)
    assert brain.current_plan is None
    assert brain.current_script() is not old


@pytest.mark.parametrize("ratio", [0, -1, 1.1, float("nan"), float("inf"), True])
def test_recovery_ratio_rejects_invalid_configuration(ratio):
    with pytest.raises(ValueError, match="recovery_hp_ratio"):
        make_brain(base_answers(), recovery_hp_ratio=ratio)


def test_configured_hysteresis_defers_new_goal_without_erasing_hold(state):
    answers = base_answers()
    answers["react_damage"] = {"choice": "rest"}
    brain = make_brain(answers, recovery_hp_ratio=0.6)
    hurt = replace(state, hp=19, max_hp=100, nearby=(poring(),))
    brain.start(hurt)
    brain.handle_event(hurt, DamageTaken(5, 1))
    assert brain.step_script(replace(hurt, hp=59)).actions == (Rest(),)
    assert brain.step_script(replace(hurt, hp=60), can_resume=False).actions == ()
    assert brain.is_recovering
    assert brain.required_recovery_hp_ratio == 0.6
    assert brain.step_script(replace(hurt, hp=60)).actions == (Attack(1),)
    assert not brain.is_recovering


def test_explicit_new_goal_updates_suspended_script_not_interrupt(state):
    first, rest, change = base_answers(), base_answers(), base_answers()
    rest["react_damage"] = {"choice": "rest"}
    change["change_goal"] = {"choice": "social"}
    brain = make_brain(queue=[first, rest, change])
    hurt = replace(state, hp=19, max_hp=100)
    brain.start(hurt)
    brain.handle_event(hurt, DamageTaken(5, 1))
    result = brain.handle_event(hurt, Heartbeat(1))
    assert any("->social" in note for note in result.notes)
    assert brain.is_recovering
    assert brain.step_script(hurt).actions == (Rest(),)
    assert type(brain.current_script()).__name__ == "IdleTownScript"
