"""Behavior scripts: mechanical execution of a goal between events.

A script is the "autopilot" — it walks, attacks, loots, idles — and it stays
in charge until the world produces an event (see robots.domain.events) or it
completes/fails. No decision-model calls happen inside a script.
"""

from enum import Enum, auto
from typing import TYPE_CHECKING, Protocol, final

from robots.domain.actions import Attack, GameAction, Loot, MoveTo, Rest
from robots.domain.farm import FarmPlan
from robots.domain.model import Goal

if TYPE_CHECKING:
    from robots.domain.model import BotState


class ScriptStatus(Enum):
    ACTIVE = auto()
    DONE = auto()
    FAILED = auto()


class BehaviorScript(Protocol):
    """Anything that can run as a bot's autopilot between events."""

    def step(self, state: BotState) -> ScriptOutcome: ...


@final
class ScriptOutcome:
    """What one script step produced."""

    __slots__ = ("actions", "status")

    def __init__(self, actions: tuple[GameAction, ...], status: ScriptStatus) -> None:
        self.actions = actions
        self.status = status


@final
class TravelScript:
    """Walk toward a destination; DONE on arrival."""

    def __init__(self, x: int, y: int) -> None:
        self._target = (x, y)

    def step(self, state: BotState) -> ScriptOutcome:
        tx, ty = self._target
        if (state.x, state.y) == (tx, ty):
            return ScriptOutcome((), ScriptStatus.DONE)
        dx = (tx > state.x) - (tx < state.x)
        dy = (ty > state.y) - (ty < state.y)
        return ScriptOutcome((MoveTo(x=state.x + dx, y=state.y + dy),), ScriptStatus.ACTIVE)


@final
class GrindScript:
    """Attack the closest monster, loot after kills, rest when hurt."""

    def __init__(self, hp_rest_below: float = 0.25) -> None:
        self._hp_rest_below = hp_rest_below

    def step(self, state: BotState) -> ScriptOutcome:
        if state.hp_ratio < self._hp_rest_below:
            return ScriptOutcome((Rest(),), ScriptStatus.ACTIVE)
        monsters = sorted(state.nearby_monsters, key=lambda m: m.distance)
        if monsters:
            return ScriptOutcome((Attack(target_id=monsters[0].id),), ScriptStatus.ACTIVE)
        if state.inventory:
            return ScriptOutcome((Loot(),), ScriptStatus.ACTIVE)
        return ScriptOutcome((), ScriptStatus.DONE)


@final
class IdleTownScript:
    """Stand around; occasionally shift position a step. Done never — events or a
    goal review end it."""

    def __init__(self, max_steps: int = 10) -> None:
        self._remaining = max_steps

    def step(self, state: BotState) -> ScriptOutcome:
        if self._remaining <= 0:
            return ScriptOutcome((), ScriptStatus.DONE)
        self._remaining -= 1
        return ScriptOutcome((MoveTo(x=state.x, y=state.y + 1),), ScriptStatus.ACTIVE)


@final
class FarmScript:
    """Plan-driven variant of GrindScript: attack only the plan's target mobs,
    ignore everything else (interrupts are the brain's/plan's business)."""

    def __init__(self, plan: FarmPlan, hp_rest_below: float = 0.25) -> None:
        self.plan = plan
        self._hp_rest_below = hp_rest_below

    def step(self, state: BotState) -> ScriptOutcome:
        if state.hp_ratio < self._hp_rest_below:
            return ScriptOutcome((Rest(),), ScriptStatus.ACTIVE)
        targets = [
            m
            for m in sorted(state.nearby_monsters, key=lambda a: a.distance)
            if m.name in self.plan.target_mobs
        ]
        if targets:
            return ScriptOutcome((Attack(target_id=targets[0].id),), ScriptStatus.ACTIVE)
        if state.inventory:
            return ScriptOutcome((Loot(),), ScriptStatus.ACTIVE)
        return ScriptOutcome((), ScriptStatus.ACTIVE)  # keep farming, no mobs right now


def script_for(goal: Goal, state: BotState) -> BehaviorScript:
    """Factory: pick the autopilot matching the chosen goal."""
    if goal in (Goal.GRIND, Goal.FARM_ITEM):
        return GrindScript()
    if goal in (Goal.IDLE_TOWN, Goal.SOCIAL):
        return IdleTownScript()
    if goal == Goal.QUEST:
        return TravelScript(x=state.x, y=max(0, state.y - 5))
    msg = f"no script for goal {goal}"
    raise AssertionError(msg)
