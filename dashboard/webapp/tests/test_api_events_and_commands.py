"""API tests for the WorldFeed event proxy and the command endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from dashboard_webapp.app import create_app
from dashboard_webapp.commands import JsonlCommandQueue
from dashboard_webapp.config import AppConfig
from dashboard_webapp.models import FeedEvent
from dashboard_webapp.repository import DataSourceError
from tests.conftest import FakeAgentSource, FakeEventSource, FakeRunSource

AGENT_0 = FakeAgentSource().agents[0]  # char_id 150001, name Fx_0, online


def _client(
    events: FakeEventSource | None = None,
    agents: FakeAgentSource | None = None,
    runtime: Path | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            agents=agents if agents is not None else FakeAgentSource(),
            runs=FakeRunSource(),
            events=events,
            commands=JsonlCommandQueue(runtime or Path("/tmp/dash-test-commands-unused")),
            goals=None,
            memory=None,
            config=AppConfig(worldfeed_url="http://worldfeed:8400"),
        )
    )


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


# ----------------------------------------------------------- command endpoints


def test_command_post_queues_and_returns_202(tmp_path: Path) -> None:
    client = _client(runtime=tmp_path)

    res = client.post("/api/agents/150001/command", json={"command": "say hi there"})

    assert res.status_code == 202
    body = res.json()
    assert body["id"].startswith("cmd-")
    assert body["status"] == "queued"
    assert body["agent_id"] == 150001
    assert body["kind"] == "say"
    assert body["text"] == "hi there"
    assert "stub" not in body["note"].lower()

    # the queue is the JSONL seam the host poller drains
    lines = (tmp_path / "commands.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["char_name"] == "Fx_0"  # resolved from the agent source


def test_command_goal_round_trip_dashboard_to_host(tmp_path: Path, repo_src: Path) -> None:
    from robots.app.command_poller import apply_to_host, drain_commands, write_receipts

    client = _client(runtime=tmp_path)
    queued = client.post("/api/agents/150001/command", json={"command": "goal quest"}).json()

    drained = drain_commands(tmp_path)
    assert [(c["id"], c["kind"], c["text"], c["char_name"]) for c in drained] == [
        (queued["id"], "goal", "quest", "Fx_0")
    ]

    class MiniEntry:
        char_name = "Fx_0"

    class MiniAgent:
        entry = MiniEntry()
        online = True
        goal = "grind"

    receipts = apply_to_host(
        _MiniHost([MiniAgent()]),  # type: ignore[arg-type]
        drained,
    )
    write_receipts(tmp_path, receipts)

    status = client.get(f"/api/commands/{queued['id']}").json()
    assert status["status"] == "applied"
    assert status["applied_ts"] == receipts[0]["applied_ts"]


class _MiniHost:
    """Enough host for the poller: personas resolve by entry.char_name."""

    def __init__(self, agents: list[Any]) -> None:
        self.agents = {f"p{i}": agent for i, agent in enumerate(agents)}
        self.submitted: list[dict[str, Any]] = []

        class _Disp:
            def submit(_self: Any, command: dict[str, Any]) -> dict[str, Any]:
                self.submitted.append(command)
                return command

        self.commands = _Disp()


def test_command_allowlist_rejected_with_422(tmp_path: Path) -> None:
    client = _client(runtime=tmp_path)

    for raw in ("rm -rf /", "goal transmog", "teleport prontera", "/sit", "say"):
        res = client.post("/api/agents/150001/command", json={"command": raw})
        assert res.status_code == 422, raw

    assert not (tmp_path / "commands.jsonl").exists()  # nothing was persisted


def test_command_payload_validation_still_422(tmp_path: Path) -> None:
    client = _client(runtime=tmp_path)

    assert client.post("/api/agents/1/command", json={}).status_code == 422
    assert client.post("/api/agents/1/command", json={"command": ""}).status_code == 422
    assert client.post("/api/agents/1/command", json={"command": "x" * 501}).status_code == 422
    assert client.get("/api/commands/cmd-none").status_code == 404


def test_command_unknown_agent_is_404(tmp_path: Path) -> None:
    client = _client(agents=FakeAgentSource(details={}), runtime=tmp_path)

    res = client.post("/api/agents/999999/command", json={"command": "say hi"})

    assert res.status_code == 404
    assert not (tmp_path / "commands.jsonl").exists()


def test_command_with_degraded_db_still_queues(tmp_path: Path) -> None:
    client = _client(agents=FakeAgentSource(error=DataSourceError("db down")), runtime=tmp_path)

    res = client.post("/api/agents/150001/command", json={"command": "say hi"})

    assert res.status_code == 202
    line = json.loads((tmp_path / "commands.jsonl").read_text(encoding="utf-8"))
    assert line["char_name"] is None  # name unresolved; the host falls back to ids


def test_command_status_unknown_id_is_404(tmp_path: Path) -> None:
    assert _client(runtime=tmp_path).get("/api/commands/cmd-nope").status_code == 404
