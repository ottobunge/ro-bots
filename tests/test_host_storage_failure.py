"""Offline shutdown faults: persistence failure must not strand owned resources."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from robots.adapters.memory_journal import JsonlExperienceStore
from robots.app.agent_runtime import AgentHost, ScheduledAgent
from robots.society.memory import ExperienceNote
from tests.test_host_memory import memory_host


def release_fixture(host: AgentHost) -> None:
    for agent in host.agents.values():
        agent.stop_flag = True
        if agent.thread is not None:
            agent.thread.join()
        agent.online = False
        assert agent.client is not None
        agent.client.close()
        agent.memory.close()


def assert_worldfeed_stopped(host: AgentHost) -> None:
    assert host._worldfeed_thread is None
    assert host._worldfeed_server is None


def assert_released(host: AgentHost, root: Path) -> None:
    assert host.world_state is not None
    for agent in host.agents.values():
        assert agent.stop_flag
        assert agent.thread is None
        assert not agent.online
        assert agent.client is not None
        assert not agent.client.connected
        state = host.world_state.agent_state(agent.persona.persona_id)
        assert state is not None
        assert not state.online
        probe = JsonlExperienceStore(root, agent.persona.persona_id)
        probe.close()


def start_final_inspector(
    host: AgentHost, release: threading.Event, errors: list[BaseException]
) -> tuple[SimpleNamespace, threading.Thread]:
    server = SimpleNamespace(should_exit=False)
    last = list(host.agents.values())[-1]

    def final_inspector_write() -> None:
        try:
            assert release.wait(5)
            assert server.should_exit
            last.memory.remember("other", "last-inspector-write")
        except BaseException as error:
            errors.append(error)

    inspector = threading.Thread(target=final_inspector_write)
    host._worldfeed_server, host._worldfeed_thread = server, inspector
    inspector.start()
    return server, inspector


def guard_journal_closes(
    host: AgentHost,
    producers: list[threading.Thread],
    monkeypatch: pytest.MonkeyPatch,
    *,
    closed: list[str] | None = None,
) -> list[str]:
    unsafe: list[str] = []
    closes = {pid: agent.memory.close for pid, agent in host.agents.items()}
    for pid, agent in host.agents.items():

        def checked_close(pid: str = pid) -> None:
            if any(thread.is_alive() for thread in producers):
                unsafe.append(pid)
                return  # Keep RED fixtures from inducing an actual post-close write.
            if closed is not None:
                closed.append(pid)
            closes[pid]()

        monkeypatch.setattr(agent.memory, "close", checked_close)
    return unsafe


def fail_session_append(
    agent: ScheduledAgent, failure: OSError, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = agent.memory.log._store
    assert isinstance(store, JsonlExperienceStore)
    append = store.append

    def fail_session(note: ExperienceNote) -> None:
        if note.kind == "session":
            raise failure
        append(note)

    monkeypatch.setattr(store, "append", fail_session)


def capture_stop(host: AgentHost, errors: list[BaseException]) -> None:
    try:
        host.stop()
    except BaseException as error:
        errors.append(error)


def start_blocked_worker(
    agent: ScheduledAgent, release: threading.Event, monkeypatch: pytest.MonkeyPatch
) -> threading.Thread:
    entered = threading.Event()

    def final_tick() -> None:
        entered.set()
        assert release.wait(5)
        agent.memory.remember("other", "last-worker-write")

    monkeypatch.setattr(agent, "tick", final_tick)
    assert agent.connect()
    assert entered.wait(5)
    assert agent.thread is not None
    return agent.thread


def observe_join(
    thread: threading.Thread, entered: threading.Event, monkeypatch: pytest.MonkeyPatch
) -> None:
    join = thread.join

    def join_without_timeout(timeout: float | None = None) -> None:
        assert timeout is None, "never abandon a live producer after a timeout"
        entered.set()
        join()

    monkeypatch.setattr(thread, "join", join_without_timeout)


def test_failed_session_note_disconnects_before_reporting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "world"
    host = memory_host(tmp_path, memory_root=root, max_agents=1)
    agent = next(iter(host.agents.values()))
    agent._threaded = False
    assert agent.connect()
    client = agent.client
    assert client is not None
    failure = OSError("session persistence failed")
    store = agent.memory.log._store
    assert isinstance(store, JsonlExperienceStore)

    def failed_write(text: str) -> int:
        raise failure

    monkeypatch.setattr(store._file, "write", failed_write)
    try:
        with pytest.raises(OSError, match="session persistence failed") as caught:
            agent.disconnect()
        assert caught.value is failure
        assert agent.stop_flag
        assert not agent.online
        assert not client.connected
        assert host.world_state is not None
        state = host.world_state.agent_state(agent.persona.persona_id)
        assert state is not None
        assert not state.online
        assert not any(note.kind == "session" for note in agent.memory.log.notes())
        with pytest.raises(OSError, match="journal failed"):
            store.load()
        agent.disconnect()
        host.stop()
        probe = JsonlExperienceStore(root, agent.persona.persona_id)
        assert not any(note.kind == "session" for note in probe.load())
        probe.close()
        host.stop()
    finally:
        # Even the RED run must release the fixture journal and fake client.
        agent.online = False
        client.close()
        agent.memory.close()


def leaf_errors(error: BaseException) -> list[BaseException]:
    if isinstance(error, BaseExceptionGroup):
        return [leaf for child in error.exceptions for leaf in leaf_errors(child)]
    return [error]


@pytest.mark.parametrize("failed_agents", [1, 2, 3])
def test_host_releases_every_resource_before_reporting_session_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed_agents: int
) -> None:
    root = tmp_path / "world"
    host = memory_host(tmp_path, memory_root=root, max_agents=3)
    failures = [OSError(f"session persistence failed {index}") for index in range(failed_agents)]
    for index, agent in enumerate(host.agents.values()):
        agent._threaded = False
        assert agent.connect()
        if index < failed_agents:
            store = agent.memory.log._store
            assert isinstance(store, JsonlExperienceStore)

            def fail_append(note: ExperienceNote, error: OSError = failures[index]) -> None:
                raise error

            monkeypatch.setattr(store, "append", fail_append)
    server = SimpleNamespace(should_exit=False)
    inspector_errors: list[BaseException] = []
    ready = threading.Event()

    def inspect_until_exit() -> None:
        ready.set()
        while not server.should_exit:
            threading.Event().wait(0.001)
        try:
            # Model an in-flight operator write on a healthy, offline persona.
            last = list(host.agents.values())[-1]
            if failed_agents < 3:
                last.memory.remember("other", "last-inspector-write")
        except BaseException as error:
            inspector_errors.append(error)

    inspector = threading.Thread(target=inspect_until_exit)
    host._worldfeed_server = server
    host._worldfeed_thread = inspector
    inspector.start()
    assert ready.wait(5)
    try:
        with pytest.raises((OSError, ExceptionGroup)) as caught:
            host.stop()
        assert leaf_errors(caught.value) == failures
        assert host._stop
        assert not inspector.is_alive()
        assert not inspector_errors
        assert_worldfeed_stopped(host)
        assert_released(host, root)
        for index, agent in enumerate(host.agents.values()):
            notes = agent.memory.log.notes()
            assert any(note.kind == "session" for note in notes) == (index >= failed_agents)
        before = [agent.memory.log.notes() for agent in host.agents.values()]
        host.stop()
        host.step()
        assert [agent.memory.log.notes() for agent in host.agents.values()] == before
    finally:
        server.should_exit = True
        inspector.join(5)
        release_fixture(host)


def test_stop_signals_every_worker_then_joins_inspector_before_any_journal_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "world"
    host = memory_host(tmp_path, memory_root=root, max_agents=3, tick_seconds=0.001)
    release_workers, release_inspector = threading.Event(), threading.Event()
    joining_worker, joining_inspector = threading.Event(), threading.Event()
    workers = [
        start_blocked_worker(agent, release_workers, monkeypatch) for agent in host.agents.values()
    ]
    first, _, last = host.agents.values()
    failure = OSError("failed final session note")
    fail_session_append(first, failure, monkeypatch)
    inspector_errors: list[BaseException] = []
    server, inspector = start_final_inspector(host, release_inspector, inspector_errors)
    observe_join(workers[0], joining_worker, monkeypatch)
    observe_join(inspector, joining_inspector, monkeypatch)
    closed: list[str] = []
    unsafe_closes = guard_journal_closes(host, [*workers, inspector], monkeypatch, closed=closed)
    stop_errors: list[BaseException] = []
    stopper = threading.Thread(target=capture_stop, args=(host, stop_errors))
    stopper.start()
    try:
        assert joining_worker.wait(5)
        assert all(agent.stop_flag for agent in host.agents.values())
        assert [agent.thread for agent in host.agents.values()] == workers
        assert not closed
        assert not stop_errors
        release_workers.set()
        assert joining_inspector.wait(5)
        assert not any(worker.is_alive() for worker in workers)
        assert host._worldfeed_thread is inspector
        assert inspector.is_alive()
        assert not closed
        assert not stop_errors
        release_inspector.set()
        stopper.join(5)
        assert not stopper.is_alive()
        assert stop_errors == [failure]
        assert not inspector_errors
        assert closed == list(host.agents)
        assert not unsafe_closes
        assert_released(host, root)
        for agent in host.agents.values():
            assert any(note.text == "last-worker-write" for note in agent.memory.log.notes())
        assert any(note.text == "last-inspector-write" for note in last.memory.log.notes())
        assert not any(note.kind == "session" for note in first.memory.log.notes())
        host.stop()
    finally:
        release_workers.set()
        server.should_exit = True
        release_inspector.set()
        stopper.join(5)
        inspector.join()
        release_fixture(host)


def test_cleanup_errors_preserve_session_failure_without_skipping_other_agents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "world"
    host = memory_host(tmp_path, memory_root=root, max_agents=2)
    first, second = host.agents.values()
    for agent in host.agents.values():
        agent._threaded = False
        assert agent.connect()
    session_error = OSError("session note not acknowledged")
    close_error = OSError("client close failed after release")
    publish_error = RuntimeError("offline publication failed after update")
    store = first.memory.log._store
    assert isinstance(store, JsonlExperienceStore)

    def fail_session(note: ExperienceNote) -> None:
        raise session_error

    assert first.client is not None
    assert second.client is not None
    client_close = first.client.close
    publish = first._publish

    def failed_close() -> None:
        client_close()
        raise close_error

    def failed_publish() -> None:
        publish()
        raise publish_error

    monkeypatch.setattr(store, "append", fail_session)
    monkeypatch.setattr(first.client, "close", failed_close)
    monkeypatch.setattr(first, "_publish", failed_publish)
    try:
        with pytest.raises(ExceptionGroup, match="shutdown failed after cleanup") as caught:
            host.stop()
        assert leaf_errors(caught.value) == [session_error, close_error, publish_error]
        assert not first.online
        assert not second.online
        assert not first.client.connected
        assert not second.client.connected
        assert not any(note.kind == "session" for note in first.memory.log.notes())
        assert any(note.kind == "session" for note in second.memory.log.notes())
        for agent in host.agents.values():
            probe = JsonlExperienceStore(root, agent.persona.persona_id)
            probe.close()
        host.stop()
    finally:
        for agent in host.agents.values():
            agent.online = False
            agent.memory.close()


@pytest.mark.parametrize("producer", ["worker", "inspector"])
@pytest.mark.parametrize("join_failure", ["raised", "returned_alive"])
def test_interrupted_join_retains_producer_and_journals_until_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, producer: str, join_failure: str
) -> None:
    root = tmp_path / "world"
    host = memory_host(tmp_path, memory_root=root, max_agents=2, tick_seconds=0.001)
    first, second = host.agents.values()
    release = threading.Event()
    if producer == "worker":
        thread = start_blocked_worker(first, release, monkeypatch)
    else:
        _, thread = start_final_inspector(host, release, [])
    join = thread.join
    join_error = RuntimeError("join interrupted")

    def failed_join(timeout: float | None = None) -> None:
        if join_failure == "raised":
            raise join_error

    monkeypatch.setattr(thread, "join", failed_join)
    unsafe_closes = guard_journal_closes(host, [thread], monkeypatch)
    try:
        with pytest.raises(RuntimeError) as caught:
            host.stop()
        if join_failure == "raised":
            assert caught.value is join_error
        else:
            assert "still alive" in str(caught.value)
        assert not unsafe_closes
        assert thread.is_alive()
        if producer == "worker":
            assert first.thread is thread
            assert not second.online
        else:
            assert host._worldfeed_thread is thread
            assert host._worldfeed_server is not None
        with pytest.raises(BlockingIOError):
            JsonlExperienceStore(root, first.persona.persona_id)
        monkeypatch.setattr(thread, "join", join)
        release.set()
        host.stop()
        assert not thread.is_alive()
        assert first.thread is None
        assert host._worldfeed_thread is None
        for agent in host.agents.values():
            probe = JsonlExperienceStore(root, agent.persona.persona_id)
            probe.close()
        host.stop()
    finally:
        monkeypatch.setattr(thread, "join", join)
        first.stop_flag = True
        release.set()
        join(5)
        host.stop()


@pytest.mark.parametrize("failure_stage", ["write", "fsync"])
def test_host_cleanup_with_real_poisoned_store_releases_every_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_stage: str
) -> None:
    root = tmp_path / "world"
    host = memory_host(tmp_path, memory_root=root, max_agents=2)
    first, second = host.agents.values()
    for agent in host.agents.values():
        agent._threaded = False
        assert agent.connect()
    store = first.memory.log._store
    assert isinstance(store, JsonlExperienceStore)
    error = OSError("session write failed before acknowledgement")
    descriptor = store._file.fileno()
    fsync = os.fsync

    def failed_write(text: str) -> int:
        raise error

    def failed_fsync(fd: int) -> None:
        if fd == descriptor:
            raise error
        fsync(fd)

    if failure_stage == "write":
        monkeypatch.setattr(store._file, "write", failed_write)
    else:
        monkeypatch.setattr(os, "fsync", failed_fsync)
    try:
        with pytest.raises(OSError, match="session write failed") as caught:
            host.stop()
        assert caught.value is error
        # Descriptor numbers may be reused by root-directory sync during reopen.
        monkeypatch.setattr(os, "fsync", fsync)
        assert_released(host, root)
        assert not any(note.kind == "session" for note in first.memory.log.notes())
        assert any(note.kind == "session" for note in second.memory.log.notes())
        with pytest.raises(OSError, match="journal failed"):
            store.load()
        probe = JsonlExperienceStore(root, first.persona.persona_id)
        if failure_stage == "write":
            assert not any(note.kind == "session" for note in probe.load())
        # fsync failure can leave an unacknowledged row; never promise it was saved.
        probe.close()
        host.stop()
    finally:
        release_fixture(host)


def test_failed_journal_close_does_not_skip_other_journals_or_mask_note_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "world"
    host = memory_host(tmp_path, memory_root=root, max_agents=3)
    first = next(iter(host.agents.values()))
    for agent in host.agents.values():
        agent._threaded = False
        assert agent.connect()
    note_error = OSError("session failed")
    close_error = OSError("journal close failed after release")
    fail_session_append(first, note_error, monkeypatch)
    attempted: list[str] = []
    closes = {pid: agent.memory.close for pid, agent in host.agents.items()}
    for pid, agent in host.agents.items():

        def fail_first_close(pid: str = pid) -> None:
            closes[pid]()
            attempted.append(pid)
            if len(attempted) == 1:
                raise close_error

        monkeypatch.setattr(agent.memory, "close", fail_first_close)
    try:
        with pytest.raises(ExceptionGroup, match="shutdown failed after cleanup") as caught:
            host.stop()
        assert leaf_errors(caught.value) == [note_error, close_error]
        assert attempted == list(host.agents)
        assert_released(host, root)
        host.stop()
    finally:
        release_fixture(host)


@pytest.mark.parametrize("producer", ["worker", "inspector"])
def test_stop_from_producer_retains_ownership_until_external_join(
    tmp_path: Path, producer: str
) -> None:
    root = tmp_path / "world"
    host = memory_host(tmp_path, memory_root=root, max_agents=1)
    agent = next(iter(host.agents.values()))
    agent._threaded = False
    assert agent.connect()
    failures: list[BaseException] = []
    thread = threading.Thread(target=capture_stop, args=(host, failures))
    if producer == "worker":
        agent.thread = thread
    else:
        host._worldfeed_server = SimpleNamespace(should_exit=False)
        host._worldfeed_thread = thread
    try:
        thread.start()
        thread.join(5)
        assert not thread.is_alive()
        assert len(failures) == 1
        assert isinstance(failures[0], RuntimeError)
        assert "from its worker itself" in str(failures[0])
        with pytest.raises(BlockingIOError):
            JsonlExperienceStore(root, agent.persona.persona_id)
        host.stop()
        assert_released(host, root)
        assert_worldfeed_stopped(host)
        host.stop()
    finally:
        thread.join(5)
        host.stop()
