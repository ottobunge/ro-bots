"""Offline synthetic wire contracts; these are not received gear observations."""

import hashlib
import json
import struct
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from robots.adapters.native_equipment import (
    EquipResult,
    UnequipResult,
    decode_equip_ack,
    decode_equipment_list,
    decode_unequip_ack,
    encode_equip_request,
    encode_unequip_request,
)


def row(wear: int = 0) -> bytes:
    data = bytearray(57)
    struct.pack_into("<hHBII", data, 0, 9, 1201, 4, 0x22, wear)
    return bytes(data)


def frame(*rows: bytes) -> bytes:
    payload = b"".join(rows)
    return struct.pack("<HH", 0x0A0D, 4 + len(payload)) + payload


def test_actual_wear_is_separate_from_allowed_locations() -> None:
    items = decode_equipment_list(frame(row(0)))
    assert len(items) == 1
    assert items[0].allowed_locations == 0x22
    assert items[0].wear_state == 0
    assert items[0].inventory_index == 9
    assert items[0].item_id == 1201
    assert decode_equipment_list(frame(row(0x20)))[0].wear_state == 0x20


def test_equip_ack_active_success_level_failure_and_error() -> None:
    for raw, expected in enumerate(
        (EquipResult.SUCCESS, EquipResult.LEVEL_FAILURE, EquipResult.FAILURE)
    ):
        ack = decode_equip_ack(struct.pack("<HHIHB", 0x0999, 9, 0x20, 42, raw))
        assert ack.result is expected
        assert ack.raw_result == raw
        assert (ack.inventory_index, ack.wear_location, ack.sprite) == (9, 0x20, 42)


def test_complete_received_metadata_preserves_signed_options_and_opaque_flags() -> None:
    data = bytearray(row(0x20))
    struct.pack_into("<B4HiHHB", data, 13, 17, 1, 2, 65535, 4, -123, 2, 65535, 2)
    for number in range(5):
        struct.pack_into("<hhB", data, 31 + number * 5, number - 2, -300 + number, 255)
    data[56] = 0xAD
    item = decode_equipment_list(frame(bytes(data)))[0]
    assert hasattr(item, "options"), "complete item metadata is not implemented"
    assert item.item_type == 4
    assert item.refine == 17
    assert item.cards == (1, 2, 65535, 4)
    assert item.hire_expire_date == -123
    assert item.bind_on_equip_type == 2
    assert item.sprite == 65535
    assert item.option_count == 2
    assert tuple((o.index, o.value, o.param) for o in item.options) == tuple(
        (number - 2, -300 + number, 255) for number in range(5)
    )
    assert item.raw_flags == 0xAD
    assert item.identified is True
    assert item.damaged is False
    assert item.place_etc_tab is True
    assert item.spare_bits == 21
    data[56] = 255
    item = decode_equipment_list(frame(bytes(data)))[0]
    assert item.identified
    assert item.damaged
    assert item.place_etc_tab
    assert item.spare_bits == 31
    data[30] = 0  # The pinned sender sets count0 even for present random options.
    item = decode_equipment_list(frame(bytes(data)))[0]
    assert item.option_count == 0
    assert item.options[0].value == -300


@pytest.mark.parametrize(
    "data",
    [
        b"\r\x0a\x04",
        struct.pack("<HH", 0x0992, 61) + row(),
        struct.pack("<HH", 0x0A0D, 60) + row(),
        frame(row()[:-1]),
        frame(row()) + b"\0",
        frame(row(), row()),
    ],
)
def test_list_rejects_invalid_complete_frame(data: bytes) -> None:
    with pytest.raises(ValueError, match=r"equipment|duplicate|exact integer"):
        decode_equipment_list(data)


def test_list_rejects_reserved_indices_nonpositive_id_and_option_overflow() -> None:
    for offset, fmt, value in ((0, "<h", -1), (0, "<h", 1), (2, "<H", 0), (30, "<B", 6)):
        data = bytearray(row())
        struct.pack_into(fmt, data, offset, value)
        with pytest.raises(ValueError, match=r"equipment|duplicate|exact integer"):
            decode_equipment_list(frame(bytes(data)))


def test_empty_list_is_empty_not_an_inventory_completion_barrier() -> None:
    assert decode_equipment_list(frame()) == ()


def test_immutable_items_and_options() -> None:
    item = decode_equipment_list(frame(row()))[0]
    for target, attribute, value in ((item, "wear_state", 32), (item.options[0], "value", 10)):
        with pytest.raises(FrozenInstanceError):
            setattr(target, attribute, value)


def test_unknown_ack_results_stay_unknown() -> None:
    equip = decode_equip_ack(struct.pack("<HHIHB", 0x0999, 65535, 0xFFFFFFFF, 65535, 255))
    assert equip.result is None
    assert equip.raw_result == 255
    assert equip.inventory_index == 65535
    unequip = decode_unequip_ack(struct.pack("<HHIB", 0x099A, 9, 0xFFFFFFFF, 255))
    assert unequip.result is None
    assert unequip.raw_flag == 255


def test_unequip_ack_zero_means_success() -> None:
    for raw, expected in enumerate((UnequipResult.SUCCESS, UnequipResult.FAILURE)):
        ack = decode_unequip_ack(struct.pack("<HHIB", 0x099A, 9, 0x20, raw))
        assert ack.result is expected
        assert (ack.inventory_index, ack.wear_location, ack.raw_flag) == (9, 0x20, raw)


def test_ack_rejects_wrong_header_length_and_reserved_index() -> None:
    for decoder, valid in (
        (decode_equip_ack, struct.pack("<HHIHB", 0x0999, 9, 32, 1, 0)),
        (decode_unequip_ack, struct.pack("<HHIB", 0x099A, 9, 32, 0)),
    ):
        for bad in (
            valid[:-1],
            valid + b"\0",
            b"\0\0" + valid[2:],
            valid[:2] + b"\1\0" + valid[4:],
        ):
            with pytest.raises(ValueError, match=r"equipment|duplicate|exact integer"):
                decoder(bad)


def test_request_encoders_preserve_wire_indices_and_all_uint32_mask_bits() -> None:
    assert encode_equip_request(9, 0x20) == struct.pack("<HHI", 0x0998, 9, 0x20)
    assert encode_equip_request(65535, 0xFFFFFFFF) == bytes.fromhex("9809ffffffffffff")
    assert encode_equip_request(2, 0) == struct.pack("<HHI", 0x0998, 2, 0)
    assert encode_unequip_request(9) == bytes.fromhex("ab000900")
    assert encode_unequip_request(65535) == bytes.fromhex("ab00ffff")


def test_encoders_reject_non_exact_integer_and_out_of_representation_values() -> None:
    invalid_indices: tuple[Any, ...] = (True, 9.0, "9", -1, 0, 1, 65536)
    for index in invalid_indices:
        with pytest.raises(ValueError, match=r"equipment|duplicate|exact integer"):
            encode_equip_request(index, 32)
        with pytest.raises(ValueError, match=r"equipment|duplicate|exact integer"):
            encode_unequip_request(index)
    invalid_masks: tuple[Any, ...] = (True, 32.0, "32", -1, 0x100000000)
    for mask in invalid_masks:
        with pytest.raises(ValueError, match=r"equipment|duplicate|exact integer"):
            encode_equip_request(9, mask)


def test_positive_identifier_and_card_widths_are_not_gameplay_capacity() -> None:
    data = bytearray(row())
    struct.pack_into("<hH", data, 0, 32767, 65535)
    struct.pack_into("<4H", data, 14, 65535, 65534, 65533, 65532)
    struct.pack_into("<i", data, 22, 2147483647)
    item = decode_equipment_list(frame(bytes(data)))[0]
    assert item.inventory_index == 32767
    assert item.item_id == 65535
    assert item.cards == (65535, 65534, 65533, 65532)
    assert item.hire_expire_date == 2147483647


def test_decode_requires_bytes_and_signed_length_boundaries() -> None:
    bad_frames: tuple[Any, ...] = (
        None,
        True,
        bytearray(frame()),
        frame().hex(),
        b"",
        b"\0" * 32768,
    )
    for data in bad_frames:
        with pytest.raises(ValueError, match="equipment"):
            decode_equipment_list(data)
        with pytest.raises(ValueError, match="equipment"):
            decode_equip_ack(data)
        with pytest.raises(ValueError, match="equipment"):
            decode_unequip_ack(data)


def test_manifest_matches_fresh_compiler_layout_and_immutable_authority() -> None:
    path = Path(__file__).resolve().parents[1] / "protocol/main-20180704-pre-re-equipment.json"
    manifest = json.loads(path.read_text())
    assert manifest["profile"] == {
        "role": "map",
        "packetver": 20180704,
        "client_family": "MAIN",
        "ruleset": "pre-re",
        "obfuscation": "ABSENT",
    }
    measured = manifest["measurements"]
    record = measured["records"]["EQUIPITEM_INFO"]
    assert record["size"] == len(row()) == 57
    assert record["fields"]["ITID"] == {"offset": 2, "width": 2}
    assert record["fields"]["location"] == {"offset": 5, "width": 4}
    assert record["fields"]["WearState"] == {"offset": 9, "width": 4}
    assert measured["flags_byte_masks"] == {
        "IsIdentified": 1,
        "IsDamaged": 2,
        "PlaceETCTab": 4,
        "SpareBits": 248,
    }
    assert measured["equip_results"] == {"success": 0, "level_failure": 1, "failure": 2}
    assert measured["max_item_options"] == 5
    source = path.parents[1] / "run/public-source/callback-qualified-e985006171d2"
    for relative, expected in manifest["header_and_sender_sha256"].items():
        assert hashlib.sha256((source / relative).read_bytes()).hexdigest() == expected
