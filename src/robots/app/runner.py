"""Runner: drives bots' brains against the world on a tick loop.

Per tick: fire due timers -> deliver interrupting events to the brain ->
otherwise let the behavior script run mechanically. Timer scheduling and
event filtering (FarmPlan interrupt rules) live in the brain; the runner
is just the pump.
"""

import logging
from typing import TYPE_CHECKING, final

from robots.app.brain import TickResult
from robots.domain.events import MonsterSpotted, WorldEvent

if TYPE_CHECKING:
    from robots.app.brain import EventDrivenBrain
    from robots.app.timers import TimerSet
    from robots.domain.model import BotState
    from robots.ports import GameClient, TickClock

logger = logging.getLogger(__name__)


@final
class BotRunner:
    """Ties one brain (+ its timers) to one game client and runs the loop."""

    def __init__(
        self,
        brain: EventDrivenBrain,
        client: GameClient,
        clock: TickClock,
        tick_seconds: float = 1.0,
        timers: TimerSet | None = None,
    ) -> None:
        self._brain = brain
        self._client = client
        self._clock = clock
        self._tick_seconds = tick_seconds
        self._timers = timers
        self.history: list[TickResult] = []

    def deliver_event(self, state: BotState, event: WorldEvent) -> TickResult | None:
        """Apply the brain's interrupt rules, then hand the event over."""
        if isinstance(event, MonsterSpotted) and not self._brain.should_interrupt(event):
            return None
        result = self._brain.handle_event(state, event)
        self.history.append(result)
        return result

    def run(self, max_ticks: int = 100) -> None:
        """Run at most ``max_ticks`` ticks; stop early on repeated errors."""
        errors = 0
        for _ in range(max_ticks):
            try:
                state = self._client.poll_state()
                self._pump_events(state)
                outcome = self._brain.step_script(state)
                for action in outcome.actions:
                    self._client.act(action)
                errors = 0
            except Exception:
                logger.exception("tick failed")
                errors += 1
                if errors >= 3:
                    logger.error("three consecutive tick failures; stopping bot")
                    return
            self._clock.sleep(self._tick_seconds)

    def _pump_events(self, state: BotState) -> None:
        if self._timers is None:
            return
        for event in self._timers.fire_due(self._clock.monotonic()):
            self.deliver_event(state, event)
