"""Compile retained public-only fixtures independently and persist real evidence."""

import collections
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile
import resolve

ROOT = pathlib.Path(__file__).resolve().parents[3]
GCC = "/nix/store/j1938gsbvbhkyz4kbmvjk56r479mkw3s-gcc-wrapper-16.2.0/bin/g++"
SCRATCH = pathlib.Path(
    tempfile.mkdtemp(prefix="ast-binding-", dir="/home/otto/.hermes/cache/scratch")
)
REPORT = ROOT / "run/reviews/native-ast-binding-feasibility.json"


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def semantic(result):
    def clean(value):
        if isinstance(value, list):
            return [clean(v) for v in value]
        if isinstance(value, dict):
            return {
                k: clean(v)
                for k, v in value.items()
                if k
                not in {
                    "call_ast_id",
                    "function_decl_id",
                    "object_decl_id",
                    "sizeof_decl_id",
                    "ast_id",
                    "member_decl_id",
                }
            }
        return value

    return clean(result["candidates"])


freeze_path = pathlib.Path(
    "/home/otto/.hermes/cache/scratch/native-ast-spike-production-freeze.json"
)
freeze = json.loads(freeze_path.read_text())
assert len(freeze) == 185
before = {p: sha(ROOT / p) for p in freeze}
assert before == freeze
fresh = json.loads(
    pathlib.Path("/home/otto/.hermes/cache/scratch/nmg-final/fresh-results.json").read_text()
)
assert len(fresh) == 23
cases = [
    {
        "source": v["source"],
        "name": v["name"],
        "group": "retained_fresh",
        "expected_stdout": v["actual_stdout"],
        "expected_kind": v["expected_kind"],
    }
    for v in fresh
]
seen = {v["source"] for v in cases}
for filename in [
    "native-manifest-generator-final-review.json",
    "native-manifest-generator-rereview.json",
]:
    old = json.loads((ROOT / "run/reviews" / filename).read_text())
    for artifact in old.get("artifacts", []):
        source = artifact["path"]
        if source.endswith(".cpp") and source not in seen and pathlib.Path(source).exists():
            seen.add(source)
            cases.append(
                {
                    "source": source,
                    "name": pathlib.Path(source).stem,
                    "group": "prior_available",
                    "expected_kind": "unresolved" if "complete-header" not in source else None,
                }
            )
rows = []
for number, case in enumerate(cases):
    directory = SCRATCH / str(number)
    directory.mkdir()
    source = pathlib.Path(case["source"])
    binary = directory / "oracle"
    command = [GCC, "-std=c++17", str(source), "-o", str(binary)]
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=30)
    (directory / "gcc.stderr").write_text(compiled.stderr)
    row: dict = dict(
        case, source_sha256=sha(source), gcc_command=command, gcc_exit=compiled.returncode
    )
    if not compiled.returncode:
        run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=5)
        row.update(
            gcc_stdout=run.stdout,
            gcc_runtime_exit=run.returncode,
            oracle_matches_retained=run.stdout == case.get("expected_stdout", run.stdout),
        )
        (directory / "gcc.stdout").write_text(run.stdout)
    first, second = resolve.analyze(source, directory / "first.ast.json"), resolve.analyze(
        source, directory / "second.ast.json"
    )
    for label, result in [("first", first), ("second", second)]:
        (directory / (label + ".json")).write_text(json.dumps(result, indent=2))
    row.update(
        clang_ast_produced=first["compiler"]["ast_produced"],
        semantic_repeat_equal=bool(
            first["compiler"]["ast_produced"]
            and second["compiler"]["ast_produced"]
            and semantic(first) == semantic(second)
            and first["compiler"].get("semantic_ast_sha256")
            == second["compiler"].get("semantic_ast_sha256")
        ),
        semantic_ast_sha256=first["compiler"].get("semantic_ast_sha256"),
        candidates=first["candidates"],
        clang_error=first.get("error"),
        artifact_directory=str(directory),
    )
    fixed = [v for v in first["candidates"] if v["decision"] == "FIXED_SIZEOF"]
    row["fixed_candidates"] = len(fixed)
    row["unresolved_candidates"] = len(first["candidates"]) - len(fixed)
    row["unsafe_all_unresolved"] = not fixed if case.get("expected_kind") == "unresolved" else None
    rows.append(row)
after = {p: sha(ROOT / p) for p in freeze}
report = {
    "verdict": "PARTIAL",
    "scope": "independent classifier-only offline synthetic C++ fixtures",
    "runtime_integration": False,
    "old_generator_approved": False,
    "real_clif_profile_supported": False,
    "full_translation_unit_supported": False,
    "numeric_lengths_extracted": False,
    "artifact_directory": str(SCRATCH),
    "physical_cpp_cases": len(rows),
    "retained_fresh_cases": sum(v["group"] == "retained_fresh" for v in rows),
    "prior_available_cases": sum(v["group"] == "prior_available" for v in rows),
    "safe_expected_cases": sum(v.get("expected_kind") == "fixed" for v in rows),
    "safe_expected_cases_admitted": sum(
        v.get("expected_kind") == "fixed" and v["fixed_candidates"] > 0 for v in rows
    ),
    "unsafe_expected_cases": sum(v.get("expected_kind") == "unresolved" for v in rows),
    "unsafe_expected_cases_all_unresolved": sum(v["unsafe_all_unresolved"] is True for v in rows),
    "compiler_frontend_successes": sum(v["clang_ast_produced"] for v in rows),
    "semantic_repeat_successes": sum(v["semantic_repeat_equal"] for v in rows),
    "gcc_compile_successes": sum(v["gcc_exit"] == 0 for v in rows),
    "gcc_oracle_comparisons": sum("expected_stdout" in v for v in rows),
    "gcc_oracle_matches": sum(
        "expected_stdout" in v and v.get("oracle_matches_retained", False) for v in rows
    ),
    "candidate_decisions": dict(
        collections.Counter(c["decision"] for v in rows for c in v["candidates"])
    ),
    "production_freeze": {
        "input_count": len(freeze),
        "before_matches": before == freeze,
        "after_matches": after == freeze,
        "changed_paths": [p for p in freeze if after[p] != freeze[p]],
    },
    "limitations": [
        "No production integration, catalogue approval or arbitrary C++ dataflow claim",
        "Straight-line direct local aggregate only; branches and lambdas unresolved",
        "Numeric sizeof lengths remain unknown; GCC stdout is independent oracle only",
        "Known clif_send is a pinned synthetic fixture sink, not server sender authority",
    ],
    "blocked_artifact": "/home/otto/.hermes/cache/scratch/nmg-final/owned/complete-header.cpp: missing config/core.hpp with fixture-only compiler options; requires separately reviewed full-TU include/profile closure. No exceptional real clif_send declarations adopted",
    "authority": str(ROOT / "run/reviews/native-ast-spike-authorization.json"),
    "cases": rows,
}
report["artifacts"] = [
    {"path": str(p), "sha256": sha(p)} for p in sorted(SCRATCH.rglob("*")) if p.is_file()
]
report["owned_code_hashes"] = {
    str(p.relative_to(ROOT)): sha(p) for p in pathlib.Path(__file__).parent.glob("*.py")
}
report["tdd_logs"] = [
    {"path": str(p), "sha256": sha(p)}
    for p in sorted(pathlib.Path("/home/otto/.hermes/cache/scratch").glob("ast-binding-*.log"))
    if p.name.startswith(("ast-binding-red", "ast-binding-green"))
]
report["validation_checks"] = {
    "fresh_gcc_oracles": all(
        v.get("oracle_matches_retained") for v in rows if v["group"] == "retained_fresh"
    ),
    "unsafe_fixture_denials": all(
        v["unsafe_all_unresolved"] for v in rows if v.get("expected_kind") == "unresolved"
    ),
    "nonzero_useful_coverage": report["safe_expected_cases_admitted"] > 0,
    "production_unchanged": before == freeze and after == freeze,
    "successful_ast_repeats": all(
        v["semantic_repeat_equal"] for v in rows if v["clang_ast_produced"]
    ),
}
REPORT.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k not in {"cases", "artifacts"}}, indent=2))
