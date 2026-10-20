"""Offline candidate facts only: never an execution or admission authority."""

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PACKAGE_OUTPUT = (
    "/nix/store/0w1nfsmj8gaipcidhgx2nkg4axqxcbbr-"
    "rathena-playable-callback-qualified-20180704-e985006171d2-callback-qualified"
)
PACKAGE_NAR_HASH = "sha256-hIVo2RvlabG8Jw362W7PxdXkQx2CDYihvHKwhZjP0Es="
SOURCE_CLOSURE = "1f2d601dc86d572af78bae036f444fbbd469539457569e4f951438b30e74236a"
GENERATED = {
    f"src/{role}/Makefile" for role in ("char", "common", "login", "map", "tool", "web")
} | {f"3rdparty/{lib}/Makefile" for lib in ("httplib", "libconfig", "rapidyaml", "yaml-cpp")}
PRIMARY_HEADERS = {
    "src/config/core.hpp",
    "src/common/packets.hpp",
    "src/map/packets.hpp",
    "src/map/packets_struct.hpp",
}
AUTHORITY_EXTRA = {
    "configured_inventory_entries",
    "public_projection_entries",
    "generated_makefiles",
    "recipe_replay",
    "gcc_version",
    "clang_version",
    "generated_oracles",
}
COVERAGE_EXTRA = {
    "discovery_units",
    "count_unit",
    "same_spelling_is_not_same_declaration",
    "common_and_map_header_guards",
    "complete_catalogue",
    "uncovered",
}
DISCOVERY_UNITS = {
    scope: f"#include <config/core.hpp>\n#include <{scope}/packets.hpp>\n"
    for scope in ("map", "common")
}
UNCOVERED = [
    "nonprefix records and aliases",
    "sender framing",
    "receiver registrations",
    "char/login/PIN/outgoing integration",
]
RAW_PRECONDITIONS = {
    "U2_allocator": "UNDISCHARGED",
    "U3_session": "UNDISCHARGED",
    "U4_source_lifetime": "UNDISCHARGED",
    "U5_recipient_lifetime": "UNDISCHARGED",
    "U6": "conditional copy only, not queue or receipt",
}
RECIPE_REPLAY = (
    "CPP/profile/type flags and include closure; not full backend/binary equivalence. "
    "Saved recipe is NPC obj/npc.o CXXFLAG_CLEARS, not clif obj/%.o CXXFLAGS. "
    "No claim CFLAGS -ffast-math applies to clif CXXFLAGS."
)
LIMITATIONS = [
    "All sender/header bindings unresolved; layout is not framing",
    "Variable/raw WFIFO/manual alias families not admitted",
]


@dataclass(frozen=True)
class PackageMetadata:
    package_output: str
    profile: dict[str, Any]
    source_files: dict[str, str]
    cppflags_sha256: str
    compile_recipe_sha256: str


PRECONDITION_SOURCES = {
    "allocator_capacity_ownership": [
        "src/common/malloc.cpp",
        "src/common/socket.cpp",
        "src/common/socket.hpp",
    ],
    "integer_copy_bounds_no_overflow": [
        "src/common/socket.cpp",
        "src/common/socket.hpp",
        "src/map/clif.cpp",
    ],
    "source_object_lifetime": ["src/map/clif.cpp"],
    "recipient_session_lifetime": ["src/map/clif.cpp", "src/common/socket.cpp"],
    "queue_noninterference": ["src/map/map.cpp", "src/map/clif.cpp"],
    "oom_and_exception_paths": ["src/common/malloc.cpp", "src/map/map.cpp", "src/map/clif.cpp"],
}


def default_preconditions() -> dict[str, dict[str, Any]]:
    return {
        name: {"status": "UNDISCHARGED", "sources": sources.copy()}
        for name, sources in PRECONDITION_SOURCES.items()
    }


@dataclass(frozen=True)
class Candidate:
    record_name: str
    classification: str
    header_value: int | None
    source: str | dict[str, Any]
    gcc_layout: dict[str, Any] | None
    clang_layout: dict[str, Any] | None
    header_candidate: dict[str, Any] | None
    direction: str = "UNKNOWN"
    declaration_key: str = ""
    header_compiler_values: dict[str, Any] | None = None
    sender_evidence: str = "UNRESOLVED"
    unresolved_reason: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class ContractReport:
    candidates: tuple[Candidate, ...]
    required_preconditions: dict[str, dict[str, Any]]
    sink_admission: bool = False
    runtime_admission: bool = False
    compiler_execution_authenticated: bool = False
    verification_boundary: str = "STRUCTURAL_ONLY_NOT_COMPILER_EXECUTION_AUTHENTICATION"
    conflicts: tuple[str, ...] = ()
    unresolved: tuple[dict[str, Any] | str, ...] = ()
    coverage: dict[str, Any] | None = None
    identity_evidence: dict[str, Any] | None = None
    authority: dict[str, Any] | None = None
    input_required_preconditions: dict[str, Any] | None = None
    source_verification_boundary: str = "IMMUTABLE_PACKAGE_SOURCE_MANIFEST"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def object_fields(
    value: Any, required: set[str], optional: set[str] | None = None
) -> dict[str, Any]:
    require(isinstance(value, dict), "expected object")
    require(
        required <= value.keys() <= required | (optional or set()), "missing or unexpected fields"
    )
    return dict(value)


def integer(value: Any, minimum: int, maximum: int | None = None) -> int:
    require(type(value) is int, "JSON integer required, no boolean or float coercion")
    require(value >= minimum and (maximum is None or value <= maximum), "integer out of bounds")
    return int(value)


def text(value: Any) -> str:
    require(isinstance(value, str) and bool(value), "nonempty literal text required")
    return str(value)


def digest(value: Any) -> str:
    result = text(value)
    require(re.fullmatch(r"[0-9a-f]{64}", result) is not None, "malformed digest")
    return result


def validate_authority_inventory(authority: dict[str, Any], metadata: PackageMetadata) -> None:
    commands = authority["compiler_commands"]
    require(isinstance(commands, list) and bool(commands), "compiler command inventory missing")
    extended = bool(AUTHORITY_EXTRA & authority.keys())
    if extended:
        require(authority.keys() >= AUTHORITY_EXTRA, "incomplete authority components")
        require(
            integer(authority["configured_inventory_entries"], 0)
            == len(metadata.source_files) + len(GENERATED),
            "configured inventory mismatch",
        )
        require(
            integer(authority["public_projection_entries"], 0) == len(metadata.source_files),
            "public projection mismatch",
        )
        require(
            authority["generated_makefiles"] == sorted(GENERATED), "generated Makefiles mismatch"
        )
        require(authority["recipe_replay"] == RECIPE_REPLAY, "backend equivalence prohibited")
        text(authority["gcc_version"])
        text(authority["clang_version"])
        oracles = object_fields(authority["generated_oracles"], {"map", "common"})
        for oracle in oracles.values():
            row = object_fields(oracle, {"path", "sha256", "effects"})
            text(row["path"])
            digest(row["sha256"])
            require(
                row["effects"] == "fixed-template printf of constant/sizeof/alignof/offsetof only",
                "oracle effects inventory mismatch",
            )
    for command in commands:
        if isinstance(command, str):
            require(
                not extended and command == "SYNTHETIC UNIT TEST ONLY",
                "legacy command must be synthetic",
            )
            continue
        row = object_fields(
            command,
            {
                "argv",
                "returncode",
                "stdout_sha256",
                "stderr_sha256",
                "stdout_path",
                "stderr_path",
                "environment",
            },
        )
        require(isinstance(row["argv"], list) and bool(row["argv"]), "argv inventory missing")
        for arg in row["argv"]:
            text(arg)
        require(type(row["returncode"]) is int, "returncode must be JSON integer")
        for key in ("stdout_sha256", "stderr_sha256"):
            digest(row[key])
        for key in ("stdout_path", "stderr_path"):
            text(row[key])
        environment = object_fields(row["environment"], {"HOME", "LC_ALL", "PATH", "TMPDIR"})
        for value in environment.values():
            text(value)


def declaration_key(record: dict[str, Any], metadata: PackageMetadata) -> str:
    name = text(record["record_name"])
    source = record["source"]
    if isinstance(source, str):
        require(
            source
            in {
                "src/common/packets.hpp",
                "src/common/packets_struct.hpp",
                "src/map/packets.hpp",
                "src/map/packets_struct.hpp",
            }
            and source in metadata.source_files,
            "unapproved source reference",
        )
        scope = source.split("/")[1]
    else:
        source = object_fields(
            source, {"translation_unit_scope", "primary_headers", "ast_location", "location_policy"}
        )
        scope = text(source["translation_unit_scope"])
        require(scope in {"map", "common"}, "unknown translation unit scope")
        require(
            source["primary_headers"] == {p: metadata.source_files[p] for p in PRIMARY_HEADERS},
            "primary header provenance mismatch",
        )
        require(isinstance(source["ast_location"], dict), "raw AST location must be object")
        require(
            source["location_policy"] == "raw compiler loc; omitted filename not inferred",
            "AST filename must not be inferred",
        )
        require("declaration_key" in record, "scoped declaration key required")
    key = scope + ":" + name
    require(record.get("declaration_key", key) == key, "declaration key mismatch")
    return key


def layout(value: Any) -> dict[str, Any]:
    row = object_fields(value, {"size", "alignment", "fields"})
    size = integer(row["size"], 1)
    align = integer(row["alignment"], 1)
    require(align & (align - 1) == 0 and size % align == 0, "invalid C++ size/alignment")
    require(isinstance(row["fields"], list), "fields must be a list")
    names: set[str] = set()
    for index, raw_field in enumerate(row["fields"]):
        field = object_fields(
            raw_field,
            {"name", "offset", "type"},
            {"offset_reason", "span", "offset_unresolved_reason", "serialization"},
        )
        name = text(field["name"])
        require(name not in names, "duplicate field name")
        names.add(name)
        field_type = text(field["type"])
        if "serialization" in field:
            require(
                field["serialization"] == "UNKNOWN_LAYOUT_IS_NOT_WIRE_ENCODING",
                "serialization is unproven",
            )
        if field["offset"] is None:
            text(field.get("offset_unresolved_reason", field.get("offset_reason")))
            require(field.get("span") is None, "unknown offset cannot prove span")
        else:
            require(
                field.get("offset_unresolved_reason") is None,
                "measured offset has unresolved reason",
            )
            offset = integer(field["offset"], 0, size)
            if offset == size:
                require(
                    re.search(r"\[(?:0)?\]$", field_type) is not None
                    and "(" not in field_type
                    and ")" not in field_type
                    and field.get("span") is None
                    and index == len(row["fields"]) - 1,
                    "only zero-extent array may have one-past offset",
                )
            if field.get("span") is not None:
                span = integer(field["span"], 1)
                require(offset + span <= size, "field span exceeds record")
    return row


def validate_coverage(facts: dict[str, Any]) -> dict[str, Any]:
    coverage = object_fields(
        facts["coverage"],
        {"discovery_prefixes", "discovered_records", "compiled_records", "unresolved_records"},
        COVERAGE_EXTRA,
    )
    discovered = integer(coverage["discovered_records"], 0)
    compiled = integer(coverage["compiled_records"], 0)
    unresolved_count = integer(coverage["unresolved_records"], 0)
    producer = bool(COVERAGE_EXTRA & coverage.keys())
    if producer:
        classes = [
            object_fields(r, {"classification"}, set(r) - {"classification"})["classification"]
            for r in facts["records"]
            if isinstance(r, dict)
        ]
        require(len(classes) == len(facts["records"]), "expected record objects")
        accounted_compiled = classes.count("LAYOUT_ONLY_NO_FRAMING_ADMISSION")
        accounted_unresolved = classes.count("UNRESOLVED_MANUAL_REVIEW")
        require(
            all(isinstance(r, str) for r in facts["unresolved"]), "producer notices must be strings"
        )
        require(
            facts["unresolved"][-len(LIMITATIONS) :] == LIMITATIONS, "producer limitations missing"
        )
    else:
        accounted_compiled = len(facts["records"])
        accounted_unresolved = len([r for r in facts["unresolved"] if isinstance(r, dict)])
    require(
        discovered == compiled + unresolved_count
        and compiled == accounted_compiled
        and unresolved_count == accounted_unresolved,
        "inventory counts do not account exactly",
    )
    require(
        isinstance(coverage["discovery_prefixes"], list) and bool(coverage["discovery_prefixes"]),
        "discovery prefixes missing",
    )
    for prefix in coverage["discovery_prefixes"]:
        text(prefix)
    if COVERAGE_EXTRA & coverage.keys():
        require(coverage.keys() >= COVERAGE_EXTRA, "incomplete coverage components")
        require(coverage["discovery_units"] == DISCOVERY_UNITS, "discovery unit mismatch")
        require(coverage["complete_catalogue"] is False, "catalogue completeness unproven")
        require(
            coverage["count_unit"]
            == "complete declarations keyed by translation-unit scope and exact symbol",
            "count unit mismatch",
        )
        require(
            coverage["same_spelling_is_not_same_declaration"]
            == "PACKET_SC_NOTIFY_BAN exists separately in common and map; retained independently",
            "declaration scope warning missing",
        )
        require(
            coverage["common_and_map_header_guards"]
            == "Separate unchanged full-header TUs; same MAP CPP profile; no undef bypass",
            "header guard scope mismatch",
        )
        require(coverage["uncovered"] == UNCOVERED, "uncovered components missing")
    return coverage


def validate_identity(
    facts: dict[str, Any], metadata: PackageMetadata, affected: set[str]
) -> dict[str, Any] | None:
    identity = None
    if "identity_evidence" in facts:
        identity = object_fields(
            facts["identity_evidence"],
            {
                "classification",
                "record_name",
                "invocation",
                "object_id",
                "address_object_id",
                "sizeof_object_id",
                "header_value",
                "size",
            },
        )
        require(
            identity["classification"] == "ADDRESS_SIZEOF_IDENTITY_ONLY"
            and identity["record_name"] == "PACKET_ZC_EMOTION",
            "identity scope is single emotion only",
        )
        text(identity["invocation"])
        object_id = text(identity["object_id"])
        require(
            identity["address_object_id"] == object_id == identity["sizeof_object_id"],
            "invocation-local object identity mismatch",
        )
        header_id = integer(identity["header_value"], 0, 65535)
        size = integer(identity["size"], 1)
        matches = [r for r in facts["records"] if r["record_name"] == identity["record_name"]]
        require(
            len(matches) == 1
            and declaration_key(matches[0], metadata) == "map:PACKET_ZC_EMOTION"
            and "map:PACKET_ZC_EMOTION" not in affected
            and matches[0]["classification"] == "LAYOUT_ONLY_NO_FRAMING_ADMISSION"
            and matches[0]["gcc_layout"] == matches[0]["clang_layout"]
            and matches[0]["gcc_layout"] is not None
            and matches[0]["header_candidate"] is not None
            and matches[0]["header_candidate"]["value"] == header_id
            and matches[0]["gcc_layout"]["size"] == matches[0]["clang_layout"]["size"] == size,
            "identity does not match candidate measurement",
        )
    return identity


def validate_record(
    raw_record: Any, authority: dict[str, Any], metadata: PackageMetadata
) -> tuple[dict[str, Any], str]:
    record = object_fields(
        raw_record,
        {
            "record_name",
            "classification",
            "source",
            "gcc_layout",
            "clang_layout",
            "header_candidate",
        },
        {
            "direction",
            "reason",
            "declaration_key",
            "header_compiler_values",
            "sender_evidence",
            "unresolved_reason",
        },
    )
    name = declaration_key(record, metadata)
    if isinstance(record["source"], dict):
        require(
            {
                "declaration_key",
                "header_compiler_values",
                "direction",
                "sender_evidence",
                "unresolved_reason",
            }
            <= record.keys(),
            "compiled record evidence components missing",
        )
        for compiler in ("gcc_layout", "clang_layout"):
            if record[compiler] is None:
                require(
                    record["classification"] == "UNRESOLVED_MANUAL_REVIEW",
                    "missing layout must be manual",
                )
                text(record.get("unresolved_reason"))
                continue
            measured_layout = layout(record[compiler])
            for raw_field in measured_layout["fields"]:
                field = object_fields(
                    raw_field,
                    {"name", "offset", "type"},
                    {"offset_reason", "span", "offset_unresolved_reason", "serialization"},
                )
                require(
                    {"offset_unresolved_reason", "serialization"} <= field.keys(),
                    "compiled field evidence missing",
                )
    else:
        require(
            authority["source_files"] == metadata.source_files
            and authority["compiler_commands"] == ["SYNTHETIC UNIT TEST ONLY"],
            "literal source form is labelled synthetic only",
        )
    require(
        text(record["classification"])
        in {"LAYOUT_ONLY_NO_FRAMING_ADMISSION", "UNRESOLVED_MANUAL_REVIEW"},
        "classification forbidden",
    )
    require(record.get("direction", "UNKNOWN") == "UNKNOWN", "packet names are not direction proof")
    require(record.get("sender_evidence", "UNRESOLVED") == "UNRESOLVED", "sender evidence unproven")
    for reason_key in ("reason", "unresolved_reason"):
        if record.get(reason_key) is not None:
            text(record[reason_key])
    return record, name


def validate_authority(facts: dict[str, Any], metadata: PackageMetadata) -> dict[str, Any]:
    authority = object_fields(
        facts["authority"],
        {
            "package_output",
            "package_nar_hash",
            "configured_source_closure",
            "role",
            "cppflags_sha256",
            "compile_recipe_sha256",
            "source_files",
            "compiler_commands",
        },
        {"artifacts"} | AUTHORITY_EXTRA,
    )
    expected = {
        "package_output": PACKAGE_OUTPUT,
        "package_nar_hash": PACKAGE_NAR_HASH,
        "configured_source_closure": SOURCE_CLOSURE,
        "role": "map",
        "cppflags_sha256": metadata.cppflags_sha256,
        "compile_recipe_sha256": metadata.compile_recipe_sha256,
    }
    require(all(authority[k] == v for k, v in expected.items()), "immutable provenance mismatch")
    primary = {p: metadata.source_files[p] for p in PRIMARY_HEADERS}
    require(
        authority["source_files"] == metadata.source_files or authority["source_files"] == primary,
        "immutable source provenance mismatch",
    )
    validate_authority_inventory(authority, metadata)
    return authority


def validate_unresolved(
    facts: dict[str, Any], coverage: dict[str, Any], names: set[str], metadata: PackageMetadata
) -> None:
    for raw_item in facts["unresolved"]:
        if isinstance(raw_item, str):
            require(
                coverage.keys() >= COVERAGE_EXTRA
                and facts["unresolved"][-len(LIMITATIONS) :] == LIMITATIONS,
                "unresolved notices must retain limitations",
            )
            text(raw_item)
            continue
        item = object_fields(raw_item, {"record_name", "source", "reason"})
        name = declaration_key(item, metadata)
        require(name not in names, "duplicate resolved/unresolved key")
        names.add(name)
        text(item["reason"])
        require(item["source"] in metadata.source_files, "unresolved source must be pinned")


def validate_header_observations(
    record: dict[str, Any], name: str, producer: bool, layout_conflict: bool
) -> tuple[set[str], list[str]]:
    affected: set[str] = set()
    conflicts: list[str] = []
    if "header_compiler_values" in record:
        values = object_fields(record["header_compiler_values"], {"gcc", "clang"})
        values = {
            compiler: None if value is None else integer(value, 0, 65535)
            for compiler, value in values.items()
        }
        header_conflict = values["gcc"] != values["clang"]
        if header_conflict:
            affected.add(name)
            conflicts.append("compiler header disagreement: " + name)
        if producer:
            for compiler in ("gcc", "clang"):
                require(
                    record[compiler + "_layout"] is not None or values[compiler] is None,
                    "missing layout cannot have measured header",
                )
            failure = layout_conflict or header_conflict
            if failure or record["classification"] == "UNRESOLVED_MANUAL_REVIEW":
                require(
                    record["classification"] == "UNRESOLVED_MANUAL_REVIEW",
                    "compiler frontier must be manual review",
                )
                text(record.get("unresolved_reason"))
                require(
                    record["header_candidate"] is None,
                    "compiler frontier cannot bind candidate",
                )
            else:
                require(
                    record.get("unresolved_reason") is None,
                    "layout-only row has unresolved reason",
                )
                if record["header_candidate"] is None:
                    require(
                        values == {"gcc": None, "clang": None},
                        "header values without candidate",
                    )
                else:
                    require(
                        all(v == record["header_candidate"]["value"] for v in values.values()),
                        "candidate must match both measured headers",
                    )
        elif record["header_candidate"] is None:
            require(values == {"gcc": None, "clang": None}, "header values without candidate")
        else:
            measured = [integer(v, 0, 65535) for v in values.values()]
            if any(v != record["header_candidate"]["value"] for v in measured):
                affected.add(name)
                conflicts.append("compiler header disagreement: " + name)
    return affected, conflicts


def validate_facts(facts: dict[str, Any], metadata: PackageMetadata) -> ContractReport:
    facts = object_fields(
        facts,
        {
            "schema",
            "authority",
            "profile",
            "records",
            "coverage",
            "unresolved",
            "required_preconditions",
            "sink_admission",
            "runtime_admission",
        },
        {"identity_evidence"},
    )
    require(facts["schema"] == "qualified-packet-candidate-facts/v1", "schema mismatch")
    require(
        facts["sink_admission"] is False and facts["runtime_admission"] is False,
        "admission prohibited",
    )
    authority = validate_authority(facts, metadata)
    primary = {p: metadata.source_files[p] for p in PRIMARY_HEADERS}
    profile = object_fields(facts["profile"], set(metadata.profile))
    require(
        all(type(profile[k]) is type(v) and profile[k] == v for k, v in metadata.profile.items()),
        "profile mismatch",
    )
    require(
        facts["required_preconditions"] in (default_preconditions(), RAW_PRECONDITIONS),
        "all source-identified conditions must stay UNDISCHARGED",
    )
    require(
        isinstance(facts["records"], list) and isinstance(facts["unresolved"], list),
        "inventories must be lists",
    )
    coverage = validate_coverage(facts)
    if coverage.keys() >= COVERAGE_EXTRA:
        require(authority.keys() >= AUTHORITY_EXTRA, "producer mode requires complete authority")
        require(
            all(
                isinstance(r, dict) and isinstance(r.get("source"), dict) for r in facts["records"]
            ),
            "producer mode requires scoped sources",
        )
    if authority["source_files"] == primary:
        require(
            authority.keys() >= AUTHORITY_EXTRA and coverage.keys() >= COVERAGE_EXTRA,
            "primary headers require explicit producer components",
        )
        require(
            facts["unresolved"][-len(LIMITATIONS) :] == LIMITATIONS, "producer limitations missing"
        )
    names: set[str] = set()
    groups: dict[int, list[str]] = {}
    symbols: dict[str, list[str]] = {}
    conflicts: list[str] = []
    affected: set[str] = set()
    for raw_record in facts["records"]:
        record, name = validate_record(raw_record, authority, metadata)
        require(name not in names, "duplicate role/record key")
        names.add(name)
        producer = coverage.keys() >= COVERAGE_EXTRA
        gcc = None if producer and record["gcc_layout"] is None else layout(record["gcc_layout"])
        clang = (
            None if producer and record["clang_layout"] is None else layout(record["clang_layout"])
        )
        layout_conflict = gcc is None or clang is None or gcc != clang
        if layout_conflict:
            affected.add(name)
            conflicts.append("compiler layout disagreement: " + name)
        if record["header_candidate"] is not None:
            header = object_fields(record["header_candidate"], {"symbol", "value", "association"})
            symbol = text(header["symbol"])
            header_value = integer(header["value"], 0, 65535)
            groups.setdefault(header_value, []).append(name)
            symbols.setdefault(symbol, []).append(name)
            require(
                header["association"] == "CONVENTIONAL_NAME_CANDIDATE_NOT_SENDER_BINDING",
                "header association is not sender proof",
            )
        header_affected, header_conflicts = validate_header_observations(
            record, name, producer, layout_conflict
        )
        affected.update(header_affected)
        conflicts.extend(header_conflicts)
    for group in [*groups.values(), *symbols.values()]:
        if len(group) > 1:
            affected.update(group)
            conflicts.append("alias/header candidate ambiguity: " + ",".join(group))
    validate_unresolved(facts, coverage, names, metadata)
    candidates = tuple(
        Candidate(
            r["record_name"],
            (
                "UNRESOLVED_MANUAL_REVIEW"
                if declaration_key(r, metadata) in affected
                else r["classification"]
            ),
            None if r["header_candidate"] is None else r["header_candidate"]["value"],
            r["source"],
            r["gcc_layout"],
            r["clang_layout"],
            r["header_candidate"],
            declaration_key=declaration_key(r, metadata),
            header_compiler_values=r.get("header_compiler_values"),
            sender_evidence=r.get("sender_evidence", "UNRESOLVED"),
            unresolved_reason=r.get("unresolved_reason"),
            reason=r.get("reason"),
        )
        for r in facts["records"]
    )
    identity = validate_identity(facts, metadata, affected)
    return ContractReport(
        candidates,
        default_preconditions(),
        conflicts=tuple(conflicts),
        unresolved=tuple(facts["unresolved"]),
        coverage=coverage,
        identity_evidence=identity,
        authority=authority,
        input_required_preconditions=facts["required_preconditions"],
        source_verification_boundary=(
            "PRIMARY_HEADER_HASHES_PLUS_IMMUTABLE_PACKAGE_SOURCE_MANIFEST"
            if authority["source_files"] == primary
            else "IMMUTABLE_PACKAGE_SOURCE_MANIFEST"
        ),
    )


def load_package_metadata() -> PackageMetadata:
    root = Path(PACKAGE_OUTPUT) / "share/rathena-playable-callback-qualified"
    manifest = json.loads((root / "configured-source.json").read_text())
    require(
        {p for p in manifest["files"] if p.endswith("/Makefile")} >= GENERATED,
        "immutable generated Makefiles missing",
    )
    files = {k: v for k, v in manifest["files"].items() if k not in GENERATED}
    if hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest() != SOURCE_CLOSURE:
        message = "immutable public source closure mismatch"
        raise ValueError(message)
    profiles = json.loads((root / "profiles.json").read_text())
    if set(profiles) != {"common", "login", "char", "map"} or any(
        p != profiles["map"] for p in profiles.values()
    ):
        message = "immutable role profile mismatch"
        raise ValueError(message)
    profile = {
        "packetver": profiles["map"]["packetver"],
        "family": "MAIN",
        "ruleset": "pre-re",
        "packet_obfuscation": False,
        "packet_obfuscation_warn": False,
    }
    return PackageMetadata(
        PACKAGE_OUTPUT,
        profile,
        files,
        hashlib.sha256((root / "map-cppflags.txt").read_bytes()).hexdigest(),
        hashlib.sha256((root / "map-compile-recipe.txt").read_bytes()).hexdigest(),
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON object key")
        result[key] = value
    return result


def verify_artifacts(authority: dict[str, Any], root: Path) -> None:
    artifacts = authority.get("artifacts", {})
    require(isinstance(artifacts, dict), "artifacts must map relative paths to hashes")
    for name, digest in artifacts.items():
        require(
            isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
            "malformed artifact digest",
        )
        path = Path(text(name))
        require(
            not path.is_absolute() and ".." not in path.parts,
            "artifact must be local relative file",
        )
        target = root / path
        require(
            target.resolve().is_relative_to(root.resolve()) and not target.is_symlink(),
            "artifact escape/symlink",
        )
        require(sha256(target.read_bytes()) == digest, "artifact digest mismatch")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Offline facts validation; never framing/admission or compiler execution authentication"
        )
    )
    parser.add_argument("facts", type=Path)
    args = parser.parse_args(argv)
    try:
        input_bytes = args.facts.read_bytes()
        facts = json.loads(input_bytes, object_pairs_hook=unique_object)
        report = validate_facts(facts, load_package_metadata())
        verify_artifacts(facts["authority"], args.facts.parent)
    except (OSError, ValueError) as error:
        sys.stderr.write(f"contract validation rejected: {error}\n")
        return 2
    output = asdict(report)
    output["input_artifact"] = {"path": str(args.facts), "sha256": sha256(input_bytes)}
    output["verification_boundary"] = (
        "IMMUTABLE_PACKAGE_METADATA_AND_OPTIONAL_ARTIFACT_INTEGRITY_ONLY_"
        "NOT_COMPILER_EXECUTION_AUTHENTICATION"
    )
    sys.stdout.write(json.dumps(output, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
