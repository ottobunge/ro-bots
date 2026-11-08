"""Leg 77: bounded stock refusals release the ring without authorizing a buy."""

import struct
from collections.abc import Callable
from dataclasses import replace
from typing import Any

import pytest

from robots.app.playing_runtime import PlayingClient
from robots.app.scripts import merchant_drive_cell, merchant_return_cell
from robots.domain.actions import GameAction, MoveTo, TalkToNpc
from robots.domain.model import Goal
from tests.test_native_self_metadata_context import bind, proof_for
from tests.test_native_shop_selection import ready_shop


def _offer(ids: tuple[int, ...]) -> bytes:
    return struct.pack("<HH", 0xC6, 4 + 11 * len(ids)) + b"".join(
        struct.pack("<IIBH", 50, 50, 5, item) for item in ids
    )


def _shop(
    monkeypatch: pytest.MonkeyPatch, ids: tuple[int, ...] = (1750, 1751, 1701)
) -> tuple[Any, PlayingClient, Callable[..., None], list[bytes]]:
    wire, client, receive, sent, selection = ready_shop(monkeypatch)
    client.perform_native(selection)
    receive(_offer(ids))
    assert bind(client, proof_for(wire))
    client._zeny_seed = 80
    client.build_native_state(Goal.GRIND)
    return wire, client, receive, sent


def _evaluate(client: PlayingClient) -> tuple[GameAction, ...]:
    state = client.build_native_state(Goal.GRIND)
    return client.mechanical_actions(state, ())


def _reopen(client: PlayingClient, receive: Callable[..., None]) -> None:
    client.perform_native(TalkToNpc(123))
    receive(struct.pack("<HI", 0xC4, 123))
    client.drain_native_events()
    selection = client.npc_shop_buy_selection()
    assert selection is not None
    client.perform_native(selection)


def test_missing_offer_item_gives_up_on_third_evaluation_once(monkeypatch, caplog):
    ids = tuple(range(1701, 1713))
    _wire, client, _receive, sent = _shop(monkeypatch, ids)
    before = len(sent)
    for _ in range(2):
        _evaluate(client)
        assert client._npc.view is not None
        assert client._shop_context.offer is not None
        assert len(sent) == before
    _evaluate(client)
    assert sent[before:] == [struct.pack("<HI", 0x146, 123)]
    assert client._npc.view is None
    assert not client._npc.actuation_blocked
    assert client._shop_context.offer is None
    for _ in range(8):
        _evaluate(client)
        client._retry_blocked_dialogue_on_tick(client._now() + 20)
        assert client._retry_blocked_dialogue() is False
    lines = [r.getMessage() for r in caplog.records if "buy give-up" in r.getMessage()]
    assert len(lines) == 1
    assert "buy give-up no stock in offer" in lines[0]
    assert f"offer_item_ids={list(ids[:8])}" in lines[0]
    assert "1709" not in lines[0]
    assert len(sent) == before + 1
    state = replace(
        client.build_native_state(Goal.GRIND),
        map_name="prt_in",
        inventory={},
        inventory_known=True,
        zeny=80,
    )
    assert merchant_drive_cell(state) is None
    assert merchant_return_cell(state) is not None
    # A new sale still owns the drive, even during the buy suspension.
    assert merchant_drive_cell(replace(state, inventory={"909": 1})) == (172, 130)


@pytest.mark.parametrize("after_give_up", [False, True])
def test_fresh_offer_with_knife_resets_missing_item_counter(monkeypatch, after_give_up):
    wire, client, receive, _sent = _shop(monkeypatch)
    for _ in range(3 if after_give_up else 2):
        _evaluate(client)
    if after_give_up:
        # A real new click/C5 round; no historical offer can revive the buy.
        _reopen(client, receive)
    receive(_offer((1201,)))
    assert bind(client, proof_for(wire))
    state = client.build_native_state(Goal.GRIND)
    assert not state.merchant_buy_suspended
    _evaluate(client)
    receive(_offer((1750,)))
    for _ in range(2):
        _evaluate(client)
        assert client._npc.view is not None
    _evaluate(client)
    assert client._npc.view is None


def test_new_epoch_resets_give_up(monkeypatch):
    wire, client, receive, _sent = _shop(monkeypatch)
    for _ in range(3):
        _evaluate(client)
    assert client.build_native_state(Goal.GRIND).merchant_buy_suspended
    wire.native_epoch += 1
    wire.selection_epoch = wire.map_epoch = wire.native_epoch
    client._reset_epoch(wire.native_epoch, 0)
    assert not client.build_native_state(Goal.GRIND).merchant_buy_suspended
    _reopen(client, receive)
    receive(_offer((1750,)))
    for _ in range(2):
        _evaluate(client)
        assert client._npc.view is not None
    _evaluate(client)
    assert client._npc.view is None


def test_stale_round_offer_cannot_count_or_close_new_dialogue(monkeypatch):
    _wire, client, _receive, sent = _shop(monkeypatch)
    old = client._shop_context.offer
    assert old is not None
    client._npc.begin(123, old.epoch, old.map_name, old.receipt_sequence + 1, client._now())
    before = len(sent)
    for _ in range(5):
        client._shop_context.offer = old
        _evaluate(client)
    assert len(sent) == before
    assert client._npc.view is not None
    assert not client.build_native_state(Goal.GRIND).merchant_buy_suspended


def test_inventory_stock_unknown_has_truthful_backoff_and_releases(monkeypatch, caplog):
    _wire, client, receive, sent = _shop(monkeypatch, (1201,))
    # Actual sell/delete receipt invalidates the indexed snapshot (leg-76 shape).
    receive(struct.pack("<HHH", 0xAF, 2, 1))
    before = len(sent)
    for _ in range(2):
        _evaluate(client)
        assert client._npc.view is not None
    _evaluate(client)
    assert sent[before:] == [struct.pack("<HI", 0x146, 123)]
    assert client._npc.view is None
    lines = [r.getMessage() for r in caplog.records if "buy give-up" in r.getMessage()]
    assert len(lines) == 1
    assert "inventory stock unknown" in lines[0]
    assert "no stock in offer" not in lines[0]
    assert "offer_item_ids=[1201]" in lines[0]
    state = replace(client.build_native_state(Goal.GRIND), map_name="prt_in")
    assert not state.inventory_known
    assert merchant_drive_cell(state) is None
    assert merchant_return_cell(state) is not None


def test_close_failure_keeps_barrier(monkeypatch):
    _wire, client, _receive, _sent = _shop(monkeypatch)
    _evaluate(client)
    _evaluate(client)

    def failed_send(raw):
        message = "synthetic close failure"
        raise OSError(message)

    monkeypatch.setattr(client.wire, "_send", failed_send)
    with pytest.raises(OSError, match="synthetic close failure"):
        _evaluate(client)
    assert client._npc.actuation_blocked
    assert client._npc.failed


def test_give_up_allows_motion_instead_of_recovery_retry(monkeypatch):
    _wire, client, _receive, sent = _shop(monkeypatch)
    for _ in range(3):
        _evaluate(client)
    before = len(sent)
    moved = []
    monkeypatch.setattr(client, "_move", lambda _state, cell: moved.append(cell))
    client.perform_native(MoveTo(43, 37))
    assert client._npc.view is None
    assert moved == [(43, 37)]
    assert all(int.from_bytes(raw[:2], "little") != 0x90 for raw in sent[before:])


def test_later_stockless_round_is_closed_without_repeating_give_up_tap(monkeypatch, caplog):
    _wire, client, receive, sent = _shop(monkeypatch)
    for _ in range(3):
        _evaluate(client)
    _reopen(client, receive)  # A fresh sale/contact must not re-arm the blocked buy.
    receive(_offer((1750,)))
    before = len(sent)
    _evaluate(client)
    assert client._npc.view is None
    assert sent[before:] == [struct.pack("<HI", 0x146, 123)]
    assert len([r for r in caplog.records if "buy give-up" in r.getMessage()]) == 1


def test_all_offer_ids_survive_ingest_and_knife_after_eighth_row_is_found(monkeypatch, caplog):
    ids = (*range(1701, 1719), 1201)
    _wire, client, _receive, _sent = _shop(monkeypatch, ids)
    offer = client.build_native_state(Goal.GRIND).shop_offer
    assert offer is not None
    assert tuple(row.item_id for row in offer.rows) == ids
    for _ in range(6):
        _evaluate(client)
        assert client._npc.view is not None
    assert not [r for r in caplog.records if "buy give-up" in r.getMessage()]
