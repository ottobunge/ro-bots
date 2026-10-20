"""Future provider-neutral planner/investigation/chat boundaries, not adapters.

An implementation must bind investigation to request.identity, preserve unknown
observations and provenance, and compute mechanics outside the LLM. This core
neither invokes these protocols nor establishes native action eligibility.
"""

from typing import Protocol

from robots.domain.planning import Capabilities, PlanningIdentity, PlanningRequest, ProposedPlan


class InvestigationTools(Protocol):
    def observed_capabilities(self, identity: PlanningIdentity) -> Capabilities:
        """Return only this identity's currently fresh prerequisite summary."""
        ...

    def public_rule(self, identity: PlanningIdentity, topic: str) -> str | None:
        """Bounded public-rule lookup; None means unknown, not permission."""
        ...


class PlannerPort(Protocol):
    def propose(self, request: PlanningRequest, _tools: InvestigationTools) -> ProposedPlan:
        """Future LLM tool loop; caller schedules work outside the lifecycle."""
        ...


class PlanningChatPort(Protocol):
    def reply(self, identity: PlanningIdentity, message: str) -> str:
        """Free-form chat is separate from plan proposal and admission."""
        ...
