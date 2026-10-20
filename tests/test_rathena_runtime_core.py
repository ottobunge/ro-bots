"""Actual pinned ELFs; only source-proven pre-initialization offline modes.

Build the separate tiny flake first. No skip, server, database or world fallback.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

ROLES = ("login", "char", "map")
REVISION = "e985006171d2eb320ee512a653f4c83aea3d81b6"
EXPECTED_PROFILE = {
    "packetver": 20180704,
    "main": 20180704,
    "renewal": False,
    "re": False,
    "zero": False,
    "obfuscation": False,
    "pincode": True,
}


def review_path() -> Path:
    return Path(__file__).resolve().parents[1] / "run/reviews/native-runtime-root.json"


def package_path() -> Path:
    configured = os.environ.get("RATHENA_RUNTIME_CORE")
    if configured:
        package = Path(configured)
    else:
        review = review_path()
        assert review.is_file(), "actual runtime-core package artifact is missing"
        package = Path(json.loads(review.read_text())["package"])
    assert package.is_dir(), "actual runtime-core package artifact is missing"
    return package


def strace_path() -> str:
    found = shutil.which("strace")
    if found:
        return found
    return str(json.loads(review_path().read_text())["strace"])


def source_proof(package: Path) -> None:
    evidence = package / "share/rathena-runtime-core"
    core = (evidence / "core-start.cpp").read_text()
    start = core.index("int32 Core::start(")
    early = core.index("runtime_root_offline_cli", start)
    refusal = core.index("return 78; // unconditional runtime-start refusal", early)
    for initialization in (
        "this->set_status( e_core_status::CORE_INITIALIZING )",
        "malloc_init();",
        "display_title();",
        "Sql_Init();",
        "db_init();",
        "timer_init();",
        "socket_init();",
        "this->initialize( argc, argv )",
    ):
        assert early < refusal < core.index(initialization, start)
    assert "return runtime_root::diagnostic(argv[2], SERVER_NAME);" in core[early:refusal]
    assert "SERVER_NAME = runtime_root::server_basename(argv[0]);" in core[early:refusal]
    assert "chdir(pwd)" not in core
    helper = (evidence / "runtime-root.hpp").read_text()
    assert "fchdir(root.get())" in helper
    assert "info.st_uid == geteuid()" in helper
    assert "(info.st_mode & 07777) == 0700" in helper
    assert "O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW" in helper
    assert helper.index("literal_absolute(path)") < helper.index('::open("/"')
    assert "!same_inode(path_info, evidence)" in helper


def binary_path(package: Path, role: str) -> Path:
    source_proof(package)
    binary = package / "libexec/rathena" / f"{role}-server"
    assert binary.read_bytes()[:4] == b"\x7fELF"
    assert os.access(binary, os.X_OK)
    return binary


def safe_env(cwd: Path) -> dict[str, str]:
    return {"PATH": "/no-search", "HOME": str(cwd), "LC_ALL": "C"}


def invoke(
    role: str, args: list[str], cwd: Path, spelling: str = "absolute-store"
) -> subprocess.CompletedProcess[str]:
    binary = binary_path(package_path(), role)
    argv0 = {
        "absolute-store": str(binary),
        "controlled-absolute": f"/controlled/not-the-root/{role}-server",
        "controlled-basename": f"{role}-server",
    }[spelling]
    return subprocess.run(
        [argv0, *args],
        executable=str(binary),
        cwd=cwd,
        env=safe_env(cwd),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


@pytest.fixture
def roots():
    with tempfile.TemporaryDirectory(prefix="runtime-core-", dir=os.environ["TMPDIR"]) as temp:
        base = Path(temp).resolve()
        root = base / "root"
        other = base / "different-cwd"
        root.mkdir(mode=0o700)
        other.mkdir(mode=0o700)
        yield root, other


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(
    "spelling", ["absolute-store", "controlled-absolute", "controlled-basename"]
)
def test_real_roles_use_explicit_root_not_argv0(roots, role, spelling):
    root, other = roots
    expected = root.stat()
    result = invoke(role, ["--check-runtime-root", str(root)], other, spelling)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    proof = json.loads(result.stdout)
    assert proof == {
        "server_name": f"{role}-server",
        "root_bound": True,
        "cwd_matches": True,
        "relative_matches": True,
        "startup_blocked": True,
        "device": expected.st_dev,
        "inode": expected.st_ino,
    }
    assert str(root) not in result.stdout + result.stderr
    assert list(root.iterdir()) == list(other.iterdir()) == []


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("option", ["--help", "--version"])
def test_help_version_are_preinit_offline_only(roots, role, option):
    root, other = roots
    result = invoke(role, [option], other)
    assert result.returncode == 0
    assert result.stderr == ""
    assert REVISION in result.stdout
    assert "All native startup remains blocked" in result.stdout
    assert list(root.iterdir()) == list(other.iterdir()) == []


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--serve"],
        ["--run"],
        ["--start"],
        ["unknown"],
        ["--help", "extra"],
        ["--check-runtime-root"],
        ["--check-runtime-root", "root", "extra"],
        ["--runtime-root", "root"],
        ["--serve", "--check-runtime-root", "<valid-root>"],
        ["--run", "--check-runtime-root", "<valid-root>"],
        ["--start", "--check-runtime-root", "<valid-root>"],
        ["--check-runtime-root", "<valid-root>", "--serve"],
    ],
)
def test_every_other_command_stays_unconditionally_blocked(roots, role, args):
    root, other = roots
    args = [str(root) if arg == "<valid-root>" else arg for arg in args]
    result = invoke(role, args, other)
    assert result.returncode == 78
    assert result.stdout == ""
    assert "runtime-start executor is blocked" in result.stderr
    assert list(root.iterdir()) == list(other.iterdir()) == []


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(
    "variant",
    ["relative", "dot", "dotdot", "double", "trailing", "nonascii", "control", "missing", "slash"],
)
def test_raw_path_spelling_rejected_before_initialization(roots, role, variant):
    root, other = roots
    paths = {
        "relative": "root",
        "dot": str(root.parent) + "/./root",
        "dotdot": str(root.parent) + "/root/../root",
        "double": str(root.parent) + "//root",
        "trailing": str(root) + "/",
        "nonascii": str(root) + "é",
        "control": str(root) + "\n",
        "missing": str(root.parent / "missing"),
        "slash": "/",
    }
    result = invoke(role, ["--check-runtime-root", paths[variant]], other)
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr == "rAthena: runtime root rejected; startup remains blocked.\n"
    assert list(root.iterdir()) == list(other.iterdir()) == []


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("mode", [0o000, 0o500, 0o750, 0o755, 0o1700, 0o2700])
def test_nonprivate_modes_rejected(roots, role, mode):
    root, other = roots
    root.chmod(mode)
    try:
        result = invoke(role, ["--check-runtime-root", str(root)], other)
        assert result.returncode == 2
        assert result.stdout == ""
    finally:
        root.chmod(0o700)


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("variant", ["leaf-symlink", "ancestor-symlink", "regular", "fifo"])
def test_nofollow_directory_only(roots, role, variant):
    root, other = roots
    bad = root.parent / "bad"
    if variant == "leaf-symlink":
        bad.symlink_to(root, target_is_directory=True)
    elif variant == "ancestor-symlink":
        bad.symlink_to(root.parent, target_is_directory=True)
        bad = bad / "root"
    elif variant == "regular":
        bad.touch(mode=0o700)
    else:
        os.mkfifo(bad, 0o700)
    result = invoke(role, ["--check-runtime-root", str(bad)], other)
    assert result.returncode == 2
    assert result.stdout == ""
    assert str(bad) not in result.stderr


def test_all_native_profile_oracles_use_actual_make_recipes():
    package = package_path()
    evidence = package / "share/rathena-runtime-core"
    profiles = json.loads((evidence / "profiles.json").read_text())
    assert profiles == dict.fromkeys(("common", *ROLES), EXPECTED_PROFILE)
    for role in ("common", *ROLES):
        flags = (evidence / f"{role}-cppflags.txt").read_text()
        recipe = (evidence / f"{role}-compile-recipe.txt").read_text()
        assert "-DPACKETVER=20180704" in flags
        assert "-DPRERE" in flags
        assert "-c " in recipe
        assert all(flag in recipe for flag in flags.split())
    metadata = json.loads((evidence / "package.json").read_text())
    assert metadata["revision"] == REVISION
    assert metadata["startup_blocked"] is True
    assert metadata["diagnostic_scope"] == "filesystem-root-only"
    assert not (package / "share/rathena-runtime-core/conf").exists()
    assert not (package / "share/rathena-runtime-core/db").exists()


@pytest.mark.parametrize("role", ROLES)
def test_native_diagnostic_trace_has_fchdir_without_network_or_writes(roots, role):
    root, other = roots
    binary = binary_path(package_path(), role)
    trace = root.parent / "syscalls.txt"
    result = subprocess.run(
        [
            strace_path(),
            "-qq",
            "-o",
            str(trace),
            "-e",
            "trace=%network,chdir,fchdir,openat,mkdir,mkdirat,unlink,unlinkat,rename,renameat",
            str(binary),
            "--check-runtime-root",
            str(root),
        ],
        cwd=other,
        env=safe_env(other),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = trace.read_text().splitlines()
    assert sum(line.startswith("fchdir(") for line in lines) == 1
    forbidden = (
        "socket(",
        "connect(",
        "bind(",
        "listen(",
        "send",
        "recv",
        "chdir(",
        "mkdir",
        "unlink",
        "rename",
    )
    assert not any(line.startswith(forbidden) for line in lines)
    assert not any(flag in line for line in lines for flag in ("O_WRONLY", "O_RDWR", "O_CREAT"))
    assert list(root.iterdir()) == list(other.iterdir()) == []


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("operation", ["openat", "fchdir", "getcwd", "close"])
def test_native_syscall_failures_refuse_without_initialization(roots, role, operation):
    root, other = roots
    binary = binary_path(package_path(), role)
    trace = root.parent / "faults.txt"
    # Calibrate against this real ELF's trace: library-loader call counts differ
    # from native root handling. Inject only into an observed helper syscall.
    when = "1"
    if operation in {"openat", "close"}:
        baseline = root.parent / "baseline.txt"
        calibrated = subprocess.run(
            [
                strace_path(),
                "-qq",
                "-o",
                str(baseline),
                "-e",
                "trace=openat,close",
                str(binary),
                "--check-runtime-root",
                str(root),
            ],
            cwd=other,
            env=safe_env(other),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert calibrated.returncode == 0
        assert calibrated.stderr == ""
        lines = baseline.read_text().splitlines()
        native_start = next(index for index, line in enumerate(lines) if "O_DIRECTORY" in line)
        target = (
            native_start
            if operation == "openat"
            else next(
                index
                for index in range(native_start, len(lines))
                if lines[index].startswith("close(")
            )
        )
        when = str(sum(line.startswith(f"{operation}(") for line in lines[: target + 1]))
    result = subprocess.run(
        [
            strace_path(),
            "-qq",
            "-o",
            str(trace),
            "-e",
            "trace=%network,openat,close,fchdir,getcwd",
            "-e",
            f"inject={operation}:error=EIO:when={when}",
            str(binary),
            "--check-runtime-root",
            str(root),
        ],
        cwd=other,
        env=safe_env(other),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert "INJECTED" in trace.read_text(), "fault must reach an actual native syscall"
    assert result.returncode == 2, result.stderr
    assert result.stdout == ""
    assert result.stderr == "rAthena: runtime root rejected; startup remains blocked.\n"
    assert not any(
        line.startswith(("socket(", "connect(", "bind(")) for line in trace.read_text().splitlines()
    )


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("replace", [False, True])
def test_root_renamed_or_replaced_during_fchdir_never_reports_success(roots, role, replace):
    root, other = roots
    binary = binary_path(package_path(), role)
    trace = root.parent / "race.txt"
    process = subprocess.Popen(
        [
            strace_path(),
            "-qq",
            "-o",
            str(trace),
            "-e",
            "trace=fchdir",
            "-e",
            "inject=fchdir:delay_exit=1s",
            str(binary),
            "--check-runtime-root",
            str(root),
        ],
        cwd=other,
        env=safe_env(other),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    moved = root.parent / "renamed-root"
    try:
        deadline = time.monotonic() + 5
        observed = False
        while time.monotonic() < deadline and process.poll() is None:
            children = Path(f"/proc/{process.pid}/task/{process.pid}/children").read_text().split()
            for child in children:
                try:
                    observed = os.readlink(f"/proc/{child}/cwd") == str(root)
                except FileNotFoundError:
                    continue
                if observed:
                    break
            if observed:
                break
            time.sleep(0.005)
        assert observed, "must observe real child fchdir before the root substitution"
        root.rename(moved)
        if replace:
            root.mkdir(mode=0o700)
        stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == 2
        assert stdout == ""
        assert stderr == "rAthena: runtime root rejected; startup remains blocked.\n"
        assert "DELAYED" in trace.read_text()
        assert list(moved.iterdir()) == list(other.iterdir()) == []
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
