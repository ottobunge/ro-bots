"""Best-effort goal/plan enrichment from the WorldFeed (port 8400).

Matches a character name to a WorldFeed persona (by persona name or id) and
copies the persona's current goal/plan onto the agent row. Any upstream failure
degrades to ``goal=None`` and never breaks the agent list.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import httpx

from dashboard_webapp.models import AgentSummary

_DEFAULT_TIMEOUT_S = 2.0


def _default_client_factory(**kwargs: Any) -> httpx.Client:
    return httpx.Client(**kwargs)


class HttpGoalSource:
    def __init__(
        self,
        base_url: str,
        client_factory: Any = None,
        timeout_s: float = _DEFAULT_TIMEOUT_S,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client_factory = client_factory or _default_client_factory
        self._timeout_s = timeout_s
        self.last_error: str | None = None

    def enrich(self, agents: list[AgentSummary]) -> list[AgentSummary]:
        try:
            index = self._persona_index()
            enriched = []
            for agent in agents:
                persona_id = index.get(agent.name)
                goal_plan: dict[str, Any] = {}
                if persona_id is not None:
                    goal_plan = self._persona_detail(persona_id)
                enriched.append(
                    replace(agent, goal=goal_plan.get("goal"), plan=goal_plan.get("plan"))
                )
            self.last_error = None
            return enriched
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            self.last_error = str(exc)
            return [replace(agent, goal=None, plan=None) for agent in agents]

    def _persona_index(self) -> dict[str, str]:
        payload = self._get_json("/feed/roster")
        index: dict[str, str] = {}
        for persona in payload.get("agents") or []:
            if not isinstance(persona, dict):
                continue
            persona_id = persona.get("persona_id")
            if not isinstance(persona_id, str):
                continue
            index[persona_id] = persona_id
            name = persona.get("name")
            if isinstance(name, str):
                index[name] = persona_id
        return index

    def _persona_detail(self, persona_id: str) -> dict[str, Any]:
        payload = self._get_json(f"/feed/agent/{persona_id}")
        return {"goal": payload.get("goal"), "plan": payload.get("plan")}

    def _get_json(self, path: str) -> dict[str, Any]:
        with self._client_factory(timeout=self._timeout_s) as client:
            response = client.get(f"{self.base_url}{path}")
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError(f"unexpected payload for {path}")
        return payload
