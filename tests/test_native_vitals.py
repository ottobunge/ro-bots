"""Synthetic native-layout contracts only; no host or live transport acceptance."""

import importlib.util
import struct
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from robots.adapters import native_vitals

CLIENT_PATH = Path(__file__).resolve().parents[1] / "spikes/003-clientless-limbs/client.py"
spec = importlib.util.spec_from_file_location("native_vitals_client", CLIENT_PATH)
assert spec is not None
assert spec.loader is not None
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


@pytest.fixture
def bot() -> Any:
    return client.BotClient("offline_vitals", "unused_offline", verbose=False)


def test_real_dispatch_retains_source_shaped_status(bot):
    for parameter, count in [(5, 37), (6, 100), (7, 0), (8, 23)]:
        bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, parameter, count))
    assert getattr(bot, "status_params", None) == {5: 37, 6: 100, 7: 0, 8: 23}
    bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, 5, 12))
    assert bot.status_params == {5: 12, 6: 100, 7: 0, 8: 23}
    assert bot.sock is None


def test_retained_status_projects_without_defaults(bot):
    for parameter, count in [(5, 37), (6, 100), (7, 0), (8, 23)]:
        bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, parameter, count))
    assert native_vitals.require_native_vitals(bot.status_params) == native_vitals.NativeVitals(
        hp=37, max_hp=100, sp=0, max_sp=23
    )
    bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, 5, 12))
    assert native_vitals.require_native_vitals(bot.status_params).hp == 12


@pytest.mark.parametrize("parameters", [{}, {5: 0}, {5: 0, 6: 100, 7: 0}])
def test_missing_status_is_explicitly_unavailable(parameters):
    assert hasattr(native_vitals, "NativeTelemetryUnavailable")
    with pytest.raises(native_vitals.NativeTelemetryUnavailable, match="native vitals unavailable"):
        native_vitals.require_native_vitals(parameters)


@pytest.mark.parametrize(
    ("parameter", "invalid"),
    [
        (5, -1),
        (7, -1),
        (6, 0),
        (8, -1),
        (5, True),
        (6, 1.0),
        (7, "0"),
        (8, None),
        (6, 2**31),
        (5, 101),
        (7, 24),
    ],
)
def test_invalid_status_denies_without_exposing_values(parameter, invalid):
    parameters = {5: 37, 6: 100, 7: 0, 8: 23}
    parameters[parameter] = invalid
    with pytest.raises(native_vitals.NativeTelemetryUnavailable) as caught:
        native_vitals.require_native_vitals(parameters)
    assert str(caught.value) == "native vitals unavailable"


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"\xb0\x00",
        struct.pack("<HHi", 0x00B1, 5, 99),
        struct.pack("<HHi", 0x00B0, 5, 99) + b"x",
    ],
)
def test_malformed_status_does_not_mutate_retention(bot, raw):
    bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, 5, 37))
    with pytest.raises(ValueError, match=r"^malformed native status packet$") as caught:
        bot._dispatch(0x00B0, raw)
    assert str(caught.value) == "malformed native status packet"
    assert bot.status_params == {5: 37}


@pytest.mark.parametrize("boundary", ["connect", "map"])
def test_new_transport_clears_status_before_failed_allocation(bot, monkeypatch, boundary):
    bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, 5, 37))

    def fail_allocation(*_args, **_kwargs):
        assert bot.status_params == {}
        message = "offline allocation denied"
        raise OSError(message)

    monkeypatch.setattr(client.socket, "create_connection", fail_allocation)
    attempt = bot.connect if boundary == "connect" else lambda: bot._map_server("offline", 1)
    with pytest.raises(OSError, match="offline allocation denied"):
        attempt()
    assert bot.status_params == {}
    assert bot.sock is None


class NonNativeInt(int):
    """Python int subclasses are not raw wire integers."""


@pytest.mark.parametrize("parameter", [5.0, NonNativeInt(5)])
def test_non_native_parameter_key_denies_projection(parameter):
    parameters = {parameter: 37, 6: 100, 7: 0, 8: 23}
    with pytest.raises(native_vitals.NativeTelemetryUnavailable):
        native_vitals.require_native_vitals(parameters)


def test_int_subclass_count_denies_projection():
    with pytest.raises(native_vitals.NativeTelemetryUnavailable):
        native_vitals.require_native_vitals({5: NonNativeInt(37), 6: 100, 7: 0, 8: 23})


@pytest.mark.parametrize("count", [-(2**31), -1, 0, 2**31 - 1])
def test_signed_wire_count_preserved_exactly(bot, count):
    bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, 5, count))
    assert bot.status_params == {5: count}


@pytest.mark.parametrize("pid", [0x00B1, 0xFFFF])
def test_non_authoritative_packets_do_not_change_status(bot, pid):
    bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, 5, 37))
    bot._dispatch(pid, struct.pack("<HHi", pid, 5, 99))
    bot._dispatch(pid, b"")
    assert bot.status_params == {5: 37}


@pytest.mark.parametrize("parameter", [0, 12, 19, 65535])
def test_other_parameters_are_ignored(bot, parameter):
    assert bot.status_params == {}
    bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, parameter, 99))
    assert bot.status_params == {}


@pytest.mark.parametrize("parameter", [11, 55])
def test_level_receipts_do_not_change_health_projection(bot: Any, parameter: int) -> None:
    received = {5: 37, 6: 100, 7: 0, 8: 23}
    for key, count in received.items():
        bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, key, count))
    expected = native_vitals.require_native_vitals(bot.status_params)
    for level in (99, 1, -1):
        bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, parameter, level))
        assert bot.status_params == {**received, parameter: level}
        assert native_vitals.require_native_vitals(bot.status_params) == expected


def test_received_levels_do_not_supply_missing_vitals(bot: Any) -> None:
    for parameter, count in [(11, 7), (55, 3)]:
        bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, parameter, count))
    assert bot.status_params == {11: 7, 55: 3}
    with pytest.raises(native_vitals.NativeTelemetryUnavailable, match="native vitals unavailable"):
        native_vitals.require_native_vitals(bot.status_params)


def test_zero_vitals_and_signed_maximum_are_valid():
    assert native_vitals.require_native_vitals({5: 0, 6: 2**31 - 1, 7: 0, 8: 0}) == (
        native_vitals.NativeVitals(0, 2**31 - 1, 0, 0)
    )


def test_projection_is_frozen_detached_snapshot():
    parameters = {5: 37, 6: 100, 7: 0, 8: 23}
    vitals = native_vitals.require_native_vitals(parameters)
    parameters[5] = 12
    assert vitals.hp == 37
    with pytest.raises(FrozenInstanceError):
        vitals.hp = 12  # type: ignore[misc]  # exercise the frozen runtime contract


def test_negative_wire_update_denies_previous_good_health(bot):
    for parameter, count in [(5, 37), (6, 100), (7, 0), (8, 23)]:
        bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, parameter, count))
    bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, 5, -1))
    assert bot.status_params[5] == -1
    with pytest.raises(native_vitals.NativeTelemetryUnavailable):
        native_vitals.require_native_vitals(bot.status_params)
