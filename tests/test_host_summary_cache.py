"""Offline host cache wiring: real private files, synthetic personas only."""

from __future__ import annotations

import errno
import json
import os
import random
import shutil
import subprocess
import sys
import threading
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch as mock_patch

import pytest

from robots import __main__ as cli
from robots.__main__ import build_host, parse_args
from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.memory_journal import JsonlExperienceStore
from robots.adapters.memory_summary_cache import JsonlSummaryNodeStore
from robots.app import agent_runtime
from robots.app.brain import EventDrivenBrain
from robots.app.world_state import WorldState
from robots.society.memory import StubSummarizer
from robots.society.society import SocietyRoster
from tests.test_agent_host import FakeGameClient, make_roster, write_manifest
from tests.test_host_memory import CapturingDecision, memory_host


class CountingSummarizer:
    def __init__(self, *, explode: bool = False) -> None:
        self.explode = explode
        self.calls: list[tuple[str, str | None]] = []
        self.stub = StubSummarizer()

    def summarize(self, text_a: str, text_b: str | None) -> str:
        assert not self.explode, "fresh process recomputed an old summary"
        self.calls.append((text_a, text_b))
        return self.stub.summarize(text_a, text_b)


def test_host_restart_reuses_previously_generated_summaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter = CountingSummarizer()
    monkeypatch.setattr(agent_runtime, "StubSummarizer", lambda: counter)
    root = tmp_path / "private-world"
    host = memory_host(
        tmp_path,
        memory_root=root,
        max_agents=2,
        summary_cache_world="world-A",
        summary_cache_policy="stub-120-v1",
    )
    persona_id = next(iter(host.agents))
    try:
        for index in range(4):
            host.agents[persona_id].memory.remember("loot", f"owned-blue-gem-{index}", ts=index)
        expected = host.agents[persona_id].memory.view()
        assert len(counter.calls) == 7
    finally:
        host.stop()
    counter.calls.clear()
    restored = memory_host(
        tmp_path,
        memory_root=root,
        max_agents=2,
        summary_cache_world="world-A",
        summary_cache_policy="stub-120-v1",
    )
    try:
        assert restored.agents[persona_id].memory.view() == expected
        assert counter.calls == [], "restart must reuse old summaries, not recompute raw notes"
        restored.agents[persona_id].memory.remember("loot", "new-owned-note", ts=5)
        restored.agents[persona_id].memory.view()
        assert counter.calls == [("loot: new-owned-note", None)]
    finally:
        restored.stop()


@pytest.mark.parametrize(
    ("world", "policy", "has_root"),
    [
        ("world-A", None, True),
        (None, "stub-v1", True),
        ("world-A", "stub-v1", False),
        ("../bad", "stub-v1", True),
        ("world-A", "bad.policy", True),
    ],
)
def test_api_rejects_config_before_allocations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, world: Any, policy: Any, has_root: bool
) -> None:
    effects: list[str] = []
    roster = make_roster()

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        effects.append("allocation")
        msg = "invalid configuration reached allocation"
        raise AssertionError(msg)

    monkeypatch.setattr(agent_runtime, "load_manifest", forbidden)
    monkeypatch.setattr(random, "Random", forbidden)
    with pytest.raises(ValueError, match="summary cache"):
        agent_runtime.AgentHost(
            roster,
            tmp_path / "missing-manifest",
            memory_root=tmp_path / "root" if has_root else None,
            summary_cache_world=world,
            summary_cache_policy=policy,
        )
    assert effects == []


def test_cli_explicit_pair_propagates_and_preflights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    captured: dict[str, Any] = {}

    def host(*args: Any, **kwargs: Any) -> Any:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(cli, "AgentHost", host)
    args = parse_args(
        [
            "--memory-root",
            str(tmp_path),
            "--summary-cache-world",
            "World_A",
            "--summary-cache-policy",
            "Stub120_v1",
        ]
    )
    build_host(args)
    assert captured["summary_cache_world"] == "World_A"
    assert captured["summary_cache_policy"] == "Stub120_v1"
    args.summary_cache_policy = None

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        msg = "invalid configuration built a roster"
        raise AssertionError(msg)

    monkeypatch.setattr(SocietyRoster, "build", forbidden)
    with pytest.raises(ValueError, match="summary cache"):
        build_host(args)


class UnnotableError(OSError):
    def add_note(self, note: str) -> None:
        msg = "diagnostic interrupted"
        raise SystemExit(msg)


def construction_observers(
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    origin: BaseException,
    *,
    raw_stores: list[Any],
    caches: list[Any],
    closes: dict[int, int],
) -> Callable[[], Any]:
    bind = WorldState.bind_memory
    scheduled = agent_runtime.ScheduledAgent

    def origin_raise(*args: Any, **kwargs: Any) -> Any:
        raise origin

    def observe_close(store: Any) -> None:
        close = store.close
        closes[id(store)] = 0

        def release_then_fail() -> None:
            closes[id(store)] += 1
            close()
            msg = "secondary path/credential must not enter diagnostic"
            raise OSError(msg)

        monkeypatch.setattr(store, "close", release_then_fail)

    def raw_factory(directory: Path, persona_id: str) -> Any:
        store = JsonlExperienceStore(directory, persona_id)
        raw_stores.append(store)
        observe_close(store)
        if phase == "raw_restore" and len(raw_stores) == 3:
            monkeypatch.setattr(store, "load", origin_raise)
        return store

    def cache_factory(*args: Any) -> Any:
        if phase == "cache" and len(raw_stores) == 3:
            origin_raise()
        cache = JsonlSummaryNodeStore(*args)
        caches.append(cache)
        observe_close(cache)
        if phase == "cache_restore" and len(raw_stores) == 3:
            monkeypatch.setattr(cache, "load", origin_raise)
        return cache

    def failing_bind(state: WorldState, persona_id: str, log: Any) -> None:
        if phase == "bind" and len(raw_stores) == 3:
            origin_raise()
        bind(state, persona_id, log)

    def decision() -> Any:
        if phase == "decision" and len(raw_stores) == 3:
            origin_raise()
        return ScriptedDecisionModel(dict(agent_runtime.DEFAULT_STUB_ANSWERS))

    def failing_scheduled(*args: Any, **kwargs: Any) -> Any:
        if phase == "scheduled" and len(raw_stores) == 3:
            origin_raise()
        return scheduled(*args, **kwargs)

    monkeypatch.setattr(agent_runtime, "JsonlExperienceStore", raw_factory)
    monkeypatch.setattr(agent_runtime, "JsonlSummaryNodeStore", cache_factory)
    monkeypatch.setattr(WorldState, "bind_memory", failing_bind)
    monkeypatch.setattr(agent_runtime, "ScheduledAgent", failing_scheduled)
    return decision


@pytest.mark.parametrize(
    "phase", ["cache", "raw_restore", "cache_restore", "bind", "decision", "scheduled"]
)
@pytest.mark.parametrize("error_type", [OSError, UnnotableError, KeyboardInterrupt])
def test_failed_construction_preserves_origin_and_attempts_all_owned_stores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str, error_type: type[BaseException]
) -> None:

    origin = error_type(errno.EIO, "synthetic construction failure")
    raw_stores: list[Any] = []
    caches: list[Any] = []
    closes: dict[int, int] = {}
    root = tmp_path / "root"
    decision = construction_observers(
        monkeypatch, phase, origin, raw_stores=raw_stores, caches=caches, closes=closes
    )
    try:
        with pytest.raises(error_type) as caught:
            memory_host(
                tmp_path,
                memory_root=root,
                max_agents=4,
                decision_factory=decision,
                summary_cache_world="world-A",
                summary_cache_policy="stub-v1",
            )
        assert caught.value is origin
        assert traceback.extract_tb(origin.__traceback__)[-1].name == "origin_raise"
        if isinstance(origin, OSError):
            assert origin.errno == errno.EIO
        assert len(raw_stores) == 3
        assert len(caches) == (2 if phase == "cache" else 3)
        assert set(closes.values()) == {1}
        assert "secondary path/credential" not in str(getattr(origin, "__notes__", []))
        for raw in raw_stores:
            reopened = JsonlExperienceStore(root, raw.path.stem)
            reopened.close()
        for cache in caches:
            reopened_cache = JsonlSummaryNodeStore(root, "world-A", cache._persona, "stub-v1")
            reopened_cache.close()
    finally:
        # Harness recovery only: no universal pre-release interruption guarantee.
        for raw in raw_stores:
            JsonlExperienceStore.close(raw)
        for cache in caches:
            JsonlSummaryNodeStore.close(cache)


class StringSubclass(str):
    pass


@pytest.mark.parametrize(
    "identifier",
    [
        True,
        1,
        1.0,
        b"world",
        StringSubclass("world"),
        "",
        "a" * 129,
        "a/b",
        "a.b",
        "-world",
        "a\n",
        "café",
        "a b",
        "a\x00",
    ],
)
@pytest.mark.parametrize("field", ["summary_cache_world", "summary_cache_policy"])
def test_api_and_cli_builder_strict_ids_fail_before_any_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, identifier: Any, field: str
) -> None:

    roster = make_roster()
    args = parse_args(
        [
            "--memory-root",
            str(tmp_path),
            "--summary-cache-world",
            "World_A",
            "--summary-cache-policy",
            "Stub_v1",
        ]
    )
    settings: dict[str, Any] = {"summary_cache_world": "World_A", "summary_cache_policy": "Stub_v1"}
    settings[field] = identifier
    setattr(args, field, identifier)
    effects: list[str] = []

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        effects.append("allocation")
        msg = "preflight failed to refuse unsafe configuration"
        raise AssertionError(msg)

    monkeypatch.setattr(SocietyRoster, "build", forbidden)
    monkeypatch.setattr(random, "Random", forbidden)
    monkeypatch.setattr(agent_runtime, "load_manifest", forbidden)
    monkeypatch.setattr(agent_runtime.AgentHost, "_autodetect_chat", forbidden)
    monkeypatch.setattr(agent_runtime, "JsonlExperienceStore", forbidden)
    monkeypatch.setattr(agent_runtime, "JsonlSummaryNodeStore", forbidden)
    with pytest.raises(ValueError, match="summary cache"):
        agent_runtime.AgentHost(roster, "absent", memory_root=tmp_path, **settings)
    with pytest.raises(ValueError, match="summary cache"):
        build_host(args)
    assert effects == []


@pytest.mark.parametrize(
    "flags",
    [
        ["--summary-cache-world", "world"],
        ["--summary-cache-policy", "stub"],
        ["--summary-cache-world", "world", "--summary-cache-policy", "stub"],
        [
            "--memory-root",
            "unused",
            "--summary-cache-world",
            "../unsafe",
            "--summary-cache-policy",
            "stub",
        ],
    ],
)
def test_cli_parse_refuses_invalid_pair(flags: list[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        parse_args(flags)
    assert caught.value.code == 2


def cache_host(tmp_path: Path, **kwargs: Any) -> agent_runtime.AgentHost:
    return memory_host(
        tmp_path,
        memory_root=tmp_path / "root",
        summary_cache_world="World_A",
        summary_cache_policy="Stub120_v1",
        max_agents=2,
        **kwargs,
    )


def test_default_is_raw_only_and_recomputes_on_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter = CountingSummarizer()
    monkeypatch.setattr(agent_runtime, "StubSummarizer", lambda: counter)
    root = tmp_path / "raw-only"
    host = memory_host(tmp_path, memory_root=root, max_agents=1)
    try:
        agent = next(iter(host.agents.values()))
        agent.memory.remember("loot", "raw-only-gem")
        agent.memory.view()
    finally:
        host.stop()
    counter.calls.clear()
    restored = memory_host(tmp_path, memory_root=root, max_agents=1)
    try:
        assert "raw-only-gem" in str(next(iter(restored.agents.values())).memory.view())
        assert counter.calls == [("loot: raw-only-gem", None)]
        assert not (root / "summary-cache").exists()
        assert parse_args([]).summary_cache_world is None
        assert parse_args([]).summary_cache_policy is None
    finally:
        restored.stop()


def test_cache_facade_shared_with_brain_and_inspector_is_source_private(tmp_path: Path) -> None:

    host = cache_host(tmp_path, decision_factory=CapturingDecision)
    try:
        first, second = list(host.agents.values())
        assert first.brain is not None
        assert second.brain is not None
        assert first.brain.memory is first.memory
        assert second.brain.memory is second.memory
        first.memory.remember("reputation", "foreign-persona-secret")
        second.memory.remember("reputation", "owned-blue-gem")
        second._threaded = False
        assert second.connect()
        assert second.client is not None
        second.client.chat = [(9001, "actually-heard-fixture")]
        second.tick()
        assert isinstance(second.brain, EventDrivenBrain)
        model = second.brain._model
        assert isinstance(model, CapturingDecision)
        view = model.requests[-1]["state"]["memory_view"]
        assert "owned-blue-gem" in view
        assert "actually-heard-fixture" in view
        assert "foreign-persona-secret" not in str(model.requests)
        assert host.world_state is not None
        lines = host.world_state.memory_lines(second.persona.persona_id)
        assert "owned-blue-gem" in str(lines)
        assert "actually-heard-fixture" in str(lines)
        assert "foreign-persona-secret" not in str(lines)
        host.world_state.apply_command(
            {"type": "force_action", "persona_id": second.persona.persona_id, "action": "rest"}
        )
        assert any("operator forced" in note.text for note in second.memory.log.notes())
        cache = second.memory.log._summary_store
        assert isinstance(cache, JsonlSummaryNodeStore)
        assert (
            cache.path
            == tmp_path
            / "root"
            / "summary-cache"
            / "World_A"
            / second.persona.persona_id
            / "Stub120_v1"
            / "nodes.jsonl"
        )
        assert os.stat(cache.path).st_mode & 0o777 == 0o600
        assert os.stat(cache.path.parent).st_mode & 0o777 == 0o700
        for line in cache.path.read_text().splitlines():
            body = json.loads(json.loads(line)["note"]["text"])
            assert (body["world"], body["persona"], body["policy"]) == (
                "World_A",
                second.persona.persona_id,
                "Stub120_v1",
            )
        assert all(note.ts != 0 or note.text != "nodes" for note in second.memory.log.notes())
    finally:
        host.stop()


def process_probe(root: Path, mode: str) -> dict[str, Any]:
    """Child-only offline probe; never invokes a host run loop or real backend."""

    persona_id = sorted(make_roster().personas)[0]
    if mode == "locked":
        result: dict[str, Any] = {}
        for label, constructor in (
            ("raw", lambda: JsonlExperienceStore(root / "root", persona_id)),
            (
                "cache",
                lambda: JsonlSummaryNodeStore(root / "root", "World_A", persona_id, "Stub120_v1"),
            ),
        ):
            try:
                store = constructor()
            except BlockingIOError:
                result[label] = "locked"
            else:
                store.close()
                result[label] = "unexpectedly-open"
        return result

    counter = CountingSummarizer(explode=True)
    with mock_patch.object(agent_runtime, "StubSummarizer", return_value=counter):
        host = cache_host(root)
    try:
        agent = host.agents[persona_id]
        return {"view": agent.memory.view(), "calls": counter.calls}
    finally:
        host.stop()


def child_probe(root: Path, mode: str) -> dict[str, Any]:
    code = (
        "import json,sys; from pathlib import Path; "
        "from tests.test_host_summary_cache import process_probe; "
        "print(json.dumps(process_probe(Path(sys.argv[1]),sys.argv[2])) )"
    )
    child = subprocess.run(
        [sys.executable, "-c", code, str(root), mode],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    result: dict[str, Any] = json.loads(child.stdout)
    return result


def test_fresh_process_locks_retained_across_reconnect_and_released_at_stop(tmp_path: Path) -> None:
    host = cache_host(tmp_path)
    agent = next(iter(host.agents.values()))
    agent._threaded = False
    try:
        assert agent.connect()
        agent.memory.remember("loot", "persistent-owned-gem")
        memory = agent.memory
        agent.disconnect()
        assert child_probe(tmp_path, "locked") == {"raw": "locked", "cache": "locked"}
        assert agent.connect()
        assert agent.memory is memory
        agent.disconnect()
        expected = memory.view()
    finally:
        host.stop()
    assert child_probe(tmp_path, "restored") == {"view": expected, "calls": []}


@pytest.mark.parametrize("identity", ["world", "persona", "policy", "copied-policy"])
def test_wrong_cache_identity_refused_without_fallback(tmp_path: Path, identity: str) -> None:

    host = cache_host(tmp_path)
    agent = next(iter(host.agents.values()))
    persona_id = agent.persona.persona_id
    try:
        agent.memory.remember("loot", "owned-gem")
        agent.memory.view()
        cache = agent.memory.log._summary_store
        assert isinstance(cache, JsonlSummaryNodeStore)
        path = cache.path
    finally:
        host.stop()
    if identity == "copied-policy":
        target = JsonlSummaryNodeStore(tmp_path / "root", "World_A", persona_id, "Policy_B")
        target.close()
        shutil.copyfile(path, target.path)
        settings = {"summary_cache_policy": "Policy_B"}
    else:
        row = json.loads(path.read_text())
        body = json.loads(row["note"]["text"])
        body[identity] = "Foreign_ID"
        row["note"]["text"] = json.dumps(
            body, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
        )
        path.write_text(json.dumps(row) + "\n")
        settings = {"summary_cache_policy": "Stub120_v1"}
    with pytest.raises(ValueError, match="world/persona/policy mismatch"):
        memory_host(
            tmp_path,
            memory_root=tmp_path / "root",
            summary_cache_world="World_A",
            max_agents=2,
            **settings,
        )
    reopened = JsonlExperienceStore(tmp_path / "root", persona_id)
    reopened.close()
    reopened_cache = JsonlSummaryNodeStore(
        tmp_path / "root", "World_A", persona_id, settings["summary_cache_policy"]
    )
    reopened_cache.close()


def test_explicit_world_roots_isolate_raw_notes_and_cache_namespaces(tmp_path: Path) -> None:
    a_dir, b_dir = tmp_path / "a", tmp_path / "b"
    a_dir.mkdir()
    b_dir.mkdir()
    a = cache_host(a_dir)
    b = memory_host(
        b_dir,
        memory_root=b_dir / "root",
        summary_cache_world="World_B",
        summary_cache_policy="Stub120_v1",
        max_agents=2,
    )
    try:
        first = next(iter(a.agents.values()))
        second = b.agents[first.persona.persona_id]
        first.memory.remember("loot", "world-A-secret")
        second.memory.remember("loot", "world-B-secret")
        assert "world-A-secret" not in str(second.memory.view())
        assert "world-B-secret" not in str(first.memory.view())
        first_cache = first.memory.log._summary_store
        second_cache = second.memory.log._summary_store
        assert isinstance(first_cache, JsonlSummaryNodeStore)
        assert isinstance(second_cache, JsonlSummaryNodeStore)
        assert first_cache.path != second_cache.path
    finally:
        a.stop()
        b.stop()


def stop_fixture_host(host: agent_runtime.AgentHost, failures: list[BaseException]) -> None:
    try:
        host.stop()
    except BaseException as exc:
        failures.append(exc)


def observe_shutdown_stores(
    agent: agent_runtime.ScheduledAgent,
    monkeypatch: pytest.MonkeyPatch,
    worker_release: threading.Event,
    inspector_release: threading.Event,
    close_events: list[str],
) -> None:
    for label, store in (
        ("raw", agent.memory.log._store),
        ("cache", agent.memory.log._summary_store),
    ):
        assert store is not None
        close = store.close

        def observed_close(label: str = label, close: Any = close) -> None:
            assert worker_release.is_set()
            assert inspector_release.is_set()
            close_events.append(label)
            close()

        monkeypatch.setattr(store, "close", observed_close)


def observe_thread_join(
    monkeypatch: pytest.MonkeyPatch,
    thread: threading.Thread,
    joining: threading.Event,
) -> None:
    join = thread.join

    def observed_join() -> None:
        joining.set()
        join()

    monkeypatch.setattr(thread, "join", observed_join)


def test_stop_joins_worker_and_inspector_before_either_store_closes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = cache_host(tmp_path)
    agent = next(iter(host.agents.values()))
    worker_entered, worker_release, inspector_entered, inspector_release = (
        threading.Event() for _ in range(4)
    )
    close_events: list[str] = []
    failures: list[BaseException] = []
    worker_joining = threading.Event()
    inspector_joining = threading.Event()

    def worker_write() -> None:
        worker_entered.set()
        assert worker_release.wait(5)
        agent.memory.remember("loot", "last-worker-note")

    def inspector_write() -> None:
        inspector_entered.set()
        assert inspector_release.wait(5)
        assert host.world_state is not None
        host.world_state.memory_lines(agent.persona.persona_id)

    observe_shutdown_stores(agent, monkeypatch, worker_release, inspector_release, close_events)
    worker = threading.Thread(target=worker_write)
    inspector = threading.Thread(target=inspector_write)
    agent.thread, host._worldfeed_thread = worker, inspector
    agent.online = True
    agent.client = FakeGameClient(agent.entry)
    host._worldfeed_server = type("FixtureServer", (), {"should_exit": False})()
    worker.start()
    inspector.start()
    assert worker_entered.wait(5)
    assert inspector_entered.wait(5)
    worker_join, inspector_join = worker.join, inspector.join

    observe_thread_join(monkeypatch, worker, worker_joining)
    observe_thread_join(monkeypatch, inspector, inspector_joining)
    stopper = threading.Thread(target=stop_fixture_host, args=(host, failures))
    stopper.start()
    try:
        assert worker_joining.wait(5)
        assert not close_events
        worker_release.set()
        assert inspector_joining.wait(5)
        assert not close_events
    finally:
        worker_release.set()
        inspector_release.set()
        stopper.join(5)
        worker_join(5)
        inspector_join(5)
    assert not stopper.is_alive()
    assert not failures
    assert close_events == ["raw", "cache"]
    assert_stopped_host_reopens(host, tmp_path)


def assert_stopped_host_reopens(host: agent_runtime.AgentHost, tmp_path: Path) -> None:
    assert host._worldfeed_thread is None
    assert all(agent.thread is None for agent in host.agents.values())
    restored = cache_host(tmp_path)
    restored.stop()


@pytest.mark.parametrize("resource", ["raw", "cache"])
def test_pre_release_cleanup_failure_is_truthfully_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, resource: str
) -> None:

    origin = OSError(errno.EIO, "synthetic bind failure")
    acquired: list[Any] = []
    close_calls: dict[str, int] = {"raw": 0, "cache": 0}
    root = tmp_path / "root"

    def observe(store: Any, label: str) -> Any:
        close = store.close
        acquired.append(store)

        def attempted_close() -> None:
            close_calls[label] += 1
            if label == resource:
                msg = "pre-release interruption"
                raise SystemExit(msg)
            close()

        monkeypatch.setattr(store, "close", attempted_close)
        return store

    def failed_bind(*args: Any) -> None:
        raise origin

    monkeypatch.setattr(
        agent_runtime,
        "JsonlExperienceStore",
        lambda *args: observe(JsonlExperienceStore(*args), "raw"),
    )
    monkeypatch.setattr(
        agent_runtime,
        "JsonlSummaryNodeStore",
        lambda *args: observe(JsonlSummaryNodeStore(*args), "cache"),
    )
    monkeypatch.setattr(WorldState, "bind_memory", failed_bind)
    try:
        with pytest.raises(OSError, match="synthetic bind failure") as caught:
            cache_host(tmp_path)
        assert caught.value is origin
        assert close_calls == {"raw": 1, "cache": 1}
        assert "storage release may be incomplete" in str(origin.__notes__)
        constructors: dict[str, Callable[[], Any]] = {
            "raw": lambda: JsonlExperienceStore(root, sorted(make_roster().personas)[0]),
            "cache": lambda: JsonlSummaryNodeStore(
                root, "World_A", sorted(make_roster().personas)[0], "Stub120_v1"
            ),
        }
        with pytest.raises(BlockingIOError):
            constructors[resource]()
        other = constructors["cache" if resource == "raw" else "raw"]()
        other.close()
    finally:
        # Observe retained locks above BEFORE explicit fixture recovery.
        JsonlExperienceStore.close(acquired[0])
        JsonlSummaryNodeStore.close(acquired[1])


def test_failed_session_write_still_closes_every_dual_resource(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    host = cache_host(tmp_path)
    first, second = list(host.agents.values())
    first._threaded = second._threaded = False
    assert first.connect()
    assert second.connect()
    store = first.memory.log._store
    assert store is not None
    origin = OSError(errno.EIO, "synthetic session write failure")

    def failed_append(*args: Any) -> None:
        raise origin

    monkeypatch.setattr(store, "append", failed_append)
    with pytest.raises(OSError, match="synthetic session write failure") as caught:
        host.stop()
    assert caught.value is origin
    for agent in host.agents.values():
        assert agent.client is not None
        assert not agent.online
        assert not agent.client.connected
        raw = JsonlExperienceStore(tmp_path / "root", agent.persona.persona_id)
        raw.close()
        cache = JsonlSummaryNodeStore(
            tmp_path / "root", "World_A", agent.persona.persona_id, "Stub120_v1"
        )
        cache.close()


def test_source_binding_mismatch_refuses_host_restore(tmp_path: Path) -> None:
    host = cache_host(tmp_path)
    agent = next(iter(host.agents.values()))
    try:
        agent.memory.remember("loot", "original-owned-note")
        agent.memory.view()
        store = agent.memory.log._store
        assert isinstance(store, JsonlExperienceStore)
        path = store.path
    finally:
        host.stop()
    row = json.loads(path.read_text())
    row["note"]["text"] = "changed-owned-note"
    path.write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="source binding mismatch"):
        cache_host(tmp_path)


def test_cli_builds_actual_cached_host_without_backend_autodetection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:

    monkeypatch.setattr(
        agent_runtime.AgentHost, "_autodetect_chat", staticmethod(lambda _: StaticChatGenerator())
    )
    args = parse_args(
        [
            "--manifest",
            write_manifest(tmp_path),
            "--memory-root",
            str(tmp_path / "root"),
            "--summary-cache-world",
            "ExactWorld_A",
            "--summary-cache-policy",
            "ExactPolicy_v1",
            "--max-agents",
            "2",
        ]
    )
    host = build_host(args)
    try:
        assert len(host.agents) == 2
        assert host.summary_cache_world == "ExactWorld_A"
        assert host.summary_cache_policy == "ExactPolicy_v1"
        assert len(list((tmp_path / "root" / "summary-cache").rglob("nodes.jsonl"))) == 2
    finally:
        host.stop()


def test_literal_max_length_identifiers_remain_exact(tmp_path: Path) -> None:
    world, policy = "W" * 128, "P" * 128
    host = memory_host(
        tmp_path,
        memory_root=tmp_path / "root",
        summary_cache_world=world,
        summary_cache_policy=policy,
        max_agents=1,
    )
    try:
        agent = next(iter(host.agents.values()))
        cache = agent.memory.log._summary_store
        assert isinstance(cache, JsonlSummaryNodeStore)
        assert cache.path.parent.name == policy
        assert cache.path.parent.parent.parent.name == world
    finally:
        host.stop()
