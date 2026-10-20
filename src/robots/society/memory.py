"""Episodic memory (ADR-004): an OptChat-style append-only log with a summary tree.

Each agent owns a private ``MemoryLog`` — nothing global. Every perceived
experience is appended verbatim as a one-line :class:`ExperienceNote`; a lazy
summary tree coalesces old notes so the whole past fits a fixed byte budget:

- node ``(l, i)`` covers notes ``[i*2^l, (i+1)*2^l)``
- level 0 is a one-line summary of a single note; level ``l`` merges its two
  children ``(l-1, 2i)`` and ``(l-1, 2i+1)``
- nodes are only ever created for *fully covered* ranges, so once a node
  exists its summary is final — appends never recompute old nodes.

``render_view`` walks the tree top-down and returns the fewest lines that
cover the log under a byte budget: recent notes at full resolution (level 0),
older ones coalesced many-per-line. ``zoom`` resolves one view line back into
its two children, down to the original note.
"""

from collections.abc import Iterator, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from threading import RLock
from typing import TYPE_CHECKING, Literal, Protocol, final

if TYPE_CHECKING:
    from robots.ports import ChatGenerator

NoteKind = Literal[
    "chat", "combat", "party", "loot", "quest", "session", "reputation", "other", "npc_dialogue"
]

VIEW_BUDGET_CHARS = 4000
QWEN_SUMMARY_MAX_CHARS = 200
STUB_SUMMARY_MAX_CHARS = 120


@dataclass(frozen=True, slots=True)
class ExperienceNote:
    """One perceived experience, verbatim, one line, never edited."""

    ts: float
    kind: NoteKind
    text: str


class ExperienceStore(Protocol):
    """Private durable journal port; one owner controls its lifetime."""

    def load(self) -> tuple[ExperienceNote, ...]: ...

    def append(self, note: ExperienceNote) -> None: ...

    def close(self) -> None: ...


@dataclass(frozen=True, slots=True)
class SummaryNode:
    """One immutable, fully covered dyadic summary."""

    level: int
    index: int
    text: str


class SummaryNodeStore(Protocol):
    """Private cache port; restore must validate source bindings and tree closure."""

    def load(self, notes: Sequence[ExperienceNote]) -> tuple[SummaryNode, ...]: ...

    def append(self, node: SummaryNode, notes: Sequence[ExperienceNote]) -> None: ...

    def close(self) -> None: ...


class Summarizer(Protocol):
    """Merges note text into one shorter line (port: local Qwen, or a stub)."""

    def summarize(self, text_a: str, text_b: str | None) -> str:
        """One-line summary of ``text_a`` merged with ``text_b`` (if given)."""
        ...


@final
class StubSummarizer:
    """Deterministic summarizer for tests and dry runs: join, then truncate."""

    def __init__(self, max_chars: int = STUB_SUMMARY_MAX_CHARS) -> None:
        self._max_chars = max_chars

    def summarize(self, text_a: str, text_b: str | None) -> str:
        merged = text_a if text_b is None else f"{text_a} ~ {text_b}"
        return merged[: self._max_chars]


@final
class QwenSummarizer:
    """Summarizes through the ChatGenerator port (local Qwen first, remote later)."""

    def __init__(self, chat: ChatGenerator, max_chars: int = QWEN_SUMMARY_MAX_CHARS) -> None:
        self._chat = chat
        self._max_chars = max_chars

    def summarize(self, text_a: str, text_b: str | None) -> str:
        prompt = f"Summarize these experience notes as ONE short line.\nA: {text_a}\n"
        if text_b is not None:
            prompt += f"B: {text_b}\n"
        raw = self._chat.generate_chat(prompt).strip()
        lines = raw.splitlines()
        line = lines[0].strip() if lines else ""
        return line[: self._max_chars]


def _note_text(note: ExperienceNote) -> str:
    return f"{note.kind}: {note.text}"


def _cleanup_note(origin: BaseException, note: str) -> None:
    with suppress(BaseException):
        origin.add_note(note)


@final
class MemoryLog:
    """Append-only notes plus a lazily built, immutable summary tree."""

    def __init__(
        self,
        summarizer: Summarizer,
        *,
        store: ExperienceStore | None = None,
        summary_store: SummaryNodeStore | None = None,
    ) -> None:
        self._summarizer = summarizer
        self._lock = RLock()
        self._store = store
        self._summary_store = summary_store
        self._summary_failed = False
        self._notes: list[ExperienceNote] = []
        self._nodes: dict[tuple[int, int], str] = {}
        self._built: list[int] = [0]  # built[l] = count of nodes built at level l
        self._dirty_upto = 0
        try:
            if store is not None:
                self._notes = list(store.load())
            if summary_store is not None:
                for node in summary_store.load(self._notes):
                    while len(self._built) <= node.level:
                        self._built.append(0)
                    self._nodes[(node.level, node.index)] = node.text
                    self._built[node.level] += 1
        except BaseException as origin:
            try:
                self.close()
            except BaseException:
                _cleanup_note(
                    origin, "memory restore cleanup failed; storage release may be incomplete"
                )
            raise

    def __len__(self) -> int:
        return len(self._notes)

    @contextmanager
    def locked(self) -> Iterator[None]:
        """Serialize a complete append, summary build, or view snapshot."""
        with self._lock:
            yield

    def append(self, note: ExperienceNote) -> None:
        """Add one note. Cheap: nothing is summarized until ``ensure_summarized``."""
        with self._lock:
            if self._store is not None:
                self._store.append(note)  # durable acknowledgement before visible memory
            self._notes.append(note)

    def close(self) -> None:
        """Release both stores, preserving the first failure and its traceback."""
        with self._lock:
            self._close_stores()

    def _close_stores(self) -> None:
        origin: BaseException | None = None
        for store in (self._store, self._summary_store):
            if store is None:
                continue
            try:
                store.close()
            except BaseException as failure:
                if origin is None:
                    origin = failure
                    _cleanup_note(
                        origin, "memory storage cleanup failed; release may be incomplete"
                    )
                else:
                    _cleanup_note(
                        origin,
                        "additional memory storage cleanup failed; release may be incomplete",
                    )
        if origin is not None:
            raise origin.with_traceback(origin.__traceback__)

    def notes(self) -> tuple[ExperienceNote, ...]:
        return tuple(self._notes)

    def capture_raw_notes(
        self, max_notes: int = 64, max_utf8_bytes: int = 8192
    ) -> tuple[ExperienceNote, ...] | None:
        """Nonblocking complete bounded prefix; None means UNKNOWN, never truncated.

        Byte accounting covers raw note text only; job capture separately bounds
        metadata and all public/observed payloads. No summaries or store effects.
        """
        if not self._lock.acquire(blocking=False):
            return None
        try:
            if len(self._notes) > max_notes:
                return None
            remaining = max_utf8_bytes
            for note in self._notes:
                if len(note.text) > remaining:
                    return None
                try:
                    remaining -= len(note.text.encode("utf-8"))
                except UnicodeEncodeError:
                    return None
                if remaining < 0:
                    return None
            return tuple(self._notes)
        finally:
            self._lock.release()

    @property
    def dirty_upto(self) -> int:
        """Notes below this index are fully summarized at every level."""
        return self._dirty_upto

    def node_summary(self, level: int, index: int) -> str | None:
        """Cached summary of node (level, index); None if not built/not covered."""
        return self._nodes.get((level, index))

    def node_tail_ts(self, level: int, index: int) -> float:
        """Timestamp of the newest note covered by node (level, index)."""
        start = index * 2**level
        note = self._notes[min(start + 2**level, len(self._notes)) - 1]
        return float(note.ts)

    def ensure_summarized(self) -> None:
        """Fill every missing node bottom-up. Existing nodes are never recomputed."""
        with self._lock:
            self._fill_summaries()

    def _fill_summaries(self) -> None:
        if self._summary_failed:
            msg = "summary storage failed; close and inspect before reuse"
            raise OSError(msg)
        n = len(self._notes)
        while self._built[0] < n:
            i = self._built[0]
            text = self._summarizer.summarize(_note_text(self._notes[i]), None)
            self._publish_summary(0, i, text)
            self._built[0] += 1
        level = 1
        while n >> level:
            while len(self._built) <= level:
                self._built.append(0)
            target = n >> level  # fully covered nodes at this level
            while self._built[level] < target:
                i = self._built[level]
                child_a = self._nodes[(level - 1, 2 * i)]
                child_b = self._nodes[(level - 1, 2 * i + 1)]
                text = self._summarizer.summarize(child_a, child_b)
                self._publish_summary(level, i, text)
                self._built[level] += 1
            level += 1
        self._dirty_upto = n

    def _publish_summary(self, level: int, index: int, text: str) -> None:
        if self._summary_store is not None:
            try:
                self._summary_store.append(SummaryNode(level, index, text), self._notes)
            except BaseException:
                self._summary_failed = True
                raise
        self._nodes[(level, index)] = text


def _minimal_cover(n: int) -> list[tuple[int, int]]:
    """Fewest dyadic nodes covering [0, n), newest note always at level 0.

    Greedy from the oldest note: take the largest aligned block that fits,
    then repeat; the final note is rendered verbatim (level 0) so the view
    always shows the present at full resolution.
    """
    cover: list[tuple[int, int]] = []
    start, end = 0, n - 1  # cover [0, n-1); the last note is appended alone
    while start < end:
        level = (end - start).bit_length() - 1  # largest 2^l <= remaining span
        while level > 0 and start % (2**level) != 0:
            level -= 1
        cover.append((level, start >> level))
        start += 2**level
    cover.append((0, n - 1))
    return cover


def _age_suffix(age_s: float) -> str:
    if age_s < 90.0:
        return " (just now)"
    if age_s < 3600.0:
        return f" ({age_s / 60.0:.0f}m ago)"
    if age_s < 86400.0:
        return f" ({age_s / 3600.0:.0f}h ago)"
    return f" ({age_s / 86400.0:.0f}d ago)"


def _view_line(log: MemoryLog, level: int, index: int, now: float | None) -> str:
    summary = log.node_summary(level, index)
    if summary is None:
        msg = "node summary missing; call ensure_summarized() before rendering"
        raise ValueError(msg)
    suffix = ""
    if now is not None:
        suffix = _age_suffix(max(0.0, now - log.node_tail_ts(level, index)))
    return f"L{level}:{index} {summary}{suffix}"


def render_view(
    log: MemoryLog, budget_chars: int = VIEW_BUDGET_CHARS, now: float | None = None
) -> list[str]:
    """OptChat-style view: whole log, fewest lines, under the byte budget.

    Recent notes appear at level 0, older ones coalesced at higher levels.
    Under budget pressure the oldest lines are dropped first (and a too-long
    line is truncated) — the agent then simply remembers less of its distant
    past, never less of its present.
    """
    with log.locked():
        return _render_view(log, budget_chars, now)


def _render_view(log: MemoryLog, budget_chars: int, now: float | None) -> list[str]:
    log.ensure_summarized()
    n = len(log)
    if n == 0:
        return []
    lines = [_view_line(log, level, index, now) for level, index in _minimal_cover(n)]
    while lines and _len_join(lines) > budget_chars:
        lines.pop(0)  # sacrifice the oldest, coarsest line first
    if lines and len(lines[0]) > budget_chars:
        lines[0] = lines[0][:budget_chars]
    return lines


def _len_join(lines: list[str]) -> int:
    return len("\n".join(lines))


def fit_budget(lines: list[str], budget_chars: int) -> list[str]:
    """Fewest oldest lines dropped so ``'\\n'.join(lines)`` fits the budget.

    Same discipline as ``render_view``: the oldest lines go first, the newest
    is truncated only if it alone exceeds the budget. Pure; never crashes.
    """
    out = list(lines)
    if budget_chars <= 0:
        return []
    while out and _len_join(out) > budget_chars:
        out.pop(0)
    if out and len(out[0]) > budget_chars:
        out[0] = out[0][:budget_chars]
    return out


def zoom(log: MemoryLog, view: list[str], node_id: str) -> list[str]:
    """Resolve one view line into its two children; pure (returns a new list).

    Unknown ids and level-0 lines (which have no children) come back unchanged.
    """
    with log.locked():
        return _zoom(log, view, node_id)


def _zoom(log: MemoryLog, view: list[str], node_id: str) -> list[str]:
    log.ensure_summarized()
    level_part, _, index_part = node_id.partition(":")
    if not level_part.startswith("L") or not index_part.isdigit():
        return list(view)
    try:
        level, index = int(level_part[1:]), int(index_part)
    except ValueError:
        return list(view)
    if level <= 0:
        return list(view)
    child_a = log.node_summary(level - 1, 2 * index)
    child_b = log.node_summary(level - 1, 2 * index + 1)
    if child_a is None or child_b is None:
        return list(view)
    expanded = [f"L{level - 1}:{2 * index} {child_a}", f"L{level - 1}:{2 * index + 1} {child_b}"]
    return _spliced(view, node_id, expanded)


def _spliced(view: list[str], node_id: str, expanded: list[str]) -> list[str]:
    """Replace the (single) line for node_id with its expanded children."""
    marker = f"{node_id} "
    out: list[str] = []
    inserted = False
    for line in view:
        if line.startswith(marker) and not inserted:
            out.extend(expanded)
            inserted = True
        elif not line.startswith(marker):
            out.append(line)
    return out


@final
class Memory:
    """One agent's private memory facade — nothing global, one per agent."""

    def __init__(
        self,
        summarizer: Summarizer,
        *,
        store: ExperienceStore | None = None,
        summary_store: SummaryNodeStore | None = None,
    ) -> None:
        self._log = MemoryLog(summarizer, store=store, summary_store=summary_store)

    def close(self) -> None:
        """Close owned durable storage after the agent stops writing."""
        self._log.close()

    @property
    def log(self) -> MemoryLog:
        return self._log

    def remember(self, kind: NoteKind, text: str, ts: float = 0.0) -> ExperienceNote:
        """Append one experience note (text collapsed to a single line)."""
        note = ExperienceNote(ts=ts, kind=kind, text=" ".join(text.split()))
        self._log.append(note)
        return note

    def view(self, budget: int = VIEW_BUDGET_CHARS, now: float | None = None) -> list[str]:
        return render_view(self._log, budget, now)

    def zoom_line(self, view: list[str], node_id: str) -> list[str]:
        return zoom(self._log, view, node_id)
