"""Offline leg-102 regression: a dead client must re-enter scheduled login."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from robots.app import scripts
from robots.app.agent_runtime import AgentHost, LoginStagger, ManifestEntry, WallClock
from robots.app.playing_runtime import PlayingClient
from robots.app.world_state import WorldState
from tests.test_agent_host import (
    FakeGameClient,
    FakeSocietyClock,
    ScriptedDecisionModel,
    _StaticChat,
    make_agent,
    make_roster,
    write_manifest,
)
from tests.test_playing_runtime import Wire
from tests.test_population_runner_transport_reporting import runner_module


@pytest.fixture(autouse=True)
def fresh_script_memos():
    scripts.reset_merchant_talk()
    scripts._KILL_COMMITMENTS.clear()
    yield
    scripts.reset_merchant_talk()
    scripts._KILL_COMMITMENTS.clear()


class TransportClient(FakeGameClient):
    def __init__(self, entry: ManifestEntry, *, fail: bool = False) -> None:
        super().__init__(entry)
        self.rx_error: Exception | None = None
        self.fail = fail
        self.connects = 0
        self.closes = 0

    def connect(self) -> TransportClient:
        self.connects += 1
        if self.fail:
            message = "synthetic login refused"
            raise ConnectionError(message)
        self.rx_error = None
        super().connect()
        return self

    def close(self) -> None:
        self.closes += 1
        super().close()


def rebuild_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Any, list[float]]:
    roster = make_roster()
    host: Any = AgentHost(
        roster,
        write_manifest(tmp_path),
        decision_factory=lambda *_: ScriptedDecisionModel({}),
        chat_generator=_StaticChat(),
        clock=FakeSocietyClock(),
        world_state=WorldState(roster),
        run_worldfeed=False,
    )
    host.agents = {}
    for pid in list(roster.personas)[:2]:
        agent, _, _ = make_agent(pid, roster=roster, world_state=host.world_state)
        agent.client = TransportClient(agent.entry)
        agent._client_factory = TransportClient
        host.agents[pid] = agent
    host.login_stagger = LoginStagger(interval_s=0.0)
    monkeypatch.setattr(host, "_scheduled_on", lambda *_: True)
    now = [1000.0]
    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    host.step()
    return host, now


def test_mid_window_failure_rebuilds_once_then_grows_backoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host, now = rebuild_host(tmp_path, monkeypatch)
    agent, other = host.agents.values()
    old = agent.client
    created: list[TransportClient] = []

    def factory(entry: ManifestEntry) -> TransportClient:
        client = TransportClient(entry, fail=True)
        created.append(client)
        return client

    agent._client_factory = factory
    old.rx_error = ValueError("unknown packet 0x019b at 112")
    now[0] = 1001.0
    host.step()
    assert not agent.online, "transport death must clear cosmetic online immediately"
    assert old.closes == 1
    assert not created, "failure detection schedules; it must not login in a tight loop"
    assert not agent.pending_switch, "recovery must preserve the selected character"
    gate = host._connect_gates[agent.persona.persona_id]
    assert gate.delay() == 5.0
    for _ in range(5):
        host.step()
    assert not created
    now[0] = 1006.0
    host.step()
    assert len(created) == 1
    assert created[0].connects == 1
    assert gate.delay() == 10.0
    for _ in range(5):
        other.tick()
        host.step()
    assert len(created) == 1
    assert other.online
    assert other.tick_count == 5
    assert agent.tick_count == 0
    assert agent.rebuild_attempts == 1
    host.stop()


@pytest.mark.parametrize("error", [ValueError("bad frame"), ConnectionError("EOF")])
def test_successful_relogin_resumes_same_persona_and_real_decisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    host, now = rebuild_host(tmp_path, monkeypatch)
    agent = next(iter(host.agents.values()))
    old, brain, memory, entry = agent.client, agent.brain, agent.memory, agent.entry
    decisions = brain.decision_count
    old.rx_error = error
    now[0] += 1
    host.step()
    assert not agent.online
    assert host.world_state is not None
    assert not host.world_state.agent_state(agent.persona.persona_id).online
    now[0] += 5
    host.step()
    assert agent.online
    assert agent.client.connected
    assert (agent.client is old) == isinstance(error, OSError)
    assert agent.brain is brain
    assert agent.memory is memory
    assert agent.entry is entry
    assert brain.decision_count > decisions
    agent.tick()
    assert agent.tick_count == 1
    assert host.world_state.agent_state(agent.persona.persona_id).online
    host.stop()


def test_failed_rebuilds_share_login_stagger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host, now = rebuild_host(tmp_path, monkeypatch)
    host.login_stagger = LoginStagger()
    for agent in host.agents.values():
        agent.client.rx_error = ValueError("bad frame")
        agent._client_factory = lambda entry: TransportClient(entry, fail=True)
    now[0] += 1
    host.step()
    now[0] += 5
    host.step()
    first, second = host.agents.values()
    assert first.rebuild_attempts == 1
    assert second.rebuild_attempts == 0, "failed logins also consume shared throttle spacing"
    now[0] += host.login_stagger.interval_s
    host.step()
    assert second.rebuild_attempts == 1
    host.stop()


@pytest.mark.parametrize("successful", [False, True])
def test_runner_receipt_names_recovery_and_never_reports_dead_online(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    successful: bool,
) -> None:
    host, now = rebuild_host(tmp_path, monkeypatch)
    agent, other = host.agents.values()
    old = agent.client
    pid = agent.persona.persona_id
    # Two failed logins leave a down sample at t=30; the third either recovers
    # at t=36 or exhausts the window's budget. All clocks and clients are local.
    attempts: list[TransportClient] = []

    def factory(entry: ManifestEntry) -> TransportClient:
        client = TransportClient(entry, fail=not (successful and len(attempts) == 2))
        attempts.append(client)
        return client

    agent._client_factory = factory

    def advance(seconds: float) -> None:
        now[0] += seconds
        if now[0] >= 1001 and old.rx_error is None:
            old.rx_error = ValueError("unknown packet 0x019b at 112")
        for scheduled_agent in host.agents.values():
            if scheduled_agent.online:
                scheduled_agent.tick()

    module = runner_module()
    from robots import playing  # noqa: PLC0415

    monkeypatch.setattr(playing, "build_host", lambda _: host)
    monkeypatch.setattr(module.time, "time", lambda: now[0])
    monkeypatch.setattr(module.time, "sleep", advance)
    monkeypatch.setattr(host, "start_worldfeed", lambda: None)
    assert (
        module.main(
            [
                "--manifest",
                "unused",
                "--runtime-root",
                "unused",
                "--memory-root",
                str(tmp_path),
                "--decision-url",
                "unused",
                "--chat-url",
                "unused",
                "--duration",
                "65",
                "--out-dir",
                str(tmp_path),
                "--leg",
                "offline102",
            ]
        )
        == 0
    )
    receipt = json.loads(next(tmp_path.glob("population-receipt-*.json")).read_text())
    down, final = receipt["samples"][1][pid], receipt["samples"][-1][pid]
    assert down["online"] is False
    assert down["rebuild_attempts"] == 2
    assert final["online"] is successful
    assert final["rebuild_attempts"] == 3
    assert final["rebuild_exhausted"] is not successful
    assert final["rx_error"] is None  # current client's health, separate from failure history
    assert "unknown packet 0x019b" in final["last_transport_error"]
    assert (final["decides"] > down["decides"]) is successful
    assert (final["ticks"] > down["ticks"]) is successful
    assert receipt["offline_agents"] == ([] if successful else [pid])
    assert "unknown packet 0x019b" in receipt["transport_recovery"][pid]["last_error"]
    assert other.tick_count > 100
    assert len(attempts) == 3
    assert capsys.readouterr().out.count("TRANSPORT DOWN") == 1
    host.stop()


@pytest.mark.parametrize("failure", ["rx", "socket", "reader", "keepalive"])
def test_playing_client_exposes_transport_death_without_observing_frames(failure: str) -> None:
    wire: Any = Wire()
    client = PlayingClient(wire)
    origin = ValueError("bad frame")
    if failure == "rx":
        wire.rx_error = origin
    elif failure == "socket":
        wire.sock = None
    elif failure == "reader":
        wire.rx_thread = None
    else:
        client._keepalive_failed = True
    before = list(wire.frames)
    assert client.transport_failure is not None
    if failure == "rx":
        assert client.transport_failure is origin
    assert wire.frames == before


def test_live_transport_dispatch_parse_error_does_not_schedule_rebuild() -> None:
    wire = Wire()
    wire.dispatch_errors.append((0x999, "per-frame failure"))
    client = PlayingClient(wire)
    assert client.transport_failure is None


def test_pending_character_itch_cannot_bypass_rebuild_backoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host, now = rebuild_host(tmp_path, monkeypatch)
    agent = next(iter(host.agents.values()))
    agent._pending_switch = True
    agent.client.rx_error = ValueError("bad frame")
    now[0] += 1
    host.step()
    assert not agent.online
    assert not agent.pending_switch
    assert agent.rebuild_attempts == 0
    host.stop()


def test_budget_is_per_window_and_includes_repeated_deaths_after_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host, now = rebuild_host(tmp_path, monkeypatch)
    agent = next(iter(host.agents.values()))
    for _ in range(host.MAX_TRANSPORT_REBUILDS):
        agent.client.rx_error = ValueError("bad frame")
        now[0] += 1
        host.step()
        now[0] += 5
        host.step()
        assert agent.online
    agent.client.rx_error = ValueError("bad frame again")
    now[0] += 1
    host.step()
    now[0] += 1000
    host.step()
    assert not agent.online
    assert agent.rebuild_exhausted
    assert agent.rebuild_attempts == host.MAX_TRANSPORT_REBUILDS
    monkeypatch.setattr(host, "_scheduled_on", lambda *_: False)
    host.step()
    monkeypatch.setattr(host, "_scheduled_on", lambda *_: True)
    host.step()
    assert agent.online
    assert agent.rebuild_attempts == 1
    assert not agent.rebuild_exhausted
    host.stop()


def test_cleanup_failure_stays_offline_without_losing_client_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host, now = rebuild_host(tmp_path, monkeypatch)
    agent, other = host.agents.values()
    old = agent.client

    def failed_close() -> None:
        message = "synthetic release unconfirmed"
        raise RuntimeError(message)

    original_close = old.close
    monkeypatch.setattr(old, "close", failed_close)
    old.rx_error = ValueError("bad frame")
    now[0] += 1
    host.step()
    now[0] += 1000
    host.step()
    other.tick()
    assert not agent.online
    assert agent.rebuild_exhausted
    assert agent.client is old
    assert agent.rebuild_attempts == 0
    assert other.tick_count == 1
    monkeypatch.setattr(old, "close", original_close)
    host.stop()


def test_slow_failed_login_waits_full_backoff_after_it_returns(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host, now = rebuild_host(tmp_path, monkeypatch)
    agent = next(iter(host.agents.values()))
    created: list[TransportClient] = []

    def factory(entry: ManifestEntry) -> TransportClient:
        now[0] += 35.0  # A slow failed handshake consumes wall time.
        client = TransportClient(entry, fail=True)
        created.append(client)
        return client

    agent._client_factory = factory
    agent.client.rx_error = ValueError("bad frame")
    now[0] += 1
    host.step()
    now[0] += 5
    host.step()
    assert len(created) == 1
    host.step()
    assert len(created) == 1, "elapsed handshake time must not consume the next backoff"
    now[0] += 10
    host.step()
    assert len(created) == 2
    host.stop()


def test_other_agent_thread_keeps_ticking_during_blocked_relogin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host, now = rebuild_host(tmp_path, monkeypatch)
    agent, other = host.agents.values()
    entered, release, stepped = threading.Event(), threading.Event(), threading.Event()

    class BlockingLogin(TransportClient):
        def connect(self) -> TransportClient:
            entered.set()
            assert release.wait(2), "test must release synthetic login"
            return super().connect()

    agent._client_factory = BlockingLogin
    agent.client.rx_error = ValueError("bad frame")
    now[0] += 1
    host.step()
    now[0] += 5
    scheduler = threading.Thread(target=host.step)
    scheduler.start()
    try:
        assert entered.wait(2)
        before = other.tick_count
        other._tick_clock = WallClock()
        other.tick_seconds = 0.005
        monkeypatch.setattr(other, "_publish", lambda *_: stepped.set())
        other.thread = threading.Thread(target=other._run_loop)
        other.thread.start()
        assert stepped.wait(2), "another agent must run while login is blocked"
        assert other.tick_count > before
        assert not agent.online
    finally:
        release.set()
        scheduler.join(2)
        host.stop()
    assert not scheduler.is_alive()
    assert agent.client.connected is False  # host.stop owns final release
