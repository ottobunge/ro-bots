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


def test_index_has_agent_tooltip_popover_with_cached_fetch() -> None:
    html = _client().get("/").text

    assert 'id="agentPopover"' in html
    # detail fetched on hover through the shared cached accessor
    assert "getAgentDetail" in html
    assert "/api/agents/" in html
    assert "DETAIL_TTL_MS = 30000" in html  # 30s cache


def test_index_has_third_agent_tab_view() -> None:
    html = _client().get("/").text

    assert 'data-view="agents"' in html
    assert 'data-view="runs"' in html
    assert 'data-view="agent"' in html


def test_index_has_decision_history_table_with_limit_selector() -> None:
    html = _client().get("/").text

    assert 'id="decisionTable"' in html
    assert "/decisions?limit=" in html
    assert ">50</option>" in html
    assert ">100</option>" in html
    assert ">250</option>" in html


def test_health_reports_config_without_secrets() -> None:
    res = _client().get("/api/health")

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["config"]["worldfeed_url"] == "http://127.0.0.1:8400"
    assert body["config"]["receipts_glob"] == ".work/playing-grind-emission/evidence/receipt-*.json"
    assert body["config"]["db_configured"] is False
    assert body["config"]["command_runtime_root"] == ".work/runtime/ro-bots-test/commands"


def test_index_has_population_generation_tab_with_form_and_result_panel() -> None:
    html = _client().get("/").text

    assert 'data-view="population"' in html
    assert "POST /api/population" in html or '"/api/population"' in html
    # the PopulationSpec fields
    assert 'id="popWorld"' in html
    assert 'id="popGroups"' in html
    assert 'id="popFriendsMin"' in html
    assert 'id="popFriendsMax"' in html
    assert 'id="popSolo"' in html
    assert 'id="popSeed"' in html
    # the result panel + the explicit apply step
    assert 'id="popResult"' in html
    assert "/api/population/" in html
    assert "/apply" in html


def test_index_command_box_targets_allowlist_and_shows_applied_status() -> None:
    html = _client().get("/").text

    # the send path hits the real command endpoint and polls the status
    assert "/api/commands/" in html
    assert "say " in html
    assert "goal " in html
    assert "applied" in html
