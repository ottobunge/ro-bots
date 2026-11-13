"""Bound dealer travel by received route progress, independently of goal scripts."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MERCHANT_NO_PROGRESS_S = 60.0
MERCHANT_RETRY_COOLDOWN_S = 120.0
MERCHANT_MAX_NO_PROGRESS_S = 300.0
MERCHANT_SECONDS_PER_CELL = 1.0


@dataclass
class MerchantTrip:
    """A route high-water mark; jitter and backward warps cannot renew the lease."""

    remaining: int
    distance: int
    progress_at: float
    retry_at: float = 0.0

    @property
    def no_progress_bound(self) -> float:
        """One second per best-known route-cell distance, clamped to 60-300s.

        Use the high-water mark: moving away cannot purchase a longer lease.
        Route-leg progress still renews the existing timer independently.
        """
        return min(
            MERCHANT_MAX_NO_PROGRESS_S,
            max(MERCHANT_NO_PROGRESS_S, self.distance * MERCHANT_SECONDS_PER_CELL),
        )

    def cooling_down(self, now: float) -> bool:
        return now < self.retry_at

    def advance(self, bot: str, remaining: int, distance: int, now: float) -> bool:
        if self.cooling_down(now):
            return False
        if self.retry_at:
            self.remaining, self.distance, self.progress_at = remaining, distance, now
            self.retry_at = 0.0
            logger.warning("merchant-drive: merchant_trip_retry (bot=%s)", bot)
        if (remaining, distance) < (self.remaining, self.distance):
            self.remaining, self.distance, self.progress_at = remaining, distance, now
        if now - self.progress_at < self.no_progress_bound:
            return True
        self.retry_at = now + MERCHANT_RETRY_COOLDOWN_S
        logger.warning(
            "merchant-drive: merchant_trip_released_no_progress "
            "(bot=%s bound_s=%s elapsed_s=%s remaining=%s best_distance=%s retry_s=%s "
            "rule=route_distance_scaled)",
            bot,
            self.no_progress_bound,
            now - self.progress_at,
            self.remaining,
            self.distance,
            MERCHANT_RETRY_COOLDOWN_S,
        )
        return False
