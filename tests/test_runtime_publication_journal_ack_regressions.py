"""Reached nonlocal-control-flow regression; private owned files only."""

import os
import traceback
from pathlib import Path

import pytest

from robots.adapters import runtime_publication_journal as publication


class Cancellation(BaseException):
    """Synthetic nonlocal cancellation outside Exception."""


@pytest.mark.parametrize("kind", [KeyboardInterrupt, SystemExit, GeneratorExit, Cancellation])
def test_acknowledgement_preserves_interrupt_origin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: type[BaseException]
) -> None:
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    borrowed = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    log = publication.PublicationJournal(borrowed)
    original_stat = os.stat
    origin = kind()
    reached: list[str] = []

    def fault_stat(*args: object, **kwargs: object) -> os.stat_result:
        if args and args[0] == publication.BASENAME and kwargs.get("dir_fd") == borrowed:
            reached.append("entry-stat")
            raise origin
        return original_stat(*args, **kwargs)  # type: ignore[arg-type]

    try:
        log.append("transaction", "test", "intent", "none")
        assert log.acknowledged_in_this_generation("transaction") is True
        observed: BaseException | None = None
        with monkeypatch.context() as scoped:
            scoped.setattr(os, "stat", fault_stat)
            try:
                log.acknowledged_in_this_generation("transaction")
            except BaseException as error:
                observed = error
        assert reached == ["entry-stat"]
        assert origin.__traceback__ is not None
        assert any(
            frame.name == "fault_stat" for frame in traceback.extract_tb(origin.__traceback__)
        )
        assert observed is origin, "acknowledgement swallowed nonlocal control flow"
        assert log.acknowledged_in_this_generation("transaction") is False
        with pytest.raises(ValueError, match="journal"):
            log.append("next", "test", "intent", "none")
    finally:
        log.close()
        os.fstat(borrowed)
        os.close(borrowed)


@pytest.mark.parametrize("kind", [OSError, ValueError])
def test_acknowledgement_ordinary_binding_failure_denies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: type[Exception]
) -> None:
    root = tmp_path / "owned"
    root.mkdir(mode=0o700)
    borrowed = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    log = publication.PublicationJournal(borrowed)
    original_stat = os.fstat
    reached: list[int] = []
    origin = kind()

    def fault_stat(fd: int) -> os.stat_result:
        if fd == borrowed:
            reached.append(fd)
            raise origin
        return original_stat(fd)

    try:
        log.append("transaction", "test", "intent", "none")
        assert log.acknowledged_in_this_generation("transaction")
        with monkeypatch.context() as patch:
            patch.setattr(os, "fstat", fault_stat)
            assert log.acknowledged_in_this_generation("transaction") is False
        assert reached == [borrowed]
        assert origin.__traceback__ is not None
        assert log.acknowledged_in_this_generation("transaction") is False
        with pytest.raises(ValueError, match="journal"):
            log.append("next", "test", "intent", "none")
    finally:
        log.close()
        original_stat(borrowed)
        os.close(borrowed)
