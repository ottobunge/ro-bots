"""Offline raw-frame retention; presentation is not combat or arrival authority."""

import importlib.util
import struct
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "actor_retention_client", ROOT / "spikes/003-clientless-limbs/client.py"
)
assert SPEC is not None
assert SPEC.loader is not None
client = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(client)


def frame(pid: int, objecttype: int = 5, actor_id: int = 101, char_id: int = 202) -> bytes:
    size, pos_off, name_off = {
        0x09FD: (110, 63, 86),
        0x09FE: (103, 59, 79),
        0x09FF: (104, 59, 80),
    }[pid]
    raw = bytearray(size)
    struct.pack_into("<HHBII", raw, 0, pid, size, objecttype, actor_id, char_id)
    struct.pack_into("<H", raw, 23, 4095)
    x, y, tx, ty = 165, 145, 166, 146
    raw[pos_off : pos_off + 3] = bytes((x >> 2, ((x & 3) << 6) | (y >> 4), (y & 15) << 4))
    if pid == 0x09FD:
        raw[pos_off + 2] |= tx >> 6
        raw[pos_off + 3] = ((tx & 63) << 2) | (ty >> 8)
        raw[pos_off + 4] = ty & 255
    raw[name_off : name_off + 24] = b"DummyActor\x00".ljust(24, b"\x00")
    return bytes(raw)


@pytest.fixture
def bot() -> Any:
    return client.BotClient("dummy_operator", "dummy_not_a_credential", verbose=False)


def deliver(bot: Any, raw: bytes) -> None:
    packets, rest = client.pdb.parse_stream(raw)
    assert rest == b""
    assert len(packets) == 1
    for pid, packet in packets:
        bot._dispatch(pid, packet)


@pytest.mark.parametrize("pid", [0x09FD, 0x09FE, 0x09FF])
def test_raw_complete_entry_retains_presentation_through_real_pipeline(bot: Any, pid: int) -> None:
    deliver(bot, frame(pid))
    assert bot.actors[101]["objecttype"] == 5


@pytest.mark.parametrize("pid", [0x09FD, 0x09FE, 0x09FF])
def test_explicit_packet_id_cannot_reinterpret_valid_other_layout(bot: Any, pid: int) -> None:
    deliver(bot, frame(pid))
    original = bot.actors[101]
    other = 0x09FE if pid != 0x09FE else 0x09FF
    with pytest.raises(ValueError, match=r"^Invalid native actor presentation frame$"):
        bot._dispatch(pid, frame(other, objecttype=255))
    assert bot.actors[101] is original


@pytest.mark.parametrize("pid", [0x09FD, 0x09FE, 0x09FF])
@pytest.mark.parametrize("objecttype", [0, 5, 6, 12, 255])
@pytest.mark.parametrize("actor_id", [0, 101, 0xFFFFFFFF])
def test_replacement_preserves_raw_type_identity_and_pose(
    bot: Any, pid: int, objecttype: int, actor_id: int
) -> None:
    deliver(bot, frame(pid, 5, actor_id, 202))
    previous = bot.actors[actor_id]
    deliver(bot, frame(pid, objecttype, actor_id, 0))
    info = bot.actors[actor_id]
    expected = {
        "gid": actor_id,
        "char_id": 0,
        "objecttype": objecttype,
        "job": 4095,
        "name": "DummyActor",
        "walking": pid == 0x09FD,
        "x": 166 if pid == 0x09FD else 165,
        "y": 146 if pid == 0x09FD else 145,
    }
    if pid == 0x09FD:
        expected["from"] = (165, 145)
    assert info == expected
    assert info is not previous
    vanish = client.pdb.pack(0x0080, struct.pack("<IB", actor_id, 0))
    deliver(bot, vanish)
    assert bot.actors == {}


@pytest.mark.parametrize("pid", [0x09FD, 0x09FE, 0x09FF])
@pytest.mark.parametrize("damage", ["truncate", "append", "declared", "header", "bytearray"])
def test_malformed_entry_does_not_replace_or_signal(bot: Any, pid: int, damage: str) -> None:
    deliver(bot, frame(pid))
    original = bot.actors[101]
    bot.actor_event.clear()
    raw: Any = frame(pid, 255)
    if damage == "truncate":
        raw = raw[:-1]
    elif damage == "append":
        raw += b"x"
    elif damage == "declared":
        raw = raw[:2] + b"\x04\x00" + raw[4:]
    elif damage == "header":
        raw = b"\x34\x12" + raw[2:]
    else:
        raw = bytearray(raw)
    with pytest.raises(ValueError, match=r"^Invalid native actor presentation frame$"):
        bot._dispatch(pid, raw)
    assert bot.actors[101] is original
    assert not bot.actor_event.is_set()


@pytest.mark.parametrize("pid", [0x09FD, 0x09FE, 0x09FF])
def test_every_partial_entry_stays_buffered(pid: int) -> None:
    raw = frame(pid)
    for split in range(len(raw)):
        packets, rest = client.pdb.parse_stream(raw[:split])
        assert packets == []
        assert rest == raw[:split]
        assert client.pdb.parse_stream(rest + raw[split:]) == ([(pid, raw)], b"")


class ReceiveChunks:
    """Deterministic reader input without creating any socket."""

    def __init__(self, bot: Any, chunk: bytes) -> None:
        self.bot = bot
        self.chunk = chunk

    def settimeout(self, value: float) -> None:
        pass

    def recv(self, count: int) -> bytes:
        if self.chunk:
            chunk, self.chunk = self.chunk, b""
            return chunk
        self.bot.running = False
        return b""


def test_malformed_known_frame_poison_is_retained_while_reader_continues(bot: Any) -> None:
    deliver(bot, frame(0x09FE))
    original = bot.actors[101]
    malformed = struct.pack("<HH", 0x09FE, 70) + frame(0x09FE)[4:70]
    next_frame = frame(0x09FF, 255, 303, 0)
    bot.sock = ReceiveChunks(bot, malformed + next_frame)
    bot.running = True
    bot._recv_loop()
    assert bot.dispatch_errors == [(0x09FE, "Invalid native actor presentation frame")]
    assert bot.actors[101] is original
    assert bot.actors[303]["objecttype"] == 255
    assert bot.rx_error is None
    assert bot.packet_counts == {0x09FE: 1, 0x09FF: 1}


def test_unknown_packet_still_fails_closed() -> None:
    with pytest.raises(ValueError, match=r"^unknown packet 0x1234 at 0,"):
        client.pdb.parse_stream(b"\x34\x12" + bytes(101))
