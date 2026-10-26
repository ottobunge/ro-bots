"""Agent-to-agent interaction ledger: the observed-interaction event layer.

Every agent already holds a :class:`~robots.society.relations.RelationshipLedger`
(friendship, human contribution, gossip, weekly half-life). This module adds the
event layer UNDER it: OBSERVED in-game interactions between two roster-known
agents move a bounded per-pair standing, which aggregates into the group-level
attitude, feeds the decide context as bounded lines, propagates between allied
groups on the review cadence, and selects RIVALRIES for the WoE arc.

Knowledge model (binding, same split as relations.py):

- ROSTER is INJECTED meta-knowledge: ``register_persona``/``seed_group`` mirror
  ``seed_roster`` — an event is ingested ONLY when both names resolve through
  the roster; everything else must have been observed in-game.
- EVENTS are OBSERVED in-game facts that the CALLER resolved from the wire
  (party membership, the 0x08C8 damage rows, invite results, chat premades);
  this ledger never mutates another agent and its emissions are in-game
  channel actions only (Say/PartyChat/WhisperTo — the anti-telepathy rule).

Score model (documented):

- Per (agent, agent) pair a bounded standing in ``[SCORE_MIN, SCORE_MAX]``.
- Asymmetry: negative events weigh ``NEGATIVE_RATIO`` (3.0) x their base
  weight while positives add their base weight — one ``attack_partner``
  (-30) erases six ``invite_accept`` (+5 each). The fixed ratio is the
  player-psychology prior: betrayals cost more than favors earn.
- Unit-scaled kinds: ``party_time`` per ``PARTY_TIME_UNIT_S`` of shared party
  membership, ``damage_shared`` per ``DAMAGE_SHARED_UNIT`` of bot-dealt damage
  while co-partied.
- Decay: the same weekly half-life as the relationship ledger
  (``WEEKLY_HALF_LIFE_S``), applied lazily from caller timestamps.
- Aggregation: per (group, agent) and (group, group) means over the member
  pair standings (missing pairs count as the neutral 0.0 — a group you never
  met is not a friend or an enemy).
- Gossip: on the review cadence each group-pair attitude at or above
  ``GOSSIP_STANDING_THRESHOLD`` propagates to the allied groups (positive
  cross-group evidence) at ``GOSSIP_HOP_DECAY`` (rival pairs at
  ``RIVAL_GOSSIP_MULTIPLIER``); when the standing crosses
  ``GOSSIP_REPORT_THRESHOLD`` the report itself becomes an IN-GAME chat premade.

Event kinds and observability (wire truth at the pinned e985 MAIN 20180704):

- party_time / party_session: the party roster (ZC_GROUP_LIST 0x0AE5 family)
  and membership time — wire-observable (producer: the host's party state).
- damage_shared: the bot-dealt damage rows (ZC_NOTIFY_ACT 0x08C8) with a
  co-party source — wire-observable.
- shared_kill: shared XP while co-partied — wire-observable.
- invite_accept / invite_decline: the invite result (CZ_PARTY_JOIN_REQ_ACK
  0x2c7 path, observed by the inviter) — wire-observable.
- helpful_chat / rude_chat: heard chat classified through the premade
  categories — wire-observable (the brain's ChatHeard seam ingests live).
- attack_partner / attack_groupmate / party_leave_in_fight: the damage rows
  and the party-roster leave diff — wire-observable.
- heal_received / buff_received: the skill-use frames EXIST in the pinned
  packet table (ZC_USE_SKILL 0x0114 31B / ZC_USE_SKILL2 0x0115 35B) but the
  clientless client parses no skill-use rows yet — the kind is implemented
  here; the wire producer lands with a skill-use parser (packetdb is a
  byte-pinned read-only artifact).
- loot_steal: NOT observable — the wire reports only the observer's own
  pickups; another player's pickup is not a distinct event (ZC_NOTIFY_VANISH
  0x0080 on a floor item is ambiguous: timeout or pickup), so the kind is
  deferred, not faked.
"""

from __future__ import annotations

import json
import os
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, final

from robots.domain.actions import GameAction, PartyChat, Say
from robots.society.objectives import parse_objective_premade
from robots.society.relations import GOSSIP_HOP_DECAY, WEEKLY_HALF_LIFE_S

if TYPE_CHECKING:
    from robots.popgen import GeneratedPopulation

INTERACTION_SCHEMA: Final = 1
SCORE_MIN: Final = -100.0
SCORE_MAX: Final = 100.0
NEGATIVE_RATIO: Final = 3.0  # the fixed asymmetry: negatives weigh 3x positives

# Positive event base weights (unit-scaled kinds scale per unit below).
POSITIVE_WEIGHTS: Final[dict[str, float]] = {
    "party_time": 1.0,
    "party_session": 2.0,
    "damage_shared": 1.0,
    "shared_kill": 3.0,
    "invite_accept": 5.0,
    "helpful_chat": 2.0,
    "heal_received": 2.0,
    "buff_received": 2.0,
}
# Negative event base weights; the applied delta is -weight * NEGATIVE_RATIO.
NEGATIVE_WEIGHTS: Final[dict[str, float]] = {
    "invite_decline": 5.0,
    "attack_partner": 10.0,
    "attack_groupmate": 6.0,
    "rude_chat": 4.0,
    "party_leave_in_fight": 5.0,
}
PARTY_TIME_UNIT_S: Final = 1800.0  # one positive point per 30 min shared party
DAMAGE_SHARED_UNIT: Final = 250  # one positive point per 250 shared damage

# Helpful chat: the LFP / goal-announce premade categories (case-insensitive
# prefixes); the objective join calls parse through the canonical premade parser.
HELPFUL_CHAT_PREFIXES: Final = ("looking for party", "inviting ")
# Rude chat: the negative premade category (the player-rudeness counterpart of
# the sanitize categories; a strict prefix match, lowercase).
RUDE_CHAT_PREMADES: Final = ("noob", "learn to play", "ks much")

GOSSIP_STANDING_THRESHOLD: Final = 10.0  # material group attitude (standing units)
GOSSIP_REPORT_THRESHOLD: Final = 30.0  # the report itself becomes a chat premade
RIVAL_GOSSIP_MULTIPLIER: Final = 2.0  # rival pairs' gossip flows doubled
RIVALRY_FORMATION_STANDING: Final = -15.0  # friend groups: noise (0.0) never rivals
RIVALRY_EMISSION_MIN_S: Final = 900.0  # the taunt/report cadence gate
INTERACTION_CONTEXT_MAX_LINES: Final = 4  # bounded decide block (partners + rival)
CONTEXT_EPS: Final = 1e-9
_PAIR_SEP: Final = "|"


def _pair_key(a: str, b: str) -> str:
    """Stable sorted pair key (persona/group/guild ids contain no separator)."""
    return _PAIR_SEP.join(sorted((a, b)))


def _clamp(value: float, lo: float = SCORE_MIN, hi: float = SCORE_MAX) -> float:
    return max(lo, min(hi, value))


def classify_chat(text: str) -> str | None:
    """The chat premade category of one heard line; None when everyday chat.

    Helpful: the goal-announce join calls (the canonical premade protocol) and
    the LFP categories. Rude: the ``RUDE_CHAT_PREMADES`` category. Both match
    case-insensitively on the stripped line.
    """
    stripped = text.strip()
    low = stripped.lower()
    if any(low.startswith(rude) for rude in RUDE_CHAT_PREMADES):
        return "rude_chat"
    if parse_objective_premade(stripped) is not None:
        return "helpful_chat"
    if any(low.startswith(prefix) for prefix in HELPFUL_CHAT_PREFIXES):
        return "helpful_chat"
    return None


def _event_delta(kind: str, seconds: float, amount: int) -> float:
    """The documented signed delta of one event (unknown kinds raise)."""
    if kind in POSITIVE_WEIGHTS:
        weight = POSITIVE_WEIGHTS[kind]
        if kind == "party_time":
            return seconds / PARTY_TIME_UNIT_S * weight
        if kind == "damage_shared":
            return amount / DAMAGE_SHARED_UNIT * weight
        return weight
    if kind in NEGATIVE_WEIGHTS:
        return -NEGATIVE_WEIGHTS[kind] * NEGATIVE_RATIO
    msg = f"unknown interaction kind: {kind!r}"
    raise ValueError(msg)


@final
@dataclass(frozen=True, slots=True)
class Rivalry:
    """One recorded (group-or-guild, group-or-guild) rivalry."""

    subject_id: str
    rival_id: str
    since_ts: float
    origin_score: float  # the aggregate standing at formation time
    seed: int  # the tie-break rng seed actually used (0 = no tie to break)


@final
@dataclass(slots=True)
class _Pair:
    """One observed pair's standing and its evidence counters."""

    score: float = 0.0
    positives: int = 0
    negatives: int = 0
    party_seconds: float = 0.0
    party_sessions: int = 0
    shared_damage: int = 0


@final
class InteractionLedger:
    """One agent's observed agent-to-agent interaction standings.

    Per-agent state (like the RelationshipLedger): the events this agent
    witnessed in-game between roster-known agents. Pure stdlib, no clock, no
    I/O beyond the explicit ``save``; ``ts`` values are caller-supplied floats.
    """

    def __init__(
        self, persona_id: str = "", *, path: Path | None = None, rng: random.Random | None = None
    ) -> None:
        self._persona_id = persona_id
        self._path = path
        self._rng = rng if rng is not None else random.Random(0)
        self._names: dict[str, str] = {}
        self._persona_by_name: dict[str, str] = {}
        self._groups: dict[str, tuple[str, ...]] = {}
        self._member_group: dict[str, str] = {}
        self._guild_members: dict[str, tuple[str, ...]] = {}
        self._pairs: dict[str, _Pair] = {}
        self._heard: dict[tuple[str, str], float] = {}
        self._rivalries: dict[str, Rivalry] = {}
        self._last_decay_ts: float | None = None
        self._last_emission_ts: float | None = None
        if path is not None and path.exists():
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                msg = f"interaction ledger file is not a JSON object: {path}"
                raise ValueError(msg)
            self._restore(InteractionLedger.from_dict(data))

    # -- roster (the injected identity knowledge) ----------------------------

    def register_persona(self, persona_id: str, display_name: str) -> None:
        """Bind a persona id to its in-game char name (for context lines)."""
        self._names.update({persona_id: display_name})
        self._persona_by_name[display_name] = persona_id

    def seed_group(self, group_id: str, members: Sequence[str]) -> None:
        """Register a popgen friend group's members (idempotent)."""
        self._groups[group_id] = tuple(members)
        for member in self._groups[group_id]:
            self._member_group[member] = group_id

    def _resolve(self, name_or_id: str) -> str | None:
        """The persona id behind a roster entry (id or display name)."""
        if name_or_id == self._persona_id or name_or_id in self._names:
            return name_or_id
        return self._persona_by_name.get(name_or_id)

    def _display(self, persona_id: str) -> str:
        return self._names.get(persona_id, persona_id)

    # -- ingestion (THE entry point for the wire producers) -------------------

    def ingest(
        self,
        a: str,
        b: str,
        kind: str,
        *,
        seconds: float = 0.0,
        amount: int = 0,
        ts: float | None = None,
    ) -> bool:
        """One OBSERVED interaction between two roster-known agents.

        Resolves both names through the injected roster; unknown agents (and
        self-events) are not ingested — returns False and changes nothing.
        """
        pid_a = self._resolve(a)
        pid_b = self._resolve(b)
        if pid_a is None or pid_b is None or pid_a == pid_b:
            return False
        self._advance(ts)
        pair = self._pairs.setdefault(_pair_key(pid_a, pid_b), _Pair())
        delta = _event_delta(kind, seconds, amount)
        pair.score = _clamp(pair.score + delta)
        if delta >= 0:
            pair.positives += 1
        else:
            pair.negatives += 1
        if kind == "party_time":
            pair.party_seconds += seconds
        elif kind == "party_session":
            pair.party_sessions += 1
        elif kind == "damage_shared":
            pair.shared_damage += amount
        return True

    def ingest_chat(self, sender_name: str, text: str, *, ts: float | None = None) -> bool:
        """One heard chat line classified through the premade categories."""
        kind = classify_chat(text)
        if kind is None:
            return False
        return self.ingest(self._persona_id, sender_name, kind, ts=ts)

    # -- reading ---------------------------------------------------------------

    def standing(self, a: str, b: str) -> float:
        """The pair's bounded standing (0.0 when nothing was observed)."""
        pid_a = self._resolve(a)
        pid_b = self._resolve(b)
        if pid_a is None or pid_b is None:
            return 0.0
        return self._pairs.get(_pair_key(pid_a, pid_b), _Pair()).score

    def group_agent_standing(self, group_id: str, agent_id: str) -> float:
        """The group's aggregate standing toward one agent (mean, neutral 0)."""
        members = self._groups.get(group_id, ())
        if not members:
            return 0.0
        return sum(self.standing(m, agent_id) for m in members) / len(members)

    def group_group_standing(self, group_a: str, group_b: str) -> float:
        """The group-level attitude: the mean over all cross member pairs."""
        members_a = self._groups.get(group_a, ())
        members_b = self._groups.get(group_b, ())
        if not members_a or not members_b:
            return 0.0
        total = sum(self.standing(a, b) for a in members_a for b in members_b)
        return total / (len(members_a) * len(members_b))

    def heard_standing(self, hearing_group: str, subject_group: str) -> float:
        """The attitude another group relayed to ``hearing_group`` via gossip."""
        return self._heard.get((hearing_group, subject_group), 0.0)

    # -- decide context ---------------------------------------------------------

    def decide_lines(
        self, viewer_id: str, *, max_lines: int = INTERACTION_CONTEXT_MAX_LINES
    ) -> list[str]:
        """Bounded decide lines: the partners' standing, then the rival line."""
        pid = self._resolve(viewer_id)
        if pid is None:
            return []
        return (self._partner_lines(pid) + self._rival_lines(pid))[:max_lines]

    def _partner_lines(self, viewer_id: str) -> list[str]:
        rows: list[tuple[float, str, _Pair]] = []
        for key, pair in self._pairs.items():
            a, b = key.split(_PAIR_SEP)
            if viewer_id not in (a, b) or abs(pair.score) <= CONTEXT_EPS:
                continue
            peer = b if a == viewer_id else a
            rows.append((-abs(pair.score), self._display(peer), pair))
        rows.sort()
        lines: list[str] = []
        for _, name, pair in rows:
            evidence = f"party {pair.party_sessions} sessions, {pair.shared_damage} shared dmg"
            if pair.negatives:
                plural = "" if pair.negatives == 1 else "s"
                tail = f"{pair.negatives} negative{plural}"
            else:
                tail = "no negatives"
            lines.append(f"{name}: {pair.score:+.0f} ({evidence}; {tail})")
        return lines

    def _rival_lines(self, viewer_id: str) -> list[str]:
        lines: list[str] = []
        own_group = self._member_group.get(viewer_id)
        subjects = {own_group} if own_group is not None else set()
        subjects.update(g for g, members in self._guild_members.items() if viewer_id in members)
        for subject in sorted(subjects):
            rival = self.rival_of(subject)
            if rival is None:
                continue
            worst = self._worst_cross_standing(subject, rival)
            lines.append(f"Rival: {rival} (worst standing {worst:+.0f})")
        return lines

    def _worst_cross_standing(self, side_a: str, side_b: str) -> float:
        """The most negative evidenced pair standing between two sides."""
        scores = [
            pair.score
            for key, pair in self._pairs.items()
            if self._key_between(key, side_a, side_b)
        ]
        return min(scores) if scores else 0.0

    def _key_between(self, key: str, side_a: str, side_b: str) -> bool:
        a, b = key.split(_PAIR_SEP)
        return (a in self._side_members(side_a) and b in self._side_members(side_b)) or (
            a in self._side_members(side_b) and b in self._side_members(side_a)
        )

    def _side_members(self, group_or_guild: str) -> set[str]:
        return set(self._groups.get(group_or_guild, self._guild_members.get(group_or_guild, ())))

    # -- gossip (the review cadence) ---------------------------------------------

    def propagate_gossip(self, *, ts: float | None = None) -> list[tuple[str, str, float]]:
        """Propagate material group attitudes to allied groups at the hop decay.

        For every group pair whose aggregate attitude crosses
        ``GOSSIP_STANDING_THRESHOLD``, each side's allied groups (positive
        cross-group evidence) receive the relayed attitude at
        ``GOSSIP_HOP_DECAY * attitude * (0.5 + 0.5 * affinity)``; rival pairs
        flow at ``RIVAL_GOSSIP_MULTIPLIER``. Returns ``(hearing, subject,
        shift)`` per hop.
        """
        self._advance(ts)
        hops: list[tuple[str, str, float]] = []
        for ga, gb in sorted(combinations(sorted(self._groups), 2)):
            attitude = self.group_group_standing(ga, gb)
            if abs(attitude) < GOSSIP_STANDING_THRESHOLD:
                continue
            multiplier = RIVAL_GOSSIP_MULTIPLIER if self._is_rivalry(ga, gb) else 1.0
            for side, subject in ((ga, gb), (gb, ga)):
                for other in sorted(self._groups):
                    if other in (ga, gb):
                        continue
                    affinity = self._cross_affinity(side, other)
                    if affinity <= 0.0:
                        continue
                    shift = (
                        attitude * GOSSIP_HOP_DECAY * (0.5 + 0.5 * min(affinity, 1.0)) * multiplier
                    )
                    key = (other, subject)
                    self._heard[key] = _clamp(self._heard.get(key, 0.0) + shift)
                    hops.append((other, subject, shift))
        return hops

    def _cross_affinity(self, group_a: str, group_b: str) -> float:
        """Mean POSITIVE pair standing between two groups' members (0 when none)."""
        values = [
            value
            for a in self._groups.get(group_a, ())
            for b in self._groups.get(group_b, ())
            if (value := self.standing(a, b)) > 0.0
        ]
        return sum(values) / len(values) if values else 0.0

    # -- review emissions (in-game channel actions ONLY) ---------------------------

    def review_actions(self, *, in_party: bool, ts: float) -> tuple[GameAction, ...]:
        """The review-cadence emissions: the rival taunt or the gossip report.

        Gossip propagates first (the ledger side of the cadence); then at most
        ONE chat premade fires per cadence window — the taunt when the
        viewer's own rivalry crosses the report threshold, else the report
        premade when any standing crosses it. Every emission is an in-game
        channel action; nothing here mutates another agent.
        """
        self.propagate_gossip(ts=ts)
        if not self._emission_due(ts):
            return ()
        action = self._taunt_action(in_party) or self._report_action(in_party)
        if action is None:
            return ()
        self._last_emission_ts = ts
        return (action,)

    def _emission_due(self, ts: float) -> bool:
        last = self._last_emission_ts
        return last is None or ts - last >= RIVALRY_EMISSION_MIN_S

    def _taunt_action(self, in_party: bool) -> GameAction | None:
        for subject in self._own_subjects():
            rival = self.rival_of(subject)
            if rival is None or abs(self._side_attitude(subject, rival)) < GOSSIP_REPORT_THRESHOLD:
                continue
            text = rivalry_premade("taunt", self._worst_member_name(subject, rival))
            if text is not None:
                return self._channel(text, in_party)
        return None

    def _report_action(self, in_party: bool) -> GameAction | None:
        own_group = self._member_group.get(self._persona_id)
        if own_group is None:
            return None
        candidates: list[tuple[float, str]] = []
        for (hearing, subject), value in self._heard.items():
            if hearing == own_group and abs(value) >= GOSSIP_REPORT_THRESHOLD:
                candidates.append((value, subject))
        for other in sorted(self._groups):
            if other == own_group:
                continue
            attitude = self.group_group_standing(own_group, other)
            if abs(attitude) >= GOSSIP_REPORT_THRESHOLD:
                candidates.append((attitude, other))
        if not candidates:
            return None
        value, subject = min(candidates, key=lambda item: (item[0], item[1]))
        category = "bad" if value < 0 else "good"
        text = GOSSIP_REPORT_PREMADES[category].format(
            name=self._worst_member_name(own_group, subject)
        )
        return self._channel(text, in_party)

    def _own_subjects(self) -> list[str]:
        pid = self._persona_id
        subjects: list[str] = []
        own_group = self._member_group.get(pid)
        if own_group is not None:
            subjects.append(own_group)
        subjects.extend(g for g, members in self._guild_members.items() if pid in members)
        return sorted(subjects)

    def _side_attitude(self, side_a: str, side_b: str) -> float:
        if side_a in self._groups and side_b in self._groups:
            return self.group_group_standing(side_a, side_b)
        return self._worst_cross_standing(side_a, side_b)

    def _worst_member_name(self, own_side: str, other_side: str) -> str:
        """The other side's most-negative member (the concrete name to name)."""
        worst_score = 0.0
        worst_member: str | None = None
        for a in sorted(self._side_members(own_side)):
            for b in sorted(self._side_members(other_side)):
                score = self.standing(a, b)
                if worst_member is None or score < worst_score:
                    worst_score = score
                    worst_member = b
        if worst_member is None:
            members = sorted(self._side_members(other_side))
            return self._display(members[0]) if members else other_side
        return self._display(worst_member)

    @staticmethod
    def _channel(text: str, in_party: bool) -> GameAction:
        return PartyChat(text) if in_party else Say(text)

    # -- rivalries -----------------------------------------------------------------

    def note_guild_created(
        self,
        new_guild_id: str,
        new_member_ids: Sequence[str],
        guild_members: Mapping[str, Sequence[str]],
        *,
        rng: random.Random,
        ts: float | None = None,
    ) -> Rivalry | None:
        """The guild-creation rival rule (the user's heuristic).

        With MORE THAN ONE guild in existence, the new guild gains a rival:
        the existing guild whose members hold the WORST aggregate standing
        with the new guild's member-agents (mean over all cross pairs,
        unevidenced pairs neutral). A tie picks through the SEEDED rng.
        A single guild selects no rival yet.
        """
        for guild_id, members in guild_members.items():
            self._guild_members[str(guild_id)] = tuple(members)
        others = {gid: ms for gid, ms in guild_members.items() if gid != new_guild_id}
        if len(guild_members) <= 1 or not others:
            return None
        new_members = tuple(new_member_ids)
        scored = sorted(
            (self._guild_aggregate(new_members, others[gid]), gid) for gid in sorted(others)
        )
        worst = scored[0][0]
        tied = [gid for aggregate, gid in scored if aggregate == worst]
        seed = rng.getrandbits(32)
        rival = tied[0] if len(tied) == 1 else random.Random(seed).choice(sorted(tied))
        return self._record_rivalry(new_guild_id, rival, origin=worst, ts=ts, seed=seed)

    def _guild_aggregate(self, members_a: Sequence[str], members_b: Sequence[str]) -> float:
        """Mean standing over ALL cross pairs (unevidenced pairs neutral 0.0)."""
        if not members_a or not members_b:
            return 0.0
        total = sum(self.standing(a, b) for a in members_a for b in members_b)
        return total / (len(members_a) * len(members_b))

    def maybe_form_group_rivalries(self, *, ts: float | None = None) -> list[Rivalry]:
        """Friend-group rivalries once interaction data accumulates.

        The same worst-aggregate heuristic: every known group pair whose
        aggregate standing reaches ``RIVALRY_FORMATION_STANDING`` (sustained
        negative evidence — two strangers at 0.0 never qualify) and that is
        not already rivals gets one rivalry recorded. Deterministic order.
        """
        formed: list[Rivalry] = []
        for ga, gb in combinations(sorted(self._groups), 2):
            if self._is_rivalry(ga, gb):
                continue
            attitude = self.group_group_standing(ga, gb)
            if attitude > RIVALRY_FORMATION_STANDING:
                continue
            formed.append(self._record_rivalry(ga, gb, origin=attitude, ts=ts, seed=0))
        return formed

    def _record_rivalry(
        self, subject_id: str, rival_id: str, *, origin: float, ts: float | None, seed: int
    ) -> Rivalry:
        rivalry = Rivalry(
            subject_id=subject_id,
            rival_id=rival_id,
            since_ts=float(ts or 0.0),
            origin_score=origin,
            seed=seed,
        )
        self._rivalries[_pair_key(subject_id, rival_id)] = rivalry
        return rivalry

    def _is_rivalry(self, a: str, b: str) -> bool:
        return _pair_key(a, b) in self._rivalries

    def rival_of(self, group_or_guild_id: str) -> str | None:
        """THE WoE-arc seam: the current rival of a group or guild, if any."""
        for key in self._rivalries:
            a, b = key.split(_PAIR_SEP)
            if group_or_guild_id == a:
                return b
            if group_or_guild_id == b:
                return a
        return None

    # -- decay ----------------------------------------------------------------------

    def decay(self, now_ts: float) -> None:
        """Decay every standing toward neutral per the elapsed weekly half-lives."""
        self._advance(now_ts)

    def _advance(self, now_ts: float | None) -> None:
        """Half-life decay up to ``now_ts``; the first timestamp only sets base."""
        if now_ts is None:
            return
        base = self._last_decay_ts
        self._last_decay_ts = now_ts
        if base is None or now_ts <= base:
            return
        factor = 0.5 ** ((now_ts - base) / WEEKLY_HALF_LIFE_S)
        for pair in self._pairs.values():
            pair.score *= factor
        for key in self._heard:
            self._heard[key] *= factor

    # -- persistence -------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """The full ledger state as a JSON-ready dict."""
        return {
            "schema": INTERACTION_SCHEMA,
            "persona_id": self._persona_id,
            "last_decay_ts": self._last_decay_ts,
            "last_emission_ts": self._last_emission_ts,
            "names": dict(self._names),
            "groups": {gid: list(members) for gid, members in self._groups.items()},
            "guild_members": {gid: list(m) for gid, m in self._guild_members.items()},
            "pairs": {
                key: {
                    "score": pair.score,
                    "positives": pair.positives,
                    "negatives": pair.negatives,
                    "party_seconds": pair.party_seconds,
                    "party_sessions": pair.party_sessions,
                    "shared_damage": pair.shared_damage,
                }
                for key, pair in self._pairs.items()
            },
            "heard": {
                f"{hearing}{_PAIR_SEP}{subject}": value
                for (hearing, subject), value in self._heard.items()
            },
            "rivalries": [
                {
                    "subject_id": r.subject_id,
                    "rival_id": r.rival_id,
                    "since_ts": r.since_ts,
                    "origin_score": r.origin_score,
                    "seed": r.seed,
                }
                for r in self._rivalries.values()
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> InteractionLedger:
        """Restore a ledger; unknown schemas fail closed."""
        if data.get("schema") != INTERACTION_SCHEMA:
            msg = f"unsupported interaction ledger schema: {data.get('schema')!r}"
            raise ValueError(msg)
        ledger = cls(persona_id=str(data.get("persona_id", "")))
        ledger._names = {str(k): str(v) for k, v in dict(data.get("names", {})).items()}
        ledger._persona_by_name = {name: pid for pid, name in ledger._names.items()}
        ledger._restore_groups(dict(data.get("groups", {})))
        ledger._restore_guilds(dict(data.get("guild_members", {})))
        ledger._restore_pairs(dict(data.get("pairs", {})))
        ledger._restore_heard(dict(data.get("heard", {})))
        ledger._restore_rivalries(data.get("rivalries", []))
        ledger._last_decay_ts = cls._optional_ts(data.get("last_decay_ts"))
        ledger._last_emission_ts = cls._optional_ts(data.get("last_emission_ts"))
        return ledger

    @classmethod
    def _optional_ts(cls, raw: Any) -> float | None:
        return float(raw) if raw is not None else None

    def _restore_groups(self, groups: Mapping[str, Any]) -> None:
        for group_id, members in groups.items():
            self.seed_group(str(group_id), [str(m) for m in members])

    def _restore_guilds(self, guilds: Mapping[str, Any]) -> None:
        for guild_id, members in guilds.items():
            self._guild_members[str(guild_id)] = tuple(str(m) for m in members)

    def _restore_pairs(self, pairs: Mapping[str, Any]) -> None:
        for key, row in pairs.items():
            valid = self._valid_pair(str(key))
            self._pairs[valid] = _Pair(
                score=float(row.get("score", 0.0)),
                positives=int(row.get("positives", 0)),
                negatives=int(row.get("negatives", 0)),
                party_seconds=float(row.get("party_seconds", 0.0)),
                party_sessions=int(row.get("party_sessions", 0)),
                shared_damage=int(row.get("shared_damage", 0)),
            )

    def _restore_heard(self, heard: Mapping[str, Any]) -> None:
        for key, value in heard.items():
            hearing, _, subject = str(key).partition(_PAIR_SEP)
            if hearing and subject:
                self._heard[(hearing, subject)] = float(value)

    def _restore_rivalries(self, rows: Any) -> None:
        for row in rows:
            rivalry = Rivalry(
                subject_id=str(row["subject_id"]),
                rival_id=str(row["rival_id"]),
                since_ts=float(row.get("since_ts", 0.0)),
                origin_score=float(row.get("origin_score", 0.0)),
                seed=int(row.get("seed", 0)),
            )
            self._rivalries[_pair_key(rivalry.subject_id, rivalry.rival_id)] = rivalry

    @classmethod
    def _valid_pair(cls, key: str) -> str:
        parts = [part for part in key.split(_PAIR_SEP) if part]
        if len(parts) != 2:
            msg = f"malformed pair key: {key!r}"
            raise ValueError(msg)
        return _PAIR_SEP.join(sorted(parts))

    def _restore(self, other: InteractionLedger) -> None:
        self._names = other._names
        self._persona_by_name = other._persona_by_name
        self._groups = other._groups
        self._member_group = other._member_group
        self._guild_members = other._guild_members
        self._pairs = other._pairs
        self._heard = other._heard
        self._rivalries = other._rivalries
        self._last_decay_ts = other._last_decay_ts
        self._last_emission_ts = other._last_emission_ts

    def save(self, path: Path | None = None) -> None:
        """Atomically write the ledger JSON (reconnection continuity)."""
        target = self._path if path is None else path
        if target is None:
            return
        tmp = target.with_name(target.name + ".tmp")
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, sort_keys=True)
            handle.write("\n")
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp, target)


# Chat premades: the report (gossip) and the rivalry taunt/war-declaration
# categories. Emitted as in-game channel actions only; ``{name}`` expands to
# the concrete character name the standing is about (injected roster names).
GOSSIP_REPORT_PREMADES: Final[dict[str, str]] = {
    "bad": "careful with {name}, bad blood there",
    "good": "{name} are solid, party with them",
}
RIVALRY_PREMADES: Final[dict[str, str]] = {
    "taunt": "{name}, you are going down",
    "war": "war on {name}! group up",
}


def rivalry_premade(kind: str, rival_name: str) -> str | None:
    """The rivalry premade phrase for one kind; None when none fits."""
    template = RIVALRY_PREMADES.get(kind)
    return None if template is None else template.format(name=rival_name)


def seed_interaction_roster(ledger: InteractionLedger, population: GeneratedPopulation) -> None:
    """Inject the group roster at agent creation (the meta-knowledge channel).

    Mirrors ``objectives.seed_roster``: the ledger learns every persona id and
    in-game character name plus the friend-group membership, so observed wire
    events can be resolved to KNOWN agents. Roster injection only — no
    coordination content ever travels this way.
    """
    groups: dict[str, list[str]] = {}
    for persona in population.personas:
        ledger.register_persona(persona.persona_id, persona.name)
        if persona.group_id is None:
            continue
        groups.setdefault(persona.group_id, []).append(persona.persona_id)
    for group_id, members in sorted(groups.items()):
        ledger.seed_group(group_id, members)
