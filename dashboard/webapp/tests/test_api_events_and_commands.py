"""API tests for the WorldFeed event proxy and the command stub endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from dashboard_webapp.app import create_app
from dashboard_webapp.commands import InMemoryCommandQueue
from dashboard_webapp.config import AppConfig
from dashboard_webapp.models import FeedEvent
from tests.conftest import FakeEventSource, FakeRunSource


def _client(events: FakeEventSource) -> TestClient:
    app = create_app(
        agents=None,
        runs=FakeRunSource(),
        events=events,
        commands=InMemoryCommandQueue(),
        goals=None,
        memory=None,
        config=AppConfig(worldfeed_url="http://worldfeed:8400"),
    )
    return TestClient(app)


def test_events_shape_and_upstream_status() -> None:
    events = FakeEventSource(
        [FeedEvent(id=3, ts=1792400003.0, kind="chat", summary="hi", operator_forced=False)]
    )
    body = _client(events).get("/api/events").json()

    assert body["upstream"] == {"url": "http://worldfeed:8400", "ok": True, "error": None}
    assert body["events"] == [
        {"id": 3, "ts": 1792400003.0, "kind": "chat", "summary": "hi", "operator_forced": False}
    ]


def test_events_limit_clamped_to_cap() -> None:
    events = FakeEventSource()
    _client(events).get("/api/events", params={"limit": 10000})

    assert events.requested_limits == [200]


def test_events_upstream_failure_still_200_with_error() -> None:
    body = _client(FakeEventSource(error="connection refused")).get("/api/events").json()

    assert body["events"] == []
    assert body["upstream"]["ok"] is False
    assert "connection refused" in body["upstream"]["error"]


def test_command_post_queues_and_returns_202() -> None:
    app = create_app(
        agents=None,
        runs=FakeRunSource(),
        events=None,
        commands=InMemoryCommandQueue(),
        goals=None,
        memory=None,
        config=AppConfig(),
    )
    client = TestClient(app)

    res = client.post("/api/agents/150001/command", json={"command": "/hi there"})

    assert res.status_code == 202
    body = res.json()
    assert body["id"].startswith("cmd-")
    assert body["status"] == "queued"
    assert body["agent_id"] == 150001
    assert "stub" in body["note"].lower()

    status = client.get(f"/api/commands/{body['id']}")
    assert status.status_code == 200
    assert status.json()["command"] == "/hi there"


def test_command_validation() -> None:
    app = create_app(
        agents=None,
        runs=FakeRunSource(),
        events=None,
        commands=InMemoryCommandQueue(),
        goals=None,
        memory=None,
        config=AppConfig(),
    )
    client = TestClient(app)

    assert client.post("/api/agents/1/command", json={}).status_code == 422
    assert client.post("/api/agents/1/command", json={"command": ""}).status_code == 422
    assert client.post("/api/agents/1/command", json={"command": "x" * 501}).status_code == 422
    # nothing was queued by the rejected payloads
    assert client.get("/api/commands/cmd-none").status_code == 404
