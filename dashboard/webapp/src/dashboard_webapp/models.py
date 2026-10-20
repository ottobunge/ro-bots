"""Typed rows exchanged over the dashboard repository interface.

Sources produce these dataclasses; the FastAPI layer turns them into JSON with
the exact operator-facing keys (``class``, ``int`` etc. are domain terms).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AgentSummary:
    char_id: int
    name: str
    char_class: int | None = None
    base_level: int | None = None
    job_level: int | None = None
    hp: int | None = None
    sp: int | None = None
    x: int | None = None
    y: int | None = None
    map: str = ""
    online: bool = False
    goal: str | None = None
    plan: str | None = None


@dataclass(frozen=True)
class InventoryItem:
    nameid: int | None = None
    amount: int | None = None
    identify: int | None = None
    equip: int | None = None
    refine: int | None = None
    attribute: int | None = None


@dataclass(frozen=True)
class MemoryFile:
    path: str
    size_bytes: int
    modified_ts: float


@dataclass(frozen=True)
class AgentDetail:
    agent: AgentSummary
    inventory: list[InventoryItem]
    stats: dict[str, int | None]
    memory_files: list[MemoryFile]
    memory_root: str | None = None


@dataclass(frozen=True)
class GoalPlan:
    goal: str | None = None
    plan: str | None = None


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    file: str
    started_ts: float
    passed: bool | None
    scenario: str | None
    operator: str | None
    elapsed_s: float | None
    agent_count: int
    agents_passed: int
    headline: dict[str, int]


@dataclass(frozen=True)
class RunDetail:
    summary: RunSummary
    agents: dict[str, dict[str, Any]]
    meta: dict[str, Any]
    omitted: list[str]


@dataclass(frozen=True)
class FeedEvent:
    id: int
    ts: float | None = None
    kind: str | None = None
    summary: str | None = None
    operator_forced: bool | None = None


@dataclass(frozen=True)
class EventsPage:
    events: list[FeedEvent]
    upstream_url: str
    ok: bool
    error: str | None = None


def agent_json(agent: AgentSummary) -> dict[str, Any]:
    return {
        "char_id": agent.char_id,
        "name": agent.name,
        "class": agent.char_class,
        "base_level": agent.base_level,
        "job_level": agent.job_level,
        "hp": agent.hp,
        "sp": agent.sp,
        "x": agent.x,
        "y": agent.y,
        "map": agent.map,
        "online": agent.online,
        "goal": agent.goal,
        "plan": agent.plan,
    }


def inventory_json(item: InventoryItem) -> dict[str, Any]:
    return asdict(item)


def memory_file_json(file: MemoryFile) -> dict[str, Any]:
    return asdict(file)


def event_json(event: FeedEvent) -> dict[str, Any]:
    return asdict(event)


def run_summary_json(run: RunSummary) -> dict[str, Any]:
    return asdict(run)
