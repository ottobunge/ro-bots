"""Offline population heartbeat phases: spread, restart stability and drift."""

import argparse
import json
import math
import random
from pathlib import Path

import pytest

from robots.app.agent_runtime import AgentHost, ScheduledAgent, load_manifest
from robots.app.brain import TickResult
from robots.app.timers import RandomTimer
from robots.playing import build_roster
from robots.popgen import generate_population
from tests.test_agent_host import FakeClock, FakeGameClient, _StaticChat, make_agent
from tests.test_popgen import make_spec


@pytest.fixture
def population_files(tmp_path: Path):
    def write(count: int) -> tuple[Path, Path]:
        population = generate_population(
            make_spec(friend_groups=count // 4, friends_per_group=(4, 4), solo_agents=count % 4)
        )
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps(population.manifest))
        summary = tmp_path / "population.json"
        summary.write_text(json.dumps(population.summary()))
        return manifest, summary

    return write


def connected_host(
    files: tuple[Path, Path],
    *,
    seed: int = 0,
    start: float = 0.0,
    bounds: tuple[float, float] = (30.0, 75.0),
    limit: int = 0,
) -> AgentHost:
    manifest, population = files
    args = argparse.Namespace(solo=True, seed=0, schedule_file=None, playground=False)
    host = AgentHost(
        build_roster(load_manifest(manifest), args),
        manifest,
        population_file=population,
        rng=random.Random(seed),
        chat_generator=_StaticChat(),
        client_factory=FakeGameClient,
        run_worldfeed=False,
        heartbeat_min_s=bounds[0],
        heartbeat_max_s=bounds[1],
        max_agents=limit,
    )
    for agent in host.agents.values():
        clock = FakeClock()
        clock.now = start
        agent._tick_clock = clock
        agent._threaded = False
        agent.brain = None
        # Gameplay RNG use must not alter the heartbeat phase or future drift.
        for _ in range(seed):
            agent.rng.random()
        assert agent.connect()
    return host


def heartbeat(agent: ScheduledAgent) -> RandomTimer:
    assert agent.timers is not None
    return agent.timers._periodic["idle_review"]


@pytest.mark.parametrize("count", [1, 7, 29, 128])
def test_startup_phases_span_the_full_window(population_files, count: int) -> None:
    host = connected_host(population_files(count))
    phases = sorted(heartbeat(agent).fire_at - 30 for agent in host.agents.values())
    spacing = 45 / count
    assert phases == pytest.approx([(i + 0.5) * spacing for i in range(count)])
    # Every sliding two-second window, including those crossing a slot boundary.
    for sample in range(451):
        instant = sample / 10
        assert sum(instant <= phase < instant + 2 for phase in phases) <= math.ceil(count * 0.1)


def test_same_population_keeps_phases_and_drift_across_runner_restarts(population_files) -> None:
    files = population_files(29)
    first = connected_host(files)
    # Manifest row order, host seed, gameplay RNG consumption and monotonic
    # origin can all change on restart; persona identities have not changed.
    data = json.loads(files[0].read_text())
    data["accounts"].reverse()
    files[0].write_text(json.dumps(data))
    restarted = connected_host(files, seed=19, start=1000)
    for pid, agent in first.agents.items():
        left, right = heartbeat(agent), heartbeat(restarted.agents[pid])
        assert left.fire_at == pytest.approx(right.fire_at - 1000)
        for _ in range(20):
            left_now, right_now = left.fire_at, right.fire_at
            assert left.fire_due(left_now) == right.fire_due(right_now)
            assert left.fire_at - left_now == pytest.approx(right.fire_at - right_now)


def test_population_stays_desynchronized_over_a_full_leg(population_files) -> None:
    host = connected_host(population_files(29))
    timers = [heartbeat(agent) for agent in host.agents.values()]
    peak = 0
    for now in range(0, 9001, 2):
        due = 0
        for timer in timers:
            if timer.fire_due(now) is not None:
                due += 1
                assert 30 <= timer.fire_at - now <= 75
        peak = max(peak, due)
    assert peak <= math.ceil(len(timers) * 0.25)
    assert min(timer.seq for timer in timers) > 100


def test_reconnect_restores_phase_and_keeps_randomized_intervals() -> None:
    agent, _client, clock = make_agent()
    agent.brain = None
    assert agent.connect()
    timer = heartbeat(agent)
    initial = timer.fire_at
    intervals = []
    for _ in range(20):
        now = timer.fire_at
        timer.fire_due(now)
        intervals.append(timer.fire_at - now)
    assert all(2 <= interval <= 3 for interval in intervals)
    assert len(set(intervals)) > 1
    agent.disconnect()
    clock.now = 100
    for _ in range(50):
        agent.rng.random()
    assert agent.connect()
    assert heartbeat(agent).fire_at - clock.now == pytest.approx(initial)


def test_fixed_bounds_remain_fixed(population_files) -> None:
    host = connected_host(population_files(7), bounds=(30, 30))
    for agent in host.agents.values():
        timer = heartbeat(agent)
        assert timer.fire_at == 30
        assert timer.fire_due(30) is not None
        assert timer.fire_at == 60


def test_slow_startup_decide_does_not_consume_the_phase(monkeypatch) -> None:
    agent, _client, clock = make_agent()

    def slow_start() -> TickResult:
        clock.now += 90
        return TickResult((), {})

    monkeypatch.setattr(agent, "_start_brain", slow_start)
    assert agent.connect()
    assert 2 <= heartbeat(agent).fire_at - clock.now <= 3


@pytest.mark.parametrize("delay", [29, 76, float("nan")])
def test_explicit_startup_delay_cannot_escape_timer_bounds(delay: float) -> None:
    with pytest.raises(ValueError, match="within"):
        RandomTimer("idle_review", 30, 75, FakeClock(), first_delay_s=delay)


def test_phase_spacing_uses_only_the_hosted_population(population_files) -> None:
    host = connected_host(population_files(29), limit=7)
    phases = sorted(heartbeat(agent).fire_at - 30 for agent in host.agents.values())
    assert phases == pytest.approx([(i + 0.5) * 45 / 7 for i in range(7)])
