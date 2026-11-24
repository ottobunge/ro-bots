"""Leg-126: a live farming commitment gets time to execute amid chat storms."""

import json
from dataclasses import replace
from types import SimpleNamespace
from typing import Any, Literal, cast

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.brain import EventDrivenBrain, TickResult
from robots.app.scripts import FarmScript, ScriptOutcome, ScriptStatus
from robots.app.trace_log import TraceLog
from robots.domain.actions import AcceptInvite, Attack, PartyChat, Say, WhisperTo
from robots.domain.events import ChatHeard, Heartbeat, InviteReceived, PlanExpired
from robots.domain.farm import FarmPlan
from robots.domain.model import ActorRef, BotState, ChatLine, Goal, PartyInvite
from robots.society.memory import Memory, StubSummarizer
from robots.society.objectives import BoundCoordinator
from tests.conftest import make_state
from tests.test_brain import base_answers, make_brain
from tests.test_objectives import join_call, make_pair


@pytest.fixture
def now(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("robots.app.brain.time.monotonic", lambda: clock[0])
    return clock


def farm_brain(**kwargs: Any) -> EventDrivenBrain:
    answers = base_answers()
    answers["use_premade"] = {"noul": 1.0}
    answers["premade_pick"] = {"choice": "greet"}
    return make_brain(answers, spawn_species=lambda _map: ("Poring", "Drops"), **kwargs)


def hear(
    brain: EventDrivenBrain,
    state: BotState,
    index: int,
    *,
    channel: Literal["public", "party", "guild", "whisper"] = "whisper",
) -> TickResult:
    return brain.handle_event(
        state, ChatHeard(ChatLine(channel, "Friend", f"hello {index}", float(index)))
    )


def chat_actions(result: TickResult) -> list[Say | PartyChat | WhisperTo]:
    return [a for a in result.actions if isinstance(a, (Say, PartyChat, WhisperTo))]


def plan_for(brain: EventDrivenBrain) -> FarmPlan:
    plan = brain.current_plan
    assert plan is not None
    return plan


@pytest.mark.parametrize("channel", ["whisper", "public", "party"])
def test_farm_chat_storm_bounds_messages_decides_and_escalations(now, channel):
    brain = farm_brain()
    brain._chat = StaticChatGenerator(["one", "two", "three", "four"])
    state = make_state()
    brain.start(state)
    before = brain.decision_count
    emitted = []
    for index in range(20):
        now[0] = 1000.0 + index * 5
        # Alternate premades so the repeat filter alone cannot satisfy the cap.
        cast(ScriptedDecisionModel, brain._model)._answers["premade_pick"] = {
            "choice": "greet" if index % 2 else "lfp"
        }
        emitted.extend(chat_actions(hear(brain, state, index, channel=channel)))
    assert len(emitted) <= 3
    assert brain.decision_count - before <= 3
    assert brain.escalation_count <= 3


def test_farm_silent_replies_still_have_a_decide_cap(now):
    brain = farm_brain()
    cast(ScriptedDecisionModel, brain._model)._answers["use_premade"] = {"noul": 0.0}
    state = make_state()
    brain.start(state)
    before = brain.decision_count
    for index in range(20):
        assert hear(brain, state, index, channel="public").actions == ()
    assert brain.decision_count - before == 3


def exhaust(brain: EventDrivenBrain, state: BotState, now: list[float]) -> None:
    for index in range(3):
        now[0] = 1000.0 + index * 15
        hear(brain, state, index)


def test_rolling_window_reopens_at_boundary_without_a_new_plan(now):
    brain = farm_brain()
    brain._chat = StaticChatGenerator(["one", "two", "three", "four"])
    state = make_state()
    brain.start(state)
    plan = brain.current_plan
    exhaust(brain, state, now)
    before = brain.decision_count
    now[0] = 1119.999
    assert hear(brain, state, 4).actions == ()
    assert brain.decision_count == before
    now[0] = 1120.0
    assert chat_actions(hear(brain, state, 5)) == [Say("four")]
    assert brain.current_plan is plan


@pytest.mark.parametrize("release", ["expiry_event", "deadline", "town_review", "session"])
def test_plan_release_reopens_chat_immediately(now, release):
    brain = farm_brain()
    brain._chat = StaticChatGenerator(["one", "two", "three", "four"])
    state = make_state()
    brain.start(state)
    exhaust(brain, state, now)
    now[0] += 15
    if release == "expiry_event":
        brain.handle_event(state, PlanExpired(plan_for(brain).plan_id))
    elif release == "deadline":
        now[0] = 1900.0
    elif release == "town_review":
        cast(ScriptedDecisionModel, brain._model)._answers["change_goal"] = {"choice": "town"}
        brain.handle_event(state, Heartbeat(2))
        assert brain.current_plan is None
    else:
        state = replace(state, native_epoch=1)
    before = brain.decision_count
    assert chat_actions(hear(brain, state, 4)) == [Say("four")]
    assert brain.decision_count == before + 1


@pytest.mark.parametrize("status", [ScriptStatus.DONE, ScriptStatus.FAILED])
def test_terminal_farm_script_reopens_chat(now, monkeypatch, status):
    brain = farm_brain()
    brain._chat = StaticChatGenerator(["one", "two", "three", "four"])
    state = make_state()
    brain.start(state)
    exhaust(brain, state, now)
    monkeypatch.setattr(FarmScript, "step", lambda _self, _state: ScriptOutcome((), status))
    brain.step_script(state)
    now[0] += 15
    assert brain.current_plan is None
    assert chat_actions(hear(brain, state, 4)) == [Say("four")]


def test_heartbeat_reauthor_does_not_refill_chat_allowance(now):
    brain = farm_brain()
    state = make_state()
    brain.start(state)
    exhaust(brain, state, now)
    previous = plan_for(brain)
    brain.handle_event(state, Heartbeat(2))
    assert plan_for(brain).plan_id != previous.plan_id
    before = brain.decision_count
    assert hear(brain, state, 4).actions == ()
    assert brain.decision_count == before


def test_budget_is_per_agent(now):
    busy, other = farm_brain(), farm_brain()
    state = make_state()
    busy.start(state)
    other.start(state)
    exhaust(busy, state, now)
    assert chat_actions(hear(other, state, 4)) == [Say("gg")]


@pytest.mark.parametrize("goal", [Goal.SOCIAL, Goal.IDLE_TOWN])
def test_no_plan_keeps_existing_social_behavior(now, goal):
    brain = make_brain(base_answers())
    brain._chat = StaticChatGenerator(["one", "two", "three", "four"])
    state = make_state(goal=goal)
    for index in range(8):
        now[0] += 15
        assert chat_actions(hear(brain, state, index))
    assert brain.decision_count == 8


def test_active_plan_disables_initiative_with_real_chance_enabled(now, monkeypatch):
    monkeypatch.setenv("CHAT_INITIATIVE_CHANCE", "1")
    brain = farm_brain()
    state = make_state()
    assert brain.start(state).actions == ()
    assert brain._initiative_text(state) is None
    brain.handle_event(state, PlanExpired(plan_for(brain).plan_id))
    assert isinstance(brain._initiative_text(state), Say)


def test_undeclared_plan_does_not_gate_chat(now):
    brain = farm_brain()
    state = make_state()
    brain.start(state)
    brain._plan = replace(plan_for(brain), target_mobs=("Deviling",))
    brain._chat = StaticChatGenerator(["one", "two", "three", "four"])
    for index in range(4):
        now[0] += 15
        assert chat_actions(hear(brain, state, index))


def test_cooldown_and_repeat_filters_remain_under_farm_cap(now):
    brain = farm_brain()
    state = make_state()
    brain.start(state)
    assert chat_actions(hear(brain, state, 0, channel="public")) == [Say("Hi all")]
    now[0] += 1
    cast(ScriptedDecisionModel, brain._model)._answers["premade_pick"] = {"choice": "lfp"}
    assert hear(brain, state, 1, channel="public").actions == ()
    now[0] += 14
    cast(ScriptedDecisionModel, brain._model)._answers["premade_pick"] = {"choice": "greet"}
    assert hear(brain, state, 2, channel="public").actions == ()


def test_capped_chat_preserves_observation_and_allows_farm_attack(now):
    observed: list[ChatLine] = []
    brain = farm_brain(interaction_ingest=observed.append)
    state = make_state(
        name="budget-attack", nearby=(ActorRef(777, "Poring", "monster", 1, 121, 74),)
    )
    brain.start(state)
    exhaust(brain, state, now)
    before = brain.decision_count
    hear(brain, state, 4)
    assert observed[-1].text == "hello 4"
    assert brain.step_script(state).actions == (Attack(777),)
    assert brain.decision_count == before
    cast(ScriptedDecisionModel, brain._model)._answers["accept_invite"] = {"noul": 1.0}
    assert brain.handle_event(state, InviteReceived(PartyInvite("Friend", 1))).actions == (
        AcceptInvite(),
    )


def test_review_reports_share_the_budget_with_replies(now):
    reports: list[SimpleNamespace] = []
    brain = farm_brain(human_reports=lambda: list(reports))
    brain._chat = StaticChatGenerator(["one", "two", "three", "four"])
    state = make_state()
    brain.start(state)
    exhaust(brain, state, now)
    now[0] += 15
    reports.append(SimpleNamespace(line="thanks for the help"))
    assert brain.handle_event(state, Heartbeat(2)).actions == ()


def test_gate_trace_has_reason_plan_and_window_counters(now, tmp_path, monkeypatch):
    monkeypatch.setenv("CHAT_INITIATIVE_CHANCE", "1")
    trace = TraceLog(tmp_path / "traces", "farm-budget")
    try:
        brain = farm_brain(trace=trace)
        state = make_state()
        brain.start(state)
        exhaust(brain, state, now)
        hear(brain, state, 4)
        rows = [json.loads(line) for line in trace.path.read_text().splitlines()]
        gated = [row for row in rows if row["kind"] == "chat_budget_gated"]
        assert {row["reason"] for row in gated} >= {"farm_plan_initiative", "farm_decide_cap"}
        row = next(row for row in gated if row["reason"] == "farm_decide_cap")
        assert row["plan_id"] == plan_for(brain).plan_id
        assert row["map"] == state.map_name
        assert row["window_s"] == 120
        assert row["limit"] == 3
        assert row["chat_decisions"] == 3
    finally:
        trace.close()


def test_capped_chat_still_records_memory_and_received_objective(now):
    _, _, mate = make_pair()
    bound = BoundCoordinator(mate, online=lambda: ("lead", "mate"))
    memory = Memory(StubSummarizer())
    brain = farm_brain(coordination=bound, memory=memory)
    state = make_state()
    brain.start(state)
    exhaust(brain, state, now)
    before = brain.decision_count
    event = ChatHeard(join_call())
    assert brain.handle_event(state, event).actions == ()
    assert brain.decision_count == before
    assert event.line.text in memory.log.notes()[-1].text
    result = brain.handle_event(state, InviteReceived(PartyInvite("PartyLeader", 1)))
    assert result.actions == (AcceptInvite(),)
    objective = bound.active_objective()
    assert objective is not None
    assert objective.map_name == "prt_fild08"


@pytest.mark.parametrize("in_party", [True, False])
def test_all_outgoing_chat_channels_share_the_cap_without_suppressing_invites(
    now, in_party, monkeypatch
):
    brain = farm_brain()
    brain._chat = StaticChatGenerator(["one", "two", "three", "four"])
    state = make_state(in_party=in_party)
    brain.start(state)
    exhaust(brain, state, now)
    now[0] += 15
    # Coordination output and party-event announcements cannot bypass the cap.
    coordination = SimpleNamespace(
        review_actions=lambda *_args: (
            Say("public"),
            PartyChat("party"),
            WhisperTo("Friend", "hi"),
            AcceptInvite(),
        )
    )
    monkeypatch.setattr(brain, "_coordination", coordination)
    assert brain._coordination_review(state, {}, []) == [AcceptInvite()]
    brain._pending_party_event = "level_up"
    assert brain._party_event_announce(state, {"chat_urgency": {"score": 2}}, []) == []
