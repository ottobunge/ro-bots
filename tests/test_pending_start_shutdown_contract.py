"""Pending-start shutdown must return without discarding active producer ownership."""

import argparse
import threading
import traceback
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from robots import playing
from robots.app.agent_runtime import AgentHost
from tests.test_agent_host import make_agent
from tests.test_playing_startup_cleanup import OwnedWire, host_for

_REAL_START = threading.Thread.start


@contextmanager
def pending_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, origin: BaseException
) -> Iterator[tuple[AgentHost, OwnedWire, threading.Event]]:
    wire = OwnedWire()
    host = host_for(tmp_path, wire, origin)
    agent = host.agents["one"]
    agent.brain = None
    agent._threaded = True
    entered, release = threading.Event(), threading.Event()
    real_start = threading.Thread.start

    def producer() -> None:
        entered.set()
        release.wait()

    def interrupted_start(worker: threading.Thread) -> None:
        real_start(worker)
        assert entered.wait(2)
        raise origin

    monkeypatch.setattr(agent, "_run_loop", producer)
    monkeypatch.setattr(threading.Thread, "start", interrupted_start)
    try:
        yield host, wire, release
    finally:
        release.set()
        monkeypatch.setattr(threading.Thread, "start", real_start)
        if agent.thread is not None:
            agent.thread.join(2)
            assert not agent.thread.is_alive()
        host.stop()


@pytest.mark.parametrize("operation", ["stop", "disconnect"])
def test_pending_shutdown_returns_with_live_resources(tmp_path, monkeypatch, operation):
    with pending_host(tmp_path, monkeypatch, KeyboardInterrupt()) as (host, wire, release):
        agent = host.agents["one"]
        with pytest.raises(KeyboardInterrupt):
            agent.connect()
        worker = agent.thread
        assert worker is not None
        other, other_client, _ = make_agent()
        host.agents[other.persona.persona_id] = other
        assert other.connect()
        memory_closed: list[bool] = []
        monkeypatch.setattr(agent.memory, "close", lambda: memory_closed.append(True))
        done = threading.Event()
        errors: list[BaseException] = []

        def shutdown() -> None:
            try:
                (host.stop if operation == "stop" else agent.disconnect)()
            except BaseException as exc:
                errors.append(exc)
            finally:
                done.set()

        runner = threading.Thread(target=shutdown)
        # Do not apply the synthetic interrupted-start boundary to the harness.
        _REAL_START(runner)
        returned = done.wait(2)
        retained = agent.thread is worker and worker.is_alive() and wire.closed == 0
        other_attempted = not other_client.connected
        release.set()
        runner.join(2)
        assert not runner.is_alive()
        assert returned, "pending-start shutdown waited for producer release"
        assert retained
        assert errors
        assert isinstance(errors[0], RuntimeError)
        assert not memory_closed
        assert agent._producer_start_pending
        assert agent.connect() is False
        if operation == "stop":
            assert other_attempted


@pytest.mark.parametrize("kind", [RuntimeError, SystemExit, KeyboardInterrupt])
@pytest.mark.parametrize("cleanup_kind", [OSError, SystemExit])
def test_run_host_keeps_origin_when_pending_join_fails(
    tmp_path, monkeypatch, caplog, kind, cleanup_kind
):
    origin = kind("private startup detail")
    with pending_host(tmp_path, monkeypatch, origin) as (host, wire, _):
        agent = host.agents["one"]
        real_join = threading.Thread.join
        closed: list[bool] = []
        monkeypatch.setattr(agent.memory, "close", lambda: closed.append(True))

        def failed_join(worker: threading.Thread, timeout: float | None = None) -> None:
            msg = "private shutdown detail"
            raise cleanup_kind(msg)

        monkeypatch.setattr(threading.Thread, "join", failed_join)
        try:
            with pytest.raises(kind) as caught:
                playing.run_host(host, 0.01)
            assert caught.value is origin
            assert traceback.extract_tb(origin.__traceback__)[-1].name == "interrupted_start"
            assert agent.thread is not None
            assert agent.thread.is_alive()
            assert agent._producer_start_pending
            assert agent._client_cleanup_pending
            assert wire.closed == 0
            assert not closed
            notes = str(origin.__notes__)
            assert "shutdown" in notes
            assert cleanup_kind.__name__ in notes
            assert "private shutdown detail" not in notes + caplog.text
            assert "private startup detail" not in notes + caplog.text
        finally:
            monkeypatch.setattr(threading.Thread, "join", real_join)


@pytest.mark.parametrize("kind", [RuntimeError, SystemExit, KeyboardInterrupt])
def test_unpublished_start_stays_owned_until_explicit_join(tmp_path, monkeypatch, kind):
    origin = kind("unpublished")
    wire = OwnedWire()
    host = host_for(tmp_path, wire, origin)
    agent = host.agents["one"]
    agent.brain = None
    agent._threaded = True
    monkeypatch.setattr(agent, "_run_loop", lambda: None)
    closed: list[bool] = []
    monkeypatch.setattr(agent.memory, "close", lambda: closed.append(True))

    def unpublished_start(worker: threading.Thread) -> None:
        raise origin

    monkeypatch.setattr(threading.Thread, "start", unpublished_start)
    try:
        with pytest.raises(kind) as caught:
            agent.connect()
        assert caught.value is origin
        worker = agent.thread
        assert worker is not None
        assert worker.ident is None
        assert not worker.is_alive()
        with pytest.raises(RuntimeError, match="cannot join"):
            host.stop()
        assert agent.thread is worker
        assert agent._producer_start_pending
        assert agent._client_cleanup_pending
        assert wire.closed == 0
        assert not closed
        assert agent.connect() is False
        assert wire.connects == 1
    finally:
        if agent.thread is not None:
            _REAL_START(agent.thread)
            agent.thread.join(2)
        host.stop()
    assert wire.closed == 1
    assert closed == [True]
    reaped = host.agents["one"]
    assert reaped.thread is None
    assert not reaped._producer_start_pending


@pytest.mark.parametrize("kind", [RuntimeError, SystemExit, KeyboardInterrupt])
def test_explicit_reap_closes_client_before_journal(tmp_path, monkeypatch, kind):
    with pending_host(tmp_path, monkeypatch, kind()) as (host, wire, release):
        agent = host.agents["one"]
        with pytest.raises(kind):
            agent.connect()
        worker = agent.thread
        assert worker is not None
        with pytest.raises(RuntimeError, match="still alive"):
            host.stop()
        assert agent.thread is worker
        assert agent.connect() is False
        release.set()
        worker.join(2)
        assert not worker.is_alive()
        observed: list[str] = []
        real_close: Callable[[], None] = wire.close
        real_memory_close = agent.memory.close

        def close_client() -> None:
            assert agent.thread is None
            assert not agent._producer_start_pending
            assert not worker.is_alive()
            observed.append("client")
            real_close()

        def close_memory() -> None:
            assert wire.closed == 1
            assert not worker.is_alive()
            observed.append("journal")
            real_memory_close()

        monkeypatch.setattr(wire, "close", close_client)
        monkeypatch.setattr(agent.memory, "close", close_memory)
        host.stop()
        assert observed == ["client", "journal"]
        assert not agent._client_cleanup_pending


@pytest.mark.parametrize("kind", [OSError, SystemExit])
def test_normal_run_propagates_shutdown_failure(tmp_path, monkeypatch, kind):
    wire = OwnedWire()
    host = host_for(tmp_path, wire, RuntimeError())
    origin = kind("synthetic shutdown")

    def stop() -> None:
        raise origin

    real_stop = host.stop
    monkeypatch.setattr(host, "stop", stop)
    try:
        with pytest.raises(kind) as caught:
            playing.run_host(host, 0)
        assert caught.value is origin
    finally:
        real_stop()


def test_successful_online_start_keeps_default_join_policy(tmp_path, monkeypatch):
    wire = OwnedWire()
    host = host_for(tmp_path, wire, RuntimeError())
    agent = host.agents["one"]
    agent.brain = None
    agent._threaded = True
    monkeypatch.setattr(agent, "_run_loop", lambda: None)
    assert agent.connect()
    real_join = threading.Thread.join
    calls: list[float | None] = []

    def observed_join(worker: threading.Thread, timeout: float | None = None) -> None:
        calls.append(timeout)
        real_join(worker, timeout)

    monkeypatch.setattr(threading.Thread, "join", observed_join)
    host.stop()
    assert calls == [None]
    assert wire.closed == 1


def test_keyboard_interrupt_cli_policy_survives_shutdown_failure(tmp_path, monkeypatch):
    with pending_host(tmp_path, monkeypatch, KeyboardInterrupt()) as (host, wire, _):
        monkeypatch.setattr(playing, "build_host", lambda _args: host)
        monkeypatch.setattr(playing, "parse_args", lambda _argv: argparse.Namespace(duration=0.01))
        assert playing.main([]) == 0
        assert host.agents["one"]._producer_start_pending
        assert wire.closed == 0
