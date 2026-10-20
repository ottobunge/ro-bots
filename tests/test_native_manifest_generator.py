"""Offline, real-compiler tracer bullets for the pinned native catalogue."""

import hashlib
import importlib.util
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/generate_native_packet_manifest.py"
SOURCE = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source")
EVIDENCE = Path(
    "/nix/store/plsvbs632sakjv9cl1pbzvjnnqs8y06n-rathena-playable-20180704-e985006171d2"
    "/share/rathena-playable"
)
SCRATCH = Path("/home/otto/.hermes/cache/scratch/native-manifest-tests")


def generate(label: str) -> dict[str, Any]:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    output = SCRATCH / f"{label}.json"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--source-root",
            str(SOURCE),
            "--profile-evidence",
            str(EVIDENCE),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return cast(dict[str, Any], json.loads(output.read_text()))


def test_emotion_has_compiled_framing_and_sender_provenance() -> None:
    catalogue = generate("emotion")
    emotion = next(row for row in catalogue["packets"] if row["name"] == "ZC_EMOTION")
    assert catalogue["schema_version"] == 1
    assert emotion["id"] == 0x00C0
    assert emotion["direction"] == "server_to_client"
    assert emotion["framing"] == {"kind": "fixed", "length": 7}
    assert emotion["evidence"]["definition_file"] == "src/map/packets.hpp"
    assert emotion["evidence"]["definition_symbol"] == "PACKET_ZC_EMOTION"
    assert emotion["evidence"]["header_symbol"] == "HEADER_ZC_EMOTION"
    assert emotion["evidence"]["sender_file"] == "src/map/clif.cpp"
    assert "clif_emotion" in emotion["evidence"]["sender_symbols"]
    assert "compiler" in emotion["evidence"]["method"]


def test_chat_flexible_prefix_is_total_length_driven_not_fixed() -> None:
    catalogue = generate("chat")
    chat = next((row for row in catalogue["packets"] if row["name"] == "ZC_NOTIFY_CHAT"), None)
    assert chat is not None, "active flexible chat sender absent"
    assert chat["framing"] == {
        "kind": "variable",
        "length_offset": 2,
        "length_size": 2,
        "minimum_length": 8,
    }
    assert chat["evidence"]["length_field"] == "PacketLength"
    assert "clif_GlobalMessage" in chat["evidence"]["sender_symbols"]


def test_every_cpp_active_zc_header_and_struct_is_accounted_for() -> None:
    catalogue = generate("inventory")
    fixture = SCRATCH / "complete-header.cpp"
    fixture.write_text(
        "#include <config/core.hpp>\n#include <map/packets.hpp>\n#include <common/packets.hpp>\n"
    )

    flags = shlex.split((EVIDENCE / "map-cppflags.txt").read_text())
    includes = [
        SOURCE / "src",
        SOURCE / "src/map",
        SOURCE / "src/common",
        SOURCE / "3rdparty/rapidyaml/src",
        SOURCE / "3rdparty/rapidyaml/ext/c4core/src",
        SOURCE / "3rdparty/libconfig",
        Path(
            "/nix/store/1w8g6rvhljfk44hx50qz4sc47sm1f28v-mariadb-connector-c-3.3.5-dev/include/mysql"
        ),
    ]
    active = subprocess.check_output(
        ["g++", *flags, *(f"-I{p}" for p in includes), "-E", str(fixture)], text=True
    )
    (SCRATCH / "complete-header.i").write_text(active)
    headers = set(re.findall(r"\bHEADER_(ZC_\w+)\b", active))
    structs = set(re.findall(r"\bstruct\s+PACKET_(ZC_\w+)\s*\{", active))
    accounted = {row["name"] for row in catalogue["packets"] + catalogue["unresolved"]}
    assert headers | structs <= accounted, sorted((headers | structs) - accounted)
    assert len(headers) > 100
    assert catalogue["inventory"]["active_zc_headers"] == sorted(headers)
    assert catalogue["inventory"]["active_zc_structs"] == sorted(structs)
    assert all(row["reason"] and row["source"] for row in catalogue["unresolved"])
    party = next(row for row in catalogue["packets"] if row["name"] == "ZC_NOTIFY_CHAT_PARTY")
    assert party["framing"]["kind"] == "variable"


def load_generator() -> ModuleType:

    spec = importlib.util.spec_from_file_location("native_manifest_generator", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_mixed_sizeof_and_length_driven_send_never_becomes_fixed() -> None:
    module = load_generator()
    definition = module.Definition(
        "PACKET_ZC_TEST", "short PacketType; char data[64];", "fixture", 1
    )
    binding = module.Sender(
        "clif_test",
        "PACKET_ZC_TEST",
        "HEADER_ZC_TEST",
        "p",
        "clif_send(&p, sizeof(p), bl, AREA); clif_send(&p, count, bl, SELF);",
        False,
    )
    assert module.framing(definition, [binding])[0] == "unresolved"


def test_complete_compiler_dependency_closure_has_reproducible_hashes() -> None:
    catalogue = generate("closure")
    dependencies = catalogue.get("build_evidence", {}).get("dependencies", [])
    assert dependencies, "complete compiler include closure was not recorded"
    paths = {row["path"] for row in dependencies}
    assert str(SOURCE / "src/map/map.hpp") in paths
    assert str(SOURCE / "src/map/packets_struct.hpp") in paths
    assert str(SOURCE / "src/map/clif.cpp") in paths

    for row in dependencies:
        assert row["sha256"] == hashlib.sha256(Path(row["path"]).read_bytes()).hexdigest()
    build = catalogue["build_evidence"]
    assert build["compiler_path"].startswith("/nix/store/")
    assert build["compiler_version"]
    assert (
        build["cppflags_sha256"]
        == hashlib.sha256((EVIDENCE / "map-cppflags.txt").read_bytes()).hexdigest()
    )
    assert (
        build["compile_recipe_sha256"]
        == hashlib.sha256((EVIDENCE / "map-compile-recipe.txt").read_bytes()).hexdigest()
    )
    assert (
        catalogue["profile"]["source_sha256_scope"]
        == "compiler-selected public source/include closure"
    )


def test_conflicting_packet_ids_and_invalid_variable_prefixes_are_rejected() -> None:

    module = load_generator()
    fixed = {
        "id": 1,
        "name": "ZC_ONE",
        "direction": "server_to_client",
        "framing": {"kind": "fixed", "length": 7},
    }
    for change in (
        {"name": "ZC_TWO"},
        {"direction": "client_to_server"},
        {"framing": {"kind": "fixed", "length": 8}},
        {
            "framing": {
                "kind": "variable",
                "length_offset": 2,
                "length_size": 2,
                "minimum_length": 4,
            }
        },
    ):
        with pytest.raises(ValueError, match=r"conflicting|uint16|prefix"):
            module.validate_packets([fixed, {**fixed, **change}], [])
    for framing in (
        {"kind": "variable", "length_offset": 1, "length_size": 2, "minimum_length": 4},
        {"kind": "variable", "length_offset": 2, "length_size": 4, "minimum_length": 8},
        {"kind": "variable", "length_offset": 2, "length_size": 2, "minimum_length": 3},
    ):
        with pytest.raises(ValueError, match=r"conflicting|uint16|prefix"):
            module.validate_packets([{**fixed, "framing": framing}], [])
    for packet_id in (-1, 65536):
        with pytest.raises(ValueError, match=r"conflicting|uint16|prefix"):
            module.validate_packets([{**fixed, "id": packet_id}], [])
        with pytest.raises(ValueError, match=r"conflicting|uint16|prefix"):
            module.validate_packets([], [{"id": packet_id}])
    module.validate_packets([fixed, dict(fixed)], [{"id": None}])


def test_fixed_buffer_computed_length_stays_unresolved() -> None:
    module = load_generator()
    definition = module.Definition(
        "PACKET_ZC_TEST", "short PacketType; char data[64];", "fixture", 1
    )
    binding = module.Sender(
        "clif_test",
        "PACKET_ZC_TEST",
        "HEADER_ZC_TEST",
        "p",
        "clif_send(&p, count, bl, SELF);",
        False,
    )
    assert module.framing(definition, [binding])[0] == "unresolved"


def test_cli_is_byte_identical_across_real_compiler_runs() -> None:
    generate("deterministic-one")
    generate("deterministic-two")
    assert (SCRATCH / "deterministic-one.json").read_bytes() == (
        SCRATCH / "deterministic-two.json"
    ).read_bytes()


def test_real_compiler_failure_preserves_existing_output(
    monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    module = load_generator()
    output = SCRATCH / "preserved-output.json"
    output.write_bytes(b"preserve old catalogue\n")
    # Interfere with the owned public translation unit, never the authorized flags.
    monkeypatch.setattr(module, "PREAMBLE", module.PREAMBLE + "#error controlled failure\n")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--source-root",
            str(SOURCE),
            "--profile-evidence",
            str(EVIDENCE),
            "--output",
            str(output),
        ],
    )
    with pytest.raises(subprocess.CalledProcessError) as failure:
        module.main()
    assert failure.value.returncode != 0
    assert "controlled failure" in capfd.readouterr().err
    assert output.read_bytes() == b"preserve old catalogue\n"


@pytest.mark.parametrize("label", ["profile_guard_bypass", "altered_abi", "altered-flags"])
def test_untrusted_options_are_rejected_before_compilation(
    label: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = load_generator()
    directory = tmp_path / label
    directory.mkdir()
    for name in ("package.json", "map-cppflags.txt", "map-compile-recipe.txt"):
        (directory / name).write_bytes((EVIDENCE / name).read_bytes())
    response = directory / "options.rsp"
    response.write_text(
        "-DCONFIG_PACKETS_HPP -DPACKETVER_MAIN_NUM=20180704 -DPACKETVER_RE_NUM=20180704"
        if label == "profile_guard_bypass"
        else "-fpack-struct=1"
    )
    with (directory / "map-cppflags.txt").open("a") as stream:
        stream.write(f" @{response}")
    calls: list[object] = []

    def forbidden(*args: object, **kwargs: object) -> str:
        calls.append(args)
        message = "compiler invoked before rejection"
        raise AssertionError(message)

    monkeypatch.setattr(module.subprocess, "check_output", forbidden)
    with pytest.raises(ValueError, match=r"trusted|reviewed"):
        module.generate(SOURCE, directory)
    assert calls == []


def test_untrusted_compiler_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_generator()
    monkeypatch.setattr(module.shutil, "which", lambda _name: "/bin/false")
    with pytest.raises(ValueError, match="pinned"):
        module.compile_profile(SOURCE, EVIDENCE)


@pytest.mark.parametrize(
    "body",
    [
        (
            "PACKET_ZC_TEST p; p.packetType = HEADER_ZC_TEST; p.packetType = HEADER_ZC_OTHER; "
            "clif_send(&p, sizeof(p), bl, AREA);"
        ),
        (
            "PACKET_ZC_TEST p; p.packetType = HEADER_ZC_TEST; { PACKET_ZC_OTHER p; "
            "clif_send(&p, sizeof(p), bl, AREA); }"
        ),
        (
            "PACKET_ZC_TEST p; p.packetType = HEADER_ZC_TEST; { char p[32]; "
            "clif_send(&p, sizeof(p), bl, AREA); }"
        ),
        (
            "PACKET_ZC_TEST p; if (flag) p.packetType = HEADER_ZC_TEST; "
            "clif_send(&p, sizeof(p), bl, AREA);"
        ),
        (
            "PACKET_ZC_TEST p; p.packetType = HEADER_ZC_TEST; p.packetType += 1; "
            "clif_send(&p, sizeof(p), bl, AREA);"
        ),
        (
            "PACKET_ZC_TEST p; p.packetType = HEADER_ZC_TEST; { char q, p[32]; "
            "clif_send(&p, sizeof(p), bl, AREA); }"
        ),
        "PACKET_ZC_TEST p; clif_send(&p, sizeof(p), bl, AREA); p.packetType = HEADER_ZC_TEST;",
        (
            "PACKET_ZC_TEST p; p.packetType = HEADER_ZC_TEST; p = other; "
            "clif_send(&p, sizeof(p), bl, AREA);"
        ),
        (
            "PACKET_ZC_TEST p; if (flag) { p.packetType = HEADER_ZC_TEST; } "
            "clif_send(&p, sizeof(p), bl, AREA);"
        ),
    ],
)
def test_ambiguous_sender_association_is_unresolved(body: str) -> None:
    module = load_generator()
    definition = module.Definition(
        "PACKET_ZC_TEST", "short packetType; char data[8];", "fixture", 1
    )
    bindings = module.senders("void clif_test() {" + body + "}")
    matches = [b for b in bindings if b.header == "HEADER_ZC_TEST"]
    assert not matches or module.framing(definition, matches)[0] == "unresolved"


def test_outer_unique_sender_supports_if_else_sends() -> None:
    module = load_generator()
    body = """void clif_test() {
        PACKET_ZC_TEST p; p.packetType = HEADER_ZC_TEST;
        if (flag) { clif_send(&p, sizeof(p), bl, AREA); }
        else { clif_send(&p, sizeof(p), bl, SELF); }
    }"""
    definition = module.Definition(
        "PACKET_ZC_TEST", "short packetType; char data[8];", "fixture", 1
    )
    assert module.framing(definition, module.senders(body))[0] == "fixed"


@pytest.mark.parametrize("field", ["length_offset", "length_size", "minimum_length"])
@pytest.mark.parametrize("value", [2.0, True, False, "2"])
def test_variable_metadata_requires_exact_integers(field: str, value: object) -> None:
    module = load_generator()
    frame: dict[str, Any] = {
        "kind": "variable",
        "length_offset": 2,
        "length_size": 2,
        "minimum_length": 4,
    }
    frame[field] = value
    with pytest.raises(ValueError, match=r"uint16|prefix"):
        module.validate_frame({"id": 1, "framing": frame})


def compiled_sender_kind(label: str, body: str, expected: str, field: str = "PacketType") -> str:
    module = load_generator()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    source = SCRATCH / f"cycle2-{label}.cpp"
    binary = source.with_suffix("")
    source.write_text(
        "#include <cstdio>\n#include <cstdint>\n"
        f"struct PACKET_ZC_ONE {{ uint16_t {field}; char data[64]; }};\n"
        f"struct PACKET_ZC_TWO {{ uint16_t {field}; char data[2]; }};\n"
        "constexpr int HEADER_ZC_ONE=1; int bl=0, SELF=0;\n"
        "void clif_send(const void* p, unsigned long n, int, int) {\n"
        'std::printf("%u %lu\\n", *static_cast<const uint16_t*>(p), n); }\n'
        "void clif_test() {" + body + "}\nint main() { clif_test(); }\n"
    )
    subprocess.run([module.pinned_compiler(), str(source), "-o", str(binary)], check=True)
    actual = subprocess.check_output([str(binary)], text=True)
    binary.with_suffix(".stdout").write_text(actual)
    assert actual == expected
    definition = module.Definition("PACKET_ZC_ONE", f"short {field}; char data[64];", "fixture", 1)
    return cast(str, module.framing(definition, module.senders(source.read_text()))[0])


def test_compiled_lambda_parameter_shadow_is_unresolved() -> None:
    body = (
        "PACKET_ZC_ONE p; p.PacketType=HEADER_ZC_ONE; "
        "auto helper=[](PACKET_ZC_TWO p){ clif_send(&p,sizeof(p),bl,SELF); }; "
        "PACKET_ZC_TWO other{}; other.PacketType=2; helper(other);"
    )
    assert compiled_sender_kind("lambda", body, "2 4\n") == "unresolved"


@pytest.mark.parametrize("field", ["packetType", "PacketType"])
@pytest.mark.parametrize(
    ("mutation", "expected"),
    [("++p.FIELD", "2 66\n"), ("--p.FIELD", "0 66\n"), ("++ ((p).FIELD)", "2 66\n")],
)
def test_compiled_prefix_header_mutation_is_unresolved(
    field: str, mutation: str, expected: str
) -> None:
    body = (
        f"PACKET_ZC_ONE p; p.{field}=HEADER_ZC_ONE; "
        + mutation.replace("FIELD", field)
        + "; clif_send(&p,sizeof(p),bl,SELF);"
    )
    label = field + ("increment" if expected.startswith("2") else "decrement")
    assert compiled_sender_kind(label, body, expected, field) == "unresolved"


def test_inprocess_generation_matches_cli_and_parses_make_escapes() -> None:
    module = load_generator()
    catalogue = module.generate(SOURCE, EVIDENCE)
    assert catalogue == generate("inprocess")
    dependency = SCRATCH / "escaped.d"
    dependency.write_text("target: /source/header\\ name.hpp \\\n /source/second.hpp\n")
    assert module.dependency_paths(dependency) == {
        Path("/source/header name.hpp"),
        Path("/source/second.hpp"),
    }
