"""Brain tests: event handling, scripts, plans, escalation (all offline)."""

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.brain import EventDrivenBrain
from robots.domain.actions import AcceptInvite, PartyChat, Rest, Say
from robots.domain.events import (
    ChatHeard,
    DamageTaken,
    Heartbeat,
    InviteReceived,
    MonsterSpotted,
    PlanExpired,
    TimerFired,
)
from robots.domain.farm import MobInfo
from robots.domain.model import ActorRef, ChatLine, Goal, PartyInvite

# -- fakes --------------------------------------------------------------


class FakeMobDB:
    def __init__(self, mobs: dict[str, MobInfo]) -> None:
        self._mobs = mobs

    def mobs_on_map(self, map_name: str) -> tuple[MobInfo, ...]:
        return tuple(sorted(self._mobs.values(), key=lambda m: m.level))

    def by_name(self, name: str) -> MobInfo | None:
        return self._mobs.get(name)


# -- helpers ------------------------------------------------------------


def base_answers() -> dict:
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
    answers: dict | None = None, queue: list[dict] | None = None, **kwargs
) -> EventDrivenBrain:
    model = ScriptedDecisionModel(answers=answers, queue=queue)
    return EventDrivenBrain(decision_model=model, chat=StaticChatGenerator(["gg"]), **kwargs)


def poring() -> ActorRef:
    return ActorRef(id=1, name="Poring", kind="monster", distance=3.0)


# -- tests --------------------------------------------------------------


def test_start_runs_heartbeat_and_picks_script(state) -> None:
    brain = make_brain(base_answers())
    result = brain.start(state)
    assert brain.decision_count == 1
    assert brain.current_script() is not None
    assert any("script->" in n for n in result.notes)


def test_monster_interrupt_wakes_brain(state) -> None:
    brain = make_brain(base_answers())
    event = MonsterSpotted(actor=poring(), aggressive=False)
    result = brain.handle_event(state, event)
    assert brain.decision_count == 1
    assert any("monster" in n for n in result.notes)


def test_damage_rest_reaction(state) -> None:
    answers = base_answers()
    answers["react_damage"] = {"type": "choice", "choice": "rest", "confidence": 0.9}
    brain = make_brain(answers)
    result = brain.handle_event(state, DamageTaken(amount=150, from_id=1))
    assert any(isinstance(a, Rest) for a in result.actions)


def test_directed_chat_escalates_to_llm(town_state) -> None:
    answers = base_answers()
    answers["should_reply"] = {"type": "noul", "noul": 0.95}
    brain = make_brain(answers)
    event = ChatHeard(line=ChatLine(channel="whisper", sender="Trader", text="hi bot", at=1.0))
    result = brain.handle_event(town_state, event)
    assert result.escalated is True
    assert brain.escalation_count == 1
    assert brain.escalation_rate == 1.0
    says = [a for a in result.actions if isinstance(a, Say)]
    assert says
    assert says[0].text == "gg"


def test_premade_chat_no_llm(town_state) -> None:
    answers = base_answers()
    answers["use_premade"] = {"type": "noul", "noul": 0.9}
    answers["premade_pick"] = {"type": "choice", "choice": "greet", "confidence": 0.9}
    brain = make_brain(answers)
    event = ChatHeard(line=ChatLine(channel="public", sender="Trader", text="hello", at=1.0))
    result = brain.handle_event(town_state, event)
    says = [a for a in result.actions if isinstance(a, (Say, PartyChat))]
    assert says
    assert says[0].text == "Hi all"
    assert result.escalated is False
    assert brain.escalation_count == 0


def test_accept_invite(invited_state) -> None:
    answers = base_answers()
    answers["accept_invite"] = {"type": "noul", "noul": 0.9}
    brain = make_brain(answers)
    result = brain.handle_event(
        invited_state, InviteReceived(invite=PartyInvite(from_name="Leader", at=1.0))
    )
    assert any(isinstance(a, AcceptInvite) for a in result.actions)


def test_goal_change_on_heartbeat(state) -> None:
    answers = base_answers()
    answers["change_goal"] = {"type": "choice", "choice": "town", "confidence": 0.9}
    brain = make_brain(answers)
    result = brain.handle_event(state, Heartbeat(seq=1))
    assert any("goal" in n and "idle_town" in n for n in result.notes)


def test_farm_plan_authored_with_mob_db(state) -> None:
    db = FakeMobDB(
        {
            "Poring": MobInfo(id=1002, name="Poring", level=1),
            "Drops": MobInfo(id=1113, name="Drops", level=3),
        }
    )
    brain = make_brain(base_answers(), mob_db=db)
    brain.handle_event(state, Heartbeat(seq=1))
    plan = brain.current_plan
    assert plan is not None
    assert plan.target_mobs == ("Poring",)
    assert plan.duration_s == 900.0  # score 1.0 -> medium
    assert plan.interrupt_level_above == state.base_level


def test_plan_interrupt_filtering(state) -> None:
    db = FakeMobDB(
        {
            "Poring": MobInfo(id=1002, name="Poring", level=1),
            "Baphomet": MobInfo(id=1039, name="Baphomet", level=81, is_mvp=True),
        }
    )
    brain = make_brain(base_answers(), mob_db=db)
    brain.handle_event(state, Heartbeat(seq=1))  # authors plan, targets Poring
    assert brain.current_plan is not None
    assert brain.should_interrupt(MonsterSpotted(actor=poring())) is False
    baphomet = ActorRef(id=2, name="Baphomet", kind="monster", distance=5.0)
    assert brain.should_interrupt(MonsterSpotted(actor=baphomet)) is True


def test_no_plan_means_everything_interrupts(state) -> None:
    brain = make_brain(base_answers())
    assert brain.should_interrupt(MonsterSpotted(actor=poring())) is True


def test_plan_expiry_clears_plan(state) -> None:
    db = FakeMobDB({"Poring": MobInfo(id=1002, name="Poring", level=1)})
    brain = make_brain(base_answers(), mob_db=db)
    brain.handle_event(state, Heartbeat(seq=1))
    assert brain.current_plan is not None
    brain.handle_event(state, PlanExpired(plan_id=1))
    assert brain.current_plan is None


def test_timer_event_reaches_brain(state) -> None:
    brain = make_brain(base_answers())
    result = brain.handle_event(state, TimerFired(name="idle_review", seq=1))
    assert brain.decision_count == 1
    assert any("idle_review" in n for n in result.notes)


def test_step_script_runs_without_model_calls(state) -> None:
    brain = make_brain(base_answers())
    brain.start(state)
    count_before = brain.decision_count
    brain.step_script(state)
    assert brain.decision_count == count_before


def test_goal_enum_values() -> None:
    assert {g.value for g in Goal} >= {"grind", "farm_item", "idle_town", "quest", "social"}


@pytest.mark.parametrize(
    ("score", "expected_s"),
    [(0.0, 300.0), (1.0, 900.0), (2.0, 1800.0)],
)
def test_farm_duration_mapping(state, score: float, expected_s: float) -> None:
    db = FakeMobDB({"Poring": MobInfo(id=1002, name="Poring", level=1)})
    answers = base_answers()
    answers["farm_duration"] = {"type": "score", "score": score}
    brain = make_brain(answers, mob_db=db)
    brain.handle_event(state, Heartbeat(seq=1))
    assert brain.current_plan is not None
    assert brain.current_plan.duration_s == expected_s
