"""Read-only qualified compiler catalogue. No sender or framing admission."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

PACKAGE = Path(
    "/nix/store/0w1nfsmj8gaipcidhgx2nkg4axqxcbbr-"
    "rathena-playable-callback-qualified-20180704-e985006171d2-callback-qualified"
)
META = PACKAGE / "share/rathena-playable-callback-qualified"
SOURCE = Path("/home/otto/.hermes/cache/scratch/callback-package-hut2_cuz/configured-variant")
CLOSURE = "1f2d601dc86d572af78bae036f444fbbd469539457569e4f951438b30e74236a"
NAR = "sha256-hIVo2RvlabG8Jw362W7PxdXkQx2CDYihvHKwhZjP0Es="
COMPILERS = {
    "gcc": "/nix/store/j1938gsbvbhkyz4kbmvjk56r479mkw3s-gcc-wrapper-16.2.0/bin/g++",
    "clang": "/nix/store/2msw5nclhpsm80z65dqmjiv8kkras989-clang-wrapper-21.1.8/bin/clang++",
}
PINS = {
    "map-cppflags.txt": "7986f2fdeb11e55ee707ac27eb4701a64b90361ce1636bb728025fb92a99291d",
    "map-compile-recipe.txt": "8488711230e38fb3a48a9d19dca18b50b3a93780fd9287775768723af9358878",
    "profiles.json": "ee2af351afee975ad4145d0e38412dfac0779cd123435f318f8c876349bc0148",
    "configured-source.json": "1fd585266bbcf2268b2cec9e901100fad68b904a8b2a8c049c5869c56af43e12",
}
HEADERS = [
    "src/config/core.hpp",
    "src/common/packets.hpp",
    "src/map/packets.hpp",
    "src/map/packets_struct.hpp",
]
UNITS = {
    "map": "#include <config/core.hpp>\n#include <map/packets.hpp>\n",
    "common": "#include <config/core.hpp>\n#include <common/packets.hpp>\n",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_authority() -> dict[str, Any]:
    for name, digest in PINS.items():
        if sha(META / name) != digest:
            msg = f"unapproved metadata: {name}"
            raise ValueError(msg)
    recorded = json.loads((META / "configured-source.json").read_text())["files"]
    generated = {name for name in recorded if name.endswith("/Makefile")}
    if len(recorded) != 3216 or len(generated) != 10:
        msg = "configured inventory boundary drift"
        raise ValueError(msg)
    projection = {name: digest for name, digest in recorded.items() if name not in generated}
    actual: dict[str, str] = {}
    for area in ("src", "3rdparty"):
        for path in sorted((SOURCE / area).rglob("*")):
            if path.is_symlink():
                msg = "source symlink denied"
                raise ValueError(msg)
            if path.is_file():
                actual[str(path.relative_to(SOURCE))] = sha(path)
    if actual != projection or len(actual) != 3206:
        msg = "actual configured public source inventory drift"
        raise ValueError(msg)
    if hashlib.sha256(json.dumps(actual, sort_keys=True).encode()).hexdigest() != CLOSURE:
        msg = "source closure mismatch"
        raise ValueError(msg)
    nar = subprocess.run(
        ["nix", "hash", "path", "--sri", str(PACKAGE)], check=True, capture_output=True, text=True
    ).stdout.strip()
    if nar != NAR:
        msg = "package NAR mismatch"
        raise ValueError(msg)
    return {
        "package_output": str(PACKAGE),
        "package_nar_hash": nar,
        "configured_source_closure": CLOSURE,
        "role": "map",
        "cppflags_sha256": PINS["map-cppflags.txt"],
        "compile_recipe_sha256": PINS["map-compile-recipe.txt"],
        "source_files": {name: actual[name] for name in HEADERS},
        "configured_inventory_entries": 3216,
        "public_projection_entries": 3206,
        "generated_makefiles": sorted(generated),
        "compiler_commands": [],
        "recipe_replay": (
            "CPP/profile/type flags and include closure; not full backend/binary equivalence. "
            "Saved recipe is NPC obj/npc.o CXXFLAG_CLEARS, not clif obj/%.o CXXFLAGS. "
            "No claim CFLAGS -ffast-math applies to clif CXXFLAGS."
        ),
    }


def flags() -> list[str]:
    if sha(META / "map-cppflags.txt") != PINS["map-cppflags.txt"]:
        msg = "unapproved CPP effects"
        raise ValueError(msg)
    includes = [
        SOURCE / name
        for name in (
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
    if not all(path.is_dir() for path in includes):
        msg = "trusted include closure missing"
        raise ValueError(msg)
    return shlex.split((META / "map-cppflags.txt").read_text()) + [f"-I{path}" for path in includes]


def run_command(command: list[str], work: Path, authority: dict[str, Any], tag: str) -> str:
    env = {"PATH": os.environ["PATH"], "HOME": str(work), "TMPDIR": str(work), "LC_ALL": "C"}
    result = subprocess.run(
        command, check=False, capture_output=True, text=True, env=env, timeout=90
    )
    for suffix, text in [("stdout", result.stdout), ("stderr", result.stderr)]:
        (work / f"{tag}.{suffix}").write_text(text)
    authority["compiler_commands"].append(
        {
            "argv": command,
            "returncode": result.returncode,
            "stdout_sha256": sha(work / f"{tag}.stdout"),
            "stderr_sha256": sha(work / f"{tag}.stderr"),
            "stdout_path": str(work / f"{tag}.stdout"),
            "stderr_path": str(work / f"{tag}.stderr"),
            "environment": env,
        }
    )
    if result.returncode:
        msg = f"compiler failed: {tag}; command/log at {work / (tag + '.stderr')}"
        raise ValueError(msg)
    return result.stdout


def macro_guard(compiler: str, unit: Path, work: Path, authority: dict[str, Any], tag: str) -> None:
    stdout = run_command([compiler, *flags(), "-dM", "-E", str(unit)], work, authority, tag)
    macros = dict(re.findall(r"^#define (\w+)(?: (.*))?$", stdout, re.MULTILINE))
    if macros.get("PACKETVER") != "20180704" or macros.get("PACKETVER_MAIN_NUM") != "PACKETVER":
        msg = "qualified MAIN macro mismatch"
        raise ValueError(msg)
    for absent in (
        "RENEWAL",
        "PACKETVER_RE",
        "PACKETVER_ZERO",
        "PACKET_OBFUSCATION",
        "PACKET_OBFUSCATION_WARN",
    ):
        if absent in macros:
            msg = f"unexpected defined macro: {absent}"
            raise ValueError(msg)


def json_stream(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    nodes = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        node, index = decoder.raw_decode(text, index)
        nodes.append(node)
    return nodes


def measured(stdout: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    offsets: dict[tuple[str, str], int] = {}
    for line in stdout.splitlines():
        parts = line.split("\t")
        if parts[0] == "R" and len(parts) == 4:
            if parts[1] in values:
                msg = "duplicate layout stdout"
                raise ValueError(msg)
            values[parts[1]] = {
                "size": parse_integer(parts[2]),
                "alignment": parse_integer(parts[3]),
                "fields": [],
            }
        elif parts[0] == "H" and len(parts) == 3:
            values[parts[1]]["candidate_header_value"] = parse_integer(parts[2], header=True)
        elif parts[0] == "F" and len(parts) == 4:
            offsets[(parts[1], parts[2])] = parse_integer(parts[3])
        else:
            msg = "unsupported oracle stdout"
            raise ValueError(msg)
    for record in records:
        layout = values[record["name"]]
        for field in record["fields"]:
            reason = offset_reason(record, field)
            name = field.get("name")
            layout["fields"].append(
                {
                    "name": name,
                    "type": field["type"]["qualType"],
                    "offset": None if reason else offsets[(record["name"], name)],
                    "offset_unresolved_reason": reason,
                    "serialization": "UNKNOWN_LAYOUT_IS_NOT_WIRE_ENCODING",
                }
            )
    return values


def header_symbols(nodes: list[dict[str, Any]]) -> dict[str, str]:
    return {
        identifier(node["name"]): node["type"]["qualType"]
        for node in nodes
        if node.get("kind") == "VarDecl"
        and node.get("name", "").startswith("HEADER_")
        and node.get("type", {}).get("qualType") == "const int16"
    }


def collect(work: Path) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    authority = verify_authority()
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    for compiler_name, compiler in COMPILERS.items():
        authority[f"{compiler_name}_version"] = run_command(
            [compiler, "--version"], work, authority, compiler_name + "-version"
        )
    for scope, includes in UNITS.items():
        unit = work / (scope + ".cpp")
        unit.write_text(includes)
        for compiler_name, compiler in COMPILERS.items():
            macro_guard(compiler, unit, work, authority, scope + compiler_name + "-macros")
        nodes = []
        for prefix in ("PACKET_", "packet_"):
            text = run_command(
                [
                    COMPILERS["clang"],
                    *flags(),
                    "-Xclang",
                    "-ast-dump=json",
                    "-Xclang",
                    "-ast-dump-filter=" + prefix,
                    "-fsyntax-only",
                    str(unit),
                ],
                work,
                authority,
                scope + prefix + "ast",
            )
            nodes.extend(json_stream(text))
        records = parse_records(nodes)
        header_text = run_command(
            [
                COMPILERS["clang"],
                *flags(),
                "-Xclang",
                "-ast-dump=json",
                "-Xclang",
                "-ast-dump-filter=HEADER_",
                "-fsyntax-only",
                str(unit),
            ],
            work,
            authority,
            scope + "headers-ast",
        )
        headers = header_symbols(json_stream(header_text))
        for record in records:
            symbol = "HEADER_" + record["name"].removeprefix("PACKET_")
            record["header_symbol"] = symbol if symbol in headers else None
        oracle = work / (scope + "-oracle.cpp")
        supported = []
        for record in records:
            try:
                oracle_source([record], includes)
                supported.append(record)
            except ValueError as error:
                record["unsupported_reason"] = str(error)
                failures.append(f"{scope}:{record['name']}: {error}")
        oracle.write_text(oracle_source(supported, includes))
        authority.setdefault("generated_oracles", {})[scope] = {
            "path": str(oracle),
            "sha256": sha(oracle),
            "effects": "fixed-template printf of constant/sizeof/alignof/offsetof only",
        }
        verify_authority()
        layouts: dict[str, Any] = {}
        for compiler_name, compiler in COMPILERS.items():
            binary = work / (scope + "-" + compiler_name)
            try:
                macro_guard(
                    compiler, unit, work, authority, scope + compiler_name + "-precompile-macros"
                )
                run_command(
                    [compiler, *flags(), str(oracle), "-o", str(binary)],
                    work,
                    authority,
                    scope + compiler_name + "-compile",
                )
                layouts[compiler_name] = measured(
                    run_command([str(binary)], work, authority, scope + compiler_name + "-oracle"),
                    supported,
                )
            except (ValueError, KeyError) as error:
                layouts[compiler_name] = {}
                failures.append(str(error))
        for record in records:
            name = record["name"]
            gcc = layouts["gcc"].get(name)
            clang = layouts["clang"].get(name)
            conflict = gcc is None or clang is None or gcc != clang
            header_value = gcc.pop("candidate_header_value", None) if gcc else None
            clang_header_value = clang.pop("candidate_header_value", None) if clang else None
            header_candidate = (
                None
                if conflict or header_value is None
                else {
                    "symbol": record["header_symbol"],
                    "value": header_value,
                    "association": "CONVENTIONAL_NAME_CANDIDATE_NOT_SENDER_BINDING",
                }
            )
            rows.append(
                {
                    "record_name": name,
                    "declaration_key": scope + ":" + name,
                    "classification": (
                        "UNRESOLVED_MANUAL_REVIEW"
                        if conflict
                        else "LAYOUT_ONLY_NO_FRAMING_ADMISSION"
                    ),
                    "source": {
                        "translation_unit_scope": scope,
                        "primary_headers": authority["source_files"],
                        "ast_location": record["node"].get("loc", {}),
                        "location_policy": "raw compiler loc; omitted filename not inferred",
                    },
                    "gcc_layout": gcc,
                    "clang_layout": clang,
                    "header_candidate": header_candidate,
                    "header_compiler_values": {"gcc": header_value, "clang": clang_header_value},
                    "direction": "UNKNOWN",
                    "sender_evidence": "UNRESOLVED",
                    "unresolved_reason": (
                        record.get(
                            "unsupported_reason",
                            "missing compiler result or GCC/Clang disagreement",
                        )
                        if conflict
                        else None
                    ),
                }
            )
        (work / "checkpoint.json").write_text(json.dumps(rows, indent=2))
    verify_authority()
    compiled = sum(row["classification"] == "LAYOUT_ONLY_NO_FRAMING_ADMISSION" for row in rows)
    return {
        "schema": "qualified-packet-candidate-facts/v1",
        "authority": authority,
        "profile": {
            "packetver": 20180704,
            "family": "MAIN",
            "ruleset": "pre-re",
            "packet_obfuscation": False,
            "packet_obfuscation_warn": False,
        },
        "records": rows,
        "coverage": {
            "discovery_prefixes": ["PACKET_", "packet_"],
            "discovered_records": len(rows),
            "compiled_records": compiled,
            "unresolved_records": len(rows) - compiled,
            "discovery_units": UNITS,
            "count_unit": "complete declarations keyed by translation-unit scope and exact symbol",
            "same_spelling_is_not_same_declaration": (
                "PACKET_SC_NOTIFY_BAN exists separately in common and map; retained independently"
            ),
            "complete_catalogue": False,
            "uncovered": [
                "nonprefix records and aliases",
                "sender framing",
                "receiver registrations",
                "char/login/PIN/outgoing integration",
            ],
            "common_and_map_header_guards": (
                "Separate unchanged full-header TUs; same MAP CPP profile; no undef bypass"
            ),
        },
        "unresolved": [
            *failures,
            "All sender/header bindings unresolved; layout is not framing",
            "Variable/raw WFIFO/manual alias families not admitted",
        ],
        "required_preconditions": {
            "U2_allocator": "UNDISCHARGED",
            "U3_session": "UNDISCHARGED",
            "U4_source_lifetime": "UNDISCHARGED",
            "U5_recipient_lifetime": "UNDISCHARGED",
            "U6": "conditional copy only, not queue or receipt",
        },
        "sink_admission": False,
        "runtime_admission": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    protected = [SOURCE.resolve(), Path(__file__).resolve().parents[2], Path("/nix/store")]
    if any(output.is_relative_to(root) for root in protected):
        message = "output targets protected source/repository/store"
        raise ValueError(message)
    scratch = Path("/home/otto/.hermes/cache/scratch")
    work = Path(tempfile.mkdtemp(prefix="catalogue-evidence-", dir=scratch))
    result = collect(work)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    sys.stdout.write(
        json.dumps({"output": str(args.output), "coverage": result["coverage"]}) + "\n"
    )


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        msg = "unsupported C++ identifier"
        raise ValueError(msg)
    return value


def parse_integer(value: str, *, header: bool = False) -> int:
    if not re.fullmatch(r"[0-9]+", value):
        msg = "noninteger compiler stdout"
        raise ValueError(msg)
    number = int(value)
    if header and not 0 <= number <= 65535:
        msg = "header outside uint16 range"
        raise ValueError(msg)
    return number


def offset_reason(record: dict[str, Any], field: dict[str, Any]) -> str | None:
    if field.get("isBitfield"):
        return "bitfield has no addressable offsetof"
    if not field.get("name"):
        return "anonymous field"
    if not record["node"].get("definitionData", {}).get("isStandardLayout"):
        return "non-standard-layout or unavailable standard-layout proof"
    return None


def oracle_source(records: list[dict[str, Any]], includes: str) -> str:
    lines = [includes, "#include <cstdio>\n#include <cstddef>\nint main(){"]
    for record in records:
        name = identifier(record["name"])
        lines.append(f'printf("R\\t{name}\\t%zu\\t%zu\\n", sizeof({name}), alignof({name}));')
        if record.get("header_symbol"):
            symbol = identifier(record["header_symbol"])
            lines.append(f'printf("H\\t{name}\\t%lld\\n", static_cast<long long>({symbol}));')
        for field in record["fields"]:
            if offset_reason(record, field) is None:
                member = identifier(field["name"])
                lines.append(
                    f'printf("F\\t{name}\\t{member}\\t%zu\\n", offsetof({name}, {member}));'
                )
    lines.append("return 0;}")
    return "\n".join(lines)


def parse_records(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for node in nodes:
        name = node.get("name", "")
        if node.get("kind") != "CXXRecordDecl" or not node.get("completeDefinition"):
            continue
        if not name.startswith(("PACKET_", "packet_")):
            continue
        fields = [child for child in node.get("inner", []) if child.get("kind") == "FieldDecl"]
        if name in records:
            msg = "duplicate complete record symbol; namespace/provenance review required"
            raise ValueError(msg)
        records[name] = {"name": name, "fields": fields, "node": node}
    return [records[name] for name in sorted(records)]


if __name__ == "__main__":
    main()
