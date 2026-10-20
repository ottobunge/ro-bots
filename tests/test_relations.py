"""Relationship ledger (criteria 1-2): scores, gossip, decay, formation.

Offline TDD slice for the social scope wiring: per-pair friendship from the
popgen group affinity + shared-party time + chat exchanges, the agent-human
contribution score (+damage/heals/buffs, -dead weight), the group-level
gossip hop (X-group's report of a human reaches the allied Y-group at a
decayed weight), the weekly half-life decay toward neutral, the JSON
persistence in the agent's memory dir, the schedule-overlap party formation
(2+2 popgen personas), the solo drift hints, and the minimal brain-context
hook (the ledger reads into the decide context).
"""

from typing import Any

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.brain import EventDrivenBrain
from robots.domain.actions import AcceptInvite, PartyChat, Say
from robots.domain.events import Heartbeat, InviteReceived
from robots.domain.model import BotState, Goal, PartyInvite
from robots.popgen import GeneratedPopulation, PopulationSpec, generate_population, overlap_fraction
from robots.society.relations import (
    CHAT_AFFINITY_DELTA,
    CONTRIBUTION_UP,
    GOSSIP_HOP_DECAY,
    GOSSIP_THRESHOLD,
    GROUP_AFFINITY_SEED,
    PARTY_AFFINITY_PER_HOUR,
    PARTY_EVENT_PREMADES,
    SOCIAL_CONTEXT_MAX_LINES,
    WEEKLY_HALF_LIFE_S,
    RelationshipLedger,
    party_event_premade,
)
from tests.test_brain import base_answers

# -- helpers -------------------------------------------------------------


def make_state(**overrides: object):
    """A deterministic BotState factory (mirrors tests/conftest.py)."""
    base: dict[str, Any] = {
        "name": "SpikeBot01",
        "job": "Swordsman",
        "base_level": 42,
        "hp": 800,
        "max_hp": 1000,
        "sp": 60,
        "max_sp": 80,
        "map_name": "prt_fild08",
        "x": 120,
        "y": 74,
        "goal": Goal.GRIND,
        "in_party": False,
        "nearby": (),
        "inventory": {"Red Potion": 5},
        "pending_invites": (),
        "recent_chat": (),
    }
    base.update(overrides)
    return BotState(**base)


class CapturingModel:
    """Scripted answers that also record every received request."""

    def __init__(self, answers: dict[str, Any]) -> None:
        self._answers = answers
        self.requests: list[dict[str, Any]] = []

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        return {"answers": dict(self._answers)}


def pop_2_2_1() -> GeneratedPopulation:
    """The acceptance example: two 2-member friend groups + 1 solo, seed 7."""
    return generate_population(
        PopulationSpec(friend_groups=2, friends_per_group=(2, 2), solo_agents=1, seed=7)
    )


# -- ledger scores ---------------------------------------------------------


def test_group_seed_sets_symmetric_friend_floor() -> None:
    ledger = RelationshipLedger()
    ledger.seed_group("pop_g00", ("a", "b"))
    assert ledger.friendship("a", "b") == GROUP_AFFINITY_SEED
    assert ledger.friendship("b", "a") == GROUP_AFFINITY_SEED
    assert ledger.friendship("a", "stranger") == 0.0


def test_party_time_builds_friendship_above_seed() -> None:
    ledger = RelationshipLedger()
    ledger.seed_group("pop_g00", ("a", "b"))
    ledger.record_party_time(["a", "b"], seconds=10 * 3600, ts=0.0)
    expected = GROUP_AFFINITY_SEED + 10 * PARTY_AFFINITY_PER_HOUR
    assert ledger.friendship("a", "b") == pytest.approx(expected)


def test_chat_exchange_nudges_friendship() -> None:
    ledger = RelationshipLedger()
    ledger.record_chat_exchange("a", "b", ts=0.0)
    ledger.record_chat_exchange("a", "b", ts=0.0)
    assert ledger.friendship("a", "b") == pytest.approx(2 * CHAT_AFFINITY_DELTA)


def test_contribution_kinds_move_human_score_up() -> None:
    ledger = RelationshipLedger()
    for kind in ("damage", "heal", "buff"):
        ledger.record_contribution("Trader", kind, ts=0.0)
    assert ledger.human_score("Trader") == pytest.approx(3 * CONTRIBUTION_UP)
    assert ledger.human_score("Nobody") == 0.0


def test_dead_weight_moves_human_score_down_and_clamps() -> None:
    ledger = RelationshipLedger()
    for _ in range(5):
        ledger.record_contribution("Leech", "dead_weight", ts=0.0)
    assert ledger.human_score("Leech") == pytest.approx(-0.5)
    for _ in range(20):
        ledger.record_contribution("Leech", "dead_weight", ts=0.0)
    assert ledger.human_score("Leech") == -1.0


def test_unknown_contribution_kind_rejected() -> None:
    ledger = RelationshipLedger()
    with pytest.raises(ValueError, match="contribution"):
        ledger.record_contribution("Trader", "kill_steal", ts=0.0)


# -- weekly decay ----------------------------------------------------------


def test_weekly_half_life_decays_scores_toward_neutral() -> None:
    ledger = RelationshipLedger()
    ledger.seed_group("pop_g00", ("a", "b"))
    ledger.record_contribution("Trader", "damage", ts=0.0)
    ledger.decay(0.0)
    ledger.decay(WEEKLY_HALF_LIFE_S)
    assert ledger.friendship("a", "b") == pytest.approx(GROUP_AFFINITY_SEED / 2)
    assert ledger.human_score("Trader") == pytest.approx(CONTRIBUTION_UP / 2)


def test_decay_pulls_negative_scores_up_toward_neutral() -> None:
    ledger = RelationshipLedger()
    ledger.record_contribution("Leech", "dead_weight", ts=0.0)
    ledger.decay(0.0)
    ledger.decay(WEEKLY_HALF_LIFE_S)
    assert ledger.human_score("Leech") == pytest.approx(-0.05)


def test_first_decay_sets_baseline_without_change() -> None:
    ledger = RelationshipLedger()
    ledger.seed_group("pop_g00", ("a", "b"))
    ledger.decay(100.0)
    assert ledger.friendship("a", "b") == GROUP_AFFINITY_SEED
    ledger.decay(100.0)  # same instant twice: nothing elapsed
    assert ledger.friendship("a", "b") == GROUP_AFFINITY_SEED


def test_timestamped_records_decay_first() -> None:
    ledger = RelationshipLedger()
    ledger.record_contribution("Trader", "damage", ts=0.0)
    ledger.record_contribution("Trader", "damage", ts=WEEKLY_HALF_LIFE_S)
    assert ledger.human_score("Trader") == pytest.approx(CONTRIBUTION_UP / 2 + CONTRIBUTION_UP)


# -- gossip hop ------------------------------------------------------------


def test_report_moves_own_scores() -> None:
    ledger = RelationshipLedger()
    ledger.seed_group("pop_g00", ("x1", "x2"))
    hops = ledger.report_human("Griefer", -0.8, group_id="pop_g00", ts=0.0)
    assert hops == []
    assert ledger.human_score("Griefer") == pytest.approx(-0.8)
    assert ledger.group_reputation("pop_g00", "Griefer") == pytest.approx(-0.8)


def test_gossip_hop_reaches_allied_group_decayed() -> None:
    ledger = RelationshipLedger()
    ledger.seed_group("pop_g00", ("x1", "x2"))
    ledger.seed_group("pop_g01", ("y1", "y2"))
    # The alliance: shared party time across the two groups.
    ledger.record_party_time(["x1", "y1"], seconds=5 * 3600, ts=0.0)
    ledger.record_party_time(["x2", "y2"], seconds=5 * 3600, ts=0.0)
    hops = ledger.report_human("Griefer", -0.8, group_id="pop_g00", ts=0.0)
    mean_cross = 5 * PARTY_AFFINITY_PER_HOUR
    expected = -0.8 * GOSSIP_HOP_DECAY * (0.5 + 0.5 * mean_cross)
    assert len(hops) == 1
    hop_group, hop_shift = hops[0]
    assert hop_group == "pop_g01"
    assert hop_shift == pytest.approx(expected)
    assert ledger.group_reputation("pop_g01", "Griefer") == pytest.approx(expected)
    # The reporter's own rows carry the full weight.
    assert ledger.group_reputation("pop_g00", "Griefer") == pytest.approx(-0.8)


def test_small_delta_stays_local() -> None:
    ledger = RelationshipLedger()
    ledger.seed_group("pop_g00", ("x1", "x2"))
    ledger.seed_group("pop_g01", ("y1", "y2"))
    ledger.record_party_time(["x1", "y1"], seconds=5 * 3600, ts=0.0)
    hops = ledger.report_human("Trader", -GOSSIP_THRESHOLD / 2, group_id="pop_g00", ts=0.0)
    assert hops == []
    assert ledger.group_reputation("pop_g01", "Trader") == 0.0
    assert ledger.human_score("Trader") == pytest.approx(-GOSSIP_THRESHOLD / 2)


def test_no_allies_no_gossip() -> None:
    ledger = RelationshipLedger()
    ledger.seed_group("pop_g00", ("x1", "x2"))
    ledger.seed_group("pop_g01", ("y1", "y2"))  # no cross edges: not allied
    hops = ledger.report_human("Griefer", -0.8, group_id="pop_g00", ts=0.0)
    assert hops == []
    assert ledger.group_reputation("pop_g01", "Griefer") == 0.0


# -- persistence ------------------------------------------------------------


def _rich_ledger() -> RelationshipLedger:
    ledger = RelationshipLedger(persona_id="x1")
    ledger.register_persona("x1", "Poringnyan")
    ledger.register_persona("y1", "Zenywind")
    ledger.seed_group("pop_g00", ("x1", "x2"), save_map="prontera")
    ledger.seed_group("pop_g01", ("y1", "y2"), save_map="gef_fild07")
    ledger.record_party_time(["x1", "x2"], seconds=3 * 3600, ts=0.0)
    ledger.record_chat_exchange("x1", "y1", ts=0.0)
    ledger.record_contribution("Trader", "damage", ts=0.0)
    ledger.record_contribution("Leech", "dead_weight", ts=0.0)
    ledger.report_human("Griefer", -0.8, group_id="pop_g00", ts=0.0)
    return ledger


def test_dict_round_trip_preserves_all_state() -> None:
    ledger = _rich_ledger()
    restored = RelationshipLedger.from_dict(ledger.to_dict())
    assert restored.to_dict() == ledger.to_dict()
    assert restored.friendship("x1", "x2") == pytest.approx(ledger.friendship("x1", "x2"))
    assert restored.human_score("Trader") == pytest.approx(ledger.human_score("Trader"))
    assert restored.group_reputation("pop_g01", "Griefer") == pytest.approx(
        ledger.group_reputation("pop_g01", "Griefer")
    )
    assert restored.group_members("pop_g00") == ("x1", "x2")
    assert restored.group_of("y1") == "pop_g01"
    assert restored.group_map("pop_g01") == "gef_fild07"


def test_file_round_trip_reconnect_continuity(tmp_path) -> None:
    path = tmp_path / "relations.json"
    _rich_ledger().save(path)
    restored = RelationshipLedger(path=path)
    assert restored.friendship("x1", "x2") == pytest.approx(
        GROUP_AFFINITY_SEED + 3 * PARTY_AFFINITY_PER_HOUR
    )
    assert restored.human_score("Griefer") == pytest.approx(-0.8)
    # A fresh agent with no saved file starts empty, not broken.
    fresh = RelationshipLedger(path=tmp_path / "missing.json")
    assert fresh.human_score("Griefer") == 0.0


def test_restore_rejects_unknown_schema() -> None:
    with pytest.raises(ValueError, match="schema"):
        RelationshipLedger.from_dict({"schema": 99})
    with pytest.raises(ValueError, match="pair"):
        RelationshipLedger.from_dict({"schema": 1, "friendship": {"just-a": 0.5}})


# -- schedule-overlap party formation (popgen 2+2, seed 7) ------------------


def test_same_group_schedules_overlap_and_formation_pairs_them() -> None:
    pop = pop_2_2_1()
    by_group: dict[str, list[str]] = {}
    solo_ids: list[str] = []
    for persona in pop.personas:
        if persona.group_id is None:
            solo_ids.append(persona.persona_id)
        else:
            by_group.setdefault(persona.group_id, []).append(persona.persona_id)
    ledger = RelationshipLedger()
    for group_id, members in by_group.items():
        ledger.seed_group(group_id, members)
    plans = ledger.party_formation([p.persona_id for p in pop.personas])
    # Both groups form; the solo is nobody's invitee.
    assert [(plan.leader_id, plan.invitee_ids) for plan in plans] == [
        (by_group[g][0], tuple(by_group[g][1:])) for g in sorted(by_group)
    ]
    invited = {m for plan in plans for m in (plan.leader_id, *plan.invitee_ids)}
    assert not invited & set(solo_ids)
    # The formation rests on the popgen guarantee: same-group schedules overlap.
    members = by_group[next(iter(by_group))]
    first, second = (p for p in pop.personas if p.persona_id in members[:2])
    assert overlap_fraction(first.schedule, second.schedule) >= 0.5


def test_formation_excludes_cross_group_strangers_and_solos() -> None:
    pop = pop_2_2_1()
    by_group: dict[str, list[str]] = {}
    solo_ids: list[str] = []
    for persona in pop.personas:
        if persona.group_id is None:
            solo_ids.append(persona.persona_id)
        else:
            by_group.setdefault(persona.group_id, []).append(persona.persona_id)
    ledger = RelationshipLedger()
    for group_id, members in by_group.items():
        ledger.seed_group(group_id, members)
    # One member per group online: no same-group pair, no plan at all.
    one_each = [by_group[g][0] for g in sorted(by_group)]
    assert ledger.party_formation(one_each) == []
    # A lone solo never forms a party.
    assert ledger.party_formation([solo_ids[0]]) == []


# -- brain context hook ------------------------------------------------------


def test_brain_without_social_view_keeps_legacy_schema() -> None:
    model = CapturingModel(base_answers())
    brain = EventDrivenBrain(decision_model=model, chat=StaticChatGenerator(["gg"]))
    brain.handle_event(make_state(), Heartbeat(seq=1))
    assert "social_relations" not in model.requests[0]["state"]


def test_brain_injects_social_view_into_decide_context() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("f1", "Ponyta")
    ledger.record_party_time(["f1", "me"], seconds=5 * 3600, ts=0.0)
    model = CapturingModel(base_answers())
    brain = EventDrivenBrain(
        decision_model=model,
        chat=StaticChatGenerator(["gg"]),
        social_view=lambda: ledger.context_lines("me"),
    )
    brain.handle_event(make_state(), Heartbeat(seq=1))
    relations = model.requests[0]["state"]["social_relations"]
    assert "Ponyta +0.20" in relations


def test_brain_bounds_social_view_lines() -> None:
    ledger = RelationshipLedger()
    for i in range(20):
        ledger.register_persona(f"p{i:02d}", f"Peer{i:02d}")
        ledger.record_chat_exchange(f"p{i:02d}", "me", ts=0.0)
    model = CapturingModel(base_answers())
    brain = EventDrivenBrain(
        decision_model=model,
        chat=StaticChatGenerator(["gg"]),
        social_view=lambda: ledger.context_lines("me", max_lines=20),
    )
    brain.handle_event(make_state(), Heartbeat(seq=1))
    relations = model.requests[0]["state"]["social_relations"]
    assert len(relations.splitlines()) == SOCIAL_CONTEXT_MAX_LINES


# -- accept/decline by affinity ----------------------------------------------


def test_invite_from_friend_context_and_accept() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("pl1", "PartyLeader")
    ledger.record_party_time(["pl1", "me"], seconds=2 * 3600, ts=0.0)
    answers = base_answers()
    answers["accept_invite"] = {"type": "noul", "noul": 0.9}
    model = CapturingModel(answers)
    brain = EventDrivenBrain(
        decision_model=model,
        chat=StaticChatGenerator(["gg"]),
        social_view=lambda: ledger.context_lines("me"),
    )
    state = make_state(pending_invites=(PartyInvite(from_name="PartyLeader", at=2.0),))
    result = brain.handle_event(
        state, InviteReceived(invite=PartyInvite(from_name="PartyLeader", at=2.0))
    )
    relations = model.requests[0]["state"]["social_relations"]
    assert "PartyLeader +0.08" in relations  # the affinity fact reaches the model
    assert any(isinstance(a, AcceptInvite) for a in result.actions)


def test_invite_from_stranger_no_context_no_accept() -> None:
    ledger = RelationshipLedger()  # nothing known about PartyLeader
    answers = base_answers()  # accept_invite noul 0.0 -> decline
    model = CapturingModel(answers)
    brain = EventDrivenBrain(
        decision_model=model,
        chat=StaticChatGenerator(["gg"]),
        social_view=lambda: ledger.context_lines("me"),
    )
    result = brain.handle_event(
        make_state(pending_invites=(PartyInvite(from_name="PartyLeader", at=2.0),)),
        InviteReceived(invite=PartyInvite(from_name="PartyLeader", at=2.0)),
    )
    relations = model.requests[0]["state"].get("social_relations", "")
    assert "PartyLeader" not in relations
    assert result.actions == ()


# -- premade selection by event ------------------------------------------------


def test_party_event_premade_table_keys() -> None:
    assert set(PARTY_EVENT_PREMADES) == {
        "party_joined",
        "party_left",
        "level_up",
        "seeking_party",
        "need_buffs",
    }
    assert party_event_premade("party_joined") == "Hi all!"
    assert party_event_premade("party_left") == "gg wp"
    level_up = party_event_premade("level_up")
    assert level_up is not None
    assert "%level" in level_up
    seeking = party_event_premade("seeking_party")
    assert seeking is not None
    assert "%job" in seeking
    assert party_event_premade("need_buffs") == "Buffs please!"


def test_unknown_party_event_has_no_premade() -> None:
    assert party_event_premade("wedding") is None


def test_brain_emits_party_joined_premade_on_urgency() -> None:
    answers = [base_answers(), base_answers(), base_answers()]
    answers[2]["chat_urgency"] = {"type": "score", "score": 2.0}
    brain = EventDrivenBrain(
        decision_model=ScriptedDecisionModel(queue=answers), chat=StaticChatGenerator(["gg"])
    )
    brain.start(make_state())
    brain.handle_event(make_state(), InviteReceived(invite=PartyInvite(from_name="Leader", at=1.0)))
    result = brain.handle_event(make_state(in_party=True), Heartbeat(seq=2))
    chats = [a for a in result.actions if isinstance(a, PartyChat)]
    assert [c.text for c in chats] == ["Hi all!"]
    assert any("party-event" in note for note in result.notes)
    assert result.escalated is False


def test_brain_holds_party_chat_when_urgency_low() -> None:
    answers = [base_answers(), base_answers(), base_answers()]  # chat_urgency 0.5
    brain = EventDrivenBrain(
        decision_model=ScriptedDecisionModel(queue=answers), chat=StaticChatGenerator(["gg"])
    )
    brain.start(make_state())
    brain.handle_event(make_state(), InviteReceived(invite=PartyInvite(from_name="Leader", at=1.0)))
    result = brain.handle_event(make_state(in_party=True), Heartbeat(seq=2))
    assert not [a for a in result.actions if isinstance(a, (PartyChat, Say))]


def test_brain_announces_level_up_publicly() -> None:
    answers = [base_answers(), base_answers()]
    answers[1]["chat_urgency"] = {"type": "score", "score": 2.0}
    brain = EventDrivenBrain(
        decision_model=ScriptedDecisionModel(queue=answers), chat=StaticChatGenerator(["gg"])
    )
    brain.start(make_state())
    result = brain.handle_event(make_state(base_level=43), Heartbeat(seq=1))
    says = [a for a in result.actions if isinstance(a, Say)]
    assert [s.text for s in says] == ["Level up! 43"]


def test_brain_says_goodbye_when_party_left() -> None:
    answers = [base_answers(), base_answers()]
    answers[1]["chat_urgency"] = {"type": "score", "score": 2.0}
    brain = EventDrivenBrain(
        decision_model=ScriptedDecisionModel(queue=answers), chat=StaticChatGenerator(["gg"])
    )
    brain.start(make_state(in_party=True))
    result = brain.handle_event(make_state(in_party=False), Heartbeat(seq=1))
    says = [a for a in result.actions if isinstance(a, Say)]
    assert [s.text for s in says] == ["gg wp"]


# -- solo drift ----------------------------------------------------------------


def test_solo_drift_hints_name_active_groups() -> None:
    ledger = RelationshipLedger()
    ledger.seed_group("pop_g01", ("y1", "y2"), save_map="gef_fild07")
    ledger.register_persona("s00", "Lorawing")
    lines = ledger.context_lines("s00", active_group_ids=["pop_g01"])
    drift = [line for line in lines if "drift" in line]
    assert len(drift) == 1
    assert "pop_g01" in drift[0]
    assert "gef_fild07" in drift[0]
    assert "2 members" in drift[0]


def test_group_member_context_has_no_drift() -> None:
    ledger = RelationshipLedger()
    ledger.seed_group("pop_g00", ("a", "b"), save_map="prontera")
    ledger.seed_group("pop_g01", ("y1", "y2"), save_map="gef_fild07")
    lines = ledger.context_lines("a", active_group_ids=["pop_g01"])
    assert not any("drift" in line for line in lines)
    assert any("your group pop_g00" in line for line in lines)


def test_no_active_groups_no_drift_lines() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("s00", "Lorawing")
    assert ledger.context_lines("s00") == []
    assert ledger.context_lines("s00", active_group_ids=[]) == []
