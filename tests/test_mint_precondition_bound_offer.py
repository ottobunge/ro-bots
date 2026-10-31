"""The mint precondition holds on the CONTEXT's bound offer, not the dialogue clock.

Leg 55 (5bd56be5): the bound offer survives its full 300s TTL (all five hold
arms live-verified), but the decide-paced mint starves: _shop_loop_action's
_npc.failed term (set by the post-C6 _deny('timeout') ~15s after every bind)
gates the mint for the offer's whole life. The dialogue denial is a NORMAL
clock-expiry artifact while the deal lives server-side: while the shop CONTEXT
holds the bound offer, only the innocent timeout denial is held off the mint
(the deny_origin='timeout' retryable contract, legs 23-24); the poison denials
(malformed, send-failure) still block, and without a bound offer the barrier
is complete. A mint-path tap names any remaining gate with its term values.
"""

from __future__ import annotations

import logging
import struct

import pytest

from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import NpcShopPurchase
from robots.domain.model import Goal
from tests.test_native_self_metadata_context import bind, proof_for
from tests.test_native_shop_selection import ready_shop

_TAP_LOGGER = "robots.app.playing_runtime"


def _bound_shop(monkeypatch: pytest.MonkeyPatch) -> PlayingClient:
    """The seeded-wallet shape: C5 sent, C6 bound, self-slots and seed armed."""
    wire, client, receive, _sent, selection = ready_shop(monkeypatch)
    client.perform_native(selection)
    # the C6 answers; the weight pair arrives; NO B1/20 zeny - the wallet is
    # the runner-side seed alone (the wire delivers SP_ZENY on changes only)
    receive(
        struct.pack("<HHIIBH", 0xC6, 15, 73, 61, 4, 1201),
        struct.pack("<HHi", 0xB0, 24, 400),
        struct.pack("<HHi", 0xB0, 25, 2000),
    )
    assert bind(client, proof_for(wire))
    client._zeny_seed = 80  # affords the fixture received full price (73)
    state = client.build_native_state(Goal.GRIND)
    assert state.shop_offer is not None  # the C6 bound before any denial
    return client


def _expire_dialogue(client: PlayingClient, *, poison: bool = False) -> None:
    """Drive the REAL dialogue machine into its post-bind deny.

    The harness clock is fixed at 100.0 and the post-C5 deadline is 105.0:
    pulling the deadline under now expires the dialogue through the machine
    own _expire -> _deny('timeout'); the malformed class denies through the
    backwards-clock guard (_last_now in the future -> _deny('poison')).
    """
    if poison:
        client._npc._last_now = 200.0
    else:
        client._npc.deadline = 99.0
    client.build_native_state(Goal.GRIND)


def test_timeout_denial_with_bound_offer_still_mints(monkeypatch) -> None:
    client = _bound_shop(monkeypatch)
    _expire_dialogue(client)
    assert client._npc.failed is True
    assert client._npc.deny_origin == "timeout"
    state = client.build_native_state(Goal.GRIND)
    assert state.shop_offer is not None  # the offer survives the clock (leg 55)
    actions = client.mechanical_actions(state, ())
    # RED (leg 55): the denial is a normal clock-expiry artifact while the
    # deal lives server-side - the mint must not starve for the offer life
    assert len(actions) == 1
    assert isinstance(actions[0], NpcShopPurchase)


def test_poison_denial_with_bound_offer_still_blocks(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = _bound_shop(monkeypatch)
    _expire_dialogue(client, poison=True)
    assert client._npc.failed is True
    assert client._npc.deny_origin == "poison"
    state = client.build_native_state(Goal.GRIND)
    assert state.shop_offer is not None
    with caplog.at_level(logging.WARNING, logger=_TAP_LOGGER):
        actions = client.mechanical_actions(state, ())
    assert not any(isinstance(a, NpcShopPurchase) for a in actions)
    # the mint-path tap names the remaining gate with its term values
    taps = [r for r in caplog.records if "mint skipped by" in r.getMessage()]
    assert len(taps) == 1
    assert "mint skipped by npc_failed" in taps[0].getMessage()
    assert "deny_origin=poison" in taps[0].getMessage()
    assert "offer_bound=True" in taps[0].getMessage()


def test_no_bound_offer_and_failed_still_blocks(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _wire, client, receive, _sent, selection = ready_shop(monkeypatch)
    del receive  # NO C6 - no bound offer ever arrives
    client.perform_native(selection)
    _expire_dialogue(client)
    assert client._npc.failed is True
    assert client._npc.deny_origin == "timeout"
    assert client._shop_context.offer is None
    with caplog.at_level(logging.WARNING, logger=_TAP_LOGGER):
        actions = client.mechanical_actions(client.build_native_state(Goal.GRIND), ())
    assert not any(isinstance(a, NpcShopPurchase) for a in actions)
    # no bound offer -> no mint was pending -> the mint-path tap stays silent
    assert not [r for r in caplog.records if "mint skipped by" in r.getMessage()]
