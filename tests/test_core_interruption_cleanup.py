"""Offline regressions for interrupted journal ownership and client cleanup."""

from __future__ import annotations

import json
import os
import traceback
from pathlib import Path

import pytest

from robots.adapters.memory_journal import JsonlExperienceStore
from robots.app.agent_runtime import AgentHost
from robots.society.memory import ExperienceNote, Memory, StubSummarizer
from tests.test_host_memory import memory_host


def test_payload_validation_failure_does_not_poison_a_writer(tmp_path: Path) -> None:
    store = JsonlExperienceStore(tmp_path, "p-0")
    memory = Memory(StubSummarizer(), store=store)
    try:
        with pytest.raises(ValueError, match="invalid journal note values"):
            memory.log.append(ExperienceNote(ts=float("nan"), kind="chat", text="invalid"))
        assert store.path.read_bytes() == b""
        assert memory.log.notes() == ()
        memory.remember("chat", "valid subsequent note", ts=1.0)
        assert store.load() == memory.log.notes()
        assert len(store.load()) == 1
    finally:
        memory.close()


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit, ValueError])
def test_prewrite_serialization_failure_does_not_poison_a_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error_type: type[BaseException]
) -> None:
    store = JsonlExperienceStore(tmp_path, "p-0")
    memory = Memory(StubSummarizer(), store=store)
    origin = error_type("prewrite serialization interrupted")

    def interrupted_serialization(*args, **kwargs):
        raise origin

    try:
        with monkeypatch.context() as patch:
            patch.setattr(json, "dumps", interrupted_serialization)
            with pytest.raises(error_type, match="prewrite serialization interrupted") as caught:
                memory.remember("chat", "not written", ts=1.0)
            assert caught.value is origin
        assert store.path.read_bytes() == b""
        assert memory.log.notes() == ()
        memory.remember("chat", "valid subsequent note", ts=2.0)
        assert store.load() == memory.log.notes()
        assert len(store.load()) == 1
    finally:
        memory.close()


def assert_poisoned_without_ack(
    memory: Memory, store: JsonlExperienceStore, uncertain: bytes
) -> None:
    assert memory.log.notes() == ()
    with pytest.raises(OSError, match="journal failed"):
        store.load()
    with pytest.raises(OSError, match="journal failed"):
        memory.remember("chat", "must not retry blindly", ts=2.0)
    assert memory.log.notes() == ()
    assert store.path.read_bytes() == uncertain


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit, RuntimeError])
@pytest.mark.parametrize("boundary", ["write", "flush", "fsync"])
def test_uncertain_append_interruption_preserves_origin_and_blocks_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error_type: type[BaseException], boundary: str
) -> None:
    store = JsonlExperienceStore(tmp_path, "p-0")
    memory = Memory(StubSummarizer(), store=store)
    origin = error_type("interrupted uncertain append")
    write, flush = store._file.write, store._file.flush

    def interrupted_write(text: str) -> int:
        write(text)
        flush()
        raise origin

    written = False

    def observed_write(text: str) -> int:
        nonlocal written
        amount = write(text)
        written = True
        return amount

    def interrupted_flush() -> None:
        flush()
        if written:
            raise origin

    def interrupted_fsync(descriptor: int) -> None:
        assert descriptor == store._file_fd
        raise origin

    try:
        with monkeypatch.context() as patch:
            if boundary == "write":
                patch.setattr(store._file, "write", interrupted_write)
            elif boundary == "flush":
                patch.setattr(store._file, "write", observed_write)
                patch.setattr(store._file, "flush", interrupted_flush)
            else:
                patch.setattr(os, "fsync", interrupted_fsync)
            with pytest.raises(error_type, match="interrupted uncertain append") as caught:
                memory.remember("chat", "uncertain note", ts=1.0)
            assert caught.value is origin
            assert traceback.extract_tb(origin.__traceback__)[-1].name == f"interrupted_{boundary}"
        uncertain = store.path.read_bytes()
        assert uncertain
        assert_poisoned_without_ack(memory, store, uncertain)
        with pytest.raises(BlockingIOError):
            JsonlExperienceStore(tmp_path, "p-0")
    finally:
        memory.close()
    reopened = JsonlExperienceStore(tmp_path, "p-0")
    try:
        assert len(reopened.load()) == 1  # Explicit inspection, not an acknowledged local note.
    finally:
        reopened.close()


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit, ValueError])
@pytest.mark.parametrize("cleanup_type", [None, OSError, SystemExit])
def test_failed_restore_releases_descriptors_and_lock_without_masking_origin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[BaseException],
    cleanup_type: type[BaseException] | None,
) -> None:
    store = JsonlExperienceStore(tmp_path, "p-0")
    descriptors = [store._file_fd, store._directory_fd]
    origin = error_type("restore interrupted")
    file_close = store._file.close

    def interrupted_load():
        raise origin

    def failed_close() -> None:
        file_close()
        if cleanup_type is not None:
            msg = "secondary cleanup failure"
            raise cleanup_type(msg)

    try:
        with monkeypatch.context() as patch:
            patch.setattr(store, "load", interrupted_load)
            patch.setattr(store._file, "close", failed_close)
            with pytest.raises(
                (KeyboardInterrupt, SystemExit, ValueError, OSError), match=r"restore|secondary"
            ) as caught:
                Memory(StubSummarizer(), store=store)
            assert caught.value is origin
            assert traceback.extract_tb(origin.__traceback__)[-1].name == "interrupted_load"
            assert store._file.closed
            for descriptor in descriptors:
                with pytest.raises(OSError, match="Bad file descriptor"):
                    os.fstat(descriptor)
        reopened = JsonlExperienceStore(tmp_path, "p-0")
        try:
            store.close()  # Idempotence must not close freshly reused descriptor numbers.
            assert reopened.load() == ()
            reopened.append(ExperienceNote(ts=1.0, kind="other", text="new owner"))
        finally:
            reopened.close()
    finally:
        store.close()


def disconnected_events(host: AgentHost, persona_id: str) -> list[str]:
    assert host.world_state is not None
    return [
        event.summary
        for event in host.world_state.events
        if event.summary.startswith(f"{persona_id} disconnected ")
    ]


def guard_session_writes(host: AgentHost, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    session_writes: list[str] = []
    for persona_id, agent in host.agents.items():
        store = agent.memory.log._store
        assert isinstance(store, JsonlExperienceStore)
        append = store.append

        def checked_append(
            note: ExperienceNote,
            store: JsonlExperienceStore = store,
            append=append,
            persona_id: str = persona_id,
        ) -> None:
            assert store._file_fd >= 0, "no retry may write after journal close"
            if note.kind == "session":
                session_writes.append(persona_id)
            append(note)

        monkeypatch.setattr(store, "append", checked_append)
    return session_writes


def assert_single_session_history(host: AgentHost, root: Path) -> None:
    for agent in host.agents.values():
        probe = JsonlExperienceStore(root, agent.persona.persona_id)
        try:
            assert len([note for note in probe.load() if note.kind == "session"]) == 1
        finally:
            probe.close()


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit, OSError])
def test_host_retries_before_release_client_failure_without_postclose_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error_type: type[BaseException]
) -> None:
    root = tmp_path / "world"
    host = memory_host(tmp_path, memory_root=root, max_agents=2)
    first, second = host.agents.values()
    for agent in host.agents.values():
        agent._threaded = False
        assert agent.connect()
    client = first.client
    assert client is not None
    original_close = client.close
    origin = error_type("client failed before release")
    close_attempts: list[bool] = []
    session_writes = guard_session_writes(host, monkeypatch)

    def failed_close() -> None:
        assert first.thread is None
        assert client.connected
        close_attempts.append(False)
        raise origin  # Deliberately do not call the real release first.

    def successful_close() -> None:
        close_attempts.append(True)
        original_close()

    monkeypatch.setattr(client, "close", failed_close)
    try:
        for _ in range(2):
            with pytest.raises(error_type, match="client failed before release") as caught:
                host.stop()
            assert caught.value is origin
            assert traceback.extract_tb(origin.__traceback__)[-1].name == "failed_close"
            assert client.connected
            assert not first.online
            assert second.client is not None
            assert not second.client.connected
            assert not disconnected_events(host, first.persona.persona_id)
            assert len(disconnected_events(host, second.persona.persona_id)) == 1
            assert session_writes == list(host.agents)
            assert_single_session_history(host, root)
        assert close_attempts == [False, False]
        monkeypatch.setattr(client, "close", successful_close)
        host.stop()
        assert not client.connected
        assert close_attempts == [False, False, True]
        assert len(disconnected_events(host, first.persona.persona_id)) == 1
        host.stop()
        host.step()
        assert close_attempts == [False, False, True]
        assert session_writes == list(host.agents)
        assert_single_session_history(host, root)
    finally:
        monkeypatch.setattr(client, "close", original_close)
        for agent in host.agents.values():
            assert agent.client is not None
            agent.client.close()
            agent.memory.close()
