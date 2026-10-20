"""The small repository interface every dashboard data source implements.

The app layer depends only on these protocols (plus the models), so tests can
stub MariaDB, the receipts glob and the WorldFeed behind fakes — offline TDD
with no live server.
"""

from __future__ import annotations

from typing import Protocol

from dashboard_webapp.models import AgentDetail, AgentSummary, EventsPage, RunDetail, RunSummary


class DataSourceError(Exception):
    """A source is unreachable or unreadable; endpoints answer 503."""


class UnknownAgentError(DataSourceError):
    """No such char id; endpoints answer 404."""


class UnknownRunError(DataSourceError):
    """No such receipt id; endpoints answer 404."""


class AgentSource(Protocol):
    def list_agents(self) -> list[AgentSummary]: ...

    def agent_detail(self, char_id: int) -> AgentDetail: ...


class RunSource(Protocol):
    def list_runs(self) -> list[RunSummary]: ...

    def run_detail(self, run_id: str) -> RunDetail: ...


class EventSource(Protocol):
    def recent_events(self, limit: int) -> EventsPage: ...


class GoalEnricher(Protocol):
    """Best-effort goal/plan join (character name -> WorldFeed persona)."""

    def enrich(self, agents: list[AgentSummary]) -> list[AgentSummary]: ...


class MemoryViewerLike(Protocol):
    def list(self, needle: str) -> list: ...
