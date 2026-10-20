"""Detached received shop metadata; never spending, ownership or planner authority."""

from dataclasses import dataclass
from typing import Literal

from robots.domain.actions import NpcShopPurchase


@dataclass(frozen=True, slots=True)
class ReceivedZeny:
    """Historical SELF B1/20 in a continuous selected session, not a spend budget.

    Ordinary same-server warps do not change the native session epoch. No B1
    refresh is inferred or required there; later spending needs separate freshness.
    Negative wire values are retained without authorizing expenditure.
    """

    balance: int
    epoch: int
    receipt_sequence: int
    observed_at: float
    source_binding: str = "selected-self-b1-20"


@dataclass(frozen=True, slots=True)
class ReceivedShopRow:
    price: int
    discount_price: int
    item_type: int
    item_id: int


@dataclass(frozen=True, slots=True)
class ReceivedShopOffer:
    """Actor attribution is a bounded local C5 exchange, not a protocol nonce.

    Publication is current only while the original controlled context survives.
    Previously captured snapshots remain historical; their deadline is not renewed.
    """

    rows: tuple[ReceivedShopRow, ...]
    receipt_sequence: int
    observed_at: float
    deadline: float
    npc_id: int
    opened_sequence: int
    map_name: str
    epoch: int
    prompt_sequence: int
    source_binding: str = "owner-local-c5-exchange"


@dataclass(frozen=True, slots=True)
class QualifiedShopItem:
    """Explicitly trusted operator facts, NOT a disk/SQL/received-item inference.

    The injector must qualify the actual loaded item, ordinary non-script/non-market
    shop, canonical actual/client ID and stable price/discount through valid_until.
    Mere source availability is not permission. Unknown loaded weight denies send.
    Runtime binds this detached value to current owner references and C6 exchange.
    """

    source_id: str
    account_id: int
    character_id: int
    epoch: int
    npc_id: int
    map_name: str
    actual_item_id: int
    client_item_id: int
    loaded_weight: int | None
    ordinary_shop: bool
    nonstackable: bool
    stable_price: int
    stable_discount_price: int
    valid_until: float


@dataclass(frozen=True, slots=True)
class ShopPurchaseProgress:
    """Bounded local exchange disposition, not nonce-origin or zero-loss proof."""

    action: NpcShopPurchase
    status: Literal["issued", "rejected", "incomplete", "acquired"]
    reason: str
    ca_result: int | None = None
    inventory_index: int | None = None
