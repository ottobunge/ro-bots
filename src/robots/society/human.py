"""Human-player interaction events feeding the ReputationStore (ADR-005).

Every human action an agent witnesses becomes a :class:`HumanContribution`;
the :class:`ContributionScorer` turns it into a :class:`ReputationEvent`
delta (useful play moves the score up, dead weight / rudeness / kill-stealing
move it down, magnitude scales and clamps per event), and the
:class:`HumanTracker` records it. When an agent's score for a human
materially crosses the propagation threshold, chattiness decides whether the
agent gossips — the rumor spreads through the existing
``ReputationStore.propagate`` and every emitted line lands in
``propagation_log`` so tests and the observer can verify it.
"""

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, final

from robots.society.models import FriendGroup
from robots.society.society import (
    PROPAGATION_THRESHOLD,
    ReputationEvent,
    ReputationStore,
    SocialGraph,
)

ContributionKind = Literal["damage_share", "heal", "buff", "dead_weight", "rude", "kill_steal"]

DELTA_BY_KIND: dict[str, float] = {
    "damage_share": 0.4,
    "heal": 0.4,
    "buff": 0.3,
    "dead_weight": -0.3,
    "rude": -0.4,
    "kill_steal": -0.5,
}

EVENT_DELTA_MIN = -0.5
EVENT_DELTA_MAX = 0.5
MAGNITUDE_MIN = -1.0
MAGNITUDE_MAX = 1.0


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass(frozen=True, slots=True)
class HumanContribution:
    """One witnessed human action, on one map, at one time."""

    human_name: str
    kind: ContributionKind
    magnitude: float  # how strong the action was, in [-1, 1]
    map_name: str
    ts: float


@final
class ContributionScorer:
    """HumanContribution -> ReputationEvent delta (signed, scaled, clamped)."""

    @staticmethod
    def score(contribution: HumanContribution, agent_id: str) -> ReputationEvent:
        """Build the reputation event; per-event delta clamped to [-0.5, 0.5]."""
        base = DELTA_BY_KIND[contribution.kind]
        magnitude = _clamp(contribution.magnitude, MAGNITUDE_MIN, MAGNITUDE_MAX)
        delta = _clamp(base * magnitude, EVENT_DELTA_MIN, EVENT_DELTA_MAX)
        reason = f"{contribution.kind} by {contribution.human_name} on {contribution.map_name}"
        return ReputationEvent(contribution.human_name, agent_id, delta, reason)


@final
class HumanTracker:
    """Records per-(human, agent) contributions and gossips past the threshold."""

    def __init__(
        self,
        reputation: ReputationStore,
        graph: SocialGraph,
        groups: Sequence[FriendGroup],
        rng: random.Random,
        chattiness_of: Callable[[str], float] | None = None,
    ) -> None:
        self.reputation = reputation
        self.graph = graph
        self.groups = list(groups)
        self.rng = rng
        self.chattiness_of = chattiness_of or (lambda _persona_id: 0.5)
        self.propagation_log: list[str] = []

    def record(self, contribution: HumanContribution, agent_id: str) -> ReputationEvent:
        """Score + apply one contribution; maybe gossip if it crossed the threshold."""
        event = ContributionScorer.score(contribution, agent_id)
        before = self.reputation.agent_score(agent_id, contribution.human_name)
        self.reputation.apply_event(event)
        after = self.reputation.agent_score(agent_id, contribution.human_name)
        self._maybe_propagate(contribution.human_name, agent_id, before, after, event.delta)
        return event

    def friendship_score(self, human_name: str, agent_id: str) -> float:
        """The agent's score for the human (delegates to the ReputationStore)."""
        return self.reputation.agent_score(agent_id, human_name)

    def group_score(self, human_name: str, group_id: str) -> float:
        """The group's score for the human (moves only via propagation)."""
        return self.reputation.group_score(group_id, human_name)

    def _maybe_propagate(
        self, human_name: str, agent_id: str, before: float, after: float, delta: float
    ) -> None:
        """Gossip when the score moved across +/-0.2, gated by chattiness."""
        crossed = (
            before < PROPAGATION_THRESHOLD <= after or before > -PROPAGATION_THRESHOLD >= after
        )
        if not crossed:
            return
        chattiness = _clamp(self.chattiness_of(agent_id), 0.0, 1.0)
        if self.rng.random() >= chattiness:
            return
        applied = self.reputation.propagate(
            ReputationEvent(human_name, agent_id, delta, "gossip"), self.graph, self.groups
        )
        for group_id, shift in applied:
            direction = "praised" if shift > 0 else "warned about"
            self.propagation_log.append(
                f"{agent_id} told their friends about {human_name}: "
                f"{direction} {human_name} to {group_id} ({shift:+.2f})"
            )
