"""Session baseline has explicit provenance, not fabricated SELF receipts."""

import importlib
from typing import Any

import pytest

from robots.adapters.native_progression import SelectedCharacterSnapshot
from robots.adapters.native_vitals import NativeTelemetryUnavailable


def project(snapshot: Any = None, params: Any = None, **overrides: Any) -> Any:
    module = importlib.import_module("robots.adapters.native_session_progression")
    values: dict[str, Any] = {
        "class_fresh": True,
        "selection_epoch": 1,
        "map_epoch": 1,
        "native_epoch": 1,
        "char_id": 202,
    }
    values.update(overrides)
    return module.require_native_session_progression(
        snapshot or SelectedCharacterSnapshot(202, 0, 10, 10, 0, 1),
        {} if params is None else params,
        **values,
    )


def test_initial_session_baseline_without_self_updates() -> None:
    params: dict[int, int] = {}
    result = project(params=params)
    assert (result.job, result.raw_job_id, result.base_level, result.job_level) == (
        "Novice",
        0,
        10,
        10,
    )
    assert (result.base_source, result.job_source) == ("selection", "selection")
    assert params == {}


@pytest.mark.parametrize("params", [{11: 1}, {55: 2}, {11: 9, 55: 3}])
def test_updates_override_baseline_including_decreases(params: dict[int, int]) -> None:
    result = project(params=params)
    assert result.base_level == params.get(11, 10)
    assert result.job_level == params.get(55, 10)
    assert result.base_source == ("self_update" if 11 in params else "selection")
    assert result.job_source == ("self_update" if 55 in params else "selection")


@pytest.mark.parametrize(
    "overrides",
    [
        {"class_fresh": False},
        {"class_fresh": 1},
        {"selection_epoch": None},
        {"selection_epoch": 0},
        {"selection_epoch": True},
        {"map_epoch": 2},
        {"native_epoch": 2},
        {"char_id": 203},
        {"char_id": True},
    ],
)
def test_stale_or_mismatched_identity_denies(overrides: dict[str, Any]) -> None:
    with pytest.raises(NativeTelemetryUnavailable):
        project(**overrides)


@pytest.mark.parametrize("params", [{11: 0}, {55: -1}, {11: True}, {55: 2**31}, {True: 3}])
def test_invalid_updates_deny_not_last_good_fallback(params: dict[int, int]) -> None:
    with pytest.raises(NativeTelemetryUnavailable):
        project(params=params)


@pytest.mark.parametrize(
    "snapshot",
    [
        SelectedCharacterSnapshot(202, 1, 10, 10, 0, 1),
        SelectedCharacterSnapshot(202, False, 10, 10, 0, 1),
        SelectedCharacterSnapshot(0, 0, 10, 10, 0, 1),
        SelectedCharacterSnapshot(202, 0, 0, 10, 0, 1),
        SelectedCharacterSnapshot(202, 0, 10, -1, 0, 1),
        SelectedCharacterSnapshot(202, 0, True, 10, 0, 1),
    ],
)
def test_invalid_snapshot_denies(snapshot: SelectedCharacterSnapshot) -> None:
    with pytest.raises(NativeTelemetryUnavailable):
        project(snapshot=snapshot)


def test_non_snapshot_object_denies() -> None:
    with pytest.raises(NativeTelemetryUnavailable):
        project(snapshot=object())
