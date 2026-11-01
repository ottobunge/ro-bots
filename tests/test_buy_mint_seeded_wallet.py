"""The buy mint must read the seeded wallet, not only the wire-observed one.

Leg 47: the C6 buy list BOUND (issued=True, the b78f105b fix) but the purchase
never minted — TWO starvation points, both the same class (the wire delivers
the wallet facts on CHANGES only, pc.cpp:5810/5844, so a fresh login has no
receipt to spend against):
1. _buy_mint_attempt read self._shop_context.balance; the e2e-43 seed feeds
   _zeny_balance's authority chain (tracked wire > shop receipt > seed) but
   not this direct read. FIXED: the mint reads the chain.
2. the purchase machine refuses to mint on unbound facts and a currency-less
   admission. FIXED: the first live qualification binds the operator's knife
   template (the pinned item db constants) to the CURRENT exchange, and the
   admission's receipt falls back to the seeded balance (marked runner-seed).

Leg 56 named the last gate of the same class: the 0xB0 24/25 weight pair is
login-truth delivered ONCE (SP_WEIGHT rides the wire on changes only), but its
freshness stamp is the login frame's arrival — by the decide-paced mint the
pair reads stale past the 5s window and the capacity gate refused. While the
shop CONTEXT carries a BOUND offer (received data with its own bounded TTL,
the C6 row re-proving the item's identity), the login-stamped pair stays
valid; without a bound offer the honest stale path stands.
"""

from __future__ import annotations

import logging
import struct
from typing import Any

import pytest

from robots.adapters import native_purchase
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import NpcShopPurchase
from robots.domain.model import Goal
from tests.test_native_self_metadata_context import bind, proof_for
from tests.test_native_shop_selection import ready_shop


@pytest.fixture(autouse=True)
def _fresh_tap_memo() -> Any:
    """The freshness tap memo is module state; isolate it per test."""
    native_purchase._FRESHNESS_TAPPED.clear()
    yield
    native_purchase._FRESHNESS_TAPPED.clear()


def _aged_login_pair_flow(monkeypatch: pytest.MonkeyPatch) -> tuple[Any, PlayingClient]:
    """The common leg-56 shape: C6 bound, login-stamped 400/2000 pair received,
    the seeded wallet, the client clock advanced 20s past the login stamp."""
    wire, client, receive, _sent, selection = ready_shop(monkeypatch)
    client.perform_native(selection)
    # the C6 answers; the weight pair arrives; NO B1/20 zeny — the wallet is
    # the runner-side seed alone (the wire delivers SP_ZENY on changes only)
    receive(
        struct.pack("<HHIIBH", 0xC6, 15, 73, 61, 4, 1201),
        struct.pack("<HHi", 0xB0, 24, 400),
        struct.pack("<HHi", 0xB0, 25, 2000),
    )
    assert bind(client, proof_for(wire))
    client._zeny_seed = 80  # affords the fixture's received full price (73)
    client._now = lambda: 120.0  # the pair stamped at 100.0: 20s, 4x the window
    return wire, client


def test_seeded_wallet_mints_the_affordable_purchase(monkeypatch) -> None:
    wire, client, receive, _sent, selection = ready_shop(monkeypatch)
    client.perform_native(selection)
    # the C6 answers; the weight pair arrives; NO B1/20 zeny — the wallet is
    # the runner-side seed alone (the wire delivers SP_ZENY on changes only)
    receive(
        struct.pack("<HHIIBH", 0xC6, 15, 73, 61, 4, 1201),
        struct.pack("<HHi", 0xB0, 24, 400),
        struct.pack("<HHi", 0xB0, 25, 2000),
    )
    assert bind(client, proof_for(wire))
    client._zeny_seed = 80  # affords the fixture's received full price (73)
    state = client.build_native_state(Goal.GRIND)
    assert state.shop_offer is not None  # the b78f105b fix holds
    assert state.zeny == 80  # the seed reports through the state chain
    actions = client.mechanical_actions(state, ())
    # RED (leg 47): with no wire zeny the mint starved even though the seeded
    # wallet affords the knife at 61z — the mechanical layer must mint it
    assert len(actions) == 1
    assert isinstance(actions[0], NpcShopPurchase)


def test_aged_login_weight_pair_mints_while_offer_is_bound(monkeypatch) -> None:
    """RED (leg 56): the login-stamped weight pair is 20s old at the mint —
    past the 5s freshness window — yet the server-side weight cannot have
    changed without a wire update arriving (SP_WEIGHT rides on changes only).
    While the shop CONTEXT carries the BOUND offer the pair stays valid and
    the purchase mints; the stale login stamp must not starve the economy."""
    _wire, client = _aged_login_pair_flow(monkeypatch)
    state = client.build_native_state(Goal.GRIND)
    assert state.shop_offer is not None
    actions = client.mechanical_actions(state, ())
    assert len(actions) == 1
    assert isinstance(actions[0], NpcShopPurchase)


def test_aged_login_weight_pair_without_bound_offer_still_refused(monkeypatch) -> None:
    """The honest stale path stands: with NO bound offer the admission never
    forms and the same aged pair mints nothing — the bound-offer hold is not
    a global relaxation of the freshness gate."""
    _wire, client, receive, _sent, _selection = ready_shop(monkeypatch)
    # NO C5 selection, NO C6: no offer ever binds; the pair arrives alone.
    receive(
        struct.pack("<HHi", 0xB0, 24, 400),
        struct.pack("<HHi", 0xB0, 25, 2000),
    )
    client._zeny_seed = 80
    client._now = lambda: 120.0  # the pair stamped at 100.0: 20s old
    state = client.build_native_state(Goal.GRIND)
    assert state.shop_offer is None
    actions = client.mechanical_actions(state, ())
    assert not any(isinstance(a, NpcShopPurchase) for a in actions)


def test_freshness_refusal_tap_names_age_and_window(monkeypatch, caplog) -> None:
    """Tap-before-fix doctrine: when the freshness gate refuses the
    login-stamped pair the shop-debug WARNING names the observed age against
    the window (and whether the bound-offer hold applies)."""
    with caplog.at_level(logging.WARNING, logger="robots.adapters.native_purchase"):
        _wire, client = _aged_login_pair_flow(monkeypatch)
        state = client.build_native_state(Goal.GRIND)
        client.mechanical_actions(state, ())
    assert "capacity freshness" in caplog.text
    assert "weight_age=20.0s" in caplog.text
    assert "max_age=20.0s" in caplog.text
    assert "window=5.0s" in caplog.text
    assert "held_by_bound_offer=True" in caplog.text
