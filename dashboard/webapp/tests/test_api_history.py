"""API tests for the per-agent history endpoints (fixture traces, offline TDD)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dashboard_webapp.app import create_app
from dashboard_webapp.config import AppConfig
from dashboard_webapp.traces import TraceHistory
from tests.conftest import AGENT_0, AGENT_1, FakeAgentSource, FakeGoals

LINE_A = {
    "t": "2026-10-22T10:00:00+00:00",
    "persona": "pop_h_m0",
    "kind": "goal_review",
    "goal": "grind",
    "previous_goal": "idle_town",
    "trigger": "heartbeat",
}
LINE_B = {
    "t": "2026-10-22T10:01:00+00:00",
    "persona": "pop_h_m0",
    "kind": "world_event",
    "map": "prt_fild08",
    "x": 170,
    "y": 372,
    "event": "MonsterSpotted",
    "monster": "Poring",
    "monster_id": 1001,
    "monster_x": 174,
    "monster_y": 358,
}
LINE_C = {
    "t": "2026-10-22T10:02:00+00:00",
    "persona": "pop_h_m0",
    "kind": "action_executed",
    "map": "prt_fild08",
    "x": 170,
    "y": 372,
    "action": "Attack",
    "params": {"target_id": 1001},
}
LINE_D = {
    "t": "2026-10-22T10:03:00+00:00",
    "persona": "pop_h_m0",
    "kind": "world_event",
    "map": "prt_fild08",
    "x": 170,
    "y": 372,
    "event": "DamageTaken",
    "amount": 7,
    "from_id": 1001,
}
LINE_E = {
    "t": "2026-10-22T10:04:00+00:00",
    "persona": "pop_h_m0",
    "kind": "chat_sent",
    "map": "prt_fild08",
    "x": 170,
    "y": 372,
    "channel": "party",
    "message": "train to fild08",
    "action": "PartyChat",
}


@pytest.fixture
def history_env(tmp_path: Path) -> tuple[AppConfig, TraceHistory]:
    traces_dir = tmp_path / "traces"
    traces_dir.mkdir()
    (traces_dir / "pop_h_m0.jsonl").write_text(
        "\n".join(json.dumps(line) for line in (LINE_A, LINE_B, LINE_C, LINE_D, LINE_E)) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "host-manifest.json").write_text(
        json.dumps(
            {"accounts": [{"persona_id": "pop_h_m0", "char_name": "Fx_0", "account": "a0"}]}
        ),
        encoding="utf-8",
    )
    config = AppConfig(
        traces_dir=str(traces_dir),
        host_manifest=str(tmp_path / "host-manifest.json"),
        memory_root="/data/memory",
    )
    return config, TraceHistory(traces_dir, tmp_path / "host-manifest.json")


def make_client(config: AppConfig, traces: TraceHistory | None) -> TestClient:
    agents = FakeAgentSource(agents=[AGENT_0, AGENT_1], details={})
    return TestClient(
        create_app(
            agents=agents,
            runs=None,
            events=None,
            commands=None,
            goals=FakeGoals(),
            memory=None,
            traces=traces,
            config=config,
        )
    )


@pytest.fixture
def client(history_env: tuple[AppConfig, TraceHistory]) -> TestClient:
    config, traces = history_env
    return make_client(config, traces)


class TestHistoryEndpoint:
    def test_history_by_char_name(self, client: TestClient) -> None:
        res = client.get("/api/agents/Fx_0/history")
        assert res.status_code == 200
        body = res.json()
        assert body["persona"] == "pop_h_m0"
        assert body["count"] == 5
        assert body["events"][0]["t"] == "2026-10-22T10:04:00+00:00"
        assert body["source"]["ok"] is True

    def test_history_by_persona_id(self, client: TestClient) -> None:
        body = client.get("/api/agents/pop_h_m0/history").json()
        assert body["persona"] == "pop_h_m0"
        assert body["count"] == 5

    def test_kind_filter_param(self, client: TestClient) -> None:
        body = client.get(
            "/api/agents/Fx_0/history", params={"kinds": "chat_sent,world_event"}
        ).json()
        assert {e["kind"] for e in body["events"]} == {"chat_sent", "world_event"}
        assert body["count"] == 3

    def test_limit_and_before_cursor(self, client: TestClient) -> None:
        first = client.get("/api/agents/Fx_0/history", params={"limit": 2}).json()
        assert first["count"] == 2
        assert first["limit"] == 2
        assert first["next_before"] == "2026-10-22T10:03:00+00:00"
        second = client.get(
            "/api/agents/Fx_0/history", params={"limit": 2, "before": first["next_before"]}
        ).json()
        assert second["count"] == 2
        assert all(e["t"] < first["next_before"] for e in second["events"])

    def test_limit_cap_and_floor(self, client: TestClient) -> None:
        assert (
            client.get("/api/agents/Fx_0/history", params={"limit": 99999}).json()["limit"] == 2000
        )
        assert client.get("/api/agents/Fx_0/history", params={"limit": 0}).json()["limit"] == 1

    def test_unknown_kind_is_422(self, client: TestClient) -> None:
        res = client.get("/api/agents/Fx_0/history", params={"kinds": "telemetry"})
        assert res.status_code == 422

    def test_invalid_before_is_422(self, client: TestClient) -> None:
        res = client.get("/api/agents/Fx_0/history", params={"before": "not-a-date"})
        assert res.status_code == 422

    def test_unknown_agent_is_404(self, client: TestClient) -> None:
        res = client.get("/api/agents/ghost/history")
        assert res.status_code == 404

    def test_agent_without_trace_file_is_empty_not_404(self, client: TestClient) -> None:
        app_agents = client.get("/api/agents").json()["agents"]
        other = next(a["name"] for a in app_agents if a["name"] != "Fx_0")
        res = client.get(f"/api/agents/{other}/history")
        assert res.status_code == 200
        assert res.json()["events"] == []

    def test_char_id_resolves_via_agent_source_name(self, history_env) -> None:
        from dashboard_webapp.models import AgentDetail

        config, traces = history_env
        agents = FakeAgentSource()
        agents.details = {
            150001: AgentDetail(agent=AGENT_0, inventory=[], stats={}, memory_files=[])
        }
        client = TestClient(
            create_app(
                agents=agents,
                runs=None,
                events=None,
                commands=None,
                goals=None,
                memory=None,
                traces=traces,
                config=config,
            )
        )
        body = client.get("/api/agents/150001/history").json()
        assert body["persona"] == "pop_h_m0"
        assert body["agent"] == {"char_id": 150001, "name": "Fx_0"}

    def test_traces_not_configured_returns_empty_list(self) -> None:
        client = make_client(AppConfig(), traces=None)
        res = client.get("/api/agents/Fx_0/history")
        assert res.status_code == 200
        body = res.json()
        assert body["events"] == []
        assert body["source"]["ok"] is False

    def test_absent_traces_dir_returns_empty_list(self, tmp_path: Path) -> None:
        config = AppConfig(
            traces_dir=str(tmp_path / "missing"), host_manifest=str(tmp_path / "m.json")
        )
        client = make_client(config, TraceHistory(config.traces_dir, config.host_manifest))
        res = client.get("/api/agents/Fx_0/history")
        assert res.status_code == 200
        assert res.json()["events"] == []


class TestCombatEndpoint:
    def test_combat_aggregation_by_char_name(self, client: TestClient) -> None:
        res = client.get("/api/agents/Fx_0/combat")
        assert res.status_code == 200
        body = res.json()
        assert body["persona"] == "pop_h_m0"
        poring = body["monsters"][0]
        assert poring["name"] == "Poring"
        assert poring["encounters"] == 1
        assert poring["attacks"] == 1
        assert poring["damage_taken"] == 7
        assert body["damage_taken_total"] == 7

    def test_combat_not_configured_is_empty(self) -> None:
        body = make_client(AppConfig(), traces=None).get("/api/agents/Fx_0/combat").json()
        assert body["monsters"] == []


class TestPlansEndpoint:
    def test_plans_timeline(self, client: TestClient) -> None:
        res = client.get("/api/agents/Fx_0/plans")
        assert res.status_code == 200
        body = res.json()
        assert body["count"] == 1
        plan = body["plans"][0]
        assert plan["kind"] == "goal_review"
        assert plan["goal"] == "grind"
        assert plan["previous_goal"] == "idle_town"

    def test_plans_not_configured_is_empty(self) -> None:
        body = make_client(AppConfig(), traces=None).get("/api/agents/Fx_0/plans").json()
        assert body["plans"] == []
