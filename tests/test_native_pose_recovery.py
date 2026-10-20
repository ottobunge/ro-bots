"""Source-shaped received pose gating; synthetic packets, no native I/O."""

import struct

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import MoveTo, Rest
from tests.test_playing_runtime import Wire, entry, map_frame


class PoseWire(Wire):
    def stand(self):
        self.sent.append("stand")


def pose(source: int = 999, kind: int = 2, target: int = 0) -> bytes:
    raw = bytearray(34)
    struct.pack_into("<HII", raw, 0, 0x08C8, source, target)
    raw[29] = kind
    return bytes(raw)


def setup() -> tuple[PoseWire, PlayingClient, list[float]]:
    wire = PoseWire()
    now = [0.0]
    client = PlayingClient(
        wire,
        cache=MapCache((WalkMap("prontera", 100, 100, bytes(10000)),)),
        monotonic=lambda: now[0],
    )
    return wire, client, now


@pytest.mark.parametrize("aid", [999, (-999) & 0xFFFFFFFF])
def test_recovered_move_requires_fresh_self_standing_receipt(aid):
    wire, client, _ = setup()
    wire.status_params[5] = 10
    client.perform_native(Rest())
    wire.add(pose(aid))
    wire.status_params[5] = 100
    client.perform_native(MoveTo(43, 37))
    assert wire.sent == ["sit", "stand"]
    assert not wire.moves
    client.perform_native(MoveTo(43, 37))
    assert not wire.moves
    wire.add(pose(aid, 3))
    client.perform_native(MoveTo(43, 37))
    assert wire.moves == [(43, 37)]


def test_standing_requests_are_paced_and_bounded_without_ack():
    wire, client, now = setup()
    wire.add(pose())
    client.perform_native(MoveTo(43, 37))
    for instant in (0.1, 0.5, 1.0, 1.1, 2.0, 3.0, 4.0, 100.0, 1000.0):
        now[0] = instant
        wire.add(pose())  # Repeated sit receipt must not reset the retry budget.
        client.perform_native(MoveTo(43, 37))
    # w65: the recovery re-arms a doubling epoch (never permanently silent),
    # so deep-time ticks keep retrying — bounded by one stand per tick.
    assert wire.sent[:3] == ["stand"] * 3
    assert len(wire.sent) <= 9
    assert not wire.moves
    wire.add(pose(kind=3))
    client.perform_native(MoveTo(43, 37))
    assert wire.moves == [(43, 37)]


@pytest.mark.parametrize(
    ("source", "target", "kind"),
    [(123, 0, 3), (999, 999, 3), (999, 0, 0), ((-123) & 0xFFFFFFFF, 0, 3)],
)
def test_peer_targeted_or_nonpose_receipts_cannot_clear_self_sit(source, target, kind):
    wire, client, _ = setup()
    wire.add(pose())
    client.perform_native(MoveTo(43, 37))
    wire.add(pose(source, kind, target))
    client.perform_native(MoveTo(43, 37))
    assert not wire.moves
    assert wire.sent == ["stand"]


def test_warp_does_not_erase_sit_and_new_epoch_resets_pose_budget():

    wire, client, _ = setup()
    wire.add(pose())
    client.perform_native(MoveTo(43, 37))
    wire.add(map_frame())
    client.perform_native(MoveTo(43, 37))
    assert not wire.moves
    assert wire.sent == ["stand"]
    wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    wire.frames = []
    wire.add(entry(), map_frame())
    client.perform_native(MoveTo(43, 37))
    assert wire.moves == [(43, 37)]


def test_rest_send_is_not_received_sit():
    wire, client, _ = setup()
    client.perform_native(Rest())
    client.perform_native(MoveTo(43, 37))
    assert wire.sent == ["sit"]
    assert wire.moves == [(43, 37)]


@pytest.mark.parametrize("size", [2, 33, 35])
def test_malformed_pose_denied_before_wrapper_metadata(size):

    wire, client, _ = setup()
    wire.add((pose() + bytes(10))[:size])
    with pytest.raises(NativeTelemetryUnavailable):
        client.perform_native(MoveTo(43, 37))
    assert not wire.moves
    assert not wire.sent


def test_late_retries_cannot_burst_in_one_tick():
    wire, client, now = setup()
    wire.add(pose())
    client.perform_native(MoveTo(43, 37))
    now[0] = 2.5
    for _ in range(10):
        client.perform_native(MoveTo(43, 37))
    assert wire.sent == ["stand", "stand"]
    assert not wire.moves


def test_death_invalidates_standing_even_after_resurrection_and_warp():
    wire, client, _ = setup()
    client.perform_native(MoveTo(43, 37))
    wire.moves.clear()
    wire.add(struct.pack("<HIB", 0x0080, 999, 1), map_frame(), struct.pack("<HIH", 0x0148, 999, 0))
    client.perform_native(MoveTo(43, 37))
    assert not wire.moves
    assert wire.sent == ["stand"]
    wire.add(pose(kind=3))
    client.perform_native(MoveTo(43, 37))
    assert wire.moves == [(43, 37)]
