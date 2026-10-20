"""UI + health tests: the single-page dashboard and the health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from dashboard_webapp.app import create_app
from dashboard_webapp.commands import InMemoryCommandQueue
from dashboard_webapp.config import AppConfig
from tests.conftest import FakeAgentSource, FakeEventSource, FakeRunSource


def _client() -> TestClient:
    return TestClient(
        create_app(
            agents=FakeAgentSource(),
            runs=FakeRunSource(),
            events=FakeEventSource(),
            commands=InMemoryCommandQueue(),
            goals=None,
            memory=None,
            config=AppConfig(),
        )
    )


def test_index_serves_single_page_dashboard() -> None:
    res = _client().get("/")

    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    html = res.text
    assert "ro-bots" in html.lower()
    # the UI wires the API surfaces it renders
    assert "/api/agents" in html
    assert "/api/runs" in html
    assert "/api/events" in html
    # no build step: no bundler artifacts required
    assert "<script>" in html


def test_health_reports_config_without_secrets() -> None:
    res = _client().get("/api/health")

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["config"]["worldfeed_url"] == "http://127.0.0.1:8400"
    assert body["config"]["receipts_glob"] == ".work/playing-grind-emission/evidence/receipt-*.json"
    assert body["config"]["db_configured"] is False
