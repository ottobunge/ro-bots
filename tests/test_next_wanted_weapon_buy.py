"""Leg-110: autonomous purchases complete the wanted set across dealer visits."""

import struct
from collections.abc import Callable
from dataclasses import replace
from typing import Any

import pytest

from robots.app import scripts
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import GameAction, NpcShopBuySelection, NpcShopPurchase, TalkToNpc
from robots.domain.model import BotState, Goal
from tests.test_native_self_metadata_context import bind, proof_for
from tests.test_native_shop_purchase import acquisition
from tests.test_native_shop_selection import actual_clients
from tests.test_shop_sell_loop import DEALER, _c4, _dealer
from tests.test_walkable_dealer_ring import _buyer


@pytest.fixture(autouse=True)
def fresh_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _offer(*rows: tuple[int, int, int]) -> bytes:
    return struct.pack("<HH", 0xC6, 4 + 11 * len(rows)) + b"".join(
        struct.pack("<IIBH", price, discount, 4, item) for item, price, discount in rows
    )


def _exchange(
    monkeypatch: pytest.MonkeyPatch, *, owned: tuple[int, ...] = (), zeny: int = 147
) -> tuple[Any, PlayingClient, Callable[..., None], list[bytes], BotState]:
    wire, client, receive, sent = actual_clients(monkeypatch)
    receive(
        *(acquisition(index=10 + i, item=item) for i, item in enumerate(owned)),
        struct.pack("<HHi", 0xB1, 20, zeny),
        struct.pack("<HHi", 0xB0, 24, 900),
        struct.pack("<HHi", 0xB0, 25, 3000),
    )
    assert bind(client, proof_for(wire))
    receive(struct.pack("<HI", 0xC4, 123))
    state = client.build_native_state(Goal.GRIND)
    return wire, client, receive, sent, state


def _actions(client: PlayingClient, state: BotState) -> tuple[GameAction, ...]:
    actions = client.shop_actions(state, ())
    assert actions is not None
    return actions


@pytest.mark.parametrize(("owned", "target"), [((), 1202), ((1202,), 1204)])
@pytest.mark.parametrize("zeny", [50, 147])
def test_holder_authors_next_unowned_purchase_from_received_offer(monkeypatch, owned, target, zeny):
    _wire, client, receive, sent, state = _exchange(monkeypatch, owned=owned, zeny=zeny)
    (selection,) = _actions(client, state)
    assert isinstance(selection, NpcShopBuySelection)
    client.perform_native(selection)
    # Deliberately reverse the list: the wanted order owns selection, and
    # affordability uses the exchange's discount, never a guessed DB price.
    receive(_offer((1204, 1250, 50), (1202, 73, 50), (1201, 50, 50)))
    state = client.build_native_state(Goal.GRIND)
    (purchase,) = _actions(client, state)
    assert isinstance(purchase, NpcShopPurchase)
    assert purchase.item_id == target
    client.perform_native(purchase)
    client.perform_native(purchase)
    assert sent[-1] == struct.pack("<HHHH", 0xC8, 8, 1, target)
    assert sum(raw[:2] == b"\xc8\x00" for raw in sent) == 1
    receive(
        struct.pack("<HHi", 0xB1, 20, zeny - 50),
        acquisition(index=20, item=target),
        struct.pack("<HHi", 0xB0, 24, 1400),
        struct.pack("<HB", 0xCA, 0),
    )
    progress = client.shop_purchase_progress()
    assert progress is not None
    assert progress.status == "acquired"
    for _ in range(5):
        state = client.build_native_state(Goal.GRIND)
        assert not any(isinstance(a, NpcShopPurchase) for a in client.shop_actions(state, ()) or ())
    assert sum(raw[:2] == b"\xc8\x00" for raw in sent) == 1


def test_idle_holder_arms_click_then_c4_buy_selection():
    client = _buyer(((7, 1201, 1),), 147)
    state = client.build_native_state(Goal.GRIND)
    assert scripts.merchant_admission_refusal(state) is None
    assert client.shop_actions(state, ()) == (TalkToNpc(DEALER),)
    client.perform_native(TalkToNpc(DEALER))
    client.wire.add(_c4(DEALER))
    (selection,) = _actions(client, client.build_native_state(Goal.GRIND))
    assert isinstance(selection, NpcShopBuySelection)


@pytest.mark.parametrize("zeny", [0, 49])
def test_poor_holder_does_not_open_or_purchase(monkeypatch, zeny):
    _wire, client, receive, sent, state = _exchange(monkeypatch, zeny=zeny)
    assert not any(isinstance(a, NpcShopBuySelection) for a in client.shop_actions(state, ()) or ())
    receive(_offer((1202, 50, 50)))
    assert not any(
        isinstance(a, NpcShopPurchase)
        for a in client.shop_actions(client.build_native_state(Goal.GRIND), ()) or ()
    )
    assert not any(raw[:2] in (b"\xc5\x00", b"\xc8\x00") for raw in sent)


def test_complete_wanted_set_never_rearms_buy(monkeypatch):
    _wire, client, _receive, sent, state = _exchange(monkeypatch, owned=(1202, 1204))
    assert scripts.merchant_drive_cell(replace(state, map_name="prt_in")) is None
    for _ in range(5):
        assert client.shop_actions(state, ()) is None
    assert not any(raw[:2] in (b"\xc5\x00", b"\xc8\x00") for raw in sent)


def test_received_offer_with_only_owned_weapons_cannot_buy(monkeypatch):
    _wire, client, receive, sent, state = _exchange(monkeypatch)
    (selection,) = _actions(client, state)
    client.perform_native(selection)
    receive(_offer((1201, 50, 50), (1202, 500, 500)))
    state = client.build_native_state(Goal.GRIND)
    assert not any(isinstance(a, NpcShopPurchase) for a in client.shop_actions(state, ()) or ())
    assert not any(raw[:2] == b"\xc8\x00" for raw in sent)


def test_owned_item_arriving_between_mint_and_dispatch_blocks_duplicate(monkeypatch):
    _wire, client, receive, sent, state = _exchange(monkeypatch)
    (selection,) = _actions(client, state)
    client.perform_native(selection)
    receive(_offer((1202, 50, 50)))
    (purchase,) = _actions(client, client.build_native_state(Goal.GRIND))
    assert isinstance(purchase, NpcShopPurchase)
    assert purchase.item_id == 1202
    receive(acquisition(index=20, item=1202), struct.pack("<HHi", 0xB0, 24, 1300))
    client.perform_native(purchase)
    assert not any(raw[:2] == b"\xc8\x00" for raw in sent)


def test_holder_finishes_set_over_two_visits_then_stops(monkeypatch):
    _wire, client, receive, sent, state = _exchange(monkeypatch, zeny=2000)
    for visit, target in enumerate((1202, 1204)):
        if visit:
            # A received departure, followed by a fresh dealer contact, grants
            # the next visit. Re-clicks in the same map must never do this.
            receive(struct.pack("<H16sHH", 0x91, b"prt_in", 42, 37))
            client.build_native_state(Goal.GRIND)
            receive(struct.pack("<H16sHH", 0x91, b"prontera", 42, 37))
            receive(_dealer((42, 37), npc_id=123))
            client.build_native_state(Goal.GRIND)
            assert bind(client, proof_for(client.wire))
            client.perform_native(TalkToNpc(123))
            receive(struct.pack("<HI", 0xC4, 123))
            state = client.build_native_state(Goal.GRIND)
        (selection,) = _actions(client, state)
        assert isinstance(selection, NpcShopBuySelection)
        client.perform_native(selection)
        # The next visit offers only Cutter: a remaining 1201-only stock
        # backoff must not reject it after successful selection.
        receive(_offer(*(((1201, 50, 50), (1202, 50, 50)) if not visit else ((1204, 50, 50),))))
        (purchase,) = _actions(client, client.build_native_state(Goal.GRIND))
        assert isinstance(purchase, NpcShopPurchase)
        assert purchase.item_id == target
        client.perform_native(purchase)
        receive(
            struct.pack("<HHi", 0xB1, 20, 1950 - visit * 50),
            acquisition(index=20 + visit, item=target),
            struct.pack("<HHi", 0xB0, 24, 1400 + visit * 500),
            struct.pack("<HB", 0xCA, 0),
        )
        state = client.build_native_state(Goal.GRIND)
        progress = client.shop_purchase_progress()
        assert progress is not None
        assert progress.status == "acquired"
        assert state.merchant_buy_suspended
        assert client.shop_actions(state, ()) is None
        # A fresh dialogue survives the old receipt but cannot spend twice.
        client.perform_native(TalkToNpc(123))
        receive(struct.pack("<HI", 0xC4, 123))
        state = client.build_native_state(Goal.GRIND)
        assert client._npc.view is not None
        assert client._npc.view.stage == "unsupported_shop"
        assert client.shop_actions(state, ()) is None
    assert state.inventory == {"1201": 1, "1202": 1, "1204": 1}
    assert scripts.merchant_drive_cell(replace(state, merchant_buy_suspended=False)) is None
    assert sum(raw[:2] == b"\xc8\x00" for raw in sent) == 2


def test_mutating_public_purchase_after_send_cannot_retarget_receipt(monkeypatch):
    _wire, client, receive, _sent, state = _exchange(monkeypatch)
    (selection,) = _actions(client, state)
    client.perform_native(selection)
    receive(_offer((1202, 50, 50)))
    (purchase,) = _actions(client, client.build_native_state(Goal.GRIND))
    assert isinstance(purchase, NpcShopPurchase)
    client.perform_native(purchase)
    object.__setattr__(purchase, "item_id", 1204)
    receive(
        struct.pack("<HHi", 0xB1, 20, 97),
        acquisition(index=20, item=1204),
        struct.pack("<HHi", 0xB0, 24, 1400),
        struct.pack("<HB", 0xCA, 0),
    )
    progress = client.shop_purchase_progress()
    assert progress is not None
    assert progress.status == "incomplete"
    assert progress.reason == "ambiguous acquisition"
