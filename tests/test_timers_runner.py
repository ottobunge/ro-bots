"""Tests for randomized timers and the runner's event pump."""

import itertools
import random

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.brain import EventDrivenBrain
from robots.app.runner import BotRunner
from robots.app.timers import TimerSet, idle_review_timer, plan_expiry_timer
from robots.domain.events import PlanExpired, TimerFired
from robots.domain.model import BotState


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def sleep(self, seconds: float) -> None:
        self.t += seconds

    def monotonic(self) -> float:
        return self.t


class FakeGameClient:
    def __init__(self, states: list[BotState]) -> None:
        self._states = list(states)
        self.actions: list[object] = []

    def poll_state(self) -> BotState:
        return self._states[0]

    def act(self, action: object) -> None:
        self.actions.append(action)


def answers() -> dict:
    return {
        "next_action": {"type": "choice", "choice": "idle", "confidence": 0.9},
        "should_reply": {"type": "noul", "noul": 0.0},
        "hp_critical": {"type": "noul", "noul": 0.0},
        "accept_invite": {"type": "noul", "noul": 0.0},
        "use_premade": {"type": "noul", "noul": 0.0},
        "premade_pick": {"type": "choice", "choice": "none", "confidence": 0.9},
        "chat_urgency": {"type": "score", "score": 0.0},
        "goal_review": {"type": "score", "score": 1.0},
        "change_goal": {"type": "choice", "choice": "keep", "confidence": 0.9},
    }


def test_random_timer_range_and_reschedule() -> None:
    clock = FakeClock()
    rng = random.Random(42)
    timer = idle_review_timer(clock, rng)
    fired_at: list[float] = []
    for _ in range(50):
        clock.t = timer.fire_at + 0.01
        event = timer.fire_due(clock.t)
        assert isinstance(event, TimerFired)
        fired_at.append(timer.fire_at)
    spans = [b - a for a, b in itertools.pairwise(fired_at)]
    assert all(5 * 60 - 1 <= s <= 20 * 60 + 1 for s in spans)


def test_timer_set_fires_once_events() -> None:
    clock = FakeClock()
    timers = TimerSet(clock)
    timers.schedule_once("late", 10.0, PlanExpired(plan_id=7))
    assert timers.fire_due(5.0) == ()
    fired = timers.fire_due(10.0)
    assert fired == (PlanExpired(plan_id=7),)
    assert timers.fire_due(11.0) == ()  # spent


def test_plan_expiry_timer_uses_plan_duration() -> None:
    clock = FakeClock()
    timer = plan_expiry_timer(clock, plan_id=3, duration_s=900.0)
    assert timer.fire_due(899.0) is None
    assert timer.fire_due(900.0) == PlanExpired(plan_id=3)


def test_runner_pumps_timers_into_brain(state) -> None:
    clock = FakeClock()
    brain = EventDrivenBrain(
        decision_model=ScriptedDecisionModel(answers=answers()),
        chat=StaticChatGenerator(),
    )
    timers = TimerSet(clock)
    timers.schedule_once("soon", 2.0, TimerFired(name="idle_review", seq=1))
    runner = BotRunner(brain, FakeGameClient([state]), clock, tick_seconds=1.0, timers=timers)
    runner.run(max_ticks=4)
    assert brain.decision_count >= 1  # the timer fired and woke the brain


def test_runner_survives_then_stops_on_errors(state) -> None:
    class ExplodingClient(FakeGameClient):
        def poll_state(self) -> BotState:
            msg = "map server gone"
            raise ConnectionError(msg)

    clock = FakeClock()
    brain = EventDrivenBrain(
        decision_model=ScriptedDecisionModel(answers=answers()),
        chat=StaticChatGenerator(),
    )
    runner = BotRunner(brain, ExplodingClient([state]), clock, tick_seconds=0.0)
    runner.run(max_ticks=10)
    assert len(runner.history) == 0
