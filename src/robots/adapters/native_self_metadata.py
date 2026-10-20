"""Trusted operator-injected helper data; no SQL, shared readers or effects.

The caller is the publisher trust boundary, not hostile-same-user security.
Unix read time remains historical metadata and is never a native freshness clock.
"""

import math
import re
import sys
from typing import Any

from robots.domain.self_metadata import ServerSelfSlots

PROVENANCE = "operator/server-verified offline DB snapshot"
_ENVELOPE = {
    "passed": True,
    "read_only": True,
    "native_sessions_opened": 0,
    "inference_calls": 0,
    "native_gameplay_acceptance": False,
}
_METADATA = {
    "scope",
    "account_id",
    "char_id",
    "name",
    "inventory_slots",
    "provenance",
    "atomic_online_state",
    "native_packet",
    "purchase_authorized",
}


def _helper_metadata(proof: object) -> dict[str, Any] | None:
    if type(proof) is not dict or set(proof) != {*_ENVELOPE, "selected_owner_metadata"}:
        return None
    if not all(
        type(proof[key]) is type(value) and proof[key] == value for key, value in _ENVELOPE.items()
    ):
        return None
    metadata = proof["selected_owner_metadata"]
    return metadata if type(metadata) is dict and set(metadata) == _METADATA else None


def _valid_metadata(metadata: dict[str, Any], owner: tuple[int, int, str]) -> bool:
    return all(
        (
            type(metadata["account_id"]) is int and 0 < metadata["account_id"] <= 0xFFFFFFFF,
            type(metadata["char_id"]) is int and 0 < metadata["char_id"] <= 0xFFFFFFFF,
            type(metadata["name"]) is str,
            (metadata["account_id"], metadata["char_id"], metadata["name"]) == owner,
            type(metadata["inventory_slots"]) is int and 0 <= metadata["inventory_slots"] <= 100,
            type(metadata["scope"]) is str and metadata["scope"] == "SELF",
            type(metadata["provenance"]) is str and metadata["provenance"] == PROVENANCE,
            metadata["atomic_online_state"] is False,
            metadata["native_packet"] is False,
            metadata["purchase_authorized"] is False,
        )
    )


def _valid_source(source_id: str, observed_at_unix: float, login_ip: str, login_port: int) -> bool:
    return all(
        (
            type(source_id) is str
            and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", source_id) is not None,
            type(observed_at_unix) in (int, float)
            and 0 <= observed_at_unix <= sys.float_info.max
            and math.isfinite(observed_at_unix),
            type(login_ip) is str and 0 < len(login_ip) <= 255,
            type(login_port) is int and 0 < login_port <= 65535,
        )
    )


def server_self_slots(
    proof: object,
    *,
    source_id: str,
    observed_at_unix: float,
    login_ip: str,
    login_port: int,
    session_epoch: int,
    owner: tuple[int, int, str],
    endpoint: tuple[str, int],
) -> ServerSelfSlots | None:
    metadata = _helper_metadata(proof)
    if metadata is None or not _valid_metadata(metadata, owner):
        return None
    if not _valid_source(source_id, observed_at_unix, login_ip, login_port):
        return None
    if (login_ip, login_port) != endpoint:
        return None
    return ServerSelfSlots(
        account_id=metadata["account_id"],
        char_id=metadata["char_id"],
        name=metadata["name"],
        inventory_slots=metadata["inventory_slots"],
        source_id=source_id,
        observed_at_unix=observed_at_unix,
        login_ip=login_ip,
        login_port=login_port,
        session_epoch=session_epoch,
        provenance=PROVENANCE,
    )
