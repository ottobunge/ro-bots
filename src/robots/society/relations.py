"""Relationship ledger (operator criteria 1-2): the popgen-era social wiring.

One agent's view of its social world, one ledger per agent, persisted as JSON
in the agent's memory dir so a reconnect resumes the same relations:

- **agent-agent friendship** (per pair, symmetric): seeded from the popgen
  friend-group affinity (a floor re-affirmed at each ``seed_group``), grown by
  shared party time and chat exchanges, decayed toward neutral with a weekly
  half-life. Same-group members therefore keep acting as friends across
  sessions while one-off bonuses fade.
- **agent-human contribution score**: the human-player friendship score. Damage,
  heals and buffs a human contributed to a party the agent is in move it up;
  dead weight moves it down. (The caller records only witnessed party-mates;
  the ledger owns no world state.)
- **group-level reputation with a gossip hop**: when the agent's group X reports
  a human, every allied group Y (positive cross-group friendship) receives the
  report at a decayed weight — ``GOSSIP_HOP_DECAY * delta * (0.5 + 0.5 *
  affinity)`` — so a bad actor's name travels between friend circles. Material
  reports only (``|delta| >= GOSSIP_THRESHOLD``), deterministically (no
  chattiness RNG here; the ADR-005 :mod:`robots.society.human` layer keeps its
  own stochastic gossip on the legacy roster).

Pure stdlib, no clock, no I/O beyond the explicit ``save`` — ``ts`` values are
caller-supplied floats so week-long simulations stay deterministic offline.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, Final, TypeVar, final

from robots.society.objectives import GroupObjectiveBook, objective_goal

_T = TypeVar("_T")

RELATION_MIN: Final = -1.0
RELATION_MAX: Final = 1.0
GROUP_AFFINITY_SEED: Final = 0.5  # same-group pairs start here (and never fall below while seeded)
FRIEND_AFFINITY: Final = 0.3  # >= this counts as a friend: invites accepted, formations pair
WEEKLY_HALF_LIFE_S: Final = 7 * 24 * 3600.0  # the weekly half-life constant
PARTY_AFFINITY_PER_HOUR: Final = 0.04  # 12.5h of shared party time -> +0.5
CHAT_AFFINITY_DELTA: Final = 0.05
CONTRIBUTION_UP: Final = 0.2  # one witnessed damage/heal/buff contribution
DEAD_WEIGHT_DELTA: Final = -0.1  # one witnessed party window without contribution
CONTRIBUTION_KINDS: Final = ("damage", "heal", "buff")
GOSSIP_THRESHOLD: Final = 0.2  # smaller reports are not worth repeating
GOSSIP_HOP_DECAY: Final = 0.5  # the decayed weight per gossip hop
# The interaction-event layer's feed vocabulary (society/interactions.py owns
# the weights); kept in sync with its POSITIVE_WEIGHTS/NEGATIVE_WEIGHTS keys.
INTERACTION_POSITIVE_KINDS: Final = (
    "party_time",
    "party_session",
    "damage_shared",
    "shared_kill",
    "invite_accept",
    "helpful_chat",
    "heal_received",
    "buff_received",
)
INTERACTION_NEGATIVE_KINDS: Final = (
    "invite_decline",
    "attack_partner",
    "attack_groupmate",
    "rude_chat",
    "party_leave_in_fight",
)
SOCIAL_CONTEXT_MAX_LINES: Final = 12  # the brain's bound on the decide-context block
LEDGER_SCHEMA: Final = 1
_PAIR_SEP: Final = "|"
_CONTEXT_EPS: Final = 1e-9
_FRIEND_LINES_CAP: Final = 12
_HUMAN_LINES_CAP: Final = 4
_HEARD_LINES_CAP: Final = 4
_GROUP_LINE_MEMBERS_CAP: Final = 8

# CLEF-layer premades keyed by party/group event: zero LLM cost to emit one;
# the LLM stays reserved for the open conversation (existing escalation path).
PARTY_EVENT_PREMADES: Final[dict[str, str]] = {
    "party_joined": "Hi all!",
    "party_left": "gg wp",
    "level_up": "Level up! %level",
    "seeking_party": "Looking for party! %job lvl %level",
    "need_buffs": "Buffs please!",
}


def party_event_premade(kind: str) -> str | None:
    """The premade phrase for one party/group event kind; None when none fits."""
    return PARTY_EVENT_PREMADES.get(kind)


def _pair_key(a: str, b: str) -> str:
    """Stable sorted pair key (persona ids contain no separator)."""
    return _PAIR_SEP.join(sorted((a, b)))


def _clamp(value: float, lo: float = RELATION_MIN, hi: float = RELATION_MAX) -> float:
    return max(lo, min(hi, value))


@final
@dataclass(frozen=True, slots=True)
class PartyPlan:
    """One schedule-overlap formation step: the leader invites its friends."""

    leader_id: str
    invitee_ids: tuple[str, ...]


@final
class RelationshipLedger:
    """One agent's relationship scores over peers, humans, and groups."""

    def __init__(self, persona_id: str = "", *, path: Path | None = None) -> None:
        self._persona_id = persona_id
        self._path = path
        self._names: dict[str, str] = {}
        self._persona_by_name: dict[str, str] = {}
        self._groups: dict[str, tuple[str, ...]] = {}
        self._group_maps: dict[str, str] = {}
        self._member_group: dict[str, str] = {}
        self._friendship: dict[str, float] = {}
        self._party_seconds: dict[str, float] = {}
        self._chat_exchanges: dict[str, int] = {}
        self._human_scores: dict[str, float] = {}
        self._group_reputation: dict[str, dict[str, float]] = {}
        self._objectives = GroupObjectiveBook()
        self._last_decay_ts: float | None = None
        if path is not None and path.exists():
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                msg = f"ledger file is not a JSON object: {path}"
                raise ValueError(msg)
            restored = RelationshipLedger.from_dict(data)
            self._restore_from(restored)

    # -- reading -------------------------------------------------------------

    def friendship(self, a: str, b: str) -> float:
        """The agent's friendship score for the a-b pair (0.0 for strangers)."""
        return self._friendship.get(_pair_key(a, b), 0.0)

    def human_score(self, human_name: str) -> float:
        """The agent's contribution score for one human player."""
        return self._human_scores.get(human_name, 0.0)

    def group_reputation(self, group_id: str, human_name: str) -> float:
        """The score one group (own or heard through gossip) holds for a human."""
        return self._group_reputation.get(group_id, {}).get(human_name, 0.0)

    def group_of(self, member_id: str) -> str | None:
        """The member's popgen group id; None for solo outsiders."""
        return self._member_group.get(member_id)

    def group_members(self, group_id: str) -> tuple[str, ...]:
        """The registered member ids, in registration (popgen) order."""
        return self._groups.get(group_id, ())

    def group_map(self, group_id: str) -> str | None:
        """The group's save map, when registered with one."""
        return self._group_maps.get(group_id)

    def display_name(self, persona_id: str) -> str:
        """The persona's in-game character name (injected roster knowledge)."""
        return self._names.get(persona_id, persona_id)

    def persona_of(self, display_name: str) -> str | None:
        """The persona id behind an in-game character name (recognizing the inviter)."""
        return self._persona_by_name.get(display_name)

    @property
    def objectives(self) -> GroupObjectiveBook:
        """This agent's group-objective book (persisted with the ledger JSON)."""
        return self._objectives

    # -- registration ----------------------------------------------------------

    def register_persona(self, persona_id: str, display_name: str) -> None:
        """Bind a persona id to its in-game char name (for context lines)."""
        self._names[persona_id] = display_name
        self._persona_by_name[display_name] = persona_id

    def seed_group(
        self, group_id: str, members: Sequence[str], *, save_map: str | None = None
    ) -> None:
        """Register a popgen friend group and re-affirm the friend floor.

        Idempotent per session start: every same-group pair's score rises to at
        least ``GROUP_AFFINITY_SEED`` (party/chat bonuses above the floor keep
        decaying with the weekly half-life).
        """
        member_ids = tuple(members)
        self._groups[group_id] = member_ids
        for member in member_ids:
            self._member_group[member] = group_id
        if save_map is not None:
            self._group_maps[group_id] = save_map
        for a, b in combinations(member_ids, 2):
            key = _pair_key(a, b)
            self._friendship[key] = max(self._friendship.get(key, 0.0), GROUP_AFFINITY_SEED)

    # -- event recording -------------------------------------------------------

    def record_party_time(
        self, member_ids: Sequence[str], seconds: float, *, ts: float | None = None
    ) -> None:
        """Shared party time among the listed members grows every pair's bond."""
        self._advance(ts)
        for a, b in combinations(sorted(member_ids), 2):
            key = _pair_key(a, b)
            self._party_seconds[key] = self._party_seconds.get(key, 0.0) + seconds
            bonus = seconds / 3600.0 * PARTY_AFFINITY_PER_HOUR
            self._friendship[key] = _clamp(self._friendship.get(key, 0.0) + bonus)

    def record_chat_exchange(self, a: str, b: str, *, ts: float | None = None) -> None:
        """One chat exchange between the two agents nudges their bond."""
        self._advance(ts)
        key = _pair_key(a, b)
        self._chat_exchanges[key] = self._chat_exchanges.get(key, 0) + 1
        self._friendship[key] = _clamp(self._friendship.get(key, 0.0) + CHAT_AFFINITY_DELTA)

    def record_contribution(self, human_name: str, kind: str, *, ts: float | None = None) -> None:
        """A human's witnessed party contribution: +useful play, -dead weight."""
        if kind == "dead_weight":
            delta = DEAD_WEIGHT_DELTA
        elif kind in CONTRIBUTION_KINDS:
            delta = CONTRIBUTION_UP
        else:
            msg = f"unknown contribution kind: {kind!r}"
            raise ValueError(msg)
        self._advance(ts)
        self._human_scores[human_name] = _clamp(self._human_scores.get(human_name, 0.0) + delta)

    def ingest_interaction(
        self, a: str, b: str, kind: str, *, seconds: float = 0.0, ts: float | None = None
    ) -> None:
        """THE narrow interaction-event seam: one observed event feeds friendship.

        The interaction layer (:mod:`robots.society.interactions`) owns the
        bounded asymmetric per-pair standing, the group aggregates, the gossip
        and the rivalries; this method only FEEDS the existing friendship
        score with the same recorders the direct events use — party time via
        its per-hour rate, every other positive kind via the chat-exchange
        bump, negative kinds reduced by that same bounded bump (an attacker is
        not a friend; party_formation and the affinity gates see that).
        """
        self._advance(ts)
        if kind == "party_time":
            self.record_party_time([a, b], seconds, ts=ts)
            return
        if kind in INTERACTION_POSITIVE_KINDS:
            self.record_chat_exchange(a, b, ts=ts)
            return
        if kind in INTERACTION_NEGATIVE_KINDS:
            key = _pair_key(a, b)
            self._friendship[key] = _clamp(self._friendship.get(key, 0.0) - CHAT_AFFINITY_DELTA)
            return
        msg = f"unknown interaction kind: {kind!r}"
        raise ValueError(msg)

    def report_human(
        self, human_name: str, delta: float, *, group_id: str, ts: float | None = None
    ) -> list[tuple[str, float]]:
        """The agent's group reports a human; allied groups hear it at decayed weight.

        Applies ``delta`` to the agent's own score and its group's row, then
        propagates the gossip hop. Returns ``(group_id, shift)`` per allied
        group for observability.
        """
        self._advance(ts)
        self._human_scores[human_name] = _clamp(self._human_scores.get(human_name, 0.0) + delta)
        row = self._group_reputation.setdefault(group_id, {})
        row[human_name] = _clamp(row.get(human_name, 0.0) + delta)
        return self._gossip(human_name, delta, group_id)

    def _gossip(self, human_name: str, delta: float, group_id: str) -> list[tuple[str, float]]:
        if abs(delta) < GOSSIP_THRESHOLD:
            return []
        applied: list[tuple[str, float]] = []
        for other in sorted(self._groups):
            if other == group_id:
                continue
            affinity = self._cross_affinity(group_id, other)
            if affinity <= 0.0:
                continue
            shift = delta * GOSSIP_HOP_DECAY * (0.5 + 0.5 * min(affinity, 1.0))
            row = self._group_reputation.setdefault(other, {})
            row[human_name] = _clamp(row.get(human_name, 0.0) + shift)
            applied.append((other, shift))
        return applied

    def _cross_affinity(self, group_a: str, group_b: str) -> float:
        """Mean positive friendship between two groups' members (0 when none)."""
        values = [
            value
            for a in self._groups.get(group_a, ())
            for b in self._groups.get(group_b, ())
            if (value := self._friendship.get(_pair_key(a, b), 0.0)) > 0.0
        ]
        return sum(values) / len(values) if values else 0.0

    # -- decay -----------------------------------------------------------------

    def decay(self, now_ts: float) -> None:
        """Decay every score toward neutral per the elapsed weekly half-lives."""
        self._advance(now_ts)

    def _advance(self, now_ts: float | None) -> None:
        """Half-life decay up to ``now_ts``; the first timestamp only sets base."""
        if now_ts is None:
            return
        if self._last_decay_ts is None:
            self._last_decay_ts = now_ts
            return
        elapsed = now_ts - self._last_decay_ts
        if elapsed <= 0:
            return
        factor = 0.5 ** (elapsed / WEEKLY_HALF_LIFE_S)
        self._friendship = {key: value * factor for key, value in self._friendship.items()}
        self._human_scores = {key: value * factor for key, value in self._human_scores.items()}
        self._group_reputation = {
            group: {human: value * factor for human, value in row.items()}
            for group, row in self._group_reputation.items()
        }
        self._last_decay_ts = now_ts

    # -- party formation ---------------------------------------------------------

    def party_formation(
        self, online_members: Sequence[str], *, threshold: float = FRIEND_AFFINITY
    ) -> list[PartyPlan]:
        """Leader-invites plan for the online members whose schedules overlap.

        Per registered group with 2+ online members: the first registered
        member leads and invites the co-present friends (affinity at or above
        the threshold). Cross-group strangers and solos are never paired.
        """
        online = set(online_members)
        plans: list[PartyPlan] = []
        for group_id in sorted(self._groups):
            present = [m for m in self._groups[group_id] if m in online]
            if len(present) < 2:
                continue
            leader = present[0]
            invitee_ids = tuple(m for m in present[1:] if self.friendship(leader, m) >= threshold)
            if invitee_ids:
                plans.append(PartyPlan(leader_id=leader, invitee_ids=invitee_ids))
        return plans

    # -- decide context ---------------------------------------------------------

    def context_lines(
        self,
        viewer_id: str,
        *,
        active_group_ids: Sequence[str] = (),
        online_members: Sequence[str] = (),
        max_lines: int = SOCIAL_CONTEXT_MAX_LINES,
    ) -> list[str]:
        """Bounded decide-context lines: objectives, bonds, humans, gossip, drift.

        Objective lines come first (most actionable): the leader's formation
        suggestion when the group's schedule-overlap window opens, a member's
        invited/active lines. Solo outsiders get drift hints naming the
        currently active groups (a goal hint for the plan/context — never a
        teleport). Group members get their own group's bonds so
        accept_invite/premade_pick can prefer friends and high-affinity groups.
        """
        own_group = self._member_group.get(viewer_id)
        lines: list[str] = []
        lines.extend(self._objective_lines(viewer_id, online_members))
        if own_group is not None:
            lines.append(self._group_line(viewer_id, own_group))
        lines.extend(self._friend_lines(viewer_id, own_group))
        lines.extend(self._human_lines())
        lines.extend(self._heard_lines())
        if own_group is None:
            lines.extend(self._drift_lines(active_group_ids))
        return lines[:max_lines]

    def _objective_lines(self, viewer_id: str, online_members: Sequence[str]) -> list[str]:
        """The group-objective facts: invited/active offers, the leader's window."""
        lines: list[str] = []
        live = self._objectives.live_objectives()
        for objective in live:
            if objective.leader_id == viewer_id:
                lines.append(self._leader_objective_line(objective))
            elif viewer_id in objective.invited and viewer_id not in objective.accepted:
                lines.append(self._member_invited_line(objective))
            elif viewer_id in objective.accepted:
                lines.append(self._member_active_line(objective))
        if any(obj.group_id == self._member_group.get(viewer_id) for obj in live):
            return lines
        lines.extend(self._formation_line(viewer_id, online_members))
        return lines

    def _leader_objective_line(self, objective: Any) -> str:
        subject = self._objective_subject(objective)
        return (
            f"your objective: {subject} ({len(objective.invited)} invited, "
            f"{len(objective.accepted)} joined)"
        )

    def _member_invited_line(self, objective: Any) -> str:
        subject = self._objective_subject(objective)
        leader = self.display_name(objective.leader_id)
        return f"invited: {subject} by {leader} - accept the party invite"

    def _member_active_line(self, objective: Any) -> str:
        subject = self._objective_subject(objective)
        goal = objective_goal(objective.kind)
        return (
            f"active objective: {subject} with {objective.group_id} "
            f"({len(objective.accepted)} joined) - your goal aligns ({goal.value})"
        )

    @staticmethod
    def _objective_subject(objective: Any) -> str:
        subject = objective.kind
        if objective.target:
            subject = f"{subject} {objective.target}"
        return f"{subject} on {objective.map_name}"

    def _formation_line(self, viewer_id: str, online_members: Sequence[str]) -> list[str]:
        """The leader's open schedule-overlap window (party_formation speaks)."""
        if not online_members:
            return []
        own_group = self._member_group.get(viewer_id)
        if own_group is None:
            return []
        members = self._groups.get(own_group, ())
        online = set(online_members) & set(members)
        if len(online) < 2:
            return []
        for plan in self.party_formation(online_members):
            if plan.leader_id != viewer_id:
                continue
            names = ", ".join(self.display_name(m) for m in plan.invitee_ids)
            return [
                (
                    f"your group {own_group} is online ({len(online)}/{len(members)}); "
                    f"you lead; party_formation suggests inviting {names}"
                )
            ]
        return []

    def _display(self, persona_id: str) -> str:
        return self._names.get(persona_id, persona_id)

    def _group_line(self, viewer_id: str, group_id: str) -> str:
        members = self._groups.get(group_id, ())
        shown = [
            f"{self._display(m)} {self.friendship(viewer_id, m):+.2f}"
            for m in members[:_GROUP_LINE_MEMBERS_CAP]
        ]
        return f"your group {group_id}: members " + ", ".join(shown)

    def _friend_lines(self, viewer_id: str, own_group: str | None) -> list[str]:
        """The viewer's direct bonds, strongest first; group mates live in the group line."""
        bonded: list[tuple[float, str, float]] = []
        for key, value in self._friendship.items():
            a, b = key.split(_PAIR_SEP)
            if viewer_id not in (a, b) or abs(value) <= _CONTEXT_EPS:
                continue
            peer = b if a == viewer_id else a
            if own_group is not None and self._member_group.get(peer) == own_group:
                continue
            bonded.append((-abs(value), self._display(peer), value))
        bonded.sort()
        return [f"friend {name} {value:+.2f}" for _, name, value in bonded[:_FRIEND_LINES_CAP]]

    def _human_lines(self) -> list[str]:
        known = [
            (name, value) for name, value in self._human_scores.items() if abs(value) > _CONTEXT_EPS
        ]
        known.sort(key=lambda item: (-abs(item[1]), item[0]))
        return [f"human {name} {value:+.2f}" for name, value in known[:_HUMAN_LINES_CAP]]

    def _heard_lines(self) -> list[str]:
        lines: list[str] = []
        for group_id in sorted(self._group_reputation):
            row = self._group_reputation[group_id]
            humans = [(name, value) for name, value in row.items() if abs(value) > _CONTEXT_EPS]
            humans.sort(key=lambda item: (-abs(item[1]), item[0]))
            for name, value in humans[:_HEARD_LINES_CAP]:
                lines.append(f"heard via {group_id}: {name} {value:+.2f}")
        return lines[:_HEARD_LINES_CAP]

    def _drift_lines(self, active_group_ids: Sequence[str]) -> list[str]:
        lines: list[str] = []
        for group_id in sorted(set(active_group_ids)):
            members = self._groups.get(group_id)
            if not members:
                continue
            map_name = self._group_maps.get(group_id, "unknown")
            lines.append(
                f"group {group_id} active near {map_name} "
                f"({len(members)} members) - consider drifting there"
            )
        return lines

    # -- persistence -------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """The full ledger state as a JSON-ready dict."""
        return {
            "schema": LEDGER_SCHEMA,
            "persona_id": self._persona_id,
            "last_decay_ts": self._last_decay_ts,
            "names": dict(self._names),
            "groups": {
                group_id: {"members": list(members), "map": self._group_maps.get(group_id)}
                for group_id, members in self._groups.items()
            },
            "friendship": dict(self._friendship),
            "party_seconds": dict(self._party_seconds),
            "chat_exchanges": dict(self._chat_exchanges),
            "human_scores": dict(self._human_scores),
            "group_reputation": {gid: dict(row) for gid, row in self._group_reputation.items()},
            "objectives": self._objectives.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RelationshipLedger:
        """Restore a ledger; unknown schemas and malformed pair keys fail closed."""
        if data.get("schema") != LEDGER_SCHEMA:
            msg = f"unsupported ledger schema: {data.get('schema')!r}"
            raise ValueError(msg)
        ledger = cls(persona_id=str(data.get("persona_id", "")))
        last_decay = data.get("last_decay_ts")
        ledger._last_decay_ts = float(last_decay) if last_decay is not None else None
        ledger._names = {str(k): str(v) for k, v in dict(data.get("names", {})).items()}
        ledger._restore_groups(dict(data.get("groups", {})))
        ledger._friendship = cls._pair_section(data, "friendship", float)
        ledger._party_seconds = cls._pair_section(data, "party_seconds", float)
        ledger._chat_exchanges = cls._pair_section(data, "chat_exchanges", int)
        ledger._human_scores = {
            str(k): float(v) for k, v in dict(data.get("human_scores", {})).items()
        }
        ledger._group_reputation = cls._reputation_section(data)
        ledger._objectives = GroupObjectiveBook.from_dict(dict(data.get("objectives", {})))
        return ledger

    @classmethod
    def _pair_section(
        cls, data: Mapping[str, Any], key: str, cast: Callable[[Any], _T]
    ) -> dict[str, _T]:
        """Restore one pair-keyed section, validating every key."""
        return {cls._valid_pair(str(k)): cast(v) for k, v in dict(data.get(key, {})).items()}

    @classmethod
    def _reputation_section(cls, data: Mapping[str, Any]) -> dict[str, dict[str, float]]:
        return {
            str(gid): {str(h): float(v) for h, v in row.items()}
            for gid, row in dict(data.get("group_reputation", {})).items()
        }

    def _restore_groups(self, groups: Mapping[str, Any]) -> None:
        for group_id, row in groups.items():
            members = tuple(str(m) for m in row.get("members", []))
            self._groups[str(group_id)] = members
            for member in members:
                self._member_group[member] = str(group_id)
            map_name = row.get("map")
            if map_name is not None:
                self._group_maps[str(group_id)] = str(map_name)

    @staticmethod
    def _valid_pair(key: str) -> str:
        parts = key.split(_PAIR_SEP)
        if len(parts) != 2 or not all(parts):
            msg = f"malformed pair key: {key!r}"
            raise ValueError(msg)
        return _pair_key(parts[0], parts[1])

    def save(self, path: Path | None = None) -> None:
        """Atomically write the ledger JSON (reconnection continuity)."""
        target = path if path is not None else self._path
        if target is None:
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(json.dumps(self.to_dict(), sort_keys=True) + "\n")
        os.replace(tmp, target)

    def _restore_from(self, other: RelationshipLedger) -> None:
        self._persona_id = other._persona_id
        self._names = other._names
        self._persona_by_name = {name: pid for pid, name in other._names.items()}
        self._groups = other._groups
        self._group_maps = other._group_maps
        self._member_group = other._member_group
        self._friendship = other._friendship
        self._party_seconds = other._party_seconds
        self._chat_exchanges = other._chat_exchanges
        self._human_scores = other._human_scores
        self._group_reputation = other._group_reputation
        self._objectives = other._objectives
        self._last_decay_ts = other._last_decay_ts
