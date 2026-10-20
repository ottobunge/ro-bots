"""Group objectives: a shared goal that travels ONLY through game socials.

The operator directive: agent planning exists at the agent level AND the
character level — agents hold objectives WITH other agents, but all
coordination runs through GAME SOCIALS (party invites, party chat, whispers,
public chat). This module owns the shared-goal lifecycle and the premade
vocabulary; it never mutates another agent. A member joins by accepting the
in-game party invite (its own brain's ``accept_invite`` path, affinity-gated
through its RelationshipLedger), and its own goal review then aligns with the
objective for its duration.

- **Lifecycle**: ``proposed`` (the leader's goal review opens one when the
  group's schedule-overlap window opens) -> ``invited`` (the in-game party
  invites went out to the online members) -> ``active`` (at least one member
  accepted) -> ``dissolved`` (the schedule window closed / the members left).
- **Premade protocol**: the announcement text (``hunting porings prt_fild08,
  join me``) is the in-game message content — structured enough to recognise
  on receive, exactly what a player would type.
- **Offline coordination**: an offline group member is never telepathised; the
  leader records a ``meet at ...`` whisper that the runtime delivers as a real
  in-game whisper once both are online.
- **Persistence**: the book serialises into the RelationshipLedger's JSON (the
  reconnect-continuity carrier).

Pure stdlib; deterministic; ``ts`` values are caller-supplied floats.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, final

from robots.domain.actions import GameAction, InviteToParty, PartyChat, Say, WhisperTo
from robots.domain.model import BotState, ChatLine, Goal

if TYPE_CHECKING:
    from robots.popgen import GeneratedPopulation
    from robots.society.relations import RelationshipLedger

OBJECTIVE_KINDS: Final = ("hunt", "farm", "town")
OBJECTIVE_PROPOSED: Final = "proposed"
OBJECTIVE_INVITED: Final = "invited"
OBJECTIVE_ACTIVE: Final = "active"
OBJECTIVE_DISSOLVED: Final = "dissolved"
LIVE_STATUSES: Final = (OBJECTIVE_PROPOSED, OBJECTIVE_INVITED, OBJECTIVE_ACTIVE)

_KIND_VERBS: Final = {"hunt": "hunting", "farm": "farming", "town": "idling in"}
_GOALS: Final = {
    "hunt": Goal.GRIND,
    "farm": Goal.FARM_ITEM,
    "town": Goal.IDLE_TOWN,
}
_JOIN_ME: Final = ", join me"
WELCOME_PREMADE: Final = "welcome, {name}!"
DISSOLVE_PREMADE: Final = "gg wp"
OUTSIDER_PREMADE: Final = "can I join? {job} lvl {level}"
OUTSIDER_FLOOR: Final = 0.0  # the solo answers neutral-to-positive senders only
MIN_WINDOW_MEMBERS: Final = 2  # a schedule window needs co-present friends


def objective_premade(kind: str, map_name: str, target: str = "") -> str:
    """The public/party-chat announcement for one objective (the join call)."""
    verb = _KIND_VERBS.get(kind)
    if verb is None:
        msg = f"unknown objective kind: {kind!r}"
        raise ValueError(msg)
    subject = f" {target}" if target else ""
    if kind == "town":
        return f"{verb} {map_name}{_JOIN_ME}"
    return f"{verb}{subject} {map_name}{_JOIN_ME}"


def meet_premade(where: str, when: str) -> str:
    """The recorded whisper for offline group coordination (delivered in-game)."""
    return f"meet at {where} at {when}"


@final
@dataclass(frozen=True, slots=True)
class ObjectiveAnnouncement:
    """One recognised objective announcement (kind + map, target when named)."""

    kind: str
    map_name: str
    target: str | None


def parse_objective_premade(text: str) -> ObjectiveAnnouncement | None:
    """Recognise one of our own announcements; everyday chat returns None.

    The premades are the protocol: the receiver decodes the same canonical
    text the leader emitted (what a player reads from the join call).
    """
    stripped = text.strip()
    for kind in OBJECTIVE_KINDS:
        verb = _KIND_VERBS[kind]
        if not stripped.startswith(verb):
            continue
        body = stripped[len(verb) :].strip()
        if not body.endswith(_JOIN_ME.strip()):
            continue
        body = body[: -len(_JOIN_ME.strip())].strip()
        if kind == "town":
            return ObjectiveAnnouncement(kind=kind, map_name=body, target=None) if body else None
        if not body:
            return None
        target, _, map_name = body.rpartition(" ")
        if not target:
            return ObjectiveAnnouncement(kind=kind, map_name=body, target=None)
        return ObjectiveAnnouncement(kind=kind, map_name=map_name, target=target)
    return None


def objective_goal(kind: str) -> Goal:
    """The drive a member's goal review adopts while the objective is active."""
    goal = _GOALS.get(kind)
    if goal is None:
        msg = f"unknown objective kind: {kind!r}"
        raise ValueError(msg)
    return goal


def seed_roster(ledger: RelationshipLedger, population: GeneratedPopulation) -> None:
    """Inject the group roster at agent creation (agent-level meta-knowledge).

    Every group member's ledger learns the persona ids AND the in-game
    character names of its whole group before any in-game contact — this is
    how friend groups start together and FIND each other in-game (the leader
    invites by the known character name; the members recognize the inviter).
    This is roster injection, NOT telepathy: no coordination MESSAGE content
    ever travels this way — those go only through the game channels.
    """
    by_group: dict[str, list[str]] = {}
    for persona in population.personas:
        ledger.register_persona(persona.persona_id, persona.name)
        if persona.group_id is not None:
            by_group.setdefault(persona.group_id, []).append(persona.persona_id)
    saves = {p.persona_id: p.save_map for p in population.personas}
    for group_id, members in by_group.items():
        ledger.seed_group(group_id, members, save_map=saves[members[0]])


@final
@dataclass(frozen=True, slots=True)
class GroupObjective:
    """One shared group goal, as THIS agent's book records it."""

    objective_id: str
    group_id: str
    leader_id: str
    kind: str
    map_name: str
    target: str | None
    status: str
    invited: tuple[str, ...]
    accepted: tuple[str, ...]
    reason: str | None = None


@final
class GroupObjectiveBook:
    """One agent's record of the group objectives it leads or joined.

    Per-agent state: the leader's book tracks its own formation steps, a
    member's book tracks the objective it joined through the in-game invite.
    Nothing here writes to another agent — cross-agent effects exist only as
    the game packets the caller sends.
    """

    def __init__(self) -> None:
        self._objectives: dict[str, dict[str, Any]] = {}
        self._pending_whispers: dict[str, list[dict[str, str]]] = {}

    # -- lifecycle -------------------------------------------------------------

    def propose(
        self,
        objective_id: str,
        group_id: str,
        leader_id: str,
        kind: str,
        map_name: str,
        *,
        target: str | None = None,
        invited: Sequence[str] = (),
        ts: float | None = None,
    ) -> GroupObjective:
        """Open a proposed objective (the leader's goal review decided)."""
        del ts  # kept for call-site symmetry with the ledger's timestamped records
        if kind not in OBJECTIVE_KINDS:
            msg = f"unknown objective kind: {kind!r}"
            raise ValueError(msg)
        self._objectives[objective_id] = {
            "objective_id": objective_id,
            "group_id": group_id,
            "leader_id": leader_id,
            "kind": kind,
            "map_name": map_name,
            "target": target,
            "status": OBJECTIVE_PROPOSED,
            "invited": tuple(invited),
            "accepted": (),
            "reason": None,
        }
        return self.objective(objective_id)  # type: ignore[return-value]

    def mark_invited(
        self, objective_id: str, member_ids: Sequence[str], *, ts: float | None = None
    ) -> GroupObjective:
        """The party-invite packets went out on the wire."""
        del ts
        row = self._row(objective_id)
        row["invited"] = tuple(member_ids)
        row["status"] = OBJECTIVE_INVITED
        return self.objective(objective_id)  # type: ignore[return-value]

    def record_join(
        self, objective_id: str, member_id: str, *, ts: float | None = None
    ) -> GroupObjective:
        """One member accepted the in-game invite; the first join activates."""
        del ts
        row = self._row(objective_id)
        if member_id not in row["accepted"]:
            row["accepted"] = (*row["accepted"], member_id)
        if row["status"] in (OBJECTIVE_PROPOSED, OBJECTIVE_INVITED):
            row["status"] = OBJECTIVE_ACTIVE
        return self.objective(objective_id)  # type: ignore[return-value]

    def record_leave(
        self, objective_id: str, member_id: str, *, ts: float | None = None
    ) -> GroupObjective:
        """One member left; the last leave dissolves the objective."""
        del ts
        row = self._row(objective_id)
        row["accepted"] = tuple(m for m in row["accepted"] if m != member_id)
        if not row["accepted"]:
            row["status"] = OBJECTIVE_DISSOLVED
            row["reason"] = "members left"
        return self.objective(objective_id)  # type: ignore[return-value]

    def dissolve(
        self, objective_id: str, *, reason: str, ts: float | None = None
    ) -> GroupObjective:
        """The schedule window closed (or the leader ended it)."""
        del ts
        row = self._row(objective_id)
        row["status"] = OBJECTIVE_DISSOLVED
        row["reason"] = reason
        return self.objective(objective_id)  # type: ignore[return-value]

    # -- offline coordination --------------------------------------------------

    def record_whisper(self, objective_id: str, member_id: str, text: str) -> None:
        """Record the meet whisper for an offline member (delivered in-game later)."""
        self._row(objective_id)
        self._pending_whispers.setdefault(objective_id, []).append({"to": member_id, "text": text})

    def due_whispers(
        self, objective_id: str, online_members: Sequence[str]
    ) -> list[tuple[str, str]]:
        """The recorded whispers whose target is online now (and marks them sent)."""
        online = set(online_members)
        pending = self._pending_whispers.get(objective_id, [])
        due = [(w["to"], w["text"]) for w in pending if w["to"] in online]
        self._pending_whispers[objective_id] = [w for w in pending if w["to"] not in online]
        return due

    # -- reading ---------------------------------------------------------------

    def objective(self, objective_id: str) -> GroupObjective | None:
        row = self._objectives.get(objective_id)
        return self._snapshot(objective_id, row) if row is not None else None

    def objectives_for_group(
        self, group_id: str, *, statuses: Sequence[str] = ()
    ) -> tuple[GroupObjective, ...]:
        wanted = tuple(statuses) if statuses else LIVE_STATUSES
        return tuple(
            snapshot
            for objective_id in self._objectives
            if self._objectives[objective_id]["group_id"] == group_id
            and self._objectives[objective_id]["status"] in wanted
            and (snapshot := self.objective(objective_id)) is not None
        )

    def joined_objectives(self) -> tuple[GroupObjective, ...]:
        """The active objectives (a member's own goal-alignment source)."""
        return tuple(
            snapshot
            for objective_id in self._objectives
            if self._objectives[objective_id]["status"] == OBJECTIVE_ACTIVE
            and (snapshot := self.objective(objective_id)) is not None
        )

    def live_objectives(self) -> tuple[GroupObjective, ...]:
        """Every not-yet-dissolved objective this book tracks."""
        return tuple(
            snapshot
            for objective_id in self._objectives
            if self._objectives[objective_id]["status"] in LIVE_STATUSES
            and (snapshot := self.objective(objective_id)) is not None
        )

    def _row(self, objective_id: str) -> dict[str, Any]:
        row = self._objectives.get(objective_id)
        if row is None:
            msg = f"unknown objective: {objective_id!r}"
            raise ValueError(msg)
        return row

    @staticmethod
    def _snapshot(objective_id: str, row: Mapping[str, Any]) -> GroupObjective:
        return GroupObjective(
            objective_id=objective_id,
            group_id=str(row["group_id"]),
            leader_id=str(row["leader_id"]),
            kind=str(row["kind"]),
            map_name=str(row["map_name"]),
            target=row["target"],
            status=str(row["status"]),
            invited=tuple(row["invited"]),
            accepted=tuple(row["accepted"]),
            reason=row["reason"],
        )

    # -- persistence -------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "objectives": {key: dict(row) for key, row in self._objectives.items()},
            "pending_whispers": {
                key: [dict(w) for w in rows] for key, rows in self._pending_whispers.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GroupObjectiveBook:
        book = cls()
        for objective_id, row in dict(data.get("objectives", {})).items():
            merged = dict(row)
            merged.setdefault("reason", None)
            merged["objective_id"] = str(objective_id)
            book._objectives[str(objective_id)] = merged
        for objective_id, rows in dict(data.get("pending_whispers", {})).items():
            book._pending_whispers[str(objective_id)] = [dict(w) for w in rows]
        return book


@final
@dataclass(frozen=True, slots=True)
class FormationSuggestion:
    """The leader's open schedule-overlap window (party_formation's plan)."""

    group_id: str
    leader_id: str
    invitee_ids: tuple[str, ...]


@final
class GroupCoordinator:
    """One agent's coordination view: its OWN ledger + book, emitting packets.

    This is the ONLY channel between agents: everything this class returns is
    in-game packets (party invites, party chat, public chat, whispers) that the
    caller dispatches over the wire. It never mutates another agent — members
    join by accepting the in-game invite through their own brain, and their own
    goal review then aligns with the objective. The roster (persona ids +
    character names) is injected knowledge from ``seed_roster``; the packets
    address friends by their known character name.
    """

    def __init__(self, ledger: RelationshipLedger, persona_id: str) -> None:
        self._ledger = ledger
        self._persona_id = persona_id
        self._offers: dict[str, ObjectiveAnnouncement] = {}

    @property
    def book(self) -> GroupObjectiveBook:
        return self._ledger.objectives

    # -- the leader's side -----------------------------------------------------

    def formation_suggestion(self, online_members: Sequence[str]) -> FormationSuggestion | None:
        """The open window for THIS leader, or None (member / no overlap / live objective)."""
        own_group = self._ledger.group_of(self._persona_id)
        if own_group is None:
            return None
        if any(o.group_id == own_group for o in self.book.live_objectives()):
            return None
        for plan in self._ledger.party_formation(online_members):
            if plan.leader_id == self._persona_id:
                return FormationSuggestion(
                    group_id=own_group, leader_id=plan.leader_id, invitee_ids=plan.invitee_ids
                )
        return None

    def form(
        self,
        kind: str,
        *,
        map_name: str,
        target: str = "",
        online_members: Sequence[str],
        in_party: bool,
        meet_where: str | None = None,
        meet_when: str | None = None,
    ) -> tuple[GroupObjective, tuple[GameAction, ...]]:
        """Open the objective and emit its formation packets (the only channel).

        Emits exactly: one InviteToParty per ONLINE invitee (by the known
        character name), the join-call premade, the ``inviting ...`` premade —
        as party chat when already in a party, public chat otherwise (so solos
        can hear the call). Offline group members get NO packet now: their
        ``meet at ...`` whisper is recorded and delivered as a real in-game
        whisper once both are online (``deliver_whispers``).
        """
        suggestion = self.formation_suggestion(online_members)
        if suggestion is None:
            msg = f"no open formation window for {self._persona_id!r}"
            raise ValueError(msg)
        online = set(online_members)
        away_members = tuple(
            m
            for m in self._ledger.group_members(suggestion.group_id)
            if m not in online and m != self._persona_id
        )
        objective = self.book.propose(
            self._mint_id(suggestion.group_id, kind),
            suggestion.group_id,
            self._persona_id,
            kind,
            map_name,
            target=target or None,
            invited=suggestion.invitee_ids,
        )
        if suggestion.invitee_ids:
            objective = self.book.mark_invited(objective.objective_id, suggestion.invitee_ids)
        for member in away_members:
            if meet_where is not None and meet_when is not None:
                self.book.record_whisper(
                    objective.objective_id, member, meet_premade(meet_where, meet_when)
                )
        channel = PartyChat if in_party else Say
        actions: list[GameAction] = [channel(objective_premade(kind, map_name, target))]
        names = ", ".join(self._ledger.display_name(m) for m in suggestion.invitee_ids)
        actions.append(channel(f"inviting {names}"))
        actions.extend(InviteToParty(self._ledger.display_name(m)) for m in suggestion.invitee_ids)
        return objective, tuple(actions)

    def deliver_whispers(self, online_members: Sequence[str]) -> tuple[GameAction, ...]:
        """The recorded meet whispers whose target is online now (sent once)."""
        actions: list[GameAction] = []
        for objective in self.book.live_objectives():
            for member_id, text in self.book.due_whispers(objective.objective_id, online_members):
                actions.append(WhisperTo(self._ledger.display_name(member_id), text))
        return tuple(actions)

    def record_party_join(self, joiner_name: str) -> tuple[GameAction, ...]:
        """A member joined my party in-game: the objective activates + welcome."""
        joiner = self._ledger.persona_of(joiner_name)
        if joiner is None:
            return ()
        joiner_group = self._ledger.group_of(joiner)
        for objective in self.book.live_objectives():
            if objective.leader_id != self._persona_id or objective.group_id != joiner_group:
                continue
            self.book.record_join(objective.objective_id, joiner)
            return (PartyChat(WELCOME_PREMADE.format(name=joiner_name)),)
        return ()

    def tick(
        self, online_members: Sequence[str], *, in_party: bool = False
    ) -> tuple[GameAction, ...]:
        """The schedule-window guard: a closed window dissolves + says goodbye."""
        actions: list[GameAction] = []
        online = set(online_members)
        for objective in self.book.live_objectives():
            members = self._ledger.group_members(objective.group_id)
            if len(online & set(members)) >= MIN_WINDOW_MEMBERS:
                continue
            self.book.dissolve(objective.objective_id, reason="schedule window closed")
            actions.append(PartyChat(DISSOLVE_PREMADE) if in_party else Say(DISSOLVE_PREMADE))
        return tuple(actions)

    # -- the member's side -----------------------------------------------------

    def note_announcement(self, sender_name: str, text: str) -> bool:
        """Heard a join call in-game: remember the offer made by that character."""
        announcement = parse_objective_premade(text)
        if announcement is None:
            return False
        self._offers[sender_name] = announcement
        return True

    def accept_invite_from(self, leader_name: str) -> GroupObjective | None:
        """MY OWN accept of the in-game invite: the offer becomes my objective.

        Records the join in MY book only (no cross-agent write) — the leader
        learns of it by observing the party join in-game. An invite without a
        heard announcement aligns nothing (there is no invented objective).
        """
        offer = self._offers.get(leader_name)
        if offer is None:
            return None
        leader_persona = self._ledger.persona_of(leader_name)
        group_id = (
            self._ledger.group_of(leader_persona)
            if leader_persona is not None
            else self._ledger.group_of(self._persona_id)
        )
        objective = self.book.propose(
            self._mint_id(group_id or "unknown", offer.kind),
            group_id or "unknown",
            leader_persona or "",
            offer.kind,
            offer.map_name,
            target=offer.target,
            invited=(self._persona_id,),
        )
        return self.book.record_join(objective.objective_id, self._persona_id)

    # -- the solo outsider's side ------------------------------------------------

    def outsider_reply(
        self, line: ChatLine, *, in_party: bool, job: str = "", level: int | None = None
    ) -> GameAction | None:
        """Affinity-gated whisper answering a public join call (the outsider).

        Solos only, never while in a party, and only for recognised join-call
        premades: neutral-to-positive senders get the join-request whisper,
        bad-reputation senders (negative friendship) get nothing.
        """
        if in_party or self._ledger.group_of(self._persona_id) is not None:
            return None
        if parse_objective_premade(line.text) is None:
            return None
        sender = self._ledger.persona_of(line.sender)
        affinity = self._ledger.friendship(self._persona_id, sender) if sender is not None else 0.0
        if affinity < OUTSIDER_FLOOR:
            return None
        return WhisperTo(line.sender, OUTSIDER_PREMADE.format(job=job, level=level))

    # -- helpers -------------------------------------------------------------

    def suggestion_line(
        self, suggestion: FormationSuggestion, online_members: Sequence[str]
    ) -> str:
        """The decide-context sentence for an open window (names + counts)."""
        members = self._ledger.group_members(suggestion.group_id)
        online = [m for m in members if m in set(online_members)]
        names = ", ".join(self._ledger.display_name(m) for m in suggestion.invitee_ids)
        return (
            f"your group {suggestion.group_id} is online ({len(online)}/{len(members)}); "
            f"you lead; party_formation suggests inviting {names}"
        )

    def _mint_id(self, group_id: str, kind: str) -> str:
        taken = sum(1 for o in self.book.live_objectives() if o.group_id == group_id)
        return f"{group_id}-{kind}-{taken + 1}"


@final
class BoundCoordinator:
    """The brain-facing adapter: the coordinator bound to the online provider.

    The runtime owns the connection facts (who is online, the rendezvous
    point); the brain must not. This adapter closes over them so the brain's
    coordination calls stay parameter-free, and turns the model's
    ``objective_action`` review answer into the packet emission.
    """

    def __init__(
        self,
        coordinator: GroupCoordinator,
        *,
        online: Callable[[], Sequence[str]],
        meet_where: str | None = None,
        meet_when: str | None = None,
    ) -> None:
        self._coordinator = coordinator
        self._online = online
        self._meet_where = meet_where
        self._meet_when = meet_when

    @property
    def book(self) -> GroupObjectiveBook:
        return self._coordinator.book

    def formation_question(self) -> dict[str, Any] | None:
        """The objective_action review question when the leader's window is open."""
        online = self._online()
        suggestion = self._coordinator.formation_suggestion(online)
        if suggestion is None:
            return None
        return {
            "type": "choice",
            "instructions": (
                f"{self._coordinator.suggestion_line(suggestion, online)}. "
                "Form a group objective? The invites and the join call go out in-game."
            ),
            "criteria": {
                "none": "Not now - keep the current plan.",
                "hunt": "Form the group objective: hunt together (party invites + join call).",
                "farm": "Form the group objective: farm together (party invites + join call).",
                "town": "Form the group objective: idle in town together.",
            },
        }

    def review_actions(self, state: BotState, answers: Mapping[str, Any]) -> tuple[GameAction, ...]:
        """One review's coordination packets: form on the answer, deliver, guard."""
        actions: list[GameAction] = []
        kind = str(answers.get("objective_action", {}).get("choice", "none"))
        window_open = self._coordinator.formation_suggestion(self._online()) is not None
        if kind in OBJECTIVE_KINDS and window_open:
            target = str(answers.get("farm_target", {}).get("choice", "")) if kind != "town" else ""
            _objective, formed = self._coordinator.form(
                kind,
                map_name=state.map_name,
                target=target,
                online_members=self._online(),
                in_party=state.in_party,
                meet_where=self._meet_where,
                meet_when=self._meet_when,
            )
            actions.extend(formed)
        actions.extend(self._coordinator.deliver_whispers(self._online()))
        actions.extend(self._coordinator.tick(self._online(), in_party=state.in_party))
        return tuple(actions)

    def active_objective(self) -> GroupObjective | None:
        """The objective this agent joined (the alignment source), if any."""
        joined = self._coordinator.book.joined_objectives()
        return joined[0] if joined else None

    def aligned_goal(self) -> Goal | None:
        """The drive the active objective pins, or None when free to choose."""
        objective = self.active_objective()
        return objective_goal(objective.kind) if objective is not None else None

    def objective_map(self) -> str | None:
        """The active objective's map (the farm-plan alignment), or None."""
        objective = self.active_objective()
        return objective.map_name if objective is not None else None

    def on_invite_accepted(self, leader_name: str) -> GroupObjective | None:
        """MY accept of the in-game invite: record the join in MY book."""
        return self._coordinator.accept_invite_from(leader_name)

    def observe_chat(self, line: ChatLine, state: BotState) -> GameAction | None:
        """A heard line: record a join-call offer, then the solo outsider gate."""
        self._coordinator.note_announcement(line.sender, line.text)
        return self.outsider_reply(line, state)

    def outsider_reply(self, line: ChatLine, state: BotState) -> GameAction | None:
        """The solo's affinity-gated whisper answering a public join call."""
        return self._coordinator.outsider_reply(
            line, in_party=state.in_party, job=state.job, level=state.base_level
        )
