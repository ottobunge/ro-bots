"""The sampled script-step telemetry: why 5,209 moves yield only 7 attacks?

Leg 17's traces record the actions but not the script's DECISION context (the
nearest-monster distance, the chosen action kind) at the moment of stepping.
A sampled script_step line (one per SCRIPT_TRACE_PERIOD_S, default 10s) makes
the approach convergence diagnosable from the traces alone."""

from __future__ import annotations

from robots.app.brain import EventDrivenBrain
from robots.app.scripts import ScriptOutcome, ScriptStatus
from robots.domain.model import BotState
from tests.conftest import make_state as _make_state


class _FakeScript:
    _starved = 0

    def __init__(self) -> None:
        self.steps = 0

    def step(self, state):
        self.steps += 1
        return ScriptOutcome((), ScriptStatus.ACTIVE)


def _brain_with_trace(monkeypatch, trace) -> EventDrivenBrain:
    brain = EventDrivenBrain.__new__(EventDrivenBrain)  # skip the heavy ctor
    brain._trace = trace
    brain._script = _FakeScript()
    brain._widen_streaks = {}
    brain._recovering = False
    brain._escape = None
    brain._last_script_trace = 0.0
    return brain


def test_first_step_traces_immediately(monkeypatch) -> None:
    lines: list[dict] = []

    class Trace:
        def log(self, kind, **payload):
            lines.append({"kind": kind, **payload})

    lines = []
    brain = _brain_with_trace(monkeypatch, Trace())
    outcome = brain.step_script(make_state())
    assert outcome.status == ScriptStatus.ACTIVE
    assert len(lines) == 1
    assert lines[0]["kind"] == "script_step"


def make_state() -> BotState:
    return _make_state()


def test_second_step_within_period_not_traced(monkeypatch) -> None:
    class Trace:
        def __init__(self) -> None:
            self.n = 0

        def log(self, kind, **payload):
            self.n += 1

    trace = Trace()
    brain = _brain_with_trace(monkeypatch, trace)
    monkeypatch.setattr(brain, "_last_script_trace", None, raising=False)
    monkeypatch.setattr("robots.app.brain.time.monotonic", lambda: 1000.0)
    brain.step_script(make_state())
    brain.step_script(make_state())  # 0s later: inside the 10s window
    assert trace.n == 1


def test_step_after_period_traced_again(monkeypatch) -> None:
    class Trace:
        def __init__(self) -> None:
            self.n = 0

        def log(self, kind, **payload):
            self.n += 1

    trace = Trace()
    brain = _brain_with_trace(monkeypatch, trace)
    clock = {"now": 1000.0}

    def fake_monotonic() -> float:
        return clock["now"]

    monkeypatch.setattr("robots.app.brain.time.monotonic", fake_monotonic)
    brain.step_script(make_state())
    clock["now"] = 1011.0
    brain.step_script(make_state())
    assert trace.n == 2


def test_no_trace_object_is_silent(monkeypatch) -> None:
    brain = _brain_with_trace(monkeypatch, None)
    outcome = brain.step_script(make_state())
    assert outcome.status == ScriptStatus.ACTIVE
