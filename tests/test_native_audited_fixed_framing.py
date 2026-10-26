"""Audited fixed frames only: no native effects or gameplay promotion."""

import re
import shutil
import struct
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from robots.adapters.native_gameplay import NativeGameplayTracker
from tests.test_client_protocol import FakeSocket, client
from tests.test_native_name_reply_framing import NPC, PLAYER, actor

SOURCE = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source/src")
EXPECTED = [
    (0x0111, 39, "ZC_ADD_SKILL"),
    (0x0139, 16, "ZC_ATTACK_FAILURE_FOR_DISTANCE"),
    (0x0AB2, 7, "ZC_GROUP_ISALIVE"),
    (0x009D, 17, "ZC_ITEM_ENTRY"),
    (0x02B8, 22, "ZC_ITEM_PICKUP_PARTY"),
    (0x0117, 18, "ZC_NOTIFY_GROUNDSKILL"),
    (0x0ABD, 10, "ZC_NOTIFY_MEMBERINFO_TO_GROUPM"),
    (0x0441, 4, "ZC_SKILLINFO_DELETE"),
    (0x010E, 11, "ZC_SKILLINFO_UPDATE"),
    (0x07E1, 15, "ZC_SKILLINFO_UPDATE2"),
    (0x0120, 6, "ZC_SKILL_DISAPPEAR"),
    (0x043D, 8, "ZC_SKILL_POSTDELAY"),
    (0x07FB, 25, "ZC_USESKILL_ACK"),
    (0x09CB, 17, "ZC_USE_SKILL"),
]
ACTIVE = [
    (0x0111, 39, "ZC_ADD_SKILL"),
    (0x0139, 16, "ZC_ATTACK_FAILURE_FOR_DISTANCE"),
    (0x0AB2, 7, "ZC_GROUP_ISALIVE"),
    (0x009D, 17, "ZC_ITEM_ENTRY"),
    (0x02B8, 22, "ZC_ITEM_PICKUP_PARTY"),
    (0x0117, 18, "ZC_NOTIFY_GROUNDSKILL"),
    (0x0ABD, 10, "ZC_NOTIFY_MEMBERINFO_TO_GROUPM"),
    (0x0441, 4, "ZC_SKILLINFO_DELETE"),
    (0x010E, 11, "ZC_SKILLINFO_UPDATE"),
    (0x07E1, 15, "ZC_SKILLINFO_UPDATE2"),
    (0x0120, 6, "ZC_SKILL_DISAPPEAR"),
    (0x043D, 8, "ZC_SKILL_POSTDELAY"),
    (0x07FB, 25, "ZC_USESKILL_ACK"),
    (0x09CB, 17, "ZC_USE_SKILL"),
]


def compile_oracle(directory: Path) -> str:
    """Exclude only unrelated map include; use its exact guarded constants."""
    header = (SOURCE / "map/packets.hpp").read_text()
    assert '#include "map.hpp"' in header
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "packets-extract.hpp").write_text(
        header.replace('#include "map.hpp"', "// Unrelated script dependency excluded.")
    )
    map_header = (SOURCE / "map/map.hpp").read_text()
    start = map_header.index("#define MESSAGE_SIZE")
    end = map_header.index("\n", map_header.index("#endif", start)) + 1
    cpp = directory / "oracle.cpp"
    cpp.write_text(
        "#include <config/core.hpp>\n"
        + map_header[start:end]
        + '\n#include "packets-extract.hpp"\n#include <cstdio>\n'
        + "static_assert(PACKETVER_MAIN_NUM == 20180704);\n"
        + "#if !defined(PRERE) || defined(PACKETVER_RE) || defined(PACKETVER_ZERO) "
        + "|| defined(RENEWAL)\n#error Wrong profile\n#endif\nint main(){\n"
        + "".join(
            f'printf("{name} %d %zu\\n", HEADER_{name}, sizeof(PACKET_{name}));\n'
            for _, _, name in EXPECTED
        )
        + "}\n"
    )
    compiler = shutil.which("g++")
    assert compiler is not None
    command = [
        compiler,
        "-DPACKETVER=20180704",
        "-DPRERE",
        "-I" + str(SOURCE),
        "-I" + str(SOURCE / "map"),
    ]
    active = subprocess.run(
        [*command, "-E", str(cpp)], check=True, capture_output=True, text=True, timeout=30
    ).stdout
    (directory / "active-header.i").write_text(active)
    for _, _, name in EXPECTED:
        match = re.search(r"struct PACKET_" + name + r"\s*\{(.*?)\}\s*__attribute__", active, re.S)
        assert match is not None
        assert re.search(r"\[\s*\]", match[1]) is None  # Not a flexible prefix.
        assert not re.search(r"\b(?:packetLength|PacketLength)\b", match[1])
    binary = directory / "oracle"
    subprocess.run(
        [*command, str(cpp), "-o", str(binary)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    result = subprocess.run(
        [str(binary)], check=True, capture_output=True, text=True, timeout=5
    ).stdout
    (directory / "sizes.txt").write_text(result)
    assert result == "".join(f"{name} {pid} {size}\n" for pid, size, name in EXPECTED)
    return result


def test_actual_compiled_fixed_oracle(tmp_path: Path) -> None:
    compile_oracle(tmp_path)


@pytest.mark.parametrize(("pid", "size", "name"), ACTIVE)
def test_active_fixed_reaches_actual_framer(pid: int, size: int, name: str) -> None:
    raw = struct.pack("<H", pid) + bytes(size - 2)
    assert client.pdb.parse_stream(raw) == ([(pid, raw)], b"")
    assert client.pdb.name_of(pid) == name


@pytest.mark.parametrize(("pid", "size", "name"), EXPECTED)
def test_mixed_every_split_bytewise_truncation(pid: int, size: int, name: str) -> None:
    raw = struct.pack("<H", pid) + bytes(size - 2)
    damage = struct.pack("<H", 0x08C8) + bytes(32)
    clock = struct.pack("<HI", 0x007F, 123)
    stop = struct.pack("<HIHH", 0x0088, 11, 123, 234)
    expected = [
        (0x09FD, actor(0x09FD)),
        (pid, raw),
        (0x08C8, damage),
        (0x0ADF, NPC),
        (0x007F, clock),
        (0x0088, stop),
        (0x0A30, PLAYER),
        (pid, raw),
    ] * 2
    stream = b"".join(frame for _, frame in expected)
    assert client.pdb.parse_stream(stream) == (expected, b"")
    for split in range(len(stream) + 1):
        first, pending = client.pdb.parse_stream(stream[:split])
        second, tail = client.pdb.parse_stream(pending + stream[split:])
        assert first + second == expected
        assert tail == b""
    for cut in range(1, size):
        assert client.pdb.parse_stream(raw[:cut]) == ([], raw[:cut])
        assert client.pdb.parse_stream(raw[:cut] + raw[cut:]) == ([(pid, raw)], b"")
    pending = b""
    frames = []
    for byte in stream:
        complete, pending = client.pdb.parse_stream(pending + bytes([byte]))
        frames.extend(complete)
    assert frames == expected
    assert pending == b""
    assert client.pdb.name_of(pid) == name
    with pytest.raises(ValueError, match=rf"unknown packet 0xfafa at {size}, preceding="):
        client.pdb.parse_stream(raw + b"\xfa\xfa")


@pytest.mark.parametrize("aid", [11, (-11) & 0xFFFFFFFF, 22, 42])
def test_real_reader_fixed_frames_preserve_authority(aid: int) -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    bot.aid = 11
    tracker = NativeGameplayTracker(11)
    tracker.consume_snapshot(*bot.native_frame_snapshot())
    before = tracker.view
    client_before = (bot.x, bot.y, bot.class_fresh, bot.status_params.copy())
    frames = []
    for pid, size, _ in EXPECTED:
        raw = bytearray(size)
        struct.pack_into("<H", raw, 0, pid)
        if size >= 6:
            struct.pack_into("<I", raw, 2, aid)
        frames.append((pid, bytes(raw)))
    stream = b"".join(raw for _, raw in frames * 2)
    bot.sock = FakeSocket([stream[:3], stream[3:], b""])
    bot.running = True
    bot._recv_loop()
    snapshot = bot.native_frame_snapshot()
    assert [entry[2:] for entry in snapshot[2]] == frames * 2
    assert [entry[0] for entry in snapshot[2]] == list(range(1, 29))
    assert bot.dispatch_errors == []
    assert isinstance(bot.rx_error, ConnectionError)  # Deliberate EOF only.
    assert tracker.consume_snapshot(*snapshot)
    # The probes are observationally inert except ZC_USE_SKILL (0x09CB): its
    # received skill-use rows are real observations now (the human-contribution
    # ear), so the invariance pin compares everything but that field.
    after = tracker.view
    assert replace(after, skill_uses=()) == before
    assert (bot.x, bot.y, bot.class_fresh, bot.status_params) == client_before
    assert tracker.view.position is None
    assert tracker.view.alive is None
    assert not tracker.view.arrival_confirmed
    assert not tracker.view.perception_ready
    for pid, _, _ in EXPECTED:
        assert bot.packet_counts[pid] == 2
    bot.close()
