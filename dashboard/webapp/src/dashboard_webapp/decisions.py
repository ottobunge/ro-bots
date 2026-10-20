"""Agent decision history: one agent's ``decision_tail`` across all receipts.

The receipts are read newest first through the RunSource interface; the agent
inside a receipt is keyed ``host_fixture_N`` and matches the DB character whose
name ends in ``_N`` (the persona index suffix). Every read is defensive —
receipts missing the tail or the agent are skipped without breaking the
history, matching the store's "not supplied" convention.
"""

from __future__ import annotations

import re
from typing import Any

from dashboard_webapp.models import RunDetail
from dashboard_webapp.repository import AgentSource, DataSourceError, RunSource

DECISIONS_LIMIT_DEFAULT = 100
DECISIONS_LIMIT_CAP = 1000

_PERSONA_INDEX = re.compile(r"_([0-9]+)$")


def clamp_limit(limit: int, default: int = DECISIONS_LIMIT_DEFAULT) -> int:
    """Clamp a query-string limit into ``[1, CAP]``."""
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, DECISIONS_LIMIT_CAP))


def persona_index(name: str | None) -> str | None:
    """The trailing ``_N`` of a character name (persona index), if present."""
    match = _PERSONA_INDEX.search(name or "")
    return match.group(1) if match else None


def _matching_agent(detail: RunDetail, index: str) -> dict[str, Any] | None:
    for key, agent in (detail.agents or {}).items():
        if persona_index(key) == index and isinstance(agent, dict):
            return agent
    return None


def agent_decision_history(
    runs: RunSource, agents: AgentSource, char_id: int, limit: int = DECISIONS_LIMIT_DEFAULT
) -> dict[str, Any]:
    """Aggregate one agent's decisions across receipts, newest receipt first.

    Raises ``UnknownAgentError`` (-> 404) for unknown char ids and lets a
    fully degraded run source raise ``DataSourceError`` (-> 503); unreadable
    single receipts are skipped so one bad file never blanks the history.
    """
    resolved = clamp_limit(limit)
    detail = agents.agent_detail(char_id)
    index = persona_index(detail.agent.name)

    decisions: list[dict[str, Any]] = []
    runs_covered = 0
    if index is not None:
        for summary in runs.list_runs():
            try:
                receipt = runs.run_detail(summary.run_id)
            except DataSourceError:
                continue
            entry = _matching_agent(receipt, index)
            if entry is None:
                continue
            runs_covered += 1
            emission = entry.get("emission")
            tail = emission.get("decision_tail") if isinstance(emission, dict) else None
            for row in tail or []:
                if len(decisions) >= resolved:
                    break
                if not isinstance(row, dict):
                    continue
                decisions.append(
                    {
                        "run_id": summary.run_id,
                        "started_ts": summary.started_ts,
                        "event": row.get("event"),
                        "goal": row.get("goal"),
                        "plan_targets": row.get("plan_targets"),
                        "actions": row.get("actions"),
                        "error_class": row.get("error_class"),
                    }
                )
            if len(decisions) >= resolved:
                break

    return {
        "agent": {"char_id": char_id, "name": detail.agent.name, "persona_index": index},
        "decisions": decisions,
        "runs_covered": runs_covered,
        "limit": resolved,
    }
