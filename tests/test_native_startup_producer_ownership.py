"""Interrupted Python producer startup: real threads, synthetic host/client only."""

import threading
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from robots import playing
from robots.app.agent_runtime import AgentHost
from tests.test_agent_host import make_agent
from tests.test_playing_startup_cleanup import OwnedWire, host_for


@contextmanager
def interrupted_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, origin: BaseException
) -> Iterator[tuple[AgentHost, OwnedWire, list[threading.Thread], threading.Event]]:
    wire = OwnedWire()
    host = host_for(tmp_path, wire, origin)
    agent = host.agents["one"]
    agent.brain = None
    agent._threaded = True
    entered = threading.Event()
    release = threading.Event()
    workers: list[threading.Thread] = []
    real_start = threading.Thread.start

    def producer() -> None:
        entered.set()
        release.wait()

    def interrupted_start(worker: threading.Thread) -> None:
        workers.append(worker)
        real_start(worker)
        assert entered.wait(1)
        raise origin

    monkeypatch.setattr(agent, "_run_loop", producer)
    monkeypatch.setattr(threading.Thread, "start", interrupted_start)
    try:
        yield host, wire, workers, release
    finally:
        release.set()
        for worker in workers:
            worker.join(2)
            assert not worker.is_alive()
        host.stop()


@pytest.mark.parametrize("kind", [KeyboardInterrupt, SystemExit])
def test_interrupted_thread_start_retains_live_producer(tmp_path, monkeypatch, kind):
    origin = kind("cancel startup")
    with interrupted_host(tmp_path, monkeypatch, origin) as (host, wire, workers, _):
        agent = host.agents["one"]
        with pytest.raises(kind) as caught:
            agent.connect()
        assert caught.value is origin
        assert traceback.extract_tb(origin.__traceback__)[-1].name == "interrupted_start"
        assert workers[0].is_alive()
        assert agent.thread is workers[0]
        assert wire.closed == 0
        assert agent._client_cleanup_pending
        assert agent.stop_flag
        assert agent.connect() is False
        assert wire.connects == 1


def test_run_host_finally_does_not_close_memory_with_live_startup_worker(tmp_path, monkeypatch):
    origin = SystemExit("cancel startup")
    with interrupted_host(tmp_path, monkeypatch, origin) as (host, wire, workers, release):
        observations: list[bool] = []
        agent = host.agents["one"]
        memory = agent.memory
        real_close = memory.close

        def observed_close() -> None:
            observations.append(workers[0].is_alive())
            real_close()

        monkeypatch.setattr(memory, "close", observed_close)
        with pytest.raises(SystemExit) as caught:
            playing.run_host(host, 0.01)
        assert caught.value is origin
        assert traceback.extract_tb(origin.__traceback__)[-1].name == "interrupted_start"
        assert workers[0].is_alive()
        assert agent.thread is workers[0]
        assert agent._producer_start_pending
        assert agent._client_cleanup_pending
        assert observations == []
        assert wire.closed == 0
        with pytest.raises(RuntimeError):
            host.stop()
        assert observations == []
        assert wire.closed == 0
        release.set()
        workers[0].join(2)
        assert not workers[0].is_alive()
        host.stop()
        reaped = host.agents["one"]
        assert reaped.thread is None
        assert not reaped._producer_start_pending
        assert not reaped._client_cleanup_pending
        assert observations == [False]
        assert wire.closed == 1


@pytest.mark.parametrize("kind", [KeyboardInterrupt, RuntimeError])
def test_join_failure_keeps_resources_and_exact_origin(tmp_path, monkeypatch, kind):
    origin = kind("cancel startup")
    with interrupted_host(tmp_path, monkeypatch, origin) as (host, wire, workers, _):
        agent = host.agents["one"]
        real_join = threading.Thread.join
        closed: list[bool] = []

        def failed_join(worker: threading.Thread, timeout: float | None = None) -> None:
            msg = "private join detail"
            raise OSError(msg)

        monkeypatch.setattr(threading.Thread, "join", failed_join)
        monkeypatch.setattr(agent.memory, "close", lambda: closed.append(True))
        try:
            with pytest.raises(kind) as caught:
                agent.connect()
            assert caught.value is origin
            assert traceback.extract_tb(origin.__traceback__)[-1].name == "interrupted_start"
            with pytest.raises(OSError, match="private join detail"):
                host.stop()
            assert not closed
            assert wire.closed == 0
            assert agent.thread is workers[0]
            assert agent._client_cleanup_pending
            assert "private join detail" not in str(origin.__notes__)
            assert agent.connect() is False
            other, other_client, _ = make_agent()
            host.agents[other.persona.persona_id] = other
            assert other.connect()
            with pytest.raises(OSError, match="private join detail"):
                host.stop()
            assert not other_client.connected
            assert not closed
        finally:
            monkeypatch.setattr(threading.Thread, "join", real_join)


@pytest.mark.parametrize("kind", [KeyboardInterrupt, SystemExit])
def test_unpublished_start_is_not_proven_absent(tmp_path, monkeypatch, kind):
    origin = kind("cancel before publication")
    wire = OwnedWire()
    host = host_for(tmp_path, wire, origin)
    agent = host.agents["one"]
    agent.brain = None
    agent._threaded = True
    real_start = threading.Thread.start
    closed: list[bool] = []

    def interrupted_start(worker: threading.Thread) -> None:
        raise origin

    monkeypatch.setattr(threading.Thread, "start", interrupted_start)
    monkeypatch.setattr(agent.memory, "close", lambda: closed.append(True))
    try:
        with pytest.raises(kind) as caught:
            agent.connect()
        assert caught.value is origin
        worker = agent.thread
        assert worker is not None
        assert worker.ident is None
        assert not worker.is_alive()
        assert agent.connect() is False
        with pytest.raises(RuntimeError, match="cannot join"):
            host.stop()
        assert not closed
        assert wire.closed == 0
        assert agent._producer_start_pending
        assert agent._client_cleanup_pending
    finally:
        # Harness supplies the missing publication/termination proof, never production.
        if agent.thread is not None:
            real_start(agent.thread)
            agent.thread.join(2)
        host.stop()


@pytest.mark.parametrize("kind", [KeyboardInterrupt, SystemExit, RuntimeError])
def test_confirmed_terminated_start_releases_client(tmp_path, monkeypatch, kind):
    origin = kind("cancel after termination")
    wire = OwnedWire()
    host = host_for(tmp_path, wire, origin)
    agent = host.agents["one"]
    agent.brain = None
    agent._threaded = True
    real_start = threading.Thread.start

    def terminated_start(worker: threading.Thread) -> None:
        real_start(worker)
        worker.join(2)
        assert not worker.is_alive()
        raise origin

    monkeypatch.setattr(agent, "_run_loop", lambda: None)
    monkeypatch.setattr(threading.Thread, "start", terminated_start)
    if isinstance(origin, Exception):
        assert agent.connect() is False
    else:
        with pytest.raises(kind) as caught:
            agent.connect()
        assert caught.value is origin
    assert agent.thread is None
    assert not agent._producer_start_pending
    assert wire.closed == 1
    assert not agent._client_cleanup_pending
    host.stop()
    assert wire.closed == 1
