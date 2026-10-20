"""Offline source-shaped session and received frame contracts."""

import struct
from itertools import pairwise
from typing import Any

import pytest

from robots.adapters.native_session_progression import require_native_session_progression
from tests.test_client_native_progression import characters, client, row, setup, zone
from tests.test_client_protocol import FakeSocket


def test_authenticated_selection_initial_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    bot, _ = setup(monkeypatch, characters(row(202, "Selected", 0, 0, 10, level=10)), zone())
    bot.native_epoch = 1
    bot._char_server("127.0.0.1", 6121)
    assert bot.selection_epoch == 1
    assert bot.class_fresh is True
    assert bot.map_epoch is None

    # Map transport allocation fails: binding occurs only after actual allocation.
    def allocate(*args: Any, **kwargs: Any) -> Any:
        message = "offline"
        raise OSError(message)

    monkeypatch.setattr(client.socket, "create_connection", allocate)
    with pytest.raises(OSError, match="offline"):
        bot._map_server("127.0.0.1", 5121)
    assert bot.map_epoch is None
    assert bot.status_params == {}
    wire = FakeSocket()
    monkeypatch.setattr(client.socket, "create_connection", lambda *_a, **_kw: wire)
    monkeypatch.setattr(client.threading.Thread, "start", lambda _: None)
    entry = struct.pack("<HI3sBBH", 0x02EB, 0, bytes([22, 6, 48]), 5, 5, 0)
    monkeypatch.setattr(bot, "_poll", lambda **_kw: (0x02EB, entry))
    bot._map_server("127.0.0.1", 5121)
    result = require_native_session_progression(
        bot.selected_character_snapshot,
        bot.status_params,
        class_fresh=bot.class_fresh,
        selection_epoch=bot.selection_epoch,
        map_epoch=bot.map_epoch,
        native_epoch=bot.native_epoch,
        char_id=bot.gid,
    )
    assert (result.base_level, result.job_level) == (10, 10)
    assert result.base_source == "selection"
    assert bot.status_params == {}
    bot.close()


def test_frame_snapshot_sequences_once_and_retention() -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    assert bot.native_frame_snapshot() == (0, 0, ())
    raw = struct.pack("<HHi", 0x00B0, 11, 10)
    for _ in range(4100):
        bot._dispatch(0x00B0, raw)
    epoch, base, frames = bot.native_frame_snapshot()
    assert (epoch, base, len(frames)) == (0, 0, 4096)
    assert frames[0][0] == 5
    assert frames[-1][0] == 4100
    assert all(frame[2:] == (0x00B0, raw) for frame in frames)
    assert all(a[1] <= b[1] for a, b in pairwise(frames))
    bot.drain()
    assert bot.native_frame_snapshot()[2] == frames


@pytest.mark.parametrize("aid", [11, (-11) & 0xFFFFFFFF])
def test_self_base_appearance_invalidates_without_guessing_class(aid: int) -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    bot.aid = 11
    bot.class_fresh = True
    bot._dispatch(0x01D7, struct.pack("<HIBHH", 0x01D7, aid, 2, 0, 0))
    assert bot.class_fresh is True
    bot._dispatch(0x01D7, struct.pack("<HIBHH", 0x01D7, aid, 0, 0, 0))
    assert bool(bot.class_fresh) is False
    bot._dispatch(0x01D7, struct.pack("<HIBHH", 0x01D7, aid, 2, 0, 0))
    assert bool(bot.class_fresh) is False


@pytest.mark.parametrize("raw", [b"\xd7\x01", struct.pack("<HIBHH", 0x01D8, 11, 0, 0, 0)])
def test_malformed_look_does_not_publish_or_mutate(raw: bytes) -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    bot.class_fresh = True
    with pytest.raises(ValueError, match="malformed native appearance"):
        bot._dispatch(0x01D7, raw)
    assert bot.class_fresh is True
    assert bot.native_frame_snapshot()[2] == ()


@pytest.mark.parametrize(("pid", "size"), [(0x0091, 22), (0x0092, 28), (0x0AC7, 156)])
def test_map_position_retention_and_transition_policy(pid: int, size: int) -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    bot.class_fresh = True
    bot.map_epoch = 1
    raw = bytearray(size)
    struct.pack_into("<H16sHH", raw, 0, pid, b"new_map.gat", 88, 99)
    bot._dispatch(pid, bytes(raw))
    assert (bot.map_name, bot.x, bot.y) == ("new_map.gat", 88, 99)
    assert bot.class_fresh is (pid == 0x0091)
    assert bot.map_epoch == (1 if pid == 0x0091 else None)


def test_entry_position_is_received_and_send_is_not_arrival(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    raw = struct.pack("<HI3sBBH", 0x02EB, 0, bytes([22, 6, 48]), 5, 5, 0)
    bot._dispatch(0x02EB, raw)
    assert (bot.x, bot.y) == (88, 99)
    monkeypatch.setattr(bot, "_send", lambda _: None)
    bot.move(100, 101)
    assert (bot.x, bot.y) == (88, 99)


def test_reconnect_epoch_discards_late_old_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    raw = struct.pack("<HHi", 0x00B0, 11, 10)
    bot._dispatch(0x00B0, raw)

    def old_close() -> None:
        assert bot.native_epoch == 1
        bot.class_fresh = True
        bot._dispatch(0x00B0, raw)
        assert bot.native_frame_snapshot()[2] == ()

    monkeypatch.setattr(bot, "close", old_close)
    monkeypatch.setattr(bot, "_login_server", lambda: ("offline", 1))
    monkeypatch.setattr(bot, "_char_server", lambda *_: ("offline", 2))
    monkeypatch.setattr(bot, "_map_server", lambda *_: None)
    bot.connect()
    assert bot.native_frame_snapshot() == (1, 2, ())
    assert bool(bot.class_fresh) is False
    bot._dispatch(0x00B0, raw)
    assert bot.native_frame_snapshot()[2][0][0] == 3


def test_reader_frames_complete_once_queue_does_not_redispatch() -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    raw = struct.pack("<HHi", 0x00B0, 11, 10)
    unknown = struct.pack("<HH", 0x013A, 99)
    bot.sock = FakeSocket([raw[:3], raw[3:] + unknown, b""])
    bot.running = True
    bot._recv_loop()
    frames = bot.native_frame_snapshot()[2]
    assert [frame[2:] for frame in frames] == [(0x00B0, raw), (0x013A, unknown)]
    assert bot._poll() == (0x00B0, raw)
    bot.drain()
    assert bot.native_frame_snapshot()[2] == frames
    assert len(bot.raw_log) == 2
    assert bot.rx_error is not None
    bot.close()
    assert bot.native_frame_snapshot()[2] == ()


@pytest.mark.parametrize(
    ("pid", "raw"),
    [
        (0x0091, b"\x91\x00"),
        (0x0092, bytes(28)),
        (0x02EB, bytes(13)),
    ],
)
def test_bad_position_framing_retains_old_position(pid: int, raw: bytes) -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    bot.x, bot.y, bot.map_name = 1, 2, "old"
    with pytest.raises(ValueError, match="malformed native"):
        bot._dispatch(pid, raw)
    assert (bot.x, bot.y, bot.map_name) == (1, 2, "old")
    assert bot.native_frame_snapshot()[2] == ()


def test_queued_entry_does_not_rewind_later_received_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    monkeypatch.setattr(client.socket, "create_connection", lambda *_a, **_kw: FakeSocket())
    monkeypatch.setattr(client.threading.Thread, "start", lambda _: None)
    entry = struct.pack("<HI3sBBH", 0x02EB, 0, bytes([22, 6, 48]), 5, 5, 0)

    def poll(**_kwargs: Any) -> tuple[int, bytes]:
        # The handshake now seeds the tracker with the consumed entry itself
        # (fx0's deadlock); the poll carries no reader-side dispatches.
        return 0x02EB, entry

    monkeypatch.setattr(bot, "_poll", poll)
    bot._map_server("offline", 1)
    assert (bot.x, bot.y) == (88, 99)  # entry seeded by the handshake
    # Reader-time later frame overwrites the seed and never rewinds to it.
    bot._dispatch(0x0091, struct.pack("<H16sHH", 0x0091, b"later.gat", 100, 101))
    assert (bot.x, bot.y, bot.map_name) == (100, 101, "later.gat")
    bot.close()
