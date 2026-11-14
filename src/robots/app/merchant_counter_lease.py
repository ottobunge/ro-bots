"""Bounded ownership of one's own received counter presence; no peer leases."""

from robots.app.scripts import MERCHANT_ROUTE
from robots.domain.model import BotState

COUNTER_LEASE_SECONDS = 180.0
COUNTER_REJOIN_SECONDS = 30.0


def at_counter(state: BotState) -> bool:
    x, y = MERCHANT_ROUTE["prt_in"]
    return state.map_name == "prt_in" and max(abs(state.x - x), abs(state.y - y)) <= 1


class MerchantCounterLease:
    """Completion or a hard deadline yields; only received parking starts rejoin.

    A timeout does not erase another player's body or authorize walking into it.
    Each client releases its own contact and walks out under normal move gates.
    """

    def __init__(self) -> None:
        self._identity: tuple[str, str, int | None] | None = None
        self._entered: float | None = None
        self._had_dialogue = False
        self.reason: str | None = None
        self._parked: float | None = None
        self.npc_id: int | None = None

    def observe(self, state: BotState, now: float) -> None:
        identity = (state.name, state.map_name, state.native_epoch)
        if identity != self._identity:
            self._entered = None
            self._had_dialogue = False
            self.reason = None
            self._parked = None
            self.npc_id = None
            self._identity = identity
        if self.reason is not None:
            return
        if not at_counter(state):
            self._entered = None
            self._had_dialogue = False
            return
        self._observe_counter(state, now)

    def _observe_counter(self, state: BotState, now: float) -> None:
        if self._entered is None:
            self._entered = now
        completed = state.merchant_returning or (self._had_dialogue and state.npc_dialogue is None)
        if state.npc_dialogue is not None:
            self.npc_id = state.npc_dialogue.npc_id
        self._had_dialogue = self._had_dialogue or state.npc_dialogue is not None
        if completed or now - self._entered >= COUNTER_LEASE_SECONDS:
            self.reason = "completed" if completed else "expired"

    def retrying(self) -> None:
        """An explicit timeout close is not a received completed exchange."""
        self._had_dialogue = False

    def parked(self, now: float) -> bool:
        """Call only for received presence at a body-free, off-lane queue cell."""
        if self._parked is None:
            self._parked = now
        if now - self._parked < COUNTER_REJOIN_SECONDS:
            return False
        self.reason = None
        self._entered = None
        self._had_dialogue = False
        self._parked = None
        return True
