"""Compiler-backed NPC layouts and real strict incremental stream framing."""

import hashlib
import json
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.test_native_npc_close_framing import packet_module
from tests.test_native_npc_guidance import dialog
from tests.test_native_protocol_manifest import (
    CPPFLAGS,
    SOURCE,
)
from tests.test_native_protocol_manifest import (
    test_immutable_source_profile_sender_binding as bind_source,
)


def test_source_bound_unchanged_npc_header_oracle(tmp_path):
    bind_source()
    includes = [
        SOURCE / p
        for p in (
            "src",
            "src/common",
            "3rdparty/libconfig",
            "3rdparty/rapidyaml/src",
            "3rdparty/rapidyaml/ext/c4core/src",
        )
    ]
    includes += [
        Path("/nix/store/1w8g6rvhljfk44hx50qz4sc47sm1f28v-mariadb-connector-c-3.3.5-dev/include"),
        Path(
            "/nix/store/1w8g6rvhljfk44hx50qz4sc47sm1f28v-mariadb-connector-c-3.3.5-dev/include/mysql"
        ),
    ]
    records = [
        ("ZC_SAY_DIALOG", "NpcID", 0xB4, 8, 4),
        ("ZC_WAIT_DIALOG", "NpcID", 0xB5, 6, 2),
        ("ZC_MENU_LIST", "npcId", 0xB7, 8, 4),
        ("ZC_CLOSE_DIALOG", "npcId", 0xB6, 6, 2),
        ("ZC_SELECT_DEALTYPE", "npcId", 0xC4, 6, 2),
        ("ZC_OPEN_EDITDLG", "npcId", 0x142, 6, 2),
        ("ZC_OPEN_EDITDLGSTR", "npcId", 0x1D4, 6, 2),
        ("CZ_CONTACTNPC", "AID", 0x90, 7, 2),
        ("CZ_CLOSE_DIALOG", "GID", 0x146, 6, 2),
    ]
    cpp = tmp_path / "npc.cpp"
    prefix = (
        "#include <config/core.hpp>\n#include <map/packets.hpp>\n"
        "#include <map/packets_struct.hpp>\n#include <cstdio>\n#include <cstddef>\n"
        "static_assert(PACKETVER_MAIN_NUM==20180704);\n"
        "#if !defined(PRERE) || defined(RENEWAL) || defined(PACKET_OBFUSCATION)\n"
        "#error wrong_profile\n#endif\n"
    )
    body = "".join(
        f'printf("%d %zu %zu %zu\\n", HEADER_{n}, sizeof(PACKET_{n}), '
        f"alignof(PACKET_{n}), offsetof(PACKET_{n},{f}));"
        for n, f, _, _, _ in records
    )
    guards = (
        "static_assert(offsetof(PACKET_ZC_SAY_DIALOG, PacketLength)==2);\n"
        "static_assert(offsetof(PACKET_ZC_SAY_DIALOG, message)==8);\n"
        "static_assert(sizeof(PACKET_ZC_SAY_DIALOG::PacketType)==2);\n"
        "static_assert(sizeof(PACKET_ZC_SAY_DIALOG::NpcID)==4);\n"
        "static_assert(offsetof(PACKET_ZC_MENU_LIST, packetLength)==2);\n"
        "static_assert(offsetof(PACKET_ZC_MENU_LIST, menu)==8);\n"
        "static_assert(sizeof(PACKET_ZC_MENU_LIST::packetLength)==2);\n"
        "static_assert(sizeof(PACKET_ZC_MENU_LIST::npcId)==4);\n"
        "static_assert(offsetof(PACKET_CZ_CONTACTNPC, type)==6);\n"
        "static_assert(sizeof(PACKET_CZ_CONTACTNPC::type)==1);\n"
        "static_assert(sizeof(PACKET_ZC_ACK_REQNAMEALL_NPC)==58);\n"
        "static_assert(offsetof(PACKET_ZC_ACK_REQNAMEALL_NPC,name)==10);\n"
    )
    cpp.write_text(prefix + guards + "int main(){" + body + "}")
    compiler = shutil.which("g++")
    assert compiler is not None
    command = [
        compiler,
        *shlex.split(CPPFLAGS),
        *["-I" + str(p) for p in includes],
        str(cpp),
        "-o",
        str(tmp_path / "npc"),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    observed = subprocess.run(
        [str(tmp_path / "npc")], capture_output=True, text=True, timeout=5, check=True
    )
    assert observed.stdout == "".join(f"{pid} {size} 1 {off}\n" for _, _, pid, size, off in records)
    (tmp_path / "oracle.json").write_text(
        json.dumps({"command": command, "stdout": observed.stdout})
    )


def test_npc_manifest_source_and_fixed_variable_contract():
    bind_source()
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "protocol/main-20180704-pre-re-npc-dialogue.json").read_text())
    original = json.loads((root / "protocol/main-20180704-pre-re.json").read_text())
    assert manifest["provenance"] == original["provenance"]
    assert manifest["profile"] == original["profile"]
    assert len(manifest["packets"]) == 11
    rows = {p["id"]: p for p in manifest["packets"]}
    assert rows[0xB4]["length_offset"] == rows[0xB7]["length_offset"] == 2
    assert rows[0xB4]["prefix_size"] == rows[0xB7]["prefix_size"] == 8
    assert rows[0xB5]["length"] == rows[0xB6]["length"] == 6
    for row in rows.values():
        source = row["source"]
        if "declaration" in source:
            assert (
                hashlib.sha256((SOURCE / source["declaration"]).read_bytes()).hexdigest()
                == source["declaration_sha256"]
            )
            start, end = source["clif_lines"]
            body = b"".join(
                (SOURCE / "src/map/clif.cpp")
                .read_bytes()
                .splitlines(keepends=True)[start - 1 : end]
            )
            assert hashlib.sha256(body).hexdigest() == source["clif_body_sha256"]
        else:
            assert (
                hashlib.sha256((SOURCE / source["registration"]).read_bytes()).hexdigest()
                == source["registration_sha256"]
            )


def test_dialogue_frames_individual_coalesced_and_bytewise():
    packets = [
        dialog(0xB4, "Guide"),
        dialog(0xB5),
        dialog(0xB7, "A::C"),
        dialog(0xB6),
        dialog(0xC4),
        dialog(0x142),
        dialog(0x1D4),
    ]
    module = packet_module()
    expected = [(int.from_bytes(p[:2], "little"), p) for p in packets]
    for p, row in zip(packets, expected, strict=True):
        assert module.parse_stream(p) == ([row], b"")
    stream = b"".join(packets)
    assert module.parse_stream(stream) == (expected, b"")
    pending = b""
    frames = []
    for byte in stream:
        ready, pending = module.parse_stream(pending + bytes([byte]))
        frames.extend(ready)
    assert frames == expected
    assert not pending


def test_existing_890_registrations_preserved_and_unknown_stays_strict():
    module = packet_module()
    root = Path(__file__).resolve().parents[1]
    baseline = json.loads(
        (root / "run/reviews/native-manifest-migration-baseline.json").read_text()
    )["current_final_PACKET_DB"]
    old = {int(key, 16): value for key, value in baseline.items()} | {0xB6: 6, 0xC0: 7}
    assert len(old) == 890  # the dialogue-era table; 0x00BC arrives later
    assert all(module.PACKET_DB[key] == value for key, value in old.items())
    assert module.PACKET_DB[0x01B3] == 67
    assert set(module.PACKET_DB) - old.keys() == {
        0xB4,
        0xB5,
        0xB7,
        0xC4,
        0x142,
        0x1D4,
        0x01B3,
        0x099D,
        0x00BC,
        0x00BE,
        0x00C7,
        0x0167,  # ZC_RESULT_MAKE_GUILD 3B, the live-verified charter reply
    }
    assert len(module.PACKET_DB) == 902
    with pytest.raises(ValueError, match="unknown packet 0xfafa"):
        module.parse_stream(dialog(0xB4, "guide") + b"\xfa\xfa")
