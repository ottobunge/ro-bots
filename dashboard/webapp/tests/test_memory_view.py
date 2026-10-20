"""Memory-view tests: read-only listing of per-agent memory files."""

from __future__ import annotations

import os
from pathlib import Path

from dashboard_webapp.memory_view import MemoryViewer


def _touch(path: Path, mtime: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n")
    os.utime(path, (mtime, mtime))
    return path


def test_lists_only_files_matching_the_needle(tmp_path: Path) -> None:
    _touch(tmp_path / "playing-native-memory" / "host_fixture_0.jsonl", 1792400000.0)
    _touch(tmp_path / "playing-native-memory" / "host_fixture_1.jsonl", 1792400001.0)

    viewer = MemoryViewer(str(tmp_path))
    files = viewer.list("host_fixture_0")

    assert [f.path for f in files] == ["playing-native-memory/host_fixture_0.jsonl"]
    assert files[0].size_bytes > 0
    assert files[0].modified_ts == 1792400000.0


def test_newest_first_recursive(tmp_path: Path) -> None:
    _touch(tmp_path / "a" / "host_fixture_0.jsonl", 100.0)
    _touch(tmp_path / "b" / "host_fixture_0.jsonl", 300.0)
    _touch(tmp_path / "host_fixture_0.jsonl", 200.0)

    viewer = MemoryViewer(str(tmp_path))
    files = viewer.list("host_fixture_0")

    assert [f.modified_ts for f in files] == [300.0, 200.0, 100.0]
    assert all("\\" not in f.path and not f.path.startswith("/") for f in files)


def test_cap_limits_results(tmp_path: Path) -> None:
    for i in range(60):
        _touch(tmp_path / f"agent_{i}" / "host_fixture_0.jsonl", float(i))

    viewer = MemoryViewer(str(tmp_path))
    assert len(viewer.list("host_fixture_0")) == 50


def test_no_match_or_missing_root_yields_empty(tmp_path: Path) -> None:
    viewer = MemoryViewer(str(tmp_path))
    assert viewer.list("nobody") == []
    assert MemoryViewer(str(tmp_path / "does-not-exist")).list("host_fixture_0") == []
    assert MemoryViewer("").list("anything") == []


def test_symlinks_are_skipped(tmp_path: Path) -> None:
    real = _touch(tmp_path / "real.jsonl", 100.0)
    link = tmp_path / "host_fixture_0.jsonl"
    link.symlink_to(real)

    viewer = MemoryViewer(str(tmp_path))
    assert viewer.list("host_fixture_0") == []


def test_memory_root_only_lists_files_not_directories(tmp_path: Path) -> None:
    (tmp_path / "host_fixture_0").mkdir()
    _touch(tmp_path / "host_fixture_0.jsonl", 100.0)

    viewer = MemoryViewer(str(tmp_path))
    assert [f.path for f in viewer.list("host_fixture_0")] == ["host_fixture_0.jsonl"]
