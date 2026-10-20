"""Offline host/private-journal integration tracer bullets."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest

from robots.__main__ import build_host, parse_args
from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.memory_journal import JsonlExperienceStore
from robots.app.agent_runtime import AgentHost
from robots.app.brain import EventDrivenBrain
from robots.app.world_state import WorldState
from robots.society.memory import VIEW_BUDGET_CHARS
from tests.test_agent_host import (
    STUB_ANSWERS,
    FakeGameClient,
    ScriptedDecisionModel,
    make_roster,
    write_manifest,
)


class CapturingDecision(ScriptedDecisionModel):
    def __init__(self) -> None:
        super().__init__(dict(STUB_ANSWERS))
        self.requests: list[dict[str, Any]] = []

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        return super().decide(request)


def memory_host(tmp_path: Path, **kwargs: Any) -> AgentHost:
    return AgentHost(
        make_roster(),
        write_manifest(tmp_path),
        chat_generator=StaticChatGenerator(),
        client_factory=FakeGameClient,
        run_worldfeed=False,
        **kwargs,
    )


def test_private_memory_is_shared_with_brain_and_live_inspector(tmp_path: Path) -> None:
    host = memory_host(tmp_path, memory_root=tmp_path / "world-a")
    try:
        first, second = list(host.agents.values())[:2]
        assert first.brain is not None
        assert first.brain.memory is first.memory
        assert second.memory is not first.memory
        first.memory.remember("loot", "private-blue-gem")
        assert host.world_state is not None
        assert "private-blue-gem" in "\n".join(
            host.world_state.memory_lines(first.persona.persona_id)
        )
        assert "private-blue-gem" not in "\n".join(
            host.world_state.memory_lines(second.persona.persona_id)
        )
        host.world_state.apply_command(
            {"type": "force_action", "persona_id": first.persona.persona_id, "action": "rest"}
        )
        assert any("operator forced" in note.text for note in first.memory.log.notes())
    finally:
        host.stop()


def test_decision_sees_only_owned_bounded_memory_and_chat_before_reply(tmp_path: Path) -> None:
    host = memory_host(tmp_path, decision_factory=CapturingDecision)
    try:
        first, second = list(host.agents.values())[:2]
        first.memory.remember("other", "foreign-persona-secret")
        second._threaded = False
        second.memory.remember("loot", "owned-blue-gem")
        assert second.connect()
        assert second.client is not None
        second.client.chat = [(9001, "actually-heard-message"), (second.client.gid, "own-echo")]
        second.tick()
        assert second.brain is not None
        assert isinstance(second.brain, EventDrivenBrain)
        model = second.brain._model
        assert isinstance(model, CapturingDecision)
        view = model.requests[-1]["state"]["memory_view"]
        assert "owned-blue-gem" in view
        assert "actually-heard-message" in view
        assert "foreign-persona-secret" not in str(model.requests)
        assert "own-echo" not in " ".join(n.text for n in second.memory.log.notes())
        for index in range(100):
            second.memory.remember("other", f"{index}: " + "x" * 200)
        second.brain.start(second.build_state())
        assert len(model.requests[-1]["state"]["memory_view"]) <= VIEW_BUDGET_CHARS
    finally:
        host.stop()


def test_disconnect_retains_memory_and_stop_releases_for_reconstruction(tmp_path: Path) -> None:
    root = tmp_path / "world-a"
    host = memory_host(tmp_path, memory_root=root)
    agent = next(iter(host.agents.values()))
    agent._threaded = False
    assert agent.connect()
    assert agent.client is not None
    agent.client.chat = [(9001, "persistent-heard-message")]
    agent.tick()
    memory = agent.memory
    agent.disconnect()
    with pytest.raises(BlockingIOError):
        JsonlExperienceStore(root, agent.persona.persona_id)
    assert agent.connect()
    assert agent.memory is memory
    host.stop()
    before = memory.log.notes()
    host.stop()
    assert memory.log.notes() == before
    restored = memory_host(tmp_path, memory_root=root)
    try:
        notes = restored.agents[agent.persona.persona_id].memory.log.notes()
        assert notes == before
        assert any("persistent-heard-message" in n.text for n in notes)
        assert len([n for n in notes if n.kind == "session"]) == 2
        assert restored.world_state is not None
        assert "persistent-heard-message" in "\n".join(
            restored.world_state.memory_lines(agent.persona.persona_id)
        )
    finally:
        restored.stop()


def test_stop_waits_for_worker_write_before_closing_journal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = memory_host(tmp_path, memory_root=tmp_path / "world-a", tick_seconds=0.001)
    agent = next(iter(host.agents.values()))
    entered, release, joining, closed = (threading.Event() for _ in range(4))
    failures: list[BaseException] = []

    def blocked_tick() -> None:
        entered.set()
        assert release.wait(5)
        assert not closed.is_set()
        agent.memory.remember("other", "last-worker-write")

    close = agent.memory.close

    def observed_close() -> None:
        closed.set()
        close()

    monkeypatch.setattr(agent, "tick", blocked_tick)
    monkeypatch.setattr(agent.memory, "close", observed_close)
    assert agent.connect()
    assert entered.wait(5)
    worker = agent.thread
    assert worker is not None
    join = worker.join

    def observed_join(timeout: float | None = None) -> None:
        joining.set()
        assert timeout is None, "storage shutdown must wait, not abandon a live worker"
        join()

    monkeypatch.setattr(worker, "join", observed_join)

    def stop_host() -> None:
        try:
            host.stop()
        except BaseException as exc:
            failures.append(exc)

    stopper = threading.Thread(target=stop_host)
    stopper.start()
    try:
        assert joining.wait(5)
        assert not closed.is_set()
        assert (agent.thread,) == (worker,)
    finally:
        release.set()
        stopper.join(5)
        join(5)
    assert not stopper.is_alive()
    assert not failures
    assert closed.is_set()
    assert not worker.is_alive()
    assert agent.thread is None
    store = JsonlExperienceStore(tmp_path / "world-a", agent.persona.persona_id)
    assert any(n.text == "last-worker-write" for n in store.load())
    store.close()


@pytest.mark.parametrize("failure", ["decision", "bind", "restore"])
def test_constructor_failure_releases_all_acquired_journals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    root = tmp_path / "world-a"
    acquired: list[JsonlExperienceStore] = []
    calls = 0

    def observed_store(directory: Path, persona_id: str) -> JsonlExperienceStore:
        store = JsonlExperienceStore(directory, persona_id)
        acquired.append(store)
        return store

    def decision_factory() -> CapturingDecision:
        nonlocal calls
        calls += 1
        if failure == "decision" and calls == 2:
            msg = "construction failed"
            raise RuntimeError(msg)
        return CapturingDecision()

    bind = WorldState.bind_memory

    def failed_bind(state: WorldState, persona_id: str, log: Any) -> None:
        if failure == "bind" and len(acquired) == 2:
            msg = "construction failed"
            raise RuntimeError(msg)
        bind(state, persona_id, log)

    if failure == "restore":
        root.mkdir(mode=0o700)
        second = sorted(make_roster().personas)[1]
        damaged = root / f"{second}.jsonl"
        damaged.write_text("invalid-json\n")
        damaged.chmod(0o600)  # isolate corrupt-record cleanup from privacy validation
    monkeypatch.setattr("robots.app.agent_runtime.JsonlExperienceStore", observed_store)
    monkeypatch.setattr(WorldState, "bind_memory", failed_bind)
    with pytest.raises((RuntimeError, ValueError)):
        memory_host(tmp_path, memory_root=root, decision_factory=decision_factory)
    assert len(acquired) == 2
    for store in acquired:
        probe = JsonlExperienceStore(root, store.path.stem)
        probe.close()


@pytest.mark.parametrize("failure", ["decision", "handshake", "factory"])
def test_failed_connect_is_offline_and_closes_partial_connection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    host = memory_host(tmp_path, memory_root=tmp_path / "world-a")
    agent = next(iter(host.agents.values()))
    agent._threaded = False

    def fail(*args: Any, **kwargs: Any) -> Any:
        msg = "backend unavailable"
        raise RuntimeError(msg)

    client = FakeGameClient(agent.entry)
    if failure == "factory":
        monkeypatch.setattr(agent, "_client_factory", fail)
    else:
        agent.client = client
        if failure == "handshake":
            client.connected = True  # failure after a partial handshake
            monkeypatch.setattr(client, "connect", fail)
        else:
            assert agent.brain is not None
            assert isinstance(agent.brain, EventDrivenBrain)
            monkeypatch.setattr(agent.brain._model, "decide", fail)
    try:
        assert agent.connect() is False
        assert not client.connected
        assert not agent.online
        assert agent.thread is None
        assert host.world_state is not None
        state = host.world_state.agent_state(agent.persona.persona_id)
        assert state is not None
        assert not state.online
        agent.memory.remember("other", "retry-memory-retained")
    finally:
        host.stop()


def test_cli_memory_opt_in_limits_before_acquiring_journals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        AgentHost, "_autodetect_chat", staticmethod(lambda _: StaticChatGenerator())
    )
    assert parse_args([]).memory_root is None
    root = tmp_path / "world-a"
    args = parse_args(
        ["--manifest", write_manifest(tmp_path), "--memory-root", str(root), "--max-agents", "2"]
    )
    assert args.memory_root == root
    host = build_host(args)
    try:
        assert len(host.agents) == 2
        assert host.memory_root == root
        assert {p.stem for p in root.glob("*.jsonl")} == set(host.agents)
        dropped = sorted(make_roster().personas)[2:]
        for persona_id in dropped:
            probe = JsonlExperienceStore(root, persona_id)
            probe.close()
    finally:
        host.stop()
    restored = build_host(args)
    restored.stop()


def test_world_roots_are_isolated_and_default_host_is_ephemeral(tmp_path: Path) -> None:
    a = memory_host(tmp_path, memory_root=tmp_path / "world-a")
    b = memory_host(tmp_path, memory_root=tmp_path / "world-b")
    ephemeral = memory_host(tmp_path)
    try:
        persona_id = next(iter(a.agents))
        a.agents[persona_id].memory.remember("other", "world-a-private")
        b.agents[persona_id].memory.remember("other", "world-b-private")
        assert "world-a-private" not in "\n".join(b.agents[persona_id].memory.view())
        assert "world-b-private" not in "\n".join(a.agents[persona_id].memory.view())
        assert ephemeral.memory_root is None
        assert not ephemeral.agents[persona_id].memory.log.notes()
    finally:
        a.stop()
        b.stop()
        ephemeral.stop()


def test_world_state_binding_validates_persona_and_log() -> None:
    state = WorldState(make_roster())
    with pytest.raises(ValueError, match="unknown persona_id"):
        state.bind_memory("unknown", object())
    with pytest.raises(TypeError, match="MemoryLog"):
        state.bind_memory(next(iter(state.roster.personas)), object())


def test_llm_escalation_receives_only_bounded_private_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = memory_host(tmp_path)
    prompts: list[str] = []

    def capture_chat(prompt: str) -> str:
        prompts.append(prompt)
        return "offline reply"

    try:
        first, second = list(host.agents.values())[:2]
        first.memory.remember("reputation", "foreign-private-relationship")
        second.memory.remember("reputation", "Trader was helpful yesterday")
        assert second.brain is not None
        assert isinstance(second.brain, EventDrivenBrain)
        monkeypatch.setattr(second.brain._chat, "generate_chat", capture_chat)
        second._threaded = False
        assert second.connect()
        assert second.client is not None
        second.client.chat = [(9001, f"hi {second.entry.char_name}")]
        second.tick()
        assert len(prompts) == 1
        assert "Trader was helpful yesterday" in prompts[0]
        assert "heard [public] Trader" in prompts[0]
        assert "foreign-private-relationship" not in prompts[0]
        for index in range(100):
            second.memory.remember("other", f"{index}: " + "x" * 200)
        second.client.chat.append((9001, f"again {second.entry.char_name}"))
        second.tick()
        assert len(prompts) == 2
        marker, memory_view = prompts[-1].split("My private memory:\n", 1)
        assert "again" in marker
        assert memory_view
        assert len(memory_view) <= VIEW_BUDGET_CHARS
        assert "foreign-private-relationship" not in prompts[-1]
    finally:
        host.stop()


def test_stopped_host_does_not_reconnect_closed_memories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = memory_host(tmp_path, memory_root=tmp_path / "world-a")
    monkeypatch.setattr(host, "_scheduled_on", lambda *_: True)
    host.stop()
    host.step()
    assert all(agent.client is None for agent in host.agents.values())


def test_stop_joins_worldfeed_writer_before_closing_journals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = memory_host(tmp_path, memory_root=tmp_path / "world-a")
    host._run_worldfeed = True
    memory = next(iter(host.agents.values())).memory
    started, exiting, completed = (threading.Event() for _ in range(3))
    failures: list[BaseException] = []

    class FakeFeedServer:
        @property
        def should_exit(self) -> bool:
            return exiting.is_set()

        @should_exit.setter
        def should_exit(self, value: bool) -> None:
            if value:
                exiting.set()

        def run(self) -> None:
            started.set()
            try:
                assert exiting.wait(5)
                memory.remember("other", "last-inspector-write")
            except BaseException as exc:
                failures.append(exc)
            finally:
                completed.set()

    monkeypatch.setattr("robots.app.agent_runtime.uvicorn.Server", lambda _: FakeFeedServer())
    host.start_worldfeed()
    assert started.wait(5)
    host.stop()
    assert completed.wait(5)
    assert not failures
    assert any(n.text == "last-inspector-write" for n in memory.log.notes())
    assert host._worldfeed_server is None
    assert host._worldfeed_thread is None
    host.stop()
