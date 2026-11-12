"""Mechanical recovery policy; offline state fixtures, no model per tick."""

import json
from dataclasses import replace

import pytest

from robots.app.trace_log import TraceLog
from robots.domain.actions import Attack, Rest
from robots.domain.events import DamageTaken, Heartbeat, MonsterSpotted, PlanExpired
from robots.domain.farm import MobInfo
from robots.domain.npc import NpcDialogue
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


@pytest.mark.parametrize(("hp", "max_hp"), [(43, 86), (86, 86), (0, 0), (-1, 86)])
@pytest.mark.parametrize("has_sell_stock", [False, True])
def test_leg93_damage_rest_cannot_override_melee_break(state, hp, max_hp, has_sell_stock):
    """Leg 93: repeated damage reviews chose rest at 43/86 beside monsters."""
    answers = base_answers()
    answers["react_damage"] = {"choice": "rest"}
    brain = make_brain(answers)
    adjacent = replace(poring(), distance=1, x=226, y=179)
    seen = replace(
        state,
        name="YuffieFy81",
        job="Novice",
        base_level=10,
        map_name="pay_fild04",
        x=226,
        y=179,
        hp=hp,
        max_hp=max_hp,
        nearby=(adjacent,),
        inventory={"1201": 1} | ({"511": 1} if has_sell_stock else {}),
    )
    brain.start(seen)
    script = brain.current_script()
    for _ in range(3):
        reaction = brain.handle_event(seen, DamageTaken(167, adjacent.id))
        assert Rest() not in reaction.actions
        outcome = brain.step_script(seen)
        assert Rest() not in outcome.actions
        if hp > 0 and not has_sell_stock:
            assert outcome.actions == (Attack(adjacent.id),)
        elif hp <= 0:
            assert outcome.actions == ()  # Unknown HP authorizes neither rest nor combat.
    assert brain.current_script() is script


@pytest.mark.parametrize("hp", [1, 19])
def test_real_low_hp_still_rests_beside_attackable(state, hp):
    answers = base_answers()
    answers["react_damage"] = {"choice": "rest"}
    brain = make_brain(answers)
    hurt = replace(
        state, hp=hp, max_hp=86, nearby=(replace(poring(), distance=1, x=state.x, y=state.y),)
    )
    assert brain.handle_event(hurt, DamageTaken(5, 1)).actions == (Rest(),)
    assert brain.step_script(hurt).actions == (Rest(),)


def test_unknown_hp_holds_existing_recovery_without_rest_or_attack(state):
    brain = make_brain(base_answers())
    brain.step_script(replace(state, hp=1))
    assert brain.is_recovering
    assert brain.step_script(replace(state, hp=0, max_hp=0)).actions == ()
    assert brain.is_recovering


def test_one_hp_cannot_attack_even_without_prior_recovery(state):
    brain = make_brain(base_answers())
    seen = replace(
        state, hp=1, max_hp=1, nearby=(replace(poring(), distance=1, x=state.x, y=state.y),)
    )
    assert brain.step_script(seen).actions == (Rest(),)


def test_rest_break_names_hp_evidence_and_reason(state, tmp_path):
    trace = TraceLog(tmp_path, "rest-test")
    brain = make_brain(base_answers(), trace=trace)
    hurt = replace(state, hp=19, max_hp=86, nearby=())
    brain.step_script(hurt)
    recovered = replace(hurt, hp=43, nearby=(replace(poring(), distance=1, x=state.x, y=state.y),))
    assert brain.step_script(recovered).actions == (Attack(1),)
    rows = [json.loads(line) for line in (tmp_path / "rest-test.jsonl").read_text().splitlines()]
    breaks = [r for r in rows if r["kind"] == "rest_decision" and r["decision"] == "break"]
    assert len(breaks) == 1
    assert breaks[0]["reason"] == "attackable_in_range"
    assert breaks[0]["hp"] == 43
    assert breaks[0]["max_hp"] == 86
    assert breaks[0]["hp_ratio"] == 0.5


def test_unknown_hp_in_npc_recovery_does_not_mint_rest(state):
    brain = make_brain(base_answers())
    dialog = NpcDialogue(321, 1, state.map_name, 1, 1, "text")
    unknown = replace(state, hp=0, max_hp=0, npc_dialogue=dialog)
    assert brain.step_script(unknown).actions == ()


def test_received_death_cannot_mint_damage_reaction_rest(state):
    answers = base_answers()
    answers["react_damage"] = {"choice": "rest"}
    brain = make_brain(answers)
    dead = replace(state, hp=1, max_hp=86, alive=False)
    assert brain.handle_event(dead, DamageTaken(5, 1)).actions == ()
    assert brain.step_script(dead).actions == ()
    assert not brain.is_recovering
