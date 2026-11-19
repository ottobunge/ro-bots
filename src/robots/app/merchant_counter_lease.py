"""Bounded ownership of one's own received counter presence; no peer leases."""

from robots.app.merchant_staging import Body, Point, _dealer_cell, _received_body_cells
from robots.domain.model import BotState

COUNTER_LEASE_SECONDS = 180.0
COUNTER_REJOIN_SECONDS = 30.0


def at_counter(state: BotState) -> bool:
    x, y = _dealer_cell(state)
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
        self.queue = MerchantCounterQueue()

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

    def rotate(self, state: BotState, own_id: int, bodies: tuple[Body, ...]) -> None:
        """Drain a legacy crowded band; received actor ID breaks bootstrap ties."""
        if self.reason is not None or not at_counter(state):
            return
        x, y = _dealer_cell(state)
        holders = [aid for aid, p in bodies if max(abs(p[0] - x), abs(p[1] - y)) <= 1]
        if holders and own_id > min(holders):
            self.reason = "rotation"

    def admits(self, state: BotState, own_id: int) -> bool:
        if self.reason is not None:
            return False
        if at_counter(state):
            return True
        x, y = _dealer_cell(state)
        occupied = any(max(abs(p[0] - x), abs(p[1] - y)) <= 1 for p in _received_body_cells(state))
        return self.queue.admits(own_id) and not occupied

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


class MerchantCounterQueue:
    """FIFO of received arrivals, never a reservation on another player's body.

    Observe each wire frame so a batch of movements preserves arrival order.
    Staying/moving inside the staging area retains one's place; received exit,
    vanish, map change or epoch replacement removes it. Simultaneous entries
    in an initial snapshot use actor ID. No inventories or decisions are shared.
    """

    def __init__(self) -> None:
        self._identity: tuple[str, int, int] | None = None
        self._arrivals: list[int] = []

    def observe(
        self,
        map_name: str,
        epoch: int,
        own_id: int,
        position: Point,
        *,
        bodies: tuple[Body, ...],
        center: Point,
    ) -> None:
        identity = (map_name, epoch, own_id)
        if identity != self._identity:
            self._arrivals.clear()
            self._identity = identity
        if map_name != "prt_in":
            return
        present = {
            aid
            for aid, point in (*bodies, (own_id, position))
            if max(abs(point[0] - center[0]), abs(point[1] - center[1])) <= 4
        }
        self._arrivals = [aid for aid in self._arrivals if aid in present]
        self._arrivals.extend(sorted(present - set(self._arrivals)))

    def admits(self, own_id: int) -> bool:
        return not self._arrivals or self._arrivals[0] == own_id
