"""Authoritative offline population admission; never allocate rejected shapes."""

import hashlib
import random

import pytest
from fastapi.testclient import TestClient

from robots.adapters.worldfeed_server import create_app
from robots.app.world_state import CommandError, WorldState
from robots.society.society import SocietyRoster


def forbidden(*args, **kwargs):
    msg = "rejected population reached generation/allocation"
    raise AssertionError(msg)


def test_factory_rejects_worst_case_population_before_generation(monkeypatch) -> None:
    rng = random.Random(42)
    before = rng.getstate()
    monkeypatch.setattr(rng, "randint", forbidden)
    monkeypatch.setattr(rng, "choice", forbidden)
    monkeypatch.setattr(rng, "random", forbidden)
    monkeypatch.setattr("robots.society.society.SocietyPersona", forbidden)
    monkeypatch.setattr("robots.society.society.FriendGroup", forbidden)
    monkeypatch.setattr("robots.society.society.SocialGraph", forbidden)
    with pytest.raises(ValueError, match="4096"):
        SocietyRoster.build(rng, n_groups=257, group_size_max=16, solos=0)
    assert rng.getstate() == before


@pytest.mark.parametrize("solos", [0, 1])
def test_factory_rejects_friend_ceiling_even_for_all_solos(monkeypatch, solos) -> None:
    rng = random.Random(42)
    monkeypatch.setattr(rng, "randint", forbidden)
    monkeypatch.setattr("robots.society.society.SocialGraph", forbidden)
    with pytest.raises(ValueError, match="16"):
        SocietyRoster.build(rng, n_groups=1, group_size_max=17, solos=solos)


@pytest.mark.parametrize(
    ("patch", "error"),
    [
        ({"n_groups": True}, TypeError),
        ({"n_groups": 1.0}, TypeError),
        ({"n_groups": "1"}, TypeError),
        ({"n_groups": -1}, ValueError),
        ({"solos": True}, TypeError),
        ({"solos": 0.5}, TypeError),
        ({"solos": -1}, ValueError),
        ({"solos": 2}, ValueError),
        ({"group_size_min": True}, TypeError),
        ({"group_size_max": False}, TypeError),
        ({"group_size_min": 2.0}, TypeError),
        ({"group_size_max": "6"}, TypeError),
        ({"group_size_min": 1}, ValueError),
        ({"group_size_min": 7}, ValueError),
        ({"group_size_min": 1, "solos": 1}, ValueError),
        ({"group_size_min": 7, "solos": 1}, ValueError),
    ],
)
def test_direct_invalid_shape_refuses_before_rng(monkeypatch, patch, error) -> None:
    rng = random.Random(42)
    before = rng.getstate()
    monkeypatch.setattr(rng, "randint", forbidden)
    monkeypatch.setattr("robots.society.society.SocialGraph", forbidden)
    kwargs = {"n_groups": 1, "solos": 0}
    kwargs.update(patch)
    with pytest.raises(error):
        SocietyRoster.build(rng, **kwargs)
    assert rng.getstate() == before


@pytest.mark.parametrize("http", [False, True])
@pytest.mark.parametrize(
    "patch",
    [
        {"groups": 257, "friends_max": 16},
        {"groups": 0, "solos": 4097},
        {"groups": 10**100},
        {"friends_max": 17},
        {"groups": 0, "solos": 1, "friends_max": 17},
    ],
)
def test_command_resource_refusal_is_atomic_before_candidates(monkeypatch, http, patch) -> None:
    state = WorldState(SocietyRoster.build(random.Random(42), n_groups=3))
    pid = next(iter(state.roster.personas))
    state._reputation._by_agent[pid] = {"human": 0.5}
    state.set_agent_state(pid, current_goal="preserved", online=True)
    state.push_event("session", "preserved")
    before = dict(vars(state))
    events = state.events
    runtimes, memories = dict(state._agent_states), dict(state._memories)
    reputation = state.reputation_entries(pid)
    monkeypatch.setattr("robots.app.world_state.random.Random", forbidden)
    monkeypatch.setattr(SocietyRoster, "build", forbidden)
    monkeypatch.setattr("robots.app.world_state.MemoryLog", forbidden)
    body = {"type": "regenerate_roster", "seed": 17, "groups": 1, "solos": 0}
    body.update(patch)
    if http:
        with TestClient(create_app(state)) as client:
            response = client.post("/commands", json=body)
        assert response.status_code == 400
    else:
        with pytest.raises(CommandError):
            state.apply_command(body)
    assert all(vars(state)[name] is value for name, value in before.items())
    assert state.events == events
    assert all(a is b for a, b in zip(state.events, events, strict=True))
    assert state._agent_states == runtimes
    assert state._memories == memories
    assert state.reputation_entries(pid) == reputation


@pytest.mark.parametrize(
    ("kwargs", "allowed"),
    [
        ({"n_groups": 4095, "solos": 4095}, True),
        ({"n_groups": 4096, "solos": 4096}, True),
        ({"n_groups": 4097, "solos": 4097}, False),
        ({"n_groups": 270, "solos": 15, "group_size_max": 16}, True),
        ({"n_groups": 271, "solos": 16, "group_size_max": 16}, True),
        ({"n_groups": 272, "solos": 17, "group_size_max": 16}, False),
        ({"n_groups": 683}, True),
        ({"n_groups": 684}, False),
        ({"n_groups": 10**100}, False),
        ({"n_groups": 0}, True),
        ({"n_groups": 0, "solos": 1}, False),
    ],
)
def test_factory_admission_boundaries_without_large_allocation(monkeypatch, kwargs, allowed):
    class AdmittedError(Exception):
        pass

    def stop_generation(*args, **kwargs):
        raise AdmittedError

    rng = random.Random(42)
    before = rng.getstate()
    monkeypatch.setattr(rng, "randint", stop_generation)
    monkeypatch.setattr("robots.society.society.SocialGraph", stop_generation)
    error = AdmittedError if allowed else ValueError
    with pytest.raises(error):
        SocietyRoster.build(rng, **kwargs)
    assert rng.getstate() == before


def test_exact_maximum_is_bounded_real_offline_factory() -> None:
    roster = SocietyRoster.build(
        random.Random(42), n_groups=256, solos=0, group_size_min=16, group_size_max=16
    )
    assert len(roster.personas) == 4096
    assert len(roster.groups) == 256
    assert all(len(group.member_ids) == 16 for group in roster.groups)
    assert len({group.group_id for group in roster.groups}) == 256
    assert sum(len(row) for row in roster.graph._edges.values()) == 4096 * 15


@pytest.mark.parametrize(
    ("kwargs", "rng_hash"),
    [
        # fingerprints updated for the wants-system personality assignment
        # (assign_personalities now draws from the same seeded rng)
        ({}, "e41cc51d37c791bf833fa8cc007eef9308d4c4ce7d00c37173ad7340bc1f4bec"),
        ({"n_groups": 0}, "a52169fac48aa2d80acadd41f776ce38656ab70adc3b32c80c1fb1f0ee56b71f"),
        ({"n_groups": 3}, "c48babd265d0fa4d26b6ba0478ccfdd1c34ea2f603309705b91ad559ab62cdff"),
        (
            {"n_groups": 5, "solos": 2, "group_size_min": 3, "group_size_max": 5},
            "29d79ce4f00d849ec1d7c80195e5b4bead7d8e1d957b6ac9d0aa915d3f073476",
        ),
    ],
)
def test_prechange_rng_fingerprints_and_reproducible_identities(kwargs, rng_hash):
    rng = random.Random(42)
    roster = SocietyRoster.build(rng, **kwargs)
    repeated = SocietyRoster.build(random.Random(42), **kwargs)
    assert roster.personas == repeated.personas
    assert roster.graph._edges == repeated.graph._edges
    assert [(g.group_id, g.member_ids, g.attitude, g.schedule.windows) for g in roster.groups] == [
        (g.group_id, g.member_ids, g.attitude, g.schedule.windows) for g in repeated.groups
    ]
    assert hashlib.sha256(repr(rng.getstate()).encode()).hexdigest() == rng_hash


@pytest.mark.parametrize("error", [TypeError, ValueError, RuntimeError])
def test_nonvalidation_factory_errors_keep_origin(monkeypatch, error):
    state = WorldState(SocietyRoster.build(random.Random(42)))
    before = dict(vars(state))
    failure = error("not a resource validation error")

    def failed_build(*args, **kwargs):
        raise failure

    monkeypatch.setattr(SocietyRoster, "build", failed_build)
    with pytest.raises(error) as caught:
        state.apply_command({"type": "regenerate_roster", "seed": 17, "groups": 1})
    assert caught.value is failure
    assert all(vars(state)[name] is value for name, value in before.items())


@pytest.mark.parametrize("total", [4095, 4096, 4097])
def test_command_solo_admission_boundary_without_candidates(monkeypatch, total):
    state = WorldState(SocietyRoster.build(random.Random(42)))
    before = dict(vars(state))
    admitted = RuntimeError("admitted: stop before candidates")

    def stop_generation(*args, **kwargs):
        raise admitted

    monkeypatch.setattr("robots.app.world_state.random.Random", stop_generation)
    body = {"type": "regenerate_roster", "seed": 17, "groups": 0, "solos": total}
    if total <= 4096:
        with pytest.raises(RuntimeError) as caught:
            state.apply_command(body)
        assert caught.value is admitted
    else:
        with pytest.raises(CommandError, match="4096"):
            state.apply_command(body)
    assert all(vars(state)[name] is value for name, value in before.items())
