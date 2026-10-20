"""Pure MAIN/pre-re PACKETVER20180704 selected-character projection.

Caller owns selection, transport epochs and job freshness; this module supplies
neither live receipt nor continuous actual-job refresh authority.
"""

import struct
from collections.abc import Mapping
from dataclasses import dataclass

from robots.adapters.native_vitals import NativeTelemetryUnavailable


@dataclass(frozen=True)
class SelectedCharacterSnapshot:
    """Raw actual class and historical levels from one selected CHARACTER_INFO."""

    raw_char_id: int
    raw_job_id: int
    snapshot_base_level: int
    snapshot_job_level: int
    slot: int
    sex: int


@dataclass(frozen=True)
class NativeProgression:
    """Detached supported actual class plus received current SELF levels."""

    job: str
    raw_job_id: int
    base_level: int
    job_level: int


def decode_selected_character_snapshot(row: bytes) -> SelectedCharacterSnapshot:
    """Decode exact155-byte CHARACTER_INFO; reject malformed input before unpack.

    Pinned packets.hpp/char.cpp: uint32 charID@0, int32 joblevel@24,
    int16 actual job@64, int16 baselevel@72, uint8 slot@118 and sex@154.
    Signed values remain raw; selection and meaning are not inferred here.
    """
    if type(row) is not bytes or len(row) != 155:
        message = "native character snapshot unavailable"
        raise ValueError(message)
    return SelectedCharacterSnapshot(
        struct.unpack_from("<I", row, 0)[0],
        struct.unpack_from("<h", row, 64)[0],
        struct.unpack_from("<h", row, 72)[0],
        struct.unpack_from("<i", row, 24)[0],
        row[118],
        row[154],
    )


def _require_selected_snapshot(
    snapshot: SelectedCharacterSnapshot | None, job_fresh: bool
) -> SelectedCharacterSnapshot:
    """Require explicit freshness and a bounded, exact selected identity/class."""
    message = "native progression unavailable"
    if (
        type(snapshot) is not SelectedCharacterSnapshot
        or job_fresh is not True
        or type(snapshot.raw_job_id) is not int
        or snapshot.raw_job_id != 0
        or type(snapshot.raw_char_id) is not int
        or not 0 < snapshot.raw_char_id <= 2**32 - 1
    ):
        raise NativeTelemetryUnavailable(message)
    return snapshot


def _received_levels(level_params: Mapping[int, int]) -> tuple[int, int]:
    """Copy current SELF parameters; never substitute historical snapshot levels."""
    message = "native progression unavailable"
    parameters = dict(level_params)
    if any(type(key) is not int for key in parameters) or not all(
        key in parameters for key in (11, 55)
    ):
        raise NativeTelemetryUnavailable(message)
    levels = [parameters[key] for key in (11, 55)]
    if any(type(level) is not int or not 0 < level <= 2**31 - 1 for level in levels):
        raise NativeTelemetryUnavailable(message)
    return levels[0], levels[1]


def require_native_progression(
    snapshot: SelectedCharacterSnapshot | None,
    level_params: Mapping[int, int],
    *,
    job_fresh: bool,
) -> NativeProgression:
    """Deny absent/stale/unsupported actual class or incomplete current levels.

    Only source-verified JOB_NOVICE=0 is supported. IDs11/55 are received
    SELF levels, not snapshot fallbacks. Caller must bind selection/transport
    epochs and invalidate job freshness on relevant LOOK_BASE/transport changes.
    The copied mapping is not an atomic multi-packet transaction or protection
    against arbitrary mapping callbacks. No identity/name/sex heuristics.
    """
    selected = _require_selected_snapshot(snapshot, job_fresh)
    base_level, job_level = _received_levels(level_params)
    return NativeProgression("Novice", selected.raw_job_id, base_level, job_level)
