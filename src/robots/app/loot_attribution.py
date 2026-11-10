"""Bounded per-client loot attribution; no floor ID is present in an ack.

Only one pickup may be outstanding. A success must match its item; a raw
failure can then refer to that sole attempt. A missing ack holds this lane
until a received map/session boundary, rather than guessing success or retrying.
The receipt tail survives those boundaries so the trace can drain it later.
"""

import logging
from collections import deque

from robots.adapters.native_gameplay import ObservedFloorItem, ObservedPickupAck

logger = logging.getLogger(__name__)


class LootAttribution:
    def __init__(self) -> None:
        self.pending: tuple[ObservedFloorItem, int] | None = None
        self._rows: deque[dict[str, object]] = deque(maxlen=128)
        self._undrained: deque[dict[str, object]] = deque(maxlen=128)
        self._held: set[tuple[int, str]] = set()
        self._attempt = 0
        self._missing = False
        self._attempt_context: dict[str, object] = {}

    @property
    def rows(self) -> tuple[dict[str, object], ...]:
        return tuple(dict(row) for row in self._rows)

    def drain(self) -> tuple[dict[str, object], ...]:
        rows = tuple(dict(row) for row in self._undrained)
        self._undrained.clear()
        return rows

    def refresh(self, present: set[int]) -> None:
        if present:
            self._missing = False
        self._held = {key for key in self._held if key[0] in present}

    def boundary(self, reason: str) -> None:
        if self.pending is not None:
            self.note(self.pending[0], "unconfirmed", reason=reason)
        self.pending = None
        self._held.clear()
        self._missing = False

    def defer(self, item: ObservedFloorItem, reason: str) -> None:
        key = (item.floor_item_id, reason)
        if key not in self._held:
            self._held.add(key)
            self.note(item, "deferred", reason=reason)

    def missing(self) -> None:
        if not self._missing:
            self._missing = True
            self._record({"outcome": "refused", "reason": "no_floor_item", "floor_item_id": None})

    def attempted(
        self, item: ObservedFloorItem, after_seq: int, *, context: dict[str, object]
    ) -> None:
        self._attempt += 1
        self.pending = (item, after_seq)
        self._attempt_context = dict(context)
        self.note(item, "attempted", sent_after_seq=after_seq)

    def consume(self, ack: ObservedPickupAck) -> None:
        if self.pending is None or ack.seq <= self.pending[1]:
            return
        item = self.pending[0]
        if ack.success and (ack.item_id != item.item_id or ack.amount != item.amount):
            # Shop, reward and party acquisitions use the same packet. Keep
            # observing inventory, but do not label an unrelated item as loot.
            return
        self.note(
            item,
            "succeeded" if ack.success else "refused-by-server",
            reason_code=ack.raw_result,
            ack_seq=ack.seq,
            received_at=ack.at,
            inventory_index=ack.inventory_index,
            received_item_id=ack.item_id,
            received_amount=ack.amount,
        )
        self.pending = None

    def note(self, item: ObservedFloorItem, outcome: str, **detail: object) -> None:
        row: dict[str, object] = {
            "attempt": self._attempt,
            "floor_item_id": item.floor_item_id,
            "item_id": item.item_id,
            "drop_seq": item.position.seq,
            "drop_x": item.position.x,
            "drop_y": item.position.y,
            "outcome": outcome,
            **(
                self._attempt_context
                if self.pending is not None and self.pending[0] == item
                else {}
            ),
            **detail,
        }
        self._record(row)

    def _record(self, row: dict[str, object]) -> None:
        self._rows.append(row)
        self._undrained.append(row)
        logger.warning("loot-debug: pickup %s %s", row["outcome"], row)
