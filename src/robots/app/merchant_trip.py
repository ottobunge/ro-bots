"""Bound dealer travel by received route progress, independently of goal scripts."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

MERCHANT_NO_PROGRESS_S = 60.0
MERCHANT_RETRY_COOLDOWN_S = 120.0


@dataclass
class MerchantTrip:
    """A route high-water mark; jitter and backward warps cannot renew the lease."""

    remaining: int
    distance: int
    progress_at: float
    retry_at: float = 0.0

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
        if now - self.progress_at < MERCHANT_NO_PROGRESS_S:
            return True
        self.retry_at = now + MERCHANT_RETRY_COOLDOWN_S
        logger.warning(
            "merchant-drive: merchant_trip_released_no_progress "
            "(bot=%s bound_s=%s elapsed_s=%s remaining=%s best_distance=%s retry_s=%s)",
            bot,
            MERCHANT_NO_PROGRESS_S,
            now - self.progress_at,
            self.remaining,
            self.distance,
            MERCHANT_RETRY_COOLDOWN_S,
        )
        return False
