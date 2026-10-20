"""Serialized, single-owner offline lifecycle; no provider or native calls.

Tokens are local correlation IDs, not native authority. Callers serialize all
access and supply a finite monotonic clock. There is no global owner registry,
thread safety, persistence, async scheduler or actual planner implementation.
max_attempts counts requests per unsuccessful episode: rejection/timeout do not
reset it; success or a relevant identity change does. Cooldown starts at request
issuance. Capability freshness/ownership are caller responsibilities; execution
still requires separately integrated received-state/mechanical action validation.
"""

from collections.abc import Callable
from dataclasses import replace

from robots.domain.planning import (
    Capabilities,
    PlanningIdentity,
    PlanningRequest,
    ProposedPlan,
    bounded_text,
    positive_number,
)


class PlanLifecycle:
    def __init__(
        self,
        identity: PlanningIdentity,
        clock: Callable[[], float],
        cooldown: float = 10.0,
        wait: float = 5.0,
        max_attempts: int = 3,
    ) -> None:
        if (
            not positive_number(cooldown)
            or not positive_number(wait)
            or type(max_attempts) is not int
            or not 1 <= max_attempts <= 8
        ):
            message = "invalid lifecycle configuration"
            raise ValueError(message)
        self.identity = identity
        self.clock = clock
        self.cooldown = cooldown
        self.wait = wait
        self.max_attempts = max_attempts
        self.active: ProposedPlan | None = None
        self.version = 0
        self.pending: PlanningRequest | None = None
        self.reasons: tuple[str, ...] = ()
        self.outcome = "idle"
        self.counters = dict.fromkeys(
            ("requests", "coalesced", "admitted", "rejected", "timeouts"), 0
        )
        self._serial = 0
        self._attempts = 0
        self._next_at = 0.0

    def request(self, reason: str) -> PlanningRequest | None:
        if not bounded_text(reason):
            message = "invalid escalation reason"
            raise ValueError(message)
        self.poll()
        if reason not in self.reasons and len(self.reasons) < 8:
            self.reasons += (reason,)
        if self.pending is not None:
            self.pending = replace(self.pending, reasons=self.reasons)
            self.counters["coalesced"] += 1
            return self.pending
        if self._attempts >= self.max_attempts:
            self.outcome = "exhausted"
            return None
        if self.clock() < self._next_at:
            self.outcome = "cooldown"
            return None
        self._attempts += 1
        self._next_at = self.clock() + self.cooldown
        self.counters["requests"] += 1
        self._serial += 1
        self.pending = PlanningRequest(
            str(self._serial), self.identity, self.version, self.reasons, self.clock() + self.wait
        )
        return self.pending

    def admit(
        self, request: PlanningRequest, plan: ProposedPlan, capabilities: Capabilities
    ) -> bool:
        self.poll()
        if (
            self.pending is None
            or request.token != self.pending.token
            or request.base_version != self.version
            or request.identity != self.identity
        ):
            self.counters["rejected"] += 1
            self.outcome = "stale"
            return False
        if plan.identity != self.identity:
            self.counters["rejected"] += 1
            self.outcome = "identity"
            self.pending = None
            return False
        denial = plan.denial(capabilities, self.clock())
        if denial is not None:
            self.counters["rejected"] += 1
            self.outcome = denial
            self.pending = None
            return False
        self.active = plan
        self.version += 1
        self.pending = None
        self._attempts = 0
        self.reasons = ()
        self.counters["admitted"] += 1
        self.outcome = "admitted"
        return True

    def poll(self) -> None:
        """Expire a wait without blocking, sleeping, or starting work."""
        if self.pending is not None and self.clock() >= self.pending.deadline:
            self.pending = None
            self.counters["timeouts"] += 1
            self.outcome = "timeout"

    def update_identity(self, identity: PlanningIdentity) -> None:
        if identity != self.identity:
            self.identity = identity
            self.active = None
            self.pending = None
            self.reasons = ()
            self.version += 1
            self._attempts = 0
            self._next_at = self.clock()
            self.outcome = "identity-changed"

    def execution_plan(self, capabilities: Capabilities | None = None) -> ProposedPlan | None:
        if self.active is None or self.clock() >= self.active.review_at:
            return None
        if capabilities is not None and self.active.denial(capabilities, self.clock()) is not None:
            return None
        return self.active
