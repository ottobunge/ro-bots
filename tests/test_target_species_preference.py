"""Leg-97: exp-less resource mobs are fallback targets, never a deadlock."""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from robots.app import scripts
from robots.app.playing_runtime import ObservedMobDatabase
from robots.app.scripts import TARGET_WIDEN_STEPS, FarmScript, GrindScript
from robots.app.trace_log import TraceLog
from robots.domain.actions import Attack, MoveTo
from robots.domain.events import MonsterSpotted
from robots.domain.farm import FarmPlan, MobInfo
from robots.domain.model import ActorRef
from tests.conftest import make_state
from tests.test_brain import base_answers, make_brain


@pytest.fixture(autouse=True)
def clear_commitment() -> Iterator[None]:
    scripts._KILL_COMMITMENTS.clear()
    yield
    scripts._KILL_COMMITMENTS.clear()


@pytest.fixture
def catalog(tmp_path: Path) -> ObservedMobDatabase:
    path = tmp_path / "mob.yml"
    path.write_text(
        "Body:\n"
        " - {Id: 1, Name: Green Plant, Level: 1}\n"
        " - {Id: 2, Name: Thief Bug Egg, Level: 4, BaseExp: 17, JobExp: 8}\n"
        " - {Id: 3, Name: Poring, Level: 1, BaseExp: 2, JobExp: 1}\n"
        " - {Id: 4, Name: Job Only, Level: 1, BaseExp: 0, JobExp: 4}\n"
        " - {Id: 5, Name: Purple Plant, Level: 1}\n"
        " - {Id: 6, Name: Shining Plant, Level: 1}\n"
        " - {Id: 7, Name: Mushroom, Level: 1}\n"
        " - {Id: 8, Name: Black Mushroom, Level: 1}\n"
        " - {Id: 9, Name: Future Resource, Level: 1, BaseExp: 0, JobExp: 0}\n"
        " - {Id: 10, Name: Drops, Level: 3, BaseExp: 2, JobExp: 1}\n"
    )
    return ObservedMobDatabase.load(path)


def actor(name: str, aid: int, distance: int = 1) -> ActorRef:
    return ActorRef(aid, name, "monster", float(distance), 120 + distance, 74)


def plan(*targets: str) -> FarmPlan:
    return FarmPlan(1, "prt_fild08", targets, 300, 42)


def script_for(kind: str, catalog: ObservedMobDatabase, *targets: str):
    if kind == "farm":
        return FarmScript(plan(*targets), mob_db=catalog)
    return GrindScript(mob_db=catalog)


def test_catalog_preserves_exp_and_yaml_zero_defaults(catalog):
    egg = catalog.by_name("Thief Bug Egg")
    plant = catalog.by_name("Green Plant")
    assert egg is not None
    assert plant is not None
    assert (egg.base_exp, egg.job_exp) == (17, 8)
    assert (plant.base_exp, plant.job_exp) == (0, 0)
    assert catalog.by_name("Uncatalogued") is None
    assert catalog.mobs_on_map("prt_fild08") == ()


@pytest.mark.parametrize("kind", ["farm", "grind"])
@pytest.mark.parametrize(
    "resource",
    [
        "Green Plant",
        "Purple Plant",
        "Shining Plant",
        "Mushroom",
        "Black Mushroom",
        "Future Resource",
    ],
)
def test_expless_melee_loses_to_distant_exp_species(kind, resource, catalog):
    script = script_for(kind, catalog, resource, "Thief Bug Egg")
    state = make_state(nearby=(actor(resource, 1), actor("Thief Bug Egg", 2, 5)))
    assert script.step(state).actions == (MoveTo(124, 74),)


@pytest.mark.parametrize("kind", ["farm", "grind"])
def test_rank_prefers_total_exp(kind, catalog):
    script = script_for(kind, catalog, "Poring", "Thief Bug Egg", "Job Only", "Unknown")
    state = make_state(
        nearby=(
            actor("Unknown", 8),
            actor("Poring", 3),
            actor("Job Only", 4),
            actor("Thief Bug Egg", 2),
        )
    )
    assert script.step(state).actions == (Attack(2),)


@pytest.mark.parametrize("kind", ["farm", "grind"])
def test_equal_rewards_keep_existing_hp_then_distance_preference(kind, catalog):
    script = script_for(kind, catalog, "Poring", "Drops")
    state = make_state(nearby=(actor("Drops", 10), actor("Poring", 3, 5)))
    assert script.step(state).actions == (MoveTo(124, 74),)
    nearer = make_state(nearby=(actor("Poring", 4, 5), actor("Poring", 3)))
    assert script.step(nearer).actions == (Attack(3),)


@pytest.mark.parametrize("kind", ["farm", "grind"])
def test_job_exp_alone_earns_preference(kind, catalog):
    script = script_for(kind, catalog, "Poring", "Job Only")
    state = make_state(nearby=(actor("Poring", 3), actor("Job Only", 4)))
    assert script.step(state).actions == (Attack(4),)


@pytest.mark.parametrize("kind", ["farm", "grind"])
def test_only_expless_visible_still_attacks(kind, catalog):
    script = script_for(kind, catalog, "Green Plant")
    state = make_state(nearby=(actor("Green Plant", 1),))
    assert script.step(state).actions == (Attack(1),)


@pytest.mark.parametrize("kind", ["farm", "grind"])
def test_unknown_species_allowed_without_bonus(kind, catalog):
    script = script_for(kind, catalog, "Unknown", "Green Plant")
    state = make_state(nearby=(actor("Green Plant", 1), actor("Unknown", 8)))
    assert script.step(state).actions == (Attack(8),)


@pytest.mark.parametrize("kind", ["farm", "grind"])
def test_missing_reward_data_is_unknown_without_bonus(kind):
    catalog = ObservedMobDatabase(
        (
            MobInfo(1, "Unknown", 1),
            MobInfo(2, "Poring", 1, base_exp=2, job_exp=1),
        )
    )
    script = script_for(kind, catalog, "Unknown", "Poring")
    state = make_state(nearby=(actor("Unknown", 1), actor("Poring", 2, 5)))
    assert script.step(state).actions == (MoveTo(124, 74),)


@pytest.mark.parametrize("kind", ["farm", "grind"])
def test_existing_actor_commitment_keeps_target(kind, catalog):
    script = script_for(kind, catalog, "Green Plant", "Thief Bug Egg")
    script.step(make_state(nearby=(actor("Green Plant", 1),)))
    state = make_state(nearby=(actor("Green Plant", 1), actor("Thief Bug Egg", 2)))
    assert script.step(state).actions == (Attack(1),)


def test_existing_plan_species_kept_and_only_plant_widens_without_deadlock(catalog):
    script = FarmScript(plan("Thief Bug Egg"), mob_db=catalog)
    plants = make_state(nearby=(actor("Green Plant", 1),))
    for _ in range(TARGET_WIDEN_STEPS - 1):
        assert isinstance(script.step(plants).actions[0], MoveTo)
    assert script.step(plants).actions == (Attack(1),)
    assert script._starved == TARGET_WIDEN_STEPS
    mixed = make_state(nearby=(*plants.nearby, actor("Thief Bug Egg", 2, 5)))
    assert script.step(mixed).actions == (MoveTo(124, 74),)
    assert script._starved == 0
    assert script.plan.target_mobs == ("Thief Bug Egg",)


def test_existing_expless_plan_keeps_species(catalog):
    script = FarmScript(plan("Green Plant"), mob_db=catalog)
    state = make_state(nearby=(actor("Green Plant", 1), actor("Thief Bug Egg", 2)))
    assert script.step(state).actions == (Attack(1),)
    assert script.plan.target_mobs == ("Green Plant",)


def test_new_brain_plan_overrides_expless_model_choice(catalog, tmp_path):
    catalog.observe("prt_fild08", (1, 2))
    answers = base_answers()
    answers["farm_target"]["choice"] = "Green Plant"
    trace = TraceLog(tmp_path / "traces", "species")
    brain = make_brain(answers, mob_db=catalog, trace=trace)
    state = make_state(nearby=(actor("Green Plant", 1), actor("Thief Bug Egg", 2, 5)))
    brain.start(state)
    assert brain.current_plan is not None
    assert brain.current_plan.target_mobs == ("Thief Bug Egg",)
    assert brain.step_script(state).actions == (MoveTo(124, 74),)
    trace.close()
    rows = [json.loads(line) for line in trace.path.read_text().splitlines()]
    skipped = [row for row in rows if row["kind"] == "target_species_skipped_expless"]
    assert skipped
    assert skipped[0]["species"] == "Green Plant"
    assert skipped[0]["reason"] == "zero_base_and_job_exp"
    assert skipped[0]["selected_species"] == "Thief Bug Egg"


def test_brain_authors_and_attacks_plant_only_view(catalog):
    catalog.observe("prt_fild08", (1,))
    brain = make_brain(base_answers(), mob_db=catalog)
    state = make_state(nearby=(actor("Green Plant", 1),))
    brain.start(state)
    assert brain.current_plan is not None
    assert brain.current_plan.target_mobs == ("Green Plant",)
    assert brain.step_script(state).actions == (Attack(1),)


def test_new_plan_ranks_exp_amount_before_model_choice(catalog):
    catalog.observe("prt_fild08", (2, 3))
    brain = make_brain(base_answers(), mob_db=catalog)
    brain.start(make_state(nearby=(actor("Poring", 3), actor("Thief Bug Egg", 2))))
    assert brain.current_plan is not None
    assert brain.current_plan.target_mobs == ("Thief Bug Egg",)


def test_monster_reaction_grind_uses_species_database(catalog):
    answers = base_answers()
    answers["react_monster"]["choice"] = "attack"
    brain = make_brain(answers, mob_db=catalog)
    state = make_state(nearby=(actor("Green Plant", 1), actor("Thief Bug Egg", 2)))
    brain.handle_event(state, MonsterSpotted(actor=actor("Green Plant", 1)))
    assert brain.step_script(state).actions == (Attack(2),)


def test_no_database_keeps_unknown_targets_attackable():
    state = make_state(nearby=(actor("Unknown", 8),))
    assert GrindScript().step(state).actions == (Attack(8),)


def test_brain_planless_grind_uses_species_database(catalog):
    brain = make_brain(base_answers(), mob_db=catalog)
    state = make_state(nearby=(actor("Green Plant", 1), actor("Thief Bug Egg", 2)))
    brain.start(state)
    assert brain.current_plan is None
    assert brain.step_script(state).actions == (Attack(2),)


@pytest.mark.parametrize("kind", ["farm", "grind"])
def test_script_species_skip_is_named_in_trace(kind, catalog, tmp_path):
    trace = TraceLog(tmp_path / "traces", "script-species")
    script = (
        FarmScript(plan("Green Plant", "Thief Bug Egg"), mob_db=catalog, trace=trace)
        if kind == "farm"
        else GrindScript(mob_db=catalog, trace=trace)
    )
    state = make_state(nearby=(actor("Green Plant", 1), actor("Thief Bug Egg", 2)))
    assert script.step(state).actions == (Attack(2),)
    row = json.loads(trace.path.read_text().splitlines()[0])
    assert row["kind"] == "target_species_skipped_expless"
    assert row["species"] == "Green Plant"
    assert row["reason"] == "zero_base_and_job_exp"
    assert row["selected_species"] == "Thief Bug Egg"
    # The previous attack now holds its actor; plants are no longer being
    # considered for a new pick and must not produce misleading skip rows.
    script.step(state)
    assert len(trace.path.read_text().splitlines()) == 1
    assert trace.dropped == 0
    trace.close()
