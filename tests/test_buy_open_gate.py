"""Leg 85: replay the post-walk C4 hold without a server or a C6 offer."""

import struct

import pytest

from robots.app import scripts
from robots.app.playing_runtime import NPC_RETRY_BUDGET, NPC_RETRY_EPOCH_S, PlayingClient
from robots.domain.actions import (
    GameAction,
    NpcClose,
    NpcShopBuySelection,
    NpcShopSellOpen,
    TalkToNpc,
)
from robots.domain.model import Goal
from tests.test_playing_runtime import walk_ack
from tests.test_post_sale_freeze import _blocked_client
from tests.test_shop_sell_loop import DEALER, _armed, _c4, _client_with, _dealer, _inv, _weight


def _post_c4(*, sellable: bool = False):
    client = _client_with(
        walk_ack((42, 37), (43, 37)),
        _dealer((43, 37)),
        _inv(((6, 909, 1),) if sellable else ()),
        _weight(),
    )
    client.build_native_state(Goal.GRIND)
    _armed(client)
    client.wire.add(_c4(DEALER))
    state = client.build_native_state(Goal.GRIND)
    assert client._tracker is not None
    assert not client._tracker.view.arrival_confirmed
    assert not client._npc_self_ready(client._tracker.view, client._epoch_character, client._epoch)
    assert client._shop_context.offer is None
    return client, state


@pytest.mark.parametrize("sellable", [False, True])
def test_post_walk_c4_opens_once_without_c6(sellable):
    client, state = _post_c4(sellable=sellable)
    (action,) = client.mechanical_actions(state, ())
    assert isinstance(action, NpcShopSellOpen if sellable else NpcShopBuySelection)
    for _ in range(20):
        assert client._shop_loop_mechanical(state, ()) is None
    client.perform_native(action)
    client.perform_native(action)
    assert client.wire.sent == [struct.pack("<HIB", 0xC5, DEALER, int(sellable))]
    assert client._shop_context.offer is None
    assert client.npc_shop_purchase(maximum_zeny=115) is None


@pytest.mark.parametrize(
    ("attribute", "value", "term"),
    [
        ("requests", 32, "requests"),
        ("failed", True, "npc_failed"),
        ("cancel_uncertain", True, "cancel_uncertain"),
        ("deadline", float("nan"), "deadline"),
        ("absolute_deadline", float("inf"), "absolute_deadline"),
    ],
)
def test_buy_open_tap_names_each_dialogue_refusal(attribute, value, term, caplog):
    client, _state = _post_c4()
    setattr(client._npc, attribute, value)
    for _ in range(2):
        assert client._shop_dialogue(client._now()) is None
    assert caplog.text.count(f"buy-open held by {term} ") == 2
    assert client.wire.sent == []


@pytest.mark.parametrize(
    ("attribute", "value", "term"),
    [
        ("_standing", False, "standing"),
        ("_stand_pending", (1, 100.0, 101.0, 0), "stand_pending"),
        ("_rest_seq", 1, "rest"),
        ("_pending", ((43, 37), 1, 100.0, 0), "pending_walk"),
    ],
)
def test_buy_open_tap_names_each_actuation_refusal(attribute, value, term, caplog):
    client, _state = _post_c4()
    setattr(client, attribute, value)
    assert client._buy_open_action() is None
    assert f"buy-open held by {term} " in caplog.text


@pytest.mark.parametrize("term", ["npc_failed", "cancel_uncertain"])
def test_outer_shop_loop_reports_pre_offer_refusals(term, caplog):
    client, state = _post_c4()
    setattr(client._npc, "failed" if term == "npc_failed" else term, True)
    for _ in range(2):
        assert client._shop_loop_mechanical(state, ()) is None
    assert caplog.text.count(f"buy-open held by {term} ") == 2


@pytest.fixture
def closed_buyer():
    scripts.reset_merchant_talk()
    client, now = _blocked_client(admitted=True)
    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1), _weight())
    state = client.build_native_state(Goal.GRIND)
    assert scripts.merchant_admission_refusal(state) is None
    first = scripts._merchant_step(state)
    assert first is not None
    assert first.actions == (TalkToNpc(DEALER),)
    client._npc_retries = NPC_RETRY_BUDGET
    yield client, now
    scripts.reset_merchant_talk()


def _close_and_tick(client: PlayingClient) -> tuple[GameAction, ...]:
    client.perform_native(NpcClose(DEALER))
    assert client._npc.view is None
    client.drain_native_events()
    state = client.build_native_state(Goal.GRIND)
    outcome = scripts._merchant_step(state)
    assert outcome is not None
    return outcome.actions


def test_closed_unpurchased_buyer_releases_talk_latch_with_shared_epoch_budget(closed_buyer):
    client, now = closed_buyer
    for attempt in range(NPC_RETRY_BUDGET):
        assert _close_and_tick(client) == (TalkToNpc(DEALER),)
        assert client._npc_retries == NPC_RETRY_BUDGET - attempt - 1
        state = client.build_native_state(Goal.GRIND)
        for _ in range(20):
            outcome = scripts._merchant_step(state)
            assert outcome is not None
            assert outcome.actions == ()
        client.perform_native(TalkToNpc(DEALER))
        now[0] += 30.0
        client.build_native_state(Goal.GRIND)

    assert _close_and_tick(client) == ()
    for _ in range(20):
        client.drain_native_events()
        outcome = scripts._merchant_step(client.build_native_state(Goal.GRIND))
        assert outcome is not None
        assert outcome.actions == ()
    assert sum(raw[:2] == b"\x90\x00" for raw in client.wire.sent) == NPC_RETRY_BUDGET
    now[0] = 130.0 + NPC_RETRY_EPOCH_S
    client.drain_native_events()
    state = client.build_native_state(Goal.GRIND)
    outcome = scripts._merchant_step(state)
    assert outcome is not None
    assert outcome.actions == (TalkToNpc(DEALER),)
    assert client._npc_retries == NPC_RETRY_BUDGET - 1
