"""Wire-map/cache identity regressions; synthetic wire, not native gameplay."""

import struct

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app.playing_runtime import PlayingClient
from robots.domain.model import Goal
from tests.test_playing_runtime import Wire, entry


def received_client(name: str) -> PlayingClient:
    wire = Wire()
    wire.frames = []
    wire.add(entry(), struct.pack("<H16sHH", 0x0091, name.encode(), 150, 154))
    cache = MapCache(WalkMap(key, 400, 400, bytes(160000)) for key in ("prontera", "prt_fild08"))
    return PlayingClient(wire, cache=cache)


@pytest.mark.parametrize("name", ["prontera.gat", "prt_fild08.gat"])
def test_received_gat_has_explicit_public_cache_identity(name: str) -> None:
    client = received_client(name)
    assert client.build_native_state(Goal.GRIND).map_name == name.removesuffix(".gat")
    assert client._tracker is not None
    assert client._tracker.view.map_name == name


def test_native_gat_map_can_plan_starter_travel() -> None:
    client = received_client("prontera.gat")
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ())


@pytest.mark.parametrize("name", ["prontera", "prt_fild08"])
def test_existing_exact_cache_identity_is_preserved(name: str) -> None:
    assert received_client(name).build_native_state(Goal.GRIND).map_name == name


@pytest.mark.parametrize(
    "name", ["unknown.gat", "prontera.gatx", "prontera.Gatx", "Prontera.gat", "../prontera.gat"]
)
def test_unmapped_wire_identity_never_falls_back_to_fixture(name: str) -> None:
    with pytest.raises(NativeTelemetryUnavailable):
        received_client(name).build_native_state(Goal.GRIND)
