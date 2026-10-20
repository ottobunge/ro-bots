"""Pinned manual specification checks, not a generic C++ sender proof."""

import hashlib
import json
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "protocol/main-20180704-pre-re.json"


def test_pinned_manifest_exists() -> None:
    assert MANIFEST.is_file()
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["schema"] == "reviewed-static-protocol/v1"
    assert len(manifest["packets"]) == 1
    validate_spec(manifest)


PACKAGE = Path(
    "/nix/store/0w1nfsmj8gaipcidhgx2nkg4axqxcbbr-rathena-playable-callback-qualified-"
    "20180704-e985006171d2-callback-qualified"
)
EVIDENCE = PACKAGE / "share/rathena-playable-callback-qualified"
SOURCE = ROOT / "run/public-source/callback-qualified-e985006171d2"
PROFILE = {
    "role": "map",
    "packetver": 20180704,
    "client_family": "MAIN",
    "ruleset": "pre-re",
    "obfuscation": "ABSENT",
}
FIELDS = [
    {"name": "packetType", "wire_type": "uint16", "cpp_type": "int16", "offset": 0, "width": 2},
    {"name": "GID", "wire_type": "uint32", "cpp_type": "int32", "offset": 2, "width": 4},
    {"name": "type", "wire_type": "uint8", "cpp_type": "uint8", "offset": 6, "width": 1},
]
CPPFLAGS = (
    "-std=c++17 -DHAS_TLS -fno-strict-aliasing -DHAVE_GETADDRINFO -DHAVE_SETRLIMIT "
    "-DHAVE_STRNLEN -DPACKETVER=20180704 -DPRERE -DHAVE_MONOTONIC_CLOCK "
    "-DHAS_TLS -fno-strict-aliasing -DHAVE_GETADDRINFO -DHAVE_SETRLIMIT "
    "-DHAVE_STRNLEN -DPACKETVER=20180704 -DPRERE -DHAVE_MONOTONIC_CLOCK"
)


def validate_spec(manifest: dict[str, Any]) -> None:
    """Test-only narrow spec guard; not a runtime manifest application API."""
    assert json.dumps(manifest["profile"], sort_keys=True) == json.dumps(PROFILE, sort_keys=True)
    assert len(manifest["packets"]) == 1
    row = manifest["packets"][0]
    assert type(row["id"]) is int
    assert 0 <= row["id"] <= 65535
    assert row["id"] == 192
    assert type(row["length"]) is int
    assert row["length"] == 7
    assert type(row["alignment"]) is int
    assert row["alignment"] == 1
    assert row["direction"] == "S->C"
    assert row["framing"] == "fixed"
    assert row["declaration_scope"] == "map"
    assert row["cpp_record"] == "PACKET_ZC_EMOTION"
    assert row["cpp_header"] == "HEADER_ZC_EMOTION"
    assert json.dumps(row["fields"], sort_keys=True) == json.dumps(FIELDS, sort_keys=True)


@pytest.mark.parametrize("invalid", [True, 192.0, -1, 65536, "192"])
def test_manifest_rejects_non_json_uint16_id(invalid: Any) -> None:
    manifest = json.loads(MANIFEST.read_text())
    manifest["packets"][0]["id"] = invalid
    with pytest.raises(AssertionError):
        validate_spec(manifest)


@pytest.mark.parametrize("field", ["packetver", "obfuscation", "client_family", "ruleset"])
def test_manifest_profile_changes_fail_closed(field: str) -> None:
    manifest = json.loads(MANIFEST.read_text())
    manifest["profile"][field] = "unreviewed"
    with pytest.raises(AssertionError):
        validate_spec(manifest)


@pytest.mark.parametrize("invalid", [True, 2.0, -1, 65536])
def test_field_layout_changes_fail_closed(invalid: Any) -> None:
    manifest = json.loads(MANIFEST.read_text())
    manifest["packets"][0]["fields"][0]["width"] = invalid
    with pytest.raises(AssertionError):
        validate_spec(manifest)


@pytest.mark.parametrize(
    ("key", "invalid"),
    [
        ("length", True),
        ("length", 7.0),
        ("direction", "C->S"),
        ("cpp_header", "HEADER_ZC_STOPMOVE"),
        ("declaration_scope", "common"),
    ],
)
def test_conflicting_spec_changes_fail_closed(key: str, invalid: Any) -> None:
    manifest = json.loads(MANIFEST.read_text())
    manifest["packets"][0][key] = invalid
    with pytest.raises(AssertionError):
        validate_spec(manifest)


def test_duplicate_rows_fail_closed() -> None:
    manifest = json.loads(MANIFEST.read_text())
    manifest["packets"].append(manifest["packets"][0])
    with pytest.raises(AssertionError):
        validate_spec(manifest)


def checked_digest(raw: bytes, expected: str) -> None:
    assert hashlib.sha256(raw).hexdigest() == expected


def test_source_drift_fails_closed() -> None:
    manifest = json.loads(MANIFEST.read_text())
    expected = manifest["provenance"]["qualified_clif_sha256"]
    with pytest.raises(AssertionError):
        checked_digest((EVIDENCE / "qualified-clif.cpp").read_bytes() + b"\n", expected)


def test_immutable_source_profile_sender_binding() -> None:
    manifest = json.loads(MANIFEST.read_text())
    provenance = manifest["provenance"]
    for artifact, key in (
        ("profiles.json", "profiles_sha256"),
        ("configured-source.json", "configured_source_sha256"),
        ("qualified-clif.cpp", "qualified_clif_sha256"),
        ("map-cppflags.txt", "map_cppflags_sha256"),
        ("map-compile-recipe.txt", "map_compile_recipe_sha256"),
    ):
        checked_digest((EVIDENCE / artifact).read_bytes(), provenance[key])
    assert provenance["package"] == str(PACKAGE)
    configured = json.loads((EVIDENCE / "configured-source.json").read_text())
    assert configured["revision"] == provenance["revision"]
    for relative, digest in configured["files"].items():
        if not relative.endswith("/Makefile"):
            checked_digest((SOURCE / relative).read_bytes(), digest)
    profiles = json.loads((EVIDENCE / "profiles.json").read_text())
    assert json.dumps(profiles["map"], sort_keys=True) == json.dumps(
        {
            "packetver": 20180704,
            "main": 20180704,
            "renewal": False,
            "re": False,
            "zero": False,
            "obfuscation": False,
            "pincode": True,
        },
        sort_keys=True,
    )
    source = manifest["packets"][0]["source"]
    body = b"".join(
        (EVIDENCE / "qualified-clif.cpp").read_bytes().splitlines(keepends=True)[9411:9420]
    )
    checked_digest(body.removesuffix(b"\n"), source["sender_body_sha256"])
    for key in ("header_assignment", "gid_assignment", "type_assignment", "send"):
        assert source[key].encode() in body
    assert b"PACKET_ZC_EMOTION p{};" in body
    assert b"void clif_emotion( const block_list& bl, emotion_type type ){" in body
    checked_digest((SOURCE / source["declaration"]).read_bytes(), source["declaration_sha256"])
    assert (EVIDENCE / "map-cppflags.txt").read_text().strip() == CPPFLAGS


@pytest.mark.parametrize("compiler_name", ["g++", "clang++"])
def test_fresh_unchanged_full_header_oracle(tmp_path: Path, compiler_name: str) -> None:
    test_immutable_source_profile_sender_binding()
    compiler = shutil.which(compiler_name)
    assert compiler is not None
    cpp = tmp_path / "emotion.cpp"
    cpp.write_text(
        "#include <config/core.hpp>\n#include <map/packets.hpp>\n"
        "#include <cstdio>\n#include <cstddef>\n"
        "static_assert(PACKETVER == 20180704 && PACKETVER_MAIN_NUM == 20180704);\n"
        "#if !defined(PRERE) || defined(RENEWAL) || defined(PACKETVER_RE) || "
        "defined(PACKETVER_ZERO) || defined(PACKET_OBFUSCATION) || "
        "defined(PACKET_OBFUSCATION_WARN)\n#error Unreviewed_profile\n#endif\n"
        "static_assert(HEADER_ZC_EMOTION == 192);\n"
        'int main(){printf("%d %zu %zu %zu %zu %zu %zu %zu %zu\\n", '
        "HEADER_ZC_EMOTION,sizeof(PACKET_ZC_EMOTION),alignof(PACKET_ZC_EMOTION),"
        "offsetof(PACKET_ZC_EMOTION,packetType),offsetof(PACKET_ZC_EMOTION,GID),"
        "offsetof(PACKET_ZC_EMOTION,type),sizeof(PACKET_ZC_EMOTION::packetType),"
        "sizeof(PACKET_ZC_EMOTION::GID),sizeof(PACKET_ZC_EMOTION::type));}\n"
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
    binary = tmp_path / "emotion"
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
    assert observed.stdout == "192 7 1 0 2 6 2 4 1\n"
