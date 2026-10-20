"""MAIN20180704/pre-re shop wire values, never permission or acquisition proof."""

import struct
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ShopOfferRow:
    """Received unsigned prices, opaque item type and active 16-bit client item ID."""

    price: int
    discount_price: int
    item_type: int
    item_id: int


@dataclass(frozen=True)
class ShopOffer:
    """A received list carries no NPC identity, session or freshness authority."""

    rows: tuple[ShopOfferRow, ...]


@dataclass(frozen=True)
class PurchaseEntry:
    """Client item ID and quantity only; no implicit NPC or request nonce."""

    item_id: int
    quantity: int


@dataclass(frozen=True)
class DealTypeMarker:
    """Raw received NPC ID, not NPC classification or interaction permission."""

    npc_id: int


@dataclass(frozen=True)
class PurchaseResult:
    """Uncorrelated raw byte; success text does not prove any inventory acquisition."""

    result: int

    @property
    def reports_success(self) -> bool:
        """Only byte0 reports ordinary purchase success in this source profile."""
        return self.result == 0


def _fixed_header(raw: bytes, header: int, length: int) -> None:
    if len(raw) != length or struct.unpack_from("<H", raw)[0] != header:
        message = "wrong shop receipt header or exact length"
        raise ValueError(message)


def decode_deal_type(raw: bytes) -> DealTypeMarker:
    """Decode C4 without granting shop actor identity."""
    _fixed_header(raw, 0xC4, 6)
    return DealTypeMarker(struct.unpack_from("<I", raw, 2)[0])


def decode_purchase_result(raw: bytes) -> PurchaseResult:
    """Preserve every possible CA result, including unknown future values."""
    _fixed_header(raw, 0xCA, 3)
    return PurchaseResult(raw[2])


@dataclass(frozen=True)
class ReceivedCurrency:
    """Historical signed received Zeny, or explicit unreceived; no freshness claim."""

    balance: int | None = None


def decode_currency(raw: bytes) -> ReceivedCurrency | None:
    """Decode source-emitted B1 parameter20; B0 is not this profile's Zeny sender.

    None means an unrelated well-shaped status frame, not a zero balance.
    ReceivedCurrency() represents an unreceived balance independently of that filter.
    """
    if len(raw) != 8:
        message = "currency status must be exactly eight bytes"
        raise ValueError(message)
    header, parameter, balance = struct.unpack("<HHi", raw)
    if header not in (0xB0, 0xB1):
        message = "wrong currency status header"
        raise ValueError(message)
    if header != 0xB1 or parameter != 20:
        return None
    return ReceivedCurrency(balance)


def _positive_uint(value: int, maximum: int) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        message = "expected nonzero unsigned integer, not bool"
        raise ValueError(message)
    return value


def encode_buy_selection(npc_id: int) -> bytes:
    """Represent explicit C5 type0 buy selection; do not classify or click actors."""
    return struct.pack("<HIB", 0xC5, _positive_uint(npc_id, 0xFFFFFFFF), 0)


def encode_purchase(entries: Sequence[PurchaseEntry]) -> bytes:
    """Represent C8, bounded to 64 entries (engineering policy, not server maximum)."""
    if not 1 <= len(entries) <= 64:
        message = "purchase requires 1..64 entries"
        raise ValueError(message)
    rows = b"".join(
        struct.pack(
            "<HH", _positive_uint(entry.quantity, 65535), _positive_uint(entry.item_id, 65535)
        )
        for entry in entries
    )
    # At most 260 bytes: valid for both signed C++ packetLength and RFIFOW wire length.
    return struct.pack("<HH", 0xC8, 4 + len(rows)) + rows


def decode_shop_offer(raw: bytes) -> ShopOffer:
    """Decode already-framed legacy C6 bytes without consulting an item catalogue."""
    if len(raw) < 4 or len(raw) > 708:
        message = "shop offer exceeds bounded prefix/64-row policy"
        raise ValueError(message)
    header, declared = struct.unpack_from("<HH", raw)
    if header != 0xC6 or declared != len(raw) or (len(raw) - 4) % 11 or len(raw) == 4:
        message = "invalid shop offer header, length or row geometry"
        raise ValueError(message)
    rows = tuple(ShopOfferRow(*row) for row in struct.iter_unpack("<IIBH", raw[4:]))
    if any(row.item_id == 0 for row in rows):
        message = "zero client item ID is outside this codec policy"
        raise ValueError(message)
    return ShopOffer(rows)
