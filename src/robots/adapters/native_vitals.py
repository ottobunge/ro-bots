"""Pure projection of received MAIN/pre-re 20180704 SELF status parameters.

map.hpp:498-505 defines IDs 5/6/7/8; clif.cpp:3548-3557 sends packed
ZC_PAR_CHANGE (<HHi). HP is client presentation, not alive/dead truth:
clif.cpp:3683-3690 can present HP=1 on death. No persona/default values.
"""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class NativeVitals:
    """Received client-presented vitals, not a server life-state assertion."""

    hp: int
    max_hp: int
    sp: int
    max_sp: int


class NativeTelemetryUnavailableError(ValueError):
    """Required native status is absent or invalid; never synthesize health."""


NativeTelemetryUnavailable = NativeTelemetryUnavailableError


def _received_values(parameters: Mapping[int, int]) -> list[int]:
    """Copy before validation; no mutable source is retained in the read model."""
    snapshot = dict(parameters)
    message = "native vitals unavailable"
    if any(type(parameter) is not int for parameter in snapshot) or not all(
        parameter in snapshot for parameter in (5, 6, 7, 8)
    ):
        raise NativeTelemetryUnavailable(message)
    return [snapshot[parameter] for parameter in (5, 6, 7, 8)]


def require_native_vitals(parameters: Mapping[int, int]) -> NativeVitals:
    """Deny incomplete, invalid or transiently inconsistent received status.

    Only exact built-in integer keys/counts are accepted, never repaired. The
    snapshot isolates later mutation, not arbitrary mapping callbacks or a
    multi-packet transaction. Callers must also gate transport/dispatch health.
    """
    values = _received_values(parameters)
    message = "native vitals unavailable"
    if any(type(value) is not int or not 0 <= value <= 2**31 - 1 for value in values):
        raise NativeTelemetryUnavailable(message)
    hp, max_hp, sp, max_sp = values
    if max_hp == 0 or hp > max_hp or sp > max_sp:
        raise NativeTelemetryUnavailable(message)
    return NativeVitals(hp, max_hp, sp, max_sp)
