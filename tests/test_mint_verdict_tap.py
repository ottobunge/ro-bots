"""Term-level mint verdict tap: golden line shape, bounds, freshness memo.

Leg 57: the seventh arm's hold engaged (144/144 held_by_bound_offer=True) and
the mint still starved - a second, untapped term in the same consumption seam.
Tap-before-fix doctrine: the failing term's NAME with both values must land in
the log before any fix, so every seam predicate is evaluated as a named
(label, verdict, values) term and the mint logs one joined verdict line per
consumed attempt while the shop CONTEXT carries a bound offer. The capacity
freshness refusal tap is bounded to once per offer identity.
"""

import logging
from typing import Any

import pytest

from robots.adapters import native_purchase
from robots.adapters.native_purchase import (
    NativePurchase,
    PurchaseAdmission,
    _capacity_fits,
    _render_terms,
)
from robots.domain.capacity import ReceivedCapacity, ReceivedCapacityValue
from robots.domain.shop import QualifiedShopItem, ReceivedShopOffer, ReceivedShopRow, ReceivedZeny

NOW = 100.0
_OWNER = ("wire", "dialogue")


@pytest.fixture(autouse=True)
def _fresh_tap_memo() -> Any:
    """The freshness tap memo is module state; isolate it per test."""
    native_purchase._FRESHNESS_TAPPED.clear()
    yield
    native_purchase._FRESHNESS_TAPPED.clear()


def _offer(**overrides: Any) -> Any:
    values: dict[str, Any] = {
        "rows": (ReceivedShopRow(price=73, discount_price=61, item_type=4, item_id=1201),),
        "receipt_sequence": 7,
        "observed_at": NOW,
        "deadline": 200.0,
        "npc_id": 123,
        "opened_sequence": 3,
        "map_name": "prontera",
        "epoch": 1,
        "prompt_sequence": 2,
    }
    values.update(overrides)
    return ReceivedShopOffer(**values)


def _facts(**overrides: Any) -> Any:
    values: dict[str, Any] = {
        "source_id": "explicitly-trusted-facts",
        "account_id": 7,
        "character_id": 8,
        "epoch": 1,
        "npc_id": 123,
        "map_name": "prontera",
        "actual_item_id": 1201,
        "client_item_id": 1201,
        "loaded_weight": 400,
        "ordinary_shop": True,
        "nonstackable": True,
        "stable_price": 73,
        "stable_discount_price": 61,
        "valid_until": 150.0,
    }
    values.update(overrides)
    return QualifiedShopItem(**values)


def _currency(balance: int = 1000) -> ReceivedZeny:
    return ReceivedZeny(balance, 1, 9, NOW)


def _capacity(weight_at: float = NOW) -> ReceivedCapacity:
    return ReceivedCapacity(
        1,
        "Fx",
        7,
        8,
        1,
        1,
        NOW,
        weight=ReceivedCapacityValue(400, 5, weight_at),
        max_weight=ReceivedCapacityValue(2000, 5, weight_at),
    )


def _admission(**overrides: Any) -> PurchaseAdmission:
    values: dict[str, Any] = {
        "owner": _OWNER,
        "offer": _offer(),
        "currency": _currency(),
        "capacity": _capacity(),
        "stock": (),
        "slots": 100,
        "account_id": 7,
        "character_id": 8,
        "now": NOW,
    }
    values.update(overrides)
    return PurchaseAdmission(**values)


def _bound_purchase(context: PurchaseAdmission) -> NativePurchase:
    purchase = NativePurchase()
    assert purchase.bind(_facts(), context)
    return purchase


def _mint_lines(records: Any) -> list[str]:
    return [record.getMessage() for record in records if "mint verdict" in record.getMessage()]


def test_mint_verdict_golden_line_names_every_term(caplog: Any) -> None:
    context = _admission()
    purchase = _bound_purchase(context)
    with caplog.at_level(logging.WARNING, logger="robots.adapters.native_purchase"):
        action = purchase.mint(context, 61)
    assert action is not None
    lines = _mint_lines(caplog.records)
    assert len(lines) == 1
    expected = " ".join(
        (
            "shop-debug: mint verdict",
            "owner=True(len 2/2)",
            "offer=True(receipt=7)",
            "f_src=True(explicitly-trusted-facts)",
            "f_acct=True(7/7)",
            "f_char=True(8/8)",
            "f_epoch=True(1/1)",
            "f_npc=True(123/123)",
            "f_map=True(prontera/prontera)",
            "f_item=True(1201/1201)",
            "f_client=True(1201/1201)",
            "f_ordinary=True(True)",
            "f_nonstack=True(True)",
            "f_price=True(73)",
            "f_disc=True(61)",
            "f_valid=True(until=150.0 now=100.0)",
            "deadline=True(now=100.0 deadline=200.0)",
            # The received-row law (leg 58): the seam no longer re-checks the
            # template's db-pin type against the row, so the template side of
            # the rendering carries price/discount only; the received row keeps
            # its own volatile third field as evidence.
            "row=True((73,61,4) v (73,61) rows=1)",
            "budget=True(budget=61 price=61)",
            "balance=True(balance=1000 price=61)",
            "currency=True(epoch 1/1 age=0.0s)",
            "epoch=True(1/1)",
            "acct=True(7/7)",
            "char=True(8/8)",
            "cap_held=True(w_age=0.0s max_age=0.0s window=5.0s)",
            "ints=True(weight=400 max=2000)",
            "loaded_int=True(loaded=400)",
            "loaded_w=True(400+400<=2000)",
            "inv_seq=True(receipt=5 changed=None)",
            "slots_free=True(0/100)",
            "rows_int=True(0 rows)",
            "no_knife_dup=True(knife rows=0)",
            "eligible=True(verdict)",
        )
    )
    assert lines[0] == expected
    # the helper's own output shape matches the logged line's term body
    rendered = _render_terms(purchase._verdict(context, 61))
    assert rendered == expected[len("shop-debug: mint verdict ") :]


def test_failing_term_renders_false_with_both_values(caplog: Any) -> None:
    context = _admission(currency=_currency(60))
    purchase = _bound_purchase(context)
    with caplog.at_level(logging.WARNING, logger="robots.adapters.native_purchase"):
        assert purchase.mint(context, 61) is None
    lines = _mint_lines(caplog.records)
    assert len(lines) == 1
    assert "balance=False(balance=60 price=61)" in lines[0]
    assert "budget=True(budget=61 price=61)" in lines[0]
    assert "eligible=False(verdict)" in lines[0]


def test_aged_pair_mint_verdict_shows_cap_held_by_bound_offer(caplog: Any) -> None:
    context = _admission(capacity=_capacity(weight_at=NOW - 20))
    purchase = _bound_purchase(context)
    with caplog.at_level(logging.WARNING, logger="robots.adapters.native_purchase"):
        assert purchase.mint(context, 61) is not None
    lines = _mint_lines(caplog.records)
    assert len(lines) == 1
    assert "cap_held=True(w_age=20.0s max_age=20.0s window=5.0s)" in lines[0]
    assert "eligible=True(verdict)" in lines[0]


def test_unbound_purchase_verdict_names_the_missing_facts(caplog: Any) -> None:
    context = _admission()
    purchase = NativePurchase()
    with caplog.at_level(logging.WARNING, logger="robots.adapters.native_purchase"):
        assert purchase.mint(context, 61) is None
    lines = _mint_lines(caplog.records)
    assert len(lines) == 1
    assert lines[0] == "shop-debug: mint verdict verdict=False(facts=False context=True)"


def test_one_verdict_line_per_consumed_attempt_and_none_without_context(caplog: Any) -> None:
    context = _admission()
    purchase = _bound_purchase(context)
    with caplog.at_level(logging.WARNING, logger="robots.adapters.native_purchase"):
        assert purchase.mint(context, 61) is not None
        assert purchase.mint(context, 61) is not None
        assert len(_mint_lines(caplog.records)) == 2
        assert purchase.mint(None, 61) is None
        assert len(_mint_lines(caplog.records)) == 2


def test_freshness_tap_fires_once_per_offer_identity(caplog: Any) -> None:
    capacity = _capacity(weight_at=NOW - 20)
    context = _admission(capacity=capacity)
    facts = _facts()
    with caplog.at_level(logging.WARNING, logger="robots.adapters.native_purchase"):
        for _ in range(3):
            assert _capacity_fits(capacity, context, facts)
        first = [
            record.getMessage()
            for record in caplog.records
            if "capacity freshness" in record.getMessage()
        ]
        assert len(first) == 1
        assert "weight_age=20.0s" in first[0]
        assert "max_age=20.0s" in first[0]
        assert "window=5.0s" in first[0]
        assert "held_by_bound_offer=True" in first[0]
        newer = _admission(offer=_offer(receipt_sequence=8), capacity=capacity)
        assert _capacity_fits(capacity, newer, facts)
        lines = [
            record.getMessage()
            for record in caplog.records
            if "capacity freshness" in record.getMessage()
        ]
        assert len(lines) == 2
