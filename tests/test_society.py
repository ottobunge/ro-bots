"""ADR-005: society — schedules, groups, social graph, reputation, roster."""

import random

import pytest

from robots.society.models import (
    Attitude,
    FriendGroup,
    Playstyle,
    Schedule,
    ScheduleFactory,
    SocietyPersona,
)
from robots.society.society import (
    PROPAGATION_FACTOR,
    ReputationEvent,
    ReputationStore,
    SocialGraph,
    SocietyRoster,
)

# -- fakes ----------------------------------------------------------------


class FakeClock:
    """SocietyClock double: returns a fixed (weekday, hour)."""

    def __init__(self, weekday: int, hour: float) -> None:
        self._now = (weekday, hour)

    def local_now(self) -> tuple[int, float]:
        return self._now


def make_persona(pid: str, attitude: Attitude = Attitude.GRINDER) -> SocietyPersona:
    return SocietyPersona(
        persona_id=pid,
        name=pid,
        playstyle=Playstyle.MAGE,
        attitude=attitude,
        chattiness=0.5,
        level_band=(30, 60),
    )


def make_group(gid: str, members: tuple[str, ...], windows) -> FriendGroup:
    return FriendGroup(gid, members, Attitude.CLIQUE, Schedule(windows))


# -- Playstyle / Attitude enums --------------------------------------------


def test_playstyle_and_attitude_values() -> None:
    assert {p.value for p in Playstyle} == {
        "tank",
        "healer",
        "mage",
        "hunter",
        "support",
        "melee",
    }
    assert {a.value for a in Attitude} == {
        "helpful_newbie",
        "clique",
        "event_focused",
        "grinder",
        "solo",
    }


# -- Schedule ---------------------------------------------------------------


def test_schedule_online_inside_window() -> None:
    sched = Schedule([(5, 20.0, 23.0)])  # Saturday evening
    assert sched.is_online((5, 20.0))
    assert sched.is_online((5, 21.5))
    assert sched.is_online((5, 22.999))


def test_schedule_offline_outside_window_and_boundaries() -> None:
    sched = Schedule([(5, 20.0, 23.0)])
    assert not sched.is_online((5, 19.999))  # just before start
    assert not sched.is_online((5, 23.0))  # end is exclusive
    assert not sched.is_online((4, 21.0))  # wrong day
    assert not sched.is_online((6, 21.0))


def test_schedule_multiple_windows_any_match() -> None:
    sched = Schedule([(1, 8.0, 10.0), (3, 20.0, 22.0)])
    assert sched.is_online((1, 9.0))
    assert sched.is_online((3, 20.5))
    assert not sched.is_online((2, 9.0))


def test_schedule_window_wrapping_midnight() -> None:
    sched = Schedule([(5, 22.0, 2.0)])  # Sat 22:00 -> Sun 02:00
    assert sched.is_online((5, 23.0))
    assert sched.is_online((6, 1.0))
    assert not sched.is_online((6, 2.0))
    assert not sched.is_online((5, 21.0))


def test_schedule_factory_windows_are_valid() -> None:
    rng = random.Random(7)
    for _ in range(20):
        sched = ScheduleFactory.make_group_schedule(rng, overlap_hint=3)
        assert 1 <= len(sched.windows) <= 3
        for day, start, end in sched.windows:
            assert 0 <= day <= 6
            assert 0.0 <= start < 24.0
            assert 0.0 < end <= 24.0


# -- SocialGraph ------------------------------------------------------------


def test_graph_defaults_and_affinity() -> None:
    g = SocialGraph()
    assert g.affinity("a", "b") == 0.0


def test_graph_seed_group_positive_both_directions() -> None:
    g = SocialGraph()
    group = make_group("grp", ("a", "b", "c"), [(1, 20.0, 22.0)])
    g.seed_group(group)
    for x in ("a", "b", "c"):
        for y in ("a", "b", "c"):
            if x != y:
                assert g.affinity(x, y) == 0.5
    assert g.affinity("a", "outsider") == 0.0


def test_graph_nudge_clamps() -> None:
    g = SocialGraph()
    g.nudge("a", "b", 0.8)
    g.nudge("a", "b", 0.8)  # would be 1.6 -> clamped
    assert g.affinity("a", "b") == 1.0
    g.nudge("a", "c", -2.0)
    assert g.affinity("a", "c") == -1.0


def test_graph_friends_of_positive_only() -> None:
    g = SocialGraph()
    g.nudge("a", "b", 0.3)
    g.nudge("a", "c", -0.9)
    assert g.friends_of("a") == ("b",)


# -- ReputationStore ---------------------------------------------------------


def test_apply_event_scores_and_clamps() -> None:
    store = ReputationStore()
    assert store.agent_score("bot1", "Otto") == 0.0
    store.apply_event(ReputationEvent("Otto", "bot1", 0.4, "healed me"))
    assert store.agent_score("bot1", "Otto") == 0.4
    store.apply_event(ReputationEvent("Otto", "bot1", 0.9, "buffs again"))
    assert store.agent_score("bot1", "Otto") == 1.0  # clamped
    store.apply_event(ReputationEvent("Otto", "bot1", -3.0, "kill stole"))
    assert store.agent_score("bot1", "Otto") == -1.0  # clamped
    assert store.agent_score("bot2", "Otto") == 0.0  # per-agent isolation


def test_propagate_below_threshold_is_noop() -> None:
    store = ReputationStore()
    graph = SocialGraph()
    group = make_group("grp", ("bot1", "bot2"), [(1, 20.0, 22.0)])
    event = ReputationEvent("Otto", "bot1", 0.19, "meh")
    assert store.propagate(event, graph, [group]) == []
    assert store.group_score("grp", "Otto") == 0.0


def test_propagate_moves_friend_groups_with_factor() -> None:
    store = ReputationStore()
    graph = SocialGraph()
    grp_a = make_group("A", ("bot1", "bot2"), [(1, 20.0, 22.0)])
    grp_b = make_group("B", ("bot3",), [(1, 20.0, 22.0)])
    graph.seed_group(grp_a)
    # no inter-group edges yet -> affinity 0 -> shift = 0.25 * delta * 0.5
    applied = store.propagate(
        ReputationEvent("Otto", "bot1", 0.6, "great tank"), graph, [grp_a, grp_b]
    )
    assert applied == [("A", PROPAGATION_FACTOR * 0.6 * 0.5)]
    assert store.group_score("A", "Otto") == pytest.approx(0.075)
    assert store.group_score("B", "Otto") == 0.0  # not the reporter's group


def test_propagate_damped_by_inter_group_affinity() -> None:
    store = ReputationStore()
    graph = SocialGraph()
    grp_a = make_group("A", ("bot1", "bot2"), [(1, 20.0, 22.0)])
    grp_b = make_group("B", ("bot3",), [(1, 20.0, 22.0)])
    graph.seed_group(grp_a)
    graph.nudge("bot2", "bot3", 1.0)  # full inter-group affinity
    applied = store.propagate(ReputationEvent("Otto", "bot1", -0.8, "rude"), graph, [grp_a, grp_b])
    # shift = 0.25 * (-0.8) * (0.5 + 0.5 * 1.0)
    assert applied == [("A", -0.8 * PROPAGATION_FACTOR)]
    assert store.group_score("A", "Otto") == pytest.approx(-0.2)


def test_propagate_group_scores_clamp() -> None:
    store = ReputationStore()
    graph = SocialGraph()
    grp = make_group("A", ("bot1",), [(1, 20.0, 22.0)])
    store.propagate(ReputationEvent("Otto", "bot1", 5.0, "legend"), graph, [grp])
    # delta 5.0 * factor 0.25 * damping 0.5 = 0.625, still within [-1, 1]
    assert store.group_score("A", "Otto") == pytest.approx(0.625)
    # push past the clamp with accumulated events
    store.propagate(ReputationEvent("Otto", "bot1", 5.0, "legend again"), graph, [grp])
    assert store.group_score("A", "Otto") == 1.0


def test_propagate_negative_delta_same_mechanism() -> None:
    store = ReputationStore()
    graph = SocialGraph()
    grp = make_group("A", ("bot1", "bot2"), [(1, 20.0, 22.0)])
    graph.seed_group(grp)
    store.propagate(ReputationEvent("Rude", "bot1", -0.5, "ks"), graph, [grp])
    assert store.group_score("A", "Rude") < 0.0


# -- SocietyRoster -----------------------------------------------------------


def test_roster_build_groups_incl_solo_and_seed_graph() -> None:
    roster = SocietyRoster.build(random.Random(42), n_groups=5)
    assert len(roster.groups) == 5
    sizes = [len(g.member_ids) for g in roster.groups]
    assert sizes[-1] == 1  # last group is always a solo outsider
    assert all(2 <= s <= 6 for s in sizes[:-1])
    all_members = [m for g in roster.groups for m in g.member_ids]
    assert len(all_members) == len(set(all_members))  # no persona in two groups
    for group in roster.groups:
        for a in group.member_ids:
            for b in group.member_ids:
                if a != b:
                    assert roster.graph.affinity(a, b) > 0.0
    solo = roster.groups[-1]
    assert solo.attitude == Attitude.SOLO


def test_roster_online_personas_respect_schedules() -> None:
    groups = [
        make_group("night", ("owl",), [(5, 22.0, 23.0)]),
        make_group("day", ("lark",), [(2, 9.0, 12.0)]),
    ]
    personas = {"owl": make_persona("owl"), "lark": make_persona("lark")}
    roster = SocietyRoster(groups, personas, SocialGraph(), ReputationStore())
    assert roster.online_personas((5, 22.5)) == [personas["owl"]]
    assert roster.online_personas((2, 9.0)) == [personas["lark"]]
    assert roster.online_personas((0, 3.0)) == []


def test_roster_online_personas_group_means_all_members() -> None:
    groups = [make_group("trio", ("a", "b", "c"), [(4, 18.0, 20.0)])]
    personas = {pid: make_persona(pid) for pid in ("a", "b", "c")}
    roster = SocietyRoster(groups, personas, SocialGraph(), ReputationStore())
    assert roster.online_personas((4, 19.0)) == [personas["a"], personas["b"], personas["c"]]


def test_roster_seeded_rng_reproducible() -> None:
    r1 = SocietyRoster.build(random.Random(1234), n_groups=4)
    r2 = SocietyRoster.build(random.Random(1234), n_groups=4)
    assert [g.group_id for g in r1.groups] == [g.group_id for g in r2.groups]
    assert [g.member_ids for g in r1.groups] == [g.member_ids for g in r2.groups]
    assert [g.schedule.windows for g in r1.groups] == [g.schedule.windows for g in r2.groups]
    assert [p.playstyle for p in r1.personas.values()] == [
        p.playstyle for p in r2.personas.values()
    ]
    r3 = SocietyRoster.build(random.Random(99), n_groups=4)
    assert [g.group_id for g in r1.groups] != [g.group_id for g in r3.groups]


def test_roster_persona_fields() -> None:
    roster = SocietyRoster.build(random.Random(5), n_groups=3)
    for persona in roster.personas.values():
        assert 0.0 <= persona.chattiness <= 1.0
        assert 1 <= persona.level_band[0] <= persona.level_band[1]
        assert isinstance(persona.playstyle, Playstyle)


def test_fake_clock_protocol_shape() -> None:
    clock = FakeClock(3, 21.5)
    weekday, hour = clock.local_now()
    assert (weekday, hour) == (3, 21.5)
