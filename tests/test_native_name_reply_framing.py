"""Pinned compiled name replies: framing only, not native gameplay acceptance."""

import re
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from robots.adapters.native_gameplay import NativeGameplayTracker
from tests.test_client_protocol import FakeSocket, client

SOURCE = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source/src")
NPC = struct.pack("<Hii24s24s", 0x0ADF, 42, 0, b"Offline", b"Title")
PLAYER = struct.pack("<Hi24s24s24s24si", 0x0A30, 42, b"Offline", b"", b"", b"", 0)


def test_compiled_name_reply_family(tmp_path: Path) -> None:
    header = (SOURCE / "map/packets_struct.hpp").read_text()
    start = header.index("#if PACKETVER_MAIN_NUM >= 20150225", header.index("// ZC_ACK_REQNAMEALL"))
    end = header.index("struct PACKET_ZC_OVERWEIGHT_PERCENT", start)
    name = re.search(r"^#define NAME_LENGTH\s+.+$", (SOURCE / "common/mmo.hpp").read_text(), re.M)
    assert name is not None
    cpp = tmp_path / "name-oracle.cpp"
    cpp.write_text(
        "#include <cstdint>\n#include <cstddef>\n#include <cstdio>\n"
        "#include <config/packets.hpp>\n"
        "using uint16=uint16_t; using int32=int32_t;\n"
        "#define DEFINE_PACKET_HEADER(name,id) constexpr int HEADER_##name=id\n"
        + name[0]
        + "\n"
        + header[start:end]
        + "\nstatic_assert(PACKETVER_MAIN_NUM==20180704);\n"
        "#if defined(PACKETVER_RE) || defined(PACKETVER_ZERO) || defined(RENEWAL)\n"
        "#error Wrong profile\n#endif\n"
        'int main(){printf("%d %d %zu %zu %zu %zu %zu %zu %d %zu %zu %zu %zu %zu %zu %zu %zu",'
        "NAME_LENGTH,HEADER_ZC_ACK_REQNAMEALL_NPC,sizeof(PACKET_ZC_ACK_REQNAMEALL_NPC),"
        "offsetof(PACKET_ZC_ACK_REQNAMEALL_NPC,packet_id),"
        "offsetof(PACKET_ZC_ACK_REQNAMEALL_NPC,gid),"
        "offsetof(PACKET_ZC_ACK_REQNAMEALL_NPC,groupId),"
        "offsetof(PACKET_ZC_ACK_REQNAMEALL_NPC,name),"
        "offsetof(PACKET_ZC_ACK_REQNAMEALL_NPC,title),"
        "HEADER_ZC_ACK_REQNAMEALL,sizeof(PACKET_ZC_ACK_REQNAMEALL),"
        "offsetof(PACKET_ZC_ACK_REQNAMEALL,packet_id),"
        "offsetof(PACKET_ZC_ACK_REQNAMEALL,gid),"
        "offsetof(PACKET_ZC_ACK_REQNAMEALL,name),"
        "offsetof(PACKET_ZC_ACK_REQNAMEALL,party_name),"
        "offsetof(PACKET_ZC_ACK_REQNAMEALL,guild_name),"
        "offsetof(PACKET_ZC_ACK_REQNAMEALL,position_name),"
        "offsetof(PACKET_ZC_ACK_REQNAMEALL,title_id));}\n"
    )
    compiler = shutil.which("g++")
    assert compiler is not None
    binary = tmp_path / "name-oracle"
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
    assert result.stdout == "24 2783 58 0 2 6 10 34 2608 106 0 2 6 30 54 78 102"
    emission = (SOURCE / "map/clif.cpp").read_text()
    for family in ("ZC_ACK_REQNAMEALL_NPC", "ZC_ACK_REQNAMEALL"):
        assert f"packet.packet_id = HEADER_{family};" in emission
    assert "clif_send(&packet, sizeof(packet), src, target);" in emission


def test_npc_name_reply_reaches_actual_framer() -> None:
    assert client.pdb.parse_stream(NPC) == ([(0x0ADF, NPC)], b"")
    assert client.pdb.name_of(0x0ADF) == "ZC_ACK_REQNAMEALL_NPC"


def actor(pid: int) -> bytes:
    size = {0x09FD: 110, 0x09FF: 104}[pid]
    raw = bytearray(size)
    struct.pack_into("<HHBII", raw, 0, pid, size, 6, 42, 0)
    return bytes(raw)


@pytest.mark.parametrize(("pid", "reply"), [(0x0ADF, NPC), (0x0A30, PLAYER)])
def test_family_coalesced_repeated_every_boundary(pid: int, reply: bytes) -> None:
    expected = [(0x09FD, actor(0x09FD)), (pid, reply), (pid, reply), (0x09FF, actor(0x09FF))]
    stream = b"".join(raw for _, raw in expected)
    assert client.pdb.parse_stream(stream) == (expected, b"")
    for split in range(len(stream) + 1):
        first, pending = client.pdb.parse_stream(stream[:split])
        second, tail = client.pdb.parse_stream(pending + stream[split:])
        assert first + second == expected
        assert tail == b""
    for cut in range(1, len(reply)):
        assert client.pdb.parse_stream(reply[:cut]) == ([], reply[:cut])
    frames = []
    pending = b""
    for byte in stream:
        complete, pending = client.pdb.parse_stream(pending + bytes([byte]))
        frames.extend(complete)
    assert frames == expected
    assert pending == b""


def test_unknown_id_remains_fail_closed() -> None:
    with pytest.raises(ValueError, match="unknown packet 0xfafa at 58, preceding=\\['0xadf'\\]"):
        client.pdb.parse_stream(NPC + b"\xfa\xfa")


def test_name_reader_sequences_once_without_authority() -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    before = (bot.x, bot.y, bot.class_fresh, bot.status_params.copy())
    bot.sock = FakeSocket([NPC[:5], NPC[5:] + PLAYER + NPC, b""])
    bot.running = True
    bot._recv_loop()
    snapshot = bot.native_frame_snapshot()
    assert [frame[0] for frame in snapshot[2]] == [1, 2, 3]
    assert [frame[2:] for frame in snapshot[2]] == [(0x0ADF, NPC), (0x0A30, PLAYER), (0x0ADF, NPC)]
    assert bot.packet_counts[0x0ADF] == 2
    assert bot.dispatch_errors == []
    assert isinstance(bot.rx_error, ConnectionError)  # Deliberate fixture EOF.
    assert (bot.x, bot.y, bot.class_fresh, bot.status_params) == before
    tracker = NativeGameplayTracker(11)
    assert tracker.consume_snapshot(*snapshot)
    assert tracker.consume_snapshot(*snapshot)
    assert tracker.view.position is None
    assert tracker.view.alive is None
    assert not tracker.view.alive_known
    assert tracker.view.actors == ()
    assert not tracker.view.perception_ready
    bot.drain()
    assert bot.native_frame_snapshot() == snapshot
    bot.close()
