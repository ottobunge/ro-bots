"""API tests for the agent endpoints (against fake sources — offline TDD)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dashboard_webapp.app import create_app
from dashboard_webapp.config import AppConfig
from dashboard_webapp.models import GoalPlan
from dashboard_webapp.repository import DataSourceError
from tests.conftest import FakeAgentSource, FakeGoals


@pytest.fixture
def client() -> TestClient:
    app = create_app(
        agents=FakeAgentSource(),
        runs=None,
        events=None,
        commands=None,
        goals=FakeGoals({"Fx_0": GoalPlan(goal="grind", plan="level to 45")}),
        memory=None,
        config=AppConfig(memory_root="/data/memory"),
    )
    return TestClient(app)


def test_agent_list_shape_and_goal_enrichment(client: TestClient) -> None:
    res = client.get("/api/agents")

    assert res.status_code == 200
    body = res.json()
    assert body["source"] == {"ok": True, "goals_error": None}
    first, second = body["agents"]
    assert first == {
        "char_id": 150001,
        "name": "Fx_0",
        "class": 0,
        "base_level": 9,
        "job_level": 7,
        "hp": 55,
        "sp": 12,
        "x": 152,
        "y": 150,
        "map": "prontera",
        "online": True,
        "goal": "grind",
        "plan": "level to 45",
    }
    assert second["goal"] is None


def test_agent_list_survives_goal_source_failure() -> None:
    app = create_app(
        agents=FakeAgentSource(),
        runs=None,
        events=None,
        commands=None,
        goals=FakeGoals(error=RuntimeError("worldfeed down")),
        memory=None,
        config=AppConfig(),
    )
    body = TestClient(app).get("/api/agents").json()

    assert body["source"]["ok"] is True
    assert "worldfeed down" in body["source"]["goals_error"]
    assert all(a["goal"] is None for a in body["agents"])


def test_agent_detail_shape(client: TestClient) -> None:
    res = client.get("/api/agents/150001")

    assert res.status_code == 200
    body = res.json()
    assert body["agent"]["char_id"] == 150001
    assert body["inventory"] == [
        {"nameid": 909, "amount": 12, "identify": 1, "equip": 0, "refine": 0, "attribute": 0}
    ]
    assert body["stats"]["zeny"] == 50
    assert body["memory"] == {
        "root": "/data/memory",
        "files": [
            {
                "path": "playing-native-memory/host_fixture_0.jsonl",
                "size_bytes": 128,
                "modified_ts": 1792400000.0,
            }
        ],
    }


def test_agent_detail_uses_memory_viewer_with_agent_name() -> None:
    seen: list[str] = []

    class RecordingMemory:
        def list(self, needle: str):
            seen.append(needle)
            return []

    app = create_app(
        agents=FakeAgentSource(),
        runs=None,
        events=None,
        commands=None,
        goals=None,
        memory=RecordingMemory(),
        config=AppConfig(memory_root="/data/memory"),
    )
    TestClient(app).get("/api/agents/150001")
    assert seen == ["Fx_0"]


def test_agent_detail_unknown_is_404(client: TestClient) -> None:
    res = client.get("/api/agents/424242")
    assert res.status_code == 404
    assert res.json()["detail"] == "unknown agent: 424242"


def test_agent_list_503_when_source_degraded() -> None:
    app = create_app(
        agents=FakeAgentSource(error=DataSourceError("mariadb unreachable")),
        runs=None,
        events=None,
        commands=None,
        goals=None,
        memory=None,
        config=AppConfig(),
    )
    res = TestClient(app).get("/api/agents")

    assert res.status_code == 503
    assert "mariadb unreachable" in res.json()["detail"]
