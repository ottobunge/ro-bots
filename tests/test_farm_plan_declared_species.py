"""Leg-125: declaration knowledge must not become an unseen-species lock."""

from dataclasses import replace
from pathlib import Path

import pytest

from robots import playing
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.spawn_species import spawn_species_index
from robots.app.brain import EventDrivenBrain
from robots.app.playing_runtime import ObservedMobDatabase
from robots.domain.actions import Attack, MoveTo
from robots.domain.farm import MobInfo
from robots.domain.model import ActorRef
from tests.conftest import make_state
from tests.test_brain import base_answers, make_brain
from tests.test_llm_planning_host_construction import host_arguments


@pytest.fixture(scope="module")
def field_knowledge():
    species = spawn_species_index(Path("rathena/npc/pre-re/mobs/fields"))
    catalog = ObservedMobDatabase.load(Path("rathena/db/pre-re/mob_db.yml"))
    return species, catalog


@pytest.fixture
def field_brain(field_knowledge):
    species, catalog = field_knowledge
    return make_brain(
        base_answers(), mob_db=catalog, spawn_species=lambda name: species.get(name, ())
    )


@pytest.mark.parametrize("name", ["Poring", "Lunatic", "Pupa", "Drops"])
@pytest.mark.parametrize("distance", [1, 5])
def test_empty_field_plan_engages_each_later_received_local_species(field_brain, name, distance):
    empty = make_state(name=f"leg125-{name}-{distance}", nearby=())
    field_brain.start(empty)
    plan = field_brain.current_plan
    assert plan is not None
    assert plan.map_name == "prt_fild08"
    assert name in plan.target_mobs
    received = replace(
        empty,
        nearby=(ActorRef(125, name, "monster", float(distance), empty.x + distance, empty.y),),
    )
    expected = Attack(125) if distance == 1 else MoveTo(empty.x + distance - 1, empty.y)
    assert field_brain.step_script(received).actions == (expected,)
    assert field_brain.current_plan is plan


def test_declared_rewards_rank_candidates_without_discarding_lower_exp(field_brain):
    field_brain.start(make_state(nearby=()))
    plan = field_brain.current_plan
    assert plan is not None
    assert plan.target_mobs[0] == "Lunatic"
    assert set(plan.target_mobs) == {"Poring", "Lunatic", "Pupa", "Drops"}


def test_pay_fild_plan_does_not_lock_on_rare_deviling(field_brain):
    empty = make_state(name="leg125-pay", map_name="pay_fild04", nearby=())
    field_brain.start(empty)
    plan = field_brain.current_plan
    assert plan is not None
    assert "Deviling" in plan.target_mobs
    assert "Poring" in plan.target_mobs
    assert "Green Plant" not in plan.target_mobs
    received = replace(empty, nearby=(ActorRef(125, "Poring", "monster", 1, empty.x + 1, empty.y),))
    assert field_brain.step_script(received).actions == (Attack(125),)


def test_declarations_never_import_other_map_species(field_brain):
    field_brain.start(make_state(nearby=()))
    plan = field_brain.current_plan
    assert plan is not None
    assert "Deviling" not in plan.target_mobs
    assert "Thief Bug" not in plan.target_mobs


def test_declared_plan_keeps_exp_preference_when_both_species_arrive(field_brain):
    empty = make_state(name="leg125-ranked", nearby=())
    field_brain.start(empty)
    received = replace(
        empty,
        nearby=(
            ActorRef(125, "Poring", "monster", 1, empty.x + 1, empty.y),
            ActorRef(126, "Lunatic", "monster", 5, empty.x + 5, empty.y),
        ),
    )
    assert field_brain.step_script(received).actions == (MoveTo(empty.x + 4, empty.y),)


@pytest.mark.parametrize("rewards", [(0, 0), (None, None)])
def test_resource_only_or_unknown_declarations_remain_viable(rewards):
    catalog = ObservedMobDatabase(
        (MobInfo(125, "Resource", 1, base_exp=rewards[0], job_exp=rewards[1]),)
    )
    brain = make_brain(base_answers(), mob_db=catalog, spawn_species=lambda _map: ("Resource",))
    empty = make_state(name=f"leg125-resource-{rewards}", nearby=())
    brain.start(empty)
    received = replace(
        empty, nearby=(ActorRef(125, "Resource", "monster", 1, empty.x + 1, empty.y),)
    )
    assert brain.step_script(received).actions == (Attack(125),)


def test_real_host_destination_plan_admits_common_mob_after_arrival(
    field_knowledge, tmp_path, monkeypatch
):
    _, catalog = field_knowledge
    monkeypatch.setattr(ObservedMobDatabase, "load", lambda _path: catalog)
    monkeypatch.setattr(
        playing, "make_private_decision", lambda _url: ScriptedDecisionModel(base_answers())
    )
    host = playing.build_host(playing.parse_args(host_arguments(tmp_path)))
    try:
        brain = host.agents["one"].brain
        assert isinstance(brain, EventDrivenBrain)
        city = make_state(name="leg125-host", map_name="prontera", x=156, y=100, nearby=())
        brain.start(city)
        plan = brain.current_plan
        assert plan is not None
        assert plan.map_name == "prt_fild08"
        arrived = replace(
            city, map_name="prt_fild08", nearby=(ActorRef(125, "Poring", "monster", 1, 157, 100),)
        )
        assert brain.step_script(arrived).actions == (Attack(125),)
        assert brain.current_plan is plan
    finally:
        host.stop()
