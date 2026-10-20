"""Pinned source-shaped offline lifecycle regressions; no native connections."""

import struct

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import MoveTo
from robots.domain.model import Goal
from tests.test_client_protocol import FakeSocket, client
from tests.test_playing_runtime import Wire, walk_ack


def test_same_server_warp_acknowledged_before_frame_publication():
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    wire = FakeSocket()
    bot.sock = wire
    bot.running = bot.connected_map = True
    bot.native_epoch = bot.selection_epoch = bot.map_epoch = 1
    bot.class_fresh = False
    raw = struct.pack("<H16sHH", 0x0091, b"prt_fild08.gat", 170, 375)
    bot._dispatch(0x0091, raw)
    assert wire.sent == [b"\x7d\x00"]
    assert (bot.map_name, bot.x, bot.y) == ("prt_fild08.gat", 170, 375)
    assert bot.native_frame_snapshot()[2][-1][2:] == (0x0091, raw)
    assert bot.class_fresh is False
    assert bot.map_epoch == 1


def test_lost_walk_feedback_requests_bounded_confirmation_without_advancing():
    wire = Wire()
    now = [0.0]
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    playing = PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    playing.perform_native(MoveTo(43, 37))
    # The walk stalled (no position frames since t=1.0): at t=2.0 the stall
    # release fires — the slot clears so the next scripted approach is a
    # FRESH move from the current geometry (no stale re-send of (43, 37)).
    now[0] = 3.0  # the position frame is the 0x0091 at t=2.0: 3.0-2.0 = the 1s stall
    playing.perform_native(MoveTo(44, 37))
    # The stall released the slot and the fresh approach walked its first
    # step toward (44, 37) from (42, 37).
    assert wire.moves == [(43, 37), (43, 37)]
    # The fresh approach owns a new pending slot (its first step); the STALE
    # (43,37) slot from the original walk is gone.
    assert playing._pending is not None
    assert playing._pending[0] == (43, 37)


def test_stalled_walk_releases_slot_and_fresh_approach_moves():
    """The walk stalled with the point unproven (the blocked path, the
    wandering target): the slot releases and the next approach is a FRESH
    move — re-sending the stale point chased wandering targets until
    exhaustion and crawled the approach to ~4 walks/minute (w57)."""
    wire = Wire()
    now = [0.0]
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    playing = PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    playing.perform_native(MoveTo(43, 37))
    # The walk ended short of the point: the zero-cell walkok at (44, 37)
    # proves the stall with the arrival flag set but the point unproven.
    wire.add(walk_ack((44, 37), (44, 37)))
    now[0] = 1.5
    playing.perform_native(MoveTo(46, 37))
    # The stalled walk released; the fresh approach walks toward (46, 37).
    assert wire.moves == [(43, 37), (45, 37)]
    assert playing.build_native_state(Goal.SOCIAL).x == 44


@pytest.mark.parametrize(("pid", "size"), [(0x0092, 28), (0x0AC7, 156)])
def test_cross_server_route_never_acknowledged_as_same_server(pid, size):
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    wire = FakeSocket()
    bot.sock = wire
    bot.running = bot.connected_map = bot.class_fresh = True
    bot.map_epoch = 1
    raw = struct.pack("<H16sHH", pid, b"remote.gat", 1, 2) + bytes(size - 22)
    bot._dispatch(pid, raw)
    assert wire.sent == []
    assert bot.class_fresh is False
    assert bot.map_epoch is None


@pytest.mark.parametrize("raw", [b"\x91\x00", bytes(22)])
def test_malformed_warp_neither_acknowledged_nor_published(raw):
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    wire = FakeSocket()
    bot.sock = wire
    bot.running = bot.connected_map = True
    with pytest.raises(ValueError, match="malformed native"):
        bot._dispatch(0x0091, raw)
    assert wire.sent == []
    assert bot.native_frame_snapshot()[2] == ()


@pytest.mark.parametrize("flag", ["running", "connected_map", "sock"])
def test_inactive_transport_does_not_acknowledge_warp(flag):
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    wire = FakeSocket()
    bot.sock = wire
    bot.running = bot.connected_map = True
    setattr(bot, flag, None if flag == "sock" else False)
    bot._dispatch(0x0091, struct.pack("<H16sHH", 0x0091, b"prontera.gat", 1, 2))
    assert wire.sent == []


def test_initial_coalesced_refresh_retains_one_ack_without_rewinding(monkeypatch):
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    wire = FakeSocket()
    monkeypatch.setattr(client.socket, "create_connection", lambda *_a, **_kw: wire)
    monkeypatch.setattr(client.threading.Thread, "start", lambda _: None)
    entry = struct.pack("<HI3sBBH", 0x02EB, 0, bytes([22, 6, 48]), 5, 5, 0)

    def poll(**_kwargs):
        # The handshake seeds the tracker with the consumed entry itself.
        return 0x02EB, entry

    monkeypatch.setattr(bot, "_poll", poll)
    bot._map_server("offline", 1)
    assert wire.sent[-1] == b"\x7d\x00"
    assert wire.sent.count(b"\x7d\x00") == 1
    assert (bot.x, bot.y) == (88, 99)  # entry seeded by the handshake
    # Reader-time later frame overwrites the seed and never rewinds to it.
    bot._dispatch(0x0091, struct.pack("<H16sHH", 0x0091, b"prontera.gat", 100, 101))
    assert (bot.x, bot.y) == (100, 101)
    bot.close()


def test_announced_destination_is_not_arrival_and_warp_resets_pending():
    wire = Wire()
    now = [0.0]
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    playing = PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    playing.perform_native(MoveTo(43, 37))
    wire.add(walk_ack((42, 37), (43, 37)))
    now[0] = 0.5
    playing.perform_native(MoveTo(44, 37))
    assert wire.moves == [(43, 37)]
    assert playing.build_native_state(Goal.SOCIAL).x == 42
    wire.add(struct.pack("<H16sHH", 0x0091, b"prontera", 50, 50))
    playing.perform_native(MoveTo(51, 50))
    assert wire.moves[-1] == (51, 50)


def test_receive_reader_acknowledges_each_framed_warp_once():
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    first = struct.pack("<H16sHH", 0x0091, b"prt_fild08.gat", 170, 375)
    second = struct.pack("<H16sHH", 0x0091, b"prontera.gat", 156, 26)
    wire = FakeSocket([first[:3], first[3:] + second, b""])
    bot.sock = wire
    bot.running = bot.connected_map = True
    bot._recv_loop()
    assert wire.sent == [b"\x7d\x00", b"\x7d\x00"]
    assert [frame[2:] for frame in bot.native_frame_snapshot()[2]] == [
        (0x0091, first),
        (0x0091, second),
    ]
    bot.drain()
    assert wire.sent == [b"\x7d\x00", b"\x7d\x00"]
    assert (bot.map_name, bot.x, bot.y) == ("prontera.gat", 156, 26)
    assert bot.running is False


def test_failed_warp_ack_not_published_as_completed_dispatch(monkeypatch):
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    bot.sock = FakeSocket()
    bot.running = bot.connected_map = True
    bot.class_fresh = False

    def fail_send(_raw):
        message = "offline failed send"
        raise OSError(message)

    monkeypatch.setattr(bot, "_send", fail_send)
    with pytest.raises(OSError, match="offline failed send"):
        bot._dispatch(0x0091, struct.pack("<H16sHH", 0x0091, b"prontera.gat", 1, 2))
    assert bot.native_frame_snapshot()[2] == ()
    assert bot.class_fresh is False
