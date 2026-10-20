"""Actual private journal and owning-loop interruption regressions, offline only."""

from __future__ import annotations

import stat
import threading
from contextlib import suppress
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from robots.adapters.memory_journal import JsonlExperienceStore
from robots.adapters.worldfeed_server import create_app
from tests.test_host_chat_commands import command
from tests.test_host_memory import memory_host


@pytest.fixture
def journal_api(tmp_path: Path):
    root = tmp_path / "journal"
    host = memory_host(tmp_path, memory_root=root, max_agents=2)
    agents = list(host.agents.values())
    for agent in agents:
        agent._threaded = False
        assert agent.connect()
        agent.brain = None
        assert agent.client is not None
        agent.client.said.clear()
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in root.iterdir())
    assert host.world_state is not None
    with TestClient(create_app(host.world_state, command_dispatcher=host.commands)) as api:
        yield host, agents, api, root
    # Poisoning is deliberate; shutdown must nevertheless release every owner.
    with suppress(OSError):
        host.stop()
    assert all(
        agent.thread is None and agent.client is not None and not agent.client.connected
        for agent in agents
    )
    for agent in agents:
        reopened = JsonlExperienceStore(root, agent.persona.persona_id)
        reopened.close()


def interrupt_write(agent: Any, monkeypatch: pytest.MonkeyPatch, origin: BaseException, at: int):
    store = agent.memory.log._store
    write = store._file.write
    calls = 0

    def interrupted_write(text: str) -> int:
        nonlocal calls
        if "operator interrupted " in text:
            calls += 1
            if calls == at:
                # Real bytes can precede the interruption: retain poisoned ownership.
                write(text)
                store._file.flush()
                raise origin
        return int(write(text))

    monkeypatch.setattr(store._file, "write", interrupted_write)


def assert_terminal(api: TestClient, agent: Any, expected: str, origin: BaseException):
    status = api.get("/commands/interrupted").json()
    assert status["status"] == expected
    assert status["phase"] == "terminal"
    assert status["audit_error_class"] == type(origin).__name__
    assert status["error_class"] is None
    assert status["delivery_confirmation"] is False
    assert "private-origin" not in str(status)
    assert api.post("/commands", json=command(agent, "interrupted")).json() == status
    with pytest.raises(OSError, match="journal failed"):
        agent.memory.remember("other", "poisoned writer must not retry")


@pytest.mark.parametrize("exception_type", [SystemExit, KeyboardInterrupt])
def test_pre_send_actual_write_interrupt_is_failed(journal_api, monkeypatch, exception_type):
    _, agents, api, _ = journal_api
    agent = agents[0]
    origin = exception_type("private-origin")
    interrupt_write(agent, monkeypatch, origin, 1)
    assert api.post("/commands", json=command(agent, "interrupted")).status_code == 200
    with pytest.raises(exception_type) as caught:
        agent.tick()
    assert caught.value is origin
    assert any(frame.name == "interrupted_write" for frame in caught.traceback)
    assert agent.client.said == []
    assert_terminal(api, agent, "failed", origin)


@pytest.mark.parametrize("exception_type", [SystemExit, KeyboardInterrupt])
def test_post_send_actual_write_interrupt_is_dispatched(journal_api, monkeypatch, exception_type):
    _, agents, api, _ = journal_api
    agent = agents[0]
    origin = exception_type("private-origin")
    interrupt_write(agent, monkeypatch, origin, 2)
    assert api.post("/commands", json=command(agent, "interrupted")).status_code == 200
    with pytest.raises(exception_type) as caught:
        agent.tick()
    assert caught.value is origin
    assert any(frame.name == "interrupted_write" for frame in caught.traceback)
    assert agent.client.said == ["hello from operator"]
    assert_terminal(api, agent, "dispatched", origin)
    assert agent.client.said == ["hello from operator"]


@pytest.mark.parametrize("exception_type", [SystemExit, KeyboardInterrupt])
@pytest.mark.parametrize("effects", [0, 1])
def test_send_boundary_interrupt_stays_uncertain(journal_api, monkeypatch, exception_type, effects):
    _, agents, api, _ = journal_api
    agent = agents[0]
    origin = exception_type("private-origin")

    def interrupted_send(text):
        if effects:
            agent.client.said.append(text)
        raise origin

    monkeypatch.setattr(agent.client, "say", interrupted_send)
    api.post("/commands", json=command(agent, "interrupted"))
    with pytest.raises(exception_type) as caught:
        agent.tick()
    assert caught.value is origin
    assert any(frame.name == "interrupted_send" for frame in caught.traceback)
    status = api.get("/commands/interrupted").json()
    assert status["status"] == "uncertain"
    assert status["phase"] == "terminal"
    assert status["error_class"] == exception_type.__name__
    assert status["audit_error_class"] is None
    assert status["delivery_confirmation"] is False
    assert "private-origin" not in str(status)
    assert api.post("/commands", json=command(agent, "interrupted")).json() == status
    agent.tick()
    assert len(agent.client.said) == effects


def start_worker(agent: Any, errors: list[BaseException]) -> threading.Thread:
    def guarded():
        try:
            agent._run_loop()
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=guarded, daemon=True)
    agent.thread = worker
    worker.start()
    return worker


@pytest.mark.parametrize("exception_type", [SystemExit, KeyboardInterrupt])
@pytest.mark.parametrize("failure_at", [1, 2])
def test_actual_worker_death_refuses_new_work_and_retains_cleanup(
    journal_api, monkeypatch, exception_type, failure_at
):
    host, agents, api, root = journal_api
    agent, other = agents
    origin = exception_type("private-origin")
    interrupt_write(agent, monkeypatch, origin, failure_at)
    api.post("/commands", json=command(agent, "interrupted"))
    api.post("/commands", json=command(agent, "unsent"))
    api.post("/commands", json=command(other, "independent"))
    errors: list[BaseException] = []
    worker = start_worker(agent, errors)
    worker.join(5)
    assert not worker.is_alive()
    assert errors == [origin]
    assert agent.online
    assert agent.client.connected
    assert agent.thread is worker
    # Death is an admission failure, not transport/journal ownership release.
    response = api.post("/commands", json=command(agent, "after-death"))
    assert response.status_code in {409, 503}
    assert "offline" in response.json()["detail"] or "stopp" in response.json()["detail"]
    assert api.get("/commands/unsent").json()["status"] == "cancelled"
    assert api.get("/commands/unsent").json()["phase"] == "terminal"
    assert_terminal(api, agent, "failed" if failure_at == 1 else "dispatched", origin)
    assert len(agent.client.said) == failure_at - 1
    assert api.get("/commands/independent").json()["status"] == "queued"
    other.tick()
    assert other.client.said == ["hello from operator"]
    with pytest.raises(BlockingIOError):
        JsonlExperienceStore(root, agent.persona.persona_id)
    with pytest.raises(OSError, match="journal failed"):
        host.stop()
    assert all(a.thread is None and not a.client.connected for a in agents)
    assert api.post("/commands", json=command(agent, "interrupted")).json()["phase"] == "terminal"


@pytest.mark.parametrize("exception_type", [SystemExit, KeyboardInterrupt])
@pytest.mark.parametrize("boundary", ["tick", "sleep", "send"])
def test_other_worker_interruptions_cancel_only_unsent(
    journal_api, monkeypatch, exception_type, boundary
):
    host, agents, api, _ = journal_api
    agent, other = agents
    origin = exception_type("private-origin")
    api.post("/commands", json=command(agent, "interrupted"))
    api.post("/commands", json=command(agent, "unsent"))
    api.post("/commands", json=command(other, "other-sending"))
    other_request = host.commands.take(other.persona.persona_id)
    assert other_request is not None
    assert host.commands.begin_send(other_request)

    def fail(*_args):
        raise origin

    if boundary == "tick":
        monkeypatch.setattr(agent, "tick", fail)
    elif boundary == "sleep":
        monkeypatch.setattr(agent, "tick", lambda: None)
        monkeypatch.setattr(agent._tick_clock, "sleep", fail)
    else:
        monkeypatch.setattr(agent.client, "say", fail)
    errors: list[BaseException] = []
    worker = start_worker(agent, errors)
    worker.join(5)
    assert not worker.is_alive()
    assert errors == [origin]
    assert agent.stop_flag
    assert agent.online
    assert agent.client.connected
    assert api.post("/commands", json=command(agent, "late")).status_code == 409
    status = api.get("/commands/interrupted").json()
    assert status["status"] == ("uncertain" if boundary == "send" else "cancelled")
    assert status["phase"] == "terminal"
    assert status["delivery_confirmation"] is False
    assert api.post("/commands", json=command(agent, "interrupted")).json() == status
    assert api.get("/commands/unsent").json()["status"] == "cancelled"
    assert api.get("/commands/other-sending").json()["phase"] == "sending"
    assert agent.client.said == []


def test_worker_cancellation_error_does_not_mask_origin(journal_api, monkeypatch, caplog):
    host, agents, api, _ = journal_api
    agent = agents[0]
    origin = KeyboardInterrupt("private-origin")

    def fail_tick():
        raise origin

    def fail_cancel(_persona_id):
        msg = "private-cleanup-detail"
        raise SystemExit(msg)

    with monkeypatch.context() as patcher:
        patcher.setattr(agent, "tick", fail_tick)
        patcher.setattr(host.commands, "cancel_pending", fail_cancel)
        errors: list[BaseException] = []
        worker = start_worker(agent, errors)
        worker.join(5)
    assert not worker.is_alive()
    assert errors == [origin]
    assert agent.stop_flag
    assert agent.online
    assert agent.client.connected
    assert api.post("/commands", json=command(agent, "late")).status_code == 409
    assert "SystemExit" in caplog.text
    assert "private-cleanup-detail" not in caplog.text


def test_stop_join_does_not_deadlock_interrupting_worker(journal_api, monkeypatch):
    host, agents, api, _ = journal_api
    agent = agents[0]
    entered, release, joining = (threading.Event() for _ in range(3))
    origin = SystemExit("private-origin")
    write = agent.memory.log._store._file.write

    def blocked_write(text):
        if "operator interrupted " in text:
            entered.set()
            assert release.wait(5)
            raise origin
        return write(text)

    monkeypatch.setattr(agent.memory.log._store._file, "write", blocked_write)
    api.post("/commands", json=command(agent, "interrupted"))
    worker_errors: list[BaseException] = []
    worker = start_worker(agent, worker_errors)
    assert entered.wait(5)

    def observed_join(timeout=None, join=worker.join):
        joining.set()
        join(timeout)

    monkeypatch.setattr(worker, "join", observed_join)
    closed: list[str] = []
    for owned in agents:
        close = owned.memory.close

        def observed_close(owned=owned, close=close):
            assert not worker.is_alive()
            closed.append(owned.persona.persona_id)
            close()

        monkeypatch.setattr(owned.memory, "close", observed_close)
    stop_errors: list[BaseException] = []

    def stop():
        try:
            host.stop()
        except BaseException as exc:
            stop_errors.append(exc)

    stopper = threading.Thread(target=stop, daemon=True)
    stopper.start()
    try:
        assert joining.wait(5)
        assert closed == []
        assert api.post("/commands", json=command(agent, "late")).status_code == 503
    finally:
        release.set()
        worker.join(5)
        stopper.join(5)
    assert not worker.is_alive()
    assert not stopper.is_alive()
    assert worker_errors == [origin]
    assert len(stop_errors) == 1
    assert isinstance(stop_errors[0], OSError)
    assert len(closed) == len(agents)
    assert all(a.thread is None and not a.client.connected for a in agents)
