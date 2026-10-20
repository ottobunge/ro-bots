"""Finite owner-thread ordinary Knife exchange, not planner or live authority.

C8 has no price cap/actor/nonce. Admission relies on explicitly trusted stable
loaded-shop facts. CA0 can follow debit and a failed add; never call that acquired.
No retries, refunds, invented ACKs or hidden-world readers.
"""

from dataclasses import dataclass, replace

from robots.adapters.native_capacity import finite_capacity_time
from robots.adapters.native_shop import PurchaseEntry, decode_purchase_result, encode_purchase
from robots.domain.actions import NpcShopPurchase
from robots.domain.capacity import ReceivedCapacity
from robots.domain.shop import (
    QualifiedShopItem,
    ReceivedShopOffer,
    ReceivedZeny,
    ShopPurchaseProgress,
)

Stock = tuple[tuple[int, int, int], ...]
Owner = tuple[object, ...]


def _integer(value: object, low: int = 1, high: int = 0x7FFFFFFF) -> bool:
    return type(value) is int and low <= value <= high


def _same_owner(left: Owner, right: Owner) -> bool:
    return len(left) == len(right) and all(a is b for a, b in zip(left, right, strict=True))


@dataclass(frozen=True)
class PurchaseAdmission:
    owner: Owner
    offer: ReceivedShopOffer
    currency: ReceivedZeny | None
    capacity: ReceivedCapacity | None
    stock: Stock | None
    slots: int | None
    account_id: int
    character_id: int
    now: float


def _facts_match(facts: QualifiedShopItem, context: PurchaseAdmission) -> bool:
    offer = context.offer
    return all(
        (
            type(facts.source_id) is str and 0 < len(facts.source_id) <= 128,
            _integer(facts.account_id) and facts.account_id == context.account_id,
            _integer(facts.character_id) and facts.character_id == context.character_id,
            _integer(facts.epoch) and facts.epoch == offer.epoch,
            _integer(facts.npc_id) and facts.npc_id == offer.npc_id,
            type(facts.map_name) is str and facts.map_name == offer.map_name,
            _integer(facts.actual_item_id) and facts.actual_item_id == 1201,
            _integer(facts.client_item_id) and facts.client_item_id == 1201,
            facts.ordinary_shop is True,
            facts.nonstackable is True,
            _integer(facts.stable_price),
            _integer(facts.stable_discount_price),
            finite_capacity_time(facts.valid_until) and context.now < facts.valid_until,
        )
    )


def _fresh(at: float, now: float) -> bool:
    return finite_capacity_time(at) and 0 <= now - at < 5.0


def _resources_fit(context: PurchaseAdmission, facts: QualifiedShopItem, budget: int) -> bool:
    currency, capacity = context.currency, context.capacity
    if currency is None or capacity is None:
        return False
    return all(
        (
            _integer(budget) and facts.stable_discount_price <= budget,
            _integer(currency.balance, 0) and currency.balance >= facts.stable_discount_price,
            currency.epoch == context.offer.epoch and _fresh(currency.observed_at, context.now),
            _capacity_fits(capacity, context, facts),
        )
    )


def _capacity_fits(
    capacity: ReceivedCapacity, context: PurchaseAdmission, facts: QualifiedShopItem
) -> bool:
    if capacity.weight is None or capacity.max_weight is None:
        return False
    weight, maximum = capacity.weight, capacity.max_weight
    return all(
        (
            capacity.epoch == context.offer.epoch,
            capacity.account_id == context.account_id
            and capacity.character_id == context.character_id,
            _fresh(weight.observed_at, context.now) and _fresh(maximum.observed_at, context.now),
            _integer(weight.value, 0) and _integer(maximum.value, 0),
            _integer(facts.loaded_weight, 0),
            type(facts.loaded_weight) is int
            and weight.value + facts.loaded_weight <= maximum.value,
            capacity.inventory_changed_sequence is None
            or weight.receipt_sequence >= capacity.inventory_changed_sequence,
        )
    )


def _stock_fits(context: PurchaseAdmission) -> bool:
    stock, slots = context.stock, context.slots
    if stock is None or not _integer(slots, 1, 100):
        return False
    return all(
        (
            type(slots) is int and len(stock) < slots,
            all(
                _integer(index, 2, 101) and _integer(item) and _integer(count)
                for index, item, count in stock
            ),
            all(item != 1201 or count == 1 for _, item, count in stock),
        )
    )


class NativePurchase:
    """One owner-local intent, consumed even on denial/uncertain transport."""

    def __init__(self) -> None:
        self.progress: ShopPurchaseProgress | None = None
        self._facts: QualifiedShopItem | None = None
        self._owner: Owner = ()
        self._offer: ReceivedShopOffer | None = None
        self._minted: NpcShopPurchase | None = None
        self._expected: NpcShopPurchase | None = None
        self._consumed = False
        self._after = 0
        self._sent_at = 0.0
        self._stock: Stock = ()
        self._last_index = 1
        self._index: int | None = None
        self._expected_balance: int | None = None
        self._successful_send = False

    def bind(self, facts: QualifiedShopItem, context: PurchaseAdmission | None) -> bool:
        self._facts = None
        if (
            type(facts) is not QualifiedShopItem
            or context is None
            or not _facts_match(facts, context)
        ):
            return False
        self._facts = replace(facts)
        self._owner, self._offer = context.owner, context.offer
        return True

    def _eligible(self, context: PurchaseAdmission | None, budget: int) -> bool:
        facts = self._facts
        if facts is None or context is None:
            return False
        rows = tuple(row for row in context.offer.rows if row.item_id == 1201)
        return all(
            (
                _same_owner(self._owner, context.owner),
                self._offer is context.offer,
                _facts_match(facts, context),
                finite_capacity_time(context.now) and context.now < context.offer.deadline,
                len(rows) == 1
                and (rows[0].price, rows[0].discount_price, rows[0].item_type)
                == (facts.stable_price, facts.stable_discount_price, 4),
                _resources_fit(context, facts, budget),
                _stock_fits(context),
            )
        )

    def mint(self, context: PurchaseAdmission | None, maximum_zeny: int) -> NpcShopPurchase | None:
        if self._consumed or not self._eligible(context, maximum_zeny) or context is None:
            return None
        if self._minted is not None:
            return self._minted
        offer = context.offer
        self._minted = NpcShopPurchase(
            offer.npc_id,
            offer.epoch,
            offer.prompt_sequence,
            offer.map_name,
            offer.opened_sequence,
            offer.receipt_sequence,
            maximum_zeny,
        )
        self._expected = replace(self._minted)
        return self._minted

    def prepare(self, action: NpcShopPurchase, context: PurchaseAdmission | None) -> bytes | None:
        if self._consumed or action is not self._minted:
            return None
        self._consumed = True
        self.progress = ShopPurchaseProgress(action, "incomplete", "dispatch denied")
        if not self._valid_action(action) or not self._eligible(context, action.maximum_zeny):
            return None
        if (
            context is None
            or context.stock is None
            or context.currency is None
            or context.slots is None
            or self._facts is None
        ):
            return None
        self._stock = context.stock
        self._last_index = context.slots + 1
        self._expected_balance = context.currency.balance - self._facts.stable_discount_price
        self._sent_at = context.now
        return encode_purchase((PurchaseEntry(1201, 1),))

    def _valid_action(self, action: NpcShopPurchase) -> bool:
        return all(
            (
                action == self._expected,
                all(
                    _integer(v)
                    for v in (
                        action.npc_id,
                        action.epoch,
                        action.prompt_sequence,
                        action.opened_sequence,
                        action.offer_sequence,
                        action.maximum_zeny,
                        action.item_id,
                        action.quantity,
                    )
                ),
                action.item_id == 1201 and action.quantity == 1,
            )
        )

    def sending(self, after: int) -> None:
        """Consume/reserve before transport; raising cannot rearm or promote receipts."""
        self._after = after
        if self.progress is not None:
            self.progress = replace(self.progress, reason="send outcome uncertain")

    def issued(self, after: int) -> None:
        self._after = after
        self._successful_send = True
        if self.progress is not None:
            self.progress = replace(
                self.progress, status="issued", reason="awaiting acquisition and CA"
            )

    def _context_matches(self, context: PurchaseAdmission) -> bool:
        return _same_owner(self._owner, context.owner) and self._offer is context.offer

    def _context_loss(self, context: PurchaseAdmission | None) -> str | None:
        if context is None or not self._context_matches(context):
            return "context lost"
        if not finite_capacity_time(context.now) or context.now >= context.offer.deadline:
            return "exchange expired"
        return None

    def _retire_pre_dispatch(self, reason: str) -> None:
        self._consumed = True
        self._facts = None
        if self._minted is not None:
            self.progress = ShopPurchaseProgress(self._minted, "incomplete", reason)

    def _check_pre_dispatch(self, context: PurchaseAdmission | None) -> None:
        if self._facts is None and self._minted is None:
            return
        reason = self._context_loss(context)
        if reason is not None:
            self._retire_pre_dispatch(reason)

    def check(self, context: PurchaseAdmission | None) -> None:
        progress = self.progress
        if progress is None:
            self._check_pre_dispatch(context)
            return
        if progress.status != "issued":
            return
        reason = self._context_loss(context)
        if reason is not None:
            self.progress = replace(progress, status="incomplete", reason=reason)

    def consume(self, frame: tuple[int, float, int, bytes], stock: Stock | None) -> None:
        progress = self.progress
        if progress is None or not self._successful_send or progress.ca_result is not None:
            return
        seq, at, pid, raw = frame
        if seq <= self._after:
            return
        if self._offer is None or not self._sent_at <= at < self._offer.deadline:
            self.progress = replace(
                progress, status="incomplete", reason="receipt outside exchange"
            )
            return
        if progress.status == "incomplete":
            if pid == 0xCA and progress.reason in ("ambiguous acquisition", "unexpected debit"):
                self.progress = replace(progress, ca_result=decode_purchase_result(raw).result)
            return
        self._consume_issued(pid, raw, stock)

    def _consume_issued(self, pid: int, raw: bytes, stock: Stock | None) -> None:
        progress = self.progress
        if progress is None:
            return
        if pid == 0xB1 and int.from_bytes(raw[2:4], "little") == 20:
            if int.from_bytes(raw[4:8], "little", signed=True) != self._expected_balance:
                self.progress = replace(progress, status="incomplete", reason="unexpected debit")
        elif pid == 0xA37:
            self._acquisition(raw, stock)
        elif pid == 0xCA:
            self._result(raw, stock)

    def _acquisition(self, raw: bytes, stock: Stock | None) -> None:
        index = int.from_bytes(raw[2:4], "little")
        addition = (index, 1201, 1)
        expected = tuple(sorted((*self._stock, addition)))
        valid = all(
            (
                len(raw) == 59 and raw[24] == 0 and raw[25] == 4,
                int.from_bytes(raw[4:6], "little", signed=True) == 1,
                int.from_bytes(raw[6:8], "little") == 1201,
                _integer(index, 2, self._last_index),
                index not in {row[0] for row in self._stock},
                self._index is None and stock == expected,
            )
        )
        if valid:
            self._index = index
        elif self.progress is not None:
            self.progress = replace(
                self.progress, status="incomplete", reason="ambiguous acquisition"
            )

    def _result(self, raw: bytes, stock: Stock | None) -> None:
        progress = self.progress
        if progress is None:
            return
        result = decode_purchase_result(raw).result
        if result in (1, 2, 3):
            self.progress = replace(
                progress, status="rejected", reason="server rejection", ca_result=result
            )
            return
        if result == 0 and self._index is not None:
            expected = tuple(sorted((*self._stock, (self._index, 1201, 1))))
            if stock == expected:
                self.progress = replace(
                    progress,
                    status="acquired",
                    reason="matching acquisition and CA0",
                    ca_result=result,
                    inventory_index=self._index,
                )
                return
        self.progress = replace(
            progress,
            status="incomplete",
            reason="CA without reconciled acquisition",
            ca_result=result,
        )
