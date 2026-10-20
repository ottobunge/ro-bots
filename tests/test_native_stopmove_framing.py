"""Source-compiled stopmove framing only; never movement/arrival authority."""

import re
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from robots.adapters.native_gameplay import NativeGameplayTracker
from tests.test_client_protocol import FakeSocket, client
from tests.test_native_gameplay import actor as gameplay_actor
from tests.test_native_name_reply_framing import NPC, PLAYER, actor

SOURCE = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source/src")
STOP = struct.pack("<HIHH", 0x0088, 11, 123, 234)


def test_compiled_stopmove_layout(tmp_path: Path) -> None:
    header = (SOURCE / "map/packets.hpp").read_text()
    start = header.index("struct PACKET_ZC_STOPMOVE {")
    end = header.index("\n", header.index("DEFINE_PACKET_HEADER(ZC_STOPMOVE,", start))
    types = (SOURCE / "common/cbasetypes.hpp").read_text()
    typedefs = "\n".join(
        re.findall(
            r"^typedef (?:int16_t|uint16_t|uint32_t)\s+(?:int16|uint16|uint32);", types, re.M
        )
    )
    assert len(typedefs.splitlines()) == 3
    macro = re.search(r"^#define DEFINE_PACKET_HEADER\(name, id\).+$", header, re.M)
    assert macro is not None
    cpp = tmp_path / "stopmove-oracle.cpp"
    cpp.write_text(
        "#include <cstdint>\n#include <cstddef>\n#include <cstdio>\n"
        "#include <config/packets.hpp>\n"
        + typedefs
        + "\n"
        + macro[0]
        + "\n"
        + header[start:end]
        + "\nstatic_assert(PACKETVER_MAIN_NUM==20180704);\n"
        "#if !defined(PRERE) || defined(PACKETVER_RE) || defined(PACKETVER_ZERO) "
        "|| defined(RENEWAL)\n#error Wrong profile\n#endif\n"
        'int main(){printf("%d %zu %zu %zu %zu %zu",HEADER_ZC_STOPMOVE,'
        "sizeof(PACKET_ZC_STOPMOVE),offsetof(PACKET_ZC_STOPMOVE,packetType),"
        "offsetof(PACKET_ZC_STOPMOVE,AID),offsetof(PACKET_ZC_STOPMOVE,xPos),"
        "offsetof(PACKET_ZC_STOPMOVE,yPos));}\n"
    )
    compiler = shutil.which("g++")
    assert compiler is not None
    binary = tmp_path / "stopmove-oracle"
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
    assert result.stdout == "136 10 0 2 6 8"
    emission = (SOURCE / "map/clif.cpp").read_text()
    start = emission.index("void clif_fixpos( const block_list& bl )")
    end = emission.index("\n}\n", start)
    body = emission[start:end]
    assert "packet.packetType = HEADER_ZC_STOPMOVE;" in body
    assert "packet.AID = bl.id;" in body
    assert "packet.xPos = bl.x;" in body
    assert "packet.yPos = bl.y;" in body
    assert "clif_send( &packet, sizeof( packet ), &bl, AREA);" in body
    assert "packet.AID = disguised_bl_id( bl.id );" in body
    assert "clif_send( &packet, sizeof( packet ), &bl, SELF );" in body


def test_stopmove_reaches_actual_framer() -> None:
    assert client.pdb.parse_stream(STOP) == ([(0x0088, STOP)], b"")
    assert client.pdb.name_of(0x0088) == "ZC_STOPMOVE"


def test_coalesced_repeated_every_boundary() -> None:
    damage = struct.pack("<H", 0x08C8) + bytes(32)
    expected = [
        (0x0088, STOP),
        (0x09FD, actor(0x09FD)),
        (0x0ADF, NPC),
        (0x0088, STOP),
        (0x0A30, PLAYER),
        (0x08C8, damage),
        (0x09FF, actor(0x09FF)),
        (0x0088, STOP),
    ]
    stream = b"".join(raw for _, raw in expected)
    assert client.pdb.parse_stream(stream) == (expected, b"")
    for split in range(len(stream) + 1):
        first, pending = client.pdb.parse_stream(stream[:split])
        second, tail = client.pdb.parse_stream(pending + stream[split:])
        assert first + second == expected
        assert tail == b""
    for cut in range(1, len(STOP)):
        assert client.pdb.parse_stream(STOP[:cut]) == ([], STOP[:cut])
    frames = []
    pending = b""
    for byte in stream:
        complete, pending = client.pdb.parse_stream(pending + bytes([byte]))
        frames.extend(complete)
    assert frames == expected
    assert pending == b""
    assert [client.pdb.PACKET_DB[pid] for pid in (0x0ADF, 0x0A30, 0x007F)] == [58, 106, 6]


def test_unknown_id_remains_rejected() -> None:
    with pytest.raises(ValueError, match="unknown packet 0xfafa at 10, preceding=\\['0x88'\\]"):
        client.pdb.parse_stream(STOP + b"\xfa\xfa")


@pytest.mark.parametrize("aid", [11, 22, 42, (-11) & 0xFFFFFFFF])
def test_reader_stopmove_does_not_promote_authority(aid: int) -> None:
    raw = struct.pack("<HIHH", 0x0088, aid, 123, 234)
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    bot.aid = 11
    before = (bot.x, bot.y, bot.class_fresh, bot.status_params.copy())
    tracker = NativeGameplayTracker(11)
    tracker.consume_snapshot(*bot.native_frame_snapshot())
    view_before = tracker.view
    bot.sock = FakeSocket([raw[:3], raw[3:] + raw + raw, b""])
    bot.running = True
    bot._recv_loop()
    snapshot = bot.native_frame_snapshot()
    assert [frame[0] for frame in snapshot[2]] == [1, 2, 3]
    assert [frame[2:] for frame in snapshot[2]] == [(0x0088, raw)] * 3
    assert bot.packet_counts[0x0088] == 3
    assert bot.dispatch_errors == []
    assert isinstance(bot.rx_error, ConnectionError)  # Deliberate EOF only.
    assert (bot.x, bot.y, bot.class_fresh, bot.status_params) == before
    assert tracker.consume_snapshot(*snapshot)
    assert tracker.consume_snapshot(*snapshot)
    assert tracker.view == view_before
    assert tracker.view.position is None
    assert tracker.view.alive is None
    assert not tracker.view.alive_known
    assert not tracker.view.arrival_confirmed
    assert not tracker.view.perception_ready
    assert bot._poll() == (0x0088, raw)
    bot.drain()
    assert bot.native_frame_snapshot() == snapshot
    bot.close()


@pytest.mark.parametrize("aid", [11, 22, 42])
def test_stopmove_preserves_received_actor_positions(aid: int) -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    bot.aid = 11
    tracker = NativeGameplayTracker(11)
    for raw in (gameplay_actor(0x09FF, 22, 0), gameplay_actor(0x09FF, 42, 6)):
        frames, tail = client.pdb.parse_stream(raw)
        assert tail == b""
        for pid, framed in frames:
            bot._dispatch(pid, framed)
    assert tracker.consume_snapshot(*bot.native_frame_snapshot())
    before = tracker.view
    assert [entry.actor_id for entry in before.actors] == [22, 42]
    assert not any(entry.attackable for entry in before.actors)
    raw = struct.pack("<HIHH", 0x0088, aid, 123, 234)
    bot.sock = FakeSocket([raw, b""])
    bot.running = True
    bot._recv_loop()
    assert tracker.consume_snapshot(*bot.native_frame_snapshot())
    assert tracker.view == before
    assert not tracker.view.arrival_confirmed
    assert bot.dispatch_errors == []
    assert isinstance(bot.rx_error, ConnectionError)
    bot.close()
