"""Offline received-vitals integration; no provider or native connection."""

from __future__ import annotations

import random
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app.agent_runtime import ManifestEntry, ScheduledAgent
from robots.society.society import SocietyRoster


class StatusClient:
    def __init__(self) -> None:
        self.status_params = {5: 37, 6: 100, 7: 0, 8: 23}
        self.connected = False
        self.closed = 0

    def connect(self) -> None:
        self.connected = True

    def close(self) -> None:
        self.connected = False
        self.closed += 1


class ReceivingClock:
    def __init__(self, receive: Callable[[], None]) -> None:
        self.now = 0.0
        self.receive = receive

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds
        self.receive()


class RecordingBrain:
    def __init__(self) -> None:
        self.states: list[Any] = []

    def start(self, state: Any) -> Any:
        self.states.append(state)
        return SimpleNamespace(actions=())

    def handle_event(self, state: Any, event: Any) -> Any:
        self.states.append(state)
        return SimpleNamespace(actions=(), notes=())

    def step_script(self, state: Any) -> Any:
        self.states.append(state)
        return SimpleNamespace(actions=())


def make_agent(client: StatusClient) -> ScheduledAgent:
    roster = SocietyRoster.build(random.Random(42), n_groups=3)
    persona = roster.personas["Doramir-01"]
    return ScheduledAgent(
        persona,
        ManifestEntry(persona.persona_id, "synthetic", "", "Synthetic"),
        client=client,
        threaded=False,
    )


def test_stopped_native_reader_denies_retained_complete_status() -> None:
    client = StatusClient()
    client.running = False  # type: ignore[attr-defined]
    client.connected_map = False  # type: ignore[attr-defined]
    client.sock = None  # type: ignore[attr-defined]
    client.rx_thread = None  # type: ignore[attr-defined]
    with pytest.raises(NativeTelemetryUnavailable, match=r"^native vitals unavailable$"):
        make_agent(client).build_state()


@pytest.mark.parametrize("flag", ["running", "connected_map"])
@pytest.mark.parametrize("value", [False, None, 1])
def test_exposed_native_flag_requires_true(flag: str, value: object) -> None:
    client = StatusClient()
    setattr(client, flag, value)
    with pytest.raises(NativeTelemetryUnavailable):
        make_agent(client).build_state()


def test_exposed_missing_socket_denies_retained_status() -> None:
    client = StatusClient()
    client.sock = None  # type: ignore[attr-defined]
    with pytest.raises(NativeTelemetryUnavailable):
        make_agent(client).build_state()


class FakeReader:
    def __init__(self, alive: bool = True, error: BaseException | None = None) -> None:
        self.alive = alive
        self.error = error

    def is_alive(self) -> bool:
        if self.error is not None:
            raise self.error
        return self.alive


@pytest.mark.parametrize("reader", [None, FakeReader(False)])
def test_exposed_missing_or_dead_reader_denies_retained_status(reader: FakeReader | None) -> None:
    client = StatusClient()
    client.rx_thread = reader  # type: ignore[attr-defined]
    with pytest.raises(NativeTelemetryUnavailable):
        make_agent(client).build_state()


@pytest.mark.parametrize("name", ["running", "connected_map", "sock", "rx_thread", "all"])
def test_exposed_healthy_native_session_accepts_zero_sp(name: str) -> None:
    client = StatusClient()
    signals = {"running": True, "connected_map": True, "sock": object(), "rx_thread": FakeReader()}
    for key, value in signals.items():
        if name in (key, "all"):
            setattr(client, key, value)
    client.is_healthy = lambda: True  # type: ignore[attr-defined]
    state = make_agent(client).build_state()
    assert (state.hp, state.max_hp, state.sp, state.max_sp) == (37, 100, 0, 23)


@pytest.mark.parametrize("origin", [KeyboardInterrupt(), SystemExit(), BaseException()])
def test_reader_liveness_preserves_nonlocal_origin(origin: BaseException) -> None:
    client = StatusClient()
    client.rx_thread = FakeReader(error=origin)  # type: ignore[attr-defined]
    with pytest.raises(type(origin)) as caught:
        make_agent(client).build_state()
    assert caught.value is origin


def test_dead_reader_complete_tick_skips_events_timers_and_script() -> None:
    client = StatusClient()
    reader = FakeReader()
    client.rx_thread = reader  # type: ignore[attr-defined]
    agent = make_agent(client)
    brain = RecordingBrain()
    agent.brain = brain  # type: ignore[assignment]
    clock = ReceivingClock(lambda: None)
    agent._tick_clock = clock
    assert agent.connect()
    brain.states.clear()
    client.chat = [(9, "pending peer")]  # type: ignore[attr-defined]
    assert agent.timers is not None
    agent.timers.add_periodic("synthetic", 0.1, 0.1)
    clock.now = 1
    reader.alive = False
    agent.tick()
    assert not brain.states
    assert agent.tick_count == 0
    assert agent._session_ticks == 0
    assert agent._chat_seen == 0
    assert agent.memory.log.notes() == ()
    assert len(agent.timers.fire_due(clock.now)) == 1


def test_dead_reader_complete_connect_cleans_up_without_cognition() -> None:
    client = StatusClient()
    client.rx_thread = FakeReader(False)  # type: ignore[attr-defined]
    original = make_agent(client)
    brain = RecordingBrain()
    clock = ReceivingClock(lambda: pytest.fail("zero budget must not sleep"))
    agent = ScheduledAgent(
        original.persona,
        original.entry,
        client=client,
        brain=brain,  # type: ignore[arg-type]
        tick_clock=clock,
        telemetry_wait_s=0,
    )
    assert not agent.connect()
    assert client.closed == 1
    assert agent.thread is None
    assert not agent.online
    assert not brain.states
    assert agent.memory.log.notes() == ()


def test_build_state_projects_current_received_vitals() -> None:
    client = StatusClient()
    agent = make_agent(client)
    state = agent.build_state()
    assert (state.hp, state.max_hp, state.sp, state.max_sp) == (37, 100, 0, 23)
    client.status_params[5] = 12
    state = agent.build_state()
    assert (state.hp, state.max_hp, state.sp, state.max_sp) == (12, 100, 0, 23)


def test_missing_status_attribute_is_opaque_unknown() -> None:
    client = StatusClient()
    del client.status_params
    with pytest.raises(NativeTelemetryUnavailable, match=r"^native vitals unavailable$"):
        make_agent(client).build_state()


def test_start_waits_for_gradually_received_quartet() -> None:
    client = StatusClient()
    client.status_params.clear()
    brain = RecordingBrain()
    packets = iter(((5, 37), (6, 100), (7, 0), (8, 23)))

    def receive() -> None:
        assert not brain.states
        key, value = next(packets)
        client.status_params[key] = value

    agent = make_agent(client)
    agent.brain = brain  # type: ignore[assignment]
    clock = ReceivingClock(receive)
    agent._tick_clock = clock
    assert agent.connect()
    assert len(brain.states) == 1
    state = brain.states[0]
    assert (state.hp, state.max_hp, state.sp, state.max_sp) == (37, 100, 0, 23)
    assert 0 < clock.now <= 5


def test_incomplete_tick_skips_all_cognition_without_last_good_health() -> None:
    client = StatusClient()
    agent = make_agent(client)
    brain = RecordingBrain()
    agent.brain = brain  # type: ignore[assignment]
    agent._tick_clock = ReceivingClock(lambda: None)
    assert agent.connect()
    brain.states.clear()
    client.status_params.pop(8)
    agent.tick()
    assert not brain.states
    assert agent.tick_count == 0
    assert agent._chat_seen == 0
    assert agent.memory.log.notes() == ()


@pytest.mark.parametrize("fault", ["rx_error", "dispatch_errors", "is_healthy"])
def test_transport_fault_denies_start_and_tick(fault: str) -> None:
    client = StatusClient()
    if fault == "is_healthy":
        setattr(client, fault, lambda: False)
    else:
        setattr(client, fault, ["synthetic transport failure"])
    agent = make_agent(client)
    brain = RecordingBrain()
    agent.brain = brain  # type: ignore[assignment]
    clock = ReceivingClock(lambda: None)
    agent._tick_clock = clock
    assert not agent.connect()
    assert not brain.states
    assert client.closed == 1
    assert agent.thread is None
    assert clock.now <= 5
    agent.tick()
    assert not brain.states


@pytest.mark.parametrize("budget", [True, -1, 6, float("nan"), float("inf"), "1"])
def test_invalid_readiness_budget_rejected_before_connect(budget: Any) -> None:
    client = StatusClient()
    agent = make_agent(client)
    with pytest.raises(ValueError, match="telemetry_wait_s"):
        ScheduledAgent(agent.persona, agent.entry, client=client, telemetry_wait_s=budget)
    assert not client.connected


def test_readiness_timeout_closes_without_start_or_thread() -> None:
    client = StatusClient()
    client.status_params.clear()
    original = make_agent(client)
    brain = RecordingBrain()
    clock = ReceivingClock(lambda: None)
    agent = ScheduledAgent(
        original.persona,
        original.entry,
        client=client,
        brain=brain,  # type: ignore[arg-type]
        tick_clock=clock,
        telemetry_wait_s=0.1,
    )
    assert not agent.connect()
    assert clock.now == 0.1
    assert client.closed == 1
    assert not brain.states
    assert agent.thread is None
    assert not agent.online
    assert agent.memory.log.notes() == ()


def test_idle_without_brain_does_not_wait_for_status() -> None:
    client = StatusClient()
    client.status_params.clear()
    agent = make_agent(client)
    clock = ReceivingClock(lambda: pytest.fail("idle must not wait"))
    agent._tick_clock = clock
    assert agent.connect()
    assert clock.now == 0
    agent.tick()
    assert agent.tick_count == 0


@pytest.mark.parametrize(
    "parameters",
    [{}, {5: 1}, {5: 37, 6: 12, 7: 0, 8: 23}, {5: 37, 6: 100, 7: 24, 8: 23}],
)
def test_partial_or_inconsistent_current_status_denies_tick(parameters: dict[int, int]) -> None:
    client = StatusClient()
    agent = make_agent(client)
    brain = RecordingBrain()
    agent.brain = brain  # type: ignore[assignment]
    client.status_params = parameters
    agent.tick()
    assert not brain.states
    assert agent.tick_count == 0


def test_complete_current_status_reaches_events_timers_and_script() -> None:
    client = StatusClient()
    client.chat = [(9, "synthetic peer")]  # type: ignore[attr-defined]
    agent = make_agent(client)
    brain = RecordingBrain()
    agent.brain = brain  # type: ignore[assignment]
    clock = ReceivingClock(lambda: None)
    agent._tick_clock = clock
    assert agent.connect()
    brain.states.clear()
    assert agent.timers is not None
    agent.timers.add_periodic("synthetic", 0.1, 0.1)
    clock.now = 1
    client.status_params[5] = 12
    agent.tick()
    assert len(brain.states) == 3
    assert all((s.hp, s.max_hp, s.sp, s.max_sp) == (12, 100, 0, 23) for s in brain.states)
    assert agent.tick_count == 1


def test_zero_readiness_budget_allows_already_complete_status() -> None:
    client = StatusClient()
    original = make_agent(client)
    brain = RecordingBrain()
    agent = ScheduledAgent(
        original.persona,
        original.entry,
        client=client,
        brain=brain,  # type: ignore[arg-type]
        threaded=False,
        telemetry_wait_s=0,
    )
    assert agent.connect()
    assert len(brain.states) == 1
