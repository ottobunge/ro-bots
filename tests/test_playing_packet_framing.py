"""Actual inherited framing, with literal pinned MAIN20180704 wire IDs."""

import importlib.util
import re
import shutil
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

FRAMES = (
    (0x0A37, bytes.fromhex("370a") + bytes(57)),
    (0x0991, bytes.fromhex("91091c000200f501000300") + bytes(17)),
    (0x00A1, bytes.fromhex("a100") + bytes(4)),
    (0x0148, bytes.fromhex("4801") + bytes(6)),
    (0x00AF, bytes.fromhex("af00") + bytes(4)),
    (0x07FA, bytes.fromhex("fa07") + bytes(6)),
    (0x0A0D, bytes.fromhex("0d0a3d00") + bytes(57)),
)


@pytest.mark.parametrize(("pid", "raw"), FRAMES)
def test_individual_coalesced_and_every_incremental_split(pid: int, raw: bytes) -> None:
    db = packetdb()
    assert db.parse_stream(raw) == ([(pid, raw)], b"")
    suffix = bytes.fromhex("b000180000000000")
    stream = raw + suffix
    assert db.parse_stream(stream) == ([(pid, raw), (0x00B0, suffix)], b"")
    for cut in range(len(stream) + 1):
        first, rest = db.parse_stream(stream[:cut])
        second, tail = db.parse_stream(rest + stream[cut:])
        assert first + second == [(pid, raw), (0x00B0, suffix)]
        assert tail == b""


def test_unknown_stream_id_still_denies() -> None:
    with pytest.raises(ValueError, match="unknown packet 0xffff"):
        packetdb().parse_stream(bytes.fromhex("ffff"))


def test_final_native_outgoing_lengths_unchanged() -> None:
    db = packetdb()
    assert db.PACKET_DB[0x0437] == 7
    assert db.PACKET_DB[0x0362] == 6
    assert db.PACKET_DB[0x08B8] == 10
    assert db.PACKET_DB[0x08B9] == 12


ROOT = Path(__file__).resolve().parents[1]


def packetdb() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "playing_packetdb", ROOT / "spikes/003-clientless-limbs/packetdb.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_literal_pickup_ack_reaches_actual_framer() -> None:
    raw = bytes.fromhex("370a") + bytes(57)
    assert packetdb().parse_stream(raw) == ([(0x0A37, raw)], b"")


def test_primary_compiled_six_frame_layouts(tmp_path: Path) -> None:
    source = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source/src")
    structs = (source / "map/packets_struct.hpp").read_text()
    packets = (source / "map/packets.hpp").read_text()
    names = (
        "EQUIPSLOTINFO",
        "NORMALITEM_INFO",
        "ItemOptions",
        "PACKET_ZC_ITEM_PICKUP_ACK",
        "packet_itemlist_normal",
        "PACKET_ZC_ITEM_DISAPPEAR",
        "PACKET_ZC_RESURRECTION",
        "PACKET_ZC_ITEM_THROW_ACK",
        "PACKET_ZC_DELETE_ITEM_FROM_BODY",
    )
    declarations = []
    for name in names:
        match = re.search(
            r"struct " + name + r" \{.*?\} __attribute__\(\(packed\)\);", structs + packets, re.S
        )
        assert match is not None
        declarations.append(match[0])
    cpp = tmp_path / "oracle.cpp"
    cpp.write_text(
        "#include <cstdint>\n#include <cstddef>\n#include <cstdio>\n#include <config/packets.hpp>\n"
        "using int16=int16_t; using uint16=uint16_t; using int32=int32_t;\n"
        "using uint32=uint32_t; using uint8=uint8_t;\n"
        "#define MAX_ITEM_OPTIONS 5\n#define MAX_ITEMLIST 100\n"
        + "\n".join(declarations)
        + "\nstatic_assert(PACKETVER_MAIN_NUM == 20180704);\n"
        + 'int main(){printf("%zu %zu %zu %zu %zu %zu %zu",\n'
        + "sizeof(PACKET_ZC_ITEM_PICKUP_ACK),offsetof(packet_itemlist_normal,list),\n"
        + "sizeof(NORMALITEM_INFO),sizeof(PACKET_ZC_ITEM_DISAPPEAR),\n"
        + "sizeof(PACKET_ZC_RESURRECTION),sizeof(PACKET_ZC_ITEM_THROW_ACK),\n"
        + "sizeof(PACKET_ZC_DELETE_ITEM_FROM_BODY));}\n"
    )
    compiler = shutil.which("g++")
    assert compiler is not None
    binary = tmp_path / "oracle"
    subprocess.run(
        [
            compiler,
            "-DPACKETVER=20180704",
            "-DPRERE",
            "-I" + str(source),
            str(cpp),
            "-o",
            str(binary),
        ],
        check=True,
        capture_output=True,
    )
    result = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
    assert result.stdout == "59 4 24 6 8 6 8"
