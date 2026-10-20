"""Separate offline callback variant; pinned public bytes are the authority."""

import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

REPO = Path(__file__).resolve().parents[1]
FLAKE = REPO / "nix/playable-callback-qualified"
SOURCE = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source")
BEFORE = "0b1db098158c240b090c6edb8417978ba495957c8a2df4cd9a0ab4cb39884ac5"
AFTER = "ace16f15be3b60f730522d620b73a68a9f2cc384016aadce9c985888aea9a1ac"
START, END = 10749, 12589


def corrector() -> Callable[[bytes], bytes]:
    path = FLAKE / "qualify-callback.py"
    assert path.is_file(), "guarded callback corrector is missing"
    spec = importlib.util.spec_from_file_location("callback_corrector", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sys, "dont_write_bytecode", True)
        spec.loader.exec_module(module)
    return cast(Callable[[bytes], bytes], module.transform)


def test_pinned_public_positive_control() -> None:
    original = (SOURCE / "src/map/clif.cpp").read_bytes()
    assert hashlib.sha256(original).hexdigest() == BEFORE
    result = corrector()(original)
    assert hashlib.sha256(result).hexdigest() == AFTER
    assert result[:START] == original[:START]
    assert result[END + len(result) - len(original) :] == original[END:]
    body = result[START : END + len(result) - len(original)]
    assert hashlib.sha256(body).hexdigest() == (
        "d85da9f09dba50ed8766ef8fc97887683a1ef10d260b424cc5e7ba3c809a4f4c"
    )
    assert body.count(b"va_arg(ap,int32)") == 2
    assert body.count(b"va_arg(ap,const void*)") == 1
    assert body.count(b"va_arg(ap,const block_list*)") == 1


@pytest.mark.parametrize("case", ["hash", "anchor", "extra", "integer", "zero", "corrected"])
def test_drift_is_refused_before_cli_write(tmp_path: Path, case: str) -> None:
    original = (SOURCE / "src/map/clif.cpp").read_bytes()
    malformed = {
        "hash": original + b" ",
        "anchor": original.replace(b"\tblock_list *src_bl;", b"\tblock_list *other;"),
        "extra": original[:END] + b"\tunsigned char *buf;" + original[END:],
        "integer": original.replace(b"type = va_arg(ap,int32);", b"type = va_arg(ap,long);"),
        "zero": b"",
        "corrected": corrector()(original),
    }[case]
    with pytest.raises(ValueError, match="drift"):
        corrector()(malformed)
    target = tmp_path / "src/map/clif.cpp"
    target.parent.mkdir(parents=True)
    target.write_bytes(malformed)
    result = subprocess.run(
        [sys.executable, "-B", str(FLAKE / "qualify-callback.py"), str(tmp_path)],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0
    assert target.read_bytes() == malformed


def test_cli_pinned_positive_control(tmp_path: Path) -> None:
    target = tmp_path / "src/map/clif.cpp"
    target.parent.mkdir(parents=True)
    target.write_bytes((SOURCE / "src/map/clif.cpp").read_bytes())
    result = subprocess.run(
        [sys.executable, "-B", str(FLAKE / "qualify-callback.py"), str(tmp_path)],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert hashlib.sha256(target.read_bytes()).hexdigest() == AFTER


def test_configured_manifest_reads_real_source(tmp_path: Path) -> None:
    script = FLAKE / "source-evidence.py"
    assert script.is_file(), "configured source manifest writer is missing"
    for area in ("src", "3rdparty"):
        (tmp_path / area).mkdir()
        (tmp_path / area / "public.hpp").write_bytes(b"public source\n")
    (tmp_path / "src/map").mkdir()
    original = (SOURCE / "src/map/clif.cpp").read_bytes()
    (tmp_path / "src/map/clif.cpp").write_bytes(corrector()(original))
    (tmp_path / "core-start.cpp").write_bytes(b"auxiliary core export\n")
    result = subprocess.run(
        [sys.executable, "-B", str(script)],
        cwd=tmp_path,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    manifest = json.loads((tmp_path / "configured-source.json").read_text())
    assert manifest["files"]["src/map/clif.cpp"] == AFTER
    assert len(manifest["files"]) == 3
    assert (
        manifest["auxiliary"]["core-start.cpp"]
        == hashlib.sha256(b"auxiliary core export\n").hexdigest()
    )


def qualified_package() -> Path:
    configured = os.environ.get("RATHENA_CALLBACK_QUALIFIED_PACKAGE")
    if configured:
        package = Path(configured)
    else:
        report = REPO / "run/reviews/native-callback-qualified-package-build.json"
        assert report.is_file(), "actual callback-qualified package evidence is missing"
        package = Path(json.loads(report.read_text())["package"])
    assert package.is_dir(), "actual callback-qualified package is missing"
    return package


def test_real_variant_source_profiles_and_artifacts() -> None:
    package = qualified_package()
    evidence = package / "share/rathena-playable-callback-qualified"
    metadata = json.loads((evidence / "package.json").read_text())
    assert metadata["variant"] == "callback-qualified"
    assert metadata["pointer_corrections"] == 4
    assert metadata["qualified_clif_sha256"] == AFTER
    assert hashlib.sha256((evidence / "qualified-clif.cpp").read_bytes()).hexdigest() == AFTER
    manifest = json.loads((evidence / "configured-source.json").read_text())
    assert manifest["files"]["src/map/clif.cpp"] == AFTER
    assert (
        manifest["auxiliary"]["core-start.cpp"]
        == hashlib.sha256((evidence / "core-start.cpp").read_bytes()).hexdigest()
    )
    expected = {
        "packetver": 20180704,
        "main": 20180704,
        "renewal": False,
        "re": False,
        "zero": False,
        "obfuscation": False,
        "pincode": True,
    }
    profiles = json.loads((evidence / "profiles.json").read_text())
    assert set(profiles) == {"common", "login", "char", "map"}
    assert all(profile == expected for profile in profiles.values())
    for name in ("apply-runtime-root.py", "profile-evidence.py", "runtime-root.hpp"):
        assert (evidence / name).read_bytes() == (REPO / "nix/playable-world" / name).read_bytes()
    for role in ("login", "char", "map"):
        assert (package / f"libexec/rathena/{role}-server").read_bytes()[:4] == b"\x7fELF"
    for role in profiles:
        flags = (evidence / f"{role}-cppflags.txt").read_text().split()
        assert "-DPACKETVER=20180704" in flags
        assert "-DPRERE" in flags
        assert not any(flag.startswith("-U") for flag in flags)


def early_source_proof(package: Path) -> None:
    evidence = package / "share/rathena-playable-callback-qualified"
    original = (SOURCE / "src/common/core.cpp").read_bytes()
    patched = (evidence / "core-start.cpp").read_bytes()
    tail = b"\tmalloc_init();"
    assert patched[patched.index(tail) :] == original[original.index(tail) :]
    start = patched.index(b"int32 Core::start(")
    prepare = patched.index(b"runtime_root::prepare(argc, argv, SERVER_NAME)", start)
    status = patched.index(b"this->get_status()", start)
    assert prepare < status < patched.index(tail, start)
    assert b"if (runtime_result != -1) return runtime_result;" in patched[prepare:status]
    assert (evidence / "runtime-root.hpp").read_bytes() == (FLAKE / "runtime-root.hpp").read_bytes()


@pytest.mark.parametrize("role", ["login", "char", "map"])
@pytest.mark.parametrize("mode", ["refusal", "diagnostic"])
def test_actual_early_only_diagnostics(tmp_path: Path, role: str, mode: str) -> None:
    package = qualified_package()
    early_source_proof(package)
    root = tmp_path / "empty-root"
    cwd = tmp_path / "cwd"
    root.mkdir(mode=0o700)
    cwd.mkdir(mode=0o700)
    args = [] if mode == "refusal" else ["--check-runtime-root", str(root)]
    result = subprocess.run(
        [str(package / f"libexec/rathena/{role}-server"), *args],
        cwd=cwd,
        env={"HOME": str(cwd), "LC_ALL": "C", "PATH": "/no-search"},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == (78 if mode == "refusal" else 0)
    if mode == "refusal":
        assert result.stdout == ""
        assert (
            result.stderr == "rAthena: explicit --runtime-root required; startup remains blocked.\n"
        )
    else:
        diagnostic = json.loads(result.stdout)
        assert diagnostic["startup_blocked"] is True
        assert diagnostic["root_bound"] is True
        assert diagnostic["inode"] == root.stat().st_ino
        assert diagnostic["device"] == root.stat().st_dev
        assert result.stderr == ""
    assert list(cwd.iterdir()) == []
    assert list(root.iterdir()) == []


def test_actual_evaluated_nix_source_is_pinned_public_only() -> None:
    result = subprocess.run(
        [
            "nix",
            "eval",
            "--offline",
            "--no-write-lock-file",
            "--raw",
            f"path:{FLAKE}#packages.x86_64-linux.playable-rathena.src.outPath",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout) == SOURCE
    for name in ("flake.lock", "apply-runtime-root.py", "profile-evidence.py", "runtime-root.hpp"):
        assert (FLAKE / name).read_bytes() == (REPO / "nix/playable-world" / name).read_bytes()
    allowed = {
        "flake.nix",
        "flake.lock",
        "apply-runtime-root.py",
        "profile-evidence.py",
        "runtime-root.hpp",
        "qualify-callback.py",
        "source-evidence.py",
    }
    assert {path.name for path in FLAKE.iterdir()} == allowed
    assert all(path.is_file() and not path.is_symlink() for path in FLAKE.iterdir())


@pytest.mark.parametrize("case", ["relative", "dot", "double", "trailing", "alias"])
def test_literal_cli_root_spelling_is_not_normalized(tmp_path: Path, case: str) -> None:
    target = tmp_path / "src/map/clif.cpp"
    target.parent.mkdir(parents=True)
    original = (SOURCE / "src/map/clif.cpp").read_bytes()
    target.write_bytes(original)
    alias = tmp_path.parent / (tmp_path.name + "-alias")
    alias.symlink_to(tmp_path, target_is_directory=True)
    tokens = {
        "relative": "public-source",
        "dot": str(tmp_path.parent) + "/./" + tmp_path.name,
        "double": str(tmp_path.parent) + "//" + tmp_path.name,
        "trailing": str(tmp_path) + "/",
        "alias": str(alias),
    }
    result = subprocess.run(
        [sys.executable, "-B", str(FLAKE / "qualify-callback.py"), tokens[case]],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0
    assert target.read_bytes() == original


@pytest.mark.parametrize("case", ["clif-drift", "missing-clif", "symlink"])
def test_manifest_refuses_before_output_write(tmp_path: Path, case: str) -> None:
    (tmp_path / "src/map").mkdir(parents=True)
    (tmp_path / "3rdparty").mkdir()
    original = (SOURCE / "src/map/clif.cpp").read_bytes()
    target = tmp_path / "src/map/clif.cpp"
    target.write_bytes(corrector()(original))
    (tmp_path / "core-start.cpp").write_bytes(b"private synthetic auxiliary\n")
    if case == "clif-drift":
        target.write_bytes(target.read_bytes() + b" ")
    elif case == "missing-clif":
        target.unlink()
    else:
        (tmp_path / "src/alias.hpp").symlink_to(target)
    result = subprocess.run(
        [sys.executable, "-B", str(FLAKE / "source-evidence.py")],
        cwd=tmp_path,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0
    assert not (tmp_path / "configured-source.json").exists()


def test_exact_reviewed_substitutions_and_unmodified_outer_scope() -> None:
    trial = REPO / "spikes/007-native-packet-ast/callback-qualification/trial.py"
    tree = ast.parse(trial.read_text())
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "REPLACEMENTS" for target in node.targets
        )
    )
    replacements = cast(tuple[tuple[bytes, bytes], ...], ast.literal_eval(assignment.value))
    assert len(replacements) == 4
    original = (SOURCE / "src/map/clif.cpp").read_bytes()
    body = original[START:END]
    for old, new in replacements:
        assert body.count(old) == 1
        body = body.replace(old, new)
    assert corrector()(original) == original[:START] + body + original[END:]
