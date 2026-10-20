"""Conditional passive CLI. Import/assembly never opens a native session.

Default execution requires parent-bound helper review and executor snapshot.
Synthetic injected tests do not authorize this adapter's operational effects.
"""

import fcntl
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/otto/dev/ro-bots")
HERE = Path(__file__).parent
SCRATCH = HERE.parent
OUTPUT = ROOT / "run/reviews/playing-mvp-passive-skill-context.json"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("module refused")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def private_json(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        meta = os.fstat(fd)
        if not (
            stat.S_ISREG(meta.st_mode)
            and meta.st_uid == os.getuid()
            and stat.S_IMODE(meta.st_mode) == 0o600
        ):
            raise ValueError("private permissions refused")
        with os.fdopen(fd, "r", closefd=False) as handle:
            return json.load(handle)
    finally:
        os.close(fd)


def load_private(loc):
    config, manifest = (private_json(loc[k]) for k in ("config", "host_manifest"))
    if (manifest.get("login_host"), manifest.get("login_port")) != ("127.0.0.1", 16900):
        raise ValueError("login endpoint refused")
    rows, pairs = manifest["accounts"], config["exact_pairs"]
    if (
        not isinstance(rows, list)
        or not isinstance(pairs, dict)
        or len(rows) != 2
        or len(pairs) != 2
    ):
        raise ValueError("fixture count refused")
    if {r["persona_id"] for r in rows} != set(pairs) or len(
        {r["persona_id"] for r in rows}
    ) != 2:
        raise ValueError("persona identity refused")
    for values in pairs.values():
        if (
            not isinstance(values, (list, tuple))
            or len(values) != 2
            or any(type(v) is not int or v <= 1 for v in values)
        ):
            raise ValueError("account identity refused")
    if any(len({pair[i] for pair in pairs.values()}) != 2 for i in (0, 1)):
        raise ValueError("account identity refused")
    for row in rows:
        if any(
            type(row.get(k)) is not str or not row[k]
            for k in ("persona_id", "account", "password", "char_name", "pincode")
        ):
            raise ValueError("required private value refused")
        pin = row["pincode"]
        if len(pin) != 4 or any(d not in "0123456789" for d in pin):
            raise ValueError("PIN shape refused")
    return rows, pairs


class FixtureLock:
    """One attempt per FD; no retry after uncertain release/reused descriptor."""

    def __init__(self, path):
        self.path, self.fd = Path(path), None
        self.quarantined = False

    def acquire(self):
        if self.fd is not None or self.quarantined:
            raise ValueError("lock already held")
        fd = os.open(
            self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600
        )
        self.fd = fd
        try:
            meta = os.fstat(fd)
            if not (
                stat.S_ISREG(meta.st_mode)
                and meta.st_uid == os.getuid()
                and stat.S_IMODE(meta.st_mode) == 0o600
            ):
                raise ValueError("lock permissions refused")
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.fd = None
            try:
                os.close(fd)
            except BaseException:
                self.fd = fd
                self.quarantined = (
                    True  # Expose unresolved ownership; never auto-retry.
                )
            raise

    def release(self):
        if self.quarantined:
            raise ValueError("lock release unresolved; retry refused")
        fd = self.fd
        if fd is None:
            raise ValueError("lock not held")
        origin, tb = None, None
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except BaseException as error:
            origin, tb = error, error.__traceback__
        try:
            os.close(fd)
        except BaseException:
            # This descriptor may already be released/reused. Retain its name
            # for manual ownership resolution, never automatically retry it.
            self.quarantined = True
            if origin is None:
                raise
        else:
            self.fd = None
        if origin is not None:
            raise origin.with_traceback(tb)


def native_factory(row, *, bot_class=None):
    if bot_class is None:
        sys.path.insert(0, str(ROOT / "spikes/003-clientless-limbs"))
        from client import BotClient

        bot_class = BotClient
    wire = bot_class(
        row["account"],
        row["password"],
        char_name=row["char_name"],
        login_ip="127.0.0.1",
        login_port=16900,
        pincode=row["pincode"],
        create_char=False,
        verbose=False,
    )
    wire.log = lambda message: None
    return wire


def proof_valid(proof):
    return (
        all(
            proof.get(k) is True
            for k in (
                "passed",
                "read_only",
                "exact_two_fixture_ownership_verified",
                "both_fixtures_offline",
            )
        )
        and type(proof.get("all_online_character_count")) is int
        and proof["all_online_character_count"] == 0
    )


def helper_proof(path, timeout, guard, *, runner=subprocess.run):
    guard()
    # subprocess.run kills/waits for its direct child on TimeoutExpired. Descendant
    # subprocesses are not universally closed by that contract: timeout is failure.
    result = runner(
        [sys.executable, "-B", str(path)],
        cwd=ROOT,
        env=dict(os.environ, PYTHONOPTIMIZE="0", PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("read-only helper refused")
    proof = json.loads(result.stdout)
    if not proof_valid(proof):
        raise ValueError("parsed offline proof refused")
    guard()
    return proof


def save_primary(report):
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")


def assemble_native():
    if sys.flags.optimize != 0:
        raise ValueError("optimized native execution refused")
    guards = load_module("completion_guards", HERE / "guards.py")
    guards.guard()  # Must fail before private auth read/lock/client construction.
    loc = json.loads(
        (ROOT / "run/reviews/scheduled-native-host-private-location.json").read_text()
    )
    rows, pairs = load_private(loc)
    lock = FixtureLock(
        Path(loc["private_directory"]).parent / "native-fixture-observer.lock"
    )
    core = load_module("completion_probe", HERE / "probe.py")
    sys.path.insert(0, str(ROOT / "src"))

    def preflight():
        # Revalidate private inputs under exclusive ownership before helper effects.
        fresh_rows, fresh_pairs = load_private(loc)
        if fresh_rows != rows or fresh_pairs != pairs:
            raise ValueError("private inputs drifted")
        return helper_proof(guards.helper_paths()["live"], 45, guards.guard)

    return core, dict(
        rows=rows,
        pairs=pairs,
        factory=native_factory,
        lock=lock,
        preflight=preflight,
        readback=lambda: helper_proof(
            guards.helper_paths()["baseline"], 35, guards.guard
        ),
        save=save_primary,
        guard=guards.guard,
    )


def main(*, assemble=None, pretty=print):
    if assemble is None:
        assemble = assemble_native
    try:
        if sys.flags.optimize != 0:
            raise ValueError("optimized native execution refused")
        core, args = assemble()
        report = core.run(**args)
    except Exception as error:
        # Admission failures have no native session outcome to invent.
        pretty(
            json.dumps(
                {
                    "passed": False,
                    "errors": [{"stage": "admission", "type": type(error).__name__}],
                }
            )
        )
        return 2
    try:
        pretty(json.dumps(report, indent=2))
    except Exception:
        return 2
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
