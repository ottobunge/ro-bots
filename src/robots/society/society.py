"""Society graph, reputation, and roster (ADR-005)."""

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, final

from robots.society.models import (
    Attitude,
    FriendGroup,
    Playstyle,
    ScheduleFactory,
    SocietyPersona,
)

if TYPE_CHECKING:
    from robots.society.models import Schedule

AFFINITY_MIN = -1.0
AFFINITY_MAX = 1.0
REPUTATION_MIN = -1.0
REPUTATION_MAX = 1.0
PROPAGATION_THRESHOLD = 0.2
PROPAGATION_FACTOR = 0.25

_PLAYSTYLES: tuple[Playstyle, ...] = tuple(Playstyle)
_ATTITUDES: tuple[Attitude, ...] = tuple(Attitude)
_SOLO_ATTITUDE = Attitude.SOLO

_PERSONA_NAMES = (
    "Mika",
    "Doramir",
    "Sable",
    "Fenris",
    "Yuni",
    "Kaede",
    "Bramble",
    "Toma",
    "Elka",
    "Rook",
    "Silvie",
    "Nari",
    "Garrick",
    "Perrin",
    "Ash",
    "Lumi",
    "Odric",
    "Wren",
    "Talia",
    "Bex",
)
_GROUP_ADJECTIVES = (
    "Silver",
    "Grim",
    "Wandering",
    "Azure",
    "Iron",
    "Quiet",
    "Amber",
    "Restless",
)
_GROUP_NOUNS = ("Wolves", "Lanterns", "Blades", "Owls", "Bells", "Foxes", "Pilgrims", "Ash")


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@final
class SocialGraph:
    """Directed agent->agent edges with affinity in [-1, 1]."""

    def __init__(self) -> None:
        self._edges: dict[str, dict[str, float]] = {}

    def seed_group(self, group: FriendGroup, affinity: float = 0.5) -> None:
        """Positive affinity among all members of a group (both directions)."""
        members = group.member_ids
        for a in members:
            for b in members:
                if a != b:
                    self._edges.setdefault(a, {})[b] = affinity

    def affinity(self, a: str, b: str) -> float:
        """Current a->b affinity; 0.0 for strangers."""
        return self._edges.get(a, {}).get(b, 0.0)

    def nudge(self, a: str, b: str, delta: float) -> None:
        """Move a->b affinity by delta, clamped to [-1, 1]."""
        current = self.affinity(a, b)
        self._edges.setdefault(a, {})[b] = _clamp(current + delta, AFFINITY_MIN, AFFINITY_MAX)

    def friends_of(self, a: str) -> tuple[str, ...]:
        """Agents a holds a positive edge toward."""
        return tuple(b for b, v in self._edges.get(a, {}).items() if v > 0.0)


@dataclass(frozen=True, slots=True)
class ReputationEvent:
    """One human did something one agent witnessed; the score moves by delta."""

    human_name: str
    agent_id: str
    delta: float
    reason: str


@final
class ReputationStore:
    """Per-human scores, per agent and per group, in [-1, 1] (default 0.0)."""

    def __init__(self) -> None:
        self._by_agent: dict[str, dict[str, float]] = {}
        self._by_group: dict[str, dict[str, float]] = {}

    def agent_score(self, agent_id: str, human_name: str) -> float:
        return self._by_agent.get(agent_id, {}).get(human_name, 0.0)

    def group_score(self, group_id: str, human_name: str) -> float:
        return self._by_group.get(group_id, {}).get(human_name, 0.0)

    def apply_event(self, event: ReputationEvent) -> None:
        """Move the reporting agent's score for the human, clamped to [-1, 1]."""
        row = self._by_agent.setdefault(event.agent_id, {})
        row[event.human_name] = _clamp(
            row.get(event.human_name, 0.0) + event.delta, REPUTATION_MIN, REPUTATION_MAX
        )

    def propagate(
        self, event: ReputationEvent, graph: SocialGraph, groups: list[FriendGroup]
    ) -> list[tuple[str, float]]:
        """Rumor spreads: friend groups of the reporter shift their group scores.

        Applies only to material events (|delta| >= 0.2); the shift is
        ``PROPAGATION_FACTOR * delta * (0.5 + 0.5 * inter-group affinity)``.
        Returns ``(group_id, applied_delta)`` for observability.
        """
        if abs(event.delta) < PROPAGATION_THRESHOLD:
            return []
        applied: list[tuple[str, float]] = []
        for group in groups:
            if event.agent_id not in group.member_ids:
                continue
            affinity = self._inter_group_affinity(group, event.agent_id, graph, groups)
            shift = PROPAGATION_FACTOR * event.delta * (0.5 + 0.5 * affinity)
            row = self._by_group.setdefault(group.group_id, {})
            row[event.human_name] = _clamp(
                row.get(event.human_name, 0.0) + shift, REPUTATION_MIN, REPUTATION_MAX
            )
            applied.append((group.group_id, shift))
        return applied

    @staticmethod
    def _other_group_members(groups: list[FriendGroup], group_id: str) -> set[str]:
        """Members of every group except the given one."""
        return {m for g in groups if g.group_id != group_id for m in g.member_ids}

    def _inter_group_affinity(
        self,
        group: FriendGroup,
        reporter: str,
        graph: SocialGraph,
        groups: list[FriendGroup],
    ) -> float:
        """Mean positive affinity from the reporter's group-mates toward other groups."""
        mates = [m for m in group.member_ids if m != reporter]
        other_members = self._other_group_members(groups, group.group_id)
        if not mates or not other_members:
            return 0.0
        scores = [v for m in mates for o in other_members if (v := graph.affinity(m, o)) > 0.0]
        return sum(scores) / len(scores) if scores else 0.0


@final
class SocietyRoster:
    """Builds the society: groups (incl. solos), personas, schedules, graph."""

    def __init__(
        self,
        groups: list[FriendGroup],
        personas: dict[str, SocietyPersona],
        graph: SocialGraph,
        reputation: ReputationStore,
    ) -> None:
        self.groups = groups
        self.personas = personas
        self.graph = graph
        self.reputation = reputation

    def online_personas(self, now: tuple[int, float]) -> list[SocietyPersona]:
        """Personas whose group's schedule says they are online right now."""
        by_id = self.personas
        online_ids = {
            member
            for group in self.groups
            if group.schedule.is_online(now)
            for member in group.member_ids
        }
        return [by_id[pid] for pid in sorted(online_ids) if pid in by_id]

    @staticmethod
    def build(rng: random.Random, n_groups: int = 6, group_size_max: int = 6) -> SocietyRoster:
        """Seed a society: mixed group sizes (always at least one solo), graph, reps."""
        groups: list[FriendGroup] = []
        personas: dict[str, SocietyPersona] = {}
        persona_seq = 0
        for g in range(n_groups):
            # Last group is always a solo outsider; sizes 1-6 otherwise.
            size = 1 if g == n_groups - 1 else rng.randint(2, group_size_max)
            attitude = _SOLO_ATTITUDE if size == 1 else rng.choice(_ATTITUDES)
            schedule: Schedule = ScheduleFactory.make_group_schedule(
                rng, overlap_hint=rng.randint(1, 3)
            )
            member_ids: list[str] = []
            for _ in range(size):
                persona_seq += 1
                name = f"{_PERSONA_NAMES[persona_seq % len(_PERSONA_NAMES)]}-{persona_seq:02d}"
                member_ids.append(name)
                personas[name] = SocietyPersona(
                    persona_id=name,
                    name=name,
                    playstyle=rng.choice(_PLAYSTYLES),
                    attitude=attitude,
                    chattiness=rng.random(),
                    level_band=(rng.randint(1, 70), rng.randint(70, 99)),
                )
                persona_seq += 1
            group_label = f"{rng.choice(_GROUP_ADJECTIVES)} {rng.choice(_GROUP_NOUNS)}"
            groups.append(
                FriendGroup(
                    group_id=group_label if size > 1 else f"solo-{member_ids[0]}",
                    member_ids=tuple(member_ids),
                    attitude=attitude,
                    schedule=schedule,
                )
            )
        graph = SocialGraph()
        for group in groups:
            graph.seed_group(group)
        return SocietyRoster(groups, personas, graph, ReputationStore())
