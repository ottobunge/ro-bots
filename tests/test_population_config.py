"""Population configuration must match requested groups and solo agents."""

import random

import pytest
from fastapi.testclient import TestClient

from robots.adapters.worldfeed_server import create_app
from robots.app.world_state import WorldState
from robots.society.memory import MemoryLog, StubSummarizer
from robots.society.society import SocietyRoster


def make_state() -> WorldState:
    return WorldState(SocietyRoster.build(random.Random(42), n_groups=3))


def test_api_generation_honors_independent_solo_count_and_fixed_group_size() -> None:
    state = make_state()
    with TestClient(create_app(state)) as client:
        response = client.post(
            "/commands",
            json={
                "type": "regenerate_roster",
                "seed": 17,
                "groups": 2,
                "solos": 3,
                "friends_min": 4,
                "friends_max": 4,
            },
        )
    assert response.status_code == 200, response.json()
    sizes = [len(group.member_ids) for group in state.roster.groups]
    assert sizes.count(1) == 3
    assert sizes.count(4) == 2
    assert len(state.roster.personas) == 2 * 4 + 3


@pytest.mark.parametrize(
    "patch",
    [
        {"groups": -1},
        {"solos": -1},
        {"groups": 0, "solos": 0},
        {"friends_min": 1},
        {"friends_max": 1},
    ],
)
def test_invalid_population_configuration_is_rejected_without_replacing_state(
    patch: dict[str, int],
) -> None:
    state = make_state()
    original = state.roster
    body: dict[str, object] = {"type": "regenerate_roster", "seed": 17, "groups": 2, "solos": 1}
    body.update(patch)
    with TestClient(create_app(state)) as client:
        response = client.post("/commands", json=body)
    assert response.status_code == 400
    assert state.roster is original


def test_regeneration_cannot_detach_host_bound_private_memory() -> None:
    state = make_state()
    persona_id = next(iter(state.roster.personas))
    memory = MemoryLog(StubSummarizer())
    state.bind_memory(persona_id, memory)
    roster = state.roster
    before = state.events
    with TestClient(create_app(state)) as client:
        response = client.post(
            "/commands",
            json={"type": "regenerate_roster", "seed": 17, "groups": 2, "solos": 1},
        )
    assert response.status_code == 400
    assert "host" in response.json()["detail"]
    assert state.roster is roster
    assert state._memories[persona_id] is memory
    assert state.events == before


def test_configured_groups_have_distinct_identity_even_when_labels_repeat() -> None:
    roster = SocietyRoster.build(random.Random(17), n_groups=70, group_size_max=2, solos=0)
    group_ids = [group.group_id for group in roster.groups]
    assert len(group_ids) == len(set(group_ids))


@pytest.mark.parametrize("counts", [(0, 3), (3, 0), (2, 2)])
def test_configured_population_boundary_counts_and_seed_are_reproducible(
    counts: tuple[int, int],
) -> None:
    groups, solos = counts
    state = make_state()
    body = {
        "type": "regenerate_roster",
        "seed": 17,
        "groups": groups,
        "solos": solos,
        "friends_min": 3,
        "friends_max": 5,
    }
    state.apply_command(body)
    first = state.roster
    sizes = [len(group.member_ids) for group in first.groups]
    assert sizes.count(1) == solos
    assert sum(size > 1 for size in sizes) == groups
    assert all(size == 1 or 3 <= size <= 5 for size in sizes)
    state.apply_command(body)
    assert [
        (group.group_id, group.member_ids, group.attitude, group.schedule.windows)
        for group in state.roster.groups
    ] == [
        (group.group_id, group.member_ids, group.attitude, group.schedule.windows)
        for group in first.groups
    ]
    assert state.roster.personas == first.personas
