"""Real immutable collector integration; perturbations are UNIT ONLY."""

import copy
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import contract
import pytest
from test_contract import synthetic_facts

RAW = Path("/home/otto/.hermes/cache/scratch/qualified-packet-catalogue-candidates.json")
RAW_SHA = "8a6443efd199edb2fc38d20109e043c637d2923648cd6aa1554cc613aeba802e"


def real_facts() -> dict[str, Any]:
    data = RAW.read_bytes()
    assert contract.sha256(data) == RAW_SHA
    result: dict[str, Any] = json.loads(data)
    return result


def test_real_catalogue_retains_every_declaration_and_evidence() -> None:
    facts = real_facts()
    report = contract.validate_facts(facts, contract.load_package_metadata())
    result = asdict(report)
    assert len(report.candidates) == 632
    assert len({c.record_name for c in report.candidates}) == 631
    for raw, candidate in zip(facts["records"], result["candidates"], strict=True):
        for key in raw.keys() - {"classification"}:
            assert candidate[key] == raw[key], key
    assert result["authority"] == facts["authority"]
    assert result["input_required_preconditions"] == facts["required_preconditions"]
    assert result["coverage"] == facts["coverage"]
    assert result["unresolved"] == tuple(facts["unresolved"])
    assert all(p["status"] == "UNDISCHARGED" for p in report.required_preconditions.values())
    assert not report.sink_admission
    assert not report.runtime_admission
    assert not report.compiler_execution_authenticated
    assert (
        result["source_verification_boundary"]
        == "PRIMARY_HEADER_HASHES_PLUS_IMMUTABLE_PACKAGE_SOURCE_MANIFEST"
    )
    assert len([c for c in report.candidates if c.record_name == "PACKET_SC_NOTIFY_BAN"]) == 2
    assert facts == real_facts()


def reject_unit(facts: dict[str, Any]) -> None:
    """Mutations are synthetic negative unit fixtures, never observations."""
    with pytest.raises(ValueError, match=r".+"):
        contract.validate_facts(facts, contract.load_package_metadata())


def test_same_scope_duplicates_rejected() -> None:
    facts = real_facts()
    facts["records"].append(copy.deepcopy(facts["records"][0]))
    facts["coverage"]["compiled_records"] += 1
    facts["coverage"]["discovered_records"] += 1
    reject_unit(facts)


def test_scoped_key_and_literal_symbol_not_repaired() -> None:
    for field, value in [
        ("declaration_key", "common:PACKET_CZ_ACK_ANSWER_MACRO_DETECTOR"),
        ("record_name", "map::PACKET_CZ_ACK_ANSWER_MACRO_DETECTOR"),
    ]:
        facts = real_facts()
        facts["records"][0][field] = value
        reject_unit(facts)


def test_claims_hashes_profiles_and_command_environment_denied() -> None:
    changes = [
        (("sink_admission",), True),
        (("runtime_admission",), True),
        (("compiler_execution_authenticated",), True),
        (("authority", "recipe_replay"), "full backend equality"),
        (("authority", "source_files", "src/config/core.hpp"), "0" * 64),
        (("profile", "packetver"), True),
        (("required_preconditions", "U2_allocator"), "PROVEN"),
    ]
    for keys, value in changes:
        facts = real_facts()
        node = facts
        for key in keys[:-1]:
            node = node[key]
        node[keys[-1]] = value
        reject_unit(facts)
    facts = real_facts()
    facts["authority"]["compiler_commands"][0]["environment"]["LD_PRELOAD"] = "/arbitrary"
    reject_unit(facts)


def test_header_ids_are_json_integers() -> None:
    for value in (True, 2652.0, -1, 65536):
        for target in ("header_candidate", "header_compiler_values"):
            facts = real_facts()
            facts["records"][0][target]["value" if target == "header_candidate" else "gcc"] = value
            reject_unit(facts)


def test_flexible_tail_offsets_are_not_wire_spans() -> None:
    facts = real_facts()
    tails = [
        (r, f)
        for r in facts["records"]
        for f in r["gcc_layout"]["fields"]
        if f["offset"] == r["gcc_layout"]["size"]
    ]
    assert len(tails) == 94
    for field_type, span in [("char", None), ("char *", None), ("char (*)[]", None), ("char[]", 1)]:
        invalid = copy.deepcopy(facts)
        record = next(
            r for r in invalid["records"] if r["declaration_key"] == tails[0][0]["declaration_key"]
        )
        field = next(
            f for f in record["gcc_layout"]["fields"] if f["offset"] == record["gcc_layout"]["size"]
        )
        field["type"] = field_type
        if span is not None:
            field["span"] = span
        reject_unit(invalid)


def test_counts_and_missing_evidence_components_denied() -> None:
    for section, key in [
        ("authority", "generated_makefiles"),
        ("coverage", "uncovered"),
        ("records", "header_compiler_values"),
    ]:
        facts = real_facts()
        node = facts["records"][0] if section == "records" else facts[section]
        del node[key]
        reject_unit(facts)
    facts = real_facts()
    facts["unresolved"] = []
    reject_unit(facts)
    for value in (True, 632.0, 631):
        facts = real_facts()
        facts["coverage"]["discovered_records"] = value
        reject_unit(facts)


def test_alias_and_compiler_conflicts_preserve_both_values() -> None:
    facts = real_facts()
    facts["records"][0]["header_compiler_values"]["clang"] += 1
    facts["records"][0].update(
        classification="UNRESOLVED_MANUAL_REVIEW",
        unresolved_reason="SYNTHETIC UNIT header disagreement",
        header_candidate=None,
    )
    facts["coverage"].update(compiled_records=631, unresolved_records=1)
    report = contract.validate_facts(facts, contract.load_package_metadata())
    assert report.candidates[0].classification == "UNRESOLVED_MANUAL_REVIEW"
    assert (
        report.candidates[0].header_compiler_values == facts["records"][0]["header_compiler_values"]
    )
    assert (
        "compiler header disagreement: " + facts["records"][0]["declaration_key"]
        in report.conflicts
    )
    assert len(report.candidates) == 632


def test_real_cli_preserves_boundary(capsys: pytest.CaptureFixture[str]) -> None:
    assert contract.main([str(RAW)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert len(output["candidates"]) == 632
    assert output["input_artifact"] == {"path": str(RAW), "sha256": RAW_SHA}
    assert not output["compiler_execution_authenticated"]
    assert not output["sink_admission"]
    assert not output["runtime_admission"]


@pytest.mark.parametrize("compiler", ["gcc_layout", "clang_layout"])
@pytest.mark.parametrize("array_type", ["char[]", "char[0]"])
def test_unit_nontrailing_zero_extent_rejected(compiler: str, array_type: str) -> None:
    facts = real_facts()
    row = next(
        r
        for r in facts["records"]
        if any(f["offset"] == r["gcc_layout"]["size"] for f in r["gcc_layout"]["fields"])
    )
    tail = row[compiler]["fields"][-1]
    assert tail["offset"] == row[compiler]["size"]
    tail["type"] = array_type
    row[compiler]["fields"].append(
        {
            "name": "SYNTHETIC_FOLLOWING_FIELD",
            "offset": 0,
            "type": "char",
            "offset_unresolved_reason": None,
            "serialization": "UNKNOWN_LAYOUT_IS_NOT_WIRE_ENCODING",
        }
    )
    reject_unit(facts)


def unit_identity() -> dict[str, Any]:
    """Synthetic invocation IDs, never actual compiler identity observations."""
    return {
        "classification": "ADDRESS_SIZEOF_IDENTITY_ONLY",
        "record_name": "PACKET_ZC_EMOTION",
        "invocation": "SYNTHETIC UNIT ONLY",
        "object_id": "0xabc",
        "address_object_id": "0xabc",
        "sizeof_object_id": "0xabc",
        "header_value": 192,
        "size": 7,
    }


def test_unit_identity_requires_actual_map_scope() -> None:
    facts = real_facts()
    facts["identity_evidence"] = unit_identity()
    assert (
        contract.validate_facts(facts, contract.load_package_metadata()).identity_evidence
        == unit_identity()
    )
    row = next(r for r in facts["records"] if r["record_name"] == "PACKET_ZC_EMOTION")
    row["source"]["translation_unit_scope"] = "common"
    row["declaration_key"] = "common:PACKET_ZC_EMOTION"
    reject_unit(facts)


@pytest.mark.parametrize(
    "mode", ["missing_gcc", "missing_both", "layout", "header", "equal_headers"]
)
def test_unit_producer_failure_grammar_retains_observations(mode: str, tmp_path: Path) -> None:
    facts = real_facts()
    row = facts["records"][0]
    row.update(
        classification="UNRESOLVED_MANUAL_REVIEW",
        unresolved_reason="SYNTHETIC UNIT compiler frontier",
        header_candidate=None,
    )
    facts["coverage"].update(compiled_records=631, unresolved_records=1)
    if mode == "missing_gcc":
        row["gcc_layout"] = None
        row["header_compiler_values"]["gcc"] = None
        facts["unresolved"].insert(0, "SYNTHETIC UNIT compiler failed")
    elif mode == "missing_both":
        row["gcc_layout"] = row["clang_layout"] = None
        row["header_compiler_values"] = {"gcc": None, "clang": None}
    elif mode in {"layout", "equal_headers"}:
        row["clang_layout"]["size"] += 1
        if mode == "layout":
            row["header_compiler_values"] = {"gcc": None, "clang": None}
    elif mode == "header":
        row["header_compiler_values"]["clang"] += 1
    original = copy.deepcopy(facts)
    report = asdict(contract.validate_facts(facts, contract.load_package_metadata()))
    assert report["candidates"][0]["classification"] == "UNRESOLVED_MANUAL_REVIEW"
    for key in row:
        assert report["candidates"][0][key] == row[key]
    assert facts == original
    assert report["coverage"] == facts["coverage"]
    assert report["unresolved"] == tuple(facts["unresolved"])
    path = tmp_path / "SYNTHETIC-UNIT-failure.json"
    path.write_text(json.dumps(facts))
    cli = subprocess.run(
        [sys.executable, str(Path(contract.__file__)), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert cli.returncode == 0, cli.stderr
    output = json.loads(cli.stdout)
    assert output["candidates"][0]["classification"] == "UNRESOLVED_MANUAL_REVIEW"
    assert not any(
        output[k]
        for k in ("sink_admission", "runtime_admission", "compiler_execution_authenticated")
    )
    facts["coverage"].update(compiled_records=632, unresolved_records=0)
    reject_unit(facts)


@pytest.mark.parametrize(
    ("target", "bad"),
    [
        ("field", None),
        ("field", 3),
        ("field", []),
        ("field", {}),
        ("layout", 3),
        ("layout", []),
        ("layout", {}),
        ("layout", None),
        ("fields", None),
        ("fields", {}),
        ("fields", 3),
        ("record", None),
        ("record", []),
        ("record", {}),
        ("identity", None),
        ("identity", []),
        ("identity", {}),
        ("headers", None),
        ("headers", []),
        ("headers", {}),
    ],
)
def test_unit_malformed_nested_shapes_api_and_cli(target: str, bad: Any, tmp_path: Path) -> None:
    facts = real_facts()
    if target == "field":
        facts["records"][0]["gcc_layout"]["fields"] = [bad]
    elif target == "fields":
        facts["records"][0]["gcc_layout"]["fields"] = bad
    elif target == "layout":
        facts["records"][0]["gcc_layout"] = bad
    elif target == "record":
        facts["records"][0] = bad
    elif target == "identity":
        facts["identity_evidence"] = bad
    elif target == "headers":
        facts["records"][0]["header_compiler_values"] = bad
    path = tmp_path / "SYNTHETIC-UNIT-malformed.json"
    path.write_text(json.dumps(facts))
    cli = subprocess.run(
        [sys.executable, str(Path(contract.__file__)), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert cli.returncode == 2, cli.stderr
    assert cli.stdout == ""
    assert "Traceback" not in cli.stderr
    reject_unit(facts)


@pytest.mark.parametrize("bad", [[], {}, None, 3])
def test_unit_classification_shape_is_value_error(bad: Any) -> None:
    facts = real_facts()
    facts["records"][0]["classification"] = bad
    reject_unit(facts)


@pytest.mark.parametrize("mode", ["legacy", "producer_masked"])
@pytest.mark.parametrize("bad", [[], {}], ids=["list", "dict"])
def test_unit_classification_shape_reaches_literal_guard(
    mode: str, bad: Any, tmp_path: Path
) -> None:
    """UNIT ONLY: exact accounting must not mask the malformed literal."""
    facts = synthetic_facts() if mode == "legacy" else real_facts()
    facts["records"][0]["classification"] = bad
    expected_count = 1 if mode == "legacy" else 631
    facts["coverage"].update(
        discovered_records=expected_count, compiled_records=expected_count, unresolved_records=0
    )
    assert len(facts["records"]) == (1 if mode == "legacy" else 632)
    assert contract.validate_coverage(facts) == facts["coverage"]
    with pytest.raises(ValueError, match="nonempty literal text required"):
        contract.validate_facts(facts, contract.load_package_metadata())
    path = tmp_path / "SYNTHETIC-UNIT-classification-shape.json"
    path.write_text(json.dumps(facts))
    cli = subprocess.run(
        [sys.executable, str(Path(contract.__file__)), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert cli.returncode == 2, cli.stderr
    assert cli.stdout == ""
    assert "Traceback" not in cli.stderr
    assert "TypeError" not in cli.stderr
    assert "nonempty literal text required" in cli.stderr


@pytest.mark.parametrize("mode", ["manual", "missing", "layout", "headers"])
def test_unit_identity_cannot_bind_compiler_frontier(mode: str) -> None:
    facts = real_facts()
    facts["identity_evidence"] = unit_identity()
    row = next(r for r in facts["records"] if r["declaration_key"] == "map:PACKET_ZC_EMOTION")
    row.update(
        classification="UNRESOLVED_MANUAL_REVIEW",
        unresolved_reason="SYNTHETIC UNIT frontier",
        header_candidate=None,
    )
    facts["coverage"].update(compiled_records=631, unresolved_records=1)
    if mode == "missing":
        row["gcc_layout"] = None
        row["header_compiler_values"]["gcc"] = None
    elif mode == "layout":
        row["clang_layout"]["size"] += 1
    elif mode == "headers":
        row["header_compiler_values"]["clang"] += 1
    reject_unit(facts)


@pytest.mark.parametrize("mode", ["missing", "layout", "headers", "no_reason", "candidate"])
def test_unit_invalid_compiler_frontier_not_layout_only(mode: str) -> None:
    facts = real_facts()
    row = facts["records"][0]
    if mode == "missing":
        row["gcc_layout"] = None
        row["header_compiler_values"]["gcc"] = None
    elif mode == "layout":
        row["clang_layout"]["size"] += 1
    elif mode == "headers":
        row["header_compiler_values"]["clang"] += 1
    else:
        row["classification"] = "UNRESOLVED_MANUAL_REVIEW"
        row["header_candidate"] = None if mode == "no_reason" else row["header_candidate"]
        row["unresolved_reason"] = None if mode == "no_reason" else "SYNTHETIC UNIT frontier"
        facts["coverage"].update(compiled_records=631, unresolved_records=1)
    reject_unit(facts)


def test_unit_nullable_layout_requires_known_producer_mode() -> None:
    facts = synthetic_facts()
    facts["coverage"] = copy.deepcopy(real_facts()["coverage"])
    facts["coverage"].update(discovered_records=1, compiled_records=0, unresolved_records=1)
    facts["unresolved"] = contract.LIMITATIONS.copy()
    row = facts["records"][0]
    row.update(
        classification="UNRESOLVED_MANUAL_REVIEW",
        unresolved_reason="SYNTHETIC UNIT fake producer",
        gcc_layout=None,
        clang_layout=None,
        header_candidate=None,
        header_compiler_values={"gcc": None, "clang": None},
    )
    reject_unit(facts)
