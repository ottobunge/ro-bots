"""Private MVP checkpoints; no raw-log, provider, migration or activation effects.

Caller supplies a private fresh root and a VERIFIED owned raw-prefix count/digest.
Shape validation is not proof or resource authority. The trusted immutable node
port supplies original UTF-8 text (512 bytes maximum), not rendered flat lines.
Older prefixes require explicit future replay; no actual-host-total claim is made.
"""

import fcntl
import hashlib
import json
import os
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from types import TracebackType
from typing import Any, Protocol

from robots.adapters.memory_journal import _open_private_root, _require_private
from robots.society.optchat_view import IncrementalView, NodeCoordinate, ViewPolicy

NodeText = Callable[[NodeCoordinate], str | None]
MAX_CHECKPOINT_BYTES = 1_048_576


@dataclass(frozen=True)
class SourcePrefixBinding:
    """Count/digest verified against actual owned raw bytes by the caller."""

    source_count: int
    sha256: str

    def __post_init__(self) -> None:
        if type(self.source_count) is not int or not 0 <= self.source_count <= 1_000_000:
            message = "Source prefix count must be an exact bounded integer"
            raise ValueError(message)
        if type(self.sha256) is not str or re.fullmatch(r"[a-f0-9]{64}", self.sha256) is None:
            message = "Source prefix digest must be lowercase SHA256"
            raise ValueError(message)


class ViewStore(Protocol):
    def save(
        self, view: IncrementalView, prefix: SourcePrefixBinding, node_text: NodeText
    ) -> None: ...

    def load(self, prefix: SourcePrefixBinding, node_text: NodeText) -> IncrementalView: ...

    def close(self) -> None: ...


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            message = "Duplicate checkpoint member"
            raise ValueError(message)
        result[key] = value
    return result


def _bound_restore(
    snapshot: object, node_text: NodeText, policy: ViewPolicy
) -> tuple[IncrementalView, str]:
    digest = hashlib.sha256(b"optchat-view-nodes-v1\0")

    def checked(node: NodeCoordinate) -> str | None:
        text = node_text(node)
        if type(text) is not str:
            message = "Missing or non-text immutable node"
            raise ValueError(message)
        raw = text.encode("utf-8")
        if len(raw) > 512:
            message = "Immutable node exceeds 512 UTF-8 bytes"
            raise ValueError(message)
        for value in (node.level, node.index, len(raw)):
            digest.update(value.to_bytes(8, "big"))
        digest.update(raw)
        return text

    view = IncrementalView.restore(snapshot, checked, expected_policy=policy)
    return view, digest.hexdigest()


class PrivateViewStore:
    """One lifetime writer within ADR-018's trusted same-UID boundary.

    Initialize ONLY by explicitly saving an empty view with a verified zero prefix.
    Missing/corrupt checkpoints never load as empty. Load failures close this owner.
    Uncertain writes poison until explicit close/reopen/validation; post-rename
    directory-sync failure may have committed, and is NOT a rollback receipt.
    Failed private random pending files are retained, never swept or retried.
    Close attempts each fd once; interrupted release remains unconfirmed and must
    be handled explicitly, never automatically retried against a possibly reused fd.
    On failed cleanup, retrieve the owner without custom exception attributes via
    BaseException.__dict__["__dict__"].__get__(origin)["view_store_owner"].
    If metadata allocation itself fails, the origin still propagates; a returned
    store's unconfirmed_ownership remains available, but constructor handoff may fail.
    The reused root helper's inherited interruption limits are not strengthened.
    """

    def __init__(self, root: Path, world: str, persona: str, policy: ViewPolicy) -> None:
        for identity in (world, persona, policy.namespace):
            if (
                type(identity) is not str
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", identity) is None
            ):
                message = "View identities must be literal safe identifiers"
                raise ValueError(message)
        self._directory = self._lock_fd = self._pending_fd = self._read_fd = -1
        self._close_attempted: set[str] = set()
        self._mutex = RLock()
        self._failed = False
        self._committed_digest: str | None = None
        self._read_digest = ""
        self._identity = (world, persona)
        self.policy = policy
        _require_private(root.lstat(), directory=True)
        self.path = root / "view-state" / world / persona / policy.namespace / "view.json"
        try:
            self._directory = _open_private_root(self.path.parent)
            for parent in (root / "view-state", *list(self.path.parents)[:3]):
                _require_private(parent.lstat(), directory=True)
            self._lock_fd = os.open(
                "writer.lock",
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
                dir_fd=self._directory,
            )
            _require_private(os.fstat(self._lock_fd))
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.fsync(self._directory)
            self._check_checkpoint()
        except BaseException as origin:
            self._cleanup_origin(origin)
            raise

    @property
    def unconfirmed_ownership(self) -> tuple[int, ...]:
        """Possibly held/released fds; not proof of physical release."""
        return tuple(
            getattr(self, name) for name in self._close_attempted if getattr(self, name) >= 0
        )

    def _cleanup_origin(self, origin: BaseException) -> None:
        try:
            self.close()
        except BaseException:
            try:
                # Bypass subclass properties/getters/setters and diagnostic dict hooks.
                metadata = BaseException.__dict__["__dict__"].__get__(origin)
                dict.__setitem__(metadata, "view_store_owner", self)
            except BaseException:
                # Secondary diagnostics must never mask the reached origin.
                pass

    def _healthy(self) -> None:
        if self._failed or self._directory < 0:
            message = "View store failed or closed; explicit close/reopen required"
            raise OSError(message)

    def _check_checkpoint(self) -> bool:
        try:
            info = os.stat("view.json", dir_fd=self._directory, follow_symlinks=False)
        except FileNotFoundError:
            return False
        _require_private(info)
        return True

    def save(self, view: IncrementalView, prefix: SourcePrefixBinding, node_text: NodeText) -> None:
        with self._mutex:
            self._healthy()
            self._validate_prior(view)
            snapshot = view.snapshot()
            if prefix.source_count != view.state.source_count:
                message = "Source prefix count does not match view"
                raise ValueError(message)
            restored, digest = _bound_restore(snapshot, node_text, self.policy)
            if restored.read() != view.read():
                message = "Node text changed since view construction"
                raise ValueError(message)
            data = {
                "version": 1,
                "world": self._identity[0],
                "persona": self._identity[1],
                "source_count": prefix.source_count,
                "source_sha256": prefix.sha256,
                "snapshot": snapshot,
                "nodes_sha256": digest,
            }
            payload = json.dumps(
                data, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
            ).encode()
            if len(payload) > MAX_CHECKPOINT_BYTES:
                message = "Checkpoint exceeds the explicit 1 MiB MVP limit"
                raise ValueError(message)
            self._publish(payload)
            self._committed_digest = hashlib.sha256(payload).hexdigest()

    def _validate_prior(self, view: IncrementalView) -> None:
        if not self._check_checkpoint():
            if self._committed_digest is not None or view.state.source_count:
                message = "Missing checkpoint requires explicit fresh empty initialization"
                raise ValueError(message)
            return
        if self._committed_digest is None:
            message = "Existing checkpoint requires explicit bound load before save"
            raise ValueError(message)
        try:
            self._read_checkpoint()
            if self._read_digest != self._committed_digest:
                message = "Committed checkpoint changed; explicit inspection required"
                raise ValueError(message)
        except BaseException:
            self._failed = True
            raise

    def _publish(self, payload: bytes) -> None:
        pending = "pending-" + secrets.token_hex(16)
        try:
            self._pending_fd = os.open(
                pending,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=self._directory,
            )
            _require_private(os.fstat(self._pending_fd))
            offset = 0
            while offset < len(payload):
                written = os.write(self._pending_fd, payload[offset:])
                if not 0 < written <= len(payload) - offset:
                    message = "Incomplete checkpoint write"
                    raise OSError(message)
                offset += written
            os.fsync(self._pending_fd)
            self._release("_pending_fd")
            self._check_checkpoint()
            os.replace(pending, "view.json", src_dir_fd=self._directory, dst_dir_fd=self._directory)
            os.fsync(self._directory)
        except BaseException:
            self._failed = True
            raise

    def load(self, prefix: SourcePrefixBinding, node_text: NodeText) -> IncrementalView:
        with self._mutex:
            self._healthy()
            try:
                data = self._read_checkpoint()
                view = self._restore(data, prefix, node_text)
                self._committed_digest = self._read_digest
                return view
            except BaseException as origin:
                self._cleanup_origin(origin)
                raise

    def _read_checkpoint(self) -> dict[str, Any]:
        self._read_fd = os.open(
            "view.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self._directory
        )
        _require_private(os.fstat(self._read_fd))
        chunks = bytearray()
        while len(chunks) <= MAX_CHECKPOINT_BYTES:
            part = os.read(self._read_fd, min(65536, MAX_CHECKPOINT_BYTES + 1 - len(chunks)))
            if not part:
                break
            chunks.extend(part)
        self._release("_read_fd")
        if len(chunks) > MAX_CHECKPOINT_BYTES:
            message = "Checkpoint exceeds the explicit 1 MiB MVP limit"
            raise ValueError(message)
        data = json.loads(chunks, object_pairs_hook=_unique_object)
        fields = {
            "version",
            "world",
            "persona",
            "source_count",
            "source_sha256",
            "snapshot",
            "nodes_sha256",
        }
        if (
            type(data) is not dict
            or set(data) != fields
            or type(data["version"]) is not int
            or data["version"] != 1
        ):
            message = "Invalid exact checkpoint schema"
            raise ValueError(message)
        self._read_digest = hashlib.sha256(chunks).hexdigest()
        return data

    def _restore(
        self, data: dict[str, Any], prefix: SourcePrefixBinding, node_text: NodeText
    ) -> IncrementalView:
        if (data["world"], data["persona"]) != self._identity:
            message = "View identity mismatch"
            raise ValueError(message)
        if SourcePrefixBinding(data["source_count"], data["source_sha256"]) != prefix:
            message = "Source prefix mismatch"
            raise ValueError(message)
        view, digest = _bound_restore(data["snapshot"], node_text, self.policy)
        if view.state.source_count != prefix.source_count or digest != data["nodes_sha256"]:
            message = "Node closure or source count mismatch"
            raise ValueError(message)
        return view

    def _release(self, name: str) -> None:
        descriptor = getattr(self, name)
        self._close_attempted.add(name)
        os.close(descriptor)
        setattr(self, name, -1)
        self._close_attempted.remove(name)

    def close(self) -> None:
        with self._mutex:
            self._failed = True
            first: tuple[BaseException, TracebackType | None] | None = None
            for name in ("_pending_fd", "_read_fd", "_lock_fd", "_directory"):
                if getattr(self, name) >= 0 and name not in self._close_attempted:
                    try:
                        self._release(name)
                    except BaseException as error:
                        if first is None:
                            first = (error, error.__traceback__)
            if first is not None:
                raise first[0].with_traceback(first[1])
            if self.unconfirmed_ownership:
                message = "View store close ownership remains unconfirmed; no automatic fd retry"
                raise OSError(message)
