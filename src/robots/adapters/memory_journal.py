"""JSONL experience storage; callers choose a world-scoped private directory."""

import fcntl
import json
import math
import os
import re
import stat
from contextlib import suppress
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast, final, get_args

from robots.society.memory import ExperienceNote, NoteKind


def _require_private(info: os.stat_result, *, directory: bool = False) -> None:
    correct_type = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not correct_type or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        kind = "directory" if directory else "regular journal file"
        msg = f"memory {kind} must be owner-private"
        raise PermissionError(msg)
    if not directory and info.st_nlink != 1:
        msg = "memory journal must have exactly one link"
        raise PermissionError(msg)


def _open_private_root(root: Path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(root.anchor or ".", flags)
    parts = root.parts[1:] if root.anchor else root.parts
    try:
        for component in parts:
            try:
                child = os.open(component, flags, dir_fd=descriptor)
            except FileNotFoundError:
                with suppress(FileExistsError):
                    os.mkdir(component, 0o700, dir_fd=descriptor)
                child = os.open(component, flags, dir_fd=descriptor)
            parent, descriptor = descriptor, child
            try:
                # Existing entries may be from a constructor whose sync failed.
                os.fsync(parent)
            finally:
                with suppress(OSError):
                    os.close(parent)
        _require_private(os.fstat(descriptor), directory=True)
        return descriptor
    except BaseException:
        with suppress(OSError):
            os.close(descriptor)
        raise


def _decode_note(body: Any) -> ExperienceNote:
    if not isinstance(body, dict) or set(body) != {"ts", "kind", "text"}:
        msg = "invalid journal note schema"
        raise ValueError(msg)
    timestamp, kind, text = body["ts"], body["kind"], body["text"]
    valid_time = (
        isinstance(timestamp, int | float)
        and not isinstance(timestamp, bool)
        and math.isfinite(timestamp)
    )
    if not valid_time or kind not in get_args(NoteKind) or not isinstance(text, str):
        msg = "invalid journal note values"
        raise ValueError(msg)
    return ExperienceNote(ts=float(timestamp), kind=cast("NoteKind", kind), text=text)


@final
class JsonlExperienceStore:
    """One persona's journal; raw experiences are replayed into its summary tree."""

    def __init__(self, root: Path, persona_id: str) -> None:
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", persona_id) is None:
            msg = "persona_id must be a literal safe identifier"
            raise ValueError(msg)
        directory = _open_private_root(root)
        self.path = root / f"{persona_id}.jsonl"
        self._persona_id = persona_id
        self._failed = False
        self._history_validated = False
        descriptor: int | None = None
        try:
            descriptor = os.open(
                self.path.name,
                os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
                dir_fd=directory,
            )
            _require_private(os.fstat(descriptor))
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.fsync(directory)  # also sync an entry left by an earlier failed constructor
            # Retain raw-fd ownership even if text-wrapper initialization fails.
            self._file = os.fdopen(descriptor, "a+", encoding="utf-8", closefd=False)
        except BaseException:
            if descriptor is not None:
                with suppress(OSError):
                    os.close(descriptor)
            with suppress(OSError):
                os.close(directory)
            raise
        self._directory_fd = directory
        self._file_fd = descriptor

    def load(self) -> tuple[ExperienceNote, ...]:
        self._require_healthy()
        try:
            notes = self._read_notes()
        except OSError, ValueError:
            self._failed = True
            raise
        self._history_validated = True
        return notes

    def _read_notes(self) -> tuple[ExperienceNote, ...]:
        self._file.seek(0)
        notes = []
        for line in self._file:
            if not line.endswith("\n"):
                msg = "unterminated journal tail; explicit repair required"
                raise ValueError(msg)
            body = json.loads(line)
            if (
                not isinstance(body, dict)
                or not isinstance(body.get("version"), int)
                or isinstance(body.get("version"), bool)
                or body.get("version") != 1
                or body.get("persona_id") != self._persona_id
            ):
                msg = "journal owner or schema version mismatch"
                raise ValueError(msg)
            notes.append(_decode_note(body.get("note")))
        return tuple(notes)

    def append(self, note: ExperienceNote) -> None:
        self._require_healthy()
        raw_note = asdict(note)
        _decode_note(raw_note)
        if not self._history_validated:
            self.load()  # never append behind unvalidated or torn history
        self._file.seek(0, 2)
        row = {"version": 1, "persona_id": self._persona_id, "note": raw_note}
        line = json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"
        try:
            _require_private(os.fstat(self._file.fileno()))
            if self._file.write(line) != len(line):
                msg = "incomplete journal write"
                raise OSError(msg)
            self._file.flush()
            os.fsync(self._file.fileno())
        except BaseException:
            # Any escaping failure after write may leave unacknowledged bytes.
            self._failed = True
            raise

    def _require_healthy(self) -> None:
        if self._failed:
            msg = "journal failed; close and inspect/reopen before reuse"
            raise OSError(msg)

    def close(self) -> None:
        try:
            self._file.close()
        finally:
            descriptor, self._file_fd = self._file_fd, -1
            if descriptor >= 0:
                with suppress(OSError):
                    os.close(descriptor)
            descriptor, self._directory_fd = self._directory_fd, -1
            if descriptor >= 0:
                with suppress(OSError):
                    os.close(descriptor)
