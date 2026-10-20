"""Shared fakes implementing the dashboard repository protocols.

The fakes are the executable specification of the small repository interface:
every API test runs against these instead of MariaDB, the receipts glob or the
WorldFeed upstream (offline TDD, no live server needed).
"""

from __future__ import annotations

from typing import Any

from dashboard_webapp.models import (
    AgentDetail,
    AgentSummary,
    EventsPage,
    FeedEvent,
    GoalPlan,
    InventoryItem,
    MemoryFile,
    RunDetail,
    RunSummary,
)
from dashboard_webapp.repository import (
    AgentSource,
    DataSourceError,
    EventSource,
    RunSource,
    UnknownAgentError,
    UnknownRunError,
)

AGENT_0 = AgentSummary(
    char_id=150001,
    name="Fx_0",
    char_class=0,
    base_level=9,
    job_level=7,
    hp=55,
    sp=12,
    x=152,
    y=150,
    map="prontera",
    online=True,
)
AGENT_1 = AgentSummary(
    char_id=150002,
    name="Fx_1",
    char_class=1,
    base_level=3,
    job_level=2,
    hp=30,
    sp=8,
    x=100,
    y=99,
    map="prt_fild08",
    online=False,
)

DETAIL_0 = AgentDetail(
    agent=AGENT_0,
    inventory=[InventoryItem(nameid=909, amount=12, identify=1, equip=0, refine=0, attribute=0)],
    stats={"str": 5, "agi": 5, "vit": 5, "int": 5, "dex": 5, "luk": 5, "zeny": 50},
    memory_files=[
        MemoryFile(
            path="playing-native-memory/host_fixture_0.jsonl",
            size_bytes=128,
            modified_ts=1792400000.0,
        )
    ],
    memory_root="/data/memory",
)


class FakeAgentSource(AgentSource):
    def __init__(
        self,
        agents: list[AgentSummary] | None = None,
        details: dict[int, AgentDetail] | None = None,
        error: DataSourceError | None = None,
    ) -> None:
        self.agents = agents if agents is not None else [AGENT_0, AGENT_1]
        self.details = details if details is not None else {150001: DETAIL_0}
        self.error = error
        self.list_calls = 0

    def list_agents(self) -> list[AgentSummary]:
        self.list_calls += 1
        if self.error is not None:
            raise self.error
        return list(self.agents)

    def agent_detail(self, char_id: int) -> AgentDetail:
        if self.error is not None:
            raise self.error
        detail = self.details.get(char_id)
        if detail is None:
            raise UnknownAgentError(f"unknown agent: {char_id}")
        return detail


class FakeGoals:
    """Goal enrichment stub: maps character name -> goal/plan."""

    def __init__(
        self, goals: dict[str, GoalPlan] | None = None, error: Exception | None = None
    ) -> None:
        self.goals = goals or {}
        self.error = error
        self.calls: list[list[AgentSummary]] = []

    def enrich(self, agents: list[AgentSummary]) -> list[AgentSummary]:
        self.calls.append(list(agents))
        if self.error is not None:
            raise self.error
        return [
            AgentSummary(
                **{
                    **{f: getattr(a, f) for f in a.__dataclass_fields__},
                    "goal": self.goals.get(a.name).goal if self.goals.get(a.name) else None,
                    "plan": self.goals.get(a.name).plan if self.goals.get(a.name) else None,
                }
            )
            for a in agents
        ]


def _receipt(run_id: str, agents: dict[str, Any] | None = None, **meta: Any) -> dict[str, Any]:
    return {
        "passed": False,
        "scenario": "operator_controlled_grind",
        "operator": "playing-grind-emission",
        "elapsed_s": 1800.0,
        "agents": agents if agents is not None else {},
        **meta,
    }


class FakeRunSource(RunSource):
    def __init__(
        self,
        summaries: list[RunSummary] | None = None,
        detail: RunDetail | None = None,
        error: DataSourceError | None = None,
    ) -> None:
        self.summaries = summaries or []
        self.detail = detail
        self.error = error
        self.requested_id: str | None = None

    def list_runs(self) -> list[RunSummary]:
        if self.error is not None:
            raise self.error
        return list(self.summaries)

    def run_detail(self, run_id: str) -> RunDetail:
        self.requested_id = run_id
        if self.error is not None:
            raise self.error
        if self.detail is None or self.detail.summary.run_id != run_id:
            raise UnknownRunError(f"unknown run: {run_id}")
        return self.detail


def make_run_summary(run_id: str, passed: bool = False, agents_passed: int = 1) -> RunSummary:
    return RunSummary(
        run_id=run_id,
        file=f"{run_id}.json",
        started_ts=1792464836.0,
        passed=passed,
        scenario="operator_controlled_grind",
        operator="playing-grind-emission",
        elapsed_s=1800.0,
        agent_count=2,
        agents_passed=agents_passed,
        headline={
            "decision_calls": 42,
            "walk_sends": 10,
            "attributed_attacks": 0,
            "xp_gain_total": 0,
            "engagement_floor_met": 1,
        },
    )


class FakeEventSource(EventSource):
    def __init__(self, events: list[FeedEvent] | None = None, error: str | None = None) -> None:
        self.events = events or []
        self.error = error
        self.requested_limits: list[int] = []

    def recent_events(self, limit: int) -> EventsPage:
        self.requested_limits.append(limit)
        if self.error is not None:
            return EventsPage(
                events=[], upstream_url="http://worldfeed:8400", ok=False, error=self.error
            )
        return EventsPage(
            events=list(self.events[-limit:]),
            upstream_url="http://worldfeed:8400",
            ok=True,
            error=None,
        )
