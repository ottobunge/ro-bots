"""Provider-neutral JSON transport and approved read-only investigation port."""

from typing import Any, Protocol

from robots.domain.planning import PlanningIdentity
from robots.ports.planning import InvestigationTools


class PlanningModel(Protocol):
    def complete(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class InvestigationReadPort(InvestigationTools, Protocol):
    def read(
        self,
        identity: PlanningIdentity,
        topic: str,
        *,
        skill_id: int | None = None,
        rule_topic: str = "",
        cursor: int = 0,
        query: str = "",
        note_id: int = 0,
        offset: int = 0,
        max_utf8_bytes: int = 4096,
    ) -> dict[str, Any]: ...
