"""Detached advisory capacity shared by decision and investigation consumers."""

from dataclasses import asdict
from typing import Any

from robots.domain.capacity import ReceivedCapacity
from robots.domain.model import BotState
from robots.domain.self_metadata import ServerSelfSlots


def _native_facts(receipt: ReceivedCapacity | None) -> dict[str, Any]:
    if receipt is None:
        return {"status": "UNKNOWN"}
    result = asdict(receipt)
    result.update(
        status="RECEIVED" if receipt.complete else "PARTIAL",
        source=result.pop("source_binding"),
        units="raw_engine_counts",
        clock="monotonic",
        complete=receipt.complete,
        nonnegative=receipt.nonnegative,
    )
    return result


def _slot_facts(receipt: ServerSelfSlots | None) -> dict[str, Any]:
    if receipt is None:
        return {"status": "UNKNOWN"}
    result = asdict(receipt)
    del result["login_ip"], result["login_port"]
    result.update(status="OFFLINE_SERVER_METADATA", clock="unix")
    return result


def inventory_capacity_facts(state: BotState) -> dict[str, Any]:
    """Expose capacity without granting any purchase permission."""
    native = state.capacity_receipt
    slots = state.server_self_slots
    return {
        "weight": native.weight.value if native is not None and native.weight is not None else None,
        "max_weight": (
            native.max_weight.value
            if native is not None and native.max_weight is not None
            else None
        ),
        "inventory_slots": slots.inventory_slots if slots is not None else None,
        "purchase_authorized": False,
        "native_capacity": _native_facts(native),
        "server_self_slots": _slot_facts(slots),
    }
