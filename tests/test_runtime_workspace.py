"""Fresh synthetic private fixtures; no engine, SQL or native execution."""

import errno
import importlib
import json
import os
import subprocess
import sys
from typing import NoReturn

import pytest

from robots.adapters import rathena_runtime
from robots.adapters import runtime_tree_sync as tree_sync
from robots.adapters.rathena_runtime_io import BundleRejectedError, write_at
from robots.adapters.runtime_workspace import PublicationReceipt, RuntimeWorkspace
from tests.test_rathena_runtime import synthetic_config


def test_real_pinned_bundle_is_managed_and_admission_denied(tmp_path):
    module = importlib.import_module("robots.adapters.runtime_workspace")
    root = tmp_path / "workspace"
    workspace = module.RuntimeWorkspace(root)
    try:
        receipt = workspace.publish_world("test", json.dumps(synthetic_config()).encode())
        assert receipt.phase == "committed"
        assert receipt.launchable is False
        assert receipt.admission_state == "denied"
        manifest = json.loads((root / "worlds/test/manifest.json").read_bytes())
        assert receipt.manifest == manifest
        assert manifest["npc_files"] > 100
        assert manifest["source_nar"] == "sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI="
        config = (root / "worlds/test/conf/inter_athena.conf").read_text()
        assert f"login_server_pw: {synthetic_config()['db_password']}\n" in config
        entries = list((root / "worlds/test").rglob("*"))
        assert len(entries) <= tree_sync.MAX_ENTRIES
        assert (
            max(len(path.relative_to(root / "worlds/test").parts) for path in entries)
            <= tree_sync.MAX_DEPTH
        )
        assert [row.event for row in workspace.records] == ["intent", "prepared", "committed"]
    finally:
        workspace.close()
    assert workspace.cleanup_status == "released_observed"


@pytest.fixture
def synthetic_builder(monkeypatch):
    """Narrow seam only; NOT an actual complete pinned-bundle production claim."""
    module = importlib.import_module("robots.adapters.runtime_workspace")
    monkeypatch.setattr(rathena_runtime, "public_assets", lambda: ({}, {}))
    monkeypatch.setattr(module, "public_assets", lambda: ({}, {}))

    def build(world, destination, raw):
        destination.mkdir(mode=0o700)
        manifest = {"world": world, "launchable": False, "synthetic_fixture": True}
        fd = os.open(destination, module.DIRECTORY_FLAGS)
        try:
            write_at(fd, "manifest.json", json.dumps(manifest).encode())
            write_at(fd, "synthetic-private", raw)
        finally:
            os.close(fd)
        return manifest

    monkeypatch.setattr(rathena_runtime, "build_from_bytes", build)
    return module


@pytest.fixture
def managed(tmp_path, synthetic_builder):
    workspace = synthetic_builder.RuntimeWorkspace(tmp_path / "workspace")
    try:
        yield workspace
    finally:
        workspace.close()


def publish(workspace: RuntimeWorkspace, world: str = "test") -> PublicationReceipt:
    return workspace.publish_world(world, json.dumps(synthetic_config()).encode())


@pytest.mark.parametrize("world", [None, "../test", "prod-", "prod-" + "a" * 15, "TEST"])
def test_invalid_world_before_intent_or_allocation(managed, world):
    with pytest.raises(BundleRejectedError):
        publish(managed, world)
    assert managed.records == ()
    assert not list((managed._root_path / "staging").iterdir())
    assert publish(managed).admission_state == "denied"


def test_builtin_types_rejected_before_overrides(managed):
    class HostileString(str):
        def encode(self, *_args, **_kwargs) -> NoReturn:
            pytest.fail("string subtype method invoked")

    with pytest.raises(BundleRejectedError):
        publish(managed, HostileString("test"))
    with pytest.raises(BundleRejectedError):
        managed.publish_world("test", bytearray(b"{}"))
    assert managed.records == ()


@pytest.mark.parametrize("raw", [b"{}", b"\xff", b"{", b"[]"])
def test_invalid_config_before_side_effects(managed, monkeypatch, raw):
    def forbidden():
        pytest.fail("invalid private input reached assets")

    monkeypatch.setattr("robots.adapters.runtime_workspace.public_assets", forbidden)
    with pytest.raises(BundleRejectedError):
        managed.publish_world("test", raw)
    assert managed.records == ()
    assert not list((managed._root_path / "staging").iterdir())


def test_missing_assets_before_intent(managed, monkeypatch):
    origin = FileNotFoundError(errno.ENOENT, "synthetic missing public dependency")

    def missing():
        raise origin

    monkeypatch.setattr("robots.adapters.runtime_workspace.public_assets", missing)
    with pytest.raises(FileNotFoundError) as caught:
        publish(managed)
    assert caught.value is origin
    assert managed.records == ()
    assert not list((managed._root_path / "staging").iterdir())
    with pytest.raises(BundleRejectedError):
        publish(managed)


@pytest.mark.parametrize("kind", ["empty", "sentinel", "symlink"])
def test_unknown_existing_root_never_adopted(tmp_path, synthetic_builder, kind):
    root = tmp_path / "workspace"
    foreign = tmp_path / "foreign"
    foreign.mkdir(mode=0o700)
    (foreign / "sentinel").write_bytes(b"synthetic foreign sentinel")
    if kind == "symlink":
        root.symlink_to(foreign, target_is_directory=True)
    else:
        root.mkdir(mode=0o700)
        if kind == "sentinel":
            (root / "sentinel").write_bytes(b"synthetic sentinel")
    with pytest.raises(FileExistsError):
        synthetic_builder.RuntimeWorkspace(root)
    assert (foreign / "sentinel").read_bytes() == b"synthetic foreign sentinel"
    if kind == "sentinel":
        assert (root / "sentinel").read_bytes() == b"synthetic sentinel"
    elif kind == "empty":
        assert list(root.iterdir()) == []


def test_reached_collision_preserves_existing_target_and_foreign_sentinel(managed, monkeypatch):
    module = importlib.import_module("robots.adapters.runtime_workspace")
    final = managed._root_path / "worlds/test"
    final.mkdir(mode=0o700)
    (final / "sentinel").write_bytes(b"synthetic existing target")
    foreign = managed._root_path.parent / "foreign"
    foreign.mkdir(mode=0o700)
    (foreign / "sentinel").write_bytes(b"synthetic unrelated")
    reached: list[int] = []
    real = module.move_directory_noreplace

    def rename(*args):
        reached.append(os.fstat(args[0]).st_ino)
        return real(*args)

    monkeypatch.setattr(module, "move_directory_noreplace", rename)
    with pytest.raises(FileExistsError) as caught:
        publish(managed)
    assert caught.value.errno == errno.EEXIST
    assert len(reached) == 1
    assert (final / "sentinel").read_bytes() == b"synthetic existing target"
    assert (foreign / "sentinel").read_bytes() == b"synthetic unrelated"
    assert managed.phase == "uncertain"
    assert list((managed._root_path / "staging").glob("*/test/manifest.json"))


def test_synthetic_builder_unmarked_failure_is_never_published(managed, monkeypatch):
    real = rathena_runtime.build_from_bytes
    origin = OSError(errno.EIO, "synthetic unmarked builder fault")

    def failed(*args):
        real(*args)
        raise origin

    monkeypatch.setattr(rathena_runtime, "build_from_bytes", failed)
    with pytest.raises(OSError, match=r".") as caught:
        publish(managed)
    assert caught.value is origin
    assert not (managed._root_path / "worlds/test").exists()
    staged = list((managed._root_path / "staging").glob("*/test"))
    assert len(staged) == 1
    assert (staged[0] / "manifest.json").is_file()
    assert not (staged[0] / "INCOMPLETE").exists()
    assert managed.phase == "quarantined"


@pytest.mark.parametrize(
    "target", ["tree", "transaction", "worlds", "candidate", "staging", "root", "journal"]
)
def test_reached_sync_faults_preserve_origin_and_deny(managed, monkeypatch, target):
    module = importlib.import_module("robots.adapters.runtime_workspace")
    real_sync = os.fsync
    origin = OSError(errno.EIO, "synthetic sync fault")
    reached: list[int] = []

    def sync(fd):
        current_phase = managed.phase
        hit = target == "tree" and current_phase == "intent" and "candidate" in managed._handles
        if target in managed._handles and current_phase == "renamed":
            hit = fd == managed._fd(target)
        if target == "journal" and current_phase == "renamed":
            hit = fd == managed._journal.cleanup_ownership.descriptor
        if hit and not reached:
            reached.append(os.fstat(fd).st_ino)
            raise origin
        return real_sync(fd)

    monkeypatch.setattr(module.os, "fsync", sync)
    with pytest.raises(OSError, match=r".") as caught:
        publish(managed)
    assert caught.value is origin
    assert caught.value.errno == errno.EIO
    assert len(reached) == 1
    final = managed._root_path / "worlds/test"
    assert final.exists() is (target != "tree")
    assert managed.phase == ("quarantined" if target == "tree" else "uncertain")
    assert not any(row.event == "committed" for row in managed.records)
    with pytest.raises(BundleRejectedError):
        publish(managed, "debug")


@pytest.mark.parametrize("entry", ["root", "staging", "worlds", "manager.lock", "PROJECT"])
def test_changed_managed_bindings_detected_under_lock(managed, entry):
    root = managed._root_path
    if entry == "root":
        root.rename(root.parent / "detached")
        root.mkdir(mode=0o700)
    else:
        selected = root / entry
        selected.rename(root / f"detached-{entry}")
        if entry in {"staging", "worlds"}:
            selected.mkdir(mode=0o700)
        else:
            selected.write_bytes(b"synthetic replacement")
            selected.chmod(0o600)
    with pytest.raises(BundleRejectedError):
        publish(managed)
    assert not (root / "worlds/test").exists()
    assert managed.phase == "quarantined"


def test_changed_candidate_binding_denied_before_rename(managed, monkeypatch):
    module = importlib.import_module("robots.adapters.runtime_workspace")
    real = module.sync_private_tree

    def sync(fd):
        real(fd)
        tx = managed._current[0]
        path = managed._root_path / "staging" / tx / "test"
        path.rename(path.parent / "detached")
        path.mkdir(mode=0o700)

    monkeypatch.setattr(module, "sync_private_tree", sync)
    with pytest.raises(BundleRejectedError):
        publish(managed)
    assert not (managed._root_path / "worlds/test").exists()


def test_actual_second_process_flock_excludes_until_normal_close(managed):
    script = (
        "import fcntl,os,sys; fd=os.open(sys.argv[1],os.O_RDWR); "
        "\ntry: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)"
        "\nexcept BlockingIOError: sys.exit(7)"
        "\nfinally: os.close(fd)"
    )
    path = str(managed._root_path / "manager.lock")
    blocked = subprocess.run([sys.executable, "-c", script, path], check=False, timeout=10)
    assert blocked.returncode == 7
    managed.close()
    released = subprocess.run([sys.executable, "-c", script, path], check=False, timeout=10)
    assert released.returncode == 0


def test_restart_refuses_committed_history_without_recovery(managed, synthetic_builder):
    receipt = publish(managed)
    root = managed._root_path
    managed.close()
    with pytest.raises(FileExistsError):
        synthetic_builder.RuntimeWorkspace(root)
    assert receipt.admission_state == "denied"
    assert (root / "worlds/test/manifest.json").is_file()


def test_multiple_worlds_have_internal_distinct_transactions(managed):
    one = publish(managed)
    two = publish(managed, "debug")
    assert one.transaction_id != two.transaction_id
    assert one.generation == two.generation
    assert one.session_id == two.session_id
    assert one.admission_state == two.admission_state == "denied"


@pytest.mark.parametrize("release_first", [False, True])
def test_postcommit_cleanup_error_preserves_origin_and_no_receipt(
    managed, monkeypatch, release_first
):
    module = importlib.import_module("robots.adapters.runtime_workspace")
    real = os.close
    origin = OSError(errno.EIO, "synthetic close fault")
    reached: list[int] = []
    pending = []

    def close(fd):
        if managed.phase == "committed" and fd == managed._fd("candidate") and not reached:
            reached.append(fd)
            if release_first:
                real(fd)
            else:
                pending.append(fd)
            raise origin
        return real(fd)

    monkeypatch.setattr(module.os, "close", close)
    with pytest.raises(OSError, match=r".") as caught:
        publish(managed)
    assert caught.value is origin
    assert len(reached) == 1
    assert managed.phase == "quarantined"
    assert (managed._root_path / "worlds/test/manifest.json").is_file()
    assert managed.cleanup_status == ("active" if release_first else "unresolved")
    assert [row.event for row in managed.records] == [
        "intent",
        "prepared",
        "committed",
        "quarantined",
    ]
    with pytest.raises(BundleRejectedError):
        publish(managed, "debug")
    managed.close()
    for fd in pending:
        real(fd)  # Harness-owned cleanup only; manager never retries.


def test_primary_builder_origin_survives_nonlocal_cleanup_diagnostic(managed, monkeypatch):
    module = importlib.import_module("robots.adapters.runtime_workspace")
    real_build = rathena_runtime.build_from_bytes
    real_after = module.JournalCleanupOwnership._after_attempt
    origin = OSError(errno.EIO, "synthetic builder primary")
    diagnostic = KeyboardInterrupt("synthetic cleanup diagnostic")

    def build(*args):
        real_build(*args)
        raise origin

    def after(row):
        observed, error = real_after(row)
        if row.descriptor == managed._fd("transaction"):
            return observed, diagnostic
        return observed, error

    monkeypatch.setattr(rathena_runtime, "build_from_bytes", build)
    monkeypatch.setattr(module.JournalCleanupOwnership, "_after_attempt", after)
    with pytest.raises(OSError, match="synthetic builder primary") as caught:
        publish(managed)
    assert caught.value is origin
    assert managed.phase == "quarantined"


def test_constructor_sync_failure_preserves_origin_and_closes_handles(
    tmp_path, synthetic_builder, monkeypatch
):
    origin = OSError(errno.EIO, "synthetic initializer fault")
    real = os.fsync
    reached: list[int] = []

    def sync(fd):
        if os.path.basename(os.readlink(f"/proc/self/fd/{fd}")) == "staging":
            reached.append(fd)
            raise origin
        return real(fd)

    monkeypatch.setattr(synthetic_builder.os, "fsync", sync)
    with pytest.raises(OSError, match=r".") as caught:
        synthetic_builder.RuntimeWorkspace(tmp_path / "workspace")
    assert caught.value is origin
    assert len(reached) == 1
    with pytest.raises(OSError, match=r".") as absent:
        os.fstat(reached[0])
    assert absent.value.errno == errno.EBADF


def test_prepared_journal_sync_failure_keeps_final_absent(managed, monkeypatch):
    real = os.fsync
    origin = OSError(errno.EIO, "synthetic prepared journal sync")
    reached: list[int] = []

    def sync(fd):
        journal = managed._journal.cleanup_ownership.descriptor
        if fd == journal and managed.phase == "intent" and "candidate" in managed._handles:
            reached.append(os.fstat(fd).st_ino)
            raise origin
        return real(fd)

    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(OSError, match="journal I/O failed") as caught:
        publish(managed)
    assert caught.value is origin
    assert len(reached) == 1
    assert not (managed._root_path / "worlds/test").exists()
    assert managed.phase == "quarantined"


def test_actual_rename_then_callback_failure_is_uncertain(managed, monkeypatch):
    module = importlib.import_module("robots.adapters.runtime_workspace")
    real = module.move_directory_noreplace
    origin = OSError(errno.EIO, "synthetic after kernel rename")
    reached: list[int] = []

    def rename(*args):
        real(*args)
        reached.append(os.fstat(args[2]).st_ino)
        raise origin

    monkeypatch.setattr(module, "move_directory_noreplace", rename)
    with pytest.raises(OSError, match="synthetic after kernel rename") as caught:
        publish(managed)
    assert caught.value is origin
    assert len(reached) == 1
    assert managed.phase == "uncertain"
    assert (managed._root_path / "worlds/test/manifest.json").is_file()


def test_final_manifest_changed_during_rename_cannot_deliver_receipt(managed, monkeypatch):
    module = importlib.import_module("robots.adapters.runtime_workspace")
    real = module.move_directory_noreplace

    def rename(*args):
        real(*args)
        (managed._root_path / "worlds/test/manifest.json").write_bytes(b"{}")

    monkeypatch.setattr(module, "move_directory_noreplace", rename)
    with pytest.raises(BundleRejectedError):
        publish(managed)
    assert managed.phase == "uncertain"
    assert not any(row.event == "committed" for row in managed.records)


def test_replaced_registration_same_bytes_is_detected(managed):
    marker = managed._root_path / "PROJECT"
    raw = marker.read_bytes()
    marker.rename(marker.parent / "detached-project")
    marker.write_bytes(raw)
    marker.chmod(0o600)
    with pytest.raises(BundleRejectedError):
        publish(managed)
    assert managed.phase == "quarantined"


def test_retained_current_handle_rebinding_denied(managed):
    foreign = managed._root_path.parent / "foreign"
    foreign.mkdir(mode=0o700)
    (foreign / "sentinel").write_bytes(b"synthetic untouched")
    borrowed = os.open(foreign, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.dup2(borrowed, managed._fd("worlds"))
    finally:
        os.close(borrowed)
    with pytest.raises(BundleRejectedError):
        publish(managed)
    assert managed.phase == "quarantined"
    assert (foreign / "sentinel").read_bytes() == b"synthetic untouched"


def test_failed_journal_constructor_retains_unresolved_ownership(
    tmp_path, synthetic_builder, monkeypatch
):
    origin = OSError(errno.EIO, "synthetic journal constructor primary")
    real_close = os.close
    pending: list[int] = []

    def read(_journal):
        raise origin

    def close(fd):
        if os.path.basename(os.readlink(f"/proc/self/fd/{fd}")) == "publication-journal.jsonl":
            pending.append(fd)
            raise OSError(errno.EIO, "synthetic unresolved journal close")
        return real_close(fd)

    monkeypatch.setattr(synthetic_builder.PublicationJournal, "_read", read)
    monkeypatch.setattr(os, "close", close)
    try:
        with pytest.raises(OSError, match="journal I/O failed") as caught:
            synthetic_builder.RuntimeWorkspace(tmp_path / "workspace")
        assert caught.value is origin
        ownership = caught.value.__dict__["workspace_cleanup_ownership"]
        assert any(row.status == "unresolved" for row in ownership)
        assert len(pending) == 1
    finally:
        for fd in pending:
            real_close(fd)  # Explicit fixture process cleanup, never manager retry.


@pytest.mark.parametrize("target", ["lock", "journal"])
def test_normal_close_error_retains_ownership_without_retry(managed, monkeypatch, target):
    real = os.close
    fd = managed._fd("lock") if target == "lock" else managed._journal.cleanup_ownership.descriptor
    origin = KeyboardInterrupt("synthetic close interruption")
    reached: list[int] = []

    def close(owned):
        if owned == fd:
            reached.append(owned)
            raise origin
        return real(owned)

    monkeypatch.setattr(os, "close", close)
    with pytest.raises(KeyboardInterrupt, match="synthetic close interruption") as caught:
        managed.close()
    assert caught.value is origin
    assert managed.cleanup_status == "unresolved"
    assert managed.phase == "quarantined"
    assert os.fstat(fd).st_uid == os.geteuid()
    managed.close()
    assert len(reached) == 1
    with pytest.raises(BundleRejectedError):
        publish(managed)
    real(fd)  # Harness-controlled cleanup; manager must not retry.
