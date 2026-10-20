"""Private source-bound summary stream, encoded in a separate journal subtree.

The audited experience backend supplies private/no-follow opens, lifetime flock,
fsync acknowledgement and uncertain-write poisoning. Its ``other``/timestamp-zero
rows are storage envelopes ONLY, never experiences presented to an agent.
Bounds: 8192 nodes, level <=20, 1,000,000 source notes, 65536 bytes/source text,
4096 bytes/summary, 16384 bytes/encoded row. Identity/policy IDs are literal safe
ASCII identifiers. Policy is caller configuration, not proof of model weights.
Cooperative locks do not protect against a hostile process with the same UID.
"""

import hashlib
import json
import math
import re
from collections.abc import Sequence
from pathlib import Path
from threading import RLock
from typing import Any, Never, final, get_args

from robots.adapters.memory_journal import JsonlExperienceStore
from robots.society.memory import ExperienceNote, NoteKind, SummaryNode

MAX_NODES = 8192
MAX_LEVEL = 20
MAX_SOURCE_NOTES = 1_000_000
MAX_SUMMARY_BYTES = 4096
MAX_RECORD_BYTES = 16384
MAX_NOTE_BYTES = 65536
_FIELDS = {
    "version",
    "purpose",
    "world",
    "persona",
    "policy",
    "level",
    "index",
    "source_count",
    "source_digest",
    "summary",
}


def _invalid(reason: str) -> Never:
    msg = f"invalid summary cache: {reason}"
    raise ValueError(msg)


def _canonical(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    )


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _invalid("duplicate field")
        result[key] = value
    return result


def _identifier(value: str) -> str:
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", value) is None:
        _invalid("identity must be a literal safe identifier")
    return value


def _summary(value: str) -> None:
    if type(value) is not str or len(value) > MAX_SUMMARY_BYTES:
        _invalid("summary type or size")
    if len(value.encode("utf-8")) > MAX_SUMMARY_BYTES or any(
        ord(char) < 32 or 127 <= ord(char) <= 159 or char in "\u2028\u2029" for char in value
    ):
        _invalid("summary must be one bounded UTF-8 line")


def _coordinate(node: SummaryNode, source_count: int) -> None:
    if type(node) is not SummaryNode:
        _invalid("node type")
    if type(node.level) is not int or not 0 <= node.level <= MAX_LEVEL:
        _invalid("level bound")
    if type(node.index) is not int or not 0 <= node.index < MAX_SOURCE_NOTES:
        _invalid("index bound")
    if (node.index + 1) * (1 << node.level) > source_count:
        _invalid("incomplete source coverage")
    _summary(node.text)


def _note_encoding(note: object) -> bytes:
    if type(note) is not ExperienceNote:
        _invalid("source note type")
    timestamp: object = note.ts
    kind: object = note.kind
    text: object = note.text
    if (
        type(timestamp) not in (int, float)
        or not isinstance(timestamp, int | float)
        or not math.isfinite(timestamp)
    ):
        _invalid("source timestamp")
    if type(kind) is not str or kind not in get_args(NoteKind):
        _invalid("source kind")
    if type(text) is not str or len(text) > MAX_NOTE_BYTES:
        _invalid("source text type or bound")
    if len(text.encode("utf-8")) > MAX_NOTE_BYTES:
        _invalid("source text byte bound")
    return _canonical([float(timestamp), kind, text]).encode("utf-8")


def _source_digest(notes: Sequence[ExperienceNote], count: int) -> str:
    if type(count) is not int or not 0 <= count <= MAX_SOURCE_NOTES or count > len(notes):
        _invalid("source count or truncation")
    digest = hashlib.sha256()
    for index in range(count):
        encoded = _note_encoding(notes[index])
        digest.update(encoded)
        digest.update(b"\n")
    return digest.hexdigest()


def _storage_text(outer: Any) -> str:
    if type(outer) is not dict or set(outer) != {"version", "persona_id", "note"}:
        _invalid("storage envelope schema")
    if type(outer["version"]) is not int or outer["version"] != 1 or outer["persona_id"] != "nodes":
        _invalid("storage envelope identity")
    return _envelope_text(outer["note"])


def _envelope_text(note: Any) -> str:
    if type(note) is not dict or set(note) != {"ts", "kind", "text"}:
        _invalid("storage note schema")
    if type(note["ts"]) is not float or note["ts"] != 0.0 or note["kind"] != "other":
        _invalid("storage note purpose")
    text = note["text"]
    if type(text) is not str:
        _invalid("storage text type")
    return text


def _payload(line: str) -> dict[str, Any]:
    text = _storage_text(json.loads(line, object_pairs_hook=_unique))
    body = json.loads(text, object_pairs_hook=_unique)
    if type(body) is not dict or set(body) != _FIELDS or _canonical(body) != text:
        _invalid("payload schema or canonical encoding")
    return body


@final
class JsonlSummaryNodeStore:
    """Fail-closed cache; only contiguous per-level prefixes with child closure."""

    def __init__(self, root: Path, world_id: str, persona_id: str, summary_policy_id: str) -> None:
        self._world = _identifier(world_id)
        self._persona = _identifier(persona_id)
        self._policy = _identifier(summary_policy_id)
        self._lock = RLock()
        self._failed = False
        self._loaded = False
        self._nodes: dict[tuple[int, int], SummaryNode] = {}
        self._counts: dict[int, int] = {}
        self._source_count = 0
        self._source_hash = _source_digest((), 0)
        self._journal = JsonlExperienceStore(
            root / "summary-cache" / self._world / self._persona / self._policy, "nodes"
        )
        self.path = self._journal.path

    def _healthy(self) -> None:
        if self._failed:
            msg = "summary cache failed; close and inspect before reuse"
            raise OSError(msg)

    def _decode(self, line: str, notes: Sequence[ExperienceNote]) -> SummaryNode:
        body = _payload(line)
        self._identity(body)
        node = SummaryNode(body["level"], body["index"], body["summary"])
        count = body["source_count"]
        self._binding(body, node, notes)
        self._source_count = count
        self._source_hash = body["source_digest"]
        return node

    def _identity(self, body: dict[str, Any]) -> None:
        if (
            type(body["version"]) is not int
            or body["version"] != 1
            or body["purpose"] != "summary-node"
        ):
            _invalid("payload version or purpose")
        if (body["world"], body["persona"], body["policy"]) != (
            self._world,
            self._persona,
            self._policy,
        ):
            _invalid("world/persona/policy mismatch")

    def _binding(
        self, body: dict[str, Any], node: SummaryNode, notes: Sequence[ExperienceNote]
    ) -> None:
        count = body["source_count"]
        if type(count) is not int or not 0 <= count <= MAX_SOURCE_NOTES or count > len(notes):
            _invalid("source count or truncation")
        _coordinate(node, count)
        if type(body["source_digest"]) is not str or body["source_digest"] != _source_digest(
            notes, count
        ):
            _invalid("source binding mismatch")
        if count < self._source_count:
            _invalid("source count regressed")

    def _check_next(self, node: SummaryNode) -> None:
        if len(self._nodes) >= MAX_NODES or node.index != self._counts.get(node.level, 0):
            _invalid("entry limit, duplicate node or noncontiguous prefix")
        if node.level and any(
            (node.level - 1, 2 * node.index + child) not in self._nodes for child in (0, 1)
        ):
            _invalid("missing child closure")

    def _accept(self, node: SummaryNode) -> None:
        self._nodes[(node.level, node.index)] = node
        self._counts[node.level] = node.index + 1

    def load(self, notes: Sequence[ExperienceNote]) -> tuple[SummaryNode, ...]:
        with self._lock:
            self._healthy()
            if len(notes) > MAX_SOURCE_NOTES:
                _invalid("source coverage bound")
            self._nodes = {}
            self._counts = {}
            self._source_count = 0
            self._source_hash = _source_digest((), 0)
            try:
                # Bounded preflight on the backend's retained stream, not a path reopen.
                # This is intentionally the only private backend implementation coupling.
                stream = self._journal._file
                stream.seek(0)
                while line := stream.readline(MAX_RECORD_BYTES + 1):
                    if len(self._nodes) >= MAX_NODES:
                        _invalid("entry limit")
                    if (
                        len(line) > MAX_RECORD_BYTES
                        or len(line.encode("utf-8")) > MAX_RECORD_BYTES
                        or not line.endswith("\n")
                    ):
                        _invalid("oversized or torn record")
                    node = self._decode(line, notes)
                    self._check_next(node)
                    self._accept(node)
                self._journal.load()  # mark bounded, validated history safe for backend append
            except BaseException:
                self._failed = True
                raise
            self._loaded = True
            return tuple(self._nodes.values())

    def append(self, node: SummaryNode, notes: Sequence[ExperienceNote]) -> None:
        with self._lock:
            self._healthy()
            if not self._loaded:
                self.load(notes)
            if len(notes) > MAX_SOURCE_NOTES:
                _invalid("source coverage bound")
            _coordinate(node, len(notes))
            self._check_next(node)
            if _source_digest(notes, self._source_count) != self._source_hash:
                _invalid("source binding mismatch")
            body = {
                "version": 1,
                "purpose": "summary-node",
                "world": self._world,
                "persona": self._persona,
                "policy": self._policy,
                "level": node.level,
                "index": node.index,
                "source_count": len(notes),
                "source_digest": _source_digest(notes, len(notes)),
                "summary": node.text,
            }
            text = _canonical(body)
            row = {
                "version": 1,
                "persona_id": "nodes",
                "note": {"ts": 0.0, "kind": "other", "text": text},
            }
            if (
                len((json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
                > MAX_RECORD_BYTES
            ):
                _invalid("encoded record size")
            try:
                self._journal.append(ExperienceNote(0.0, "other", text))
            except BaseException:
                self._failed = True
                raise
            self._accept(node)  # durable acknowledgement before visible coordinates
            self._source_count = len(notes)
            self._source_hash = str(body["source_digest"])

    def close(self) -> None:
        with self._lock:
            self._journal.close()
