"""Explicit session selection baseline; caller still owns full transport health.

Pinned e985006 MAIN20180704 loads selected char_id's class/base/job from the
same character table into cached mmo_charstatus and sends it through map auth.
The list and selection reload are separate reads, not an atomic DB transaction.
This bounded session baseline is NOT the received-only native_progression API.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from robots.adapters.native_progression import SelectedCharacterSnapshot
from robots.adapters.native_vitals import NativeTelemetryUnavailable


@dataclass(frozen=True)
class SessionProgression:
    """Detached progression with independent baseline/update provenance."""

    job: str
    raw_job_id: int
    base_level: int
    job_level: int
    base_source: Literal["selection", "self_update"]
    job_source: Literal["selection", "self_update"]


def require_native_session_progression(
    snapshot: SelectedCharacterSnapshot | None,
    level_params: Mapping[int, int],
    *,
    class_fresh: bool,
    selection_epoch: int | None,
    map_epoch: int | None,
    native_epoch: int,
    char_id: int,
) -> SessionProgression:
    """Project fresh selected Novice baseline, overridden by every actual update.

    Epochs must be exact positive ints and equal. Invalid received levels deny,
    never restore an older good baseline. No persona fallback or status mutation.
    Class freshness must be invalidated by relevant appearance/transport changes;
    this helper is not an atomic liveness or universal current-class guarantee.
    """
    selected = _session_selection(snapshot, class_fresh, char_id)
    epochs = (selection_epoch, map_epoch, native_epoch)
    if any(type(epoch) is not int or epoch <= 0 for epoch in epochs) or len(set(epochs)) != 1:
        message = "native session progression unavailable"
        raise NativeTelemetryUnavailable(message)
    parameters = dict(level_params)
    if any(type(key) is not int for key in parameters):
        message = "native session progression unavailable"
        raise NativeTelemetryUnavailable(message)
    base = parameters.get(11, selected.snapshot_base_level)
    job = parameters.get(55, selected.snapshot_job_level)
    _require_levels((base, job))
    return SessionProgression(
        "Novice",
        selected.raw_job_id,
        base,
        job,
        "self_update" if 11 in parameters else "selection",
        "self_update" if 55 in parameters else "selection",
    )


def _require_levels(levels: tuple[int, int]) -> None:
    if any(type(level) is not int or not 0 < level <= 2**31 - 1 for level in levels):
        message = "native session progression unavailable"
        raise NativeTelemetryUnavailable(message)


def _session_selection(
    snapshot: SelectedCharacterSnapshot | None,
    class_fresh: bool,
    char_id: int,
) -> SelectedCharacterSnapshot:
    message = "native session progression unavailable"
    if type(snapshot) is not SelectedCharacterSnapshot:
        raise NativeTelemetryUnavailable(message)
    identity = (char_id, snapshot.raw_char_id, snapshot.raw_job_id)
    if any(type(value) is not int for value in identity):
        raise NativeTelemetryUnavailable(message)
    valid = (
        class_fresh is True,
        0 < char_id <= 2**32 - 1,
        snapshot.raw_char_id == char_id,
        snapshot.raw_job_id == 0,
    )
    if not all(valid):
        raise NativeTelemetryUnavailable(message)
    _require_levels((snapshot.snapshot_base_level, snapshot.snapshot_job_level))
    return snapshot
