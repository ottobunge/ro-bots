"""Guilds and WoE scheduling (completes the ADR-005 society spec).

Groups may form a :class:`Guild` (multiple friend groups under one banner,
with shared goals); WoE events are weekly recurring world events that the
participation rules map onto group attitudes (event-focused groups always
attend, cliques never, grinders only when a guild goal covers the map, solos
follow their guild). Pure domain layer: no clock, no I/O — ``now`` is the
same ``(weekday, hour_float)`` tuple a :class:`SocietyClock` produces.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import final

from robots.society.models import Attitude, FriendGroup

_GUILD_ID_FMT = "guild-{:03d}"


def majority_attitude(groups: Sequence[FriendGroup]) -> Attitude:
    """The groups' shared attitude: most common, ties broken by first seen."""
    if not groups:
        msg = "a guild needs at least one friend group"
        raise ValueError(msg)
    counts: dict[Attitude, int] = {}
    for group in groups:
        counts[group.attitude] = counts.get(group.attitude, 0) + 1
    # max() returns the first maximal item in insertion order -> first seen.
    return max(counts, key=lambda a: counts[a])


@dataclass(frozen=True, slots=True)
class Guild:
    """Several friend groups under one banner with shared WoE goals."""

    guild_id: str
    name: str
    member_group_ids: tuple[str, ...]
    goals: tuple[str, ...]  # e.g. ("hold Kriemhild", "reach lvl-avg 60")
    attitude: Attitude  # inherited from the member groups' majority

    def member_persona_ids(self, groups: Mapping[str, FriendGroup]) -> tuple[str, ...]:
        """Union of the member groups' persona ids (deduped, group order)."""
        seen: set[str] = set()
        personas: list[str] = []
        for group_id in self.member_group_ids:
            group = groups.get(group_id)
            if group is None:
                continue
            for member in group.member_ids:
                if member not in seen:
                    seen.add(member)
                    personas.append(member)
        return tuple(personas)


@final
class GuildRegistry:
    """Creates and finds guilds; knows which guild a group belongs to."""

    def __init__(self) -> None:
        self._guilds: dict[str, Guild] = {}
        self._group_to_guild: dict[str, str] = {}
        self._seq = 0

    def create(self, name: str, groups: Sequence[FriendGroup], goals: Sequence[str] = ()) -> Guild:
        """Found a guild from one or more friend groups."""
        guild = Guild(
            guild_id=self._next_id(),
            name=name,
            member_group_ids=tuple(g.group_id for g in groups),
            goals=tuple(goals),
            attitude=majority_attitude(groups),
        )
        self._guilds[guild.guild_id] = guild
        for group_id in guild.member_group_ids:
            self._group_to_guild[group_id] = guild.guild_id
        return guild

    def merge(self, groups: Sequence[FriendGroup]) -> Guild:
        """Multiple friend groups joining together; existing goals carry over."""
        merged_goals: list[str] = []
        for group in groups:
            for goal in self.goals_for_group(group.group_id):
                if goal not in merged_goals:
                    merged_goals.append(goal)
        name = " + ".join(g.group_id for g in groups)
        return self.create(name, groups, merged_goals)

    def find(self, guild_id: str) -> Guild | None:
        return self._guilds.get(guild_id)

    def guild_for_group(self, group_id: str) -> Guild | None:
        guild_id = self._group_to_guild.get(group_id)
        return None if guild_id is None else self._guilds.get(guild_id)

    def goals_for_group(self, group_id: str) -> tuple[str, ...]:
        """The goals of the guild holding this group; empty if none."""
        guild = self.guild_for_group(group_id)
        return guild.goals if guild is not None else ()

    def _next_id(self) -> str:
        self._seq += 1
        return _GUILD_ID_FMT.format(self._seq)


@dataclass(frozen=True, slots=True)
class WoeEvent:
    """A weekly recurring War of Emperium window on one target map."""

    woe_id: str
    start_hour: float
    end_hour: float
    day_of_week: int  # Monday=0 (same week model as SocietyClock)
    target_map: str


def _start_weekhour(event: WoeEvent) -> float:
    return event.day_of_week * 24.0 + event.start_hour


@final
class WoeCalendar:
    """Holds the WoE events and answers active/next for a (weekday, hour) now."""

    def __init__(self, events: Sequence[WoeEvent] = ()) -> None:
        self.events: tuple[WoeEvent, ...] = tuple(events)

    def active_woe(self, now: tuple[int, float]) -> WoeEvent | None:
        """The event running right now (start inclusive, end exclusive), if any."""
        weekday, hour = now
        for event in self.events:
            if event.day_of_week == weekday and event.start_hour <= hour < event.end_hour:
                return event
        return None

    def next_woe(self, now: tuple[int, float]) -> WoeEvent | None:
        """The soonest event strictly after ``now``, wrapping to next week."""
        if not self.events:
            return None
        weekday, hour = now
        now_weekhour = weekday * 24.0 + hour
        upcoming = [e for e in self.events if _start_weekhour(e) > now_weekhour]
        # Empty -> every event already passed this week; the earliest one is
        # next week's occurrence (the calendar is weekly recurring).
        return min(upcoming or self.events, key=_start_weekhour)


def _goal_holds_map(goals: tuple[str, ...], target_map: str) -> bool:
    needle = target_map.lower()
    return any(needle in goal.lower() for goal in goals)


_FOLLOWERS = (Attitude.SOLO, Attitude.HELPFUL_NEWBIE)


@final
class WoeParticipation:
    """Decides which groups attend an active WoE, from attitudes + guild goals.

    Rules (deterministic, in group order):
    - ``event_focused`` groups always attend.
    - ``grinder`` groups attend only if their guild's goals include holding
      the WoE's target map.
    - ``clique`` groups never attend.
    - ``solo`` (and ``helpful_newbie``) groups attend if their guild attends —
      i.e. some *other* member group of their guild participates.
    """

    @staticmethod
    def decide(
        groups: Sequence[FriendGroup],
        registry: GuildRegistry,
        woe: WoeEvent | None,
    ) -> tuple[tuple[str, str], ...]:
        """``((group_id, reason), ...)`` for every participating group."""
        if woe is None:
            return ()
        participants: list[tuple[str, str]] = []
        attending: set[str] = set()
        for group in groups:
            reason = WoeParticipation._own_reason(group, registry, woe)
            if reason is None:
                continue
            participants.append((group.group_id, reason))
            attending.add(group.group_id)
        participants.extend(WoeParticipation._followers(groups, registry, attending))
        return tuple(participants)

    @staticmethod
    def _own_reason(group: FriendGroup, registry: GuildRegistry, woe: WoeEvent) -> str | None:
        """A group's own (attitude-driven) reason to attend, or None."""
        if group.attitude is Attitude.EVENT_FOCUSED:
            return f"{group.group_id} attends {woe.target_map}: event_focused always attends WoE"
        if group.attitude is Attitude.GRINDER and _goal_holds_map(
            registry.goals_for_group(group.group_id), woe.target_map
        ):
            return f"{group.group_id} attends: guild goal holds {woe.target_map}"
        return None  # cliques never attend; grinders stay home without a goal

    @staticmethod
    def _followers(
        groups: Sequence[FriendGroup],
        registry: GuildRegistry,
        attending: set[str],
    ) -> list[tuple[str, str]]:
        """Solos/helpfuls follow their guild when some other member attends."""
        followers: list[tuple[str, str]] = []
        for group in groups:
            if group.attitude not in _FOLLOWERS:
                continue
            guild = registry.guild_for_group(group.group_id)
            if guild is None:
                continue
            if any(mid in attending and mid != group.group_id for mid in guild.member_group_ids):
                followers.append((group.group_id, f"{group.group_id} attends: their guild attends"))
        return followers
