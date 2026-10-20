"""In-process HTTP -> host queue -> owning tick -> fake say; no game/provider I/O."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from robots.adapters.chat.stub import StaticChatGenerator
from robots.app.agent_runtime import AgentHost
from tests.test_agent_host import (
    STUB_ANSWERS,
    FakeClock,
    FakeGameClient,
    FakeSocietyClock,
    ScriptedDecisionModel,
    make_roster,
    write_manifest,
)


@pytest.fixture
def host_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    apps: list[Any] = []

    class InProcessServer:
        def __init__(self, config: Any) -> None:
            apps.append(config.app)
            self.should_exit = False

        def run(self) -> None:
            pass

    monkeypatch.setattr("robots.app.agent_runtime.uvicorn.Server", InProcessServer)
    host = AgentHost(
        make_roster(),
        write_manifest(tmp_path),
        chat_generator=StaticChatGenerator(),
        decision_factory=lambda: ScriptedDecisionModel(dict(STUB_ANSWERS)),
        client_factory=FakeGameClient,
        clock=FakeSocietyClock(),
    )
    agent = next(iter(host.agents.values()))
    agent._threaded = False
    agent._tick_clock = FakeClock()
    assert agent.connect()
    agent.brain = None  # The operator limb must not require inference or swallow its errors.
    assert agent.client is not None
    agent.client.said.clear()
    host.start_worldfeed()
    with TestClient(apps[0]) as api:
        yield host, agent, api
    host.stop()


def command(agent: Any, command_id: str = "operator-1", text: Any = "hello from operator"):
    return {
        "type": "force_action",
        "persona_id": agent.persona.persona_id,
        "action": "chat",
        "args": text,
        "command_id": command_id,
    }


def test_http_queues_then_tick_dispatches_without_server_confirmation(host_api) -> None:
    host, agent, api = host_api
    result = api.post("/commands", json=command(agent))
    assert result.status_code == 200
    assert result.json().get("status") == "queued"
    assert result.json()["delivery_confirmation"] is False
    assert agent.client.said == []
    agent.tick()
    status = api.get("/commands/operator-1")
    assert status.status_code == 200
    assert status.json()["status"] == "dispatched"
    assert status.json()["delivery_confirmation"] is False
    assert agent.client.said == ["hello from operator"]
    agent.tick()
    assert agent.client.said == ["hello from operator"]
    assert any("operator-1" in note.text for note in agent.memory.log.notes())
    assert host.world_state is not None


@pytest.mark.parametrize(
    "text",
    [
        None,
        42,
        True,
        {},
        [],
        "",
        "   ",
        "a\nhi",
        "a\rhi",
        "a\x00hi",
        "a\thi",
        "a\x7fhi",
        "😀" * 20000,
    ],
)
def test_invalid_chat_rejected_before_memory_or_queue(host_api, text) -> None:
    _host, agent, api = host_api
    before = agent.memory.log.notes()
    result = api.post("/commands", json=command(agent, text=text))
    assert result.status_code == 400
    agent.tick()
    assert agent.client.said == []
    assert agent.memory.log.notes() == before


@pytest.mark.parametrize("command_id", [None, 3, "", "../escape", "a b", "x" * 129])
def test_required_safe_id_rejected(host_api, command_id) -> None:
    _host, agent, api = host_api
    assert api.post("/commands", json=command(agent, command_id=command_id)).status_code == 400


def test_host_unsupported_force_actions_fail_closed(host_api) -> None:
    _host, agent, api = host_api
    request = command(agent)
    request["action"] = "rest"
    before = agent.memory.log.notes()
    assert api.post("/commands", json=request).status_code == 400
    assert agent.memory.log.notes() == before


def test_unknown_and_unowned_persona_rejected(host_api) -> None:
    host, agent, api = host_api
    request = command(agent)
    request["persona_id"] = "unknown"
    assert api.post("/commands", json=request).status_code == 404
    del host.agents[agent.persona.persona_id]
    try:
        assert api.post("/commands", json=command(agent)).status_code == 404
    finally:
        host.agents[agent.persona.persona_id] = agent


def test_duplicates_replay_status_and_conflicts_do_not_send(host_api) -> None:
    _host, agent, api = host_api
    first = api.post("/commands", json=command(agent)).json()
    assert api.post("/commands", json=command(agent)).json() == first
    assert api.post("/commands", json=command(agent, text="different")).status_code == 400
    agent.tick()
    assert api.post("/commands", json=command(agent)).json()["status"] == "dispatched"
    agent.tick()
    assert agent.client.said == ["hello from operator"]


def test_queue_and_terminal_retention_are_bounded(host_api) -> None:
    _host, agent, api = host_api
    for index in range(64):
        assert api.post("/commands", json=command(agent, f"q-{index}")).status_code == 200
    assert api.post("/commands", json=command(agent, "overflow")).status_code == 429
    assert api.post("/commands", json=command(agent, "q-0")).json()["status"] == "queued"
    agent.tick()
    assert len(agent.client.said) == 64
    for index in range(257):
        assert api.post("/commands", json=command(agent, f"terminal-{index}")).status_code == 200
        agent.tick()
    assert api.get("/commands/q-0").status_code == 404
    assert api.get("/commands/terminal-0").status_code == 404
    retained = api.get("/commands/terminal-256").json()
    assert retained["idempotency_scope"] == "retained_process_lifetime"
    assert retained["terminal_retention"] == 256
    assert api.post("/commands", json=command(agent, "q-0")).json()["status"] == "queued"


def test_concurrent_duplicate_http_submissions_enqueue_once(host_api) -> None:

    _host, agent, api = host_api
    barrier = threading.Barrier(8)

    def submit() -> int:
        barrier.wait(timeout=5)
        return int(api.post("/commands", json=command(agent)).status_code)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: submit(), range(8)))
    assert results == [200] * 8
    agent.tick()
    assert agent.client.said == ["hello from operator"]


def test_offline_rejected_at_admission_and_rechecked_before_send(host_api) -> None:
    _host, agent, api = host_api
    agent.online = False
    assert api.post("/commands", json=command(agent)).status_code == 409
    agent.online = True
    assert api.post("/commands", json=command(agent)).status_code == 200
    agent.online = False
    agent.tick()
    assert api.get("/commands/operator-1").json()["status"] == "cancelled"
    agent.online = True
    agent.tick()
    assert agent.client.said == []


def test_stop_cancels_pending_and_refuses_new_requests(host_api) -> None:
    host, agent, api = host_api
    assert api.post("/commands", json=command(agent)).status_code == 200
    host.stop()
    assert api.get("/commands/operator-1").json()["status"] == "cancelled"
    assert api.post("/commands", json=command(agent, "late")).status_code == 503
    agent.tick()
    assert agent.client.said == []


def test_disconnect_cancels_pending_even_if_next_login_precedes_tick(host_api) -> None:
    _host, agent, api = host_api
    api.post("/commands", json=command(agent))
    agent.disconnect()
    assert agent.connect()
    agent.tick()
    assert api.get("/commands/operator-1").json()["status"] == "cancelled"
    assert agent.client.said == []


def test_send_exception_is_uncertain_sanitized_and_not_retried(host_api, monkeypatch) -> None:
    _host, agent, api = host_api

    def fail(text: str) -> None:
        agent.client.said.append(text)  # effect may precede exception
        msg = "secret transport detail"
        raise OSError(msg)

    monkeypatch.setattr(agent.client, "say", fail)
    api.post("/commands", json=command(agent))
    agent.tick()
    result = api.get("/commands/operator-1").json()
    assert result["status"] == "uncertain"
    assert result["error_class"] == "OSError"
    assert "secret" not in str(result)
    assert api.post("/commands", json=command(agent)).json()["status"] == "uncertain"
    agent.tick()
    assert agent.client.said == ["hello from operator"]


@pytest.mark.parametrize("failure_at", [1, 2])
def test_memory_failure_before_or_after_send_is_not_a_retry(
    host_api, monkeypatch, failure_at
) -> None:
    _host, agent, api = host_api
    remember = agent.memory.remember
    calls = 0

    def fail(kind, text, **kwargs) -> None:
        nonlocal calls
        calls += 1
        if calls == failure_at:
            msg = "secret journal detail"
            raise OSError(msg)
        remember(kind, text, **kwargs)

    api.post("/commands", json=command(agent))
    with monkeypatch.context() as patch:
        patch.setattr(agent.memory, "remember", fail)
        agent.tick()
    result = api.get("/commands/operator-1").json()
    assert result["status"] == ("failed" if failure_at == 1 else "dispatched")
    assert result["audit_error_class"] == "OSError"
    assert "secret" not in str(result)
    assert result["delivery_confirmation"] is False
    agent.tick()
    assert agent.client.said == ([] if failure_at == 1 else ["hello from operator"])


def test_all_offline_pending_requests_cancel_before_future_login(host_api) -> None:
    _host, agent, api = host_api
    for index in range(3):
        api.post("/commands", json=command(agent, f"offline-{index}"))
    agent.online = False
    agent.tick()
    agent.online = True
    agent.tick()
    assert agent.client.said == []
    assert all(
        api.get(f"/commands/offline-{index}").json()["status"] == "cancelled" for index in range(3)
    )


def test_stop_waits_for_worker_and_prevents_send_after_blocked_audit(host_api, monkeypatch) -> None:

    host, agent, api = host_api
    entered, release, joining = (threading.Event() for _ in range(3))
    remember = agent.memory.remember

    def blocked(kind, text, **kwargs) -> None:
        if "chat intent:" in text:
            entered.set()
            assert release.wait(5)
        remember(kind, text, **kwargs)

    monkeypatch.setattr(agent.memory, "remember", blocked)
    api.post("/commands", json=command(agent))
    worker = threading.Thread(target=agent.tick)
    agent.thread = worker
    original_join = worker.join

    def join(timeout=None) -> None:
        joining.set()
        original_join(timeout)

    monkeypatch.setattr(worker, "join", join)
    worker.start()
    try:
        assert entered.wait(5)
        stopper = threading.Thread(target=host.stop)
        stopper.start()
        assert joining.wait(5)
        assert api.post("/commands", json=command(agent, "late")).status_code == 503
    finally:
        release.set()
        worker.join(5)
    stopper.join(5)
    assert not stopper.is_alive()
    assert agent.thread is None
    assert api.get("/commands/operator-1").json()["status"] == "cancelled"
    assert agent.client.said == []


def test_inflight_send_is_not_dispatched_until_return(host_api, monkeypatch) -> None:

    _host, agent, api = host_api
    entered, release = threading.Event(), threading.Event()

    def blocked(text: str) -> None:
        entered.set()
        assert release.wait(5)
        agent.client.said.append(text)

    monkeypatch.setattr(agent.client, "say", blocked)
    api.post("/commands", json=command(agent))
    worker = threading.Thread(target=agent.tick)
    worker.start()
    try:
        assert entered.wait(5)
        result = api.get("/commands/operator-1").json()
        assert result["status"] == "uncertain"
        assert api.post("/commands", json=command(agent)).json()["status"] == "uncertain"
    finally:
        release.set()
        worker.join(5)
    assert api.get("/commands/operator-1").json()["status"] == "dispatched"
    assert not worker.is_alive()


def test_lost_client_connection_rejected_and_cancelled(host_api) -> None:
    _host, agent, api = host_api
    agent.client.connected = False
    assert api.post("/commands", json=command(agent)).status_code == 409
    agent.client.connected = True
    api.post("/commands", json=command(agent))
    agent.client.connected = False
    agent.tick()
    assert api.get("/commands/operator-1").json()["status"] == "cancelled"
    assert agent.client.said == []


def test_tick_has_a_bounded_drain_under_reentrant_admission(host_api, monkeypatch) -> None:
    _host, agent, api = host_api

    def enqueue_from_send(text: str) -> None:
        agent.client.said.append(text)
        index = len(agent.client.said)
        if index < 100:
            assert (
                api.post("/commands", json=command(agent, f"reentrant-{index}")).status_code == 200
            )

    monkeypatch.setattr(agent.client, "say", enqueue_from_send)
    api.post("/commands", json=command(agent))
    agent.tick()
    assert len(agent.client.said) == 64
    assert api.get("/commands/reentrant-64").json()["status"] == "queued"


def test_host_chat_refuses_unknown_fields_instead_of_ignoring_payload_conflicts(host_api) -> None:
    _host, agent, api = host_api
    request = command(agent)
    request["password"] = "not-a-credential-input"
    assert api.post("/commands", json=request).status_code == 400
    assert agent.client.said == []


def test_exact_utf8_packet_limit_counts_name_prefix_header_and_nul(host_api) -> None:
    _host, agent, api = host_api
    budget = 65535 - len((agent.client.char_name + " : ").encode()) - 5
    text = "é" * (budget // 2) + "x" * (budget % 2)
    assert api.post("/commands", json=command(agent, text=text)).status_code == 200
    assert api.post("/commands", json=command(agent, "over-limit", text + "x")).status_code == 400
    agent.tick()
    assert agent.client.said == [text]
