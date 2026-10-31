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
        self.invalidate_offer("identity-changed")

    def invalidate_offer(self, reason: str = "unspecified") -> None:
        # e2e-48 lifecycle tap: an invalidation only matters when a binding or
        # an offer existed - log WHAT died and WHY (fails open, bounded)
        if self._issued is not None or self.offer is not None:
            logger.warning(
                "shop-debug: offer invalidated (%s) had_issued=%s had_offer=%s",
                reason,
                self._issued is not None,
                self.offer is not None,
            )
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
        self.invalidate_offer("re-issued")
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
            self.invalidate_offer(
                f"not-ready={not ready} dialog-none={dialog is None}"
                f" past-deadline={now >= self._deadline}"
            )
            return
        if not all(
            (
                dialog.stage == "waiting",
                # the prompt_sequence term is deliberately absent: the dealer's
                # repeat C4 dealtype marker (leg 46, 0.5ms before the C5)
                # re-bumps dialog.sequence after the C5 moved the stage to
                # "waiting", and an invalidation here killed the in-flight C6
                # binding (_issued None -> the C6 dropped silently). A REAL new
                # prompt still invalidates: it changes the stage (menu/text/
                # unsupported_*) or the opened dialogue, both still guarded.
                dialog.opened_sequence == action.opened_sequence,
                dialog.map_name == action.map_name,
                dialog.epoch == action.epoch,
                dialog.npc_id == action.npc_id,
            )
        ):
            self.invalidate_offer(
                f"guard-failed stage={dialog.stage} opened={dialog.opened_sequence}"
                f"/{action.opened_sequence} map={dialog.map_name == action.map_name}"
                f" epoch={dialog.epoch == action.epoch} npc={dialog.npc_id == action.npc_id}"
            )

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
        if pid == 0xC6:
            # e2e-45 diagnostic tap: EVERY seen C6 names its guard state -
            # leg 46 showed zero tap lines with the purchase still missing,
            # so the drop may sit in these early guards themselves
            logger.warning(
                "shop-debug: C6 seen (seq=%s issued=%s after=%s consumed=%s rows=%d)",
                seq,
                action is not None,
                self._after,
                self._consumed,
                len(raw),
            )
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
            self.invalidate_offer("c6-outside-window")
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
            self.invalidate_offer("c6-decode-failed")
            return
        logger.warning(
            "shop-debug: C6 BOUND (seq=%s rows=%d npc=%s)", seq, len(decoded.rows), action.npc_id
        )
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
