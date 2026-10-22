"""Standalone offline reviewed public closure replay; no production imports."""

import ast
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import time
import argparse

REPO = Path("/home/otto/dev/ro-bots")
SOURCE = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source")
META = Path(
    "/nix/store/plsvbs632sakjv9cl1pbzvjnnqs8y06n-rathena-playable-20180704-e985006171d2/share/rathena-playable"
)
AUDIT = REPO / "run/reviews/native-ast-configured-source-audit.json"
AUDIT_HASH = "c70312d5b1bd6a3e80f85453461851c85019fb4d73b6c82b29169120ecca1567"
APPEND = b"\n#undef PACKET_OBFUSCATION\n#undef PACKET_OBFUSCATION_WARN\n"
GCC = "/nix/store/j1938gsbvbhkyz4kbmvjk56r479mkw3s-gcc-wrapper-16.2.0/bin/g++"
CLANG = "/nix/store/2msw5nclhpsm80z65dqmjiv8kkras989-clang-wrapper-21.1.8/bin/clang++"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked(path, expected):
    data = Path(path).read_bytes()
    if digest(data) != expected:
        raise ValueError("authority hash drift: " + str(path))
    return data


def authorities():
    audit = json.loads(checked(AUDIT, AUDIT_HASH))
    a, b = audit["authorities"], audit["available_artifacts"]
    checked(a["installed_deriver"], a["deriver_sha256"])
    for key in ["immutable_runtime_header", "immutable_transform", "immutable_profile_script"]:
        checked(a[key]["path"], a[key]["sha256"])
    for name, key in [
        ("profiles.json", "profiles_sha256"),
        ("profile-oracle.cpp", "profile_oracle_sha256"),
    ]:
        checked(META / name, b[key])
    for role in ["common", "login", "char", "map"]:
        checked(META / (role + "-cppflags.txt"), b[role + "_cppflags_sha256"])
        checked(META / (role + "-compile-recipe.txt"), b[role + "_recipe_sha256"])
    checked(META / "core-start.cpp", b["retained_exact_core"]["sha256"])
    checked(SOURCE / "src/common/core.cpp", a["upstream_core_sha256"])
    checked(SOURCE / "src/custom/defines_post.hpp", a["upstream_defines_post_sha256"])
    checked(SOURCE / "configure", a["configure_sha256"])
    tree = ast.parse(Path(a["immutable_transform"]["path"]).read_text())
    writes = [
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "custom"
        and node.func.attr == "write"
    ]
    if writes != [APPEND.decode()]:
        raise ValueError("unreviewed append literal")
    return audit


def inventory(root):
    result = {}
    for directory in ["src", "3rdparty"]:
        for path in sorted((root / directory).rglob("*")):
            if path.is_symlink():
                raise ValueError("public source symlink refused: " + str(path))
            if path.is_file():
                result[str(path.relative_to(root))] = digest(path.read_bytes())
    return result


def validate_flags(role, text):
    audit = authorities()
    if role not in ["common", "login", "char", "map"]:
        raise ValueError("unsupported role")
    trusted = checked(
        META / (role + "-cppflags.txt"), audit["available_artifacts"][role + "_cppflags_sha256"]
    ).decode()
    if text != trusted:
        raise ValueError("unreviewed compiler flags")
    return shlex.split(trusted)


def verify_diff(result):
    before, after = result["before"], result["after"]
    changed = sorted(
        name for name in set(before) | set(after) if before.get(name) != after.get(name)
    )
    if changed != [
        "src/common/core.cpp",
        "src/common/runtime-root.hpp",
        "src/custom/defines_post.hpp",
    ]:
        raise ValueError("unreviewed source differences: " + repr(changed))
    return changed


def construct(destination):
    audit = authorities()
    destination = Path(destination)
    scratch = Path(os.environ["TMPDIR"]).resolve()
    if not destination.resolve().is_relative_to(scratch):
        raise ValueError("destination outside private scratch")
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    before = inventory(SOURCE)
    for name, expected in before.items():
        data = checked(SOURCE / name, expected)
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (destination / "src/common/core.cpp").write_bytes((META / "core-start.cpp").read_bytes())
    (destination / "src/common/runtime-root.hpp").write_bytes(
        Path(audit["authorities"]["immutable_runtime_header"]["path"]).read_bytes()
    )
    custom = destination / "src/custom/defines_post.hpp"
    custom.write_bytes(custom.read_bytes() + APPEND)
    checked(custom, audit["obfuscation_mismatch"]["expected_replayed_defines_post_sha256"])
    after = inventory(destination)
    return {
        "before": before,
        "after": after,
        "source_closure_sha256": digest(json.dumps(after, sort_keys=True).encode()),
    }


GUARD = """#include "src/common/mmo.hpp"
static_assert(PACKETVER == 20180704 && PACKETVER_MAIN_NUM == 20180704);
#if defined(PACKETVER_RE_NUM) || defined(PACKETVER_ZERO_NUM)
#error unexpected RE or ZERO numeric family macro
#endif
static_assert(PACKETVER_SUPPORTS_PINCODE);
#if defined(RENEWAL) || defined(PACKETVER_RE) || defined(PACKETVER_ZERO) || defined(PACKET_OBFUSCATION) || defined(PACKET_OBFUSCATION_WARN)
#error incorrect replay profile including WARN
#endif
"""
LAYOUT = """#include <config/core.hpp>
#include <map/packets.hpp>
#include <common/packets.hpp>
#include <cstddef>
#include <cstdio>
static_assert(HEADER_ZC_EMOTION == 192 && sizeof(PACKET_ZC_EMOTION) == 7);
static_assert(offsetof(PACKET_ZC_EMOTION,packetType)==0 && offsetof(PACKET_ZC_EMOTION,GID)==2 && offsetof(PACKET_ZC_EMOTION,type)==6);
static_assert(HEADER_ZC_STOPMOVE == 136 && sizeof(PACKET_ZC_STOPMOVE) == 10);
static_assert(offsetof(PACKET_ZC_STOPMOVE,packetType)==0 && offsetof(PACKET_ZC_STOPMOVE,AID)==2 && offsetof(PACKET_ZC_STOPMOVE,xPos)==6 && offsetof(PACKET_ZC_STOPMOVE,yPos)==8);
static_assert(sizeof(packet_unit_walking)==110 && sizeof(packet_idle_unit)==104 && sizeof(packet_spawn_unit)==103);
static_assert(unit_walkingType==0x9fd && spawn_unitType==0x9fe && idle_unitType==0x9ff);
int main(){
 printf("{\\"emotion\\":{\\"id\\":%d,\\"size\\":%zu,\\"offsets\\":[%zu,%zu,%zu]},\\"stopmove\\":{\\"id\\":%d,\\"size\\":%zu,\\"offsets\\":[%zu,%zu,%zu,%zu]},\\"actors\\":{\\"walking\\":%zu,\\"idle\\":%zu,\\"spawn\\":%zu}}\\n", HEADER_ZC_EMOTION,sizeof(PACKET_ZC_EMOTION),offsetof(PACKET_ZC_EMOTION,packetType),offsetof(PACKET_ZC_EMOTION,GID),offsetof(PACKET_ZC_EMOTION,type), HEADER_ZC_STOPMOVE,sizeof(PACKET_ZC_STOPMOVE),offsetof(PACKET_ZC_STOPMOVE,packetType),offsetof(PACKET_ZC_STOPMOVE,AID),offsetof(PACKET_ZC_STOPMOVE,xPos),offsetof(PACKET_ZC_STOPMOVE,yPos),sizeof(packet_unit_walking),sizeof(packet_idle_unit),sizeof(packet_spawn_unit));
}
"""


def execute(report, output, name, command, cwd, expected=0):
    stdout, stderr = output / (name + ".stdout"), output / (name + ".stderr")
    started = time.monotonic()
    with stdout.open("wb") as out, stderr.open("wb") as err:
        try:
            result = subprocess.run(command, cwd=cwd, stdout=out, stderr=err, timeout=45)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 124
    entry = {
        "name": name,
        "command": command,
        "cwd": str(cwd),
        "exit": code,
        "expected": expected,
        "seconds": round(time.monotonic() - started, 3),
        "stdout": str(stdout),
        "stderr": str(stderr),
        "stdout_sha256": digest(stdout.read_bytes()),
        "stderr_sha256": digest(stderr.read_bytes()),
    }
    report["commands"].append(entry)
    (output / "progress.json").write_text(json.dumps(report, indent=2) + "\n")
    if code != expected:
        raise RuntimeError(name + " failed, exit " + str(code) + ", diagnostics " + str(stderr))
    return stdout.read_text()


def includes(root):
    # Explicit public include paths already reviewed in retained commands.json.
    return [
        "-I" + str(root / p)
        for p in [
            "src",
            "src/map",
            "src/common",
            "3rdparty/rapidyaml/src",
            "3rdparty/rapidyaml/ext/c4core/src",
            "3rdparty/libconfig",
        ]
    ] + [
        "-I/nix/store/1w8g6rvhljfk44hx50qz4sc47sm1f28v-mariadb-connector-c-3.3.5-dev/include/mysql"
    ]


def ast_counts(text, name):
    decoder = json.JSONDecoder()
    docs, position = [], 0
    while position < len(text):
        while position < len(text) and text[position].isspace():
            position += 1
        if position == len(text):
            break
        doc, position = decoder.raw_decode(text, position)
        docs.append(doc)
    definitions, nodes = [], 0
    stack = docs.copy()
    while stack:
        item = stack.pop()
        nodes += 1
        if (
            item.get("kind") == "FunctionDecl"
            and item.get("name") == name
            and any(c.get("kind") == "CompoundStmt" for c in item.get("inner", []))
        ):
            definitions.append(item.get("id"))
        stack.extend(item.get("inner", []))
    if not definitions:
        raise ValueError("missing real sender definition " + name)
    return {
        "json_documents": len(docs),
        "nodes": nodes,
        "definition_ids": definitions,
        "sender_admitted": False,
    }


def freeze_status():
    before = json.loads((Path(__file__).parent / "before.json").read_text())
    drift = [
        name
        for section in ["production", "old_spike"]
        for name, expected in before[section].items()
        if digest((REPO / name).read_bytes()) != expected
    ]
    return {
        "stable": not drift,
        "production_count": len(before["production"]),
        "old_spike_count": len(before["old_spike"]),
        "drift": drift,
    }


def experiment():
    root = Path(tempfile.mkdtemp(prefix="native-profile-replay-", dir=os.environ["TMPDIR"]))
    output = root / "output"
    output.mkdir(mode=0o700)
    source = root / "public-source"
    report = {
        "schema": "native-ast-profile-replay-v1",
        "verdict": "PARTIAL",
        "source_claim": "reviewed reconstructed public configured closure",
        "binary_equivalence": False,
        "runtime_integration": False,
        "sender_admission": False,
        "world_criteria_completed": False,
        "private_artifact_root": str(root),
        "commands": [],
        "profiles": [],
        "layouts": [],
        "asts": {},
        "issues": [],
    }
    try:
        report["production_freeze_before"] = freeze_status()
        if not report["production_freeze_before"]["stable"]:
            raise ValueError("frozen input drift")
        closure = construct(source)
        report["source_differences"] = verify_diff(closure)
        report["source_closure_sha256"] = closure["source_closure_sha256"]
        report["public_file_counts"] = {
            "before": len(closure["before"]),
            "after": len(closure["after"]),
        }
        inventory_path = output / "inventory.json"
        inventory_path.write_text(json.dumps(closure, indent=2) + "\n")
        report["inventory"] = {
            "path": str(inventory_path),
            "sha256": digest(inventory_path.read_bytes()),
        }
        audit = authorities()
        report["authority_audit_sha256"] = AUDIT_HASH
        oracle = output / "profile-oracle.cpp"
        oracle.write_bytes(
            checked(
                META / "profile-oracle.cpp", audit["available_artifacts"]["profile_oracle_sha256"]
            )
        )
        guard = output / "profile-guard.cpp"
        guard.write_text(GUARD)
        layout = output / "layout.cpp"
        layout.write_text(GUARD + LAYOUT)
        expected = json.loads((META / "profiles.json").read_text())
        mapflags = validate_flags("map", (META / "map-cppflags.txt").read_text())
        for frontend, compiler in [("gcc", GCC), ("clang", CLANG)]:
            execute(report, output, frontend + "-version", [compiler, "--version"], output)
            for role in ["common", "login", "char", "map"]:
                prefix = frontend + "-" + role
                flags = validate_flags(role, (META / (role + "-cppflags.txt")).read_text())
                base = [compiler] + flags + ["-I" + str(source)] + includes(source)
                execute(
                    report, output, prefix + "-guard", base + ["-fsyntax-only", str(guard)], output
                )
                macros = execute(
                    report, output, prefix + "-macros", base + ["-E", "-dM", str(guard)], output
                )
                relevant = {
                    line.split()[1]: " ".join(line.split()[2:])
                    for line in macros.splitlines()
                    if line.startswith("#define ")
                    and (
                        line.split()[1].startswith("PACKET")
                        or line.split()[1] in ["RENEWAL", "PRERE"]
                    )
                }
                executable = output / (prefix + "-oracle")
                execute(
                    report,
                    output,
                    prefix + "-build",
                    base + [str(oracle), "-o", str(executable)],
                    output,
                )
                measured = json.loads(
                    execute(report, output, prefix + "-run", [str(executable)], output)
                )
                report["profiles"].append(
                    {
                        "frontend": frontend,
                        "role": role,
                        "measured": measured,
                        "matches_installed": measured == expected[role],
                        "macros": relevant,
                    }
                )
                if measured != expected[role]:
                    raise ValueError("installed profile mismatch " + prefix)
            negative = (
                [compiler]
                + mapflags
                + ["-I" + str(SOURCE)]
                + includes(SOURCE)
                + ["-fsyntax-only", str(oracle)]
            )
            execute(report, output, frontend + "-original-negative", negative, output, expected=1)
            if (
                "incorrect compiled profile"
                not in (output / (frontend + "-original-negative.stderr")).read_text()
            ):
                raise ValueError("negative control did not reach profile guard")
            binary = output / (frontend + "-layout")
            base = [compiler] + mapflags + ["-I" + str(source)] + includes(source)
            execute(
                report,
                output,
                frontend + "-layout-build",
                base + [str(layout), "-o", str(binary)],
                output,
            )
            observation = json.loads(
                execute(report, output, frontend + "-layout-run", [str(binary)], output)
            )
            report["layouts"].append({"frontend": frontend, "measured": observation})
        report["original_negative_control"] = True
        execute(
            report,
            output,
            "gcc-full-clif-syntax",
            [GCC]
            + mapflags
            + includes(source)
            + [
                "-fsyntax-only",
                "-MD",
                "-MF",
                str(output / "gcc-clif.d"),
                str(source / "src/map/clif.cpp"),
            ],
            source / "src/map",
        )
        for name in ["clif_emotion", "clif_name", "clif_sitting"]:
            command = (
                [CLANG]
                + mapflags
                + includes(source)
                + [
                    "-fsyntax-only",
                    "-MD",
                    "-MF",
                    str(output / (name + ".d")),
                    str(source / "src/map/clif.cpp"),
                    "-Xclang",
                    "-ast-dump=json",
                    "-Xclang",
                    "-ast-dump-filter=" + name,
                ]
            )
            text = execute(report, output, "clang-" + name, command, source / "src/map")
            report["asts"][name] = ast_counts(text, name)
        report["production_freeze"] = freeze_status()
        if not report["production_freeze"]["stable"] or inventory(source) != closure["after"]:
            raise ValueError("post-execution source drift")
        report["verdict"] = "VALIDATED_BOUNDED_PROFILE_LAYOUT_AST"
    except Exception as error:
        report["issues"].append(str(error))
    finally:
        report["production_freeze"] = freeze_status()
        report["limitations"] = [
            "Not recovered exact binary-build source or fully expanded historical compiler environment",
            "Reduced retained role flags plus explicit reviewed include paths; no host /usr/include fallback",
            "No full catalogue, identity/dataflow sender admission, generator acceptance or gameplay/runtime integration",
            "Older GCC-preprocessed Clang bf16 incompatibility artifacts preserved unchanged",
        ]
        artifacts = {
            str(p): digest(p.read_bytes())
            for p in output.iterdir()
            if p.is_file() and p.name not in ["progress.json", "result.json"]
        }
        report["artifacts"] = artifacts
        result = output / "result.json"
        result.write_text(json.dumps(report, indent=2) + "\n")
        (Path(__file__).parent / "latest.json").write_text(
            json.dumps(
                {
                    "path": str(result),
                    "sha256": digest(result.read_bytes()),
                    "verdict": report["verdict"],
                },
                indent=2,
            )
            + "\n"
        )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    outcome = experiment()
    print(
        json.dumps(
            {
                "verdict": outcome["verdict"],
                "artifact_root": outcome["private_artifact_root"],
                "profiles": len(outcome["profiles"]),
                "layouts": len(outcome["layouts"]),
                "asts": outcome["asts"],
                "issues": outcome["issues"],
            },
            indent=2,
        )
    )
    raise SystemExit(0 if outcome["verdict"].startswith("VALIDATED") else 1)
