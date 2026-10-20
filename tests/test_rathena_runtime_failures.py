"""Reached offline faults against real attested synthetic private bundles."""

import json
import os
import stat
import subprocess
import sys
import threading
import traceback
from typing import BinaryIO

import pytest

from robots.adapters import rathena_runtime as runtime
from robots.adapters import rathena_runtime_io as bundle_io
from tests.test_rathena_runtime import synthetic_config


def raw_input() -> bytes:
    return json.dumps(synthetic_config()).encode()


def test_fsync_fault_after_root_moves_marks_original_only(tmp_path, monkeypatch):
    real_sync = os.fsync
    origin = OSError("synthetic moved publication")
    reached: list[bool] = []
    foreign = tmp_path / "foreign"
    foreign.mkdir(mode=0o700)
    (foreign / "sentinel").write_bytes(b"preserve")

    def sync(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode) and not reached:
            (tmp_path / "test").rename(tmp_path / "owned-moved")
            foreign.rename(tmp_path / "test")
            reached.append(True)
            raise origin
        return real_sync(fd)

    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(OSError, match="synthetic moved publication") as caught:
        runtime.build_from_bytes("test", tmp_path / "test", raw_input())
    assert caught.value is origin
    assert reached == [True]
    assert (tmp_path / "owned-moved/INCOMPLETE").exists()
    assert [p.name for p in (tmp_path / "test").iterdir()] == ["sentinel"]
    assert (tmp_path / "test/sentinel").read_bytes() == b"preserve"


@pytest.mark.parametrize("fault", ["fsync", "root-close", "parent-close", "unlink"])
def test_failed_publication_stays_incomplete(tmp_path, monkeypatch, fault):
    real_sync, real_close, real_unlink = os.fsync, os.close, os.unlink
    reached: list[bool] = []
    origin = OSError("synthetic publication")

    def sync(fd):
        if fault == "fsync" and stat.S_ISDIR(os.fstat(fd).st_mode):
            reached.append(True)
            raise origin
        return real_sync(fd)

    def close(fd):
        path = os.readlink(f"/proc/self/fd/{fd}")
        real_close(fd)
        target = str(tmp_path / "test") if fault == "root-close" else str(tmp_path)
        if (
            fault in ("root-close", "parent-close")
            and path == target
            and not reached
            and (tmp_path / "test/manifest.json").exists()
        ):
            reached.append(True)
            raise origin

    def unlink(path, *args, **kwargs):
        result = real_unlink(path, *args, **kwargs)
        if fault == "unlink" and str(path).endswith("INCOMPLETE") and not reached:
            reached.append(True)
            raise origin
        return result

    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(os, "close", close)
    monkeypatch.setattr(os, "unlink", unlink)
    with pytest.raises(OSError, match="synthetic publication") as caught:
        runtime.build_from_bytes("test", tmp_path / "test", raw_input())
    assert caught.value is origin
    assert reached == [True]
    assert (tmp_path / "test/manifest.json").exists()
    assert (tmp_path / "test/INCOMPLETE").exists()


@pytest.mark.parametrize("target", ["root", "parent"])
def test_requested_destination_binding_before_publication(tmp_path, monkeypatch, target):
    parent = tmp_path / "parent"
    parent.mkdir(mode=0o700)
    foreign = tmp_path / "foreign"
    foreign.mkdir(mode=0o700)
    (foreign / "sentinel").write_bytes(b"preserve")
    real_write = bundle_io.write_at
    reached: list[bool] = []

    def moved(fd, name, data):
        real_write(fd, name, data)
        if name == "INCOMPLETE" and not reached:
            if target == "root":
                (parent / "test").rename(tmp_path / "owned-moved")
                foreign.rename(parent / "test")
            else:
                parent.rename(tmp_path / "parent-moved")
                foreign.rename(parent)
            reached.append(True)

    monkeypatch.setattr(runtime, "write_at", moved)
    with pytest.raises(bundle_io.BundleRejectedError):
        runtime.build_from_bytes("test", parent / "test", raw_input())
    assert reached == [True]
    replacement = parent / "test" if target == "root" else parent
    assert (replacement / "sentinel").read_bytes() == b"preserve"
    assert [p.name for p in replacement.iterdir()] == ["sentinel"]
    owned = tmp_path / "owned-moved" if target == "root" else tmp_path / "parent-moved/test"
    assert (owned / "INCOMPLETE").exists()


@pytest.mark.parametrize("mutation", ["mode", "inode", "root", "subdir"])
def test_output_readback_enforces_private_identity(tmp_path, monkeypatch, mutation):
    real_read = bundle_io.read_at
    reached: list[bool] = []

    def changed(fd, name, *args, **kwargs):
        if name == "inter_athena.conf" and not reached:
            reached.append(True)
            if mutation == "mode":
                os.chmod(name, 0o644, dir_fd=fd)
            elif mutation == "inode":
                original = tmp_path / "test/conf/inter_athena.conf"
                replacement = tmp_path / "replacement"
                replacement.write_bytes(original.read_bytes())
                replacement.chmod(0o600)
                original.rename(tmp_path / "owned-leaf")
                replacement.rename(original)
            else:
                (tmp_path / "test" if mutation == "root" else tmp_path / "test/conf").chmod(0o755)
        return real_read(fd, name, *args, **kwargs)

    monkeypatch.setattr(bundle_io, "read_at", changed)
    with pytest.raises(bundle_io.BundleRejectedError):
        runtime.build_from_bytes("test", tmp_path / "test", raw_input())
    assert reached == [True]
    assert (tmp_path / "test/INCOMPLETE").exists()


@pytest.mark.parametrize("fault", ["root", "directory", "stream"])
def test_cleanup_double_fault_preserves_exact_origin(tmp_path, monkeypatch, fault):
    real_write = bundle_io.write_at
    real_close = os.close
    real_fdopen = os.fdopen
    origin = KeyboardInterrupt("synthetic origin")
    secondary = OSError("synthetic close")
    state = {"root": None, "origin": False, "close": False}
    before = len(os.listdir("/proc/self/fd"))

    def interrupted(fd, name, data):
        state["root"] = fd
        real_write(fd, name, data)
        if name == "LICENSE":
            state["origin"] = True
            raise origin

    def close(fd):
        real_close(fd)
        if (
            state["origin"]
            and not state["close"]
            and (
                (fault == "root" and fd == state["root"])
                or (fault == "directory" and fd != state["root"])
            )
        ):
            state["close"] = True
            raise secondary

    class Stream:
        def __init__(self, stream: BinaryIO) -> None:
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.stream.close()
            state["close"] = True
            raise secondary

        def write(self, data):
            self.stream.write(data)
            state["origin"] = True
            raise origin

    def stream(fd, mode, *args, **kwargs):
        actual = real_fdopen(fd, mode, *args, **kwargs)
        if fault == "stream" and mode == "wb":
            return Stream(actual)
        return actual

    monkeypatch.setattr(runtime, "write_at", interrupted)
    monkeypatch.setattr(os, "close", close)
    monkeypatch.setattr(os, "fdopen", stream)
    with pytest.raises(KeyboardInterrupt, match="synthetic origin") as caught:
        runtime.build_from_bytes("test", tmp_path / "test", raw_input())
    assert caught.value is origin
    assert any(
        frame.name == "write" if fault == "stream" else frame.name == "interrupted"
        for frame in traceback.extract_tb(caught.value.__traceback__)
    )
    assert state["origin"]
    assert state["close"]
    assert len(os.listdir("/proc/self/fd")) == before
    assert (tmp_path / "test/INCOMPLETE").exists()


@pytest.mark.parametrize("mode", [0o755, 0o700])
def test_root_substitution_before_open_is_not_adopted(tmp_path, monkeypatch, mode):
    foreign = tmp_path / "foreign"
    foreign.mkdir(mode=mode)
    sentinel = foreign / "sentinel"
    sentinel.write_bytes(b"preserve")
    sentinel.chmod(0o600)
    real_open = os.open
    reached: list[bool] = []

    def swapped(path, flags, *args, **kwargs):
        if path == "test" and flags & os.O_DIRECTORY and not reached:

            def replace():
                (tmp_path / "test").rename(tmp_path / "new-owned")
                foreign.rename(tmp_path / "test")
                reached.append(True)

            thread = threading.Thread(target=replace)
            thread.start()
            thread.join(timeout=5)
            assert not thread.is_alive()
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", swapped)
    with pytest.raises(bundle_io.BundleRejectedError):
        runtime.build_from_bytes("test", tmp_path / "test", raw_input())
    assert reached == [True]
    assert sentinel.name == "sentinel"
    assert (tmp_path / "test/sentinel").read_bytes() == b"preserve"
    assert [p.name for p in (tmp_path / "test").iterdir()] == ["sentinel"]
    assert stat.S_IMODE((tmp_path / "test").stat().st_mode) == mode
    assert not any((tmp_path / "new-owned").iterdir())


def test_native_display_world_capacity(tmp_path, monkeypatch):
    def forbidden():
        pytest.fail("oversized world reached public reads")

    with monkeypatch.context() as patch:
        patch.setattr(runtime, "public_assets", forbidden)
        for length in (20, 37):
            world = "prod-" + "A" * (length - 5)
            with pytest.raises(bundle_io.BundleRejectedError):
                runtime.build_from_bytes(world, tmp_path / world, raw_input())
    world = "prod-" + "A" * 14
    result = runtime.build_from_bytes(world, tmp_path / world, raw_input())
    assert result["world"] == world
    assert (
        f"server_name: {world}\n".encode()
        in (tmp_path / world / "conf/char_athena.conf").read_bytes()
    )
    assert not (tmp_path / world / "INCOMPLETE").exists()


@pytest.mark.parametrize("encoding", ["utf-16", "utf-32"])
@pytest.mark.parametrize("use_stdin", [False, True])
def test_only_utf8_before_public_reads(tmp_path, monkeypatch, encoding, use_stdin):
    def forbidden():
        pytest.fail("alternate encoding reached public reads")

    monkeypatch.setattr(runtime, "public_assets", forbidden)
    raw = json.dumps(synthetic_config()).encode(encoding)
    with pytest.raises(bundle_io.BundleRejectedError):
        runtime.build_from_bytes("test", tmp_path / "test", raw)
    secret = tmp_path / "private.json"
    secret.write_bytes(raw)
    secret.chmod(0o600)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "robots.adapters.rathena_runtime",
            "--world",
            "test",
            "--destination",
            str(tmp_path / "test"),
            "--secret-file",
            "-" if use_stdin else str(secret),
        ],
        input=raw if use_stdin else None,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 2
    assert result.stdout == b""
    assert not (tmp_path / "test").exists()


@pytest.mark.parametrize("option", ["--destination", "--secret-file"])
@pytest.mark.parametrize("alias", ["/./", "//", "/../"])
def test_cli_literal_spelling_rejected(tmp_path, monkeypatch, option, alias):
    secret = tmp_path / "private.json"
    secret.write_bytes(raw_input())
    secret.chmod(0o600)
    destination = str(tmp_path) + "/test"
    source = str(secret)
    if option == "--destination":
        destination = str(tmp_path) + alias + "test"
    else:
        source = str(tmp_path) + alias + "private.json"

    def forbidden(*_args, **_kwargs):
        pytest.fail("alias reached input or public reads")

    monkeypatch.setattr(runtime, "read_path", forbidden)
    monkeypatch.setattr(runtime, "public_assets", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        ["runtime", "--world", "test", "--destination", destination, "--secret-file", source],
    )
    assert runtime.main() == 2
    assert not (tmp_path / "test").exists()
