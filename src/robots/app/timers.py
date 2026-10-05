"""Randomized timers: time-based triggers as event sources.

Example: an 'idle_review' timer that fires X seconds after the last action,
with X drawn uniformly from a configurable range (say 5-20 minutes). Each bot
gets its own phase, so a crowd of bots doesn't review goals in lockstep.
"""

import random
from typing import TYPE_CHECKING, final

from robots.domain.events import PlanExpired, TimerFired, WorldEvent

if TYPE_CHECKING:
    from robots.ports import TickClock


@final
class RandomTimer:
    """Fires TimerFired every time a random delay in [min_s, max_s] elapses."""

    def __init__(
        self,
        name: str,
        min_s: float,
        max_s: float,
        clock: TickClock,
        rng: random.Random | None = None,
    ) -> None:
        self.name = name
        self.min_s = min_s
        self.max_s = max_s
        self._clock = clock
        self._rng = rng or random.Random()
        self.seq = 0
        self._fire_at = self._next_fire_at(self._clock.monotonic())

    def _next_fire_at(self, now: float) -> float:
        return now + self._rng.uniform(self.min_s, self.max_s)

    def fire_due(self, now: float) -> TimerFired | None:
        """Fire at most once per call; auto-reschedules with a fresh delay."""
        if now < self._fire_at:
            return None
        self.seq += 1
        self._fire_at = self._next_fire_at(now)
        return TimerFired(name=self.name, seq=self.seq)

    @property
    def fire_at(self) -> float:
        return self._fire_at


@final
class OnceTimer:
    """Fires a single custom event after a fixed delay, then is spent."""

    def __init__(self, name: str, delay_s: float, clock: TickClock, event: WorldEvent) -> None:
        self.name = name
        self._clock = clock
        self._event = event
        self._fire_at = clock.monotonic() + delay_s
        self.spent = False

    def fire_due(self, now: float) -> WorldEvent | None:
        if self.spent or now < self._fire_at:
            return None
        self.spent = True
        return self._event


@final
class TimerSet:
    """The timers belonging to one bot. Runner polls fire_due() each loop."""

    def __init__(self, clock: TickClock, rng: random.Random | None = None) -> None:
        self._clock = clock
        self._rng = rng
        self._periodic: dict[str, RandomTimer] = {}
        self._once: dict[str, OnceTimer] = {}

    def add_periodic(self, name: str, min_s: float, max_s: float) -> RandomTimer:
        timer = RandomTimer(name, min_s, max_s, self._clock, self._rng)
        self._periodic[name] = timer
        return timer

    def schedule_once(self, name: str, delay_s: float, event: WorldEvent) -> OnceTimer:
        timer = OnceTimer(name, delay_s, self._clock, event)
        self._once[name] = timer
        return timer

    def cancel(self, name: str) -> None:
        self._once.pop(name, None)

    def fire_due(self, now: float | None = None) -> tuple[WorldEvent, ...]:
        t = self._clock.monotonic() if now is None else now
        fired: list[WorldEvent] = []
        for timer in self._periodic.values():
            fired_event: WorldEvent | None = timer.fire_due(t)
            if fired_event is not None:
                fired.append(fired_event)
        for name, once in list(self._once.items()):
            fired_event = once.fire_due(t)
            if fired_event is not None:
                fired.append(fired_event)
                self._once.pop(name, None)
        return tuple(fired)


def idle_review_timer(clock: TickClock, rng: random.Random | None = None) -> RandomTimer:
    """The canonical 'X time since last action' trigger: random 5-20 minutes."""
    return RandomTimer("idle_review", 5 * 60, 20 * 60, clock, rng)


def plan_expiry_timer(clock: TickClock, plan_id: int, duration_s: float) -> OnceTimer:
    return OnceTimer(f"plan_{plan_id}", duration_s, clock, PlanExpired(plan_id=plan_id))
