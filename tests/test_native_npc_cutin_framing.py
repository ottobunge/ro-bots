"""Cut-in framing only: no NPC identity, gameplay, or interpretation authority."""

import hashlib
import json
import shlex
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from tests.test_native_npc_close_framing import packet_module
from tests.test_native_protocol_manifest import CPPFLAGS, SOURCE
from tests.test_native_protocol_manifest import (
    test_immutable_source_profile_sender_binding as bind_source,
)

CUTIN = struct.pack("<H64sB", 0x01B3, b"guide.bmp\0", 0)
TEXT = struct.pack("<HHI", 0x00B4, 14, 0x12345678) + b"Guide\0"
NEXT = struct.pack("<HI", 0x00B5, 0x12345678)


def test_reached_cutin_then_npc_text_next() -> None:
    assert len(CUTIN) == 67
    expected = [(0x01B3, CUTIN), (0x00B4, TEXT), (0x00B5, NEXT)]
    assert packet_module().parse_stream(CUTIN + TEXT + NEXT) == (expected, b"")


@pytest.mark.parametrize("compiler_name", ["g++", "clang++"])
def test_bound_full_unchanged_header_oracle(tmp_path: Path, compiler_name: str) -> None:
    # Authorize the installed configured source and exact flags BEFORE compiler lookup/run.
    bind_source()
    includes = [
        SOURCE / relative
        for relative in (
            "src",
            "src/common",
            "3rdparty/libconfig",
            "3rdparty/rapidyaml/src",
            "3rdparty/rapidyaml/ext/c4core/src",
        )
    ] + [
        Path("/nix/store/1w8g6rvhljfk44hx50qz4sc47sm1f28v-mariadb-connector-c-3.3.5-dev/include"),
        Path(
            "/nix/store/1w8g6rvhljfk44hx50qz4sc47sm1f28v-mariadb-connector-c-3.3.5-dev/include/mysql"
        ),
    ]
    assert all(path.is_dir() for path in includes)
    cpp = tmp_path / "cutin.cpp"
    cpp.write_text(
        "#include <config/core.hpp>\n#include <map/packets.hpp>\n"
        "#include <map/packets_struct.hpp>\n#include <cstdio>\n#include <cstddef>\n"
        "#include <type_traits>\n"
        "static_assert(PACKETVER == 20180704 && PACKETVER_MAIN_NUM == 20180704);\n"
        "#if !defined(PRERE) || defined(RENEWAL) || defined(PACKETVER_RE) || "
        "defined(PACKETVER_ZERO) || defined(PACKET_OBFUSCATION) || "
        "defined(PACKET_OBFUSCATION_WARN)\n#error Unreviewed_profile\n#endif\n"
        "static_assert(HEADER_ZC_SHOW_IMAGE == 0x01b3);\n"
        "static_assert(sizeof(PACKET_ZC_SHOW_IMAGE) == 67);\n"
        "static_assert(alignof(PACKET_ZC_SHOW_IMAGE) == 1);\n"
        "static_assert(offsetof(PACKET_ZC_SHOW_IMAGE, packetType) == 0);\n"
        "static_assert(offsetof(PACKET_ZC_SHOW_IMAGE, image) == 2);\n"
        "static_assert(offsetof(PACKET_ZC_SHOW_IMAGE, type) == 66);\n"
        "static_assert(sizeof(PACKET_ZC_SHOW_IMAGE::packetType) == 2);\n"
        "static_assert(sizeof(PACKET_ZC_SHOW_IMAGE::image) == 64);\n"
        "static_assert(sizeof(PACKET_ZC_SHOW_IMAGE::type) == 1);\n"
        "static_assert(std::is_signed_v<decltype(PACKET_ZC_SHOW_IMAGE::packetType)>);\n"
        "static_assert(std::is_same_v<decltype(PACKET_ZC_SHOW_IMAGE::image), char[64]>);\n"
        "static_assert(std::is_same_v<decltype(PACKET_ZC_SHOW_IMAGE::type), uint8>);\n"
        'int main(){printf("%d %zu %zu %zu %zu %zu %zu %zu %zu %d %d %d\\n", '
        "HEADER_ZC_SHOW_IMAGE,sizeof(PACKET_ZC_SHOW_IMAGE),alignof(PACKET_ZC_SHOW_IMAGE),"
        "offsetof(PACKET_ZC_SHOW_IMAGE,packetType),offsetof(PACKET_ZC_SHOW_IMAGE,image),"
        "offsetof(PACKET_ZC_SHOW_IMAGE,type),sizeof(PACKET_ZC_SHOW_IMAGE::packetType),"
        "sizeof(PACKET_ZC_SHOW_IMAGE::image),sizeof(PACKET_ZC_SHOW_IMAGE::type),"
        "std::is_signed_v<decltype(PACKET_ZC_SHOW_IMAGE::packetType)>,"
        "std::is_signed_v<char>,std::is_signed_v<decltype(PACKET_ZC_SHOW_IMAGE::type)>);}\n"
    )
    compiler = shutil.which(compiler_name)
    assert compiler is not None
    binary = tmp_path / "cutin"
    command = [
        compiler,
        *shlex.split(CPPFLAGS),
        *["-I" + str(path) for path in includes],
        str(cpp),
        "-o",
        str(binary),
    ]
    (tmp_path / "command.json").write_text(json.dumps(command))
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=30)
    (tmp_path / "compile.stdout").write_text(result.stdout)
    (tmp_path / "compile.stderr").write_text(result.stderr)
    assert result.returncode == 0, result.stderr
    observed = subprocess.run([str(binary)], check=True, capture_output=True, text=True, timeout=5)
    (tmp_path / "oracle.stdout").write_text(observed.stdout)
    assert observed.stdout == "435 67 1 0 2 66 2 64 1 1 1 0\n"


def validate_cutin_manifest(manifest: dict[str, object]) -> None:
    expected = json.loads(
        (Path(__file__).resolve().parents[1] / "protocol/main-20180704-pre-re.json").read_text()
    )
    assert manifest["profile"] == expected["profile"]
    packets = manifest["packets"]
    assert isinstance(packets, list)
    assert len(packets) == 1
    row = packets[0]
    assert isinstance(row, dict)
    assert type(row["id"]) is int
    assert row["id"] == 0x01B3
    assert type(row["length"]) is int
    assert row["length"] == 67
    assert type(row["alignment"]) is int
    assert row["alignment"] == 1
    assert row["fields"] == [
        {"name": "packetType", "offset": 0, "width": 2, "cpp_type": "int16", "signed": True},
        {"name": "image", "offset": 2, "width": 64, "cpp_type": "char[64]", "signed": True},
        {"name": "type", "offset": 66, "width": 1, "cpp_type": "uint8", "signed": False},
    ]
    assert row["presentation_only"] is True
    assert row["approved"] is False
    assert row["cpp_record"] == "PACKET_ZC_SHOW_IMAGE"
    assert row["cpp_header"] == "HEADER_ZC_SHOW_IMAGE"
    assert row["direction"] == "S->C"
    assert row["framing"] == "fixed"
    provenance = manifest["provenance"]
    assert isinstance(provenance, dict)
    assert {key: provenance[key] for key in expected["provenance"]} == expected["provenance"]


def test_measured_candidate_manifest() -> None:
    validate_cutin_manifest(
        json.loads((ROOT / "protocol/main-20180704-pre-re-npc-cutin.json").read_text())
    )


@pytest.mark.parametrize(
    "mutation", ["id", "length", "alignment", "field", "extra", "missing", "profile"]
)
def test_manifest_changes_fail_closed(mutation: str) -> None:
    manifest = json.loads((ROOT / "protocol/main-20180704-pre-re-npc-cutin.json").read_text())
    if mutation in {"id", "length", "alignment"}:
        manifest["packets"][0][mutation] = True
    elif mutation == "field":
        manifest["packets"][0]["fields"][1]["width"] = 63
    elif mutation == "extra":
        manifest["packets"].append(manifest["packets"][0])
    elif mutation == "missing":
        manifest["packets"] = []
    else:
        manifest["profile"]["ruleset"] = "renewal"
    with pytest.raises(AssertionError):
        validate_cutin_manifest(manifest)


ROOT = Path(__file__).resolve().parents[1]
CUTIN_BLOCK = (
    b"# Source/compiler-measured cut-in presentation only; no NPC/gameplay authority.\n"
    b"# See protocol/main-20180704-pre-re-npc-cutin.json.\n"
    b"PACKET_DB.update({0x01B3: 67})\n\n\n"
)
# Reviewed charlist-per-page framing entry (see
# .work/playing-grind-protocol-completion/evidence/oracle_pinned_layout.log).
CHAR_PAGE_BLOCK = (
    b"    # Pinned common/packets.hpp:621-626 (#else branch @20180704): int16\n"
    b"    # packetType + int16 packetLength + CHARACTER_INFO(155)[] tail. Sent only\n"
    b"    # in reply to client CH_CHARLIST_REQ 0x09A1 (char_clif.cpp:893-898),\n"
    b"    # twice when exactly 3 chars. Executed pinned-include oracle\n"
    b"    # (.work/playing-grind-protocol-completion/evidence/oracle_pinned_layout.log):\n"
    b"    # HEADER=0x099d, base sizeof=4, len word @2. 0x0B72 needs MAIN>=20201007.\n"
    b"    0x099D: -1,     # HC_ACK_CHARINFO_PER_PAGE: len word @2, 155B/char entry\n"
)
# Reviewed status-change receive entry (see
# .work/e2e-run/evidence/oracle_zc_status_change.log).
STAT_CHANGE_BLOCK = (
    b"# Narrow source/compiler-proven status-change receive addition. Preserve all\n"
    b"# prior entries and strict unknown rejection. ZC_STATUS_CHANGE 0x00BE\n"
    b"# (<statusID>.W <value>.B, 5B packed \xe2\x80\x94 packets_struct.hpp:368-373, oracle\n"
    b"# sizeof=5) is the SP_U* point-cost update the pinned server sends during the\n"
    b"# login status calc and after every stat spend (clif.cpp:3774); without it the\n"
    b"# reader dies mid-login-burst and the session starves. Executed pinned-include\n"
    b"# oracle: .work/e2e-run/evidence/oracle_zc_status_change.log\n"
    b"PACKET_DB.update({0x00BE: 5})\n\n\n"
)
SELF = struct.pack("<HHi", 0x00B0, 5, 42)
CLOCK = struct.pack("<HI", 0x007F, 123)
CLOSE = struct.pack("<HI", 0x00B6, 0x12345678)
FRAMES = [
    (0x007F, CLOCK),
    (0x01B3, CUTIN),
    (0x00B4, TEXT),
    (0x00B5, NEXT),
    (0x00B0, SELF),
    (0x01B3, CUTIN),
    (0x00B6, CLOSE),
    (0x01B3, CUTIN),
]
STREAM = b"".join(raw for _, raw in FRAMES)


@pytest.mark.parametrize("split", range(len(STREAM) + 1))
def test_every_split_preserves_exact_adjacent_frames(split: int) -> None:
    module = packet_module()
    first, pending = module.parse_stream(STREAM[:split])
    second, tail = module.parse_stream(pending + STREAM[split:])
    assert first + second == FRAMES
    assert tail == b""


@pytest.mark.parametrize("cut", range(67))
def test_short_cutin_remains_pending(cut: int) -> None:
    assert packet_module().parse_stream(CUTIN[:cut]) == ([], CUTIN[:cut])


def test_one_byte_chunks() -> None:
    module = packet_module()
    frames: list[tuple[int, bytes]] = []
    pending = b""
    for byte in STREAM:
        ready, pending = module.parse_stream(pending + bytes([byte]))
        frames.extend(ready)
    assert frames == FRAMES
    assert pending == b""


@pytest.mark.parametrize("subtype", [0, 1, 2, 255])
def test_image_and_subtype_are_opaque(subtype: int) -> None:
    raw = struct.pack("<H64sB", 0x01B3, bytes(range(64)), subtype)
    assert packet_module().parse_stream(raw) == ([(0x01B3, raw)], b"")


@pytest.mark.parametrize("prefix", [b"", CUTIN, STREAM])
def test_unknown_or_trailing_unknown_stays_strict(prefix: bytes) -> None:
    with pytest.raises(ValueError, match=f"unknown packet 0xfafa at {len(prefix)},"):
        packet_module().parse_stream(prefix + b"\xfa\xfa")


def test_trailing_partial_is_not_discarded() -> None:
    assert packet_module().parse_stream(CUTIN + b"\xfa") == ([(0x01B3, CUTIN)], b"\xfa")
    with pytest.raises(ValueError, match="bad variable length 3 for 0x00b4"):
        packet_module().parse_stream(CUTIN + struct.pack("<HH", 0x00B4, 3))
    with pytest.raises(ValueError, match="fixed length 67"):
        packet_module().pack(0x01B3, CUTIN[2:] + b"x")


def validate_exact_addition(table: dict[int, int], raw: bytes) -> None:
    prior = json.loads(
        (ROOT / "run/reviews/playing-mvp-native-npc-cutin-framing-fix.json").read_text()
    )["hash_evidence"]["before"]
    baseline = {int(key): value for key, value in prior["mappings"].items()}
    assert len(baseline) == 896
    assert 0x01B3 not in baseline
    assert 0x099D not in baseline
    # Reviewed additions after the cut-in slice: charlist-per-page framing
    # (0x099D; pinned common/packets.hpp:621-626 #else branch at 20180704).
    prior_897 = baseline | {0x01B3: 67}
    prior_898 = prior_897 | {0x099D: -1}
    # Criterion-9 stat ack (0x00BC, the stat-allocation slice): the only
    # addition after the cutin-era final table.
    prior_899 = prior_898 | {0x00BC: 6}
    # ZC_STATUS_CHANGE point-cost updates (0x00BE, the e2e-world slice).
    prior_900 = prior_899 | {0x00BE: 5}
    # ZC_PC_SELL_ITEMLIST (0x00C7, the shop-list slice): length-prefixed
    # variable packet; the framer strictly rejected it before this addition.
    prior_901 = prior_900 | {0x00C7: -1}
    # Party invite re-registration (0x2C4: 6 -> 26, the party slice): MAIN
    # 20180704 parse registration CZ_PARTY_JOIN_REQ (packets.hpp:1368-1373);
    # the numeric section still carries the older-era 6B size, hence the
    # live-verified shadow override rather than an addition.
    prior_901 = prior_901 | {0x2C4: 26}
    assert len(table) == 901
    assert table == prior_901
    assert raw.count(CUTIN_BLOCK) == 1
    assert raw.count(CHAR_PAGE_BLOCK) == 1
    assert raw.count(STAT_CHANGE_BLOCK) == 1
    stripped = (
        raw.replace(CUTIN_BLOCK, b"", 1)
        .replace(CHAR_PAGE_BLOCK, b"", 1)
        .replace(STAT_CHANGE_BLOCK, b"", 1)
    )
    current_hash = hashlib.sha256(stripped).hexdigest()
    historical = prior["files"]["spikes/003-clientless-limbs/packetdb.py"]
    # The criterion-9 lane added the 0x00BC entry to the PACKET_DB literal
    # (the acknowledged table delta above); either the historical cutin-era
    # source or its +0x00BC descendant is accepted, nothing else.
    assert current_hash in (
        historical,
        "465274d1518bdb8151840660490fd116c11a4c44dc69cb0241331d5ca21813bc",
        # the shop-list slice: +0x00C7 (and 0x00C6 already present) appended
        # after the 0x00BE block (the w82/w83 null-offer framer fix)
        "d190c4837b578b2ba4fb6afd702197690314c74fe858b9f478106b942a2b7411",
        # the party slice: the 0x2C4 shadow override (6 -> 26, MAIN 20180704
        # CZ_PARTY_JOIN_REQ) + its accounting comment appended to packetdb.py
        "ebbd4985b4d714c1a6b291d8944640521e3ee37d8dc0cbf4f6b7be133668d2cd",
    )


def test_exact_single_addition_and_old_bytes() -> None:
    validate_exact_addition(
        packet_module().PACKET_DB, (ROOT / "spikes/003-clientless-limbs/packetdb.py").read_bytes()
    )


@pytest.mark.parametrize("mutation", ["old", "extra", "changed", "missing"])
def test_table_mutations_rejected(mutation: str) -> None:
    table = dict(packet_module().PACKET_DB)
    if mutation == "old":
        table[0x007F] = 7
    elif mutation == "extra":
        table[0xFAFA] = 2
    elif mutation == "changed":
        table[0x01B3] = 68
    else:
        table.pop(0x01B3, None)
    with pytest.raises(AssertionError):
        validate_exact_addition(
            table, (ROOT / "spikes/003-clientless-limbs/packetdb.py").read_bytes()
        )
