"""Equip-from-inventory progression slice: synthetic wire contracts only.

Pinned authority (rathena e985006171d2, MAIN/pre-re 20180704): CZ_REQ_WEAR_EQUIP
0x0998 <index>.W <position>.L (packets.hpp:1503-1509 MAIN>=20120925 branch,
clif_packetdb.hpp:58, measured 8B in protocol/main-20180704-pre-re-equipment.json);
ack ZC_ACK_WEAR_EQUIP_V5 0x0999 <index>.W <wear location>.L <view id>.W <result>.B
(packets_struct.hpp:1270-1276, 11B) with ITEM_EQUIP_ACK_OK=0 / FAIL=2 /
FAILLEVEL=1 for MAIN>=20121205 (clif.hpp:523-532), sent verbatim as p.result
(clif.cpp:4313-4326). Indices on both directions are client-side inventory
indices (clif.cpp:122-127, clif.cpp:3084-3099). These tests are not live
gameplay evidence.
"""

import struct

import pytest

from robots.adapters.native_gameplay import EQP_HAND_R, NativeGameplayTracker, equip
from robots.app import playing_runtime as runtime
from robots.app.scripts import NOVICE_WANTED_WEAPONS, novice_weapon_index
from robots.domain.actions import Attack
from tests.test_playing_runtime import Wire


def ack(index: int, wear: int, sprite: int, raw_result: int) -> bytes:
    return struct.pack("<HHIHB", 0x0999, index, wear, sprite, raw_result)


def auth() -> bytes:
    raw = bytearray(13)
    struct.pack_into("<H", raw, 0, 0x02EB)
    raw[6:9] = bytes([10, 0x82, 0x50])
    return bytes(raw)


def inventory_row(index: int, item: int) -> bytes:
    raw = bytearray(4 + 24)
    struct.pack_into("<HHHH", raw, 0, 0x0991, len(raw), index, item)
    struct.pack_into("<h", raw, 9, 1)
    return bytes(raw)


WEIGHT = struct.pack("<HHi", 0x00B0, 24, 0)


def tracker_with_knife() -> NativeGameplayTracker:
    tracker = NativeGameplayTracker(999)
    assert tracker.consume_snapshot(
        1,
        0,
        (
            (1, 1.0, 0x02EB, auth()),
            (2, 2.0, 0x0991, inventory_row(4, 1202)),
            (3, 3.0, 0x00B0, WEIGHT),
        ),
    )
    return tracker


def test_equip_encoder_uses_pinned_v5_layout() -> None:
    assert equip(4) == struct.pack("<HHI", 0x0998, 4, EQP_HAND_R)
    assert equip(4) == struct.pack("<HHI", 0x0998, 4, 2)
    assert equip(4, position=0x20) == struct.pack("<HHI", 0x0998, 4, 0x20)


def test_equip_encoder_rejects_non_wire_index() -> None:
    for bad in (0, 1, -1, True, 2**16):
        with pytest.raises(ValueError, match="wire representation"):
            equip(bad)


def test_success_ack_marks_index_worn_and_is_recorded() -> None:
    tracker = tracker_with_knife()
    assert tracker.consume_snapshot(1, 3, ((4, 4.0, 0x0999, ack(4, 2, 42, 0)),))
    assert tracker.view.worn == ((4, 2),)
    assert len(tracker.view.equip_acks) == 1
    observed = tracker.view.equip_acks[0]
    assert (observed.inventory_index, observed.wear_location, observed.raw_result) == (4, 2, 0)
    assert observed.success is True


def test_failure_acks_do_not_mark_worn_but_stay_recorded() -> None:
    tracker = tracker_with_knife()
    assert tracker.consume_snapshot(
        1,
        3,
        (
            (4, 4.0, 0x0999, ack(4, 2, 42, 2)),  # ITEM_EQUIP_ACK_FAIL
            (5, 5.0, 0x0999, ack(4, 2, 42, 1)),  # ITEM_EQUIP_ACK_FAILLEVEL
            (6, 6.0, 0x0999, ack(4, 2, 42, 7)),  # unknown raw preserved
        ),
    )
    assert tracker.view.worn == ()
    assert [a.raw_result for a in tracker.view.equip_acks] == [2, 1, 7]
    assert [a.success for a in tracker.view.equip_acks] == [False, False, False]


def test_malformed_ack_length_denies_snapshot() -> None:
    tracker = tracker_with_knife()
    assert not tracker.consume_snapshot(1, 3, ((4, 4.0, 0x0999, ack(4, 2, 42, 0)[:-1]),))
    assert tracker.view.worn == ()


def test_new_epoch_clears_worn_to_unknown() -> None:
    tracker = tracker_with_knife()
    assert tracker.consume_snapshot(1, 3, ((4, 4.0, 0x0999, ack(4, 2, 42, 0)),))
    assert tracker.consume_snapshot(2, 0, ())
    assert tracker.view.worn == ()
    assert tracker.view.equip_acks == ()


def test_wanted_weapons_include_the_pinned_poring_drop() -> None:
    # mob_db.yml Poring 1002 drops AegisName "Knife_" (Rate 100) which is item
    # 1202 in item_db_equip.yml (Id: 1202 AegisName: Knife_), NOT 1201. 1201
    # (Knife) and 1204 (Cutter) are the other Novice-wearable pinned daggers.
    assert 1202 in NOVICE_WANTED_WEAPONS
    assert 1201 in NOVICE_WANTED_WEAPONS
    assert 1204 in NOVICE_WANTED_WEAPONS


def test_rule_returns_unworn_wanted_index_only_for_known_novice_stock() -> None:
    stock = ((4, 1202, 1), (7, 909, 3), (9, 1204, 1))
    assert novice_weapon_index(stock, (), job="Novice") == 4
    assert novice_weapon_index(stock, ((4, 2),), job="Novice") == 9
    assert novice_weapon_index(stock, ((4, 2), (9, 2)), job="Novice") is None
    assert novice_weapon_index(None, (), job="Novice") is None
    assert novice_weapon_index(stock, (), job="Swordman") is None
    assert novice_weapon_index(((7, 909, 3),), (), job="Novice") is None


def _runtime_wire() -> runtime.PlayingClient:
    return runtime.PlayingClient(Wire())


def test_runtime_dispatch_sends_bounded_equip_requests() -> None:
    client = _runtime_wire()
    wire = client.wire
    wire.add(auth(), inventory_row(4, 1202), WEIGHT)
    equip_bytes = struct.pack("<HHI", 0x0998, 4, 2)
    client.perform_native(Attack(123))
    assert wire.sent.count(equip_bytes) == 1
    # A second dispatch before any ack stays bounded: no spam while unknown.
    client.perform_native(Attack(123))
    assert wire.sent.count(equip_bytes) == 2
    # Success ack closes the rule for this epoch.
    wire.add(ack(4, 2, 42, 0))
    client.perform_native(Attack(123))
    client.perform_native(Attack(123))
    assert wire.sent.count(equip_bytes) == 2
    assert client._tracker is not None
    assert client._tracker.view.worn == ((4, 2),)


def test_runtime_equip_attempts_cap_per_epoch() -> None:
    client = _runtime_wire()
    wire = client.wire
    wire.add(auth(), inventory_row(4, 1202), WEIGHT)
    equip_bytes = struct.pack("<HHI", 0x0998, 4, 2)
    for _ in range(6):
        client.perform_native(Attack(123))
    assert wire.sent.count(equip_bytes) == 3
    # A new epoch re-arms the bounded budget (worn returns to unknown).
    wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    client.perform_native(Attack(123))
    assert wire.sent.count(equip_bytes) == 4


def test_runtime_dispatch_without_wanted_weapon_sends_no_equip() -> None:
    client = _runtime_wire()
    wire = client.wire
    wire.add(auth(), inventory_row(4, 909), WEIGHT)
    client.perform_native(Attack(123))
    assert not [s for s in wire.sent if isinstance(s, bytes) and s[:2] == b"\x98\x09"]
