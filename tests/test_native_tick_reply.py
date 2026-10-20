"""Compiled MAIN/pre-re clock framing; offline, not native acceptance."""

import re
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from robots.adapters.native_gameplay import NativeGameplayTracker
from robots.adapters.native_vitals import NativeTelemetryUnavailableError, require_native_vitals
from tests.test_client_protocol import FakeSocket, client

CLOCK = bytes.fromhex("7f0078563412")
SOURCE = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source/src")


def test_literal_clock_reply_reaches_actual_framer() -> None:
    assert client.pdb.parse_stream(CLOCK) == ([(0x007F, CLOCK)], b"")
    assert struct.unpack_from("<I", CLOCK, 2) == (0x12345678,)
    assert client.pdb.name_of(0x007F) == "ZC_NOTIFY_TIME"


def test_compiled_clock_layout(tmp_path: Path) -> None:
    header = (SOURCE / "map/packets.hpp").read_text()
    match = re.search(
        r"struct PACKET_ZC_NOTIFY_TIME \{.*?DEFINE_PACKET_HEADER\(ZC_NOTIFY_TIME, 0x7f\);",
        header,
        re.S,
    )
    assert match is not None
    cpp = tmp_path / "oracle.cpp"
    cpp.write_text(
        "#include <cstdint>\n#include <cstddef>\n#include <cstdio>\n"
        "#include <config/packets.hpp>\n"
        "using int16=int16_t; using uint32=uint32_t;\n"
        "#define DEFINE_PACKET_HEADER(name,id) constexpr int HEADER_##name=id\n"
        + match[0]
        + "\nstatic_assert(PACKETVER_MAIN_NUM==20180704);\n"
        "#if defined(PACKETVER_RE) || defined(PACKETVER_ZERO) || defined(RENEWAL)\n"
        "#error Wrong profile\n#endif\n"
        'int main(){printf("%d %zu %zu %zu %zu",HEADER_ZC_NOTIFY_TIME,\n'
        "sizeof(PACKET_ZC_NOTIFY_TIME),offsetof(PACKET_ZC_NOTIFY_TIME,packetType),\n"
        "offsetof(PACKET_ZC_NOTIFY_TIME,time),sizeof(PACKET_ZC_NOTIFY_TIME::time));}\n"
    )
    compiler = shutil.which("g++")
    assert compiler is not None
    binary = tmp_path / "oracle"
    subprocess.run(
        [
            compiler,
            "-DPACKETVER=20180704",
            "-DPRERE",
            "-I" + str(SOURCE),
            str(cpp),
            "-o",
            str(binary),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    result = subprocess.run([str(binary)], check=True, capture_output=True, text=True, timeout=5)
    assert result.stdout == "127 6 0 2 4"
    assert client.pdb.PACKET_DB[0x007F] == 6
    # Emission uses the packed sizeof, and the actual shuffled request calls it.
    source = (SOURCE / "map/clif.cpp").read_text()
    assert "p.packetType = HEADER_ZC_NOTIFY_TIME;" in source
    assert "p.time = client_tick(time);" in source
    assert "clif_send( &p, sizeof( p ), &sd, SELF );" in source
    assert "clif_notify_time( *sd, gettick() );" in source


def walking() -> bytes:
    raw = bytearray(110)
    struct.pack_into("<HHBII", raw, 0, 0x09FD, 110, 0, 42, 9001)
    raw[86:110] = b"Offline".ljust(24, b"\0")
    return bytes(raw)


@pytest.mark.parametrize("clock_first", [True, False])
def test_coalesced_clock_and_walking_every_split(clock_first: bool) -> None:
    actor = walking()
    expected = [(0x007F, CLOCK), (0x09FD, actor)]
    if not clock_first:
        expected.reverse()
    stream = b"".join(raw for _, raw in expected)
    assert client.pdb.parse_stream(stream) == (expected, b"")
    for split in range(len(stream) + 1):
        first, pending = client.pdb.parse_stream(stream[:split])
        second, tail = client.pdb.parse_stream(pending + stream[split:])
        assert first + second == expected
        assert tail == b""


@pytest.mark.parametrize("cut", range(1, 6))
def test_truncated_clock_retained_until_complete(cut: int) -> None:
    assert client.pdb.parse_stream(CLOCK[:cut]) == ([], CLOCK[:cut])
    assert client.pdb.parse_stream(CLOCK[:cut] + CLOCK[cut:]) == ([(0x007F, CLOCK)], b"")


def test_repeated_clocks_preserve_each_frame() -> None:
    frames, tail = client.pdb.parse_stream(CLOCK * 3)
    assert frames == [(0x007F, CLOCK)] * 3
    assert tail == b""


def test_unknown_id_still_rejects_with_preceding_context() -> None:
    with pytest.raises(ValueError, match="unknown packet 0xfafa at 6, preceding=\\['0x7f'\\]"):
        client.pdb.parse_stream(CLOCK + b"\xfa\xfa")


def test_reader_preserves_unknown_parser_error() -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    bot.sock = FakeSocket([CLOCK + b"\xfa\xfa"])
    bot.running = True
    bot._recv_loop()
    assert isinstance(bot.rx_error, ValueError)
    assert "unknown packet 0xfafa at 6, preceding=['0x7f']" in str(bot.rx_error)
    # Fail-closed batch parsing does not publish a partial success.
    assert bot.native_frame_snapshot()[2] == ()
    bot.close()


def test_clock_dispatch_records_once_without_inventing_authority() -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    before = (bot.x, bot.y, bot.class_fresh, bot.status_params.copy())
    tracker = NativeGameplayTracker(11)
    frames, tail = client.pdb.parse_stream(CLOCK + walking() + CLOCK)
    assert tail == b""
    for pid, raw in frames:
        bot._dispatch(pid, raw)
    snapshot = bot.native_frame_snapshot()
    assert [frame[0] for frame in snapshot[2]] == [1, 2, 3]
    assert [frame[2:] for frame in snapshot[2]] == frames
    assert (bot.x, bot.y, bot.class_fresh, bot.status_params) == before
    assert bot.rx_error is None
    assert bot.dispatch_errors == []
    assert tracker.consume_snapshot(*snapshot)
    assert tracker.consume_snapshot(*snapshot)
    view = tracker.view
    assert len(view.actors) == 1
    assert view.position is None
    assert view.alive is None
    assert not view.alive_known
    assert not view.perception_ready
    with pytest.raises(NativeTelemetryUnavailableError):
        require_native_vitals(bot.status_params)
    bot.close()


def test_reader_publishes_clock_and_walking_once_without_redispatch() -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    bot.sock = FakeSocket([CLOCK[:3], CLOCK[3:] + walking() + CLOCK, b""])
    bot.running = True
    bot._recv_loop()
    snapshot = bot.native_frame_snapshot()
    assert [frame[2] for frame in snapshot[2]] == [0x007F, 0x09FD, 0x007F]
    assert bot.packet_counts[0x007F] == 2
    assert bot.dispatch_errors == []
    assert isinstance(bot.rx_error, ConnectionError)  # Deliberate fixture EOF, not parser error.
    assert bot._poll() == (0x007F, CLOCK)
    bot.drain()
    assert bot.native_frame_snapshot() == snapshot
    bot.close()
