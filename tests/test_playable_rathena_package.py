"""Pinned runnable variant: safe diagnostics only; never execute a valid run mode."""

import hashlib
import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
FLAKE = REPO / "nix/playable-world"
SOURCE = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source")
ROLES = ("login", "char", "map")
REVISION = "e985006171d2eb320ee512a653f4c83aea3d81b6"


def patch_source(destination: Path) -> str:
    assert (FLAKE / "apply-runtime-root.py").is_file(), "new runnable source adapter is missing"
    (destination / "src/common").mkdir(parents=True)
    (destination / "src/custom").mkdir(parents=True)
    for name in ("src/common/core.cpp", "src/custom/defines_post.hpp"):
        (destination / name).write_bytes((SOURCE / name).read_bytes())
    result = subprocess.run(
        ["python3", str(FLAKE / "apply-runtime-root.py")],
        cwd=destination,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return (destination / "core-start.cpp").read_text()


def test_explicit_mode_reaches_unchanged_native_startup(tmp_path):
    core = patch_source(tmp_path)
    original = (SOURCE / "src/common/core.cpp").read_text()
    assert core[core.index("\tmalloc_init();") :] == original[original.index("\tmalloc_init();") :]
    begin = core.index("int32 Core::start(")
    bind = core.index("runtime_root::prepare(argc, argv, SERVER_NAME)", begin)
    assert (
        "if (runtime_result != -1) return runtime_result;"
        in core[bind : core.index("malloc_init();", bind)]
    )
    for anchor in (
        "this->set_status( e_core_status::CORE_INITIALIZING )",
        "malloc_init();",
        "Sql_Init();",
        "timer_init();",
        "socket_init();",
        "this->initialize( argc, argv )",
    ):
        assert bind < core.index(anchor, begin)
    assert "chdir(pwd)" not in core
    assert "unconditional runtime-start refusal" not in core


def test_runtime_option_removed_without_replacing_original_parser():
    helper = (FLAKE / "runtime-root.hpp").read_text()
    assert "static int prepare(int& argc, char** argv" in helper
    assert "argv[i] = argv[i + 2]" in helper
    assert "argc -= 2;" in helper
    assert "bind_runtime_root(requested, evidence)" in helper
    assert "known_name(server_name)" in helper
    assert "return -1; // original Core startup continues" in helper


def test_public_package_image_contract():
    flake = (FLAKE / "flake.nix").read_text()
    assert 'pname = "rathena-playable";' in flake
    assert "pkgs.dockerTools.buildLayeredImage" in flake
    assert 'User = "10000:10000";' in flake
    assert 'Volumes = { "/world" = {}; };' in flake
    assert "Cmd = [];" in flake
    assert "runtime_selection_required" in flake
    assert (FLAKE / "flake.lock").read_bytes() == (
        REPO / "nix/runtime-core/flake.lock"
    ).read_bytes()


def test_source_drift_refused_before_writes(tmp_path):
    (tmp_path / "src/common").mkdir(parents=True)
    source = tmp_path / "src/common/core.cpp"
    source.write_bytes((SOURCE / "src/common/core.cpp").read_bytes() + b"\n// drift\n")
    before = source.read_bytes()
    result = subprocess.run(
        ["python3", str(FLAKE / "apply-runtime-root.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0
    assert "pinned Core source drift" in result.stderr
    assert source.read_bytes() == before
    assert not (tmp_path / "core-start.cpp").exists()


def package_path() -> Path:
    configured = os.environ.get("RATHENA_PLAYABLE_PACKAGE")
    if configured:
        package = Path(configured)
    else:
        review = REPO / "run/reviews/playable-rathena-package.json"
        assert review.is_file(), "actual new package artifact is missing"
        package = Path(json.loads(review.read_text())["package"])
    assert package.is_dir(), "actual new package artifact is missing"
    return package


def safe_source_proof(package: Path) -> None:
    evidence = package / "share/rathena-playable"
    original = (SOURCE / "src/common/core.cpp").read_text()
    core = (evidence / "core-start.cpp").read_text()
    assert core[core.index("\tmalloc_init();") :] == original[original.index("\tmalloc_init();") :]
    begin = core.index("int32 Core::start(")
    prepare = core.index("runtime_root::prepare(argc, argv, SERVER_NAME)", begin)
    assert prepare < core.index("this->get_status()", begin) < core.index("malloc_init();", begin)
    assert (
        "if (runtime_result != -1) return runtime_result;"
        in core[prepare : core.index("this->get_status()", begin)]
    )
    assert (evidence / "runtime-root.hpp").read_bytes() == (FLAKE / "runtime-root.hpp").read_bytes()


def invoke(
    role: str, args: list[str], cwd: Path, argv0: str | None = None
) -> subprocess.CompletedProcess[str]:
    package = package_path()
    safe_source_proof(package)
    binary = package / "libexec/rathena" / f"{role}-server"
    assert binary.read_bytes()[:4] == b"\x7fELF"
    return subprocess.run(
        [argv0 or str(binary), *args],
        executable=str(binary),
        cwd=cwd,
        env={"PATH": "/no-search", "HOME": str(cwd), "LC_ALL": "C"},
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


@pytest.fixture
def roots(tmp_path):
    base = tmp_path.resolve()
    root, other = base / "root", base / "different-cwd"
    root.mkdir(mode=0o700)
    other.mkdir(mode=0o700)
    return root, other


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("spelling", ["store", "absolute-other", "basename"])
def test_all_real_roles_explicit_diagnostic_root(roots, role, spelling):
    root, other = roots
    argv0 = {
        "store": None,
        "absolute-other": f"/not-the-runtime/{role}-server",
        "basename": f"{role}-server",
    }[spelling]
    result = invoke(role, ["--check-runtime-root", str(root)], other, argv0)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    proof = json.loads(result.stdout)
    assert proof == {
        "server_name": f"{role}-server",
        "root_bound": True,
        "cwd_matches": True,
        "relative_matches": True,
        "startup_blocked": True,
        "device": root.stat().st_dev,
        "inode": root.stat().st_ino,
    }
    assert str(root) not in result.stdout
    assert list(root.iterdir()) == list(other.iterdir()) == []


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("option", ["--help", "--version"])
def test_real_help_version_before_initialization(roots, role, option):
    root, other = roots
    result = invoke(role, [option], other)
    assert result.returncode == 0
    assert result.stderr == ""
    assert REVISION in result.stdout
    assert "Native startup requires --runtime-root ABS" in result.stdout
    assert list(root.iterdir()) == list(other.iterdir()) == []


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(
    "case",
    [
        "none",
        "unknown",
        "missing",
        "duplicate",
        "equals",
        "help-extra",
        "help-run",
        "check-missing",
        "check-extra",
        "check-run",
        "check-unknown",
        "version-run",
    ],
)
def test_invalid_runtime_flags_never_initialize(roots, role, case):
    root, other = roots
    args = {
        "none": [],
        "unknown": ["--unknown"],
        "missing": ["--runtime-root"],
        "duplicate": ["--runtime-root", str(root), "--runtime-root", str(root)],
        "equals": ["--runtime-root=" + str(root)],
        "help-extra": ["--help", "extra"],
        "help-run": ["--runtime-root", str(root), "--help"],
        "check-missing": ["--check-runtime-root"],
        "check-extra": ["--check-runtime-root", str(root), "extra"],
        "check-run": ["--runtime-root", str(root), "--check-runtime-root", str(root)],
        "check-unknown": ["--runtime-root", str(root), "--check-unknown"],
        "version-run": ["--version", "--runtime-root", str(root)],
    }[case]
    result = invoke(role, args, other)
    assert result.returncode == (78 if case in ("none", "unknown") else 2)
    assert result.stdout == ""
    assert "startup remains blocked" in result.stderr
    assert str(root) not in result.stderr
    assert list(root.iterdir()) == list(other.iterdir()) == []


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("option", ["--runtime-root", "--check-runtime-root"])
@pytest.mark.parametrize(
    "variant",
    [
        "relative",
        "dot",
        "dotdot",
        "double",
        "trailing",
        "missing",
        "slash",
        "mode",
        "symlink",
        "nonascii",
        "control",
    ],
)
def test_invalid_root_rejected_before_native_startup(roots, role, option, variant):
    root, other = roots
    paths = {
        "relative": "root",
        "dot": str(root.parent) + "/./root",
        "dotdot": str(root) + "/../root",
        "double": str(root.parent) + "//root",
        "trailing": str(root) + "/",
        "missing": str(root.parent / "missing"),
        "slash": "/",
        "mode": str(root),
        "symlink": str(root.parent / "alias"),
        "nonascii": str(root) + "é",
        "control": str(root) + "\n",
    }
    if variant == "mode":
        root.chmod(0o750)
    if variant == "symlink":
        (root.parent / "alias").symlink_to(root)
    result = invoke(role, [option, paths[variant]], other)
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == "rAthena: runtime root rejected; startup remains blocked.\n"
    assert list(root.iterdir()) == list(other.iterdir()) == []


@pytest.mark.parametrize("role", ROLES)
def test_unknown_basename_refused(roots, role):
    _root, other = roots
    result = invoke(role, ["--help"], other, "unknown-server")
    assert result.returncode == 2
    assert result.stdout == ""
    assert "basename rejected" in result.stderr


def test_actual_compiled_profile():
    profiles = json.loads((package_path() / "share/rathena-playable/profiles.json").read_text())
    expected = {
        "packetver": 20180704,
        "main": 20180704,
        "renewal": False,
        "re": False,
        "zero": False,
        "obfuscation": False,
        "pincode": True,
    }
    assert set(profiles) == {"common", *ROLES}
    assert all(profile == expected for profile in profiles.values())


def image_path() -> Path:
    configured = os.environ.get("RATHENA_PLAYABLE_IMAGE")
    if configured:
        image = Path(configured)
    else:
        review = REPO / "run/reviews/playable-rathena-package.json"
        assert review.is_file(), "actual new image archive is missing"
        image = Path(json.loads(review.read_text())["image"])
    assert image.is_file(), "actual new image archive is missing"
    return image


def test_actual_docker_archive_contract():
    with tarfile.open(image_path(), "r:gz") as archive:
        manifest_stream = archive.extractfile("manifest.json")
        assert manifest_stream is not None
        manifest = json.load(manifest_stream)
        assert len(manifest) == 1
        config_stream = archive.extractfile(manifest[0]["Config"])
        assert config_stream is not None
        config = json.load(config_stream)["config"]
        assert config["User"] == "10000:10000"
        assert config["WorkingDir"] == "/world"
        assert config["Volumes"] == {"/world": {}}
        assert config["Entrypoint"] == [str(package_path() / "libexec/rathena/login-server")]
        assert config["Cmd"] == []
        assert config["Labels"]["org.opencontainers.image.revision"] == REVISION
        assert config["Labels"]["org.rathena.profile"] == "MAIN-pre-re-20180704"
        closure = set(
            subprocess.check_output(
                ["nix-store", "--query", "--requisites", str(package_path())], text=True
            ).splitlines()
        )
        roots = set()
        for layer_name in manifest[0]["Layers"]:
            layer_stream = archive.extractfile(layer_name)
            assert layer_stream is not None
            with tarfile.open(fileobj=layer_stream, mode="r|") as layer:
                for member in layer:
                    name = member.name.removeprefix("./").lstrip("/")
                    parts = Path(name).parts
                    assert not any(
                        part
                        in {
                            "conf",
                            "npc",
                            "sql-files",
                            "robots",
                            ".git",
                            ".env",
                            "reviews",
                        }
                        for part in parts
                    )
                    assert not name.startswith(("home/", "run/", "tmp/", "root/"))
                    if len(parts) >= 3 and parts[:2] == ("nix", "store"):
                        roots.add("/" + "/".join(parts[:3]))
        assert roots == closure


def test_public_native_evidence_hashes():
    package = package_path()
    review_file = REPO / "run/reviews/playable-rathena-package.json"
    assert review_file.is_file()
    evidence = json.loads(review_file.read_text())
    for name, record in evidence["package_files"].items():
        raw = (package / name).read_bytes()
        assert len(raw) == record["size"]
        assert hashlib.sha256(raw).hexdigest() == record["sha256"]
