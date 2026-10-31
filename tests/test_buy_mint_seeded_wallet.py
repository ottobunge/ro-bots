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
"""

from __future__ import annotations

import struct

from robots.domain.actions import NpcShopPurchase
from robots.domain.model import Goal
from tests.test_native_self_metadata_context import bind, proof_for
from tests.test_native_shop_selection import ready_shop


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
