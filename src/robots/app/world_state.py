"""WorldState: the in-memory aggregate behind the WorldFeed API (ADR-007/008).

The runner owns one :class:`WorldState`:

- the :class:`~robots.society.society.SocietyRoster` (seeded, reproducible),
- per-agent :class:`AgentRuntimeState` (goal / script / plan / memory view /
  characters / online flag),
- a bounded event feed of :class:`FeedItem`s (what ``GET /feed/events``
  streams),
- per-agent :class:`~robots.society.memory.MemoryLog` instances, and the
  reputation entries of the roster's :class:`ReputationStore` when the human
  layer (``robots.society.human``) is present.

Operator commands arrive as plain dicts (the WorldFeed ``POST /commands``
body) and are applied by :meth:`WorldState.apply_command`; invalid input
raises :class:`CommandError`, which the API layer maps to HTTP 400/404.
"""

import random
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from threading import RLock
from typing import TYPE_CHECKING, Any, final

from robots.app.roster_edit import with_group_schedule, with_persona_edited
from robots.society.memory import ExperienceNote, MemoryLog, StubSummarizer, render_view
from robots.society.models import Attitude, Playstyle, Schedule
from robots.society.population_limits import validate_population
from robots.society.society import ReputationStore, SocietyRoster

if TYPE_CHECKING:
    from robots.society.human import HumanTracker

try:  # the human layer is landing concurrently; tolerate its absence
    from robots.society.human import HumanTracker
except ImportError:  # pragma: no cover - exercised only while human.py is in flight
    HumanTracker = None  # type: ignore[assignment, misc]

EVENT_FEED_MAXLEN = 1000
DEFAULT_SEED = 42
DEFAULT_GROUPS = 3
DEFAULT_GROUP_SIZE_MAX = 6

_EDITABLE_PERSONA_FIELDS = ("name", "playstyle", "attitude", "chattiness")


class CommandError(ValueError):
    """Invalid operator command: bad type, unknown persona, malformed fields."""


def _parse_windows(windows_raw: Any) -> tuple[tuple[int, float, float], ...]:
    """Validate a JSON ``windows`` list into typed ``ScheduleWindow`` tuples."""
    if not isinstance(windows_raw, list) or not windows_raw:
        msg = "'windows' must be a non-empty list of [day, start, end]"
        raise CommandError(msg)
    windows: list[tuple[int, float, float]] = []
    for raw in windows_raw:
        if not isinstance(raw, (list, tuple)) or len(raw) != 3:
            msg = "each window must be [day, start, end]"
            raise CommandError(msg)
        day, start, end = raw
        try:
            window = (int(day), float(start), float(end))
        except TypeError, ValueError:
            msg = "window fields must be numeric"
            raise CommandError(msg) from None
        if not 0 <= window[0] <= 6:
            msg = "window day must be in [0, 6]"
            raise CommandError(msg)
        if not 0.0 <= window[1] < 24.0 or not 0.0 < window[2] <= 24.0:
            msg = "window hours must be in [0, 24]"
            raise CommandError(msg)
        windows.append(window)
    return tuple(windows)


@final
@dataclass(frozen=True, slots=True)
class AgentRuntimeState:
    """What one agent is doing right now, as shown in the dashboard inspector."""

    persona_id: str
    current_goal: str = "idle"
    current_script: str = ""
    current_plan: str = ""
    memory_view: tuple[str, ...] = ()
    characters: tuple[str, ...] = ()
    online: bool = False


@final
@dataclass(frozen=True, slots=True)
class FeedItem:
    """One event-feed line (SSE payload of ``GET /feed/events``)."""

    ts: float
    kind: str
    summary: str
    operator_forced: bool = False
    sequence: int = 0


@final
class WorldState:
    """Mutable aggregate: roster + runtime states + bounded event feed."""

    def __init__(self, roster: SocietyRoster, *, clock: Callable[[], float] | None = None) -> None:
        # One aggregate lock also owns the feed: there is no feed/state lock
        # inversion. Never acquire a MemoryLog lock while holding this lock.
        self._state_lock = RLock()
        self._roster = roster
        self._clock = clock or time.time
        self._feed: list[FeedItem] = []
        self._feed_lock = self._state_lock
        self._next_event_sequence = 0
        self._agent_states: dict[str, AgentRuntimeState] = {}
        self._memories: dict[str, MemoryLog] = {}
        self._host_bound = False
        self._seed: int = DEFAULT_SEED
        self._group_size_max: int = DEFAULT_GROUP_SIZE_MAX
        self._reputation: ReputationStore = roster.reputation
        for persona in roster.personas.values():
            self._agent_states[persona.persona_id] = AgentRuntimeState(
                persona_id=persona.persona_id, online=False
            )
            self._memories[persona.persona_id] = MemoryLog(StubSummarizer())

    # -- read paths ---------------------------------------------------------

    @property
    def roster(self) -> SocietyRoster:
        """One committed roster; separate calls are not a transaction snapshot.

        Raw mutable collections and multi-call adapter serialization still
        require external exclusion of unbound regeneration.
        """
        with self._state_lock:
            return self._roster

    @roster.setter
    def roster(self, roster: SocietyRoster) -> None:
        with self._state_lock:
            self._roster = roster

    @property
    def events(self) -> tuple[FeedItem, ...]:
        """The bounded event feed, oldest first (capped at ``EVENT_FEED_MAXLEN``)."""
        with self._feed_lock:
            return tuple(self._feed)

    def memory_lines(self, persona_id: str) -> tuple[str, ...]:
        """The agent's current memory view (ADR-004 render), including notes."""
        with self._state_lock:
            log = self._memories[persona_id]
        return self._memory_lines(log)

    @staticmethod
    def _memory_lines(log: MemoryLog) -> tuple[str, ...]:
        # Summarizers/storage may call back into WorldState. Resolve ownership
        # first, then release the aggregate lock before touching private memory.
        with log.locked():
            lines = list(render_view(log))
            for note in log.notes()[log.dirty_upto :]:
                lines.append(f"{note.kind}: {note.text}")
            return tuple(lines)

    def agent_state(self, persona_id: str) -> AgentRuntimeState | None:
        """The agent's runtime state, or None for an unknown id."""
        with self._state_lock:
            return self._agent_states.get(persona_id)

    def reputation_entries(self, persona_id: str) -> list[dict[str, float | str]]:
        """Score rows for the agent's group and (if the human layer landed) itself.

        With ``robots.society.human`` present the tracker writes per-agent rows
        alongside the propagated group rows; without it only group rows exist.
        """
        with self._state_lock:
            return self._reputation_entries(persona_id)

    def _reputation_entries(self, persona_id: str) -> list[dict[str, float | str]]:
        group_id = self._group_of(persona_id)
        humans = sorted(
            self._reputation.group_humans(group_id) | self._reputation.agent_humans(persona_id)
        )
        entries: list[dict[str, float | str]] = []
        for human in humans:
            entry: dict[str, float | str] = {
                "human": human,
                "group_score": self._reputation.group_score(group_id, human),
            }
            if HumanTracker is not None:
                entry["agent_score"] = self._reputation.agent_score(persona_id, human)
            entries.append(entry)
        return entries

    # -- mutation paths -----------------------------------------------------

    def bind_memory(self, persona_id: str, log: object) -> None:
        """Bind the runtime's live log; storage remains owned by its host."""
        with self._state_lock:
            self._require_persona(persona_id)
            if not isinstance(log, MemoryLog):
                msg = "memory must be a MemoryLog"
                raise TypeError(msg)
            self._memories[persona_id] = log
            self._host_bound = True

    def push_event(self, kind: str, summary: str, operator_forced: bool = False) -> FeedItem:
        """Append one event to the bounded feed (oldest silently evicted)."""
        with self._feed_lock:
            return self._push_event(kind, summary, operator_forced)

    def _push_event(self, kind: str, summary: str, operator_forced: bool) -> FeedItem:
        item = FeedItem(
            ts=self._clock(),
            kind=kind,
            summary=summary,
            operator_forced=operator_forced,
            sequence=self._next_event_sequence,
        )
        self._next_event_sequence += 1
        self._feed.append(item)
        if len(self._feed) > EVENT_FEED_MAXLEN:
            self._feed = self._feed[-EVENT_FEED_MAXLEN:]
        return item

    def set_agent_state(
        self,
        persona_id: str,
        *,
        current_goal: str | None = None,
        current_script: str | None = None,
        current_plan: str | None = None,
        online: bool | None = None,
    ) -> AgentRuntimeState:
        """Update the running goal/script/plan/online flag of one agent."""
        while True:
            with self._state_lock:
                self._require_persona(persona_id)
                log = self._memories[persona_id]
            memory_view = self._memory_lines(log)
            with self._state_lock:
                self._require_persona(persona_id)
                if self._memories[persona_id] is not log:
                    continue
                current = self._agent_states[persona_id]
                updated = replace(
                    current,
                    current_goal=current.current_goal if current_goal is None else current_goal,
                    current_script=(
                        current.current_script if current_script is None else current_script
                    ),
                    current_plan=current.current_plan if current_plan is None else current_plan,
                    memory_view=memory_view,
                    characters=current.characters,
                    online=current.online if online is None else online,
                )
                self._agent_states[persona_id] = updated
                return updated

    def apply_command(self, cmd: Any) -> FeedItem:
        """Dispatch one operator command dict; returns the emitted feed item."""
        if not isinstance(cmd, dict):
            msg = "command body must be a JSON object"
            raise CommandError(msg)
        match cmd.get("type"):
            case "regenerate_roster":
                return self._apply_regenerate_roster(cmd)
            case "edit_persona":
                with self._state_lock:
                    return self._apply_edit_persona(cmd)
            case "force_action":
                return self._apply_force_action(cmd)
            case "force_schedule":
                with self._state_lock:
                    return self._apply_force_schedule(cmd)
            case _:
                msg = f"unknown command type: {cmd.get('type')!r}"
                raise CommandError(msg)

    # -- command implementations --------------------------------------------

    def _apply_regenerate_roster(self, cmd: dict[str, Any]) -> FeedItem:
        with self._state_lock:
            self._require_unbound()
            default_size = self._group_size_max
        seed = self._int_field(cmd, "seed")
        groups = self._int_field(cmd, "groups")
        solos = self._int_field(cmd, "solos", default=0)
        friends_min = self._int_field(cmd, "friends_min", default=2)
        friends_max = self._int_field(cmd, "friends_max", default=default_size)
        if groups < 0 or solos < 0 or groups + solos == 0:
            msg = "'groups' and 'solos' must be nonnegative with a nonempty population"
            raise CommandError(msg)
        if friends_min < 2:
            msg = "'friends_min' must be >= 2; request singleton groups through 'solos'"
            raise CommandError(msg)
        if friends_min > friends_max:
            msg = "'friends_min' must be <= 'friends_max'"
            raise CommandError(msg)
        n_groups = groups + solos
        try:
            validate_population(n_groups, friends_min, friends_max, solos)
        except (TypeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        rng = random.Random(seed)
        roster = SocietyRoster.build(
            rng,
            n_groups=n_groups,
            group_size_min=friends_min,
            group_size_max=friends_max,
            solos=solos,
        )
        agent_states = {}
        memories = {}
        for persona in roster.personas.values():
            agent_states[persona.persona_id] = AgentRuntimeState(
                persona_id=persona.persona_id, online=False
            )
            memories[persona.persona_id] = MemoryLog(StubSummarizer())
        with self._state_lock:
            # Binding can win while the candidate is built. Nothing in the
            # aggregate (including defaults and feed) changes before this guard.
            self._require_unbound()
            self._seed = seed
            self._group_size_max = max(self._group_size_max, friends_max)
            self.roster = roster
            self._reputation = roster.reputation
            self._agent_states = agent_states
            self._memories = memories
            return self.push_event(
                "roster", f"roster regenerated (seed {seed}, {groups} groups + {solos} solos)"
            )

    def _require_unbound(self) -> None:
        if self._host_bound:
            msg = "host-bound roster regeneration requires account and memory reconciliation"
            raise CommandError(msg)

    def _apply_edit_persona(self, cmd: dict[str, Any]) -> FeedItem:
        persona_id = self._str_field(cmd, "persona_id")
        self._require_persona(persona_id)
        fields: dict[str, Any] = {}
        for name in _EDITABLE_PERSONA_FIELDS:
            if name not in cmd:
                continue
            value = cmd[name]
            if name == "playstyle":
                fields[name] = self._enum_field(value, Playstyle, name)
            elif name == "attitude":
                fields[name] = self._enum_field(value, Attitude, name)
            elif name == "chattiness":
                try:
                    value = float(value)
                except TypeError, ValueError:
                    msg = "'chattiness' must be a number"
                    raise CommandError(msg) from None
                if not 0.0 <= value <= 1.0:
                    msg = "'chattiness' must be in [0, 1]"
                    raise CommandError(msg)
                fields[name] = value
            else:
                fields[name] = self._str_field(cmd, name)
        if not fields:
            msg = "no editable persona fields given"
            raise CommandError(msg)
        self.roster = with_persona_edited(self.roster, persona_id, **fields)
        self.roster.personas[persona_id]
        changed = ", ".join(sorted(fields))
        return self.push_event("edit", f"persona {persona_id} edited ({changed})")

    def _apply_force_action(self, cmd: dict[str, Any]) -> FeedItem:
        persona_id = self._str_field(cmd, "persona_id")
        action = self._str_field(cmd, "action")
        with self._state_lock:
            self._require_persona(persona_id)
            log = self._memories[persona_id]
        args = cmd.get("args", "")
        summary = f"operator forced: {action} {args}".strip()
        note = ExperienceNote(ts=self._clock(), kind="session", text=summary)
        log.append(note)
        return self.push_event("force", summary, operator_forced=True)

    def _apply_force_schedule(self, cmd: dict[str, Any]) -> FeedItem:
        persona_id = self._str_field(cmd, "persona_id")
        self._require_persona(persona_id)
        windows = _parse_windows(cmd.get("windows"))
        self.roster = with_group_schedule(self.roster, persona_id, Schedule(windows))
        shown = ", ".join(f"d{d} {s:.0f}-{e:.0f}" for d, s, e in windows)
        return self.push_event("schedule", f"schedule of {persona_id} replaced ({shown})")

    # -- helpers ------------------------------------------------------------

    def _require_persona(self, persona_id: str) -> None:
        if persona_id not in self.roster.personas:
            msg = f"unknown persona_id: {persona_id!r}"
            raise CommandError(msg)

    @staticmethod
    def _str_field(cmd: dict[str, Any], name: str) -> str:
        value = cmd.get(name)
        if not isinstance(value, str) or not value:
            msg = f"missing or empty field: {name!r}"
            raise CommandError(msg)
        return value

    @staticmethod
    def _int_field(cmd: dict[str, Any], name: str, *, default: int | None = None) -> int:
        if name not in cmd and default is not None:
            return default
        value = cmd.get(name)
        if not isinstance(value, int) or isinstance(value, bool):
            msg = f"missing or non-integer field: {name!r}"
            raise CommandError(msg)
        return value

    @staticmethod
    def _enum_field(value: Any, enum_type: Any, name: str) -> Any:
        try:
            return enum_type(value)
        except ValueError:
            members = ", ".join(m.value for m in enum_type)
            msg = f"invalid {name!r}: {value!r} (expected one of {members})"
            raise CommandError(msg) from None

    def _group_of(self, persona_id: str) -> str:
        for group in self.roster.groups:
            if persona_id in group.member_ids:
                return group.group_id
        msg = f"unknown persona_id: {persona_id!r}"
        raise CommandError(msg)  # pragma: no cover
