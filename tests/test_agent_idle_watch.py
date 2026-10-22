from types import SimpleNamespace

from robots.app.agent_runtime import IDLE_REVIEW_S, ScheduledAgent


def test_idle_watch_constants() -> None:
    """The user directive: the AFK ceiling is five minutes and the heartbeat
    upper bound equals it."""
    from robots.app import agent_runtime as rt  # noqa: PLC0415

    assert rt.HEARTBEAT_MAX_S <= 300.0
    assert IDLE_REVIEW_S <= 300.0


def test_idle_agent_gets_synthetic_review() -> None:
    """An agent with no executed actions for IDLE_REVIEW_S synthesizes one
    idle-review decide; the review clock then re-arms (one review, not a
    storm)."""

    class FakeClock:
        def __init__(self) -> None:
            self.t = 1000.0

        def monotonic(self) -> float:
            return self.t

        def sleep(self, s: float) -> None:
            self.t += s

    agent = ScheduledAgent.__new__(ScheduledAgent)
    agent.persona = SimpleNamespace(persona_id="test")
    agent._tick_clock = FakeClock()
    agent._last_action_monotonic = agent._tick_clock.monotonic()
    agent.brain = SimpleNamespace()  # the real run: both live
    agent.client = SimpleNamespace()
    reviews: list[str] = []

    def fake_deliver(state, event):
        reviews.append(str(event))

    agent.deliver_event = fake_deliver  # type: ignore[method-assign]
    agent._idle_watch(None)
    assert reviews == []
    agent._tick_clock.t += IDLE_REVIEW_S + 1.0
    agent._idle_watch(None)
    assert len(reviews) == 1, "the idle agent must get exactly one forced review"
    agent._tick_clock.t += 1.0
    agent._idle_watch(None)
    assert len(reviews) == 1, "the review clock re-arms: no storm"
