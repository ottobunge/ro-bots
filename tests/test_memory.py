"""ADR-004: OptChat-style episodic memory — tree, view, zoom, facade."""

import itertools

import pytest

from robots.domain.decisions import build_decision_request
from robots.society.memory import (
    ExperienceNote,
    Memory,
    MemoryLog,
    StubSummarizer,
    render_view,
    zoom,
)
from tests.conftest import make_state


def make_note(i: int, ts: float | None = None) -> ExperienceNote:
    return ExperienceNote(ts=1000.0 + i if ts is None else ts, kind="chat", text=f"note {i}")


def make_log(n: int) -> MemoryLog:
    log = MemoryLog(StubSummarizer())
    for i in range(n):
        log.append(make_note(i))
    return log


def view_ids(lines: list[str]) -> set[str]:
    return {line.split(" ", 1)[0] for line in lines}


# -- stub summarizer -----------------------------------------------------


def test_stub_summarizer_deterministic() -> None:
    a, b = StubSummarizer(), StubSummarizer()
    assert a.summarize("alpha", "beta") == a.summarize("alpha", "beta")
    assert a.summarize("alpha", "beta") == b.summarize("alpha", "beta")
    assert a.summarize("alpha", None) == "alpha"
    assert a.summarize("alpha", "beta") == "alpha ~ beta"
    long = "x" * 300
    assert len(a.summarize(long, long)) == StubSummarizer().summarize(long, long).__len__() == 120


# -- append & tree invariants --------------------------------------------


def test_append_is_cheap_and_notes_preserved() -> None:
    log = make_log(10)
    assert len(log) == 10
    assert log.notes() == tuple(make_note(i) for i in range(10))


def test_ensure_summarized_builds_all_levels() -> None:
    log = make_log(5)
    log.ensure_summarized()
    # node (0, i) exists for every note; node (1, i) for every full pair
    assert all(log.node_summary(0, i) is not None for i in range(5))
    assert log.node_summary(1, 0) is not None
    assert log.node_summary(1, 1) is not None
    assert log.node_summary(1, 2) is None  # 5 notes -> only 2 full pairs
    assert log.node_summary(2, 0) is not None  # full block of 4
    # level-0 summary is the note itself (stub, single input)
    assert log.node_summary(0, 3) == "chat: note 3"
    # merge separator present in higher-level summaries
    assert "~" in (log.node_summary(1, 0) or "")


def test_append_after_view_does_not_recompute_old_nodes() -> None:
    log = make_log(4)
    log.ensure_summarized()
    snapshot = dict(log._nodes)
    for i in range(4, 8):
        log.append(make_note(i))
    log.ensure_summarized()
    assert log.dirty_upto == 8
    for key, text in snapshot.items():
        assert log.node_summary(*key) == text  # old summaries untouched


def test_appending_is_lazy_without_ensure() -> None:
    log = MemoryLog(StubSummarizer())
    log.append(make_note(0))
    assert log.node_summary(0, 0) is None
    assert log.dirty_upto == 0


# -- view: budget + coverage ---------------------------------------------


def test_view_respects_byte_budget() -> None:
    log = make_log(64)
    lines = render_view(log, budget_chars=200)
    assert lines
    assert len("\n".join(lines)) <= 200
    assert all(line.startswith("L") for line in lines)


def test_view_default_budget_4000() -> None:
    log = make_log(300)
    lines = render_view(log)
    assert len("\n".join(lines)) <= 4000


def test_view_covers_every_note_exactly_once() -> None:
    """Coverage math: dyadic intervals of chosen nodes tile [0, n) without gaps."""
    for n in (1, 2, 3, 5, 7, 8, 13, 16, 31, 40):
        log = make_log(n)
        lines = render_view(log, budget_chars=100_000)
        covered: list[tuple[int, int]] = []
        for line in lines:
            node_id = line.split(" ", 1)[0]
            level, index = int(node_id[1 : node_id.index(":")]), int(node_id.split(":")[1])
            covered.append((index * 2**level, (index + 1) * 2**level))
        covered.sort()
        assert covered[0][0] == 0
        assert covered[-1][1] == n
        for (_, prev_end), (next_start, _) in itertools.pairwise(covered):
            assert next_start == prev_end  # exact tiling, no gap, no overlap


def test_view_recent_notes_at_level_0_older_coalesced() -> None:
    log = make_log(16)
    lines = render_view(log, budget_chars=100_000)
    ids = sorted(view_ids(lines), key=lambda s: int(s.split(":")[1]))
    assert "L0:15" in ids  # newest note verbatim
    assert sum(1 for i in ids if i.startswith("L0:")) <= 2  # only the newest note(s)
    assert any(i.startswith(("L2:", "L3:", "L4:")) for i in ids)  # old notes coalesced


def test_view_empty_log() -> None:
    assert render_view(MemoryLog(StubSummarizer())) == []


def test_view_has_addressable_node_ids() -> None:
    log = make_log(9)
    lines = render_view(log)
    assert all(line.split(" ", 1)[0].startswith("L") for line in lines)
    assert ":" in lines[0]


def test_view_timestamp_suffix() -> None:
    log = MemoryLog(StubSummarizer())
    log.append(ExperienceNote(ts=0.0, kind="combat", text="fought a Poring"))
    lines = render_view(log, now=7200.0)
    assert "(2h ago)" in lines[0]


# -- zoom -----------------------------------------------------------------


def test_zoom_expands_node_into_two_children() -> None:
    log = make_log(8)
    view = render_view(log, budget_chars=100_000)
    target = next(line for line in view if line.startswith("L2:"))
    zoomed = zoom(log, view, target.split(" ", 1)[0])
    assert len(zoomed) == len(view) + 1  # 1 line replaced by 2
    ids = view_ids(zoomed)
    assert "L1:0" in ids
    assert "L1:1" in ids
    assert target.split(" ", 1)[0] not in ids  # parent gone
    # original view untouched (pure)
    assert view == render_view(log, budget_chars=100_000)


def test_zoom_level_zero_is_noop() -> None:
    log = make_log(4)
    view = render_view(log)
    zoomed = zoom(log, view, "L0:0")
    assert zoomed == view


def test_zoom_unknown_id_is_noop() -> None:
    log = make_log(4)
    view = render_view(log)
    assert zoom(log, view, "garbage") == view
    assert zoom(log, view, "L9:42") == view


def test_zoom_returns_new_list() -> None:
    log = make_log(8)
    view = render_view(log)
    zoomed = zoom(log, view, "L2:0")
    assert zoomed is not view
    assert zoomed != view  # L2:0 present in the default view of 8 notes


def test_zoom_id_not_in_view_is_noop() -> None:
    log = make_log(8)
    view = render_view(log)  # contains L2:0, L1:2, L0:6, L0:7
    assert zoom(log, view, "L1:0") == view  # valid node but not in this view


# -- Memory facade ---------------------------------------------------------


def test_memory_facade_remember_view_zoom() -> None:
    mem = Memory(StubSummarizer())
    mem.remember("chat", "Otto said hello", ts=1.0)
    mem.remember("party", "partied with Mika\non orc dungeon", ts=2.0)  # newline collapsed
    view = mem.view(budget=10_000)
    assert len(view) == 2  # recent notes at level 0
    assert view[0].startswith("L0:0")
    assert "Otto said hello" in view[0]
    assert "\n" not in view[1]  # text was one-lined
    zoomed = mem.zoom_line(view, "L0:1")
    assert zoomed == view  # level 0 has no children


def test_memory_per_agent_no_global_state() -> None:
    a, b = Memory(StubSummarizer()), Memory(StubSummarizer())
    a.remember("loot", "found a clip", ts=1.0)
    assert b.view() == []
    assert len(a.view()) == 1


def test_memory_lines_in_decision_request() -> None:

    state = make_state()
    request = build_decision_request(state, memory_lines=["L0:0 hello", "L1:0 older stuff"])
    assert request["state"]["memory_view"] == "L0:0 hello\nL1:0 older stuff"

    plain = build_decision_request(state)
    assert "memory_view" not in plain["state"]


def test_decision_request_memory_lines_capped_at_40() -> None:

    lines = [f"L0:{i} line {i}" for i in range(60)]
    payload = build_decision_request(make_state(), memory_lines=lines)["state"]
    assert payload["memory_view"].count("\n") == 39
    assert "line 40" not in payload["memory_view"]


@pytest.mark.parametrize(("n", "budget"), [(3, 500), (10, 150), (24, 400)])
def test_view_budget_never_exceeded(n: int, budget: int) -> None:
    lines = render_view(make_log(n), budget_chars=budget)
    assert len("\n".join(lines)) <= budget
