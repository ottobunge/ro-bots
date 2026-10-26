"""Agent-to-agent interaction ledger (feature/agent-interaction-ledger).

The interaction-event layer that feeds the RelationshipLedger: OBSERVED
in-game interactions between two roster-known agents (party time, shared
damage rows, invite accepts/declines, helpful/rude chat premades, attacks)
move a bounded per-pair standing with an asymmetric +/- model (negatives
weigh NEGATIVE_RATIO x positives), decayed with the weekly half-life,
aggregated per (group, agent) and (group, group), persisted like the
relationship ledger, and exposed to the brain as bounded decide lines.
"""

import random
from pathlib import Path
from typing import Any

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.app.brain import EventDrivenBrain
from robots.domain.actions import PartyChat, Say, WhisperTo
from robots.domain.events import ChatHeard
from robots.domain.model import ChatLine
from robots.society.interactions import (
    DAMAGE_SHARED_UNIT,
    GOSSIP_REPORT_THRESHOLD,
    INTERACTION_CONTEXT_MAX_LINES,
    NEGATIVE_RATIO,
    NEGATIVE_WEIGHTS,
    PARTY_TIME_UNIT_S,
    POSITIVE_WEIGHTS,
    RIVAL_GOSSIP_MULTIPLIER,
    RIVALRY_FORMATION_STANDING,
    SCORE_MAX,
    SCORE_MIN,
    InteractionLedger,
    classify_chat,
    rivalry_premade,
)
from robots.society.objectives import BoundCoordinator, GroupCoordinator
from robots.society.relations import (
    CHAT_AFFINITY_DELTA,
    GOSSIP_HOP_DECAY,
    PARTY_AFFINITY_PER_HOUR,
    WEEKLY_HALF_LIFE_S,
    RelationshipLedger,
)
from tests.test_brain import base_answers
from tests.test_coordination_wiring import make_population, wiring_host
from tests.test_relations import CapturingModel, make_state

# -- helpers -------------------------------------------------------------


def make_ledger(persona_id: str = "obs") -> InteractionLedger:
    """One observer ledger with a two-group roster (the injected knowledge)."""
    ledger = InteractionLedger(persona_id)
    ledger.register_persona("obs", "Observer")
    ledger.register_persona("x", "Xavier")
    ledger.register_persona("y", "Yuri")
    ledger.register_persona("z", "Zoe")
    ledger.seed_group("g1", ("obs", "x"))
    ledger.seed_group("g2", ("y", "z"))
    return ledger


DOCUMENTED_POSITIVE: dict[str, tuple[dict[str, Any], float]] = {
    "party_time": ({"seconds": PARTY_TIME_UNIT_S}, 1.0),
    "party_session": ({}, 2.0),
    "damage_shared": ({"amount": DAMAGE_SHARED_UNIT}, 1.0),
    "shared_kill": ({}, 3.0),
    "invite_accept": ({}, 5.0),
    "helpful_chat": ({}, 2.0),
    "heal_received": ({}, 2.0),
    "buff_received": ({}, 2.0),
}

DOCUMENTED_NEGATIVE: dict[str, float] = {
    "invite_decline": 5.0,
    "attack_partner": 10.0,
    "attack_groupmate": 6.0,
    "rude_chat": 4.0,
    "party_leave_in_fight": 5.0,
}


# -- the documented weight tables -----------------------------------------


def test_positive_weight_table_matches_documentation() -> None:
    assert {kind: w for kind, (_, w) in DOCUMENTED_POSITIVE.items()} == POSITIVE_WEIGHTS


def test_negative_weight_table_matches_documentation() -> None:
    assert NEGATIVE_WEIGHTS == DOCUMENTED_NEGATIVE
    assert NEGATIVE_RATIO == 3.0  # the fixed asymmetry: negatives weigh 3x


# -- knowledge model: roster in, observation only --------------------------


def test_unknown_partner_event_is_not_ingested() -> None:
    ledger = make_ledger()
    assert ledger.ingest("obs", "ghost", "shared_kill", ts=0.0) is False
    assert ledger.ingest("ghost", "obs", "shared_kill", ts=0.0) is False
    assert ledger.standing("obs", "ghost") == 0.0


def test_self_event_is_never_ingested() -> None:
    ledger = make_ledger()
    assert ledger.ingest("obs", "obs", "shared_kill", ts=0.0) is False
    assert ledger.standing("obs", "obs") == 0.0


def test_known_pair_event_ingests() -> None:
    ledger = make_ledger()
    assert ledger.ingest("obs", "x", "shared_kill", ts=0.0) is True
    assert ledger.standing("obs", "x") == pytest.approx(3.0)


def test_ingest_resolves_display_names_through_the_roster() -> None:
    ledger = make_ledger()
    assert ledger.ingest("Observer", "Xavier", "shared_kill", ts=0.0) is True
    assert ledger.standing("obs", "x") == pytest.approx(3.0)


def test_unknown_kind_rejected() -> None:
    ledger = make_ledger()
    with pytest.raises(ValueError, match="unknown interaction kind"):
        ledger.ingest("obs", "x", "kill_steal", ts=0.0)


# -- every event kind moves the score the documented way -------------------


@pytest.mark.parametrize("kind", sorted(DOCUMENTED_POSITIVE))
def test_each_positive_kind_moves_score_up_documented(kind: str) -> None:
    ledger = make_ledger()
    kwargs, expected = DOCUMENTED_POSITIVE[kind]
    assert ledger.ingest("obs", "x", kind, ts=0.0, **kwargs) is True
    assert ledger.standing("obs", "x") == pytest.approx(expected)


@pytest.mark.parametrize("kind", sorted(DOCUMENTED_NEGATIVE))
def test_each_negative_kind_moves_score_down_by_ratio(kind: str) -> None:
    ledger = make_ledger()
    assert ledger.ingest("obs", "x", kind, ts=0.0) is True
    assert ledger.standing("obs", "x") == pytest.approx(-DOCUMENTED_NEGATIVE[kind] * NEGATIVE_RATIO)


def test_party_time_scales_with_seconds() -> None:
    ledger = make_ledger()
    ledger.ingest("obs", "x", "party_time", seconds=3 * PARTY_TIME_UNIT_S, ts=0.0)
    assert ledger.standing("obs", "x") == pytest.approx(3.0)


def test_shared_damage_scales_with_amount_and_accumulates() -> None:
    ledger = make_ledger()
    ledger.ingest("obs", "x", "damage_shared", amount=100, ts=0.0)
    ledger.ingest("obs", "x", "damage_shared", amount=320, ts=0.0)
    assert ledger.standing("obs", "x") == pytest.approx(420 / DAMAGE_SHARED_UNIT)


def test_negatives_outweigh_positives() -> None:
    ledger = make_ledger()
    ledger.ingest("obs", "x", "invite_accept", ts=0.0)
    ledger.ingest("obs", "x", "attack_partner", ts=0.0)
    expected = 5.0 - 10.0 * NEGATIVE_RATIO
    assert ledger.standing("obs", "x") == pytest.approx(expected)
    assert expected < 0.0  # one attack erases the accept and more


def test_score_clamps_at_both_bounds() -> None:
    ledger = make_ledger()
    for _ in range(50):
        ledger.ingest("obs", "x", "attack_partner", ts=0.0)
    assert ledger.standing("obs", "x") == SCORE_MIN
    for _ in range(200):
        ledger.ingest("obs", "y", "invite_accept", ts=0.0)
    assert ledger.standing("obs", "y") == SCORE_MAX


# -- decay: the weekly half-life -------------------------------------------


def test_weekly_half_life_halves_the_standing() -> None:
    ledger = make_ledger()
    ledger.ingest("obs", "x", "shared_kill", ts=0.0)
    ledger.decay(WEEKLY_HALF_LIFE_S)
    assert ledger.standing("obs", "x") == pytest.approx(1.5)


def test_decay_reaches_zero_never_flips_sign() -> None:
    ledger = make_ledger()
    ledger.ingest("obs", "x", "attack_partner", ts=0.0)
    ledger.decay(52 * WEEKLY_HALF_LIFE_S)
    assert ledger.standing("obs", "x") == pytest.approx(0.0, abs=1e-6)


# -- the group aggregates -----------------------------------------------------


def test_group_agent_aggregate_is_the_member_mean() -> None:
    ledger = make_ledger()
    ledger.ingest("obs", "y", "invite_accept", ts=0.0)  # +5
    ledger.ingest("x", "y", "attack_partner", ts=0.0)  # -30
    # g1 = (obs, x): mean(+5, -30) = -12.5 toward y
    assert ledger.group_agent_standing("g1", "y") == pytest.approx(-12.5)
    assert ledger.group_agent_standing("g1", "obs") == 0.0  # no evidence -> neutral


def test_group_group_aggregate_is_the_cross_pair_mean() -> None:
    ledger = make_ledger()
    ledger.ingest("obs", "y", "invite_accept", ts=0.0)  # +5
    ledger.ingest("x", "z", "shared_kill", ts=0.0)  # +3
    # cross pairs: (obs,y)=+5, (obs,z)=0, (x,y)=0, (x,z)=+3 -> mean +2
    assert ledger.group_group_standing("g1", "g2") == pytest.approx(2.0)
    assert ledger.group_group_standing("g1", "missing") == 0.0


# -- the decide block -------------------------------------------------------


def test_decide_line_shape_without_negatives() -> None:
    ledger = make_ledger()
    for _ in range(3):
        ledger.ingest("obs", "x", "party_session", ts=0.0)
    ledger.ingest("obs", "x", "damage_shared", amount=420, ts=0.0)
    lines = ledger.decide_lines("obs")
    assert lines == ["Xavier: +8 (party 3 sessions, 420 shared dmg; no negatives)"]


def test_decide_line_shape_with_negatives() -> None:
    ledger = make_ledger()
    ledger.ingest("obs", "x", "party_session", ts=0.0)
    ledger.ingest("obs", "x", "rude_chat", ts=0.0)
    lines = ledger.decide_lines("obs")
    assert lines == ["Xavier: -10 (party 1 sessions, 0 shared dmg; 1 negative)"]


def test_decide_lines_are_bounded_and_strongest_first() -> None:
    ledger = make_ledger()
    ledger.ingest("obs", "x", "party_session", ts=0.0)  # +2
    ledger.ingest("obs", "y", "invite_accept", ts=0.0)  # +5 strongest
    ledger.ingest("obs", "z", "party_time", seconds=PARTY_TIME_UNIT_S, ts=0.0)  # +1
    for i in range(6):
        ledger.register_persona(f"w{i}", f"W{i}")
        ledger.ingest("obs", f"w{i}", "shared_kill", ts=0.0)  # +3 each
    lines = ledger.decide_lines("obs")
    assert len(lines) == INTERACTION_CONTEXT_MAX_LINES
    assert lines[0].startswith("Yuri: +5")
    assert lines[1].startswith("W0: +3")


def test_decide_lines_empty_without_evidence() -> None:
    assert make_ledger().decide_lines("obs") == []


# -- chat classification (the premade categories) ---------------------------


def test_classify_chat_helpful_categories() -> None:
    assert classify_chat("hunting Poring prt_fild08, join me") == "helpful_chat"
    assert classify_chat("Looking for party! Swordsman lvl 42") == "helpful_chat"
    assert classify_chat("inviting Xavier") == "helpful_chat"


def test_classify_chat_rude_category() -> None:
    assert classify_chat("noob") == "rude_chat"
    assert classify_chat("learn to play") == "rude_chat"


def test_classify_chat_everyday_lines_are_none() -> None:
    assert classify_chat("gg wp") is None
    assert classify_chat("anyone selling jellopy?") is None


def test_ingest_chat_records_against_roster_sender() -> None:
    ledger = make_ledger()
    assert ledger.ingest_chat("Xavier", "noob", ts=0.0) is True
    assert ledger.standing("obs", "x") == pytest.approx(
        -DOCUMENTED_NEGATIVE["rude_chat"] * NEGATIVE_RATIO
    )
    assert ledger.ingest_chat("Yuri", "hunting Poring prt_fild08, join me", ts=0.0) is True
    assert ledger.standing("obs", "y") == pytest.approx(2.0)


def test_ingest_chat_ignores_unknown_and_own_lines() -> None:
    ledger = make_ledger()
    assert ledger.ingest_chat("Ghost", "noob", ts=0.0) is False
    assert ledger.ingest_chat("Observer", "noob", ts=0.0) is False
    assert ledger.standing("obs", "obs") == 0.0


# -- gossip propagation (review cadence) ------------------------------------


def test_gossip_propagates_to_allied_group_at_hop_decay() -> None:
    ledger = make_ledger()
    # g1 holds a strong negative standing toward g2 (obs and x were attacked)
    ledger.ingest("y", "obs", "attack_partner", ts=0.0)  # (obs,y) -30
    ledger.ingest("z", "x", "attack_partner", ts=0.0)  # (x,z) -30
    # the g1 <-> g3 alliance: positive cross evidence between obs and g3's ace
    ledger.register_persona("a", "Ace")
    ledger.seed_group("g3", ("a",))
    ledger.ingest("obs", "a", "shared_kill", ts=0.0)  # +3 affinity
    attitude = ledger.group_group_standing("g1", "g2")
    assert attitude == pytest.approx(-15.0)  # mean over the four cross pairs
    hops = ledger.propagate_gossip(ts=0.0)  # same base ts: no decay yet
    assert hops, "the material attitude must propagate"
    hearing, subject, shift = hops[0]
    assert hearing == "g3"
    assert subject == "g2"
    affinity = ledger.standing("obs", "a")
    expected = attitude * GOSSIP_HOP_DECAY * (0.5 + 0.5 * min(affinity, 1.0))
    assert shift == pytest.approx(expected)
    assert ledger.heard_standing("g3", "g2") == pytest.approx(expected)


def test_gossip_skips_sub_threshold_attitudes() -> None:
    ledger = make_ledger()
    ledger.ingest("y", "obs", "party_session", ts=0.0)  # +2/4 cross pairs: below material
    assert ledger.propagate_gossip(ts=1.0) == []


def test_gossip_ignores_unallied_groups() -> None:
    ledger = make_ledger()
    ledger.ingest("y", "obs", "attack_partner", ts=0.0)
    # negative attitude, but no positive cross evidence to any third group
    assert ledger.propagate_gossip(ts=1.0) == []


# -- review emissions: the report and the taunt are IN-GAME channel actions --


def make_attacked_world() -> InteractionLedger:
    """g1 (obs/x) holds -32.5 toward g2 (y/z): crossed, not yet a rivalry."""
    ledger = make_ledger()
    for _ in range(4):
        ledger.ingest("y", "obs", "attack_partner", ts=0.0)  # -100 (clamped)
    ledger.ingest("z", "x", "attack_partner", ts=0.0)  # -30
    return ledger


def make_rival_world() -> InteractionLedger:
    """make_attacked_world plus the g1<->g3 alliance and the formed rivalry."""
    ledger = make_attacked_world()
    ledger.register_persona("a", "Ace")
    ledger.seed_group("g3", ("a",))
    ledger.ingest("obs", "a", "shared_kill", ts=0.0)
    ledger.maybe_form_group_rivalries(ts=0.0)
    return ledger


def test_review_emits_the_rival_taunt_in_game() -> None:
    ledger = make_rival_world()
    actions = ledger.review_actions(in_party=False, ts=1000.0)
    assert actions == (Say("Yuri, you are going down"),)
    for action in actions:
        # ANTI-TELEPATHY: the emission exists only as an in-game channel action
        assert isinstance(action, Say | PartyChat | WhisperTo)


def test_review_emits_the_gossip_report_when_crossing_the_threshold() -> None:
    ledger = make_attacked_world()
    assert abs(ledger.group_group_standing("g1", "g2")) >= GOSSIP_REPORT_THRESHOLD
    actions = ledger.review_actions(in_party=False, ts=1000.0)
    assert actions == (Say("careful with Yuri, bad blood there"),)


def test_review_channel_follows_the_party_state() -> None:
    ledger = make_rival_world()
    solo = ledger.review_actions(in_party=False, ts=1000.0)
    party = ledger.review_actions(in_party=True, ts=1000.0 + 10_000.0)
    assert solo
    assert party
    assert isinstance(solo[0], Say)
    assert isinstance(party[0], PartyChat)


def test_review_cadence_gates_repeat_emissions() -> None:
    ledger = make_rival_world()
    first = ledger.review_actions(in_party=False, ts=1000.0)
    assert first
    repeat = ledger.review_actions(in_party=False, ts=1000.0 + 1.0)
    assert repeat == ()


def test_review_silent_without_material_standing() -> None:
    ledger = make_ledger()
    ledger.ingest("y", "obs", "party_session", ts=0.0)
    assert ledger.review_actions(in_party=False, ts=1000.0) == ()


def test_rival_pair_gossip_flows_at_the_multiplier() -> None:
    ledger = make_rival_world()
    plain_shift = -32.5 * GOSSIP_HOP_DECAY * 1.0
    hops = ledger.propagate_gossip(ts=0.0)  # same base ts: no decay yet
    shifted = [shift for hearing, _subject, shift in hops if hearing == "g3"]
    assert shifted
    assert shifted[0] == pytest.approx(plain_shift * RIVAL_GOSSIP_MULTIPLIER)


# -- rivalries ---------------------------------------------------------------


def test_single_guild_creation_selects_no_rival() -> None:
    ledger = make_ledger()
    rivalry = ledger.note_guild_created(
        "guild-001", ("obs",), {"guild-001": ("obs",)}, rng=random.Random(1), ts=0.0
    )
    assert rivalry is None
    assert ledger.rival_of("guild-001") is None


def test_guild_creation_picks_the_worst_aggregate_existing_guild() -> None:
    ledger = make_ledger()
    ledger.register_persona("a", "Ace")
    ledger.register_persona("b", "Bo")
    # the new guild's members hold -18 toward Ace, +5 toward Bo
    ledger.ingest("obs", "a", "attack_groupmate", ts=0.0)
    ledger.ingest("x", "a", "attack_groupmate", ts=0.0)
    ledger.ingest("obs", "b", "invite_accept", ts=0.0)
    rivalry = ledger.note_guild_created(
        "guild-new",
        ("obs", "x"),
        {"guild-ace": ("a",), "guild-bo": ("b",)},
        rng=random.Random(1),
        ts=100.0,
    )
    assert rivalry is not None
    assert rivalry.rival_id == "guild-ace"  # both members attacked: -18 < (+5 + 0) / 2 = +2.5
    assert rivalry.subject_id == "guild-new"
    assert rivalry.origin_score == pytest.approx(-18.0)
    assert rivalry.since_ts == pytest.approx(100.0)
    assert rivalry.seed == random.Random(1).getrandbits(32)
    assert ledger.rival_of("guild-new") == "guild-ace"
    assert ledger.rival_of("guild-ace") == "guild-new"


def test_guild_rival_tie_break_is_seeded_random() -> None:
    def pick(seed: int) -> str:
        ledger = make_ledger()
        rivalry = ledger.note_guild_created(
            "guild-new",
            ("obs",),
            {"guild-a": ("x",), "guild-b": ("y",)},  # equal (no) evidence: a tie
            rng=random.Random(seed),
            ts=0.0,
        )
        assert rivalry is not None
        return rivalry.rival_id

    assert pick(1234) == pick(1234)  # deterministic under a fixed seed
    assert pick(1234) in ("guild-a", "guild-b")


def test_group_rivalry_needs_the_documented_threshold() -> None:
    ledger = make_ledger()
    ledger.ingest("y", "obs", "party_session", ts=0.0)  # strangers/noise: +2
    assert ledger.maybe_form_group_rivalries(ts=0.0) == []
    for _ in range(4):  # sustained negative arc: g1 -> g2 aggregate -36
        ledger.ingest("y", "obs", "attack_groupmate", ts=0.0)
        ledger.ingest("z", "x", "attack_groupmate", ts=0.0)
    formed = ledger.maybe_form_group_rivalries(ts=10.0)
    assert len(formed) == 1
    assert formed[0].subject_id == "g1"
    assert formed[0].rival_id == "g2"
    assert formed[0].origin_score <= RIVALRY_FORMATION_STANDING
    assert ledger.rival_of("g1") == "g2"


def test_existing_rivalry_is_not_duplicated() -> None:
    ledger = make_ledger()
    for _ in range(4):
        ledger.ingest("y", "obs", "attack_groupmate", ts=0.0)
        ledger.ingest("z", "x", "attack_groupmate", ts=0.0)
    first = ledger.maybe_form_group_rivalries(ts=10.0)
    assert first
    assert ledger.maybe_form_group_rivalries(ts=20.0) == []


def test_rival_decide_line_shows_the_worst_standing() -> None:
    ledger = make_rival_world()
    lines = ledger.decide_lines("obs")
    assert any(line.startswith("Rival: g2 (worst standing ") for line in lines)


def test_rivalry_premade_table_and_expansion() -> None:
    assert rivalry_premade("taunt", "Yuri") == "Yuri, you are going down"
    assert rivalry_premade("war", "Yuri") == "war on Yuri! group up"
    assert rivalry_premade("missing", "Yuri") is None


# -- persistence --------------------------------------------------------------


def test_persistence_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "interactions.json"
    ledger = InteractionLedger("obs", path=path)
    ledger.register_persona("obs", "Observer")
    ledger.register_persona("x", "Xavier")
    ledger.register_persona("y", "Yuri")
    ledger.seed_group("g1", ("obs", "x"))
    ledger.seed_group("g2", ("y",))
    ledger.ingest("obs", "x", "party_session", ts=0.0)
    ledger.ingest("obs", "x", "damage_shared", amount=420, ts=0.0)
    ledger.ingest("obs", "y", "rude_chat", ts=0.0)
    ledger.note_guild_created(
        "guild-new",
        ("obs",),
        {"guild-new": ("obs",), "guild-old": ("x",)},
        rng=random.Random(9),
        ts=5.0,
    )
    ledger.save()

    restored = InteractionLedger("obs", path=path)
    assert restored.standing("obs", "x") == pytest.approx(ledger.standing("obs", "x"))
    assert restored.standing("obs", "y") == pytest.approx(-12.0)
    assert restored.decide_lines("obs") == ledger.decide_lines("obs")
    assert restored.rival_of("guild-new") == "guild-old"


def test_restored_ledger_rejects_unknown_schema(tmp_path: Path) -> None:
    path = tmp_path / "interactions.json"
    path.write_text('{"schema": 999}')
    with pytest.raises(ValueError, match=r"unsupported.*schema"):
        InteractionLedger("obs", path=path)


# -- the narrow RelationshipLedger seam ---------------------------------------


def test_relations_seam_positive_feeds_friendship() -> None:
    ledger = RelationshipLedger()
    ledger.ingest_interaction("a", "b", "shared_kill", ts=0.0)
    assert ledger.friendship("a", "b") == pytest.approx(CHAT_AFFINITY_DELTA)
    ledger.ingest_interaction("a", "b", "party_time", seconds=3600.0, ts=1.0)
    assert ledger.friendship("a", "b") == pytest.approx(
        CHAT_AFFINITY_DELTA + PARTY_AFFINITY_PER_HOUR
    )


def test_relations_seam_negative_reduces_friendship() -> None:
    ledger = RelationshipLedger()
    ledger.seed_group("g", ("a", "b"))
    ledger.ingest_interaction("a", "b", "attack_partner", ts=0.0)
    assert ledger.friendship("a", "b") == pytest.approx(0.5 - CHAT_AFFINITY_DELTA)


def test_relations_seam_unknown_kind_raises() -> None:
    ledger = RelationshipLedger()
    with pytest.raises(ValueError, match="unknown interaction kind"):
        ledger.ingest_interaction("a", "b", "kill_steal", ts=0.0)


# -- the live wiring: coordinator review hook, brain chat seam, host build -----


def test_coordinator_review_extends_with_the_interaction_emission() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("me", "MeChar")
    inter = make_rival_world()
    bound = BoundCoordinator(
        GroupCoordinator(ledger, "me"),
        online=lambda: ("me",),
        interactions=inter,
        now=lambda: 1000.0,  # the injected clock keeps the review deterministic
    )
    actions = bound.review_actions(make_state(), base_answers())
    assert any(isinstance(a, Say | PartyChat | WhisperTo) for a in actions)


def test_coordinator_without_interactions_keeps_review_unchanged() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("me", "MeChar")
    bound = BoundCoordinator(GroupCoordinator(ledger, "me"), online=lambda: ("me",))
    assert bound.review_actions(make_state(), base_answers()) == ()


def test_brain_ingests_heard_chat_through_the_seam() -> None:
    ledger = make_ledger()
    seen: list[ChatLine] = []
    model = CapturingModel(base_answers())
    brain = EventDrivenBrain(
        decision_model=model,
        chat=StaticChatGenerator(["gg"]),
        interaction_ingest=seen.append,
    )
    line = ChatLine(channel="public", sender="Xavier", text="noob", at=12.0)
    brain.handle_event(make_state(), ChatHeard(line=line))
    assert seen == [line]
    # the runtime closure resolves the line through the ledger itself:
    assert ledger.ingest_chat(line.sender, line.text, ts=line.at) is True


def test_host_wires_interaction_ledgers_and_the_composed_view(tmp_path: Path) -> None:
    population = make_population()
    host = wiring_host(tmp_path, population)
    try:
        persona = population.personas[0]
        inter = host._interactions[persona.persona_id]
        assert isinstance(inter, InteractionLedger)
        # the roster is injected: display names resolve for ingestion
        mate = population.personas[1]
        assert inter.ingest(persona.persona_id, mate.name, "shared_kill", ts=0.0) is True
        # the decide view is composed: the interaction line rides the social block
        brain = host.agents[persona.persona_id].brain
        assert isinstance(brain, EventDrivenBrain)
        social_view = brain._social_view
        assert social_view is not None
        view = "\n".join(social_view())
        assert f"{mate.name}: +3" in view
        # the brain chat seam is live and the ledger is durable from first start
        assert brain._interaction_ingest is not None
        assert (
            tmp_path / "memory" / "relations" / f"{persona.persona_id}.interactions.json"
        ).exists()
    finally:
        host.stop()
    restored = InteractionLedger(
        persona.persona_id,
        path=tmp_path / "memory" / "relations" / f"{persona.persona_id}.interactions.json",
    )
    assert restored.standing(persona.persona_id, mate.persona_id) == pytest.approx(3.0)


# -- documented constants ------------------------------------------------------


def test_rival_gossip_multiplier_is_documented() -> None:
    assert RIVAL_GOSSIP_MULTIPLIER == 2.0
    assert RIVALRY_FORMATION_STANDING == -15.0
