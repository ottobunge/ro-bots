"""Synthetic-only private checkpoint contracts; never open a real journal."""

import fcntl
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from robots.adapters import optchat_view_store as storage
from robots.adapters.optchat_view_store import PrivateViewStore, SourcePrefixBinding
from robots.society import optchat_view as core


def synthetic_prefix(count: int) -> storage.SourcePrefixBinding:
    rows = [
        json.dumps({"ordinal": i, "text": f"public synthetic 😀 {i}"}).encode() + b"\n"
        for i in range(count)
    ]
    return storage.SourcePrefixBinding(len(rows), hashlib.sha256(b"".join(rows)).hexdigest())


def saved_store(
    tmp_path: Path,
) -> tuple[
    storage.PrivateViewStore,
    core.IncrementalView,
    dict[core.NodeCoordinate, str],
    storage.SourcePrefixBinding,
]:
    view, texts = fixture_view()
    prefix = synthetic_prefix(4)
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    store = storage.PrivateViewStore(root, "world", "persona", view.policy)
    empty = core.IncrementalView(texts.get, view.policy)
    store.save(empty, storage.SourcePrefixBinding(0, hashlib.sha256(b"").hexdigest()), texts.get)
    store.save(view, prefix, texts.get)
    return store, view, texts, prefix


@pytest.mark.parametrize("mutation", ["world", "persona", "source", "count", "node", "newline"])
def test_bindings_fail_closed(tmp_path, mutation):
    store, view, texts, prefix = saved_store(tmp_path)
    if mutation in {"world", "persona"}:
        data = json.loads(store.path.read_bytes())
        data[mutation] = "foreign"
        store.path.write_text(json.dumps(data))
    elif mutation == "source":
        prefix = storage.SourcePrefixBinding(4, hashlib.sha256(b"reordered raw").hexdigest())
    elif mutation == "count":
        prefix = storage.SourcePrefixBinding(3, prefix.sha256)
    else:
        node = view.state.coordinates[0]
        texts[node] = texts[node].replace("\n", " ") if mutation == "newline" else "changed"
    with pytest.raises(
        ValueError,
        match=r"prefix|identity|closure",
    ):
        store.load(prefix, texts.get)
    store.close()


@pytest.mark.parametrize("value", [True, 1, 1.0, "../escape", "a/b", "", "é"])
def test_invalid_ids_allocate_nothing(tmp_path, value):
    root = tmp_path / "absent"
    with pytest.raises(
        ValueError,
        match="literal safe identifiers",
    ):
        storage.PrivateViewStore(root, value, "persona", core.ViewPolicy())
    assert not root.exists()


def test_save_requires_exact_prefix_count(tmp_path):
    store, view, texts, prefix = saved_store(tmp_path)
    before = store.path.read_bytes()
    with pytest.raises(
        ValueError,
        match="prefix count",
    ):
        store.save(view, storage.SourcePrefixBinding(3, prefix.sha256), texts.get)
    assert store.path.read_bytes() == before
    store.close()


@pytest.mark.parametrize(
    ("count", "digest"),
    [
        (True, "a" * 64),
        (1.0, "a" * 64),
        (-1, "a" * 64),
        (1, "A" * 64),
        (1, "x" * 64),
        (1, "a" * 63),
    ],
)
def test_prefix_requires_exact_types(count, digest):
    with pytest.raises(
        ValueError,
        match="Source prefix",
    ):
        storage.SourcePrefixBinding(count, digest)


def test_lifetime_writer_subprocess_and_release(tmp_path):
    store, view, _texts, _prefix = saved_store(tmp_path)
    root = store.path.parents[4]
    code = """
import sys
from pathlib import Path
from robots.adapters.optchat_view_store import PrivateViewStore
from robots.society.optchat_view import ViewPolicy
try: s=PrivateViewStore(Path(sys.argv[1]),'world','persona',ViewPolicy('synthetic',10,20))
except BlockingIOError: sys.exit(17)
s.close()
"""
    result = subprocess.run([sys.executable, "-c", code, str(root)], check=False)
    try:
        assert result.returncode == 17
    finally:
        store.close()
    next_store = storage.PrivateViewStore(root, "world", "persona", view.policy)
    next_store.close()


@pytest.mark.parametrize(
    ("target", "kind"),
    [
        ("view.json", "public"),
        ("view.json", "hardlink"),
        ("view.json", "symlink"),
        ("writer.lock", "public"),
        ("writer.lock", "hardlink"),
        ("writer.lock", "symlink"),
        ("ancestor", "public"),
        ("ancestor", "symlink"),
    ],
)
def test_private_namespace_and_files(tmp_path, target, kind):
    store, view, _texts, _prefix = saved_store(tmp_path)
    path = store.path.parent / target
    root = store.path.parents[4]
    store.close()
    if target == "writer.lock" and not path.exists():
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
    if target == "ancestor":
        path = root / "view-state"
    if kind == "public":
        path.chmod(0o755 if path.is_dir() else 0o644)
    elif kind == "hardlink":
        os.link(path, tmp_path / "second-link")
    else:
        moved = path.with_name(path.name + "-original")
        path.rename(moved)
        path.symlink_to(moved)
    with pytest.raises(OSError, match=r"private|link|directory|Directory|symbolic"):
        storage.PrivateViewStore(root, "world", "persona", view.policy)


@pytest.mark.parametrize("mutation", ["version-bool", "extra", "duplicate", "oversize"])
def test_outer_schema_and_bound(tmp_path, mutation):
    store, _view, texts, prefix = saved_store(tmp_path)
    data = json.loads(store.path.read_bytes())
    if mutation == "version-bool":
        data["version"] = True
    elif mutation == "extra":
        data["other"] = 0
    payload = json.dumps(data)
    if mutation == "duplicate":
        payload = payload.replace('"version": 1', '"version": 1, "version": 1')
    elif mutation == "oversize":
        payload += " " * 1_048_576
    store.path.write_text(payload)
    try:
        with pytest.raises(
            ValueError,
            match=r"schema|Duplicate|Checkpoint",
        ):
            store.load(prefix, texts.get)
    finally:
        store.close()


@pytest.mark.parametrize("fault", ["zero-write", "file-sync", "rename", "directory-sync"])
def test_uncertain_publish_poison_preserves_origin(tmp_path, monkeypatch, fault):
    store, view, texts, prefix = saved_store(tmp_path)
    before = store.path.read_bytes()
    texts[core.NodeCoordinate(0, 4)] = "new public synthetic appended summary"
    view.append()
    prefix = synthetic_prefix(5)
    origin = KeyboardInterrupt("synthetic interruption")
    operations = []
    real_write, real_sync, real_replace = os.write, os.fsync, os.replace

    def write(fd, data):
        operations.append("write")
        return 0 if fault == "zero-write" else real_write(fd, data)

    def sync(fd):
        kind = "directory-sync" if fd == store._directory else "file-sync"
        operations.append(kind)
        if fault == kind:
            raise origin
        real_sync(fd)

    def replace(*args, **kwargs):
        operations.append("rename")
        if fault == "rename":
            raise origin
        return real_replace(*args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(os, "write", write)
        patcher.setattr(os, "fsync", sync)
        patcher.setattr(os, "replace", replace)
        expected = OSError if fault == "zero-write" else KeyboardInterrupt
        with pytest.raises(expected) as caught:
            store.save(view, prefix, texts.get)
        if fault != "zero-write":
            assert caught.value is origin
        assert fault in operations or fault == "zero-write"
        with pytest.raises(OSError, match="failed"):
            store.save(view, prefix, texts.get)
        with pytest.raises(OSError, match="failed"):
            store.load(prefix, texts.get)
    if fault != "directory-sync":
        assert store.path.read_bytes() == before
    else:
        # The rename happened, but NO durable acknowledgement was returned.
        assert store.path.read_bytes() != before
        assert json.loads(store.path.read_bytes())["snapshot"] == view.snapshot()
    store.close()


def test_partial_writes_complete_and_ack_order(tmp_path, monkeypatch):
    store, view, texts, prefix = saved_store(tmp_path)
    operations = []
    real_write, real_sync, real_replace = os.write, os.fsync, os.replace

    def write(fd, data):
        operations.append("write")
        return real_write(fd, data[:7])

    def sync(fd):
        operations.append("directory-sync" if fd == store._directory else "file-sync")
        real_sync(fd)

    def replace(*args, **kwargs):
        operations.append("rename")
        return real_replace(*args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(os, "write", write)
        patcher.setattr(os, "fsync", sync)
        patcher.setattr(os, "replace", replace)
        store.save(view, prefix, texts.get)
    assert operations[-3:] == ["file-sync", "rename", "directory-sync"]
    assert operations.count("write") > 1
    assert store.load(prefix, texts.get).read() == view.read()
    store.close()


def test_callback_failure_releases_physical_lock(tmp_path):
    store, view, _texts, prefix = saved_store(tmp_path)
    root = store.path.parents[4]
    origin = SystemExit(23)

    def callback(_node):
        raise origin

    with pytest.raises(SystemExit) as caught:
        store.load(prefix, callback)
    assert caught.value is origin
    new = storage.PrivateViewStore(root, "world", "persona", view.policy)
    new.close()
    store.close()


@pytest.mark.parametrize("release_first", [False, True])
def test_close_failure_reports_unconfirmed_physical_ownership(tmp_path, monkeypatch, release_first):
    store, view, _texts, _prefix = saved_store(tmp_path)
    lock_fd, directory_fd = store._lock_fd, store._directory
    origin = KeyboardInterrupt("close interruption")
    real_close = os.close
    reached = []

    def close(fd):
        reached.append(fd)
        if fd == lock_fd:
            if release_first:
                real_close(fd)
            raise origin
        real_close(fd)

    with monkeypatch.context() as patcher:
        patcher.setattr(os, "close", close)
        with pytest.raises(KeyboardInterrupt) as caught:
            store.close()
        assert caught.value is origin
        assert directory_fd in reached
        assert store.unconfirmed_ownership == (lock_fd,)
        with pytest.raises(OSError, match="unconfirmed"):
            store.close()
        assert reached.count(lock_fd) == 1
    with pytest.raises(OSError, match="Bad file descriptor"):
        os.fstat(directory_fd)
    root = store.path.parents[4]
    if release_first:
        with pytest.raises(OSError, match="Bad file descriptor"):
            os.fstat(lock_fd)
        new = storage.PrivateViewStore(root, "world", "persona", view.policy)
        new.close()
    else:
        os.fstat(lock_fd)
        probe = os.open(store.path.parent / "writer.lock", os.O_RDWR)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            real_close(probe)
            real_close(lock_fd)  # harness recovery only AFTER physical observations


def test_missing_nonempty_save_requires_explicit_initialization(tmp_path):
    view, texts = fixture_view()
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    store = storage.PrivateViewStore(root, "world", "persona", view.policy)
    prefix = storage.SourcePrefixBinding(4, hashlib.sha256(b"raw").hexdigest())
    try:
        with pytest.raises(ValueError, match="empty"):
            store.save(view, prefix, texts.get)
        assert not store.path.exists()
    finally:
        store.close()


def test_corrupt_checkpoint_cannot_be_overwritten(tmp_path):
    store, view, texts, prefix = saved_store(tmp_path)
    store.path.write_bytes(b"corrupt")
    try:
        with pytest.raises(
            ValueError,
            match="Expecting value",
        ):
            store.save(view, prefix, texts.get)
        assert store.path.read_bytes() == b"corrupt"
    finally:
        store.close()


@pytest.mark.parametrize("count", [0, 4])
def test_missing_load_never_fabricates_zero(tmp_path, count):
    view, texts = fixture_view()
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    store = storage.PrivateViewStore(root, "world", "persona", view.policy)
    with pytest.raises(FileNotFoundError):
        store.load(storage.SourcePrefixBinding(count, hashlib.sha256(b"").hexdigest()), texts.get)
    assert not store.path.exists()
    store.close()


@pytest.mark.parametrize(
    "mutation",
    [
        "low",
        "high",
        "namespace",
        "coords",
        "pending",
        "count-float",
        "missing-node",
        "unicode-oversize",
        "truncated",
    ],
)
def test_core_corruption_is_rejected_without_repair(tmp_path, mutation):
    store, _view, texts, prefix = saved_store(tmp_path)
    data = json.loads(store.path.read_bytes())
    if mutation in {"low", "high"}:
        data["snapshot"]["policy"][mutation + "_bytes"] += 1
    elif mutation == "namespace":
        data["snapshot"]["policy"]["namespace"] = "foreign"
    elif mutation == "coords":
        data["snapshot"]["coordinates"].reverse()
    elif mutation == "pending":
        data["snapshot"]["pending_batch"] = 1
    elif mutation == "count-float":
        data["snapshot"]["source_count"] = 4.0
    elif mutation == "missing-node":
        texts.clear()
    elif mutation == "unicode-oversize":
        texts[core.NodeCoordinate(0, 0)] = "😀" * 129
    payload = json.dumps(data).encode()
    if mutation == "truncated":
        payload = payload[:-3]
    store.path.write_bytes(payload)
    with pytest.raises(
        ValueError,
        match=r"policy|Coordinates|Pending|integer|node|UTF-8|Unterminated",
    ):
        store.load(prefix, texts.get)
    assert store.path.read_bytes() == payload
    store.close()


def test_admitted_leaf_callback_failure_does_not_require_reappend(tmp_path):
    texts = {core.NodeCoordinate(0, i): "long-leaf" for i in range(2)}
    failed = False
    origin = RuntimeError("parent not yet available")

    def callback(node):
        if node.level and not failed:
            raise origin
        return texts.get(node)

    policy = core.ViewPolicy("synthetic", 10, 20)
    view = core.IncrementalView(callback, policy)
    view.append()
    with pytest.raises(RuntimeError) as caught:
        view.append()
    assert caught.value is origin
    assert view.state.source_count == 2
    failed = True
    view.advance()  # caller uses admitted ordinal, NOT blind append again
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    store = storage.PrivateViewStore(root, "world", "persona", policy)
    store.save(core.IncrementalView(texts.get, policy), synthetic_prefix(0), texts.get)
    store.save(view, synthetic_prefix(2), texts.get)
    restored = store.load(synthetic_prefix(2), texts.get)
    assert restored.state == view.state
    assert restored.read() == view.read()
    store.close()


@pytest.mark.parametrize("which", ["lock", "read", "pending"])
def test_fstat_interruption_has_no_lost_descriptor(tmp_path, monkeypatch, which):
    origin = SystemExit(42)
    real_open, real_fstat = os.open, os.fstat
    opened = []
    target_fd = -1

    def open_fd(path, flags, *args, **kwargs):
        nonlocal target_fd
        fd = real_open(path, flags, *args, **kwargs)
        opened.append(fd)
        if (
            (which == "lock" and path == "writer.lock")
            or (which == "read" and path == "view.json")
            or (which == "pending" and isinstance(path, str) and path.startswith("pending-"))
        ):
            target_fd = fd
        return fd

    def fstat(fd):
        if fd == target_fd:
            raise origin
        return real_fstat(fd)

    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    view, texts = fixture_view()
    store = None
    if which != "lock":
        store, view, texts, prefix = saved_store(root)
        root = store.path.parents[4]

    def operation() -> None:
        if which == "lock":
            storage.PrivateViewStore(root, "world", "persona", view.policy)
        else:
            assert store is not None
            if which == "read":
                store.load(prefix, texts.get)
            else:
                store.save(view, prefix, texts.get)

    with monkeypatch.context() as patcher:
        patcher.setattr(os, "open", open_fd)
        patcher.setattr(os, "fstat", fstat)
        with pytest.raises(SystemExit) as caught:
            operation()
        assert caught.value is origin
    assert target_fd >= 0
    if store is not None:
        store.close()
    with pytest.raises(OSError, match="Bad file descriptor"):
        real_fstat(target_fd)
    new = storage.PrivateViewStore(root, "world", "persona", view.policy)
    new.close()


def test_restore_origin_and_cleanup_owner_survive_failed_close(tmp_path, monkeypatch):
    store, _view, _texts, prefix = saved_store(tmp_path)
    lock_fd = store._lock_fd
    real_close = os.close
    origin = SystemExit(73)

    def callback(_node):
        raise origin

    def close(fd):
        if fd == lock_fd:
            message = "cleanup interrupted"
            raise KeyboardInterrupt(message)
        real_close(fd)

    with monkeypatch.context() as patcher:
        patcher.setattr(os, "close", close)
        with pytest.raises(SystemExit) as caught:
            store.load(prefix, callback)
        assert caught.value is origin
        assert origin.__dict__["view_store_owner"] is store
        assert store.unconfirmed_ownership == (lock_fd,)
        frames = []
        frame = origin.__traceback__
        while frame is not None:
            frames.append(frame.tb_frame.f_code.co_name)
            frame = frame.tb_next
        assert frames[-1] == "callback"
        os.fstat(lock_fd)
    probe = os.open(store.path.parent / "writer.lock", os.O_RDWR)
    try:
        with pytest.raises(BlockingIOError):
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        real_close(probe)
        real_close(lock_fd)


def unavailable_diagnostics_origin(base: type[BaseException], attributes: str) -> BaseException:
    def dictionary(_self):
        message = "diagnostic attribute unavailable"
        raise RuntimeError(message)

    def getter(self, name):
        if attributes == "hooks" and name in {"__dict__", "view_store_owner"}:
            message = "diagnostic getter unavailable"
            raise RuntimeError(message)
        return object.__getattribute__(self, name)

    def setter(_self, _name, _value):
        message = "diagnostic setter unavailable"
        raise RuntimeError(message)

    def note(_self, _note):
        message = "diagnostic note unavailable"
        raise RuntimeError(message)

    origin_type = type(
        "Origin",
        (base,),
        {
            "__dict__": property(dictionary),
            "__getattribute__": getter,
            "__setattr__": setter,
            "add_note": note,
        },
    )
    origin: BaseException = origin_type("synthetic source-port origin")
    return origin


def assert_safe_handoff(origin, store, operation, *, lock_fd, calls, root, code) -> None:
    # Supported handoff bypasses all overridden exception diagnostic attributes.
    metadata = BaseException.__dict__["__dict__"].__get__(origin)
    owner = metadata["view_store_owner"]
    assert isinstance(owner, storage.PrivateViewStore)
    assert owner.unconfirmed_ownership == (lock_fd,)
    if operation == "load":
        assert owner is store
    frame = origin.__traceback__
    assert frame is not None
    while frame.tb_next is not None:
        frame = frame.tb_next
    assert frame.tb_frame.f_code.co_name == ("callback" if operation == "load" else "sync")
    os.fstat(lock_fd)
    assert subprocess.run([sys.executable, "-c", code, str(root)], check=False).returncode == 17
    with pytest.raises(OSError, match="unconfirmed"):
        owner.close()
    assert calls.count(lock_fd) == 1


@pytest.mark.parametrize("base", [OSError, KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("attributes", ["property", "hooks"])
@pytest.mark.parametrize("operation", ["load", "constructor"])
def test_custom_origin_safe_owner_handoff(tmp_path, monkeypatch, base, attributes, operation):
    origin = unavailable_diagnostics_origin(base, attributes)
    store, view, _texts, prefix = saved_store(tmp_path)
    root = store.path.parents[4]
    real_close, real_open, real_sync = os.close, os.open, os.fsync
    if operation == "constructor":
        store.close()
    lock_fd = -1 if operation == "constructor" else store._lock_fd
    calls: list[int] = []

    def open_fd(path, flags, *args, **kwargs):
        nonlocal lock_fd
        fd = real_open(path, flags, *args, **kwargs)
        if path == "writer.lock":
            lock_fd = fd
            calls.clear()  # Ignore reused root-helper descriptors before lock allocation.
        return fd

    def callback(_node):
        raise origin

    def sync(fd):
        if lock_fd >= 0:
            raise origin
        real_sync(fd)

    def close(fd):
        calls.append(fd)
        if fd == lock_fd:
            message = "synthetic close before physical release"
            raise OSError(message)
        real_close(fd)

    def reach_origin() -> None:
        if operation == "load":
            store.load(prefix, callback)
        else:
            storage.PrivateViewStore(root, "world", "persona", view.policy)

    code = """
import sys
from pathlib import Path
from robots.adapters.optchat_view_store import PrivateViewStore
from robots.society.optchat_view import ViewPolicy
try: s=PrivateViewStore(Path(sys.argv[1]),'world','persona',ViewPolicy('synthetic',10,20))
except BlockingIOError: sys.exit(17)
s.close()
"""
    try:
        with monkeypatch.context() as patcher:
            patcher.setattr(os, "close", close)
            if operation == "constructor":
                patcher.setattr(os, "open", open_fd)
                patcher.setattr(os, "fsync", sync)
            with pytest.raises(base) as caught:
                reach_origin()
            assert caught.value is origin
            assert_safe_handoff(
                origin, store, operation, lock_fd=lock_fd, calls=calls, root=root, code=code
            )
    finally:
        real_close(lock_fd)  # Known held fixture fd: harness recovery, never production retry.
    assert subprocess.run([sys.executable, "-c", code, str(root)], check=False).returncode == 0


@pytest.mark.parametrize("secondary", [MemoryError, KeyboardInterrupt, SystemExit])
def test_secondary_metadata_fault_cannot_replace_control_flow(tmp_path, monkeypatch, secondary):
    store, _view, _texts, prefix = saved_store(tmp_path)
    origin = SystemExit(81)
    lock_fd = store._lock_fd
    real_close = os.close

    class FaultingMetadata:
        def __setitem__(self, _key, _owner):
            raise secondary

    def callback(_node):
        # Fault injection only at diagnostic publication, not load admission.
        monkeypatch.setattr(storage, "dict", FaultingMetadata, raising=False)
        raise origin

    def close(fd):
        if fd == lock_fd:
            message = "synthetic close before release"
            raise OSError(message)
        real_close(fd)

    try:
        monkeypatch.setattr(os, "close", close)
        with pytest.raises(SystemExit) as caught:
            store.load(prefix, callback)
        assert caught.value is origin
        frame = origin.__traceback__
        assert frame is not None
        while frame.tb_next is not None:
            frame = frame.tb_next
        assert frame.tb_frame.f_code.co_name == "callback"
        assert store.unconfirmed_ownership == (lock_fd,)
        os.fstat(lock_fd)
    finally:
        real_close(lock_fd)


def test_store_is_available():
    assert importlib.util.find_spec("robots.adapters.optchat_view_store") is not None


def fixture_view() -> tuple[core.IncrementalView, dict[core.NodeCoordinate, str]]:
    texts = {core.NodeCoordinate(0, i): f"2026-10-09 catégorie 😀\n{i}" for i in range(4)}
    view = core.IncrementalView(texts.get, core.ViewPolicy("synthetic", 10, 20))
    for _ in range(4):
        view.append()
    return view, texts


def test_exact_reopen_and_fresh_process(tmp_path):
    view, texts = fixture_view()
    prefix = synthetic_prefix(4)
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    store = PrivateViewStore(root, "world", "persona", view.policy)
    store.save(
        core.IncrementalView(texts.get, view.policy),
        SourcePrefixBinding(0, hashlib.sha256(b"").hexdigest()),
        texts.get,
    )
    store.save(view, prefix, texts.get)
    store.close()
    reopened = PrivateViewStore(root, "world", "persona", view.policy)
    restored = reopened.load(prefix, texts.get)
    assert restored.snapshot() == view.snapshot()
    assert restored.read() == view.read()
    assert restored.state.pending_batch
    with pytest.raises(core.OverBudgetError):
        restored.read_ready()
    reopened.close()
    code = """
import json,sys
from pathlib import Path
from robots.adapters.optchat_view_store import PrivateViewStore,SourcePrefixBinding
from robots.society.optchat_view import NodeCoordinate,ViewPolicy
texts={NodeCoordinate(0,i):f'2026-10-09 catégorie 😀\\n{i}' for i in range(4)}
s=PrivateViewStore(Path(sys.argv[1]),'world','persona',ViewPolicy('synthetic',10,20))
v=s.load(SourcePrefixBinding(4,sys.argv[2]),texts.get)
print(json.dumps({'snapshot':v.snapshot(),'hex':v.read().hex()}))
s.close()
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(root), prefix.sha256],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == {"snapshot": view.snapshot(), "hex": view.read().hex()}
    assert os.stat(root / "view-state/world/persona/synthetic/view.json").st_mode & 0o777 == 0o600
