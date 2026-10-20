import os
import stat
from collections.abc import Callable
from pathlib import Path

import pytest

from robots.adapters import runtime_tree_sync as sync


class InjectedStop(BaseException):
    """Non-Exception interruption owned by this fixture."""


def identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    for relative in ("left/deep", "right"):
        (root / relative).mkdir(mode=0o700, parents=True)
    for directory in root.rglob("*"):
        directory.chmod(0o700)
    for relative in ("top", "left/leaf", "left/deep/leaf", "right/leaf"):
        path = root / relative
        path.write_bytes(b"private fixture; never published")
        path.chmod(0o600)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        yield root, fd
    finally:
        os.close(fd)


def test_actual_bottom_up_acknowledgement(tree, monkeypatch):
    root, fd = tree
    expected = {identity(p.stat()): p for p in (root, *root.rglob("*"))}
    calls = []
    actual = os.fsync

    def acknowledge(opened):
        info = os.fstat(opened)
        actual(opened)
        calls.append(identity(info))

    monkeypatch.setattr(os, "fsync", acknowledge)
    acknowledge_tree: Callable[[int], object] = sync.sync_private_tree
    assert acknowledge_tree(fd) is None
    assert set(calls) == set(expected)
    assert len(calls) == len(expected)
    assert calls[-1] == identity(os.fstat(fd))
    for key, path in expected.items():
        if path != root:
            assert calls.index(key) < calls.index(identity(path.parent.stat()))
    assert stat.S_ISDIR(os.fstat(fd).st_mode)


@pytest.mark.parametrize(
    ("target", "mode"), [(".", 0o750), ("left", 0o1700), ("top", 0o640), ("top", 0o4600)]
)
def test_refuses_private_metadata(tree, monkeypatch, target, mode):
    root, fd = tree
    (root / target).chmod(mode)
    opened = []
    actual = os.open

    def record(name, flags, *args, **kwargs):
        opened.append(name)
        return actual(name, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", record)
    with pytest.raises(ValueError, match="private tree"):
        sync.sync_private_tree(fd)
    if target == ".":
        assert not opened
    else:
        assert Path(target).name not in opened


@pytest.mark.parametrize("kind", ["symlink", "fifo"])
def test_rejects_nonregular_before_open(tree, monkeypatch, kind):
    root, fd = tree
    victim = root / "top"
    victim.unlink()
    if kind == "symlink":
        victim.symlink_to("right/leaf")
    else:
        os.mkfifo(victim, 0o600)
    actual = os.open
    opened = []

    def record(name, flags, *args, **kwargs):
        opened.append(name)
        return actual(name, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", record)
    with pytest.raises(ValueError, match="private tree"):
        sync.sync_private_tree(fd)
    assert "top" not in opened


@pytest.mark.parametrize("invalid", [True, False, 1.5, "3", None])
def test_root_requires_integer_nonbool(invalid):
    with pytest.raises(ValueError, match="private tree"):
        sync.sync_private_tree(invalid)


def test_synthetic_uid_on_actual_opened_root(tree, monkeypatch):
    _, fd = tree
    actual = os.fstat
    hits = []

    def synthetic_uid(opened):
        info = actual(opened)
        if opened == fd:
            values = list(info)
            values[4] = info.st_uid + 1
            hits.append(opened)
            return os.stat_result(values)
        return info

    monkeypatch.setattr(os, "fstat", synthetic_uid)
    with pytest.raises(ValueError, match="private tree"):
        sync.sync_private_tree(fd)
    assert hits == [fd]


@pytest.mark.parametrize("relative", ["left/deep/leaf", "left/deep", "."])
@pytest.mark.parametrize("fault_type", [OSError, KeyboardInterrupt, InjectedStop])
def test_sync_fault_preserves_origin_through_released_cleanup(
    tree, monkeypatch, relative, fault_type
):
    root, fd = tree
    target = identity((root / relative).stat())
    fault = OSError(22, "unsupported sync") if fault_type is OSError else fault_type("origin")
    actual_sync, actual_close = os.fsync, os.close
    reached, released, acknowledged = [], [], []
    baseline = len(os.listdir("/proc/self/fd"))

    def fail_sync(opened):
        key = identity(os.fstat(opened))
        if key == target:
            reached.append(key)
            raise fault
        actual_sync(opened)
        acknowledged.append(key)

    def fail_close(opened: int) -> None:
        released.append(opened)
        actual_close(opened)
        message = "cleanup"
        raise OSError(message)

    monkeypatch.setattr(os, "fsync", fail_sync)

    # Only double-fault during unwinding, not before the selected seam.
    def close_if_reached(opened):
        if reached:
            fail_close(opened)
        else:
            actual_close(opened)

    monkeypatch.setattr(os, "close", close_if_reached)
    with pytest.raises(fault_type) as caught:
        sync.sync_private_tree(fd)
    assert caught.value is fault
    frames = []
    tb = caught.value.__traceback__
    while tb is not None:
        frames.append(tb.tb_frame.f_code.co_name)
        tb = tb.tb_next
    assert "fail_sync" in frames
    assert reached == [target]
    assert len(released) == len(set(released))
    assert fd not in released
    assert os.fstat(fd)
    assert len(os.listdir("/proc/self/fd")) == baseline
    if relative == ".":
        assert acknowledged
    else:
        assert identity(os.fstat(fd)) not in acknowledged


@pytest.mark.parametrize("phase", ["before_open", "after_sync"])
@pytest.mark.parametrize("target", ["top", "left"])
def test_reached_inode_substitution_is_refused(tree, monkeypatch, phase, target):
    root, fd = tree
    victim = root / target
    key = identity(victim.stat())
    actual_open, actual_sync = os.open, os.fsync
    reached = []

    def replace() -> None:
        victim.rename(root / "moved")
        if target == "left":
            victim.mkdir(mode=0o700)
        else:
            victim.write_bytes(b"replacement")
            victim.chmod(0o600)
        reached.append(True)

    def opening(name, flags, *args, **kwargs):
        if phase == "before_open" and name == target and not reached:
            replace()
        return actual_open(name, flags, *args, **kwargs)

    def acknowledging(opened):
        actual_sync(opened)
        if phase == "after_sync" and identity(os.fstat(opened)) == key and not reached:
            replace()

    monkeypatch.setattr(os, "open", opening)
    monkeypatch.setattr(os, "fsync", acknowledging)
    with pytest.raises(ValueError, match="private tree"):
        sync.sync_private_tree(fd)
    assert reached == [True]
    assert os.fstat(fd)


def test_anchor_survives_parent_rename_and_cwd_change(tree, monkeypatch, tmp_path):
    root, fd = tree
    moved_parent = tmp_path.with_name(tmp_path.name + "-moved")
    tmp_path.rename(moved_parent)
    tmp_path.mkdir(mode=0o700)
    root.mkdir(mode=0o700)
    sentinel = root / "sentinel"
    sentinel.write_bytes(b"untouched")
    sentinel.chmod(0o600)
    expected = {identity(p.stat()) for p in (moved_parent / root.name).rglob("*")}
    expected.add(identity(os.fstat(fd)))
    calls = []
    actual = os.fsync

    def acknowledge(opened):
        actual(opened)
        calls.append(identity(os.fstat(opened)))

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(os, "fsync", acknowledge)
    sync.sync_private_tree(fd)
    assert set(calls) == expected
    assert identity(sentinel.stat()) not in calls
    assert sentinel.read_bytes() == b"untouched"


def test_all_files_precede_any_directory_ack(tree, monkeypatch):
    _, fd = tree
    modes = []
    actual = os.fsync

    def acknowledge(opened):
        actual(opened)
        modes.append(stat.S_ISDIR(os.fstat(opened).st_mode))

    monkeypatch.setattr(os, "fsync", acknowledge)
    sync.sync_private_tree(fd)
    assert modes == sorted(modes)


@pytest.mark.parametrize("depth", [32, 33])
def test_actual_depth_boundary(tmp_path, monkeypatch, depth):
    root = tmp_path / "bounded"
    root.mkdir(mode=0o700)
    cursor = root
    for _ in range(depth):
        cursor = cursor / "d"
        cursor.mkdir(mode=0o700)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    actual = os.fsync
    calls = []

    def acknowledge(opened):
        actual(opened)
        calls.append(identity(os.fstat(opened)))

    monkeypatch.setattr(os, "fsync", acknowledge)
    try:
        if depth == 32:
            sync.sync_private_tree(fd)
            assert len(calls) == depth + 1
        else:
            with pytest.raises(ValueError, match="private tree bound"):
                sync.sync_private_tree(fd)
            assert not calls
        assert os.fstat(fd)
    finally:
        os.close(fd)


@pytest.mark.parametrize("count", [8192, 8193])
def test_actual_entry_boundary(tmp_path, monkeypatch, count):
    root = tmp_path / "bounded"
    root.mkdir(mode=0o700)
    for index in range(count):
        child = os.open(root / str(index), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(child)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    actual = os.fsync
    calls = []

    def acknowledge(opened):
        actual(opened)
        calls.append(identity(os.fstat(opened)))

    monkeypatch.setattr(os, "fsync", acknowledge)
    try:
        if count == 8192:
            sync.sync_private_tree(fd)
            assert len(calls) == count + 1
        else:
            with pytest.raises(ValueError, match="private tree bound"):
                sync.sync_private_tree(fd)
            assert identity(os.fstat(fd)) not in calls
    finally:
        os.close(fd)


@pytest.mark.parametrize("operation", ["scandir", "stat", "open"])
def test_syscall_failure_is_sanitized_and_origin_retained(tree, monkeypatch, operation):
    root, fd = tree
    actual = getattr(os, operation)
    fault = OSError(13, "private pathname detail", str(root / "top"))
    reached = []

    def fail(*args, **kwargs):
        # Reach a nested directory so independently owned ancestors unwind.
        if (operation == "scandir" and args[0] != fd) or (
            operation != "scandir" and args[0] == "leaf"
        ):
            reached.append(True)
            raise fault
        return actual(*args, **kwargs)

    baseline = len(os.listdir("/proc/self/fd"))
    monkeypatch.setattr(os, operation, fail)
    with pytest.raises(OSError, match="private tree synchronization") as caught:
        sync.sync_private_tree(fd)
    assert caught.value is fault
    assert reached == [True]
    assert fault.errno == 13
    assert fault.filename is None
    assert "private pathname detail" not in str(fault)
    assert str(root) not in str(fault)
    assert len(os.listdir("/proc/self/fd")) == baseline
    assert os.fstat(fd)


def test_cleanup_failure_before_release_is_not_retried(tree, monkeypatch):
    root, fd = tree
    target = identity((root / "left/deep/leaf").stat())
    actual_sync, actual_close = os.fsync, os.close
    fault = KeyboardInterrupt("origin")
    reached, attempts = [], []
    baseline = len(os.listdir("/proc/self/fd"))

    def fail_sync(opened):
        if identity(os.fstat(opened)) == target:
            reached.append(True)
            raise fault
        actual_sync(opened)

    def fail_close(opened: int) -> None:
        if reached:
            attempts.append(opened)
            message = "before physical release"
            raise OSError(message)
        actual_close(opened)

    monkeypatch.setattr(os, "fsync", fail_sync)
    monkeypatch.setattr(os, "close", fail_close)
    try:
        with pytest.raises(KeyboardInterrupt) as caught:
            sync.sync_private_tree(fd)
        assert caught.value is fault
        assert reached == [True]
        assert len(attempts) == 3
        assert len(set(attempts)) == len(attempts)
        assert len(os.listdir("/proc/self/fd")) == baseline + len(attempts)
        assert all(os.fstat(opened) for opened in attempts)
        assert fd not in attempts
    finally:
        monkeypatch.setattr(os, "close", actual_close)
        for opened in attempts:
            actual_close(opened)
    assert len(os.listdir("/proc/self/fd")) == baseline


def test_scan_read_origin_survives_scan_close_after_release(tree, monkeypatch):
    _, fd = tree
    actual = os.scandir
    fault = BaseException("scan origin")
    closed = []
    baseline = len(os.listdir("/proc/self/fd"))

    class FailedScan:
        def __init__(self, opened):
            self.scan = actual(opened)

        def __iter__(self):
            return self

        def __next__(self):
            raise fault

        def close(self):
            self.scan.close()
            closed.append(True)
            message = "scan cleanup"
            raise OSError(message)

    monkeypatch.setattr(os, "scandir", FailedScan)
    with pytest.raises(BaseException, match="scan origin") as caught:
        sync.sync_private_tree(fd)
    assert caught.value is fault
    assert closed == [True]
    assert len(os.listdir("/proc/self/fd")) == baseline


def test_actual_chmod_during_file_sync_is_refused(tree, monkeypatch):
    root, fd = tree
    target = identity((root / "top").stat())
    actual = os.fsync
    reached = []

    def acknowledge(opened):
        actual(opened)
        if identity(os.fstat(opened)) == target:
            os.fchmod(opened, 0o640)
            reached.append(True)

    monkeypatch.setattr(os, "fsync", acknowledge)
    with pytest.raises(ValueError, match="private tree"):
        sync.sync_private_tree(fd)
    assert reached == [True]


def test_regular_file_borrowed_root_is_rejected(tree):
    root, _ = tree
    fd = os.open(root / "top", os.O_RDONLY)
    try:
        with pytest.raises(ValueError, match="private tree"):
            sync.sync_private_tree(fd)
        assert stat.S_ISREG(os.fstat(fd).st_mode)
    finally:
        os.close(fd)


def test_success_path_close_error_refuses_acknowledgement(tree, monkeypatch):
    _, fd = tree
    actual = os.close
    released = []
    fault = OSError(5, "cleanup detail")
    baseline = len(os.listdir("/proc/self/fd"))

    def fail_close(opened):
        actual(opened)
        released.append(opened)
        raise fault

    monkeypatch.setattr(os, "close", fail_close)
    with pytest.raises(OSError, match="private tree synchronization") as caught:
        sync.sync_private_tree(fd)
    assert caught.value is fault
    assert len(set(released)) == len(released)
    assert fd not in released
    assert len(os.listdir("/proc/self/fd")) == baseline
