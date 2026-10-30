"""Owner-thread, bounded read-only shop observer. No sends or policy timers."""

import logging

from robots.adapters.native_shop import decode_currency, decode_shop_offer
from robots.domain.actions import NpcShopBuySelection
from robots.domain.npc import NpcDialogue
from robots.domain.shop import ReceivedShopOffer, ReceivedShopRow, ReceivedZeny

logger = logging.getLogger(__name__)


class NativeShopContext:
    def __init__(self) -> None:
        self.offer: ReceivedShopOffer | None = None
        self.currency: ReceivedZeny | None = None
        self._identity: tuple[object, ...] | None = None
        self._currency_after = 0
        self._currency_blocked = False
        self._binding: tuple[object, ...] | None = None
        self._issued: NpcShopBuySelection | None = None
        self._after = 0
        self._deadline = 0.0
        self._sent_at = 0.0
        self._consumed = False

    @property
    def balance(self) -> int | None:
        return self.currency.balance if self.currency is not None else None

    @property
    def actor_id(self) -> int | None:
        return self._issued.npc_id if self._issued is not None else None

    def invalidate(self) -> None:
        self.currency = None
        self._currency_blocked = True
        self.invalidate_offer()

    def invalidate_offer(self) -> None:
        self.offer = None
        self._issued = None

    def bind(self, binding: tuple[object, ...], identity: tuple[object, ...], tail: int) -> None:
        changed = self._binding is not None and not all(
            a is b for a, b in zip(self._binding, binding, strict=True)
        )
        if changed or (self._identity is not None and self._identity != identity):
            self.invalidate()
        if self._currency_blocked:
            self._currency_after = tail
            self._currency_blocked = False
        self._binding, self._identity = binding, identity

    def issued(
        self, action: NpcShopBuySelection, after: int, sent_at: float, deadline: float
    ) -> None:
        self.invalidate_offer()
        self._issued = NpcShopBuySelection(
            action.npc_id,
            action.epoch,
            action.prompt_sequence,
            action.map_name,
            action.opened_sequence,
        )
        self._after, self._sent_at, self._deadline = after, sent_at, deadline
        self._consumed = False

    def check(self, dialog: NpcDialogue | None, ready: bool, now: float) -> None:
        action = self._issued
        if action is None:
            return
        if not ready or dialog is None or now >= self._deadline:
            self.invalidate_offer()
            return
        if not all(
            (
                dialog.stage == "waiting",
                dialog.sequence == action.prompt_sequence,
                dialog.opened_sequence == action.opened_sequence,
                dialog.map_name == action.map_name,
                dialog.epoch == action.epoch,
                dialog.npc_id == action.npc_id,
            )
        ):
            self.invalidate_offer()

    def consume(self, frame: tuple[int, float, int, bytes], epoch: int) -> None:
        self._consume_currency(frame, epoch)
        self._consume_offer(frame)

    def _consume_currency(self, frame: tuple[int, float, int, bytes], epoch: int) -> None:
        seq, at, pid, raw = frame
        if pid in (0xB0, 0xB1) and seq > self._currency_after:
            try:
                received = decode_currency(raw)
            except ValueError:
                self.currency = None
            else:
                if received is not None and received.balance is not None:
                    self.currency = ReceivedZeny(received.balance, epoch, seq, at)
            self._currency_after = seq

    def _consume_offer(self, frame: tuple[int, float, int, bytes]) -> None:
        seq, at, pid, raw = frame
        action = self._issued
        if pid != 0xC6 or action is None or seq <= self._after or self._consumed:
            return
        self._consumed = True
        if not self._sent_at <= at < self._deadline:
            # e2e-45 diagnostic tap: a C6 outside the issue window is one of
            # the two silent drop points - name it (fails open, bounded line)
            logger.warning(
                "shop-debug: C6 outside the issue window (seq=%s sent_at=%s deadline=%s)",
                seq,
                self._sent_at,
                self._deadline,
            )
            self.invalidate_offer()
            return
        try:
            decoded = decode_shop_offer(raw)
        except ValueError:
            # e2e-45 diagnostic tap: the decode drop - the raw frame is the
            # evidence (hex, bounded to the first 64 bytes)
            logger.warning(
                "shop-debug: C6 decode failed (%d bytes): %s",
                len(raw),
                raw[:64].hex(),
            )
            self.invalidate_offer()
            return
        self.offer = ReceivedShopOffer(
            rows=tuple(
                ReceivedShopRow(r.price, r.discount_price, r.item_type, r.item_id)
                for r in decoded.rows
            ),
            npc_id=action.npc_id,
            epoch=action.epoch,
            map_name=action.map_name,
            opened_sequence=action.opened_sequence,
            prompt_sequence=action.prompt_sequence,
            receipt_sequence=seq,
            observed_at=at,
            deadline=self._deadline,
        )
