"""Synthetic source-shaped contracts; no native receipt or lifecycle authority."""

import struct
from dataclasses import replace

import pytest

from robots.adapters.native_progression import (
    NativeProgression,
    SelectedCharacterSnapshot,
    decode_selected_character_snapshot,
    require_native_progression,
)
from robots.adapters.native_vitals import NativeTelemetryUnavailable


def character_row() -> bytes:
    row = bytearray(155)
    struct.pack_into("<I", row, 0, 101)
    struct.pack_into("<i", row, 24, 3)
    struct.pack_into("<h", row, 64, 0)
    struct.pack_into("<h", row, 72, 12)
    row[118] = 7
    row[154] = 0
    return bytes(row)


def test_received_novice_uses_current_levels_not_snapshot() -> None:
    snapshot = decode_selected_character_snapshot(character_row())
    assert snapshot == SelectedCharacterSnapshot(101, 0, 12, 3, 7, 0)
    assert require_native_progression(
        snapshot, {11: 15, 55: 4}, job_fresh=True
    ) == NativeProgression("Novice", 0, 15, 4)


@pytest.mark.parametrize("fresh", [False, 1, None, "yes"])
def test_explicit_literal_freshness_required(fresh) -> None:
    with pytest.raises(NativeTelemetryUnavailable, match=r"^native progression unavailable$"):
        require_native_progression(
            decode_selected_character_snapshot(character_row()), {11: 15, 55: 4}, job_fresh=fresh
        )


def test_missing_snapshot_denied() -> None:
    with pytest.raises(NativeTelemetryUnavailable, match=r"^native progression unavailable$"):
        require_native_progression(None, {11: 15, 55: 4}, job_fresh=True)


@pytest.mark.parametrize("raw_job", [1, -1, -32768, 32767, True, False, 0.0])
def test_only_exact_received_job_zero_supported(raw_job) -> None:
    snapshot = replace(decode_selected_character_snapshot(character_row()), raw_job_id=raw_job)
    with pytest.raises(NativeTelemetryUnavailable, match=r"^native progression unavailable$"):
        require_native_progression(snapshot, {11: 15, 55: 4}, job_fresh=True)


@pytest.mark.parametrize("char_id", [0, -1, 2**32, True, 101.0])
def test_selected_identity_must_be_positive_exact_uint32(char_id) -> None:
    snapshot = replace(decode_selected_character_snapshot(character_row()), raw_char_id=char_id)
    with pytest.raises(NativeTelemetryUnavailable, match=r"^native progression unavailable$"):
        require_native_progression(snapshot, {11: 15, 55: 4}, job_fresh=True)


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {11: 15},
        {55: 4},
        {11: 0, 55: 4},
        {11: 15, 55: -1},
        {11: 2**31, 55: 4},
        {11: 15, 55: True},
        {11: 15.0, 55: 4},
        {11.0: 15, 55: 4},
        {11: 15, 55: 4, True: 1},
    ],
)
def test_invalid_or_missing_current_levels_denied(parameters) -> None:
    with pytest.raises(NativeTelemetryUnavailable, match=r"^native progression unavailable$"):
        require_native_progression(
            decode_selected_character_snapshot(character_row()), parameters, job_fresh=True
        )


@pytest.mark.parametrize(
    "row", [b"", bytes(154), bytes(156), bytearray(155), "private-not-a-row", None]
)
def test_malformed_row_is_opaque_before_unpack(row) -> None:
    with pytest.raises(ValueError, match=r"^native character snapshot unavailable$"):
        decode_selected_character_snapshot(row)


@pytest.mark.parametrize("snapshot", [101, {}, "not-selected"])
def test_non_snapshot_denied(snapshot) -> None:
    with pytest.raises(NativeTelemetryUnavailable, match=r"^native progression unavailable$"):
        require_native_progression(snapshot, {11: 15, 55: 4}, job_fresh=True)


@pytest.mark.parametrize("raw_job", [-32768, -1, 1, 32767])
def test_signed_received_job_is_preserved_before_denial(raw_job: int) -> None:
    row = bytearray(character_row())
    struct.pack_into("<h", row, 64, raw_job)
    struct.pack_into("<h", row, 72, -32768)
    struct.pack_into("<i", row, 24, -2147483648)
    snapshot = decode_selected_character_snapshot(bytes(row))
    assert (snapshot.raw_job_id, snapshot.snapshot_base_level, snapshot.snapshot_job_level) == (
        raw_job,
        -32768,
        -2147483648,
    )
    with pytest.raises(NativeTelemetryUnavailable, match=r"^native progression unavailable$"):
        require_native_progression(snapshot, {11: 15, 55: 4}, job_fresh=True)


def test_decreases_and_detached_immutable_projection() -> None:
    snapshot = decode_selected_character_snapshot(character_row())
    parameters = {11: 15, 55: 4}
    prior = require_native_progression(snapshot, parameters, job_fresh=True)
    parameters.update({11: 1, 55: 1})
    assert prior == NativeProgression("Novice", 0, 15, 4)
    assert require_native_progression(snapshot, parameters, job_fresh=True) == NativeProgression(
        "Novice", 0, 1, 1
    )
    with pytest.raises(AttributeError):
        prior.base_level = 99  # type: ignore[misc]
    with pytest.raises(AttributeError):
        snapshot.raw_job_id = 1  # type: ignore[misc]


class IntAlias(int):
    """An integer subtype is not an exact native count or parameter key."""


@pytest.mark.parametrize(
    "parameters", [{IntAlias(11): 15, 55: 4}, {11: IntAlias(15), 55: 4}, {11: 15, 55.0: 4}]
)
def test_integer_subtypes_and_float_key_aliases_denied(parameters) -> None:
    with pytest.raises(NativeTelemetryUnavailable, match=r"^native progression unavailable$"):
        require_native_progression(
            decode_selected_character_snapshot(character_row()), parameters, job_fresh=True
        )


def test_maximum_received_levels_and_uint32_identity() -> None:
    snapshot = replace(decode_selected_character_snapshot(character_row()), raw_char_id=2**32 - 1)
    assert require_native_progression(
        snapshot, {11: 2**31 - 1, 55: 2**31 - 1}, job_fresh=True
    ) == NativeProgression("Novice", 0, 2**31 - 1, 2**31 - 1)


def test_freshness_has_no_default() -> None:
    with pytest.raises(TypeError, match="job_fresh"):
        require_native_progression(  # type: ignore[call-arg]
            decode_selected_character_snapshot(character_row()), {11: 15, 55: 4}
        )
