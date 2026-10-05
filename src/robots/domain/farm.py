"""Farm plans: Clef-authored farming sessions with custom interrupt rules.

When a bot starts a farming session, the decision model picks the target mobs
(from the map's mob DB) and the session duration. The plan then drives the
behavior script AND customizes the interrupt system: while farming, random
monsters do not wake the brain — only mobs the plan flags as interrupts
(very high level or MVP/unique) do.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MobInfo:
    """One entry from the rAthena mob DB."""

    id: int
    name: str
    level: int
    is_mvp: bool = False


@dataclass(frozen=True, slots=True)
class FarmPlan:
    """A farming session set up by one decision-model call."""

    plan_id: int
    map_name: str
    target_mobs: tuple[str, ...]
    duration_s: float
    interrupt_level_above: int
    interrupt_on_mvp: bool = True


# Clef answers a 3-level score for duration; these map to seconds.
FARM_DURATION_S: dict[int, float] = {0: 300.0, 1: 900.0, 2: 1800.0}

# A mob at least this many levels above the bot is "very high level".
INTERRUPT_LEVEL_MARGIN = 10
