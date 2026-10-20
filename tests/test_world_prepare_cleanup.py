"""Reached write/close faults on an actual owned preparation file."""

import errno
from pathlib import Path
from typing import IO, NoReturn

import pytest

from robots.adapters import world_prepare


@pytest.mark.parametrize("origin_type", [OSError, KeyboardInterrupt])
def test_close_failure_does_not_replace_active_write_error(tmp_path, monkeypatch, origin_type):
    origin = origin_type("synthetic write interruption")
    cleanup = OSError(errno.EIO, "synthetic close failure")
    real_open = Path.open
    opened = []

    class FaultingFile:
        def __init__(self, handle: IO[bytes]) -> None:
            self.handle = handle
            self.close_attempts = 0

        def fileno(self):
            return self.handle.fileno()

        def write(self, raw):
            self.handle.write(raw[:1])
            raise origin

        def close(self) -> NoReturn:
            self.close_attempts += 1
            self.handle.close()
            raise cleanup

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    def faulting_open(path, *args, **kwargs):
        wrapped = FaultingFile(real_open(path, *args, **kwargs))
        opened.append(wrapped)
        return wrapped

    monkeypatch.setattr(Path, "open", faulting_open)
    with pytest.raises(origin_type) as caught:
        world_prepare._write(tmp_path, "fixture.bin", b"synthetic-public-bytes")
    assert caught.value is origin, "close exception replaced the active write origin"
    assert len(opened) == 1
    assert opened[0].close_attempts == 1
    assert opened[0].handle.closed
