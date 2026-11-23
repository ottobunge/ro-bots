"""Finite continuation of an authored target, independent of decision latency."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from threading import RLock
from typing import Concatenate

from robots.domain.model import BotState

COMBAT_PUMP_INTERVAL_S = 2.0
COMBAT_INTENT_SECONDS = 30.0


def gameplay_serialized[T, **P, R](
    method: Callable[Concatenate[T, P], R],
) -> Callable[Concatenate[T, P], R]:
    """Share received-state mutations between the host and its keepalive pump.

    Lazy allocation also supports the small __new__ runtime fixtures. An RLock
    permits ordinary perform -> build -> observe nesting; model calls never
    hold this lock. Keepalive's send lock must be released before entering it.
    """

    @wraps(method)
    def guarded(self: T, /, *args: P.args, **kwargs: P.kwargs) -> R:
        with vars(self).setdefault("_gameplay_lock", RLock()):
            return method(self, *args, **kwargs)

    return guarded


@dataclass(frozen=True)
class CombatIntent:
    target_id: int
    epoch: int | None
    map_name: str
    until: float

    def valid(self, state: BotState, now: float) -> bool:
        return (
            state.native_epoch == self.epoch
            and state.map_name == self.map_name
            and self.until - COMBAT_INTENT_SECONDS <= now < self.until
        )
