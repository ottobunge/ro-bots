"""Accepted component objects must not alter validated native pathname bytes."""

import os
from pathlib import Path

import pytest

from robots.adapters import runtime_publication_io as publication
from robots.adapters.runtime_publication_io import move_directory_noreplace


class RedirectedComponent(str):
    def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        del encoding, errors
        return b"../escaped"


def test_destination_subclass_cannot_escape_retained_parent(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir(mode=0o700)
    destination.mkdir(mode=0o700)
    stage = source / "stage"
    stage.mkdir(mode=0o700)
    identity = stage.stat()
    source_fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY)
    destination_fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(ValueError, match="literal printable ASCII"):
            move_directory_noreplace(
                source_fd, "stage", destination_fd, RedirectedComponent("final")
            )
        assert stage.stat().st_ino == identity.st_ino
        assert list(destination.iterdir()) == []
        assert not (tmp_path / "escaped").exists()
        assert os.fstat(source_fd).st_ino == source.stat().st_ino
        assert os.fstat(destination_fd).st_ino == destination.stat().st_ino
    finally:
        os.close(destination_fd)
        os.close(source_fd)


@pytest.mark.parametrize("side", ["source", "destination"])
def test_all_string_subclasses_rejected_before_encoding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, side: str
) -> None:
    calls: list[str] = []

    class Component(str):
        def encode(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
            del encoding, errors
            calls.append("encode")
            return b"../escaped"

    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir(mode=0o700)
    destination.mkdir(mode=0o700)
    stage = source / "stage"
    stage.mkdir(mode=0o700)
    identity = stage.stat().st_ino
    source_fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY)
    destination_fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY)

    def forbidden_native(*args: object) -> int:
        del args
        calls.append("native")
        pytest.fail("subclass reached native move")

    monkeypatch.setattr(publication, "_renameat2", forbidden_native)
    try:
        source_name = Component("stage") if side == "source" else "stage"
        target_name = Component("final") if side == "destination" else "final"
        with pytest.raises(ValueError, match="literal printable ASCII"):
            move_directory_noreplace(source_fd, source_name, destination_fd, target_name)
        assert calls == []
        assert stage.stat().st_ino == identity
        assert list(destination.iterdir()) == []
        assert not (tmp_path / "escaped").exists()
    finally:
        os.close(destination_fd)
        os.close(source_fd)
