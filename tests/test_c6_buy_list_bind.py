"""Offline C6 through the real framer/ring after a nonzero dealer approach."""

import struct
from collections.abc import Callable
from typing import Any

import pytest

from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import NpcShopBuySelection, NpcShopPurchase, TalkToNpc
from robots.domain.model import Goal
from tests.test_native_self_metadata_context import bind, proof_for
from tests.test_native_shop_selection import actual_clients
from tests.test_playing_runtime import walk_ack

# e985 packets_struct.hpp:3065-3080, MAIN 20180704: uint32 price,
# uint32 discountPrice, uint8 itemType, uint16 itemId (11-byte rows).
C6 = bytes.fromhex("c6000f00320000003200000004b104")


def _approached_buyer(
    monkeypatch: pytest.MonkeyPatch, *, balance: int = 50
) -> tuple[Any, PlayingClient, Callable[..., None], list[bytes]]:
    wire, client, receive, sent = actual_clients(monkeypatch)
    client._npc.invalidate()  # Discard the shared fixture's initial click.
    receive(
        walk_ack((42, 37), (43, 37)),
        struct.pack("<HHi", 0xB1, 20, balance),
        struct.pack("<HHi", 0xB0, 25, 2000),
    )
    assert bind(client, proof_for(wire))
    client.build_native_state(Goal.GRIND)
    client.perform_native(TalkToNpc(123))
    assert sent[-1] == struct.pack("<HIB", 0x90, 123, 1)
    assert client._npc.view is not None
    assert client._npc.view.stage == "opening"
    receive(struct.pack("<HI", 0xC4, 123))
    state = client.build_native_state(Goal.GRIND)
    assert client._tracker is not None
    assert not client._tracker.view.arrival_confirmed
    assert client._pending is None
    (selection,) = client.mechanical_actions(state, ())
    assert isinstance(selection, NpcShopBuySelection)
    client.perform_native(selection)
    assert sent[-1] == bytes.fromhex("c5007b00000000")
    return wire, client, receive, sent


def test_c6_after_real_approach_binds_and_sends_one_purchase(monkeypatch):
    wire, client, receive, sent = _approached_buyer(monkeypatch)
    receive(C6)
    state = client.build_native_state(Goal.GRIND)
    assert state.shop_offer is not None
    assert state.shop_offer.rows[0].item_id == 1201
    assert state.shop_offer.rows[0].price == 50
    assert client._tracker is not None
    assert client._tracker.view.sell_lists == ()  # C6 never uses the C7 parser.
    assert wire.native_frame_snapshot()[2][-1][3] == C6
    (purchase,) = client.mechanical_actions(state, ())
    assert isinstance(purchase, NpcShopPurchase)
    client.perform_native(purchase)
    client.perform_native(purchase)
    # clif.cpp:12297-12300: CZ purchase is C8; CA is the received result.
    assert sent[-1] == bytes.fromhex("c80008000100b104")
    assert sum(raw[:2] == b"\xc8\x00" for raw in sent) == 1


@pytest.mark.parametrize(
    "raw",
    [
        bytes.fromhex("c6000e0006003200000032000000"),  # C7 geometry under C6 ID.
        bytes.fromhex("c6000f003200000032000000040000"),  # Zero item ID.
        struct.pack("<HHIIBH", 0xC6, 15, 50, 50, 4, 999),  # Unknown item.
        struct.pack("<HHIIBH", 0xC6, 15, 50, 51, 4, 1201),  # Inconsistent price.
        struct.pack("<HH", 0xC6, 26) + C6[4:] * 2,  # Ambiguous duplicate.
    ],
)
def test_corrupt_or_inconsistent_c6_cannot_purchase(monkeypatch, raw):
    _wire, client, receive, sent = _approached_buyer(monkeypatch, balance=1000)
    receive(raw)
    state = client.build_native_state(Goal.GRIND)
    actions = client.mechanical_actions(state, ())
    assert not any(isinstance(action, NpcShopPurchase) for action in actions)
    assert client.npc_shop_purchase(maximum_zeny=1000) is None
    assert not any(raw[:2] == b"\xc8\x00" for raw in sent)


@pytest.mark.parametrize("boundary", ["pending_walk", "new_walk", "sit", "vanish", "far"])
def test_c6_after_approach_keeps_current_context_guards(monkeypatch, boundary):
    _wire, client, receive, sent = _approached_buyer(monkeypatch)
    if boundary == "pending_walk":
        client._pending = ((44, 37), client._metadata_cursor, 100.0, 0)
    elif boundary == "new_walk":
        receive(walk_ack((43, 37), (42, 37)))
    elif boundary == "sit":
        client._standing = False
    elif boundary == "vanish":
        receive(struct.pack("<HIB", 0x80, 123, 0))
    else:
        receive(walk_ack((43, 37), (60, 37)))
    receive(C6)
    assert client.build_native_state(Goal.GRIND).shop_offer is None
    assert client.npc_shop_purchase(maximum_zeny=1000) is None
    assert not any(raw[:2] == b"\xc8\x00" for raw in sent)


def test_buy_keeps_fifty_zeny_floor_even_for_a_cheaper_offer(monkeypatch):
    _wire, client, receive, sent = _approached_buyer(monkeypatch, balance=49)
    receive(struct.pack("<HHIIBH", 0xC6, 15, 1, 1, 4, 1201))
    state = client.build_native_state(Goal.GRIND)
    actions = client.mechanical_actions(state, ())
    assert not any(isinstance(action, NpcShopPurchase) for action in actions)
    assert client.npc_shop_purchase(maximum_zeny=1000) is None
    assert not any(raw[:2] == b"\xc8\x00" for raw in sent)
