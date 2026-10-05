"""Society domain models (ADR-005): personas, groups, schedules."""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, final


class Playstyle(StrEnum):
    """Combat role; limits class choice (tank/melee, healer/support, ...)."""

    TANK = "tank"
    HEALER = "healer"
    MAGE = "mage"
    HUNTER = "hunter"
    SUPPORT = "support"
    MELEE = "melee"


class Attitude(StrEnum):
    """How a group relates to strangers and to world events."""

    HELPFUL_NEWBIE = "helpful_newbie"
    CLIQUE = "clique"
    EVENT_FOCUSED = "event_focused"
    GRINDER = "grinder"
    SOLO = "solo"


class SocietyClock(Protocol):
    """Time source for schedules; adapter feeds local server time."""

    def local_now(self) -> tuple[int, float]:
        """Return ``(weekday, hour_float)`` — Monday=0, hour in [0, 24)."""
        ...


@dataclass(frozen=True, slots=True)
class SocietyPersona:
    """One bot's social identity: name, role, talkativeness, level range."""

    persona_id: str
    name: str
    playstyle: Playstyle
    attitude: Attitude
    chattiness: float
    level_band: tuple[int, int]


ScheduleWindow = tuple[int, float, float]  # (day_of_week 0-6, start_hour, end_hour)


@final
class Schedule:
    """Weekly recurring online windows; windows may wrap midnight."""

    def __init__(self, windows: Sequence[ScheduleWindow]) -> None:
        self.windows: tuple[ScheduleWindow, ...] = tuple(windows)

    def is_online(self, now: tuple[int, float]) -> bool:
        """True if ``now`` (weekday, hour_float) falls inside any window."""
        weekday, hour = now
        for day, start, end in self.windows:
            if start <= end:
                if day == weekday and start <= hour < end:
                    return True
            elif (day == weekday and hour >= start) or ((day + 1) % 7 == weekday and hour < end):
                return True
        return False


@dataclass(frozen=True, slots=True)
class FriendGroup:
    """2-6 personas with mostly-overlapping schedules; size 1 = solo outsider."""

    group_id: str
    member_ids: tuple[str, ...]
    attitude: Attitude
    schedule: Schedule


class ScheduleFactory:
    """Builds mostly-overlapping schedules: shared base windows with jitter."""

    JITTER_HOURS = 2.0
    DURATION_SPREAD = 2.0

    @staticmethod
    def make_group_schedule(rng: random.Random, overlap_hint: int = 2) -> Schedule:
        """A shared base window per 'session' (count = overlap_hint), jittered per group."""
        windows: list[ScheduleWindow] = []
        for _ in range(max(1, overlap_hint)):
            day = rng.randrange(7)
            start = float(rng.randrange(16, 22))  # evening play sessions
            duration = rng.uniform(2.0, 2.0 + ScheduleFactory.DURATION_SPREAD)
            end = start + duration
            if end > 24.0:  # wrap midnight
                windows.append((day, start, end % 24.0))
            else:
                windows.append((day, start, end))
        return Schedule(windows)
