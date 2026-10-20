"""Synthetic UNIT fixtures; real compiler integration uses pinned full headers."""

import copy
import importlib.util
from dataclasses import asdict
from pathlib import Path
from types import ModuleType
from typing import Any

import contract
import pytest


def test_synthetic_safe_oracle_and_nullable_bitfield() -> None:
    module = load()
    record = {
        "name": "PACKET_SYNTHETIC_UNIT",
        "node": {"definitionData": {"isStandardLayout": True}},
        "fields": [{"name": "flag", "isBitfield": True, "type": {"qualType": "unsigned int"}}],
    }
    code = module.oracle_source([record], "#include <map/packets.hpp>\n")
    assert "sizeof(PACKET_SYNTHETIC_UNIT)" in code
    assert "offsetof(PACKET_SYNTHETIC_UNIT, flag)" not in code
    record["name"] = 'x);system("bad")'
    with pytest.raises(ValueError, match="identifier"):
        module.oracle_source([record], "")


def test_integer_stdout_rejects_bool_float_and_out_of_range() -> None:
    module = load()
    assert module.parse_integer("192", header=True) == 192
    for value in ["True", "1.0", "65536", "-1"]:
        with pytest.raises(ValueError, match=r"integer|range"):
            module.parse_integer(value, header=True)


def test_synthetic_header_type_denies_float_bool() -> None:
    module = load()
    for typename in ["const bool", "const float", "const double", "int16"]:
        assert (
            module.header_symbols(
                [{"kind": "VarDecl", "name": "HEADER_UNIT", "type": {"qualType": typename}}]
            )
            == {}
        )
    assert module.header_symbols(
        [{"kind": "VarDecl", "name": "HEADER_UNIT", "type": {"qualType": "const int16"}}]
    ) == {"HEADER_UNIT": "const int16"}


def test_synthetic_duplicate_complete_record_denied() -> None:
    module = load()
    node = {"kind": "CXXRecordDecl", "name": "PACKET_UNIT", "completeDefinition": True}
    with pytest.raises(ValueError, match="duplicate"):
        module.parse_records([node, node])


def test_source_drift_denied_before_compiler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load()
    monkeypatch.setattr(module, "SOURCE", tmp_path)
    calls: list[Any] = []
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **_kwargs: calls.append(args))
    with pytest.raises(ValueError, match="inventory drift"):
        module.collect(tmp_path / "out")
    assert calls == []


def test_cli_unreviewed_flags_response_and_plugin_denied_before_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = load()
    calls: list[Any] = []
    monkeypatch.setattr(module, "collect", lambda *_args: calls.append(1))
    for option in ["--cppflag=-URO", "@response", "--plugin=evil"]:
        monkeypatch.setattr(
            module.sys, "argv", ["compiler_catalogue.py", "--output", "/private/new.json", option]
        )
        with pytest.raises(SystemExit, match="2"):
            module.main()
    assert calls == []


def test_output_cannot_overwrite_source_or_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load()
    calls: list[Any] = []
    monkeypatch.setattr(module, "collect", lambda *_args: calls.append(1))
    monkeypatch.setattr(module, "SOURCE", tmp_path)
    monkeypatch.setattr(
        module.sys,
        "argv",
        ["compiler_catalogue.py", "--output", str(module.SOURCE / "src/config/core.hpp")],
    )
    with pytest.raises(ValueError, match="protected"):
        module.main()
    assert calls == []


def test_failed_real_compiler_preserves_logs(tmp_path: Path) -> None:
    module = load()
    module.verify_authority()
    unit = tmp_path / "unit-expected-syntax-failure.cpp"
    unit.write_text(module.UNITS["map"] + "#error SYNTHETIC_UNIT_EXPECTED_FAILURE\n")
    authority: dict[str, Any] = {"compiler_commands": []}
    with pytest.raises(ValueError, match="compiler failed"):
        module.run_command(
            [module.COMPILERS["gcc"], *module.flags(), "-fsyntax-only", str(unit)],
            tmp_path,
            authority,
            "synthetic-unit-failure",
        )
    assert authority["compiler_commands"][0]["returncode"] != 0
    assert (
        "SYNTHETIC_UNIT_EXPECTED_FAILURE"
        in (tmp_path / "synthetic-unit-failure.stderr").read_text()
    )


def test_synthetic_conflict_retains_both_layouts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load()
    original = module.measured
    invocation = 0

    def synthetic_conflict(stdout: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        nonlocal invocation
        invocation += 1
        values: dict[str, Any] = original(stdout, records)
        if invocation == 2:
            values["PACKET_ZC_EMOTION"]["size"] += 1
        return values

    monkeypatch.setattr(module, "measured", synthetic_conflict)
    facts = module.collect(tmp_path)
    row = next(row for row in facts["records"] if row["record_name"] == "PACKET_ZC_EMOTION")
    assert row["classification"] == "UNRESOLVED_MANUAL_REVIEW"
    assert row["gcc_layout"]["size"] == 7
    assert row["clang_layout"]["size"] == 8
    assert facts["coverage"]["unresolved_records"] == 1


def test_pinned_source_authority_and_real_collection(tmp_path: Path) -> None:
    module = load()
    authority = module.verify_authority()
    assert authority["configured_source_closure"] == module.CLOSURE
    facts = module.collect(tmp_path)
    assert facts["sink_admission"] is False
    assert facts["runtime_admission"] is False
    assert facts["coverage"]["discovered_records"] > 5
    rows = {row["record_name"]: row for row in facts["records"]}
    assert rows["PACKET_ZC_EMOTION"]["gcc_layout"]["size"] == 7
    assert rows["PACKET_ZC_STOPMOVE"]["gcc_layout"]["size"] == 10
    assert rows["PACKET_ZC_EMOTION"]["header_candidate"]["value"] == 192
    assert rows["PACKET_ZC_STOPMOVE"]["header_candidate"]["value"] == 136
    keys = [row["declaration_key"] for row in facts["records"]]
    assert len(set(keys)) == len(keys)
    assert sorted(
        rows[name]["gcc_layout"]["size"]
        for name in ["packet_idle_unit", "packet_spawn_unit", "packet_unit_walking"]
    ) == [103, 104, 110]


def load() -> ModuleType:
    path = Path(__file__).with_name("compiler_catalogue.py")
    assert path.exists(), "compiler-backed collector not implemented"
    spec = importlib.util.spec_from_file_location("compiler_catalogue", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_synthetic_active_record_discovery() -> None:
    module = load()
    node = {
        "kind": "CXXRecordDecl",
        "name": "PACKET_SYNTHETIC_UNIT",
        "completeDefinition": True,
        "definitionData": {"isStandardLayout": True},
        "inner": [{"kind": "FieldDecl", "name": "value", "type": {"qualType": "int"}}],
    }
    records = module.parse_records(
        [node, {"kind": "CXXRecordDecl", "name": "PACKET_SYNTHETIC_UNIT"}]
    )
    assert len(records) == 1
    assert records[0]["name"] == "PACKET_SYNTHETIC_UNIT"
    assert records[0]["fields"][0]["name"] == "value"


@pytest.mark.parametrize("mode", ["gcc_failure", "both_failure", "header_disagreement"])
def test_unit_collect_failure_assembly_interchange(
    mode: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Controlled UNIT seams; actual collect assembles rows, not fabricated GCC observations."""
    module = load()
    original_run = module.run_command
    original_measured = module.measured
    invocation = 0

    def controlled_run(argv: list[str], work: Path, authority: dict[str, Any], label: str) -> str:
        if label in (
            {"mapgcc-compile"}
            if mode == "gcc_failure"
            else {"mapgcc-compile", "mapclang-compile"} if mode == "both_failure" else set()
        ):
            raise ValueError("SYNTHETIC UNIT failed compiler seam: " + label)
        result: str = original_run(argv, work, authority, label)
        return result

    def controlled_measured(stdout: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        nonlocal invocation
        invocation += 1
        result: dict[str, Any] = original_measured(stdout, records)
        if mode == "header_disagreement" and invocation == 2:
            result["PACKET_ZC_EMOTION"]["candidate_header_value"] += 1
        return result

    monkeypatch.setattr(module, "run_command", controlled_run)
    monkeypatch.setattr(module, "measured", controlled_measured)
    facts = module.collect(tmp_path)
    saved = copy.deepcopy(facts)
    report = asdict(contract.validate_facts(facts, contract.load_package_metadata()))
    assert facts == saved
    for row, candidate in zip(facts["records"], report["candidates"], strict=True):
        for key in row.keys() - {"classification"}:
            assert candidate[key] == row[key]
    row = next(r for r in facts["records"] if r["declaration_key"] == "map:PACKET_ZC_EMOTION")
    assert row["classification"] == "UNRESOLVED_MANUAL_REVIEW"
    assert row["header_candidate"] is None
    assert row["unresolved_reason"]
    if mode == "header_disagreement":
        assert row["header_compiler_values"] == {"gcc": 192, "clang": 193}
        assert facts["coverage"]["compiled_records"] == 631
        assert facts["coverage"]["unresolved_records"] == 1
    else:
        assert row["gcc_layout"] is None
        assert row["header_compiler_values"]["gcc"] is None
        assert facts["coverage"]["compiled_records"] == 54
        assert facts["coverage"]["unresolved_records"] == 578
        assert any("SYNTHETIC UNIT failed compiler seam" in s for s in facts["unresolved"])
        assert (row["clang_layout"] is None) == (mode == "both_failure")
    assert not any(
        report[k]
        for k in ("sink_admission", "runtime_admission", "compiler_execution_authenticated")
    )
