"""Detached operator/server metadata, never a native receipt or spending grant."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ServerSelfSlots:
    """Offline SELF slot allowance; read time is Unix, not receive freshness."""

    account_id: int
    char_id: int
    name: str
    inventory_slots: int
    source_id: str
    observed_at_unix: float
    login_ip: str
    login_port: int
    session_epoch: int
    provenance: str
    scope: Literal["SELF"] = "SELF"
    atomic_online_state: Literal[False] = False
    native_packet: Literal[False] = False
    purchase_authorized: Literal[False] = False
