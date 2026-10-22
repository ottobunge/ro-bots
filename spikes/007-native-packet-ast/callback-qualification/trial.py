#!/usr/bin/env python3
"""Offline bounded callback qualification trial; no server link or execution."""

import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

REPO = Path("/home/otto/dev/ro-bots")
SCRATCH = Path("/home/otto/.hermes/cache/scratch")
BASE = SCRATCH / "native-profile-replay-s2jdj4rn/public-source"
BO = BASE.parent / "output"
RESULT_SHA = "602c856e8e368fe767ff6b54704416818dc7939a5c6606f0fb6af6b49c2e71ac"
CLIF_SHA = "0b1db098158c240b090c6edb8417978ba495957c8a2df4cd9a0ab4cb39884ac5"
BODY_SHA = "cc5199666ee7cedc35d14ad724695eacfed9cfccf525c452325b0103136758d5"
GCC = "/nix/store/j1938gsbvbhkyz4kbmvjk56r479mkw3s-gcc-wrapper-16.2.0/bin/g++"
CLANG = "/nix/store/2msw5nclhpsm80z65dqmjiv8kkras989-clang-wrapper-21.1.8/bin/clang++"
REPLACEMENTS = (
    (b"\tblock_list *src_bl;", b"\tconst block_list *src_bl;"),
    (b"\tunsigned char *buf;", b"\tconst unsigned char *buf;"),
    (
        b"buf = va_arg(ap,unsigned char*);",
        b"buf = static_cast<const unsigned char*>(va_arg(ap,const void*));",
    ),
    (b"va_arg(ap,block_list*)", b"va_arg(ap,const block_list*)"),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    result = {}
    for name in ("src", "3rdparty"):
        for p in sorted((root / name).rglob("*")):
            if p.is_symlink():
                raise ValueError("symlink in public source")
            if p.is_file():
                result[str(p.relative_to(root))] = sha(p.read_bytes())
    return dict(sorted(result.items()))


def closure(inv):
    return sha(json.dumps(inv, sort_keys=True).encode())


def transform(data):
    if len(data) != 775974 or sha(data) != CLIF_SHA:
        raise ValueError("baseline file hash/size drift")
    start, end = 10749, 12589
    if sha(data[start:end]) != BODY_SHA:
        raise ValueError("bounded callback body hash drift")
    body = data[start:end]
    for old, new in REPLACEMENTS:
        if body.count(old) != 1:
            raise ValueError("callback unique anchor drift")
        body = body.replace(old, new)
    patched = data[:start] + body + data[end:]
    assert patched[:start] == data[:start] and patched[start + len(body) :] == data[end:]
    return patched


def nodes(node):
    yield node
    for child in node.get("inner", []):
        yield from nodes(child)


def json_stream(text):
    dec, pos, roots = json.JSONDecoder(), 0, []
    while pos < len(text):
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos == len(text):
            break
        obj, pos = dec.raw_decode(text, pos)
        roots.append(obj)
    return roots


def freeze():
    expected = json.loads((SCRATCH / "native-profile-replay-parent-freeze.json").read_text())
    actual = {p: sha((REPO / p).read_bytes()) for p in expected}
    if actual != expected:
        raise ValueError("parent frozen files drift")
    return actual


def main():
    os.umask(0o077)
    root = Path(tempfile.mkdtemp(prefix="callback-qualification-", dir=SCRATCH))
    out = root / "output"
    out.mkdir()
    trial = root / "public-source"
    commands, issues = [], []
    before, oldcode = None, {}
    report = {
        "schema": "native-ast-callback-qualification-experiment-v1",
        "artifact_root": str(root),
        "scope": "scratch-only pointer qualification/retrieval experiment; no server build, deployment or effects",
        "sink_adopted": False,
        "runtime_integration": False,
        "binary_equivalence": False,
        "sender_admission": False,
        "all_six_milestones_open": True,
        "commands": commands,
        "issues": issues,
    }

    def put(name, data):
        p = out / name
        p.write_bytes(data.encode() if isinstance(data, str) else data)
        return p

    def run(name, args, timeout=45):
        so, se = out / (name + ".stdout"), out / (name + ".stderr")
        start = time.monotonic()
        with so.open("wb") as stdout, se.open("wb") as stderr:
            proc = subprocess.run(
                args, cwd=out, stdout=stdout, stderr=stderr, timeout=timeout, check=False
            )
        commands.append(
            {
                "name": name,
                "argv": args,
                "cwd": str(out),
                "exit": proc.returncode,
                "seconds": round(time.monotonic() - start, 3),
                "stdout": str(so),
                "stderr": str(se),
                "stdout_sha256": sha(so.read_bytes()),
                "stderr_sha256": sha(se.read_bytes()),
            }
        )
        return proc.returncode

    try:
        report["freeze_before"] = freeze()
        oldcode = {
            str(p.relative_to(REPO)): sha(p.read_bytes())
            for area in ("profile-replay", "sender-proof", "compiler", "bindings", "toolchain")
            for p in (REPO / "spikes/007-native-packet-ast" / area).rglob("*")
            if p.is_file() and "__pycache__" not in str(p)
        }
        report["old_spike_code_before"] = oldcode
        assert sha((BO / "result.json").read_bytes()) == RESULT_SHA
        reviewed = json.loads((BO / "result.json").read_text())
        assert (
            sha(Path(reviewed["inventory"]["path"]).read_bytes()) == reviewed["inventory"]["sha256"]
        )
        inv = json.loads(Path(reviewed["inventory"]["path"]).read_text())["after"]
        before = inventory(BASE)
        assert before == inv and len(before) == 3206
        assert closure(before) == reviewed["source_closure_sha256"]
        report["baseline_inventory_equal"] = True
        report["baseline_source_closure_sha256"] = reviewed["source_closure_sha256"]
        report["baseline_result_sha256"] = RESULT_SHA
        for file, expected in (
            (
                "native-ast-real-sink-audit.json",
                "6269acb7714e59533c8da9cc8bd0edd679c6e64eb5b4ac0cd6a8bf07095c6a38",
            ),
            (
                "native-ast-varargs-contract.json",
                "e3d539fa3d9692c3c94f15d817ae3bbde1b89921ddf2365ce2268fc805041be8",
            ),
        ):
            assert sha((REPO / "run/reviews" / file).read_bytes()) == expected
        trial.mkdir()
        for name in ("src", "3rdparty"):
            shutil.copytree(BASE / name, trial / name)
        assert inventory(trial) == before
        original = (trial / "src/map/clif.cpp").read_bytes()
        from test_trial import qualification_contract

        try:
            qualification_contract(original)
        except AssertionError as exc:
            put("RED.log", "Expected pristine source contract failure: " + str(exc) + "\n")
        else:
            raise AssertionError("RED unexpectedly passed")
        patched = transform(original)
        qualification_contract(patched)
        (trial / "src/map/clif.cpp").write_bytes(patched)
        put("GREEN.log", "Qualified source contract passed after exactly four substitutions.\n")
        # Denial checks run before any compiler invocation and never write bad inputs.
        denial = []
        for data in (
            original + b" ",
            original.replace(b"\tblock_list *src_bl;", b"\tblock_list *other;"),
            original.replace(b"type = va_arg(ap,int32);", b"type = va_arg(ap,long);"),
        ):
            try:
                transform(data)
            except ValueError as exc:
                denial.append(str(exc))
            else:
                raise AssertionError("drift accepted")
        report["prewrite_precompile_denials"] = denial
        assert (
            run(
                "unittest-GREEN",
                [
                    "python3",
                    "-B",
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    str(Path(__file__).parent),
                    "-p",
                    "test_trial.py",
                    "-v",
                ],
            )
            == 0
        )
        report["bounded_anchor_counts"] = {
            old.decode(): original[10749:12589].count(old) for old, new in REPLACEMENTS
        }
        after = inventory(trial)
        changed = [p for p in before if before[p] != after.get(p)]
        assert changed == ["src/map/clif.cpp"] and before.keys() == after.keys()
        put("inventory-before.json", json.dumps(before, sort_keys=True, indent=2))
        put("inventory-after.json", json.dumps(after, sort_keys=True, indent=2))
        put(
            "callback.diff",
            "".join(
                difflib.unified_diff(
                    original.decode().splitlines(True),
                    patched.decode().splitlines(True),
                    fromfile="baseline/src/map/clif.cpp",
                    tofile="trial/src/map/clif.cpp",
                )
            ),
        )
        report["source_difference"] = {
            "changed_paths": changed,
            "before_file_count": len(before),
            "after_file_count": len(after),
            "clif_before_sha256": sha(original),
            "clif_after_sha256": sha(patched),
            "callback_before_sha256": sha(original[10749:12589]),
            "callback_after_sha256": sha(patched[10749 : 12589 + len(patched) - len(original)]),
            "trial_source_closure_sha256": closure(after),
            "trial_closure_hash_encoding": "sha256(json.dumps(sorted path/hash mapping, sort_keys=True).encode())",
            "four_substitutions_only": True,
        }
        byname = {c["name"]: c for c in reviewed["commands"]}

        def rebase(args):
            return [a.replace(str(BASE), str(trial)).replace(str(BO), str(out)) for a in args]

        syntax = rebase(byname["gcc-full-clif-syntax"]["command"])
        report["gcc_whole_TU_exit"] = run("gcc-full-clif-syntax", syntax)
        clang = [CLANG] + syntax[1:]
        clang[clang.index("-MF") + 1] = str(out / "clang-clif.d")
        report["clang_whole_TU_exit"] = run("clang-full-clif-syntax", clang)
        pristine_clang = [a.replace(str(trial), str(BASE)) for a in clang]
        pristine_clang[pristine_clang.index("-MF") + 1] = str(out / "pristine-clang-clif.d")
        report["pristine_clang_whole_TU_exit"] = run(
            "clang-pristine-full-clif-syntax", pristine_clang
        )
        pristine_diag = (
            (out / "clang-pristine-full-clif-syntax.stderr")
            .read_text()
            .replace(str(BASE), "<SOURCE>")
        )
        patched_diag = (
            (out / "clang-full-clif-syntax.stderr").read_text().replace(str(trial), "<SOURCE>")
        )
        report["clang_diagnostics_unchanged"] = pristine_diag == patched_diag
        assert report[
            "clang_diagnostics_unchanged"
        ], "new diagnostic retained; scope expansion forbidden"
        import shlex

        dependencies = {}
        for depname in ("gcc-clif.d", "clang-clif.d"):
            text = (out / depname).read_text().replace("\\\n", "")
            dependencies[depname] = {
                p: sha(Path(p).read_bytes())
                for p in shlex.split(text.split(":", 1)[1])
                if Path(p).is_file()
            }
        put(
            "complete-TU-dependency-hashes.json", json.dumps(dependencies, indent=2, sort_keys=True)
        )
        report["TU_dependency_counts"] = {k: len(v) for k, v in dependencies.items()}
        report["compiler_wrapper_hashes"] = {p: sha(Path(p).read_bytes()) for p in (GCC, CLANG)}
        astcmd = clang + ["-Xclang", "-ast-dump=json", "-Xclang", "-ast-dump-filter=clif_send"]
        report["active_AST_exit"] = run("clang-callback-AST", astcmd)
        roots = json_stream((out / "clang-callback-AST.stdout").read_text())
        selected = {
            r["name"]: r
            for r in roots
            if r.get("kind") == "FunctionDecl"
            and r.get("name") in ("clif_send_sub", "clif_send")
            and any(n.get("kind") == "CompoundStmt" for n in r.get("inner", []))
        }
        sub, send = selected["clif_send_sub"], selected["clif_send"]
        va = [n for n in nodes(sub) if n.get("kind") == "VAArgExpr"]
        locals_ = {
            n.get("name"): n.get("type")
            for n in nodes(sub)
            if n.get("kind") == "VarDecl" and n.get("name") in ("buf", "src_bl")
        }
        args_ = []
        for n in nodes(send):
            if n.get("kind") == "CallExpr" and n.get("inner"):
                refs = [x.get("referencedDecl", {}).get("name") for x in nodes(n["inner"][0])]
                if "map_foreachinallarea" in refs:
                    args_.append(n)
        casts = [
            n
            for n in nodes(sub)
            if n.get("kind") == "CXXStaticCastExpr"
            and n.get("type", {}).get("qualType") == "const unsigned char *"
        ]
        assert [n["type"]["qualType"] for n in va] == [
            "const void *",
            "int32",
            "const block_list *",
            "int32",
        ]
        assert (
            locals_["buf"]["qualType"] == "const unsigned char *"
            and locals_["src_bl"]["qualType"] == "const block_list *"
        )
        assert len(casts) == 1
        forwarding = [[x.get("type") for x in n["inner"][-4:]] for n in args_]
        assert forwarding and all(
            [x["qualType"] for x in f] == ["const void *", "int32", "const block_list *", "int"]
            for f in forwarding
        )
        report["active_types"] = {
            "callback_signature": sub["type"],
            "retrievals": [n["type"] for n in va],
            "locals": locals_,
            "AREA_forwarding_slots": forwarding,
            "const_byteview_static_casts": len(casts),
            "AST_ids_invocation_local": True,
        }
        put(
            "active-types.json",
            json.dumps(
                {
                    "retrieval_nodes": va,
                    "byteview_cast_nodes": casts,
                    "forwarding_call_nodes": args_,
                    "locals": locals_,
                },
                indent=2,
            ),
        )
        for name in ("profile-guard.cpp", "profile-oracle.cpp", "layout.cpp"):
            shutil.copyfile(BO / name, out / name)
        report["unchanged_oracle_hashes"] = {
            n: sha((out / n).read_bytes())
            for n in ("profile-guard.cpp", "profile-oracle.cpp", "layout.cpp")
        }
        assert run("gcc-map-guard", rebase(byname["gcc-map-guard"]["command"])) == 0
        for name in ("gcc-map-build", "gcc-map-run", "gcc-layout-build", "gcc-layout-run"):
            assert run(name, rebase(byname[name]["command"])) == 0
        assert (out / "gcc-layout-run.stdout").read_bytes() == Path(
            byname["gcc-layout-run"]["stdout"]
        ).read_bytes()
        assert (out / "gcc-map-run.stdout").read_bytes() == Path(
            byname["gcc-map-run"]["stdout"]
        ).read_bytes()
        report["profile_and_layout_identical"] = True
        macros = clang[: clang.index("-fsyntax-only")] + [
            "-E",
            "-dM",
            str(trial / "src/map/clif.cpp"),
        ]
        assert run("clang-full-TU-macros", macros) == 0
        macro_lines = (out / "clang-full-TU-macros.stdout").read_text().splitlines()
        macro_names = (
            "PACKETVER",
            "PACKETVER_MAIN_NUM",
            "PACKETVER_RE_NUM",
            "PACKETVER_ZERO_NUM",
            "PRERE",
            "RENEWAL",
            "PACKET_OBFUSCATION",
            "PACKET_OBFUSCATION_WARN",
            "NULLPO_CHECK",
            "DEBUG",
            "SEND_SHORTLIST",
            "AREA_SIZE",
            "nullpo_ret",
        )
        report["active_macros"] = {
            n: next(
                (
                    l
                    for l in macro_lines
                    if l.startswith("#define " + n + " ") or l.startswith("#define " + n + "(")
                ),
                "ABSENT",
            )
            for n in macro_names
        }
        audit = json.loads((REPO / "run/reviews/native-ast-real-sink-audit.json").read_text())
        assert all(
            report["active_macros"][k] == audit["profile"]["full_clif_TU_macro_values"][k]
            for k in macro_names
        )
        # Source-extracted enum, real configured int32 alias; no real callback/FIFO simulation.
        h = (trial / "src/map/clif.hpp").read_text()
        start = h.index("enum send_target : uint8_t {")
        enum = h[start : h.index("};", start) + 2]
        put("send-target-enum.hpp", enum + "\n")
        probe = """#include <common/cbasetypes.hpp>
#include <cstdarg>
#include <cstring>
#include <cstdio>
#include <type_traits>
#include "send-target-enum.hpp"
struct block_list;
static_assert(std::is_same_v<int32,int>);
static_assert(std::is_same_v<decltype(+AREA),int>);
static_assert(!std::is_same_v<const void*,unsigned char*>);
static_assert(!std::is_same_v<const block_list*,block_list*>);
int witness(int marker, ...) {
  va_list ap; va_start(ap, marker);
  const unsigned char* buf = static_cast<const unsigned char*>(va_arg(ap,const void*));
  int32 len = va_arg(ap,int32);
  const block_list* bl = va_arg(ap,const block_list*);
  int32 target = va_arg(ap,int32);
  va_end(ap);
  static_assert(std::is_same_v<decltype(buf),const unsigned char*>);
  unsigned char dest[7] = {};
  const unsigned char expected[7] = {0xc0,0,1,2,3,4,5};
  if (len != 7 || bl != nullptr || target != AREA) return 1;
  std::memcpy(dest,buf,7);
  if (std::memcmp(dest,expected,7)) return 2;
  std::printf("defined isolated type-bridge: bytes=7 len=%d target=%d pointer=null copy=equal\\n",len,target);
  return 0;
}
int main() {
  const unsigned char bytes[7] = {0xc0,0,1,2,3,4,5};
  const void* buf = bytes;
  int32 len = 7;
  const block_list* bl = nullptr;
  send_target target = AREA;
  return witness(0,buf,len,bl,target);
}
"""
        put("type-bridge.cpp", probe)
        flags = rebase(byname["gcc-map-guard"]["command"])[1:]
        flags = flags[: flags.index("-fsyntax-only")]
        report["isolated_type_bridge"] = {}
        for compiler, label in ((GCC, "gcc"), (CLANG, "clang")):
            assert (
                run(
                    label + "-bridge-build",
                    [compiler]
                    + flags
                    + [str(out / "type-bridge.cpp"), "-o", str(out / (label + "-type-bridge"))],
                )
                == 0
            )
            assert run(label + "-bridge-run", [str(out / (label + "-type-bridge"))]) == 0
            report["isolated_type_bridge"][label] = (
                (out / (label + "-bridge-run.stdout")).read_text().strip()
            )
        report["original_negative_control"] = {
            "pointer_type_inequality_static_asserts": True,
            "baseline_preserved": True,
            "mismatched_varargs_executed": False,
        }
        report["bounded_resource_conditions"] = [
            "valid nonnull byte buffer of at least len readable bytes",
            "len fixed at seven and destination has seven writable bytes",
            "block_list pointer passed and retrieved as const block_list*, null compared only, never dereferenced",
            "real callback session/FIFO/recipient/allocator/locking conditions not exercised",
        ]
        report["unchanged_selected_caller_body"] = (
            sha(original[289393:289562])
            == "f1997d1169309f5c0e5ff58d3f8f11810984fe9f12e1f74e972c8ccec33b06f5"
        )
        report["verdict"] = (
            "VALIDATED_BOUNDED_QUALIFICATION_TYPES_TU_AND_LOCAL_BRIDGE"
            if report["gcc_whole_TU_exit"]
            == report["clang_whole_TU_exit"]
            == report["active_AST_exit"]
            == 0
            else "PARTIAL_CONST_CORRECTNESS_DIAGNOSTIC_RETAINED"
        )
    except Exception as exc:
        issues.append(type(exc).__name__ + ": " + str(exc))
        report["verdict"] = "PARTIAL"
    finally:
        try:
            report["freeze_after"] = freeze()
            report["freeze_unchanged"] = report.get("freeze_before") == report["freeze_after"]
            report["baseline_unchanged"] = inventory(BASE) == before
            report["old_spike_code_unchanged"] = all(
                sha((REPO / p).read_bytes()) == h for p, h in oldcode.items()
            )
        except Exception as exc:
            issues.append("final guard: " + str(exc))
            report["verdict"] = "INVALIDATED"
        report["unresolved"] = [
            "U2-U7 allocator/indirect SendFunc/unlock/recipient/libc obligations",
            "independent review and parent replay",
            "no packet receipt, real sink execution, gameplay, catalogue or deployment approval",
        ]
        report["artifacts"] = {
            str(p.relative_to(root)): sha(p.read_bytes())
            for p in sorted(out.rglob("*"))
            if p.is_file()
        }
        put("result.json", json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(
            json.dumps(
                {
                    "result": str(out / "result.json"),
                    "verdict": report["verdict"],
                    "issues": issues,
                    "whole_TU": [
                        report.get("gcc_whole_TU_exit"),
                        report.get("clang_whole_TU_exit"),
                    ],
                    "active_types": report.get("active_types"),
                },
                indent=2,
            )
        )
    return 0 if report["verdict"].startswith("VALIDATED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
