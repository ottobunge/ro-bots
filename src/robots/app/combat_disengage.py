"""Bounded withdrawal from the particular target this client actually swung at."""

import logging

from robots.adapters.native_navigation import NoRoute, Point, WalkMap, shortest_path
from robots.app.combat_survival import survivability_refusal
from robots.domain.model import ActorRef, BotState
from robots.ports import MobDatabase

logger = logging.getLogger(__name__)
DISENGAGE_SECONDS = 8.0
DISENGAGE_ENGAGEMENT_S = 30.0
_DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1))


class CombatDisengage:
    """One engagement, one finite retreat; expiry needs a fresh swing to rearm."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._engaged: ActorRef | None = None
        self._until: float | None = None
        self._engaged_until = 0.0

    def engage(self, actor: ActorRef, now: float) -> None:
        self._engaged = actor
        self._until = None
        self._engaged_until = now + DISENGAGE_ENGAGEMENT_S

    def vanish(self, actor_id: int) -> None:
        if self._engaged is not None and self._engaged.id == actor_id and self._until is None:
            self.reset()

    def source(self, state: BotState, mob_db: MobDatabase | None, now: float) -> Point | None:
        target = self._current(state, now)
        if target is None:
            return None
        target = next((a for a in state.nearby_monsters if a.id == target.id), target)
        self._engaged = target
        if not self._withdrawing(state, mob_db, now, target):
            return None
        if target.x is None or target.y is None:
            return None
        return target.x, target.y

    def _current(self, state: BotState, now: float) -> ActorRef | None:
        valid_life = state.alive is True and state.hp > 1 and state.max_hp > 0
        stale = self._until is None and now >= self._engaged_until
        if not valid_life or stale:
            self.reset()
        return self._engaged

    def _withdrawing(
        self, state: BotState, mob_db: MobDatabase | None, now: float, target: ActorRef
    ) -> bool:
        if self._until is None:
            self._begin(state, mob_db, now, target)
        if self._until is None:
            return False
        if now >= self._until:
            logger.warning("disengage_end reason=disengage_expired bot=%s", state.name)
            self.reset()
            return False
        return True

    def _begin(
        self, state: BotState, mob_db: MobDatabase | None, now: float, target: ActorRef
    ) -> None:
        detail = survivability_refusal(state, str(target.name), mob_db)
        if detail is None:
            return
        self._until = now + DISENGAGE_SECONDS
        logger.warning(
            "disengage_start reason=disengage_%s target_id=%s species=%s bot=%s bound_s=%s",
            detail,
            target.id,
            target.name,
            state.name,
            DISENGAGE_SECONDS,
        )


def disengage_step(grid: WalkMap, state: BotState, source: Point) -> Point | None:
    """Choose only an adjacent, reachable cell pointing away from that target.

    Do not route around a wall through the target. Dynamic blockers come only
    from the bot's visible stream; a sealed retreat holds without inventing one.
    """
    vx, vy = state.x - source[0], state.y - source[1]
    directions = sorted(
        _DIRECTIONS,
        key=lambda d: (d[0] * vx + d[1] * vy, -abs(d[0] * vy - d[1] * vx)),
        reverse=True,
    )
    blocked = frozenset(state.occupied_cells) | {
        (a.x, a.y) for a in state.nearby if a.x is not None and a.y is not None
    }
    for dx, dy in directions:
        point = state.x + dx, state.y + dy
        if dx * vx + dy * vy <= 0 or point in blocked:
            continue
        try:
            path = shortest_path(grid, (state.x, state.y), point)
        except NoRoute:
            continue
        if len(path) == 2:
            return point
    return None
