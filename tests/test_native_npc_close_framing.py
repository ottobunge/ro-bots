"""Synthetic real-framer regressions and pinned full-header NPC-close evidence."""

import hashlib
import importlib.util
import json
import shlex
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "protocol/main-20180704-pre-re-npc-close.json"
PACKAGE = Path(
    "/nix/store/0w1nfsmj8gaipcidhgx2nkg4axqxcbbr-rathena-playable-callback-qualified-"
    "20180704-e985006171d2-callback-qualified"
)
EVIDENCE = PACKAGE / "share/rathena-playable-callback-qualified"
SOURCE = ROOT / "run/public-source/callback-qualified-e985006171d2"
CPPFLAGS = (
    "-std=c++17 -DHAS_TLS -fno-strict-aliasing -DHAVE_GETADDRINFO -DHAVE_SETRLIMIT "
    "-DHAVE_STRNLEN -DPACKETVER=20180704 -DPRERE -DHAVE_MONOTONIC_CLOCK "
    "-DHAS_TLS -fno-strict-aliasing -DHAVE_GETADDRINFO -DHAVE_SETRLIMIT "
    "-DHAVE_STRNLEN -DPACKETVER=20180704 -DPRERE -DHAVE_MONOTONIC_CLOCK"
)
FIELDS = [
    {"name": "packetType", "wire_type": "uint16", "cpp_type": "int16", "offset": 0, "width": 2},
    {"name": "npcId", "wire_type": "uint32", "cpp_type": "uint32", "offset": 2, "width": 4},
]


def packet_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "npc_close_packetdb", ROOT / "spikes/003-clientless-limbs/packetdb.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("npc_id", [0, 0x12345678, 0x80000000, 0xFFFFFFFF, 0xFAFA00B6])
def test_npc_close_individual(npc_id: int) -> None:
    # Arbitrary payloads are opaque bytes, never NPC identity approval.
    raw = struct.pack("<HI", 0x00B6, npc_id)
    assert packet_module().parse_stream(raw) == ([(0x00B6, raw)], b"")


CLOSE = struct.pack("<HI", 0x00B6, 0x12345678)
B0 = struct.pack("<HHi", 0x00B0, 5, 42)
CLOCK = struct.pack("<HI", 0x007F, 123)
EMOTION = struct.pack("<HIB", 0x00C0, 42, 1)
DEATH = struct.pack("<HIB", 0x0080, 42, 1)
# Opaque synthetic bodies, not fabricated native captures or new layout claims.
# The observed predecessor IDs are already fixed at 9, 7, 7 in the frozen table.
PREDECESSORS = [
    (0x0196, bytes.fromhex("9601") + bytes(7)),
    (0x0AB2, bytes.fromhex("b20a") + bytes(5)),
    (0x0080, DEATH),
]
CHAT = struct.pack("<HH", 0x008E, 7) + b"hi\0"
EXPECTED = [
    *PREDECESSORS,
    (0x00B6, CLOSE),
    (0x00B0, B0),
    (0x007F, CLOCK),
    (0x00C0, EMOTION),
    (0x008E, CHAT),
    (0x00B6, CLOSE),
    (0x00B6, CLOSE),
]
STREAM = b"".join(raw for _, raw in EXPECTED)


def test_coalesced_predecessor_boundary() -> None:
    module = packet_module()
    assert [module.length_of(pid) for pid, _ in PREDECESSORS] == [9, 7, 7]
    assert module.is_variable(0x008E)
    assert module.parse_stream(STREAM) == (EXPECTED, b"")


@pytest.mark.parametrize("split", range(len(STREAM) + 1))
def test_every_split_retains_exact_frames(split: int) -> None:
    module = packet_module()
    first, pending = module.parse_stream(STREAM[:split])
    second, tail = module.parse_stream(pending + STREAM[split:])
    assert first + second == EXPECTED
    assert tail == b""


@pytest.mark.parametrize("cut", range(len(CLOSE)))
def test_incomplete_close_retained_exactly(cut: int) -> None:
    module = packet_module()
    assert module.parse_stream(CLOSE[:cut]) == ([], CLOSE[:cut])
    assert module.parse_stream(CLOCK + CLOSE[:cut]) == ([(0x007F, CLOCK)], CLOSE[:cut])


def test_one_byte_chunks() -> None:
    module = packet_module()
    pending = b""
    frames: list[tuple[int, bytes]] = []
    for byte in STREAM:
        complete, pending = module.parse_stream(pending + bytes([byte]))
        frames.extend(complete)
    assert frames == EXPECTED
    assert pending == b""


@pytest.mark.parametrize("prefix", [b"", CLOSE, CLOSE + CLOSE, STREAM])
def test_unknown_successor_remains_strict(prefix: bytes) -> None:
    with pytest.raises(ValueError, match=f"unknown packet 0xfafa at {len(prefix)},"):
        packet_module().parse_stream(prefix + b"\xfa\xfa" + CLOCK)


@pytest.mark.parametrize("size", [0, 1, 2, 3])
def test_existing_bad_variable_length_remains_strict(size: int) -> None:
    with pytest.raises(ValueError, match=f"bad variable length {size} for 0x008e"):
        packet_module().parse_stream(CLOSE + struct.pack("<HH", 0x008E, size))


def test_all_889_mappings_macros_and_parser_preserved_bitexact() -> None:
    module = packet_module()
    baseline = json.loads(
        (ROOT / "run/reviews/native-manifest-migration-baseline.json").read_text()
    )["current_final_PACKET_DB"]
    old = {int(key, 16): value for key, value in baseline.items()} | {0x00C0: 7}
    assert len(old) == 889
    assert 0x00B6 not in old
    additions = {0x00B4: -1, 0x00B5: 6, 0x00B7: -1, 0x00C4: 6, 0x0142: 6, 0x01D4: 6}
    manifest = json.loads((ROOT / "protocol/main-20180704-pre-re-npc-dialogue.json").read_text())
    assert {
        row["id"]: row["length"] for row in manifest["packets"] if row["id"] in additions
    } == additions
    presentation = {0x01B3: 67}
    char_page = {0x099D: -1}  # charlist-per-page framing (pinned common/packets.hpp:621-626)
    stat_change = {0x00BE: 5}  # ZC_STATUS_CHANGE SP_U* point-cost updates (clif.cpp:3774)
    shop_lists = {0x00C7: -1}  # ZC_PC_SELL_ITEMLIST: length-prefixed variable (clif.cpp:2265-2280)
    # Guild-create slice: ZC_RESULT_MAKE_GUILD 0x0167 (3B), the live-verified
    # charter reply (0x0165 30B is already in the migration baseline).
    guild_reply = {0x0167: 3}
    # Guild invite slice (packets.hpp:1302-1330): the inviter ack + the
    # invitee prompt + the reply echo, all live-verified on the e2e world.
    guild_invite = {0x0169: 3, 0x016A: 30, 0x016B: 10}
    assert module.PACKET_DB[0x01B3] == 67
    prior_891 = {
        key: value
        for key, value in module.PACKET_DB.items()
        if key not in additions
        and key not in presentation
        and key not in char_page
        and key not in stat_change
        and key not in shop_lists
        and key not in guild_reply
        and key not in guild_invite
    }
    assert old | {0x00B6: 6, 0x00BC: 6} == prior_891
    assert len(prior_891) == 891
    assert not additions.keys() & prior_891.keys()
    assert not char_page.keys() & prior_891.keys()
    assert (
        prior_891
        | additions
        | presentation
        | char_page
        | stat_change
        | shop_lists
        | guild_reply
        | guild_invite
        == module.PACKET_DB
    )
    assert len(module.PACKET_DB) == 905
    raw = (ROOT / "spikes/003-clientless-limbs/packetdb.py").read_bytes()
    cutin_block = (
        b"# Source/compiler-measured cut-in presentation only; no NPC/gameplay authority.\n"
        b"# See protocol/main-20180704-pre-re-npc-cutin.json.\n"
        b"PACKET_DB.update({0x01B3: 67})\n\n\n"
    )
    assert raw.count(cutin_block) == 1
    raw = raw.replace(cutin_block, b"", 1)
    stat_change_block = (
        b"# Narrow source/compiler-proven status-change receive addition. Preserve all\n"
        b"# prior entries and strict unknown rejection. ZC_STATUS_CHANGE 0x00BE\n"
        b"# (<statusID>.W <value>.B, 5B packed \xe2\x80\x94 packets_struct.hpp:368-373, oracle\n"
        b"# sizeof=5) is the SP_U* point-cost update the pinned server sends during the\n"
        b"# login status calc and after every stat spend (clif.cpp:3774); without it the\n"
        b"# reader dies mid-login-burst and the session starves. Executed pinned-include\n"
        b"# oracle: .work/e2e-run/evidence/oracle_zc_status_change.log\n"
        b"PACKET_DB.update({0x00BE: 5})\n\n\n"
    )
    assert raw.count(stat_change_block) == 1
    raw = raw.replace(stat_change_block, b"", 1)
    block = (
        b"# Narrow source/compiler-proven NPC receive additions. Preserve all 890 prior\n"
        b"# entries and strict unknown rejection. See protocol/...-npc-dialogue.json.\n"
        b"PACKET_DB.update({0x00B4: -1, 0x00B5: 6, 0x00B7: -1,\n"
        b"                  0x00C4: 6, 0x0142: 6, 0x01D4: 6})\n\n\n"
    )
    assert raw.count(block) == 1
    raw = raw.replace(block, b"", 1)
    char_page_block = (
        b"    # Pinned common/packets.hpp:621-626 (#else branch @20180704): int16\n"
        b"    # packetType + int16 packetLength + CHARACTER_INFO(155)[] tail. Sent only\n"
        b"    # in reply to client CH_CHARLIST_REQ 0x09A1 (char_clif.cpp:893-898),\n"
        b"    # twice when exactly 3 chars. Executed pinned-include oracle\n"
        b"    # (.work/playing-grind-protocol-completion/evidence/oracle_pinned_layout.log):\n"
        b"    # HEADER=0x099d, base sizeof=4, len word @2. 0x0B72 needs MAIN>=20201007.\n"
        b"    0x099D: -1,     # HC_ACK_CHARINFO_PER_PAGE: len word @2, 155B/char entry\n"
    )
    assert raw.count(char_page_block) == 1
    raw = raw.replace(char_page_block, b"", 1)
    assert hashlib.sha256(raw).hexdigest() in (
        # the party slice: the 0x2C4 shadow override (6 -> 26, MAIN 20180704
        # CZ_PARTY_JOIN_REQ) + its accounting comment appended to packetdb.py
        "9c041193ba212927aeb19263436c5bcfbcb91271a453d3b427e04728317cb99e",
        # the guild invite slice: the 0x0169/0x016A/0x016B block appended
        # to packetdb.py after the 0x0167 registration
        "9e63c5fccd387a0bdbbbfe07646e1154fda663654361aec42ee3934876a05c82",
        "26291ffbe4ab0bf1c64adcbaf3be46c10f2e720d8bc6ff408c8052244ad8a240",
        # the guild-create slice: ZC_RESULT_MAKE_GUILD 0x0167 (3B) appended
        # (the live-verified charter reply; 0x0165 30B already in the baseline)
        "d257a7779bb4b60e2c1081a1892759efe0a6736a6e1b002f6020b12125e94bd8",
    )
    token = b", 0x00B6: 6"
    assert raw.count(token) == 1
    assert hashlib.sha256(raw.replace(token, b"", 1)).hexdigest() in (
        # the party slice: the 0x2C4 shadow override (6 -> 26, MAIN 20180704
        # CZ_PARTY_JOIN_REQ) + its accounting comment appended to packetdb.py
        "3ae219473ecb152f882ee12622d59e1ae17db9c8772a5c6f8061ab4dda86c94a",
        # the guild invite slice
        "14dac668fabe5ab6928ed5b98f5f0e793bb40e9f10ee5ba93918a98d252c4225",
        "2b0a38740ef0fcae523a586ea84860acc6e3ca46d46c76faf6b37ef21e4ab445",
        # the guild-create slice: ZC_RESULT_MAKE_GUILD 0x0167 (3B) appended
        # (the live-verified charter reply; 0x0165 30B already in the baseline)
        "fc6a3fa048b19e444d86abae4d183eec8ee95bd727eabd7c9f17fbdcd63f159c",
    )


def manifest_data() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(MANIFEST.read_text()))


def validate_npc_close(manifest: dict[str, Any]) -> None:
    """Test-only single named packet contract; no runtime or generic loader."""
    assert manifest["schema"] == "reviewed-static-protocol/v1"
    assert json.dumps(manifest["profile"], sort_keys=True) == json.dumps(
        {
            "role": "map",
            "packetver": 20180704,
            "client_family": "MAIN",
            "ruleset": "pre-re",
            "obfuscation": "ABSENT",
        },
        sort_keys=True,
    )
    assert len(manifest["packets"]) == 1
    row = manifest["packets"][0]
    expected = {
        "id": 182,
        "length": 6,
        "alignment": 1,
        "direction": "S->C",
        "name": "ZC_CLOSE_DIALOG",
        "cpp_record": "PACKET_ZC_CLOSE_DIALOG",
        "cpp_header": "HEADER_ZC_CLOSE_DIALOG",
        "declaration_scope": "map",
        "framing": "fixed",
        "byte_order": "little-endian",
        "fields": FIELDS,
    }
    assert json.dumps({key: row[key] for key in expected}, sort_keys=True) == json.dumps(
        expected, sort_keys=True
    )


def test_companion_manifest_contract() -> None:
    validate_npc_close(manifest_data())


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("id", True),
        ("id", 182.0),
        ("id", -1),
        ("id", 65536),
        ("id", "182"),
        ("length", 6.0),
        ("length", True),
        ("length", 7),
        ("alignment", 2),
        ("cpp_header", "HEADER_CZ_CLOSE_DIALOG"),
        ("direction", "C->S"),
    ],
)
def test_conflicting_companion_contract_rejected(key: str, value: Any) -> None:
    manifest = manifest_data()
    manifest["packets"][0][key] = value
    with pytest.raises(AssertionError):
        validate_npc_close(manifest)


def test_duplicate_companion_rows_rejected() -> None:
    manifest = manifest_data()
    manifest["packets"].append(manifest["packets"][0])
    with pytest.raises(AssertionError):
        validate_npc_close(manifest)


@pytest.mark.parametrize("key", ["packetver", "client_family", "ruleset", "obfuscation"])
def test_profile_drift_rejected(key: str) -> None:
    manifest = manifest_data()
    manifest["profile"][key] = "unreviewed"
    with pytest.raises(AssertionError):
        validate_npc_close(manifest)


@pytest.mark.parametrize("key", ["offset", "width", "cpp_type"])
def test_field_drift_rejected(key: str) -> None:
    manifest = manifest_data()
    manifest["packets"][0]["fields"][1][key] = "unreviewed"
    with pytest.raises(AssertionError):
        validate_npc_close(manifest)


def checked_digest(raw: bytes, expected: str) -> None:
    assert hashlib.sha256(raw).hexdigest() == expected


@pytest.fixture(scope="module")
def pinned_source() -> None:
    manifest = manifest_data()
    validate_npc_close(manifest)
    provenance = manifest["provenance"]
    original = json.loads((ROOT / "protocol/main-20180704-pre-re.json").read_text())
    assert provenance == original["provenance"]
    assert provenance["package"] == str(PACKAGE)
    assert provenance["revision"] == "e985006171d2eb320ee512a653f4c83aea3d81b6"
    for artifact, key in (
        ("profiles.json", "profiles_sha256"),
        ("configured-source.json", "configured_source_sha256"),
        ("qualified-clif.cpp", "qualified_clif_sha256"),
        ("map-cppflags.txt", "map_cppflags_sha256"),
        ("map-compile-recipe.txt", "map_compile_recipe_sha256"),
    ):
        checked_digest((EVIDENCE / artifact).read_bytes(), provenance[key])
    configured = json.loads((EVIDENCE / "configured-source.json").read_text())
    assert configured["revision"] == provenance["revision"]
    for relative, digest in configured["files"].items():
        if not relative.endswith("/Makefile"):
            checked_digest((SOURCE / relative).read_bytes(), digest)
    profile = json.loads((EVIDENCE / "profiles.json").read_text())["map"]
    assert profile == {
        "packetver": 20180704,
        "main": 20180704,
        "renewal": False,
        "re": False,
        "zero": False,
        "obfuscation": False,
        "pincode": True,
    }
    source = manifest["packets"][0]["source"]
    assert source["declaration"] == "src/map/packets.hpp"
    assert source["sender_artifact"] == "qualified-clif.cpp"
    assert source["sender_lines"] == [2519, 2526]
    assert source["sender_function"] == "clif_scriptclose"
    assert source["object"] == "packet"
    body = b"".join(
        (EVIDENCE / "qualified-clif.cpp").read_bytes().splitlines(keepends=True)[2518:2526]
    ).removesuffix(b"\n")
    assert body == (
        b"void clif_scriptclose( const map_session_data& sd, uint32 npcid ){\n"
        b"\tPACKET_ZC_CLOSE_DIALOG packet{};\n\n"
        b"\tpacket.packetType = HEADER_ZC_CLOSE_DIALOG;\n"
        b"\tpacket.npcId = npcid;\n\n"
        b"\tclif_send( &packet, sizeof( packet ), &sd, SELF );\n}"
    )
    checked_digest(body, source["sender_body_sha256"])
    for key in ("header_assignment", "npc_id_assignment", "send"):
        assert source[key].encode() in body
    checked_digest((SOURCE / source["declaration"]).read_bytes(), source["declaration_sha256"])
    assert (EVIDENCE / "map-cppflags.txt").read_text().strip() == CPPFLAGS


def test_pinned_source_profile_sender(pinned_source: None) -> None:
    assert pinned_source is None


def test_source_drift_rejected() -> None:
    source = manifest_data()["packets"][0]["source"]
    body = b"".join(
        (EVIDENCE / "qualified-clif.cpp").read_bytes().splitlines(keepends=True)[2518:2526]
    ).removesuffix(b"\n")
    with pytest.raises(AssertionError):
        checked_digest(body + b"\n", source["sender_body_sha256"])


@pytest.mark.parametrize("compiler_name", ["g++", "clang++"])
def test_fresh_full_unchanged_header_oracle(
    tmp_path: Path, compiler_name: str, pinned_source: None
) -> None:
    assert pinned_source is None
    compiler = shutil.which(compiler_name)
    assert compiler is not None
    cpp = tmp_path / "npc-close.cpp"
    cpp.write_text(
        "#include <config/core.hpp>\n#include <map/packets.hpp>\n"
        "#include <cstdio>\n#include <cstddef>\n"
        "static_assert(PACKETVER == 20180704 && PACKETVER_MAIN_NUM == 20180704);\n"
        "#if !defined(PRERE) || defined(RENEWAL) || defined(PACKETVER_RE) || "
        "defined(PACKETVER_ZERO) || defined(PACKET_OBFUSCATION) || "
        "defined(PACKET_OBFUSCATION_WARN)\n#error Unreviewed_profile\n#endif\n"
        "static_assert(HEADER_ZC_CLOSE_DIALOG == 182);\n"
        'int main(){printf("%d %zu %zu %zu %zu %zu %zu\\n", '
        "HEADER_ZC_CLOSE_DIALOG,sizeof(PACKET_ZC_CLOSE_DIALOG),alignof(PACKET_ZC_CLOSE_DIALOG),"
        "offsetof(PACKET_ZC_CLOSE_DIALOG,packetType),offsetof(PACKET_ZC_CLOSE_DIALOG,npcId),"
        "sizeof(PACKET_ZC_CLOSE_DIALOG::packetType),sizeof(PACKET_ZC_CLOSE_DIALOG::npcId));}\n"
    )
    includes = [
        SOURCE / path
        for path in (
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
    binary = tmp_path / "npc-close"
    command = [
        compiler,
        *shlex.split(CPPFLAGS),
        *["-I" + str(p) for p in includes],
        str(cpp),
        "-o",
        str(binary),
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=30)
    (tmp_path / "compile.stdout").write_text(result.stdout)
    (tmp_path / "compile.stderr").write_text(result.stderr)
    (tmp_path / "command.json").write_text(json.dumps(command))
    assert result.returncode == 0, result.stderr
    observed = subprocess.run([str(binary)], check=True, capture_output=True, text=True, timeout=5)
    (tmp_path / "oracle.stdout").write_text(observed.stdout)
    assert observed.stdout == "182 6 1 0 2 2 4\n"
