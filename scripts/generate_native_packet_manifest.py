"""Compile complete pinned rAthena headers; publish an offline review catalogue only.

The C++ preprocessor selects guards. The restricted sender recognizer never
executes source expressions and leaves unsupported send bindings unresolved.
"""

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REVISION = "e985006171d2eb320ee512a653f4c83aea3d81b6"
SOURCE = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source")
MYSQL = Path("/nix/store/1w8g6rvhljfk44hx50qz4sc47sm1f28v-mariadb-connector-c-3.3.5-dev")
TRUSTED_EVIDENCE = Path(
    "/nix/store/plsvbs632sakjv9cl1pbzvjnnqs8y06n-rathena-playable-20180704-e985006171d2"
    "/share/rathena-playable"
)
TRUSTED_INPUTS = {
    "package.json": "b50eb76970a43974524393c7c1763185dcdc8eb27c6e9527bc898fbc1be479c6",
    "map-cppflags.txt": "7986f2fdeb11e55ee707ac27eb4701a64b90361ce1636bb728025fb92a99291d",
    "map-compile-recipe.txt": "8488711230e38fb3a48a9d19dca18b50b3a93780fd9287775768723af9358878",
}
COMPILER = Path("/nix/store/j1938gsbvbhkyz4kbmvjk56r479mkw3s-gcc-wrapper-16.2.0/bin/g++")
PREAMBLE = """#include <config/core.hpp>
#include <map/packets.hpp>
#include <common/packets.hpp>
#include <cstdio>
#include <cstddef>
static_assert(PACKETVER == 20180704);
static_assert(PACKETVER_MAIN_NUM == 20180704);
#if !defined(PACKETVER_MAIN_NUM) || defined(PACKETVER_RE_NUM) || defined(PACKETVER_ZERO_NUM)
#error Unexpected numeric family profile
#endif
#if defined(PACKETVER_RE) || defined(PACKETVER_ZERO) || defined(RENEWAL)
#error Unexpected server profile
#endif
"""
HEADERS = {"src/map/packets.hpp", "src/map/packets_struct.hpp", "src/common/packets.hpp"}


@dataclass(frozen=True)
class Definition:
    symbol: str
    body: str
    file: str
    line: int


@dataclass(frozen=True)
class Sender:
    symbol: str
    definition: str
    header: str
    variable: str
    body: str
    pointer: bool


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def authorize_evidence(evidence: Path) -> None:
    """Hashes authorize only the named immutable store package, never caller data."""
    if evidence.resolve() != TRUSTED_EVIDENCE or any(
        digest(evidence / name) != value for name, value in TRUSTED_INPUTS.items()
    ):
        message = "only immutable trusted reviewed profile evidence is supported"
        raise ValueError(message)


def pinned_compiler() -> str:
    compiler = shutil.which("g++")
    if compiler is None or Path(compiler).resolve() != COMPILER or not COMPILER.is_file():
        message = "g++ required from the pinned offline Nix development shell"
        raise ValueError(message)
    return compiler


def compile_profile(source: Path, evidence: Path) -> tuple[list[str], dict[str, Any]]:
    authorize_evidence(evidence)
    profile = json.loads((evidence / "package.json").read_text())
    expected: dict[str, Any] = {
        "revision": REVISION,
        "packetver": 20180704,
        "client_family": "MAIN",
        "ruleset": "pre-re",
    }
    if source.resolve() != SOURCE or any(profile.get(k) != v for k, v in expected.items()):
        message = "unsupported source revision or profile"
        raise ValueError(message)
    compiler = pinned_compiler()
    flags = shlex.split((evidence / "map-cppflags.txt").read_text())
    includes = [
        source / "src",
        source / "src/map",
        source / "src/common",
        source / "3rdparty/rapidyaml/src",
        source / "3rdparty/rapidyaml/ext/c4core/src",
        source / "3rdparty/libconfig",
        MYSQL / "include/mysql",
    ]
    command = [compiler, *flags, *(f"-I{p}" for p in includes)]
    expected["compiler_flags"] = flags
    return command, expected


def source_code(text: str, source: Path, files: set[str]) -> tuple[str, list[tuple[str, int]]]:
    """Retain CPP-selected tokens and original coordinates, not evaluated guards."""
    lines = []
    coordinates = []
    file = ""
    number = 0
    for line in text.splitlines():
        marker = re.match(r'^#\s+(\d+)\s+"([^"]+)"', line)
        if marker:
            number = int(marker[1])
            path = Path(marker[2])
            file = str(path.relative_to(source)) if path.is_relative_to(source) else ""
        else:
            if file in files:
                lines.append(line)
                coordinates.append((file, number))
            number += 1
    return "\n".join(lines), coordinates


def masked(text: str) -> str:
    """Mask comments/strings so braces inside literals cannot truncate bodies."""
    return re.sub(
        r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
        lambda match: re.sub(r"[^\n]", " ", match[0]),
        text,
    )


def closing_brace(text: str, start: int) -> int:
    depth = 0
    for offset in range(start, len(text)):
        if text[offset] == "{":
            depth += 1
        elif text[offset] == "}":
            depth -= 1
            if depth == 0:
                return offset
    message = "unbalanced preprocessed body"
    raise ValueError(message)


def definitions(text: str, coordinates: list[tuple[str, int]]) -> dict[str, Definition]:
    clean = masked(text)
    result = {}
    for match in re.finditer(r"\bstruct\s+(\w+)\s*\{", clean):
        end = closing_brace(clean, match.end() - 1)
        file, line = coordinates[clean.count("\n", 0, match.start())]
        result[match[1]] = Definition(match[1], clean[match.end() : end], file, line)
    return result


def lexical_scope(body: str, offset: int) -> tuple[int, ...]:
    """Brace identities in already masked CPP tokens, not a complete C++ AST."""
    stack: list[int] = []
    for token in re.finditer(r"[{}]", body[:offset]):
        if token[0] == "{":
            stack.append(token.start())
        elif stack:
            stack.pop()
    return tuple(stack)


def associated_body(body: str, declaration: re.Match[str], header: re.Match[str]) -> str:
    """Retain only a unique local identity with one unconditional prior header."""
    variable = re.escape(declaration[3])
    # Lambda captures/parameters are outside this brace-only identity recognizer.
    # Keep every binding in a possible lambda-containing function unresolved.
    if re.search(
        r"(?:^|[=(:,;{}?]|\breturn)\s*\[[^\]]*\][^;{}]*\{",
        body,
    ):
        return ""
    declarations = re.findall(
        rf"(?:\b[\w:<>]+\s*[*&]?\s*\b|,\s*[*&]?\s*){variable}\s*[=;{{\[]", body
    )
    writes = re.findall(
        rf"\b{variable}\s*(?:\.|->)\s*(?:packetType|PacketType)\s*(?:[+*/%&|^-]?=(?!=)|\+\+|--)",
        body,
    )
    rebound = re.search(rf"\b{variable}\s*=(?!=)", body[declaration.end() :])
    # Reject prefix writes rooted at this object, including parenthesized forms;
    # do not infer a new header value or approve uncertain member mutations.
    prefix_write = re.search(rf"(?:\+\+|--)\s*(?:\(\s*)*\b{variable}\b", body)
    scope = lexical_scope(body, declaration.start())
    if len(declarations) != 1 or len(writes) != 1 or rebound or prefix_write:
        return ""
    if not unconditional_header(body, declaration, header, scope):
        return ""
    sends = re.finditer(rf"\bclif_send\s*\(\s*&?\s*{variable}\s*,", body)
    for send in sends:
        send_scope = lexical_scope(body, send.start())
        if send.start() < header.end() or send_scope[: len(scope)] != scope:
            return ""
    return body


def unconditional_header(
    body: str, declaration: re.Match[str], header: re.Match[str], scope: tuple[int, ...]
) -> bool:
    prefix = re.split(r"[;{}]", body[: header.start()])[-1]
    return (
        header.start() >= declaration.end()
        and lexical_scope(body, header.start()) == scope
        and not prefix.strip()
    )


def senders(text: str) -> list[Sender]:
    clean = masked(text)
    result = []
    for function in re.finditer(r"\b(clif_\w+)\s*\([^;{}]*\)\s*\{", clean):
        end = closing_brace(clean, function.end() - 1)
        body = clean[function.end() : end]
        for declaration in re.finditer(r"\b(PACKET_\w+)\s*(\*?)\s+(\w+)\s*(?:[={;])", body):
            variable = declaration[3]
            header = re.search(
                rf"\b{variable}\s*(?:\.|->)\s*(?:packetType|PacketType)\s*=\s*(HEADER_\w+)\s*;",
                body,
            )
            if header:
                result.append(
                    Sender(
                        function[1],
                        declaration[1],
                        header[1],
                        variable,
                        associated_body(body, declaration, header),
                        bool(declaration[2]),
                    )
                )
    return result


def send_kind(
    definition: Definition, binding: Sender, length: str, flexible: bool
) -> tuple[str, str]:
    expression = re.sub(r"\s+", "", length)
    variable = re.escape(binding.variable)
    field = re.fullmatch(rf"{variable}(?:\.|->)(\w+)", expression)
    if field and flexible and re.search(rf"\b{field[1]}\s*;", definition.body):
        return "variable", field[1]
    direct_sizes = {f"sizeof({binding.variable})", f"sizeof({definition.symbol})"}
    if not flexible and not binding.pointer and expression in direct_sizes:
        return "fixed", ""
    return "unresolved", "length-driven buffer or unsupported length expression"


def framing(definition: Definition, bindings: list[Sender]) -> tuple[str, str]:
    """Recognize only direct local sizeof or flexible total-wire-length sends."""
    flexible = bool(re.search(r"\[\s*(?:0)?\s*\]", definition.body))
    kinds = set()
    fields = set()
    for binding in bindings:
        variable = re.escape(binding.variable)
        sends = list(
            re.finditer(rf"\bclif_send\s*\(\s*&?\s*{variable}\s*,\s*([^,]+),", binding.body)
        )
        if not sends:
            return "unresolved", "unsupported send binding"
        for send in sends:
            kind, field = send_kind(definition, binding, send[1], flexible)
            if kind == "unresolved":
                return kind, field
            kinds.add(kind)
            if field:
                fields.add(field)
    if kinds == {"fixed"}:
        return "fixed", ""
    if kinds == {"variable"} and len(fields) == 1:
        return "variable", next(iter(fields))
    return "unresolved", "ambiguous direction or length"


def dependency_paths(path: Path) -> set[Path]:
    """Read GCC make dependencies, including continuations and escaped spaces."""
    text = re.sub(r"\\\r?\n", "", path.read_text())
    payload = text.split(":", 1)[1]
    tokens = re.findall(r"(?:\\.|[^\s\\])+", payload)
    return {Path(re.sub(r"\\(.)", r"\1", token)) for token in tokens}


def build_evidence(command: list[str], source: Path, evidence: Path, root: Path) -> dict[str, Any]:
    paths = (
        dependency_paths(root / "headers.d")
        | dependency_paths(root / "senders.d")
        | dependency_paths(root / "layout.d")
    )
    dependencies = [
        {"path": str(p), "sha256": digest(p)} for p in sorted(paths) if not p.is_relative_to(root)
    ]
    public = {
        str(Path(row["path"]).relative_to(source)): row["sha256"]
        for row in dependencies
        if Path(row["path"]).is_relative_to(source)
    }
    canonical = json.dumps(dependencies, sort_keys=True, separators=(",", ":"))
    return {
        "dependencies": dependencies,
        "source_sha256": public,
        "sourceClosureHash": hashlib.sha256(canonical.encode()).hexdigest(),
        "sourceClosureHash_definition": (
            "sha256 UTF-8 compact sort_keys JSON of path-sorted dependencies "
            "(path, sha256), excluding generated probes"
        ),
        "compiler_path": command[0],
        "compiler_sha256": digest(Path(command[0]).resolve()),
        "compiler_version": subprocess.check_output([command[0], "--version"], text=True).strip(),
        "cppflags_sha256": digest(evidence / "map-cppflags.txt"),
        "compile_recipe_sha256": digest(evidence / "map-compile-recipe.txt"),
        "commands": [
            [*command, "-E", "-MD", "-MF", "<scratch>/headers.d", "<scratch>/probe.cpp"],
            [*command, "-E", "-MD", "-MF", "<scratch>/senders.d", str(source / "src/map/clif.cpp")],
            [
                *command,
                "-MD",
                "-MF",
                "<scratch>/layout.d",
                "<scratch>/probe.cpp",
                "-o",
                "<scratch>/probe",
            ],
            ["<scratch>/probe"],
        ],
        "command_path_notation": (
            "<scratch> is the fresh private TemporaryDirectory; otherwise exact argv"
        ),
    }


def validate_ids(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        packet_id = row["id"]
        if packet_id is not None and (type(packet_id) is not int or not 0 <= packet_id <= 65535):
            message = "packet ID is not uint16"
            raise ValueError(message)


def validate_frame(row: dict[str, Any]) -> None:
    frame = row["framing"]
    if row["id"] is None:
        message = "resolved packet has no compiler-proven ID"
        raise ValueError(message)
    if frame["kind"] == "variable" and (
        any(
            type(frame[field]) is not int
            for field in ("length_offset", "length_size", "minimum_length")
        )
        or frame["length_offset"] != 2
        or frame["length_size"] != 2
        or not 4 <= frame["minimum_length"] <= 65535
    ):
        message = "variable framing requires uint16 at offset 2 within its prefix"
        raise ValueError(message)


def validate_packets(packets: list[dict[str, Any]], unresolved: list[dict[str, Any]]) -> None:
    seen: dict[int, tuple[str, str, str]] = {}
    validate_ids(packets + unresolved)
    for row in packets:
        validate_frame(row)
        signature = (row["name"], row["direction"], json.dumps(row["framing"], sort_keys=True))
        if row["id"] in seen and seen[row["id"]] != signature:
            message = "conflicting duplicate packet ID"
            raise ValueError(message)
        seen[row["id"]] = signature


Selected = tuple[str, Definition | None, str, list[Sender], str, str]


def measurement_expression(record: Selected) -> str:
    name, definition, header, _, kind, field = record
    offset = f"offsetof({definition.symbol}, {field})" if definition and kind == "variable" else "0"
    width = (
        f"sizeof((({definition.symbol}*)nullptr)->{field})"
        if definition and kind == "variable"
        else "0"
    )
    size = f"sizeof({definition.symbol})" if definition else "0"
    return (
        f'std::printf("{name} %d %zu %zu %zu\\n", {header or "-1"}, '
        f"size_t({size}), size_t({offset}), size_t({width}));"
    )


def select_candidates(
    headers: set[str], zc_structs: set[str], structs: dict[str, Definition], bindings: list[Sender]
) -> tuple[list[Selected], list[str]]:
    selected = []
    expressions = []
    for name in sorted(headers | zc_structs):
        definition = structs.get(f"PACKET_{name}")
        header = f"HEADER_{name}" if name in headers else ""
        matches = [
            b
            for b in bindings
            if definition and b.definition == definition.symbol and b.header == header
        ]
        kind, field = (
            framing(definition, matches)
            if definition and matches
            else (
                "unresolved",
                (
                    "no active recognized emitter"
                    if definition
                    else "unsupported header-to-struct binding"
                ),
            )
        )
        selected.append((name, definition, header, matches, kind, field))
        expressions.append(measurement_expression(selected[-1]))
    return selected, expressions


def render_packets(
    selected: list[Selected], measurements: dict[str, list[int]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    packets: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for name, definition, header, matches, kind, field in selected:
        packet_id, size, offset, width = measurements[name]
        if kind == "unresolved":
            unresolved.append(
                {
                    "id": packet_id if packet_id >= 0 else None,
                    "name": name,
                    "reason": field,
                    "source": definition.file if definition else "src/map/packets.hpp",
                    "layout_sizeof": size if definition else None,
                }
            )
            continue
        assert definition is not None
        frame = (
            {"kind": "fixed", "length": size}
            if kind == "fixed"
            else {
                "kind": "variable",
                "length_offset": offset,
                "length_size": width,
                "minimum_length": size,
            }
        )
        proof: dict[str, Any] = {
            "definition_file": definition.file,
            "definition_line": definition.line,
            "definition_symbol": definition.symbol,
            "header_symbol": header,
            "sender_file": "src/map/clif.cpp",
            "sender_symbols": sorted({b.symbol for b in matches}),
            "method": "compiler sizeof/offsetof + CPP-active direct sender",
        }
        if field:
            proof["length_field"] = field
        packets.append(
            {
                "id": packet_id,
                "name": name,
                "direction": "server_to_client",
                "framing": frame,
                "evidence": proof,
            }
        )
    return packets, unresolved


def generate(source: Path, evidence: Path) -> dict[str, Any]:
    command, profile = compile_profile(source, evidence)
    with tempfile.TemporaryDirectory(
        prefix="native-manifest-", dir="/home/otto/.hermes/cache/scratch"
    ) as directory:
        root = Path(directory)
        probe = root / "probe.cpp"
        binary = root / "probe"
        probe.write_text(PREAMBLE)
        header_command = [*command, "-E", "-MD", "-MF", str(root / "headers.d"), str(probe)]
        header_text = subprocess.check_output(header_command, text=True)
        text, coordinates = source_code(header_text, source, HEADERS)
        structs = definitions(text, coordinates)
        sender_command = [
            *command,
            "-E",
            "-MD",
            "-MF",
            str(root / "senders.d"),
            str(source / "src/map/clif.cpp"),
        ]
        sender_text = subprocess.check_output(sender_command, text=True)
        active, _ = source_code(sender_text, source, {"src/map/clif.cpp"})
        bindings = senders(active)
        headers = set(re.findall(r"\bHEADER_(ZC_\w+)\b", text))
        zc_structs = {
            symbol.removeprefix("PACKET_") for symbol in structs if symbol.startswith("PACKET_ZC_")
        }
        selected, expressions = select_candidates(headers, zc_structs, structs, bindings)
        probe.write_text(PREAMBLE + "int main() {\n" + "\n".join(expressions) + "\n}\n")
        subprocess.run(
            [*command, "-MD", "-MF", str(root / "layout.d"), str(probe), "-o", str(binary)],
            check=True,
        )
        build = build_evidence(command, source, evidence, root)
        profile["source_sha256"] = build["source_sha256"]
        profile["source_sha256_scope"] = "compiler-selected public source/include closure"
        measurements = {
            parts[0]: list(map(int, parts[1:]))
            for line in subprocess.check_output([str(binary)], text=True).splitlines()
            if (parts := line.split())
        }
    packets, unresolved = render_packets(selected, measurements)
    validate_packets(packets, unresolved)
    return {
        "schema_version": 1,
        "profile": profile,
        "build_evidence": build,
        "packets": packets,
        "unresolved": unresolved,
        "inventory": {
            "active_zc_headers": sorted(headers),
            "active_zc_structs": sorted(zc_structs),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--profile-evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.output.is_absolute():
        parser.error("absolute output required")
    document = generate(args.source_root, args.profile_evidence)
    rendered = json.dumps(document, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", dir=args.output.parent, delete=False) as output:
        output.write(rendered)
        name = output.name
    os.replace(name, args.output)


if __name__ == "__main__":
    main()
