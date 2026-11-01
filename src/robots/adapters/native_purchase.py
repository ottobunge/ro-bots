"""Finite owner-thread ordinary Knife exchange, not planner or live authority.

C8 has no price cap/actor/nonce. Admission relies on explicitly trusted stable
loaded-shop facts. CA0 can follow debit and a failed add; never call that acquired.
No retries, refunds, invented ACKs or hidden-world readers.
"""

import logging
from dataclasses import dataclass, replace
from typing import NamedTuple

from robots.adapters.native_capacity import finite_capacity_time
from robots.adapters.native_shop import PurchaseEntry, decode_purchase_result, encode_purchase
from robots.domain.actions import NpcShopPurchase
from robots.domain.capacity import ReceivedCapacity, ReceivedCapacityValue
from robots.domain.shop import (
    QualifiedShopItem,
    ReceivedShopOffer,
    ReceivedShopRow,
    ReceivedZeny,
    ShopPurchaseProgress,
)

Stock = tuple[tuple[int, int, int], ...]
Owner = tuple[object, ...]

logger = logging.getLogger(__name__)

# The login-stamped wallet facts' freshness window (the 0xB0 24/25 pair and
# the SP_ZENY receipt share it); the capacity gate names it in its refusal tap.
_FRESH_WINDOW = 5.0


class _Term(NamedTuple):
    """One gate predicate: its label, its verdict and the compared values."""

    label: str
    passed: bool
    values: str


def _render_terms(terms: tuple[_Term, ...]) -> str:
    """Join term verdicts into the one-line `label=verdict(values)` shape."""
    return " ".join(f"{term.label}={term.passed}({term.values})" for term in terms)


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


# Once-per-bound-offer memo for the freshness refusal tap: the same
# login-stamped refusal reads identically on every ~2s decide tick (144
# identical lines in leg 57), so one line per distinct offer identity (the
# owner's account/character plus the exchange epoch/npc/map/opening and the
# C6 receipt sequence) is enough. Offer receipts arrive rarely; the set stays
# a handful of small tuples for a process lifetime.
_FRESHNESS_TAPPED: set[tuple[object, ...]] = set()


def _offer_identity(context: PurchaseAdmission) -> tuple[object, ...]:
    offer = context.offer
    return (
        context.account_id,
        context.character_id,
        offer.epoch,
        offer.npc_id,
        offer.map_name,
        offer.opened_sequence,
        offer.receipt_sequence,
    )


def _tap_capacity_freshness(
    context: PurchaseAdmission, weight: ReceivedCapacityValue, maximum: ReceivedCapacityValue
) -> None:
    identity = _offer_identity(context)
    if identity in _FRESHNESS_TAPPED:
        return
    _FRESHNESS_TAPPED.add(identity)
    # Tap-before-fix doctrine: name the raw login-stamp refusal with the
    # observed ages, whether or not the bound-offer hold below keeps the
    # mint alive. Fails open, bounded, never behavior.
    logger.warning(
        "shop-debug: capacity freshness gate refused the login-stamped pair"
        " (weight_age=%.1fs max_age=%.1fs window=%.1fs) held_by_bound_offer=%s",
        context.now - weight.observed_at,
        context.now - maximum.observed_at,
        _FRESH_WINDOW,
        context.offer is not None,
    )


def _facts_terms(facts: QualifiedShopItem, context: PurchaseAdmission) -> tuple[_Term, ...]:
    offer = context.offer
    return (
        _Term(
            "f_src",
            type(facts.source_id) is str and 0 < len(facts.source_id) <= 128,
            facts.source_id[:24],
        ),
        _Term(
            "f_acct",
            _integer(facts.account_id) and facts.account_id == context.account_id,
            f"{facts.account_id}/{context.account_id}",
        ),
        _Term(
            "f_char",
            _integer(facts.character_id) and facts.character_id == context.character_id,
            f"{facts.character_id}/{context.character_id}",
        ),
        _Term(
            "f_epoch",
            _integer(facts.epoch) and facts.epoch == offer.epoch,
            f"{facts.epoch}/{offer.epoch}",
        ),
        _Term(
            "f_npc",
            _integer(facts.npc_id) and facts.npc_id == offer.npc_id,
            f"{facts.npc_id}/{offer.npc_id}",
        ),
        _Term(
            "f_map",
            type(facts.map_name) is str and facts.map_name == offer.map_name,
            f"{facts.map_name}/{offer.map_name}",
        ),
        _Term(
            "f_item",
            _integer(facts.actual_item_id) and facts.actual_item_id == 1201,
            f"{facts.actual_item_id}/1201",
        ),
        _Term(
            "f_client",
            _integer(facts.client_item_id) and facts.client_item_id == 1201,
            f"{facts.client_item_id}/1201",
        ),
        _Term("f_ordinary", facts.ordinary_shop is True, f"{facts.ordinary_shop}"),
        _Term("f_nonstack", facts.nonstackable is True, f"{facts.nonstackable}"),
        _Term("f_price", _integer(facts.stable_price), f"{facts.stable_price}"),
        _Term("f_disc", _integer(facts.stable_discount_price), f"{facts.stable_discount_price}"),
        _Term(
            "f_valid",
            finite_capacity_time(facts.valid_until) and context.now < facts.valid_until,
            f"until={facts.valid_until} now={context.now}",
        ),
    )


def _facts_match(facts: QualifiedShopItem, context: PurchaseAdmission) -> bool:
    return all(term.passed for term in _facts_terms(facts, context))


def _fresh(at: float, now: float) -> bool:
    return finite_capacity_time(at) and 0 <= now - at < _FRESH_WINDOW


def _resources_terms(
    currency: ReceivedZeny, context: PurchaseAdmission, facts: QualifiedShopItem, budget: int
) -> tuple[_Term, ...]:
    offer = context.offer
    return (
        _Term(
            "budget",
            _integer(budget) and facts.stable_discount_price <= budget,
            f"budget={budget} price={facts.stable_discount_price}",
        ),
        _Term(
            "balance",
            _integer(currency.balance, 0) and currency.balance >= facts.stable_discount_price,
            f"balance={currency.balance} price={facts.stable_discount_price}",
        ),
        _Term(
            "currency",
            currency.epoch == offer.epoch and _fresh(currency.observed_at, context.now),
            f"epoch {currency.epoch}/{offer.epoch} age={context.now - currency.observed_at:.1f}s",
        ),
    )


def _capacity_terms(
    capacity: ReceivedCapacity,
    context: PurchaseAdmission,
    facts: QualifiedShopItem,
    weight: ReceivedCapacityValue,
    maximum: ReceivedCapacityValue,
) -> tuple[_Term, ...]:
    fresh = _fresh(weight.observed_at, context.now) and _fresh(maximum.observed_at, context.now)
    return (
        _Term(
            "epoch",
            capacity.epoch == context.offer.epoch,
            f"{capacity.epoch}/{context.offer.epoch}",
        ),
        _Term(
            "acct",
            capacity.account_id == context.account_id,
            f"{capacity.account_id}/{context.account_id}",
        ),
        _Term(
            "char",
            capacity.character_id == context.character_id,
            f"{capacity.character_id}/{context.character_id}",
        ),
        _Term(
            "cap_held",
            fresh or context.offer is not None,
            f"w_age={context.now - weight.observed_at:.1f}s"
            f" max_age={context.now - maximum.observed_at:.1f}s window={_FRESH_WINDOW}s",
        ),
        _Term(
            "ints",
            _integer(weight.value, 0) and _integer(maximum.value, 0),
            f"weight={weight.value} max={maximum.value}",
        ),
        _Term("loaded_int", _integer(facts.loaded_weight, 0), f"loaded={facts.loaded_weight}"),
        _Term(
            "loaded_w",
            type(facts.loaded_weight) is int
            and weight.value + facts.loaded_weight <= maximum.value,
            f"{weight.value}+{facts.loaded_weight}<={maximum.value}",
        ),
        _Term(
            "inv_seq",
            capacity.inventory_changed_sequence is None
            or weight.receipt_sequence >= capacity.inventory_changed_sequence,
            f"receipt={weight.receipt_sequence} changed={capacity.inventory_changed_sequence}",
        ),
    )


def _capacity_checked(
    capacity: ReceivedCapacity, context: PurchaseAdmission, facts: QualifiedShopItem
) -> tuple[_Term, ...]:
    if capacity.weight is None or capacity.max_weight is None:
        return (
            _Term(
                "capacity",
                False,
                f"weight={capacity.weight is not None} max={capacity.max_weight is not None}",
            ),
        )
    weight, maximum = capacity.weight, capacity.max_weight
    fresh = _fresh(weight.observed_at, context.now) and _fresh(maximum.observed_at, context.now)
    if not fresh:
        _tap_capacity_freshness(context, weight, maximum)
    return _capacity_terms(capacity, context, facts, weight, maximum)


def _capacity_fits(
    capacity: ReceivedCapacity, context: PurchaseAdmission, facts: QualifiedShopItem
) -> bool:
    return all(term.passed for term in _capacity_checked(capacity, context, facts))


def _resources_checked(
    context: PurchaseAdmission, facts: QualifiedShopItem, budget: int
) -> tuple[_Term, ...]:
    currency, capacity = context.currency, context.capacity
    if currency is None or capacity is None:
        return (
            _Term(
                "resources",
                False,
                f"currency={currency is not None} capacity={capacity is not None}",
            ),
        )
    return (
        *_resources_terms(currency, context, facts, budget),
        *_capacity_checked(capacity, context, facts),
    )


def _resources_fit(context: PurchaseAdmission, facts: QualifiedShopItem, budget: int) -> bool:
    return all(term.passed for term in _resources_checked(context, facts, budget))


def _acquisition_bound(slots: int | None) -> int:
    """The acquisition-index bound: slots+1 when the allowance is received
    (the wire overrides when it speaks), the absolute 100-slot pin cap
    (indices 2..101) while it is unknown — never a zero free-slot read."""
    return 101 if slots is None else slots + 1


def _allowance_received(slots: int | None) -> bool:
    """The slots-unknown law (leg 58): an absent allowance (None) is UNKNOWN
    and passes; a RECEIVED value must be a real slot count (fail-closed on
    received-bad data, never a zero free-slot read)."""
    return slots is None or _integer(slots, 1, 100)


def _stock_rows_integer(stock: Stock) -> bool:
    return all(
        _integer(index, 2, 101) and _integer(item) and _integer(count)
        for index, item, count in stock
    )


def _stock_knife_unique(stock: Stock) -> bool:
    return all(item != 1201 or count == 1 for _, item, count in stock)


def _stock_checked(context: PurchaseAdmission) -> tuple[_Term, ...]:
    stock, slots = context.stock, context.slots
    # The slots-unknown law (leg 58): the allowance facts gate nothing until
    # they exist (the wire overrides when it speaks); stock=True alone passes.
    if stock is None or not _allowance_received(slots):
        return (_Term("stock", False, f"stock={stock is not None} slots={slots}"),)
    return (
        _Term(
            "slots_free",
            slots is None or len(stock) < slots,
            f"{len(stock)}/{slots}",
        ),
        _Term("rows_int", _stock_rows_integer(stock), f"{len(stock)} rows"),
        _Term(
            "no_knife_dup",
            _stock_knife_unique(stock),
            f"knife rows={sum(1 for _, item, _ in stock if item == 1201)}",
        ),
    )


def _stock_fits(context: PurchaseAdmission) -> bool:
    return all(term.passed for term in _stock_checked(context))


def _row_values(rows: tuple[ReceivedShopRow, ...], facts: QualifiedShopItem) -> str:
    # The received-row law (leg 58): the row's volatile third field is the
    # exchange's own value, rendered for evidence only — the template supplies
    # IDENTITY and takes price/discount FROM the received row, so the seam
    # never re-checks the template's db-pin type against the row.
    received = f"({rows[0].price},{rows[0].discount_price},{rows[0].item_type})" if rows else "none"
    return f"{received} v ({facts.stable_price},{facts.stable_discount_price}) rows={len(rows)}"


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

    @property
    def has_facts(self) -> bool:
        return self._facts is not None

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

    def _verdict(self, context: PurchaseAdmission | None, budget: int) -> tuple[_Term, ...]:
        """Every consumption-seam predicate as a named term, in gate order.

        The `all(...)` over the returned terms is exactly the gate's historic
        conjunction: each term is the identical expression the gates used, the
        nested _resources_fit/_capacity_fits sets are flattened (a flattened
        conjunction equals the nested one) and every element of the tuple is
        evaluated regardless of the verdict, so the freshness tap still fires.
        """
        facts = self._facts
        if facts is None or context is None:
            return (
                _Term(
                    "verdict",
                    False,
                    f"facts={facts is not None} context={context is not None}",
                ),
            )
        rows = tuple(row for row in context.offer.rows if row.item_id == 1201)
        terms = (
            _Term(
                "owner",
                _same_owner(self._owner, context.owner),
                f"len {len(self._owner)}/{len(context.owner)}",
            ),
            _Term(
                "offer",
                self._offer is context.offer,
                f"receipt={context.offer.receipt_sequence}",
            ),
            *_facts_terms(facts, context),
            _Term(
                "deadline",
                finite_capacity_time(context.now) and context.now < context.offer.deadline,
                f"now={context.now} deadline={context.offer.deadline}",
            ),
            # The received-row law (leg 58): identity by nameid (the filtered
            # 1201 rows), price/discount re-checked against the row-derived
            # facts; the row's volatile third field is the exchange's own and
            # is never demanded equal to the template's db-pin (4).
            _Term(
                "row",
                len(rows) == 1
                and (rows[0].price, rows[0].discount_price)
                == (facts.stable_price, facts.stable_discount_price),
                _row_values(rows, facts),
            ),
            *_resources_checked(context, facts, budget),
            *_stock_checked(context),
        )
        return (*terms, _Term("eligible", all(term.passed for term in terms), "verdict"))

    def _eligible(self, context: PurchaseAdmission | None, budget: int) -> bool:
        return all(term.passed for term in self._verdict(context, budget))

    def mint(self, context: PurchaseAdmission | None, maximum_zeny: int) -> NpcShopPurchase | None:
        if self._consumed or context is None:
            return None
        terms = self._verdict(context, maximum_zeny)
        if context.offer is not None:
            # Term-level verdict tap (tap-before-fix doctrine): one bounded
            # line per consumed mint attempt while the shop CONTEXT carries a
            # bound offer, naming EVERY seam predicate's verdict with both
            # values, so one grep names the starving term. Never behavior.
            logger.warning("shop-debug: mint verdict %s", _render_terms(terms))
        if not all(term.passed for term in terms):
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
            or not _allowance_received(context.slots)
            or self._facts is None
        ):
            return None
        self._stock = context.stock
        self._last_index = _acquisition_bound(context.slots)
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
                progress,
                status="rejected",
                reason="server rejection",
                ca_result=result,
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
