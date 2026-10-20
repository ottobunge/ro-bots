"""Private summary cache: deterministic injected summarizers, never model evidence."""

import json
import subprocess
import sys
import threading
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from robots.adapters.memory_journal import JsonlExperienceStore
from robots.adapters.memory_summary_cache import JsonlSummaryNodeStore
from robots.society.memory import ExperienceNote, Memory, StubSummarizer, SummaryNode


class CountingSummarizer:
    def __init__(self) -> None:
        self.calls = 0

    def summarize(self, text_a: str, text_b: str | None) -> str:
        self.calls += 1
        return StubSummarizer().summarize(text_a, text_b)


def test_real_restart_reuses_old_nodes(tmp_path) -> None:
    first = CountingSummarizer()
    memory = Memory(
        first,
        store=JsonlExperienceStore(tmp_path / "raw", "p"),
        summary_store=JsonlSummaryNodeStore(tmp_path, "world", "p", "stub-v1"),
    )
    for index in range(4):
        memory.remember("party", f"synthetic note {index}", ts=index + 0.5)
    expected = memory.view(now=8.0)
    expected_zoom = memory.zoom_line(expected, "L1:0")
    notes = memory.log.notes()
    assert first.calls == 7
    memory.close()
    second = CountingSummarizer()
    restored = Memory(
        second,
        store=JsonlExperienceStore(tmp_path / "raw", "p"),
        summary_store=JsonlSummaryNodeStore(tmp_path, "world", "p", "stub-v1"),
    )
    try:
        assert restored.log.notes() == notes
        assert restored.view(now=8.0) == expected
        assert restored.zoom_line(expected, "L1:0") == expected_zoom
        assert second.calls == 0
    finally:
        restored.close()


class CacheDouble:
    def __init__(self) -> None:
        self.nodes: list[SummaryNode] = []
        self.closed = False

    def load(self, notes):
        return tuple(self.nodes)

    def append(self, node, notes):
        self.nodes.append(node)

    def close(self):
        self.closed = True


def test_optional_cache_reuses_completed_nodes() -> None:
    cache = CacheDouble()
    memory = Memory(StubSummarizer(), summary_store=cache)
    note = memory.remember("party", "synthetic healer", ts=2.5)
    expected = memory.view()
    assert len(cache.nodes) == 1
    memory.close()
    assert cache.closed

    # The same raw note must be supplied when restoring a cache.
    class Raw:
        def load(self):
            return (note,)

        def close(self):
            pass

        def append(self, note):
            pass

    class Exploding:
        def summarize(self, text_a, text_b):
            msg = "cached node recomputed"
            raise AssertionError(msg)

    restored = Memory(Exploding(), store=Raw(), summary_store=cache)
    assert restored.view() == expected
    restored.close()


def test_integer_timestamp_matches_restored_raw_semantics(tmp_path) -> None:
    memory = Memory(
        StubSummarizer(),
        store=JsonlExperienceStore(tmp_path / "raw", "p"),
        summary_store=JsonlSummaryNodeStore(tmp_path, "w", "p", "s"),
    )
    memory.remember("chat", "synthetic", ts=1)
    expected = memory.view()
    memory.close()
    restored = Memory(
        StubSummarizer(),
        store=JsonlExperienceStore(tmp_path / "raw", "p"),
        summary_store=JsonlSummaryNodeStore(tmp_path, "w", "p", "s"),
    )
    try:
        assert restored.view() == expected
    finally:
        restored.close()


def test_public_cache_append_rejects_mutated_prior_source(tmp_path) -> None:
    cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
    original = [ExperienceNote(1.0, "chat", "synthetic first")]
    try:
        cache.append(SummaryNode(0, 0, "first"), original)
        before = cache.path.read_bytes()
        changed = [ExperienceNote(1.0, "chat", "changed"), ExperienceNote(2.0, "loot", "next")]
        with pytest.raises(ValueError, match="binding"):
            cache.append(SummaryNode(0, 1, "next"), changed)
        assert cache.path.read_bytes() == before
    finally:
        cache.close()


PROCESS_READER = """
import json, sys
from pathlib import Path
from robots.adapters.memory_journal import JsonlExperienceStore
from robots.adapters.memory_summary_cache import JsonlSummaryNodeStore
from robots.society.memory import Memory, StubSummarizer
class Counting:
    calls = 0
    def summarize(self, text_a, text_b):
        self.calls += 1
        if sys.argv[2] == 'old':
            raise AssertionError('recomputed old node')
        return StubSummarizer().summarize(text_a, text_b)
s = Counting()
root = Path(sys.argv[1])
m = Memory(s, store=JsonlExperienceStore(root / 'raw', 'p'),
           summary_store=JsonlSummaryNodeStore(root, 'w', 'p', 's'))
old = m.view(now=10.0)
zoomed = m.zoom_line(old, 'L1:0')
if sys.argv[2] == 'append':
    m.remember('loot', 'synthetic new', ts=8.0)
    m.view()
print(json.dumps({'view':old,'zoom':zoomed,'calls':s.calls,
                  'notes':[[n.ts,n.kind,n.text] for n in m.log.notes()]}))
m.close()
"""


def test_fresh_process_old_nodes_zero_calls_append_only_missing(tmp_path) -> None:
    m = Memory(
        CountingSummarizer(),
        store=JsonlExperienceStore(tmp_path / "raw", "p"),
        summary_store=JsonlSummaryNodeStore(tmp_path, "w", "p", "s"),
    )
    for i in range(4):
        m.remember("party", f"synthetic {i}", ts=i + 0.5)
    expected = m.view(now=10.0)
    zoomed = m.zoom_line(expected, "L1:0")
    m.close()
    for mode, calls in [("old", 0), ("append", 1)]:
        result = subprocess.run(
            [sys.executable, "-c", PROCESS_READER, str(tmp_path), mode],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        output = json.loads(result.stdout)
        assert output["view"] == expected
        assert output["zoom"] == zoomed
        assert output["calls"] == calls
        assert output["notes"][0] == [0.5, "party", "synthetic 0"]


def seeded_cache(tmp_path: Path) -> tuple[list[ExperienceNote], Path]:
    notes = [
        ExperienceNote(1.0, "chat", "synthetic one"),
        ExperienceNote(2.0, "party", "synthetic two"),
    ]
    cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
    for i in range(2):
        cache.append(SummaryNode(0, i, f"summary {i}"), notes)
    cache.append(SummaryNode(1, 0, "merged"), notes)
    path = cache.path
    cache.close()
    return notes, path


@pytest.mark.parametrize("change", ["text", "timestamp", "kind", "reorder", "truncate"])
def test_source_mutation_rejected_without_rewrite(tmp_path, change) -> None:
    notes, path = seeded_cache(tmp_path)
    before = path.read_bytes()
    if change == "reorder":
        notes.reverse()
    elif change == "truncate":
        notes.pop()
    else:
        note = notes[0]
        notes[0] = ExperienceNote(
            9.0 if change == "timestamp" else note.ts,
            "loot" if change == "kind" else note.kind,
            "changed" if change == "text" else note.text,
        )
    cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
    try:
        with pytest.raises(ValueError, match="invalid summary cache"):
            cache.load(notes)
        with pytest.raises(OSError, match="failed"):
            cache.load(notes)
        assert path.read_bytes() == before
    finally:
        cache.close()


@pytest.mark.parametrize("scope", ["world", "persona", "policy"])
def test_real_scope_isolation_and_copied_cache_rejection(tmp_path, scope) -> None:
    notes, path = seeded_cache(tmp_path)
    ids = ["w", "p", "s"]
    ids[["world", "persona", "policy"].index(scope)] = "other"
    cache = JsonlSummaryNodeStore(tmp_path, *ids)
    assert cache.load(notes) == ()
    other = cache.path
    cache.close()
    other.write_bytes(path.read_bytes())
    copied = JsonlSummaryNodeStore(tmp_path, *ids)
    try:
        with pytest.raises(ValueError, match="mismatch"):
            copied.load(notes)
    finally:
        copied.close()


@pytest.mark.parametrize(
    "defect",
    [
        "torn",
        "oversized",
        "duplicate_node",
        "child",
        "gap",
        "unknown",
        "duplicate_key",
        "outer_key",
        "outer_version",
        "purpose",
        "bool_level",
        "large_level",
        "negative_index",
        "large_index",
        "large_count",
        "bool_count",
        "multiline",
        "large_summary",
        "digest",
    ],
)
def test_malformed_private_cache_fails_closed(tmp_path, defect) -> None:
    notes, path = seeded_cache(tmp_path)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    body = json.loads(rows[0]["note"]["text"])
    if defect == "torn":
        raw = path.read_bytes()[:-1]
    elif defect == "oversized":
        raw = b"x" * 16385 + b"\n"
    else:
        if defect == "duplicate_node":
            rows.append(rows[0])
        elif defect == "child":
            rows = [rows[-1]]
        elif defect == "gap":
            rows = [rows[1]]
        elif defect == "outer_key":
            rows[0]["unknown"] = 1
        elif defect == "outer_version":
            rows[0]["version"] = True
        else:
            changes = {
                "unknown": ("unknown", 1),
                "purpose": ("purpose", "experience"),
                "bool_level": ("level", True),
                "large_level": ("level", 10**100),
                "negative_index": ("index", -1),
                "large_index": ("index", 1000000),
                "large_count": ("source_count", 1000001),
                "bool_count": ("source_count", True),
                "multiline": ("summary", "bad\nline"),
                "large_summary": ("summary", "x" * 4097),
                "digest": ("source_digest", "wrong"),
            }
            if defect == "duplicate_key":
                rows[0]["note"]["text"] = '{"version":1,' + rows[0]["note"]["text"][1:]
            else:
                key, value = changes[defect]
                body[key] = value
                rows[0]["note"]["text"] = json.dumps(body, sort_keys=True, separators=(",", ":"))
        raw = ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
    path.write_bytes(raw)
    assert path.stat().st_mode & 0o777 == 0o600
    cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
    try:
        with pytest.raises(ValueError, match="invalid summary cache"):
            cache.load(notes)
        assert path.read_bytes() == raw
    finally:
        cache.close()


@pytest.mark.parametrize("fault", ["fsync", "short_write"])
def test_uncertain_cache_write_no_local_progress_and_poison(tmp_path, monkeypatch, fault) -> None:
    cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
    summarizer = CountingSummarizer()
    m = Memory(summarizer, summary_store=cache)
    m.remember("chat", "synthetic")
    reached = []
    origin = OSError("injected cache failure")
    if fault == "fsync":

        def fail(fd):
            reached.append(fd)
            raise origin

        monkeypatch.setattr("robots.adapters.memory_journal.os.fsync", fail)
    else:
        write = cache._journal._file.write

        def short(text):
            reached.append(text)
            write(text[:3])
            return 3

        monkeypatch.setattr(cache._journal._file, "write", short)
    try:
        with pytest.raises(OSError, match=r"injected|incomplete") as caught:
            m.view()
        if fault == "fsync":
            assert caught.value is origin
        assert reached
        assert m.log.node_summary(0, 0) is None
        assert m.log._built == [0]
        assert m.log.dirty_upto == 0
        with pytest.raises(OSError, match="failed"):
            m.view()
        assert summarizer.calls == 1
    finally:
        m.close()


def test_partial_tree_restores_completed_prefix_after_summarizer_failure(tmp_path) -> None:
    origin = RuntimeError("injected summarizer failure")

    class Partial(CountingSummarizer):
        def summarize(self, text_a, text_b):
            if self.calls == 2:
                raise origin
            return super().summarize(text_a, text_b)

    m = Memory(
        Partial(),
        store=JsonlExperienceStore(tmp_path / "raw", "p"),
        summary_store=JsonlSummaryNodeStore(tmp_path, "w", "p", "s"),
    )
    for i in range(4):
        m.remember("chat", f"synthetic {i}")
    with pytest.raises(RuntimeError) as caught:
        m.view()
    assert caught.value is origin
    assert m.log._built == [2]
    assert m.log.dirty_upto == 0
    m.close()
    s = CountingSummarizer()
    restored = Memory(
        s,
        store=JsonlExperienceStore(tmp_path / "raw", "p"),
        summary_store=JsonlSummaryNodeStore(tmp_path, "w", "p", "s"),
    )
    try:
        restored.view()
        assert s.calls == 5
    finally:
        restored.close()


@pytest.mark.parametrize("restore", [False, True])
def test_both_owned_stores_release_preserving_first_failure(tmp_path, monkeypatch, restore) -> None:
    raw = JsonlExperienceStore(tmp_path / "raw", "p")
    cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
    first = RuntimeError("first")
    second = RuntimeError("second")
    raw_close, cache_close = raw.close, cache.close
    calls = []

    def close_raw():
        calls.append("raw")
        raw_close()
        raise first

    def close_cache():
        calls.append("cache")
        cache_close()
        raise second

    monkeypatch.setattr(raw, "close", close_raw)
    monkeypatch.setattr(cache, "close", close_cache)
    if restore:

        def fail(notes):
            raise first

        monkeypatch.setattr(cache, "load", fail)
        with pytest.raises(RuntimeError) as caught:
            Memory(StubSummarizer(), store=raw, summary_store=cache)
    else:
        m = Memory(StubSummarizer(), store=raw, summary_store=cache)
        with pytest.raises(RuntimeError) as caught:
            m.close()
    assert caught.value is first
    assert calls == ["raw", "cache"]
    assert first.__notes__
    reopened_raw = JsonlExperienceStore(tmp_path / "raw", "p")
    reopened_cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
    reopened_raw.close()
    reopened_cache.close()


@pytest.mark.parametrize("operation", ["append", "view", "zoom", "close"])
def test_summary_build_serializes_other_facade_operations(tmp_path, operation) -> None:
    entered, release, attempting, finished = (threading.Event() for _ in range(4))
    errors = []

    class Blocking(CountingSummarizer):
        def summarize(self, text_a, text_b):
            entered.set()
            assert release.wait(3)
            return super().summarize(text_a, text_b)

    m = Memory(Blocking(), summary_store=JsonlSummaryNodeStore(tmp_path, "w", "p", "s"))
    m.remember("chat", "synthetic")

    def build():
        try:
            m.view()
        except BaseException as exc:
            errors.append(exc)

    def other():
        attempting.set()
        try:
            if operation == "append":
                m.remember("party", "new")
            elif operation == "view":
                m.view()
            elif operation == "zoom":
                m.zoom_line([], "L1:0")
            else:
                m.close()
        except BaseException as exc:
            errors.append(exc)
        finally:
            finished.set()

    first, second = threading.Thread(target=build), threading.Thread(target=other)
    first.start()
    try:
        assert entered.wait(1)
        second.start()
        assert attempting.wait(1)
        assert not finished.wait(0.1)
    finally:
        release.set()
        first.join(3)
        if second.ident is not None:
            second.join(3)
        m.close()
    assert not first.is_alive()
    assert not second.is_alive()
    assert not errors


@pytest.mark.parametrize("value", [True, 1, "", "../x", "a/b", "a\n", "x" * 129])
def test_identity_validated_before_filesystem(tmp_path, value) -> None:
    with pytest.raises(ValueError, match="invalid summary cache"):
        JsonlSummaryNodeStore(tmp_path / "untouched", value, "p", "s")
    assert not (tmp_path / "untouched").exists()


def test_backend_lifetime_lock_and_private_modes(tmp_path) -> None:
    cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
    try:
        with pytest.raises(BlockingIOError):
            JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
        assert cache.path.stat().st_mode & 0o777 == 0o600
        assert cache.path.parent.stat().st_mode & 0o777 == 0o700
    finally:
        cache.close()


def test_encoded_record_limit_rejected_before_backend_write(tmp_path) -> None:
    cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
    notes = [ExperienceNote(1.0, "chat", "synthetic")]
    try:
        cache.load(notes)
        with pytest.raises(ValueError, match="record"):
            cache.append(SummaryNode(0, 0, '"' * 4096), notes)
        assert cache.path.read_bytes() == b""
    finally:
        cache.close()


@pytest.mark.parametrize("which", ["raw", "cache"])
def test_pre_release_close_failure_reports_residual_and_releases_other(
    tmp_path, monkeypatch, which
) -> None:
    raw = JsonlExperienceStore(tmp_path / "raw", "p")
    cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
    m = Memory(StubSummarizer(), store=raw, summary_store=cache)
    failing = raw if which == "raw" else cache
    real_close = failing.close
    origin = RuntimeError("injected before release")

    def fail():
        raise origin

    monkeypatch.setattr(failing, "close", fail)
    with pytest.raises(RuntimeError, match="injected") as caught:
        m.close()
    assert caught.value is origin
    assert any("incomplete" in note for note in getattr(origin, "__notes__", []))

    # Residual ownership is real, not misreported as closed.
    def reopen_failing() -> JsonlExperienceStore | JsonlSummaryNodeStore:
        if which == "raw":
            return JsonlExperienceStore(tmp_path / "raw", "p")
        return JsonlSummaryNodeStore(tmp_path, "w", "p", "s")

    with pytest.raises(BlockingIOError):
        reopen_failing()
    real_close()  # explicit fixture recovery, not a production blind retry
    reopened_raw = JsonlExperienceStore(tmp_path / "raw", "p")
    reopened_cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
    reopened_raw.close()
    reopened_cache.close()


def test_cleanup_annotation_failure_never_masks_origin() -> None:
    class OriginError(RuntimeError):
        def add_note(self, note):
            msg = "injected annotation failure"
            raise AssertionError(msg)

    origin = OriginError("original close")
    cache = CacheDouble()

    class Raw:
        def load(self):
            return ()

        def append(self, note):
            pass

        def close(self):
            raise origin

    m = Memory(StubSummarizer(), store=Raw(), summary_store=cache)
    with pytest.raises(RuntimeError, match="original close") as caught:
        m.close()
    assert caught.value is origin
    assert cache.closed


@pytest.mark.parametrize(
    ("level", "index"), [(True, 0), (21, 0), (10**100, 0), (0, True), (0, 1000000), (0, -1)]
)
def test_coordinate_bounds_before_source_iteration(tmp_path, level, index) -> None:
    cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")

    class Notes:
        def __len__(self):
            return 100

        def __getitem__(self, index):
            msg = "source iterated before coordinate validation"
            raise AssertionError(msg)

    try:
        with pytest.raises(ValueError, match="bound"):
            cache.append(
                SummaryNode(level, index, "synthetic"), cast("Sequence[ExperienceNote]", Notes())
            )
        assert cache.path.read_bytes() == b""
    finally:
        cache.close()


@pytest.mark.parametrize("operation", ["load", "append"])
def test_source_coverage_bound_before_iteration(tmp_path, operation) -> None:
    cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")

    class Notes:
        def __len__(self):
            return 1000001

        def __getitem__(self, index):
            msg = "oversized source iterated"
            raise AssertionError(msg)

    try:
        notes = cast("Sequence[ExperienceNote]", Notes())

        def invoke() -> None:
            if operation == "load":
                cache.load(notes)
            else:
                cache.append(SummaryNode(0, 0, "synthetic"), notes)

        with pytest.raises(ValueError, match="coverage bound"):
            invoke()
        assert cache.path.read_bytes() == b""
    finally:
        cache.close()


@pytest.mark.parametrize("text", ["x" * 4097, "😀" * 1025, "a\n", "a\x00", "a\u2028", "\ud800"])
def test_summary_bounds_and_utf8_rejected_before_storage(tmp_path, text) -> None:
    cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
    try:
        with pytest.raises(ValueError, match=r"summary|surrogates"):
            cache.append(SummaryNode(0, 0, text), [ExperienceNote(1.0, "chat", "synthetic")])
        assert cache.path.read_bytes() == b""
    finally:
        cache.close()


def test_entry_bound_before_decoding_next_record(tmp_path, monkeypatch) -> None:
    notes, path = seeded_cache(tmp_path)
    before = path.read_bytes()
    monkeypatch.setattr("robots.adapters.memory_summary_cache.MAX_NODES", 1)
    cache = JsonlSummaryNodeStore(tmp_path, "w", "p", "s")
    try:
        with pytest.raises(ValueError, match="entry limit"):
            cache.load(notes)
        assert cache.path.read_bytes() == before
    finally:
        cache.close()
