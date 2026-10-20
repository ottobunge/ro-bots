"""API + aggregation tests for GET /api/agents/{id}/decisions.

The decision history aggregates an agent's ``decision_tail`` across the window
receipts, newest receipt first, each entry tagged with its ``run_id``. The
receipts are read through the RunSource interface, so the schema-drift cases
(missing tails, missing agents) are synthetic receipts shaped like the real
store's projection.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from dashboard_webapp.app import create_app
from dashboard_webapp.config import AppConfig
from dashboard_webapp.models import AgentDetail, AgentSummary, RunDetail, RunSummary
from dashboard_webapp.repository import DataSourceError, UnknownAgentError, UnknownRunError
from tests.conftest import AGENT_1, DETAIL_0

CHAR_0 = 150001  # conftest AGENT_0: name "Fx_0" -> persona index "0"
CHAR_1 = 150002  # conftest AGENT_1: name "Fx_1" -> persona index "1"


def _summary(run_id: str, started_ts: float) -> RunSummary:
    return RunSummary(
        run_id=run_id,
        file=f"{run_id}.json",
        started_ts=started_ts,
        passed=True,
        scenario="operator_controlled_grind",
        operator="playing-grind-emission",
        elapsed_s=1800.0,
        agent_count=2,
        agents_passed=2,
        headline={},
    )


def _detail(run_id: str, started_ts: float, agents: dict[str, Any]) -> RunDetail:
    return RunDetail(summary=_summary(run_id, started_ts), agents=agents, meta={}, omitted=[])


def _tail(*rows: dict[str, Any]) -> dict[str, Any]:
    return {"emission": {"decision_tail": list(rows)}}


def _row(event: str, error_class: str | None = None) -> dict[str, Any]:
    return {
        "event": event,
        "goal": "grind on prt_fild08",
        "plan_targets": [100, 99],
        "actions": [{"type": "walk", "x": 101, "y": 100}],
        "error_class": error_class,
    }


def _receipts() -> list[RunDetail]:
    """Synthetic receipts, newest first, covering the schema-drift cases."""
    return [
        # newest receipt: both agents, richer tails
        _detail(
            "receipt-3000",
            3000.0,
            {
                "host_fixture_0": _tail(_row("Heartbeat"), _row("Move")),
                "host_fixture_1": _tail(_row("Heartbeat-other")),
            },
        ),
        # older receipt: host_fixture_0 with a single error-classed row
        _detail("receipt-2000", 2000.0, {"host_fixture_0": _tail(_row("Attack", "timeout"))}),
        # schema drift: pre-emission receipt — agent present, no decision_tail at all
        _detail(
            "receipt-1000",
            1000.0,
            {"host_fixture_0": {"passed": True, "decision_calls": {"count": 3}}},
        ),
        # agent missing from this receipt entirely
        _detail("receipt-500", 500.0, {"host_fixture_1": _tail(_row("Heartbeat-500"))}),
    ]


class MultiReceiptRunSource:
    """RunSource fake holding several receipts (list order = newest first)."""

    def __init__(self, details: list[RunDetail], error: DataSourceError | None = None) -> None:
        self.details = details
        self.error = error
        self._by_id = {d.summary.run_id: d for d in details}

    def list_runs(self) -> list[RunSummary]:
        if self.error is not None:
            raise self.error
        return [d.summary for d in self.details]

    def run_detail(self, run_id: str) -> RunDetail:
        if self.error is not None:
            raise self.error
        detail = self._by_id.get(run_id)
        if detail is None:
            raise UnknownRunError(f"unknown run: {run_id}")
        return detail


def _agent_details() -> dict[int, AgentDetail]:
    no_index = AgentSummary(char_id=150003, name="NoPersonaSuffix", online=False)
    return {
        150001: DETAIL_0,
        150002: AgentDetail(agent=AGENT_1, inventory=[], stats={}, memory_files=[]),
        150003: AgentDetail(agent=no_index, inventory=[], stats={}, memory_files=[]),
    }


def _client(
    details: list[RunDetail] | None = None, runs_error: DataSourceError | None = None
) -> TestClient:
    return TestClient(
        create_app(
            agents=_FailingAgentSource(),
            runs=MultiReceiptRunSource(details or _receipts(), error=runs_error),
            events=None,
            commands=None,
            goals=None,
            memory=None,
            config=AppConfig(),
        )
    )


class _FailingAgentSource:
    """Minimal AgentSource over the conftest fixtures + a no-suffix agent."""

    def list_agents(self) -> list[AgentSummary]:
        raise NotImplementedError

    def agent_detail(self, char_id: int) -> AgentDetail:
        detail = _agent_details().get(char_id)
        if detail is None:
            raise UnknownAgentError(f"unknown agent: {char_id}")
        return detail


def test_decisions_aggregate_newest_first_tagged_with_run_id() -> None:
    body = _client().get(f"/api/agents/{CHAR_0}/decisions").json()

    assert body["agent"] == {"char_id": CHAR_0, "name": "Fx_0", "persona_index": "0"}
    assert [(d["run_id"], d["event"]) for d in body["decisions"]] == [
        ("receipt-3000", "Heartbeat"),
        ("receipt-3000", "Move"),
        ("receipt-2000", "Attack"),
    ]
    assert body["runs_covered"] == 3  # 3000, 2000 and the tail-less 1000
    assert body["limit"] == 100  # default


def test_decision_rows_carry_fields_and_receipt_timestamp() -> None:
    body = _client().get(f"/api/agents/{CHAR_0}/decisions").json()

    third = body["decisions"][2]
    assert third["started_ts"] == 2000.0
    assert third["goal"] == "grind on prt_fild08"
    assert third["plan_targets"] == [100, 99]
    assert third["actions"] == [{"type": "walk", "x": 101, "y": 100}]
    assert third["error_class"] == "timeout"


def test_limit_is_respected_and_stops_across_receipts() -> None:
    body = _client().get(f"/api/agents/{CHAR_0}/decisions?limit=2").json()

    assert [d["event"] for d in body["decisions"]] == ["Heartbeat", "Move"]
    assert body["limit"] == 2
    assert body["runs_covered"] == 1  # stopped inside the newest receipt

    exhausted = _client().get(f"/api/agents/{CHAR_0}/decisions?limit=250").json()
    assert len(exhausted["decisions"]) == 3
    assert exhausted["runs_covered"] == 3


def test_agent_without_persona_index_matches_no_receipts() -> None:
    body = _client().get("/api/agents/150003/decisions").json()

    assert body["decisions"] == []
    assert body["runs_covered"] == 0
    assert body["agent"]["persona_index"] is None


def test_other_agent_only_sees_its_own_receipts() -> None:
    body = _client().get(f"/api/agents/{CHAR_1}/decisions").json()

    assert [d["event"] for d in body["decisions"]] == ["Heartbeat-other", "Heartbeat-500"]
    assert body["runs_covered"] == 2


def test_unknown_agent_is_404() -> None:
    assert _client().get("/api/agents/999999/decisions").status_code == 404


def test_degraded_run_source_is_503() -> None:
    res = _client(runs_error=DataSourceError("receipts glob missing")).get(
        f"/api/agents/{CHAR_0}/decisions"
    )

    assert res.status_code == 503


def test_unreadable_single_receipt_is_skipped() -> None:
    class PartiallyBroken(MultiReceiptRunSource):
        def run_detail(self, run_id: str) -> RunDetail:
            if run_id == "receipt-2000":
                raise DataSourceError(f"unreadable receipt: {run_id}.json")
            return super().run_detail(run_id)

    app = create_app(
        agents=_FailingAgentSource(),
        runs=PartiallyBroken(_receipts()),
        events=None,
        commands=None,
        goals=None,
        memory=None,
        config=AppConfig(),
    )

    body = TestClient(app).get(f"/api/agents/{CHAR_0}/decisions").json()

    assert [d["run_id"] for d in body["decisions"]] == ["receipt-3000", "receipt-3000"]
    assert body["runs_covered"] == 2  # 3000 (rows) + 1000 (agent present, tail-less)


@pytest.mark.parametrize("bad_limit", [0, -5])
def test_non_positive_limit_clamps_to_one(bad_limit: int) -> None:
    body = _client().get(f"/api/agents/{CHAR_0}/decisions?limit={bad_limit}").json()

    assert body["limit"] == 1
    assert len(body["decisions"]) == 1


def test_huge_limit_clamps_to_cap() -> None:
    body = _client().get("/api/agents/150001/decisions?limit=10000").json()

    assert body["limit"] == 1000
