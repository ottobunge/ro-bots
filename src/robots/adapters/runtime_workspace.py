"""Fresh project workspace under ADR-018's cooperative same-UID trust policy.

No hostile-user construction receipt, mutation immunity, restart recovery or world
execution authority. Every same-UID mutator must respect the lifetime flock.
Historical events and returned data never grant admission. Unknown roots are refused.
"""

import fcntl
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from threading import RLock
from typing import Literal

from robots.adapters import rathena_runtime
from robots.adapters.rathena_runtime_assets import public_assets
from robots.adapters.rathena_runtime_io import (
    check_output,
    close_owned,
    create_root,
    decode_input,
    directory,
    literal_parts,
    read_at,
    reject,
    verify_binding,
    write_at,
)
from robots.adapters.runtime_publication_io import move_directory_noreplace
from robots.adapters.runtime_publication_journal import (
    JournalCleanupOwnership,
    JournalRecord,
    PublicationJournal,
)
from robots.adapters.runtime_tree_sync import sync_private_tree

MARKER = b"ro-bots cooperative runtime workspace v1\nNo world execution authority.\n"
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


@dataclass(frozen=True)
class PublicationReceipt:
    """Current-session publication observation only; not a capability or grant."""

    transaction_id: str
    generation: str
    session_id: str
    world: str
    manifest: dict[str, object]
    phase: Literal["committed"] = "committed"
    launchable: Literal[False] = False
    admission_state: Literal["denied"] = "denied"


class RuntimeWorkspace:
    """Explicit NEW initializer: existing roots, even empty/private, are rejected.

    Root selection belongs to trusted project/operator configuration, not publish
    callers. The only publication destination is the internally managed worlds
    namespace. No open/recover API: restart always refuses this existing root.
    """

    def __init__(self, root: Path) -> None:
        literal_parts(root)
        self._root_path = root
        self._mutex = RLock()
        self._owner_pid = os.getpid()
        self._session = uuid.uuid4().hex
        self._handles: dict[str, JournalCleanupOwnership] = {}
        self._journal: PublicationJournal | None = None
        self._closed = False
        self._poisoned = False
        self.phase = "uninitialized"
        self._current: tuple[str, str] | None = None
        try:
            self._initialize()
        except BaseException as origin:
            self._poisoned = True
            journal_cleanup = getattr(origin, "journal_cleanup_ownership", None)
            if isinstance(journal_cleanup, JournalCleanupOwnership):
                self._handles["failed_journal"] = journal_cleanup
            self.close()
            origin.__dict__["workspace_cleanup_ownership"] = self.cleanup_ownership
            origin.add_note(f"Workspace initialization denied; cleanup={self.cleanup_status}.")
            raise

    def _retain(self, name: str, fd: int) -> int:
        self._handles[name] = JournalCleanupOwnership(fd, self._owner_pid)
        info = os.fstat(fd)
        self._handles[name] = replace(
            self._handles[name], expected_identity=(info.st_dev, info.st_ino)
        )
        return fd

    def _fd(self, name: str) -> int:
        return self._handles[name].descriptor

    def _initialize(self) -> None:
        with directory(self._root_path.parent) as parent:
            self._retain("parent", os.dup(parent))
            self._retain("root", create_root(parent, self._root_path.name))
        root = self._fd("root")
        lock = self._retain(
            "lock",
            os.open(
                "manager.lock",
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=root,
            ),
        )
        check_output(os.fstat(lock))
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        write_at(root, "PROJECT", MARKER)
        marker_info = os.stat("PROJECT", dir_fd=root, follow_symlinks=False)
        self._marker_identity = (marker_info.st_dev, marker_info.st_ino)
        for name in ("staging", "worlds"):
            self._retain(name, create_root(root, name))
        self._journal = PublicationJournal(root)
        for name in ("staging", "worlds", "root", "parent"):
            os.fsync(self._fd(name))
        self._binding()
        self.phase = "ready"

    def _bound_entry(self, parent: int, name: str, handle: str, *, file: bool = False) -> None:
        owned = self._handles[handle]
        for info in (
            os.fstat(owned.descriptor),
            os.stat(name, dir_fd=parent, follow_symlinks=False),
        ):
            check_output(info, is_directory=not file)
            if (info.st_dev, info.st_ino) != owned.expected_identity or (
                file and info.st_nlink != 1
            ):
                reject("workspace managed binding changed")

    def _binding(self) -> None:
        self._bound_entry(self._fd("parent"), self._root_path.name, "root")
        verify_binding(self._root_path, os.fstat(self._fd("parent")), os.fstat(self._fd("root")))
        for name in ("staging", "worlds"):
            self._bound_entry(self._fd("root"), name, name)
        self._bound_entry(self._fd("root"), "manager.lock", "lock", file=True)
        marker_info = os.stat("PROJECT", dir_fd=self._fd("root"), follow_symlinks=False)
        if (
            marker_info.st_nlink != 1
            or (marker_info.st_dev, marker_info.st_ino) != self._marker_identity
            or read_at(self._fd("root"), "PROJECT", output=marker_info) != MARKER
        ):
            reject("workspace project registration changed")

    @property
    def records(self) -> tuple[JournalRecord, ...]:
        return self._journal.records if self._journal is not None else ()

    @property
    def cleanup_ownership(self) -> tuple[JournalCleanupOwnership, ...]:
        rows = tuple(self._handles.values())
        return rows + ((self._journal.cleanup_ownership,) if self._journal is not None else ())

    @property
    def cleanup_status(self) -> str:
        states = {row.status for row in self.cleanup_ownership}
        if "unresolved" in states:
            return "unresolved"
        return "active" if "active" in states else "released_observed"

    def _release(self, names: tuple[str, ...]) -> None:
        first: BaseException | None = None
        for name in names:
            row = self._handles[name]
            if row.close_attempted:
                continue
            self._handles[name] = replace(row, close_attempted=True, status="unresolved")
            try:
                close_owned(row.descriptor)
            except BaseException as error:
                first = first or error
            finally:
                observed, diagnostic = self._handles[name]._after_attempt()
                self._handles[name] = observed
                first = first or diagnostic
        if first is not None:
            raise first

    def _event(self, event: str, reason: str = "none") -> None:
        if self._journal is None or self._current is None:
            reject("workspace has no registered transaction")
        transaction, world = self._current
        self._journal.append(transaction, world, event, reason)
        self.phase = event

    def _stage(self, world: str, raw: bytes) -> dict[str, object]:
        if self._current is None:
            reject("workspace has no registered transaction")
        transaction = self._current[0]
        self._retain("transaction", create_root(self._fd("staging"), transaction))
        os.fsync(self._fd("staging"))
        self._binding()
        destination = self._root_path / "staging" / transaction / world
        # Builder's path reopening is conditional on the cooperating namespace.
        manifest = rathena_runtime.build_from_bytes(world, destination, raw)
        self._binding()
        self._bound_entry(self._fd("staging"), transaction, "transaction")
        self._retain("candidate", os.open(world, DIRECTORY_FLAGS, dir_fd=self._fd("transaction")))
        self._bound_entry(self._fd("transaction"), world, "candidate")
        self._readback(manifest)
        if manifest.get("world") != world or manifest.get("launchable") is not False:
            reject("offline manifest required")
        sync_private_tree(self._fd("candidate"))
        self._bound_entry(self._fd("transaction"), world, "candidate")
        os.fsync(self._fd("transaction"))
        self._event("prepared")
        return manifest

    def _readback(self, manifest: dict[str, object]) -> None:
        info = os.stat("manifest.json", dir_fd=self._fd("candidate"), follow_symlinks=False)
        if (
            info.st_nlink != 1
            or json.loads(read_at(self._fd("candidate"), "manifest.json", output=info)) != manifest
        ):
            reject("managed manifest readback mismatch")

    def _publish(self, world: str, manifest: dict[str, object]) -> None:
        self._binding()
        if self._current is None:
            reject("workspace has no registered transaction")
        self._bound_entry(self._fd("staging"), self._current[0], "transaction")
        self._bound_entry(self._fd("transaction"), world, "candidate")
        # No atomic provenance claim: source-kind check requires cooperative mutators.
        self.phase = "rename_attempted"
        move_directory_noreplace(self._fd("transaction"), world, self._fd("worlds"), world)
        self.phase = "renamed"
        for name in ("transaction", "worlds", "candidate", "staging", "root"):
            os.fsync(self._fd(name))
        self._binding()
        self._bound_entry(self._fd("worlds"), world, "candidate")
        self._readback(manifest)
        self._event("committed")
        if self._journal is None or not self._journal.acknowledged_in_this_generation(
            self._current[0]
        ):
            reject("current journal acknowledgement required")

    def _failed(self, origin: BaseException) -> None:
        self._poisoned = True
        prior = self.phase
        event = "uncertain" if prior in {"rename_attempted", "renamed"} else "quarantined"
        try:
            self._event(event, "cleanup_failure" if prior == "committed" else "io_failure")
        except BaseException:
            origin.add_note(
                "Workspace failure event unacknowledged; retained state denies admission."
            )
        self.phase = event
        origin.add_note(
            f"Workspace phase={event}; no receipt or admission; retained bytes not deleted."
        )

    @staticmethod
    def _validate_input(world: str, raw: bytes) -> None:
        if (
            type(world) is not str
            or re.fullmatch(r"(?:test|debug|prod-[A-Za-z0-9][A-Za-z0-9_-]{0,13})", world) is None
        ):
            reject("explicit literal world identity required")
        if type(raw) is not bytes:
            reject("exact private input bytes required")
        rathena_runtime.validate(decode_input(raw), world)

    def _release_transaction(self, origin: BaseException | None = None) -> None:
        try:
            self._release(
                tuple(name for name in ("candidate", "transaction") if name in self._handles)
            )
        except BaseException:
            if origin is None:
                raise
            origin.add_note("Transaction cleanup also failed; retain ownership, never retry.")

    def _complete(self, world: str, raw: bytes) -> PublicationReceipt:
        self._binding()
        # Missing pinned dependencies are rejected before durable intent/allocation.
        public_assets()
        self._event("intent")
        manifest = self._stage(world, raw)
        self._publish(world, manifest)
        self._release_transaction()
        if self.cleanup_status == "unresolved":
            reject("transaction cleanup ownership unresolved")
        if self._journal is None or self._current is None:
            reject("workspace journal and current transaction required")
        return PublicationReceipt(
            self._current[0], self._journal.generation, self._session, world, manifest
        )

    def publish_world(self, world: str, raw: bytes) -> PublicationReceipt:
        """Validate before intent/allocation; publish only inside registered namespaces."""
        self._validate_input(world, raw)
        with self._mutex:
            if self._closed or self._poisoned:
                reject("workspace unavailable; explicit recovery required")
            self._current = (uuid.uuid4().hex, world)
            try:
                return self._complete(world, raw)
            except BaseException as origin:
                self._failed(origin)
                self._release_transaction(origin)
                raise
            finally:
                self._current = None

    def close(self) -> None:
        """Attempt each owned close once, retaining unresolved process ownership."""
        with self._mutex:
            if self._closed:
                return
            self._closed = True
            first: BaseException | None = None
            try:
                if self._journal is not None:
                    self._journal.close()
            except BaseException as error:
                first = error
            try:
                self._release(tuple(reversed(self._handles)))
            except BaseException as error:
                first = first or error
            if first is not None:
                self._poisoned = True
                self.phase = "quarantined"
                primary = sys.exception()
                if primary is None:
                    raise first
                primary.add_note("Workspace cleanup failed; retained ownership, no retry.")
