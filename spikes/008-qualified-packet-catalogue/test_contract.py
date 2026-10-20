"""Synthetic layout fixtures; metadata comes from the real immutable package."""

import contextlib
import copy
import io
import json
import tempfile
from pathlib import Path
from typing import Any

import contract
import pytest


class TestContract:
    def test_real_metadata_is_bound(self) -> None:
        metadata = contract.load_package_metadata()
        assert metadata.package_output == contract.PACKAGE_OUTPUT
        assert metadata.profile["packetver"] == 20180704
        assert metadata.profile["family"] == "MAIN"
        assert len(metadata.source_files) == 3206

    def test_synthetic_layout_never_admits(self) -> None:
        facts = synthetic_facts()
        report = contract.validate_facts(facts, contract.load_package_metadata())
        assert not report.sink_admission
        assert not report.runtime_admission
        assert report.candidates[0].header_value == 192
        assert report.candidates[0].classification == "LAYOUT_ONLY_NO_FRAMING_ADMISSION"
        assert all(p["status"] == "UNDISCHARGED" for p in report.required_preconditions.values())

    def test_provenance_profile_and_conditions_fail_closed(self) -> None:
        changes = [
            (("schema",), "v2"),
            (("sink_admission",), True),
            (("runtime_admission",), 0),
            (("authority", "package_output"), "/caller/fake"),
            (("authority", "package_nar_hash"), "bad"),
            (("authority", "configured_source_closure"), "a" * 64),
            (("authority", "role"), "char"),
            (("authority", "cppflags_sha256"), "A" * 64),
            (("authority", "compile_recipe_sha256"), "0" * 64),
            (("authority", "source_files"), {}),
            (("authority", "compiler_commands"), []),
            (("profile", "packetver"), True),
            (("profile", "packetver"), 20180704.0),
            (("profile", "family"), "RE"),
            (("profile", "ruleset"), "renewal"),
            (("profile", "packet_obfuscation"), 0),
            (("profile", "packet_obfuscation_warn"), True),
            (("required_preconditions",), {}),
            (("required_preconditions", "source_object_lifetime", "status"), "PROVEN"),
        ]
        for keys, value in changes:
            with contextlib.nullcontext():
                facts = copy.deepcopy(synthetic_facts())
                node = facts
                for key in keys[:-1]:
                    node = node[key]
                node[keys[-1]] = value
                with pytest.raises(ValueError, match=r".+"):
                    contract.validate_facts(facts, contract.load_package_metadata())
        facts = synthetic_facts()
        facts["semantic_approval"] = True
        with pytest.raises(ValueError, match=r".+"):
            contract.validate_facts(facts, contract.load_package_metadata())

    def test_layout_integer_bounds_and_field_offsets_are_strict(self) -> None:
        value: Any
        for field, bad_values in {
            "size": [True, 7.0, 0, -1],
            "alignment": [False, 1.0, 0, -1, 3, 8],
        }.items():
            for value in bad_values:
                with contextlib.nullcontext():
                    facts = copy.deepcopy(synthetic_facts())
                    facts["records"][0]["gcc_layout"][field] = value
                    with pytest.raises(ValueError, match=r".+"):
                        contract.validate_facts(facts, contract.load_package_metadata())
        for value in [True, 0.0, -1, 7, None]:
            facts = copy.deepcopy(synthetic_facts())
            facts["records"][0]["gcc_layout"]["fields"][0]["offset"] = value
            with contextlib.nullcontext(), pytest.raises(ValueError, match=r".+"):
                contract.validate_facts(facts, contract.load_package_metadata())
        for value in [True, 192.0, -1, 65536]:
            facts = copy.deepcopy(synthetic_facts())
            facts["records"][0]["header_candidate"]["value"] = value
            with contextlib.nullcontext(), pytest.raises(ValueError, match=r".+"):
                contract.validate_facts(facts, contract.load_package_metadata())
        facts = copy.deepcopy(synthetic_facts())
        facts["records"][0]["header_candidate"] = None
        assert (
            contract.validate_facts(facts, contract.load_package_metadata())
            .candidates[0]
            .header_value
            is None
        )
        for compiler in ["gcc_layout", "clang_layout"]:
            facts["records"][0][compiler]["fields"][0].update(
                offset=None, offset_reason="bitfield offset unavailable"
            )
        assert not contract.validate_facts(facts, contract.load_package_metadata()).sink_admission

    def test_inventory_counts_duplicates_and_alias_conflicts(self) -> None:
        for field in ["discovered_records", "compiled_records", "unresolved_records"]:
            for value in [True, 1.0, -1, 9]:
                facts = copy.deepcopy(synthetic_facts())
                facts["coverage"][field] = value
                with contextlib.nullcontext(), pytest.raises(ValueError, match=r".+"):
                    contract.validate_facts(facts, contract.load_package_metadata())
        facts = copy.deepcopy(synthetic_facts())
        facts["records"].append(copy.deepcopy(facts["records"][0]))
        facts["coverage"].update(discovered_records=2, compiled_records=2)
        with pytest.raises(ValueError, match=r".+"):
            contract.validate_facts(facts, contract.load_package_metadata())
        facts["records"][1]["record_name"] = "PACKET_ALIAS"
        report = contract.validate_facts(facts, contract.load_package_metadata())
        assert len(report.candidates) == 2
        assert report.conflicts
        assert all(c.classification == "UNRESOLVED_MANUAL_REVIEW" for c in report.candidates)
        facts["records"] = facts["records"][:1]
        facts["unresolved"] = [
            {
                "record_name": "PACKET_MANUAL",
                "source": "src/map/packets_struct.hpp",
                "reason": "variable/helper/raw FIFO uncertain",
            }
        ]
        facts["coverage"].update(compiled_records=1, unresolved_records=1)
        report = contract.validate_facts(facts, contract.load_package_metadata())
        assert len(report.unresolved) == 1
        facts["unresolved"][0]["record_name"] = "PACKET_ZC_EMOTION"
        with pytest.raises(ValueError, match=r".+"):
            contract.validate_facts(facts, contract.load_package_metadata())

    def test_identity_stays_invocation_local_and_separate(self) -> None:
        facts = synthetic_facts()
        identity = {
            "classification": "ADDRESS_SIZEOF_IDENTITY_ONLY",
            "record_name": "PACKET_ZC_EMOTION",
            "invocation": "synthetic-one",
            "object_id": "0xabc",
            "address_object_id": "0xabc",
            "sizeof_object_id": "0xabc",
            "header_value": 192,
            "size": 7,
        }
        facts["identity_evidence"] = identity
        report = contract.validate_facts(facts, contract.load_package_metadata())
        assert report.identity_evidence == identity
        assert not report.sink_admission
        assert not report.compiler_execution_authenticated
        for key, value in [
            ("address_object_id", "0xdef"),
            ("sizeof_object_id", "0xdef"),
            ("invocation", ""),
            ("classification", "FRAMING_PROVEN"),
            ("size", True),
            ("header_value", 193),
        ]:
            invalid = copy.deepcopy(facts)
            invalid["identity_evidence"][key] = value
            with contextlib.nullcontext(), pytest.raises(ValueError, match=r".+"):
                contract.validate_facts(invalid, contract.load_package_metadata())

    def test_offline_cli_keeps_artifact_integrity_below_authentication(self) -> None:
        with tempfile.TemporaryDirectory(dir="/home/otto/.hermes/cache/scratch") as directory:
            root = Path(directory)
            facts_path = root / "synthetic.json"
            artifact = root / "synthetic.stdout"
            artifact.write_text("THIS IS SYNTHETIC NOT COMPILER OUTPUT")
            facts = synthetic_facts()
            facts["authority"]["artifacts"] = {
                "synthetic.stdout": contract.sha256(artifact.read_bytes())
            }
            facts_path.write_text(json.dumps(facts))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = contract.main([str(facts_path)])
                assert status == 0
            report = json.loads(output.getvalue())
            assert not report["compiler_execution_authenticated"]
            assert not report["runtime_admission"]
            assert report["candidates"][0]["gcc_layout"]["size"] == 7
            artifact.write_text("TAMPERED")
            with contextlib.redirect_stderr(io.StringIO()):
                status = contract.main([str(facts_path)])
                assert status == 2
            facts_path.write_text('{"schema":1,"schema":2}')
            with contextlib.redirect_stderr(io.StringIO()):
                status = contract.main([str(facts_path)])
                assert status == 2


def synthetic_facts() -> dict[str, Any]:
    """NOT published compiler evidence: synthetic 7-byte emotion layout."""
    m = contract.load_package_metadata()
    layout = {
        "size": 7,
        "alignment": 1,
        "fields": [{"name": "header", "offset": 0, "type": "uint16"}],
    }
    return {
        "schema": "qualified-packet-candidate-facts/v1",
        "authority": {
            "package_output": m.package_output,
            "package_nar_hash": contract.PACKAGE_NAR_HASH,
            "configured_source_closure": contract.SOURCE_CLOSURE,
            "role": "map",
            "cppflags_sha256": m.cppflags_sha256,
            "compile_recipe_sha256": m.compile_recipe_sha256,
            "source_files": m.source_files,
            "compiler_commands": ["SYNTHETIC UNIT TEST ONLY"],
        },
        "profile": m.profile.copy(),
        "records": [
            {
                "record_name": "PACKET_ZC_EMOTION",
                "classification": "LAYOUT_ONLY_NO_FRAMING_ADMISSION",
                "source": "src/map/packets_struct.hpp",
                "gcc_layout": layout,
                "clang_layout": layout,
                "header_candidate": {
                    "symbol": "HEADER_ZC_EMOTION",
                    "value": 192,
                    "association": "CONVENTIONAL_NAME_CANDIDATE_NOT_SENDER_BINDING",
                },
            }
        ],
        "coverage": {
            "discovery_prefixes": ["PACKET_"],
            "discovered_records": 1,
            "compiled_records": 1,
            "unresolved_records": 0,
        },
        "unresolved": [],
        "required_preconditions": contract.default_preconditions(),
        "sink_admission": False,
        "runtime_admission": False,
    }
