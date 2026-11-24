"""Empty-view farm roaming follows public spawn regions, never a live census."""

from dataclasses import replace
from pathlib import Path

import pytest

from robots.adapters import spawn_species as declarations
from robots.app.playing_runtime import PlayingClient
from robots.app.scripts import FarmScript
from robots.domain.actions import Attack, MoveTo, Rest
from robots.domain.model import ActorRef, Goal
from tests.test_farm_combat_pump import _client
from tests.test_farm_target_widening import _script, _state


def test_declared_clusters_ignore_mapwide_random_spawns_and_deduplicate(tmp_path):
    (tmp_path / "town.txt").write_text(
        "field,0,0\tmonster\tPoring\t1002,40\n"
        "field,30,40,5,5\tmonster\tPlant\t1080,5\n"
        "field,30,40\tmonster\tAnother\t1083,1\n"
        "field,90,80\twarp\tDoor\t1,1,town,1,1\n"
        "other,20,50\tmonster\tPoring\t1002,4\n"
    )
    assert declarations.spawn_cluster_index(tmp_path) == {
        "field": ((30, 40),),
        "other": ((20, 50),),
    }
    assert declarations.spawn_cluster_index(tmp_path / "absent") == {}


@pytest.mark.parametrize("location", ["field", "field,bad,20", "field,0,30", "field,-1,30"])
def test_invalid_or_random_declarations_are_not_cluster_coordinates(tmp_path, location):
    (tmp_path / "town.txt").write_text(f"{location}\tmonster\tPoring\t1002,40\n")
    assert declarations.spawn_cluster_index(tmp_path) == {}


def test_pay_fild04_cluster_knowledge_is_honest_about_random_plan_species():
    index = declarations.spawn_cluster_index(Path("rathena/npc/pre-re/mobs/fields"))
    assert index["pay_fild04"] == ((346, 335), (254, 193))


def test_runtime_exposes_nearest_reachable_map_cluster(monkeypatch):
    existing, wire, now = _client()
    client = PlayingClient(
        wire,
        cache=existing.cache,
        monotonic=lambda: now[0],
        spawn_clusters={"prontera": ((70, 37), (90, 37)), "other": ((50, 37),)},
    )
    assert client.build_native_state(Goal.GRIND).farm_roam_target == (70, 37)
    monkeypatch.setattr(client, "merchant_reachable", lambda _map, _pos, cell: cell != (70, 37))
    assert client.build_native_state(Goal.GRIND).farm_roam_target == (90, 37)
    monkeypatch.setattr(client, "merchant_reachable", lambda *_args: False)
    assert client.build_native_state(Goal.GRIND).farm_roam_target is None


def test_near_cluster_retains_local_roam_instead_of_parking():
    existing, wire, now = _client()
    client = PlayingClient(
        wire,
        cache=existing.cache,
        monotonic=lambda: now[0],
        spawn_clusters={"prontera": ((45, 37),)},
    )
    assert client.build_native_state(Goal.GRIND).farm_roam_target is None


def test_empty_farm_roam_heads_to_declared_cluster_beyond_old_jitter():
    script, _plan = _script()
    state = replace(_state([]), farm_roam_target=(254, 193))
    assert script.step(state).actions == (MoveTo(254, 193),)


def test_visible_target_keeps_priority_over_spawn_roam():
    script, plan = _script()
    target = ActorRef(123, "Poring", "monster", 1, 101, 100)
    state = replace(_state([target]), farm_roam_target=(254, 193))
    assert script.step(state).actions == (Attack(123),)
    assert FarmScript(plan).step(replace(state, hp=1)).actions == (Rest(),)
