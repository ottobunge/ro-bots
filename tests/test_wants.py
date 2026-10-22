"""Wants-system tests: decay tables, satisfaction map, decide block, roll.

All offline per the design (docs/wants-design.md): pure WantState math plus
brain/runtime wiring tests over scripted/stub models. The design tables are
the authority — the personality rows and satisfaction amounts here are copied
from the doc, not invented.
"""

import random
from typing import Any

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.app.agent_runtime import ScheduledAgent
from robots.app.brain import EventDrivenBrain
from robots.domain.events import ChatHeard, Heartbeat, InviteReceived, MonsterSpotted
from robots.domain.model import ActorRef, ChatLine, PartyInvite
from robots.society.models import Attitude, Playstyle, SocietyPersona
from robots.society.society import SocietyRoster
from robots.society.wants import (
    BASE_DECAY_PER_HOUR,
    PERSONALITY_PROFILES,
    Personality,
    Want,
    WantEvent,
    WantSatisfier,
    WantState,
    assign_personalities,
)
from tests.conftest import make_state

# -- helpers -------------------------------------------------------------


class RecordingModel:
    """Decide stub that records every request (offline; no network)."""

    def __init__(self, answers: dict[str, Any]) -> None:
        self._answers = answers
        self.requests: list[dict[str, Any]] = []

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        return {"answers": dict(self._answers)}


def brain_answers() -> dict[str, Any]:
    return {
        "next_action": {"type": "choice", "choice": "grind", "confidence": 0.9},
        "target_choice": {"type": "choice", "choice": "closest", "confidence": 0.9},
        "should_reply": {"type": "noul", "noul": 0.1},
        "hp_critical": {"type": "noul", "noul": 0.05},
        "threat_near": {"type": "noul", "noul": 0.2},
        "accept_invite": {"type": "noul", "noul": 0.0},
        "use_premade": {"type": "noul", "noul": 0.0},
        "premade_pick": {"type": "choice", "choice": "none", "confidence": 0.9},
        "chat_urgency": {"type": "score", "score": 0.5},
        "goal_review": {"type": "score", "score": 1.0},
        "change_goal": {"type": "choice", "choice": "keep", "confidence": 0.9},
        "react_monster": {"type": "choice", "choice": "ignore", "confidence": 0.9},
        "react_damage": {"type": "choice", "choice": "keep", "confidence": 0.9},
        "farm_duration": {"type": "score", "score": 1.0},
        "farm_target": {"type": "choice", "choice": "Poring", "confidence": 0.9},
    }


def make_brain(
    answers: dict[str, Any] | None = None, **kwargs: Any
) -> tuple[EventDrivenBrain, RecordingModel]:
    model = RecordingModel(answers or brain_answers())
    return EventDrivenBrain(decision_model=model, chat=StaticChatGenerator(["gg"]), **kwargs), model


def grind_state(**overrides: Any) -> Any:
    return make_state(**overrides)


def heard(sender: str = "NyxSong", text: str = "anyone partying?") -> ChatHeard:
    return ChatHeard(line=ChatLine(channel="public", sender=sender, text=text, at=1.0))


def fresh(personality: Personality = Personality.ACHIEVER, **kwargs: Any) -> WantState:
    return WantState(personality, **kwargs)


# -- the design's personality table -----------------------------------------


def test_all_six_personalities_present() -> None:
    assert set(PERSONALITY_PROFILES) == set(Personality)


def test_design_multiplier_rows() -> None:
    """Copy of the design table: 9 multipliers + roster cap + create factor."""
    expected: dict[Personality, tuple[float, ...]] = {
        Personality.ACHIEVER: (2.0, 1.2, 1.3, 0.6, 0.8, 0.5, 1.5, 0.7, 1.0, 4, 0.6),
        Personality.SOCIALIZER: (0.5, 0.7, 0.8, 2.0, 1.0, 1.2, 0.6, 2.0, 1.4, 6, 1.2),
        Personality.EXPLORER: (1.0, 0.8, 1.0, 0.8, 2.0, 0.4, 1.2, 0.9, 1.3, 5, 1.0),
        Personality.TYCOON: (0.8, 2.0, 1.5, 0.7, 1.2, 0.8, 0.9, 0.8, 0.9, 4, 0.5),
        Personality.CASUAL: (0.4, 0.6, 0.7, 1.2, 1.5, 2.0, 0.5, 1.1, 1.2, 6, 1.1),
        Personality.COMPETITOR: (1.5, 1.0, 1.1, 0.9, 0.9, 0.3, 2.0, 0.8, 0.8, 5, 0.7),
    }
    order = (
        Want.POWER,
        Want.WEALTH,
        Want.EQUIPMENT,
        Want.SOCIAL,
        Want.NOVELTY,
        Want.COMFORT,
        Want.COMPETENCE,
        Want.FRIENDSHIP,
        Want.CHAR_SWITCH,
    )
    for personality, row in expected.items():
        profile = PERSONALITY_PROFILES[personality]
        assert tuple(profile.multipliers[w] for w in order) == row[:9]
        assert profile.char_cap == row[9]
        assert profile.create_factor == row[10]


def test_base_decay_rates_match_design() -> None:
    rates = {w: BASE_DECAY_PER_HOUR[w] for w in Want}
    assert rates == {
        Want.POWER: 6.0,
        Want.WEALTH: 4.0,
        Want.EQUIPMENT: 3.0,
        Want.SOCIAL: 5.0,
        Want.NOVELTY: 4.0,
        Want.COMFORT: 3.0,
        Want.COMPETENCE: 4.0,
        Want.FRIENDSHIP: 2.0,
        Want.CHAR_SWITCH: 1.0,
    }


def test_assign_personalities_mixes_friend_groups() -> None:
    """Design section 3: friend groups mix personalities (>=2 per group)."""
    for seed in range(12):
        drawn = assign_personalities(random.Random(seed), 4)
        assert len(set(drawn)) >= 2, f"seed {seed} drew a uniform group"


def test_assign_personalities_single_and_deterministic() -> None:
    solo = assign_personalities(random.Random(3), 1)
    assert len(solo) == 1
    assert isinstance(solo[0], Personality)
    assert assign_personalities(random.Random(3), 1) == solo


# -- decay -------------------------------------------------------------------


def test_online_decay_uses_personality_multiplier() -> None:
    ws = fresh(Personality.ACHIEVER)
    ws.decay(1.0)
    assert ws.scores[Want.POWER] == pytest.approx(50.0 - 6.0 * 2.0)
    assert ws.scores[Want.SOCIAL] == pytest.approx(50.0 - 5.0 * 0.6)
    assert ws.scores[Want.CHAR_SWITCH] == pytest.approx(50.0 - 1.0 * 1.0)


def test_offline_decay_at_quarter_rate() -> None:
    ws = fresh(Personality.ACHIEVER)
    ws.decay(0.0, offline_hours=2.0)
    assert ws.scores[Want.POWER] == pytest.approx(50.0 - 6.0 * 2.0 * 0.25 * 2.0)
    assert ws.scores[Want.CHAR_SWITCH] == pytest.approx(50.0 - 1.0 * 0.25 * 2.0)


def test_decay_clamps_at_zero() -> None:
    ws = fresh(Personality.ACHIEVER, scores={Want.POWER: 5.0})
    ws.decay(1.0)
    assert ws.scores[Want.POWER] == 0.0


def test_session_itch_beyond_second_hour() -> None:
    """+2/h per full session hour beyond the second (design section 2)."""
    ws = fresh(Personality.SOCIALIZER)
    ws.decay(3.0)  # one full hour beyond the second
    assert ws.scores[Want.CHAR_SWITCH] == pytest.approx(50.0 - 1.4 * (3.0 + 2.0 * 1))
    ws.decay(2.0)  # session 3h -> 5h: two more full hours beyond the second
    assert ws.scores[Want.CHAR_SWITCH] == pytest.approx(
        50.0 - 1.4 * (3.0 + 2.0) - 1.4 * (2.0 + 2.0 * 2)
    )


def test_group_new_itch() -> None:
    ws = fresh(Personality.SOCIALIZER, group_is_new=True)
    ws.decay(1.0)
    assert ws.scores[Want.CHAR_SWITCH] == pytest.approx(50.0 - (1.0 + 5.0) * 1.4)


def test_grass_is_greener_itch() -> None:
    ws = fresh(Personality.ACHIEVER, current_level=42, other_char_levels=(45,))
    assert ws.grass_is_greener()
    ws.decay(1.0)
    assert ws.scores[Want.CHAR_SWITCH] == pytest.approx(50.0 - (1.0 + 2.0) * 1.0)
    far = fresh(Personality.ACHIEVER, current_level=42, other_char_levels=(90,))
    assert not far.grass_is_greener()


def test_friend_announce_is_a_one_shot_itch() -> None:
    ws = fresh(Personality.ACHIEVER)
    ws.note_friend_switch_announce()
    assert ws.scores[Want.CHAR_SWITCH] == pytest.approx(53.0)


def test_negative_hours_rejected() -> None:
    ws = fresh()
    with pytest.raises(ValueError, match="hours"):
        ws.decay(-1.0)


# -- satisfy -----------------------------------------------------------------


def test_satisfy_clamps_to_0_100() -> None:
    ws = fresh()
    ws.satisfy(Want.POWER, 60.0, "test high")
    assert ws.scores[Want.POWER] == 100.0
    ws.satisfy(Want.WEALTH, -80.0, "test low")
    assert ws.scores[Want.WEALTH] == 0.0


def test_satisfy_records_reason() -> None:
    ws = fresh()
    ws.satisfy(Want.POWER, 1.0, "killed a Poring")
    assert ("Power", 1.0, "killed a Poring") in ws.reasons


# -- the event -> satisfaction map ------------------------------------------


@pytest.fixture
def ws() -> WantState:
    return fresh(Personality.ACHIEVER)


def apply(kind: str, state: WantState, **facts: Any) -> None:
    WantSatisfier.apply(state, WantEvent(kind, **facts))


def test_kill_satisfies_power_and_competence(ws: WantState) -> None:
    apply("kill", ws)
    assert ws.scores[Want.POWER] == pytest.approx(51.0)
    apply("kill", ws, higher_level=True)
    assert ws.scores[Want.POWER] == pytest.approx(54.0)
    apply("kill", ws, solo=True)
    assert ws.scores[Want.COMPETENCE] == pytest.approx(52.0)
    apply("kill", ws, solo=True, level_gap=7)
    assert ws.scores[Want.COMPETENCE] == pytest.approx(64.0)  # solo +2 stacks with +10


def test_level_up_and_quests_satisfy_power(ws: WantState) -> None:
    apply("level_up", ws)
    assert ws.scores[Want.POWER] == pytest.approx(75.0)
    apply("quest_turn_in", ws)
    assert ws.scores[Want.POWER] == pytest.approx(95.0)
    apply("quest_new", ws)
    assert ws.scores[Want.NOVELTY] == pytest.approx(65.0)


def test_economy_events(ws: WantState) -> None:
    apply("sell", ws, zeny=250)
    assert ws.scores[Want.WEALTH] == pytest.approx(75.0)  # +1 per 10 zeny
    apply("buy", ws)
    assert ws.scores[Want.WEALTH] == pytest.approx(65.0)
    apply("loot_valuable", ws)
    assert ws.scores[Want.WEALTH] == pytest.approx(67.0)
    apply("loot_wanted", ws)
    assert ws.scores[Want.EQUIPMENT] == pytest.approx(58.0)
    apply("equip_planned", ws)
    assert ws.scores[Want.EQUIPMENT] == pytest.approx(78.0)
    apply("budget_tier", ws)
    assert ws.scores[Want.EQUIPMENT] == pytest.approx(88.0)
    apply("buy_failed", ws)
    assert ws.scores[Want.EQUIPMENT] == pytest.approx(83.0)
    apply("quest_reward", ws)
    assert ws.scores[Want.WEALTH] == pytest.approx(77.0)


def test_social_events(ws: WantState) -> None:
    ws.partyless_hours = 3.0
    apply("party_join", ws)
    assert ws.scores[Want.SOCIAL] == pytest.approx(65.0)
    assert ws.partyless_hours == 0.0
    apply("invite_received", ws)
    assert ws.scores[Want.SOCIAL] == pytest.approx(73.0)
    apply("chat_exchange", ws)
    assert ws.scores[Want.SOCIAL] == pytest.approx(76.0)
    apply("buff_friend", ws)
    assert ws.scores[Want.SOCIAL] == pytest.approx(80.0)
    apply("group_objective", ws)
    assert ws.scores[Want.SOCIAL] == pytest.approx(85.0)


def test_death_hits_four_wants(ws: WantState) -> None:
    apply("death", ws)
    assert ws.scores[Want.COMFORT] == pytest.approx(25.0)
    assert ws.scores[Want.WEALTH] == pytest.approx(45.0)
    assert ws.scores[Want.EQUIPMENT] == pytest.approx(46.0)
    assert ws.scores[Want.COMPETENCE] == pytest.approx(35.0)


def test_novelty_first_seen_only(ws: WantState) -> None:
    apply("map_change", ws, name="prt_fild08")
    assert ws.scores[Want.NOVELTY] == pytest.approx(62.0)
    apply("map_change", ws, name="prt_fild08")
    assert ws.scores[Want.NOVELTY] == pytest.approx(62.0)
    apply("map_change", ws, name="gef_fild07")
    assert ws.scores[Want.NOVELTY] == pytest.approx(74.0)
    apply("new_species", ws, name="Poring")
    assert ws.scores[Want.NOVELTY] == pytest.approx(80.0)
    apply("new_species", ws, name="Poring")
    assert ws.scores[Want.NOVELTY] == pytest.approx(80.0)
    apply("activity_change", ws)
    assert ws.scores[Want.NOVELTY] == pytest.approx(84.0)


def test_comfort_events(ws: WantState) -> None:
    apply("rest_town", ws)
    assert ws.scores[Want.COMFORT] == pytest.approx(52.0)
    apply("kafra_rest", ws)
    assert ws.scores[Want.COMFORT] == pytest.approx(62.0)
    apply("safe_activity", ws)
    assert ws.scores[Want.COMFORT] == pytest.approx(63.0)
    apply("hp_low", ws)
    assert ws.scores[Want.COMFORT] == pytest.approx(60.0)


def test_friendship_events(ws: WantState) -> None:
    apply("friend_copresence", ws)
    assert ws.scores[Want.FRIENDSHIP] == pytest.approx(51.0)
    apply("friend_joint_kill", ws)
    assert ws.scores[Want.FRIENDSHIP] == pytest.approx(53.0)
    apply("friend_party", ws)
    assert ws.scores[Want.FRIENDSHIP] == pytest.approx(57.0)
    apply("friend_gift", ws)
    assert ws.scores[Want.FRIENDSHIP] == pytest.approx(63.0)


def test_char_switch_satisfied_only_by_roster_moves(ws: WantState) -> None:
    apply("roster_switch", ws)
    assert ws.scores[Want.CHAR_SWITCH] == 100.0  # clamped, like every want
    ws2 = fresh()
    apply("character_created", ws2)
    assert ws2.scores[Want.CHAR_SWITCH] == 100.0


def test_unknown_event_kind_raises(ws: WantState) -> None:
    with pytest.raises(ValueError, match="bogus"):
        WantSatisfier.apply(ws, WantEvent("bogus"))


# -- top_want and the decide block ------------------------------------------


def socializer_block_state() -> WantState:
    return fresh(
        Personality.SOCIALIZER,
        scores={
            Want.POWER: 34.0,
            Want.WEALTH: 12.0,
            Want.EQUIPMENT: 90.0,
            Want.SOCIAL: 71.0,
            Want.NOVELTY: 55.0,
            Want.COMFORT: 82.0,
            Want.COMPETENCE: 95.0,
            Want.FRIENDSHIP: 100.0,
            Want.CHAR_SWITCH: 44.0,
        },
        partyless_hours=2.0,
        online_friends=("NyxSong", "RinceNyan"),
        group_is_new=True,
    )


def test_top_want_uses_score_times_decay_pressure() -> None:
    """Design section 4: highest urgency = lowest score x decay pressure."""
    ws = fresh(Personality.ACHIEVER)
    ws.scores.update({Want.SOCIAL: 20.0})  # 20*5*0.6=60 beats friendship's 70
    want, score = ws.top_want()
    assert want is Want.SOCIAL
    assert score == pytest.approx(20.0)
    ws.scores.update({Want.SOCIAL: 40.0, Want.FRIENDSHIP: 30.0})  # 30*1.4=42 lowest
    want, score = ws.top_want()
    assert want is Want.FRIENDSHIP
    assert score == pytest.approx(30.0)


def test_top_wants_orders_by_urgency(ws: WantState) -> None:
    ranked = [want for want, _ in ws.top_wants(3)]
    assert len(ranked) == 3
    assert len(set(ranked)) == 3
    assert ws.top_want()[0] == ranked[0]


def test_decide_block_format() -> None:
    ws = socializer_block_state()
    block = ws.decide_block()
    lines = block.splitlines()
    assert lines[0] == ("wants: Wealth 12→ Power 34→ Novelty 55→ Social 71→ Comfort 82→")
    assert lines[1] == ("top_want: Wealth 12 (partyless for 2h; friends NyxSong+RinceNyan online)")
    assert lines[2] == ("char_switch_itch: 44 (group is new: no member >= level 30)")
    assert len(lines) == 3


def test_decide_block_omits_group_note_when_not_new() -> None:
    ws = socializer_block_state()
    ws.group_is_new = False
    assert ws.decide_block().splitlines()[2] == "char_switch_itch: 44"


def test_decide_block_stays_under_150_tokens() -> None:
    ws = socializer_block_state()
    ws.decay(2.0)
    block = ws.decide_block()
    # crude token proxy: whitespace words; the design budgets <=150 tokens
    assert len(block.split()) <= 150


def test_decide_block_arrows_track_decay() -> None:
    ws = fresh(Personality.ACHIEVER, scores={Want.WEALTH: 0.0})
    ws.group_is_new = True
    ws.decay(1.0)
    block = ws.decide_block()
    assert "Wealth 0→" in block, "a clamped-at-zero want shows no decay arrow"
    assert "↓↓" in block, "the boosted itch shows the fast-decay arrow"
    assert "Social" not in block.splitlines()[0], "only the 5 lowest-score wants show"


# -- the char-switch creation roll ------------------------------------------


class ScriptedRng:
    """A deterministic stand-in for random.Random (one scripted draw)."""

    def __init__(self, value: float) -> None:
        self.value = value

    def random(self) -> float:
        return self.value


def test_roll_requires_itch_above_80(ws: WantState) -> None:
    assert ws.roll_character_choice(ScriptedRng(0.0)) == "none"
    assert ws.creation_probability() == 0.0


def test_roll_vanishing_probability_math() -> None:
    ws = fresh(Personality.SOCIALIZER, roster_size=1)
    ws.scores[Want.CHAR_SWITCH] = 85.0
    # p = 0.10 * 1.2 * (1 - 1/6) = 0.10
    assert ws.creation_probability() == pytest.approx(0.10)
    assert ws.roll_character_choice(ScriptedRng(0.05)) == "create"
    assert ws.roll_character_choice(ScriptedRng(0.5)) == "switch"


def test_roll_never_creates_at_the_roster_cap() -> None:
    ws = fresh(Personality.SOCIALIZER, roster_size=6)
    ws.scores[Want.CHAR_SWITCH] = 100.0
    assert ws.creation_probability() == 0.0
    assert ws.roll_character_choice(ScriptedRng(0.0)) == "switch"
    for seed in range(20):
        assert ws.roll_character_choice(random.Random(seed)) == "switch"


# -- brain wiring ------------------------------------------------------------


def test_decide_payload_carries_the_want_block() -> None:
    ws = fresh()
    brain, model = make_brain(wants=ws)
    brain.handle_event(grind_state(), heard())
    request = model.requests[-1]
    assert request["state"]["wants"] == ws.decide_block()


def test_no_want_block_without_a_want_state() -> None:
    brain, model = make_brain()
    brain.handle_event(grind_state(), heard())
    assert "wants" not in model.requests[-1]["state"]


def test_party_chat_exchange_satisfies_social() -> None:
    ws = fresh()
    brain, _ = make_brain(wants=ws)
    brain.handle_event(grind_state(in_party=True), heard())
    assert ws.scores[Want.SOCIAL] == pytest.approx(53.0)


def test_chat_outside_party_is_not_an_exchange() -> None:
    ws = fresh()
    brain, _ = make_brain(wants=ws)
    brain.handle_event(grind_state(in_party=False), heard())
    assert ws.scores[Want.SOCIAL] == pytest.approx(50.0)


def test_invite_received_satisfies_social() -> None:
    ws = fresh()
    brain, _ = make_brain(wants=ws)
    invite = InviteReceived(invite=PartyInvite(from_name="Leader", at=1.0))
    brain.handle_event(grind_state(), invite)
    assert ws.scores[Want.SOCIAL] == pytest.approx(58.0)


def test_new_species_spotted_satisfies_novelty() -> None:
    ws = fresh()
    brain, _ = make_brain(wants=ws)
    spot = MonsterSpotted(actor=ActorRef(id=9, name="Poring", kind="monster", distance=3.0))
    brain.handle_event(grind_state(), spot)
    brain.handle_event(grind_state(), spot)
    assert ws.scores[Want.NOVELTY] == pytest.approx(56.0)


def test_level_up_diff_satisfies_power() -> None:
    ws = fresh()
    brain, _ = make_brain(wants=ws)
    brain.handle_event(grind_state(base_level=42), Heartbeat(seq=0))
    brain.handle_event(grind_state(base_level=43), Heartbeat(seq=1))
    assert ws.scores[Want.POWER] == pytest.approx(75.0)


def test_party_join_diff_satisfies_social() -> None:
    ws = fresh()
    brain, _ = make_brain(wants=ws)
    brain.handle_event(grind_state(in_party=False), Heartbeat(seq=0))
    brain.handle_event(grind_state(in_party=True), Heartbeat(seq=1))
    assert ws.scores[Want.SOCIAL] == pytest.approx(65.0)


def test_review_gains_the_which_want_to_serve_question() -> None:
    ws = fresh()
    brain, model = make_brain(wants=ws)
    brain.handle_event(grind_state(), Heartbeat(seq=0))
    questions = model.requests[-1]["questions"]
    question = questions["which_want_to_serve"]
    assert question["type"] == "choice"
    assert set(question["criteria"]) <= {w.value for w in Want}
    assert 1 <= len(question["criteria"]) <= 3


def test_review_has_no_want_question_without_state() -> None:
    brain, model = make_brain()
    brain.handle_event(grind_state(), Heartbeat(seq=0))
    assert "which_want_to_serve" not in model.requests[-1]["questions"]


# -- runtime wiring ----------------------------------------------------------


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.t += seconds


def make_agent(wants: WantState | None) -> tuple[ScheduledAgent, FakeClock]:
    clock = FakeClock()
    agent = ScheduledAgent.__new__(ScheduledAgent)
    agent.persona = SocietyPersona(
        persona_id="p1",
        name="p1",
        playstyle=Playstyle.MELEE,
        attitude=Attitude.SOLO,
        chattiness=0.5,
        level_band=(10, 40),
    )
    agent._tick_clock = clock
    agent.wants = wants
    agent._wants_clock = None
    agent._wants_last_map = None
    agent._wants_was_alive = True
    agent._trace = None  # partial construction: the tap lane stays off
    agent.brain = None
    agent.client = None
    return agent, clock


def test_runtime_decays_wants_on_heartbeat() -> None:
    ws = fresh(Personality.ACHIEVER)
    agent, clock = make_agent(ws)
    agent.deliver_event(grind_state(), Heartbeat(seq=1))
    assert ws.scores[Want.POWER] == pytest.approx(50.0)  # first call only anchors the clock
    clock.t += 3600.0
    agent.deliver_event(grind_state(), Heartbeat(seq=2))
    assert ws.scores[Want.POWER] == pytest.approx(50.0 - 12.0)


def test_runtime_observes_map_change_and_death() -> None:
    ws = fresh()
    agent, _clock = make_agent(ws)
    agent.deliver_event(grind_state(map_name="prt_fild08"), Heartbeat(seq=1))
    assert ws.scores[Want.NOVELTY] == pytest.approx(50.0)
    agent.deliver_event(grind_state(map_name="gef_fild07"), Heartbeat(seq=2))
    assert ws.scores[Want.NOVELTY] == pytest.approx(62.0)
    agent.deliver_event(grind_state(map_name="gef_fild07", alive=False), Heartbeat(seq=3))
    assert ws.scores[Want.COMFORT] == pytest.approx(25.0)


def test_runtime_low_hp_ticks_comfort() -> None:
    ws = fresh()
    agent, _clock = make_agent(ws)
    agent.deliver_event(grind_state(hp=200, max_hp=1000), Heartbeat(seq=1))
    assert ws.scores[Want.COMFORT] == pytest.approx(47.0)


def test_runtime_without_wants_is_unchanged() -> None:
    agent, _clock = make_agent(None)
    agent.deliver_event(grind_state(), Heartbeat(seq=1))
    assert agent.wants is None


# -- persona/roster personality assignment ----------------------------------


def test_society_persona_has_a_personality_default() -> None:
    persona = SocietyPersona(
        persona_id="p",
        name="p",
        playstyle=Playstyle.MELEE,
        attitude=Attitude.SOLO,
        chattiness=0.5,
        level_band=(1, 99),
    )
    assert Personality(persona.personality) in PERSONALITY_PROFILES


def test_roster_build_mixes_personalities_in_groups() -> None:
    roster = SocietyRoster.build(random.Random(11), 3, 5, solos=1)
    for group in roster.groups:
        drawn = {
            Personality(roster.personas[pid].personality)
            for pid in group.member_ids
            if pid in roster.personas
        }
        if len(group.member_ids) >= 2:
            assert len(drawn) >= 2, f"group {group.group_id} did not mix personalities"
