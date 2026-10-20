"""Pinned MAIN20180704 pre-re equipment byte representations, without actuation.

Authority: protocol/main-20180704-pre-re-equipment.json and its unchanged-header
GCC/Clang measurements. These are single-frame immutable observations, not current
inventory/session trackers. No quantity, bonus, expiry interpretation, eligibility,
ownership, request correlation, or successful application is inferred. Preserve
opaque spare flags and all five option slots, including slots beyond option_count.

Before any actual use of request bytes, the caller must verify a current owned
inventory in the matching session, class/level/sex/slot legality and other server
constraints, adopt receive framing and correlate a fresh ACK. A send or silence
never establishes success; even a decoded success for another index/epoch does not
apply to the account. This module deliberately provides no transport or actuator.
"""

import struct
from dataclasses import dataclass
from enum import IntEnum


class EquipResult(IntEnum):
    SUCCESS = 0
    LEVEL_FAILURE = 1
    FAILURE = 2


class UnequipResult(IntEnum):
    SUCCESS = 0
    FAILURE = 1


@dataclass(frozen=True, slots=True)
class UnequipAcknowledgement:
    inventory_index: int
    wear_location: int
    raw_flag: int
    result: UnequipResult | None


def decode_unequip_ack(data: bytes) -> UnequipAcknowledgement:
    """Decode only; this does not apply a session outcome."""
    _fixed_frame(data, 0x099A, 9)
    _, index, wear, raw = struct.unpack("<HHIB", data)
    _integer(index, 2, 65535)
    result = UnequipResult(raw) if raw in (0, 1) else None
    return UnequipAcknowledgement(index, wear, raw, result)


def encode_equip_request(inventory_index: int, position: int) -> bytes:
    """Represent bytes only, without asserting equip eligibility."""
    _integer(inventory_index, 2, 65535)
    _integer(position, 0, 0xFFFFFFFF)
    return struct.pack("<HHI", 0x0998, inventory_index, position)


def encode_unequip_request(inventory_index: int) -> bytes:
    """Represent bytes only, without asserting ownership or current wear."""
    _integer(inventory_index, 2, 65535)
    return struct.pack("<HH", 0x00AB, inventory_index)


@dataclass(frozen=True, slots=True)
class EquipAcknowledgement:
    inventory_index: int
    wear_location: int
    sprite: int
    raw_result: int
    result: EquipResult | None


def decode_equip_ack(data: bytes) -> EquipAcknowledgement:
    """Decode only; this does not correlate a request or establish ownership."""
    _fixed_frame(data, 0x0999, 11)
    _, index, wear, sprite, raw = struct.unpack("<HHIHB", data)
    _integer(index, 2, 65535)
    result = EquipResult(raw) if raw in (0, 1, 2) else None
    return EquipAcknowledgement(index, wear, sprite, raw, result)


def _integer(value: int, minimum: int, maximum: int) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        message = "expected an exact integer within the supported wire representation"
        raise ValueError(message)


def _fixed_frame(data: bytes, header: int, size: int) -> None:
    if type(data) is not bytes or len(data) != size or int.from_bytes(data[:2], "little") != header:
        message = "incorrect equipment frame header or complete length"
        raise ValueError(message)


@dataclass(frozen=True, slots=True)
class ItemOption:
    index: int
    value: int
    param: int


@dataclass(frozen=True, slots=True)
class EquipmentItem:
    inventory_index: int
    item_id: int
    allowed_locations: int
    wear_state: int
    item_type: int
    refine: int
    cards: tuple[int, int, int, int]
    hire_expire_date: int
    bind_on_equip_type: int
    sprite: int
    option_count: int
    options: tuple[ItemOption, ...]
    raw_flags: int

    @property
    def identified(self) -> bool:
        return bool(self.raw_flags & 1)

    @property
    def damaged(self) -> bool:
        return bool(self.raw_flags & 2)

    @property
    def place_etc_tab(self) -> bool:
        return bool(self.raw_flags & 4)

    @property
    def spare_bits(self) -> int:
        return self.raw_flags >> 3


def decode_equipment_list(data: bytes) -> tuple[EquipmentItem, ...]:
    """Decode a single equipment-list frame, not inventory completeness."""
    if type(data) is not bytes or not 4 <= len(data) <= 32767:
        message = "equipment list requires a complete signed16-length frame"
        raise ValueError(message)
    header, length = struct.unpack_from("<Hh", data)
    if header != 0x0A0D or length != len(data) or (length - 4) % 57:
        message = "equipment list header, length or row boundary mismatch"
        raise ValueError(message)
    items = tuple(_equipment_item(data, offset) for offset in range(4, length, 57))
    if len({item.inventory_index for item in items}) != len(items):
        message = "duplicate equipment inventory index"
        raise ValueError(message)
    return items


def _equipment_item(data: bytes, offset: int) -> EquipmentItem:
    index: int = struct.unpack_from("<h", data, offset)[0]
    item_id: int = struct.unpack_from("<H", data, offset + 2)[0]
    option_count = data[offset + 30]
    _integer(index, 2, 32767)
    _integer(item_id, 1, 65535)
    _integer(option_count, 0, 5)
    return EquipmentItem(
        inventory_index=index,
        item_id=item_id,
        allowed_locations=struct.unpack_from("<I", data, offset + 5)[0],
        wear_state=struct.unpack_from("<I", data, offset + 9)[0],
        item_type=data[offset + 4],
        refine=data[offset + 13],
        cards=struct.unpack_from("<4H", data, offset + 14),
        hire_expire_date=struct.unpack_from("<i", data, offset + 22)[0],
        bind_on_equip_type=struct.unpack_from("<H", data, offset + 26)[0],
        sprite=struct.unpack_from("<H", data, offset + 28)[0],
        option_count=option_count,
        options=tuple(
            ItemOption(*struct.unpack_from("<hhB", data, offset + 31 + number * 5))
            for number in range(5)
        ),
        raw_flags=data[offset + 56],
    )
