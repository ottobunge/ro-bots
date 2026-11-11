"""Attempt identity survives interleaving and missing pending bookkeeping."""

from dataclasses import replace

import pytest

from robots.adapters.native_gameplay import ObservedFloorItem, ObservedPickupAck, ObservedPosition
from robots.app.loot_attribution import LootAttribution


def drop(fid: int = 321, item: int = 909, seq: int = 1) -> ObservedFloorItem:
    return ObservedFloorItem(fid, item, 0, 1, ObservedPosition(43, 38, seq, 1.0))


def verdict(seq: int, item: int = 909, result: int = 0, amount: int = 1) -> ObservedPickupAck:
    return ObservedPickupAck(seq, 2.0, 2, item, amount, result, result == 0)


@pytest.mark.parametrize("second_kind", ["same_floor", "same_type", "different"])
@pytest.mark.parametrize("reverse", [False, True])
def test_interleaved_attempts_keep_their_own_number_sequence_and_context(second_kind, reverse):
    receipt = LootAttribution()
    first = drop()
    second = (
        first
        if second_kind == "same_floor"
        else drop(322, 909 if second_kind == "same_type" else 705, 2)
    )
    receipt.attempted(first, 10, context={"map": "prontera", "x": 43})
    receipt.attempted(second, 20, context={"map": "prontera", "x": 44})
    # Identical wire items have no floor ID: their only provable order is FIFO.
    reversed_items = reverse and second_kind == "different"
    order = [second, first] if reversed_items else [first, second]
    for seq, item in enumerate(order, 21):
        receipt.consume(verdict(seq, item.item_id))
    rows = [row for row in receipt.rows if row["outcome"] == "succeeded"]
    expected = [2, 1] if reversed_items else [1, 2]
    assert [row["attempt"] for row in rows] == expected
    assert [row["sent_after_seq"] for row in rows] == [n * 10 for n in expected]
    assert [row["x"] for row in rows] == [42 + n for n in expected]
    assert receipt.pending is None


def test_item_fallback_recovers_a_missed_sequence_match_without_settling_other_attempt():
    receipt = LootAttribution()
    receipt.attempted(drop(), 100, context={"map": "prontera", "x": 43})
    receipt.attempted(drop(322, 705), 10, context={"map": "prontera", "x": 44})
    receipt.consume(verdict(20))  # first attempt's sent cursor missed this ack
    row = receipt.rows[-1]
    assert (row["outcome"], row["reason"]) == ("succeeded", "attributed_by_item")
    assert (row["attempt"], row["floor_item_id"], row["sent_after_seq"]) == (1, 321, 100)
    assert receipt.pending == (drop(322, 705), 10)
    receipt.consume(verdict(21, 705))
    assert receipt.rows[-1]["attempt"] == 2
    assert receipt.pending is None


def test_dropped_pending_entry_still_attributes_by_item_and_keeps_attempt_context():
    receipt = LootAttribution()
    receipt.attempted(drop(), 10, context={"map": "prontera", "native_epoch": 7})
    receipt._pending.clear()  # reproduce lost ack-lane bookkeeping, not lost attempt history
    receipt.consume(verdict(20))
    row = receipt.rows[-1]
    assert (row["outcome"], row["reason"]) == ("succeeded", "attributed_by_item")
    assert (row["attempt"], row["floor_item_id"], row["native_epoch"]) == (1, 321, 7)
    receipt.consume(verdict(21))
    assert receipt.rows[-1]["outcome"] == "unattributed_ack"  # one verdict per attempt


@pytest.mark.parametrize("result", [0, 6])
def test_genuinely_unmatched_ack_names_itself_with_full_verdict(result):
    receipt = LootAttribution()
    receipt.consume(verdict(20, 501 if result == 0 else 0, result))
    row = receipt.rows[-1]
    assert row["outcome"] == "unattributed_ack"
    assert row["floor_item_id"] is None
    assert row["reason_code"] == result
    assert row["ack_seq"] == 20
    assert row["received_item_id"] == (501 if result == 0 else 0)


@pytest.mark.parametrize("expiry", ["absence", "replacement", "map"])
def test_item_fallback_cannot_cross_a_presence_or_map_epoch(expiry):
    receipt = LootAttribution()
    receipt.attempted(drop(), 100, context={})
    if expiry == "map":
        receipt.boundary("map_changed")
    else:
        receipt.refresh(set())
        if expiry == "replacement":
            receipt.attempted(
                replace(drop(), position=ObservedPosition(43, 38, 30, 3.0)), 100, context={}
            )
    receipt.consume(verdict(20))
    assert receipt.rows[-1]["outcome"] == "unattributed_ack"


@pytest.mark.parametrize("item", [0, 501])
def test_raw_refusal_settles_oldest_eligible_attempt_and_boundary_names_the_rest(item):
    receipt = LootAttribution()
    receipt.attempted(drop(), 10, context={"x": 43})
    receipt.attempted(drop(322, 705), 20, context={"x": 44})
    receipt.consume(verdict(21, item, 6, 0))
    assert (receipt.rows[-1]["outcome"], receipt.rows[-1]["attempt"]) == ("refused-by-server", 1)
    assert receipt.pending == (drop(322, 705), 20)
    receipt.boundary("session_changed")
    assert (receipt.rows[-1]["outcome"], receipt.rows[-1]["attempt"]) == ("unconfirmed", 2)
    assert receipt.rows[-1]["x"] == 44
    assert receipt.pending is None


def test_bounded_ledger_names_unsettled_eviction_and_never_reuses_its_context():
    receipt = LootAttribution()
    for number in range(1, 130):
        receipt.attempted(drop(number, 900 + number), 10, context={"x": number})
    evictions = [r for r in receipt.rows if r.get("reason") == "attribution_capacity"]
    assert [(r["attempt"], r["outcome"]) for r in evictions] == [(1, "unconfirmed")]
    assert len(receipt._attempts) == len(receipt._pending) == 128
    receipt.consume(verdict(20, 901))
    assert receipt.rows[-1]["outcome"] == "unattributed_ack"
    receipt.consume(verdict(21, 902))
    assert (receipt.rows[-1]["attempt"], receipt.rows[-1]["x"]) == (2, 2)
