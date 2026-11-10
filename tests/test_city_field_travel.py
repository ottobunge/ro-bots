"""LEG-88: a solo farmer leaves a spawn-empty city using local knowledge."""

from dataclasses import replace
from pathlib import Path

import pytest

from robots import playing
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.native_navigation import MapCache, WalkMap
from robots.adapters.spawn_species import spawn_species_index
from robots.app.brain import EventDrivenBrain
from robots.app.field_travel import FieldTravelPlanner
from robots.app.scripts import TARGET_WIDEN_STEPS, FarmScript
from robots.app.travel_routing import TravelRouter
from robots.domain.actions import Attack, MoveTo
from robots.domain.events import Heartbeat
from robots.domain.model import ActorRef, Goal
from robots.knowledge.queries import warp_edges
from tests.conftest import make_state
from tests.test_brain import base_answers, make_brain
from tests.test_llm_planning_host_construction import host_arguments
from tests.test_travel_route_brain_wiring import walled_prt_in


def _brain() -> EventDrivenBrain:
    answers = base_answers()
    answers["farm_target"]["choice"] = "Pupa"
    return make_brain(
        answers,
        spawn_species=lambda map_name: ("Pupa",) if map_name == "prt_fild08" else (),
        travel_resolver=lambda *_args: None,
        field_travel=FieldTravelPlanner(
            {"prt_fild08": ("Pupa",)},
            (("prontera", 156, 22, "south", "prt_fild08", 170, 375),),
            TravelRouter(MapCache(())),
        ),
    )


@pytest.mark.parametrize("goal", [Goal.GRIND, Goal.FARM_ITEM])
def test_empty_city_authors_a_destination_plan_and_walks_the_warp(goal):
    brain = _brain()
    state = make_state(map_name="prontera", goal=goal, nearby=())
    brain.start(state)
    script = brain.current_script()
    assert isinstance(script, FarmScript)
    assert script.plan.map_name == "prt_fild08"
    assert script.plan.target_mobs == ("Pupa",)
    assert brain.step_script(state).actions == (MoveTo(156, 22),)


def test_known_field_keeps_local_roam():
    brain = _brain()
    state = make_state(nearby=())
    brain.start(state)
    assert isinstance(brain.current_script(), FarmScript)
    move = brain.step_script(state).actions[0]
    assert isinstance(move, MoveTo)
    assert (move.x - state.x, move.y - state.y) in (
        (8, 0),
        (-8, 0),
        (0, 8),
        (0, -8),
        (5, 5),
        (-5, -5),
    )


def test_travel_preserves_destination_species_and_widen_streak_on_arrival():
    brain = _brain()
    field = make_state(nearby=())
    brain.start(field)
    for _ in range(TARGET_WIDEN_STEPS - 1):
        brain.step_script(field)
    city = replace(field, map_name="prontera")
    brain.handle_event(city, Heartbeat(seq=1))
    assert brain.step_script(city).actions == (MoveTo(156, 22),)
    script = brain.current_script()
    assert isinstance(script, FarmScript)
    assert script._starved == TARGET_WIDEN_STEPS - 1
    brain.handle_event(city, Heartbeat(seq=2))
    brain.handle_event(field, Heartbeat(seq=3))
    script = brain.current_script()
    assert isinstance(script, FarmScript)
    assert script.plan.target_mobs == ("Pupa",)
    assert script._starved == TARGET_WIDEN_STEPS - 1
    other = replace(field, nearby=(ActorRef(88, "Poring", "monster", 1.0, 120, 75),))
    assert brain.step_script(other).actions == (Attack(88),)


def test_arrival_farms_from_spawn_knowledge_without_waiting_for_a_review():
    brain = _brain()
    city = make_state(map_name="prontera", nearby=())
    brain.start(city)
    field = replace(city, map_name="prt_fild08")
    move = brain.step_script(field).actions[0]
    assert isinstance(move, MoveTo)
    assert max(abs(move.x - field.x), abs(move.y - field.y)) == 8 or (
        abs(move.x - field.x),
        abs(move.y - field.y),
    ) == (5, 5)
    script = brain.current_script()
    assert isinstance(script, FarmScript)
    assert script.plan.target_mobs == ("Pupa",)
    preferred = replace(field, nearby=(ActorRef(89, "Pupa", "monster", 1.0, 120, 75),))
    assert brain.step_script(preferred).actions == (Attack(89),)


def test_nearest_field_uses_total_route_cost_not_name_or_hop_count():
    planner = FieldTravelPlanner(
        {"a_far": ("Poring",), "z_near": ("Pupa",), "empty": ()},
        (
            ("town", 200, 200, "far", "a_far", 1, 1),
            ("town", 11, 10, "hop", "corridor", 5, 5),
            ("corridor", 6, 5, "near", "z_near", 20, 20),
            ("town", 10, 10, "empty", "empty", 1, 1),
            ("corridor", 5, 5, "cycle", "town", 10, 10),
        ),
        TravelRouter(MapCache(())),
    )
    assert planner.nearest("town", 10, 10) == "z_near"
    assert planner.route("town", 10, 10, "z_near") == (
        ("town", 11, 10),
        ("corridor", 6, 5),
        ("z_near", 20, 20),
    )
    assert planner.route("z_near", 20, 20, "z_near") == ()
    assert planner.nearest("unknown", 1, 1) is None


def test_disconnected_interior_uses_its_own_exit():
    planner = FieldTravelPlanner(
        {"prt_fild08": ("Pupa",)},
        (
            ("prt_in", 168, 124, "wrong_room", "prt_fild08", 1, 1),
            ("prt_in", 53, 105, "own_door", "prontera", 136, 186),
            ("prontera", 156, 22, "south", "prt_fild08", 170, 375),
        ),
        TravelRouter(walled_prt_in()),
    )
    assert planner.nearest("prt_in", 44, 102) == "prt_fild08"
    assert planner.route("prt_in", 44, 102, "prt_fild08")[0] == ("prt_in", 53, 105)
    assert planner.route("unknown", 299, 199, "prt_fild08") == ()


def test_real_local_spawn_and_warp_knowledge_releases_prontera():
    species = spawn_species_index(Path("rathena/npc/pre-re/mobs/fields"))
    assert not species.get("prontera")
    cache = MapCache.load(Path("rathena/db/map_cache.dat"), Path("rathena/db/pre-re/map_cache.dat"))
    planner = FieldTravelPlanner(species, warp_edges(), TravelRouter(cache))
    assert planner.nearest("prontera", 156, 100) == "prt_fild08"
    brain = make_brain(
        base_answers(), spawn_species=lambda name: species.get(name, ()), field_travel=planner
    )
    city = make_state(map_name="prontera", x=156, y=100, nearby=())
    result = brain.start(city)
    assert "travel: prontera->prt_fild08" in result.notes
    assert brain.step_script(city).actions == (MoveTo(156, 22),)
    script = brain.current_script()
    assert isinstance(script, FarmScript)
    assert "Poring" in script.plan.target_mobs


def test_missing_route_never_falls_back_to_city_roam():
    brain = _brain()
    brain._field_travel = FieldTravelPlanner({}, (), TravelRouter(MapCache(())))
    city = make_state(map_name="unknown_city", nearby=())
    brain.start(city)
    for _ in range(5):
        assert brain.step_script(city).actions == ()


def test_observed_monster_on_unknown_map_is_still_engaged():
    brain = _brain()
    city = make_state(map_name="prontera", nearby=(ActorRef(90, "Pupa", "monster", 1, 120, 75),))
    brain.start(city)
    assert brain.step_script(city).actions == (Attack(90),)


def test_actual_host_composition_injects_field_knowledge(tmp_path, monkeypatch):
    monkeypatch.setattr(
        playing, "make_private_decision", lambda _url: ScriptedDecisionModel(base_answers())
    )
    host = playing.build_host(playing.parse_args(host_arguments(tmp_path)))
    try:
        brain = host.agents["one"].brain
        assert isinstance(brain, EventDrivenBrain)
        assert isinstance(brain._field_travel, FieldTravelPlanner)
        city = make_state(map_name="prontera", x=156, y=100, nearby=())
        brain.start(city)
        assert brain.step_script(city).actions == (MoveTo(156, 22),)
        assert brain.current_plan is not None
        assert brain.current_plan.map_name == "prt_fild08"
    finally:
        host.stop()


def test_an_underway_destination_stays_stable_when_another_field_becomes_closer():
    species = {"prt_fild08": ("Pupa",), "other": ("Poring",)}
    planner = FieldTravelPlanner(
        species,
        (
            ("prontera", 10, 10, "south", "prt_fild08", 1, 1),
            ("prontera", 100, 10, "east", "other", 1, 1),
        ),
        TravelRouter(MapCache(())),
    )
    brain = make_brain(
        base_answers(), spawn_species=lambda name: species.get(name, ()), field_travel=planner
    )
    city = make_state(map_name="prontera", x=11, y=10, nearby=())
    brain.start(city)
    displaced = replace(city, x=99)
    assert planner.nearest(displaced.map_name, displaced.x, displaced.y) == "other"
    brain.handle_event(displaced, Heartbeat(seq=1))
    assert brain.current_plan is not None
    assert brain.current_plan.map_name == "prt_fild08"
    assert brain.current_plan.target_mobs == ("Pupa",)
    assert brain.step_script(displaced).actions == (MoveTo(10, 10),)


def test_a_disconnected_walkable_room_cannot_borrow_another_rooms_exit():
    cells = bytearray([1]) * 25
    cells[6] = cells[18] = 0
    planner = FieldTravelPlanner(
        {"field": ("Pupa",)},
        (("interior", 3, 3, "wrong_room", "field", 1, 1),),
        TravelRouter(MapCache((WalkMap("interior", 5, 5, bytes(cells)),))),
    )
    assert planner.nearest("interior", 1, 1) is None
    assert planner.route("interior", 1, 1, "field") == ()


def test_a_city_objective_cannot_replace_the_selected_field_with_the_empty_city(monkeypatch):
    brain = _brain()
    monkeypatch.setattr(brain, "_coordination_map", lambda: "prontera")
    city = make_state(map_name="prontera", nearby=())
    brain.start(city)
    assert brain.current_plan is not None
    assert brain.current_plan.map_name == "prt_fild08"
    assert brain.step_script(city).actions == (MoveTo(156, 22),)
