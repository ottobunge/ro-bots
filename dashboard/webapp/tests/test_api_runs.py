"""API tests for the run-visibility endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dashboard_webapp.app import create_app
from dashboard_webapp.config import AppConfig
from dashboard_webapp.models import RunDetail, RunSummary
from dashboard_webapp.repository import DataSourceError
from tests.conftest import FakeRunSource


def _summary(run_id: str) -> RunSummary:
    return RunSummary(
        run_id=run_id,
        file=f"{run_id}.json",
        started_ts=1792464836.0,
        passed=False,
        scenario="operator_controlled_grind",
        operator="playing-grind-emission",
        elapsed_s=1800.0,
        agent_count=2,
        agents_passed=1,
        headline={
            "decision_calls": 42,
            "walk_sends": 10,
            "attributed_attacks": 0,
            "xp_gain_total": 130,
            "engagement_floor_met": 1,
        },
    )


def _detail() -> RunDetail:
    return RunDetail(
        summary=_summary("receipt-1792464836"),
        agents={
            "host_fixture_0": {
                "passed": True,
                "decision_calls": {"count": 21, "verdict": "observed"},
                "frame_counters": {"walk_sends": 4},
                "engagement_floor": "met",
                "emission": {
                    "decision_tail": [{"event": "Heartbeat"}],
                    "script_tail": [{"step": "approach"}],
                    "move_gate_reasons": ["no_attackable_in_reach"],
                    "gates": {},
                    "killcommit": {},
                    "xp_gain_total": 130,
                },
            }
        },
        meta={"scenario": "operator_controlled_grind"},
        omitted=["diagnostic_samples"],
    )


@pytest.fixture
def client() -> TestClient:
    app = create_app(
        agents=None,
        runs=FakeRunSource(
            summaries=[_summary("receipt-1792464836"), _summary("receipt-1792455324")],
            detail=_detail(),
        ),
        events=None,
        commands=None,
        goals=None,
        memory=None,
        config=AppConfig(),
    )
    return TestClient(app)


def test_run_list_newest_first(client: TestClient) -> None:
    body = client.get("/api/runs").json()

    assert [r["run_id"] for r in body["runs"]] == ["receipt-1792464836", "receipt-1792455324"]
    first = body["runs"][0]
    assert first["passed"] is False
    assert first["agent_count"] == 2
    assert first["headline"]["decision_calls"] == 42


def test_run_detail_carries_per_agent_counters_and_tails(client: TestClient) -> None:
    body = client.get("/api/runs/receipt-1792464836").json()

    agent = body["agents"]["host_fixture_0"]
    assert agent["decision_calls"]["count"] == 21
    assert agent["emission"]["decision_tail"] == [{"event": "Heartbeat"}]
    assert agent["emission"]["script_tail"] == [{"step": "approach"}]
    assert agent["emission"]["move_gate_reasons"] == ["no_attackable_in_reach"]
    assert body["run_id"] == "receipt-1792464836"
    assert body["omitted"] == ["diagnostic_samples"]


def test_run_detail_unknown_is_404(client: TestClient) -> None:
    assert client.get("/api/runs/receipt-does-not-exist").status_code == 404


def test_run_list_503_when_source_degraded() -> None:
    app = create_app(
        agents=None,
        runs=FakeRunSource(error=DataSourceError("receipts glob missing")),
        events=None,
        commands=None,
        goals=None,
        memory=None,
        config=AppConfig(),
    )
    res = TestClient(app).get("/api/runs")

    assert res.status_code == 503
