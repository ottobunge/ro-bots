"""Private historical events, never workspace/publication/world admission authority.

Borrow a caller-owned directory fd. No construction identity or same-UID exclusion
is established here; flock serializes cooperative writers only. Acknowledgement
means this process synced and read back one journal append, NOT a runtime tree.
Restart restores history only and cannot acknowledge old records.
Unbuffered os.write has no userspace flush stage. Short writes poison without retry.
Binding checks anchor the borrowed root inode and its fixed journal entry; they
cannot prove the root still occupies an arbitrary external pathname or exclude
privileged/same-UID races. No tree, manager, recovery or admission API is present.
"""

import errno
import fcntl
import json
import os
import re
import sys
import uuid
from dataclasses import asdict, dataclass, replace
from threading import RLock
from typing import Literal, NoReturn

from robots.adapters.rathena_runtime_io import check_output, close_owned, unique_object

BASENAME = "publication-journal.jsonl"
MAX_RECORD_BYTES = 4096
MAX_RECORDS = 8192
MAX_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class JournalCleanupOwnership:
    """Retained process ownership evidence, never permission to retry a close.

    Descriptor numbers and inode observations cannot prove continuous identity.
    Retain unresolved evidence until controlled teardown of the owning process.
    """

    descriptor: int
    owner_pid: int
    expected_identity: tuple[int, int] | None = None
    close_attempted: bool = False
    status: Literal["active", "released_observed", "unresolved"] = "active"
    observation: str = "not_attempted"

    def _after_attempt(self) -> tuple[JournalCleanupOwnership, BaseException | None]:
        diagnostic: BaseException | None = None
        try:
            info = os.fstat(self.descriptor)
        except OSError as error:
            if error.errno == errno.EBADF:
                return (
                    replace(self, status="released_observed", observation="descriptor_absent"),
                    None,
                )
        except BaseException as error:
            if not isinstance(error, Exception):
                diagnostic = error
        else:
            identity = (info.st_dev, info.st_ino)
            observation = "descriptor_present"
            if self.expected_identity is None:
                observation = "identity_unknown"
            elif identity != self.expected_identity:
                observation = "descriptor_reused"
            return replace(self, status="unresolved", observation=observation), None
        return replace(self, status="unresolved", observation="diagnostic_failed"), diagnostic


@dataclass(frozen=True)
class JournalRecord:
    """Schema 1 historical event, not the proposed schema 2 publication receipt."""

    version: int
    transaction_id: str
    world: str
    generation: str
    event: str
    reason: str


def _encode(record: JournalRecord) -> bytes:
    return (json.dumps(asdict(record), sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _validate(record: JournalRecord) -> None:
    if type(record.version) is not int or record.version != 1:
        _reject()
    patterns = (
        (record.transaction_id, r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}"),
        (record.world, r"(?:test|debug|prod-[A-Za-z0-9][A-Za-z0-9_-]{0,13})"),
        (record.generation, r"[a-f0-9]{32}"),
    )
    for value, pattern in patterns:
        if type(value) is not str or re.fullmatch(pattern, value) is None:
            _reject()
    if type(record.event) is not str or record.event not in {
        "intent",
        "prepared",
        "committed",
        "uncertain",
        "quarantined",
    }:
        _reject()
    if type(record.reason) is not str or record.reason not in {
        "none",
        "io_failure",
        "binding_lost",
        "cleanup_failure",
        "recovery_required",
    }:
        _reject()


def _reject() -> NoReturn:
    message = "journal record or phase rejected"
    raise ValueError(message)


def _transition(record: JournalRecord, phases: dict[str, JournalRecord]) -> None:
    previous = phases.get(record.transaction_id)
    if previous is None:
        if record.event != "intent":
            _reject()
        return
    allowed = {
        "intent": {"prepared", "uncertain", "quarantined"},
        "prepared": {"committed", "uncertain", "quarantined"},
        "committed": {"quarantined"},
    }
    if (
        record.world != previous.world
        or record.generation != previous.generation
        or record.event not in allowed.get(previous.event, set())
    ):
        _reject()


def _decode_line(line: bytes) -> JournalRecord:
    if len(line) > MAX_RECORD_BYTES:
        _reject()
    try:
        data = json.loads(line.decode("utf-8", errors="strict"), object_pairs_hook=unique_object)
    except ValueError, UnicodeError, RecursionError:
        _reject()
    if type(data) is not dict or set(data) != {
        "version",
        "transaction_id",
        "world",
        "generation",
        "event",
        "reason",
    }:
        _reject()
    record = JournalRecord(**data)
    _validate(record)
    if _encode(record) != line:
        _reject()
    return record


def _decode(raw: bytes) -> tuple[JournalRecord, ...]:
    if len(raw) > MAX_BYTES or (raw and not raw.endswith(b"\n")):
        _reject()
    lines = raw.splitlines(keepends=True)
    if len(lines) > MAX_RECORDS:
        _reject()
    records = []
    phases: dict[str, JournalRecord] = {}
    for line in lines:
        record = _decode_line(line)
        _transition(record, phases)
        phases[record.transaction_id] = record
        records.append(record)
    return tuple(records)


def _redact(error: BaseException) -> None:
    if isinstance(error, OSError):
        error.strerror = "journal I/O failed"
        error.filename = None
        error.filename2 = None
        error.args = (error.errno, error.strerror)


class PublicationJournal:
    """Single cooperative writer; caller must keep the borrowed root fd valid."""

    def __init__(self, root_fd: int) -> None:
        if type(root_fd) is not int or root_fd < 0:
            _reject()
        self._lock = RLock()
        self._root = root_fd
        self._root_info = os.fstat(root_fd)
        check_output(self._root_info, is_directory=True)
        self._poisoned = False
        self._closed = False
        owner_pid = os.getpid()
        self._fd = os.open(
            BASENAME,
            os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK,
            0o600,
            dir_fd=root_fd,
        )
        self._cleanup_ownership = JournalCleanupOwnership(self._fd, owner_pid)
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._file_info = os.fstat(self._fd)
            self._cleanup_ownership = replace(
                self._cleanup_ownership,
                expected_identity=(self._file_info.st_dev, self._file_info.st_ino),
            )
            self._binding()
            self._generation = uuid.uuid4().hex
            self._acknowledged: set[str] = set()
            self._records = _decode(self._read())
            self._phases = {record.transaction_id: record for record in self._records}
            self._binding()
        except BaseException as error:
            _redact(error)
            self.close()
            error.journal_cleanup_ownership = self.cleanup_ownership  # type: ignore[attr-defined]
            if self.cleanup_ownership.status == "unresolved":
                error.add_note(
                    "Journal writer cleanup unresolved; retain journal_cleanup_ownership "
                    "until controlled owner-process teardown. Do not retry descriptor close."
                )
            raise

    @property
    def generation(self) -> str:
        return self._generation

    @property
    def records(self) -> tuple[JournalRecord, ...]:
        with self._lock:
            return self._records

    def _binding(self) -> None:
        root = os.fstat(self._root)
        check_output(root, is_directory=True)
        if (root.st_dev, root.st_ino) != (self._root_info.st_dev, self._root_info.st_ino):
            _reject()
        opened = os.fstat(self._fd)
        named = os.stat(BASENAME, dir_fd=self._root, follow_symlinks=False)
        for info in (opened, named):
            check_output(info)
            if info.st_nlink != 1 or (info.st_dev, info.st_ino) != (
                self._file_info.st_dev,
                self._file_info.st_ino,
            ):
                _reject()

    def _live(self) -> None:
        if self._closed or self._poisoned:
            _reject()

    def _read(self) -> bytes:
        if os.fstat(self._fd).st_size > MAX_BYTES:
            _reject()
        return os.pread(self._fd, MAX_BYTES + 1, 0)

    def append(self, transaction_id: str, world: str, event: str, reason: str) -> None:
        with self._lock:
            record = JournalRecord(1, transaction_id, world, self._generation, event, reason)
            _validate(record)
            _transition(record, self._phases)
            raw = _encode(record)
            self._live()
            if len(self._records) >= MAX_RECORDS or len(raw) > MAX_RECORD_BYTES:
                _reject()
            try:
                self._binding()
                previous = self._read()
                if previous != b"".join(_encode(item) for item in self._records):
                    _reject()
                if len(self._records) >= MAX_RECORDS or len(previous) + len(raw) > MAX_BYTES:
                    _reject()
                if os.write(self._fd, raw) != len(raw):
                    _reject()
                os.fsync(self._fd)
                os.fsync(self._root)
                if self._read() != previous + raw:
                    _reject()
                self._binding()
            except BaseException as error:
                self._poisoned = True
                _redact(error)
                raise
            self._records += (record,)
            self._phases[transaction_id] = record
            self._acknowledged.add(transaction_id)

    def acknowledged_in_this_generation(self, transaction_id: str) -> bool:
        """Volatile journal-event acknowledgement only; never a permission check.

        Ordinary binding exceptions poison and deny. Nonlocal origins poison and
        propagate unchanged; subsequent calls deny without another binding check.
        """
        with self._lock:
            if (
                type(transaction_id) is not str
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", transaction_id) is None
            ):
                _reject()
            if self._closed or self._poisoned:
                return False
            try:
                self._binding()
            except BaseException as error:
                self._poisoned = True
                if not isinstance(error, Exception):
                    raise
                return False
            return transaction_id in self._acknowledged

    def close(self) -> None:
        """Attempt once; consult cleanup_ownership, not this return, for status.

        Repeated calls never retry a possibly released/reused descriptor. An
        unresolved snapshot remains pending ownership, not completed cleanup.
        Sole nonlocal diagnostic origins propagate after retaining the snapshot;
        ordinary diagnostic errors remain unresolved, and active primary failures win.
        """
        with self._lock:
            if not self._closed:
                self._closed = True
                self._cleanup_ownership = replace(
                    self._cleanup_ownership, close_attempted=True, status="unresolved"
                )
                try:
                    close_owned(self._fd)
                except BaseException as error:
                    _redact(error)
                    raise
                finally:
                    primary = sys.exception()
                    self._cleanup_ownership, diagnostic = self._cleanup_ownership._after_attempt()
                    if primary is None and diagnostic is not None:
                        raise diagnostic

    @property
    def cleanup_ownership(self) -> JournalCleanupOwnership:
        """Snapshot under the call lock; unresolved is not successful cleanup."""
        with self._lock:
            return self._cleanup_ownership
