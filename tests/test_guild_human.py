"""Guild/WoE layer + human interaction feeding reputation (ADR-005 completion)."""

import random

import pytest

from robots.society.guild import (
    GuildRegistry,
    WoeCalendar,
    WoeEvent,
    WoeParticipation,
    majority_attitude,
)
from robots.society.human import (
    EVENT_DELTA_MAX,
    EVENT_DELTA_MIN,
    ContributionScorer,
    HumanContribution,
    HumanTracker,
)
from robots.society.models import Attitude, FriendGroup, Schedule
from robots.society.society import ReputationStore, SocialGraph


def make_group(
    gid: str,
    members: tuple[str, ...],
    attitude: Attitude = Attitude.CLIQUE,
) -> FriendGroup:
    return FriendGroup(gid, members, attitude, Schedule([(1, 20.0, 22.0)]))


WOE = WoeEvent("woe-1", 20.0, 22.0, 3, "kriemhild")


# -- Guild / GuildRegistry ----------------------------------------------------


def test_guild_attitude_is_member_groups_majority() -> None:
    groups = [
        make_group("a", ("p1", "p2"), Attitude.EVENT_FOCUSED),
        make_group("b", ("p3",), Attitude.GRINDER),
        make_group("c", ("p4",), Attitude.GRINDER),
    ]
    assert majority_attitude(groups) is Attitude.GRINDER
    assert majority_attitude(groups[:1]) is Attitude.EVENT_FOCUSED
    with pytest.raises(ValueError, match="at least one"):
        majority_attitude([])


def test_guild_registry_create_and_find() -> None:
    reg = GuildRegistry()
    a = make_group("a", ("p1", "p2"), Attitude.EVENT_FOCUSED)
    guild = reg.create("Iron Wolves", [a], ("hold Kriemhild",))
    assert reg.find(guild.guild_id) is guild
    assert reg.find("guild-nope") is None
    assert guild.member_group_ids == ("a",)
    assert guild.goals == ("hold Kriemhild",)
    assert guild.attitude is Attitude.EVENT_FOCUSED


def test_guild_member_persona_ids_dedupes_and_skips_unknown_groups() -> None:
    reg = GuildRegistry()
    a = make_group("a", ("p1", "p2"), Attitude.EVENT_FOCUSED)
    b = make_group("b", ("p2", "p3"), Attitude.EVENT_FOCUSED)
    guild = reg.merge([a, b])
    groups = {g.group_id: g for g in (a, b)}
    assert guild.member_persona_ids(groups) == ("p1", "p2", "p3")
    assert guild.member_persona_ids({}) == ()  # unknown group ids are skipped


def test_goals_for_group_empty_without_guild() -> None:
    reg = GuildRegistry()
    assert reg.goals_for_group("lonely") == ()
    a = make_group("a", ("p1",), Attitude.GRINDER)
    reg.create("G", [a], ("hold Kriemhild", "reach lvl-avg 60"))
    assert reg.goals_for_group("a") == ("hold Kriemhild", "reach lvl-avg 60")
    assert reg.goals_for_group("b") == ()


def test_merge_joins_groups_and_carries_goals() -> None:
    reg = GuildRegistry()
    a = make_group("a", ("p1", "p2"), Attitude.GRINDER)
    reg.create("First", [a], ("hold Kriemhild",))
    b = make_group("b", ("p3",), Attitude.EVENT_FOCUSED)
    c = make_group("c", ("p4",), Attitude.EVENT_FOCUSED)
    merged = reg.merge([b, c])
    assert merged.member_group_ids == ("b", "c")
    assert merged.attitude is Attitude.EVENT_FOCUSED
    # merge only carries goals of the *merged* groups; b and c are fresh.
    assert merged.goals == ()
    assert reg.goals_for_group("b") == ()
    assert reg.goals_for_group("a") == ("hold Kriemhild",)
    d = make_group("d", ("p5",), Attitude.GRINDER)
    reg.create("HasGoals", [d], ("hold aldebaran",))
    e = make_group("e", ("p6",), Attitude.GRINDER)
    reg.merge([e])
    merged2 = reg.merge([d, e])
    assert merged2.goals == ("hold aldebaran",)


# -- WoeCalendar ----------------------------------------------------------------


def test_active_woe_inside_and_boundary_times() -> None:
    cal = WoeCalendar([WOE])
    assert cal.active_woe((3, 20.0)) is WOE  # start inclusive
    assert cal.active_woe((3, 21.0)) is WOE
    assert cal.active_woe((3, 21.999)) is WOE
    assert cal.active_woe((3, 19.999)) is None  # just before start
    assert cal.active_woe((3, 22.0)) is None  # end exclusive
    assert cal.active_woe((2, 21.0)) is None  # wrong day


def test_next_woe_same_day_and_wrap_to_next_week() -> None:
    cal = WoeCalendar([WOE, WoeEvent("woe-2", 8.0, 10.0, 5, "aldeg_cas02")])
    assert cal.next_woe((3, 10.0)) is WOE  # later today
    assert cal.next_woe((3, 22.0)) is cal.events[1]  # Friday's event
    # At (5, 9.0) woe-2 is already ACTIVE; the next one is next week's WOE.
    assert cal.next_woe((5, 9.0)) is WOE
    assert cal.next_woe((5, 10.0)) is WOE
    # After the last event of the week, the earliest one wraps to next week.
    assert cal.next_woe((6, 12.0)) is WOE
    assert cal.next_woe((3, 22.5)) is cal.events[1]


def test_next_woe_empty_calendar_returns_none() -> None:
    assert WoeCalendar().next_woe((3, 20.0)) is None
    assert WoeCalendar().active_woe((3, 20.0)) is None


# -- WoeParticipation -------------------------------------------------------------


def test_participation_event_focused_always_attends() -> None:
    reg = GuildRegistry()
    a = make_group("a", ("p1", "p2"), Attitude.EVENT_FOCUSED)
    reg.create("G", [a])  # no goals at all
    decided = WoeParticipation.decide([a], reg, WOE)
    assert [gid for gid, _ in decided] == ["a"]
    assert "event_focused" in decided[0][1]


def test_participation_grinder_only_with_map_holding_goal() -> None:
    reg = GuildRegistry()
    grinder = make_group("g", ("p1",), Attitude.GRINDER)
    reg.create("NoGoals", [grinder])
    assert WoeParticipation.decide([grinder], reg, WOE) == ()
    reg.create("Holders", [grinder], ("hold Kriemhild",))
    decided = WoeParticipation.decide([grinder], reg, WOE)
    assert [gid for gid, _ in decided] == ["g"]
    assert "guild goal" in decided[0][1]


def test_participation_clique_never_attends() -> None:
    reg = GuildRegistry()
    clique = make_group("c", ("p1",), Attitude.CLIQUE)
    reg.create("G", [clique], ("hold Kriemhild",))
    assert WoeParticipation.decide([clique], reg, WOE) == ()


def test_participation_solo_follows_guild() -> None:
    reg = GuildRegistry()
    event_focused = make_group("ef", ("p1",), Attitude.EVENT_FOCUSED)
    solo = make_group("solo-p2", ("p2",), Attitude.SOLO)
    reg.create("G", [event_focused, solo])
    decided = WoeParticipation.decide([event_focused, solo], reg, WOE)
    assert [gid for gid, _ in decided] == ["ef", "solo-p2"]
    assert "guild attends" in decided[1][1]


def test_participation_solo_without_attending_guild_stays_home() -> None:
    reg = GuildRegistry()
    clique = make_group("c", ("p1",), Attitude.CLIQUE)
    solo = make_group("solo-p2", ("p2",), Attitude.SOLO)
    reg.create("G", [clique, solo])
    assert WoeParticipation.decide([clique, solo], reg, WOE) == ()
    lone = make_group("solo-p3", ("p3",), Attitude.SOLO)  # no guild at all
    assert WoeParticipation.decide([lone], reg, WOE) == ()


def test_participation_none_when_no_active_woe() -> None:
    reg = GuildRegistry()
    a = make_group("a", ("p1",), Attitude.EVENT_FOCUSED)
    reg.create("G", [a])
    assert WoeParticipation.decide([a], reg, None) == ()


# -- ContributionScorer -------------------------------------------------------------


def make_contribution(kind: str, magnitude: float = 1.0) -> HumanContribution:
    return HumanContribution("Otto", kind, magnitude, "prt_fild08", ts=100.0)  # type: ignore[arg-type]


def test_scorer_useful_kinds_are_positive() -> None:
    for kind in ("damage_share", "heal", "buff"):
        event = ContributionScorer.score(make_contribution(kind), "bot1")
        assert event.delta > 0
        assert event.human_name == "Otto"
        assert event.agent_id == "bot1"


def test_scorer_bad_kinds_are_negative() -> None:
    for kind in ("dead_weight", "rude", "kill_steal"):
        assert ContributionScorer.score(make_contribution(kind), "bot1").delta < 0


def test_scorer_magnitude_scales_and_zero_is_neutral() -> None:
    full = ContributionScorer.score(make_contribution("damage_share", 1.0), "bot1")
    half = ContributionScorer.score(make_contribution("damage_share", 0.5), "bot1")
    assert half.delta == pytest.approx(full.delta / 2)
    assert ContributionScorer.score(make_contribution("heal", 0.0), "bot1").delta == 0.0


def test_scorer_clamps_per_event() -> None:
    # kill_steal (-0.5) hits both clamp bounds at full magnitude...
    assert ContributionScorer.score(make_contribution("kill_steal", 1.0), "bot1").delta == (
        EVENT_DELTA_MIN
    )
    # ...and flips positive with an inverted magnitude, hitting the other bound.
    assert ContributionScorer.score(make_contribution("kill_steal", -1.0), "bot1").delta == (
        EVENT_DELTA_MAX
    )
    # Out-of-range magnitudes are clamped to [-1, 1] before scaling.
    wild = ContributionScorer.score(make_contribution("heal", 9.0), "bot1")
    assert wild.delta == pytest.approx(0.4)
    assert EVENT_DELTA_MIN <= wild.delta <= EVENT_DELTA_MAX


# -- HumanTracker --------------------------------------------------------------


def test_tracker_friendship_score_accumulates_and_clamps() -> None:
    tracker = HumanTracker(ReputationStore(), SocialGraph(), [], random.Random(1))
    for _ in range(5):
        tracker.record(make_contribution("heal"), "bot1")
    assert tracker.friendship_score("Otto", "bot1") == pytest.approx(1.0)
    for _ in range(5):
        tracker.record(HumanContribution("Mallory", "kill_steal", 1.0, "x", 1.0), "bot1")
    assert tracker.friendship_score("Mallory", "bot1") == pytest.approx(-1.0)
    assert tracker.friendship_score("Stranger", "bot1") == 0.0


def test_tracker_propagates_past_threshold_by_chattiness() -> None:
    store = ReputationStore()
    graph = SocialGraph()
    reporter = make_group("reporters", ("bot1", "bot2"), Attitude.HELPFUL_NEWBIE)
    friends = make_group("friends", ("bot3",), Attitude.EVENT_FOCUSED)
    graph.seed_group(reporter)
    graph.seed_group(friends)
    chattiness: dict[str, float] = {"bot1": 1.0, "bot2": 0.0}
    tracker = HumanTracker(
        store, graph, [reporter, friends], random.Random(42), chattiness_of=lambda a: chattiness[a]
    )
    # 0.4 * 0.9 = 0.36 >= 0.2: crosses the threshold in one event.
    tracker.record(HumanContribution("Otto", "damage_share", 0.9, "prt_fild08", 1.0), "bot1")
    assert tracker.friendship_score("Otto", "bot1") == pytest.approx(0.36)
    assert len(tracker.propagation_log) == 1
    line = tracker.propagation_log[0]
    assert "bot1 told their friends about Otto" in line
    # Group score moved by PROPAGATION_FACTOR * delta * (0.5 + 0.5 * affinity)
    assert tracker.group_score("Otto", "reporters") == pytest.approx(0.25 * 0.36 * 0.5)
    assert tracker.group_score("Otto", "friends") == 0.0  # bot1 is not in that group


def test_tracker_low_chattiness_stays_silent_seeded() -> None:
    store = ReputationStore()
    graph = SocialGraph()
    group = make_group("g", ("bot1", "bot2"), Attitude.HELPFUL_NEWBIE)
    graph.seed_group(group)
    tracker = HumanTracker(store, graph, [group], random.Random(42), chattiness_of=lambda _a: 0.0)
    tracker.record(HumanContribution("Otto", "damage_share", 0.9, "map", 1.0), "bot1")
    assert tracker.friendship_score("Otto", "bot1") == pytest.approx(0.36)
    assert tracker.propagation_log == []
    assert tracker.group_score("Otto", "g") == 0.0


def test_tracker_no_propagation_below_threshold() -> None:
    store = ReputationStore()
    graph = SocialGraph()
    group = make_group("g", ("bot1", "bot2"), Attitude.HELPFUL_NEWBIE)
    graph.seed_group(group)
    tracker = HumanTracker(store, graph, [group], random.Random(42), chattiness_of=lambda _a: 1.0)
    # buff * 0.3 = 0.09 per event; two events reach 0.18, never crossing 0.2.
    tracker.record(HumanContribution("Otto", "buff", 0.3, "map", 1.0), "bot1")
    tracker.record(HumanContribution("Otto", "buff", 0.3, "map", 2.0), "bot1")
    assert tracker.friendship_score("Otto", "bot1") == pytest.approx(0.18)
    assert tracker.propagation_log == []
    assert tracker.group_score("Otto", "g") == 0.0


def test_tracker_negative_crossing_propagates_warning() -> None:
    store = ReputationStore()
    graph = SocialGraph()
    group = make_group("g", ("bot1", "bot2"), Attitude.HELPFUL_NEWBIE)
    graph.seed_group(group)
    tracker = HumanTracker(store, graph, [group], random.Random(7), chattiness_of=lambda _a: 1.0)
    tracker.record(HumanContribution("Mallory", "kill_steal", 1.0, "map", 1.0), "bot1")
    assert tracker.friendship_score("Mallory", "bot1") == pytest.approx(-0.5)
    assert len(tracker.propagation_log) == 1
    assert "warned about Mallory" in tracker.propagation_log[0]
    assert tracker.group_score("Mallory", "g") < 0
