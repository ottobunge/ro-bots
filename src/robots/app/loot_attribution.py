"""Bounded per-client loot attribution; no floor ID is present in an ack.

Dispatch holds one wire lane until an ACK or an own take-item receipt.
Receipts retain each attempt's identity. Success acks match that item and amount; raw refusals use
send order. Identical items also require FIFO: the wire cannot prove a floor
ID. A missed pending match may fall back to an unsettled attempt in the same
presence epoch. Every other ack is explicitly unattributed, never success.
The receipt tail survives map/session boundaries so traces can drain it later.
"""

import logging
from collections import deque
from dataclasses import dataclass

from robots.adapters.native_gameplay import ObservedDamage, ObservedFloorItem, ObservedPickupAck

logger = logging.getLogger(__name__)


@dataclass
class _LootAttempt:
    item: ObservedFloorItem
    after_seq: int
    number: int
    context: dict[str, object]
    present: bool = True
    settled: bool = False
    collected: bool = False
    acknowledged: bool = False


class LootAttribution:
    def __init__(self) -> None:
        self._pending: list[_LootAttempt] = []
        self._attempts: deque[_LootAttempt] = deque(maxlen=128)
        self._rows: deque[dict[str, object]] = deque(maxlen=128)
        self._undrained: deque[dict[str, object]] = deque(maxlen=128)
        self._held: set[tuple[int, str]] = set()
        self._attempt = 0
        self._missing = False
        self._deferred: dict[int, tuple[ObservedFloorItem, str]] = {}

    @property
    def pending(self) -> tuple[ObservedFloorItem, int] | None:
        if not self._pending:
            return None
        attempt = self._pending[0]
        return attempt.item, attempt.after_seq

    @property
    def deferred(self) -> tuple[ObservedFloorItem, ...]:
        return tuple(item for item, _ in self._deferred.values())

    @property
    def rows(self) -> tuple[dict[str, object], ...]:
        return tuple(dict(row) for row in self._rows)

    def drain(self) -> tuple[dict[str, object], ...]:
        rows = tuple(dict(row) for row in self._undrained)
        self._undrained.clear()
        return rows

    def refresh(self, present: set[int]) -> None:
        for attempt in self._attempts:
            attempt.present = attempt.present and attempt.item.floor_item_id in present
        for fid in tuple(self._deferred):
            if fid not in present:
                item, reason = self._deferred.pop(fid)
                self.note(
                    item,
                    "expired",
                    reason="presence_epoch_expired",
                    deferred_reason=reason,
                    tap="pickup_race_expired",
                )
        if present:
            self._missing = False
        self._held = {key for key in self._held if key[0] in present}

    def boundary(self, reason: str) -> None:
        for attempt in self._attempts:
            if not attempt.settled:
                self._note_attempt(attempt, "unconfirmed", reason=reason)
        self._pending.clear()
        self._attempts.clear()
        for item, _ in self._deferred.values():
            self.note(item, "expired", reason=reason)
        self._deferred.clear()
        self._held.clear()
        self._missing = False

    def defer(self, item: ObservedFloorItem, reason: str) -> None:
        self._deferred.setdefault(item.floor_item_id, (item, reason))
        key = (item.floor_item_id, reason)
        if key not in self._held:
            self._held.add(key)
            self.note(item, "deferred", reason=reason, tap="drop_unattempted_reason")

    def missing(self) -> None:
        if not self._missing:
            self._missing = True
            self._record({"outcome": "refused", "reason": "no_floor_item", "floor_item_id": None})

    def attempted(
        self, item: ObservedFloorItem, after_seq: int, *, context: dict[str, object]
    ) -> None:
        self._attempt += 1
        if len(self._attempts) == self._attempts.maxlen:
            oldest = self._attempts.popleft()
            if not oldest.settled:
                self._note_attempt(oldest, "unconfirmed", reason="attribution_capacity")
                self._settle(oldest)
        attempt = _LootAttempt(item, after_seq, self._attempt, dict(context))
        self._attempts.append(attempt)
        self._pending.append(attempt)
        deferred = self._deferred.pop(item.floor_item_id, None)
        if deferred is not None:
            reason = {
                "resting": "after_rest",
                "not_standing": "after_rest",
                "awaiting_pickup_ack": "after_ack",
            }.get(deferred[1], "after_walk")
            self._note_attempt(
                attempt,
                "refired",
                reason=f"loot_refired_{reason}",
                deferred_reason=deferred[1],
                tap="pickup_deferred_retried",
            )
        self._note_attempt(attempt, "attempted")

    def consume(self, ack: ObservedPickupAck) -> None:
        attempt = next(
            (a for a in self._attempts if self._ack_candidate(a, ack)),
            None,
        )
        reason = "pending_attempt"
        if attempt is None:
            attempt = self._by_item(ack)
            reason = "attributed_by_item"
        detail: dict[str, object] = {
            "reason_code": ack.raw_result,
            "ack_seq": ack.seq,
            "received_at": ack.at,
            "inventory_index": ack.inventory_index,
            "received_item_id": ack.item_id,
            "received_amount": ack.amount,
        }
        if attempt is None:
            self._record({"outcome": "unattributed_ack", "floor_item_id": None, **detail})
        else:
            if not ack.success and not attempt.present:
                detail["tap"] = "pickup_race_expired"
            self._note_attempt(
                attempt,
                (
                    ("received" if attempt.collected else "succeeded")
                    if ack.success
                    else "refused-by-server"
                ),
                reason=reason,
                **detail,
            )
            attempt.acknowledged = True
            self._settle(attempt)

    def _ack_candidate(self, attempt: _LootAttempt, ack: ObservedPickupAck) -> bool:
        return (
            not attempt.acknowledged
            and (attempt in self._pending or (attempt.collected and ack.success))
            and ack.seq > attempt.after_seq
            and (not ack.success or self._matches(attempt, ack))
        )

    def observe_take(self, hit: ObservedDamage, own_id: int) -> None:
        """clif_takeitem confirms collection even when party_share_loot ACKs a peer.

        This frees the wire lane, never credits inventory. A later matching
        inventory ACK has its own receipt and cannot count collection twice.
        """
        if hit.damage_type != 1 or hit.source_id not in (own_id, (-own_id) & 0xFFFFFFFF):
            return
        attempt = next(
            (
                a
                for a in self._pending
                if a.item.floor_item_id == hit.target_id and hit.seq > a.after_seq
            ),
            None,
        )
        if attempt is not None:
            attempt.collected = True
            self._note_attempt(attempt, "collected", reason="received_takeitem", sequence=hit.seq)
            self._settle(attempt)

    @staticmethod
    def _matches(attempt: _LootAttempt, ack: ObservedPickupAck) -> bool:
        return ack.item_id == attempt.item.item_id and (
            not ack.success or ack.amount == attempt.item.amount
        )

    def _by_item(self, ack: ObservedPickupAck) -> _LootAttempt | None:
        if ack.item_id == 0:
            return None
        return next(
            (
                a
                for a in self._attempts
                if not a.settled
                and a.present
                and ack.seq > a.item.position.seq
                and self._matches(a, ack)
            ),
            None,
        )

    def _settle(self, attempt: _LootAttempt) -> None:
        attempt.settled = True
        if attempt in self._pending:
            self._pending.remove(attempt)

    def _note_attempt(self, attempt: _LootAttempt, outcome: str, **detail: object) -> None:
        self.note(
            attempt.item,
            outcome,
            **{
                **attempt.context,
                "attempt": attempt.number,
                "sent_after_seq": attempt.after_seq,
                **detail,
            },
        )

    def note(self, item: ObservedFloorItem, outcome: str, **detail: object) -> None:
        row: dict[str, object] = {
            "attempt": self._attempt,
            "floor_item_id": item.floor_item_id,
            "item_id": item.item_id,
            "drop_seq": item.position.seq,
            "drop_x": item.position.x,
            "drop_y": item.position.y,
            "outcome": outcome,
            **detail,
        }
        self._record(row)

    def _record(self, row: dict[str, object]) -> None:
        self._rows.append(row)
        self._undrained.append(row)
        logger.warning("loot-debug: pickup %s %s", row["outcome"], row)
