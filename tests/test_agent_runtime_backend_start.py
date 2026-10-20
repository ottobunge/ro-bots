"""Connect resilience: a decision-backend failure at brain start keeps the session.

Live finding (window 32, run/reviews/engagement-diagnosis.json): the decision
backend's 30s httpx timeout raised PlayingBackendError out of brain.start
inside ScheduledAgent.connect; the except path tore down the just-authenticated
transport session, so the agent re-logged forever and never came online. The
transport session and the decision backend are independent: a backend-class
failure must keep the authenticated session (the tick loop's decision-failure
handling already counts transient failures and continues) while genuinely
broken startups keep tearing down.
"""

from __future__ import annotations

from typing import Any

import pytest

from robots.adapters.playing_backends import PlayingBackendError
from robots.app.agent_runtime import ScheduledAgent
from robots.app.brain import EventDrivenBrain, TickResult
from tests.test_agent_host import (
    STUB_ANSWERS,
    FakeGameClient,
    ScriptedDecisionModel,
    _StaticChat,
    make_entry,
    make_roster,
)


class _BackendFailBrain:
    """Brain whose start() fails with the live-observed backend error."""

    _ERR = PlayingBackendError("real inference request failed (details redacted)")

    def __init__(self) -> None:
        self.start_calls = 0

    def start(self, state: Any) -> TickResult:
        self.start_calls += 1
        raise self._ERR

    def sync_context(self, state: Any) -> None:
        return None

    def step_script(self, state: Any) -> TickResult:
        return TickResult((), {})


class _ContextFailBrain:
    """Brain whose start() fails with a non-backend (environment) error."""

    _ERR = RuntimeError("planning context unavailable")

    def start(self, state: Any) -> TickResult:
        raise self._ERR

    def sync_context(self, state: Any) -> None:
        return None

    def step_script(self, state: Any) -> TickResult:
        return TickResult((), {})


def _agent(brain: Any) -> tuple[ScheduledAgent, FakeGameClient]:
    rng = __import__("random").Random(7)
    client = FakeGameClient(make_entry("Doramir-01"))
    agent = ScheduledAgent(
        make_roster().personas["Doramir-01"],
        make_entry("Doramir-01"),
        brain=brain,
        client=client,
        heartbeat_min_s=2.0,
        heartbeat_max_s=3.0,
        rng=rng,
        threaded=False,
    )
    return agent, client


def test_connect_keeps_session_when_decision_backend_fails() -> None:
    brain = _BackendFailBrain()
    agent, client = _agent(brain)

    assert agent.connect() is True
    assert brain.start_calls == 1
    assert agent.online is True
    assert client.connected is True, "backend failure must not tear down the session"


def test_backend_fail_session_ticks_and_survives() -> None:
    brain = _BackendFailBrain()
    agent, client = _agent(brain)
    assert agent.connect() is True

    agent.tick()
    agent.tick()
    assert agent.online is True
    assert client.connected is True


def test_non_backend_start_failure_still_tears_down() -> None:
    brain = _ContextFailBrain()
    agent, client = _agent(brain)

    assert agent.connect() is False
    assert agent.online is False
    assert client.connected is False, "non-backend startup failures keep the old contract"


@pytest.mark.parametrize(
    "brain",
    [EventDrivenBrain(ScriptedDecisionModel(dict(STUB_ANSWERS)), _StaticChat())],
)
def test_healthy_brain_connect_unchanged(brain: Any) -> None:
    agent, client = _agent(brain)
    assert agent.connect() is True
    assert agent.online is True
    assert client.connected is True
