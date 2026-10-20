"""Offline contracts for the opt-in view core; no existing memory integration."""

import json
from typing import Any

import pytest

from robots.society import optchat_view as core


def test_append_is_summary_only_and_read_stable():
    texts = {core.NodeCoordinate(0, 0): "leaf\nsummary"}
    view = core.IncrementalView(texts.get)
    assert view.read() == b""
    view.append()
    before = view.state
    assert view.read() == b"0+1|leaf summary\n"
    assert view.read() == view.read()
    assert view.state == before
    texts[core.NodeCoordinate(0, 1)] = "next"
    old = view.read()
    view.append()
    assert view.read().startswith(old)
    assert view.state.source_count == 2
    assert view.state.coordinates == (core.NodeCoordinate(0, 0), core.NodeCoordinate(0, 1))


def test_high_water_crossing_compacts_to_low_not_every_append():
    policy = core.ViewPolicy(low_bytes=22, high_bytes=40)
    view = core.IncrementalView(lambda _node: "x", policy)
    for _ in range(6):
        old = view.read()
        view.append()
        assert view.read().startswith(old)
    assert len(view.read()) == 36
    view.append()
    assert len(view.read()) <= 22
    assert view.snapshot()["pending_batch"] is False
    assert sum(1 << node.level for node in view.state.coordinates) == 7


def test_unbuilt_parent_stalls_and_advance_resumes_without_read_mutation():
    texts = {core.NodeCoordinate(0, i): "😀" for i in range(4)}
    view = core.IncrementalView(texts.get, core.ViewPolicy(low_bytes=10, high_bytes=20))
    for _ in range(4):
        view.append()
    assert view.state.pending_batch
    before = view.state
    assert len(view.read()) == 36
    assert view.state == before
    with pytest.raises(core.OverBudgetError):
        view.read_ready()
    texts.update(
        {
            core.NodeCoordinate(1, 0): "a",
            core.NodeCoordinate(1, 1): "b",
            core.NodeCoordinate(2, 0): "root",
        }
    )
    view.advance()
    assert view.state.coordinates == (core.NodeCoordinate(2, 0),)
    assert view.snapshot()["pending_batch"] is False
    assert view.read_ready() == b"0+4|root\n"


def test_impossible_low_keeps_complete_cover_and_pending_flag():
    view = core.IncrementalView(lambda _node: "x" * 10, core.ViewPolicy(low_bytes=1, high_bytes=20))
    for _ in range(3):
        view.append()
    assert view.state.coordinates == (core.NodeCoordinate(1, 0), core.NodeCoordinate(0, 2))
    assert view.state.pending_batch
    assert view.state.source_count == 3


def snapshot_for(count: int, coordinates: list[list[int]], pending: bool = True) -> dict[str, Any]:
    return {
        "version": 1,
        "policy": {"namespace": "test", "low_bytes": 20, "high_bytes": 100},
        "source_count": count,
        "coordinates": coordinates,
        "pending_batch": pending,
    }


def test_last_message_rank_at_ten_merges_newest_pair_first():
    state = snapshot_for(10, [[2, 0], [2, 1], [0, 8], [0, 9]])
    view = core.IncrementalView.restore(state, lambda _node: "x")
    view.advance()
    assert view.state.coordinates == (
        core.NodeCoordinate(2, 0),
        core.NodeCoordinate(2, 1),
        core.NodeCoordinate(1, 4),
    )


def test_oldest_tie_wins():
    state = snapshot_for(7, [[1, 0], [1, 1], [0, 4], [0, 5], [0, 6]])
    state["policy"]["low_bytes"] = 25
    view = core.IncrementalView.restore(state, lambda _node: "x")
    view.advance()
    assert view.state.coordinates[0] == core.NodeCoordinate(2, 0)


def test_serializable_roundtrip_is_exact_and_does_not_refit():
    texts = {core.NodeCoordinate(0, i): "😀\nline" for i in range(4)}
    view = core.IncrementalView(texts.get, core.ViewPolicy("custom", 10, 20))
    for _ in range(4):
        view.append()
    snapshot = json.loads(json.dumps(view.snapshot()))
    restored = core.IncrementalView.restore(snapshot, texts.get, expected_policy=view.policy)
    assert restored.state == view.state
    assert restored.policy == view.policy
    assert restored.read() == view.read()
    assert restored.snapshot() == view.snapshot()
    assert restored.state.pending_batch


@pytest.mark.parametrize(
    "mutation",
    ["missing", "gap", "overlap", "reorder", "bool", "extra", "version", "pending", "empty"],
)
def test_corrupt_restore_fails_closed(mutation):
    state = snapshot_for(2, [[0, 0], [0, 1]])
    if mutation == "missing":
        del state["coordinates"]
    elif mutation == "gap":
        state["coordinates"] = [[0, 1]]
    elif mutation == "overlap":
        state["coordinates"] = [[0, 0], [0, 0]]
    elif mutation == "reorder":
        state["coordinates"].reverse()
    elif mutation == "bool":
        state["source_count"] = True
    elif mutation == "extra":
        state["raw"] = "forbidden"
    elif mutation == "version":
        state["version"] = True
    elif mutation == "pending":
        state["pending_batch"] = 1
    else:
        state["coordinates"] = []
    with pytest.raises(core.InvalidViewError):
        core.IncrementalView.restore(state, lambda _node: "x")


def test_restore_requires_nodes_and_matching_policy():
    state = snapshot_for(1, [[0, 0]])
    with pytest.raises(core.InvalidViewError):
        core.IncrementalView.restore(state, lambda _node: None)
    with pytest.raises(core.InvalidViewError):
        core.IncrementalView.restore(state, lambda _node: "x", expected_policy=core.ViewPolicy())


def test_default_profile_really_crosses_128k_then_reaches_64k():
    view = core.IncrementalView(lambda _node: "😀" * 128)
    count = 0
    old = b""
    while len(old) + len(f"{count}+1|".encode()) + 513 <= 128_000:
        view.append()
        assert view.read().startswith(old)
        old = view.read()
        count += 1
    assert len(old) <= 128_000
    view.append()
    assert len(view.read()) <= 64_000
    assert view.state.source_count == count + 1
    assert view.snapshot()["pending_batch"] is False


def test_utf8_bytes_include_ids_and_every_newline():
    view = core.IncrementalView(lambda _node: "é", core.ViewPolicy("boundary", 7, 14))
    view.append()
    view.append()
    assert view.read() == "0+1|é\n1+1|é\n".encode()
    assert len(view.read()) == 14
    view.append()
    assert view.state.pending_batch
    assert sum(1 << node.level for node in view.state.coordinates) == 3


def test_skips_unbuilt_highest_priority_parent():
    data = snapshot_for(10, [[2, 0], [2, 1], [0, 8], [0, 9]])
    texts = {
        core.NodeCoordinate(2, 0): "x",
        core.NodeCoordinate(2, 1): "x",
        core.NodeCoordinate(0, 8): "x",
        core.NodeCoordinate(0, 9): "x",
        core.NodeCoordinate(3, 0): "x",
    }
    view = core.IncrementalView.restore(data, texts.get)
    view.advance()
    assert view.state.coordinates[0] == core.NodeCoordinate(3, 0)
    assert sum(1 << node.level for node in view.state.coordinates) == 10


def test_empty_snapshot_roundtrip():
    view = core.IncrementalView(lambda _node: None)
    restored = core.IncrementalView.restore(
        json.loads(json.dumps(view.snapshot())), lambda _node: None
    )
    assert restored.state == core.ViewState()
    assert restored.read() == b""


@pytest.mark.parametrize(
    "state", [None, [], {}, {"version": 1}], ids=["none", "array", "missing", "partial"]
)
def test_absent_snapshot_is_not_bootstrapped(state):
    with pytest.raises(core.InvalidViewError):
        core.IncrementalView.restore(state, lambda _node: "x")


@pytest.mark.parametrize(
    "coordinates",
    [None, [[0]], [[0, 0, 0]], [[21, 0]], [[0, True]]],
    ids=["none", "short", "long", "level", "bool"],
)
def test_invalid_coordinate_snapshot_shape(coordinates):
    state = snapshot_for(1, [[0, 0]])
    state["coordinates"] = coordinates
    with pytest.raises(core.InvalidViewError):
        core.IncrementalView.restore(state, lambda _node: "x")


def test_parent_oversize_is_not_a_silent_clip():
    state = snapshot_for(2, [[0, 0], [0, 1]])
    state["policy"]["low_bytes"] = 1
    view = core.IncrementalView.restore(state, lambda node: "x" if node.level == 0 else "😀" * 129)
    before = view.state
    with pytest.raises(core.InvalidViewError):
        view.advance()
    assert view.state == before
    assert view.read() == b"0+1|x\n1+1|x\n"


def test_summary_type_is_checked_at_runtime():
    view = core.IncrementalView(lambda _node: 123)  # type: ignore[arg-type, return-value]
    with pytest.raises(core.InvalidViewError):
        view.append()


def test_carriage_return_cannot_create_extra_wire_lines():
    view = core.IncrementalView(lambda _node: "a\rb\nc")
    view.append()
    assert view.read() == b"0+1|a b c\n"


def test_defaults_are_literal_byte_profile():
    assert core.ViewPolicy().low_bytes == 64_000
    assert core.ViewPolicy().high_bytes == 128_000
    assert core.ViewPolicy().namespace == "optchat-reference-v1"


@pytest.mark.parametrize(
    ("low", "high"), [(0, 10), (10, 10), (20, 10), (True, 20), (1, float("inf"))]
)
def test_invalid_policy_is_rejected(low, high):
    with pytest.raises(core.InvalidViewError):
        core.ViewPolicy(low_bytes=low, high_bytes=high)


def test_missing_leaf_is_explicit_not_ready_without_admission():
    view = core.IncrementalView(lambda _node: None)
    with pytest.raises(core.NotReadyError):
        view.append()
    assert view.state == core.ViewState()


@pytest.mark.parametrize(
    "text", ["😀" * 129, "x" * 513, "\ud800"], ids=["emoji", "ascii", "surrogate"]
)
def test_invalid_summary_is_rejected_without_admission(text):
    view = core.IncrementalView(lambda _node: text)
    with pytest.raises(core.InvalidViewError):
        view.append()
    assert view.state.source_count == 0


def test_callback_changes_cannot_rewrite_rendered_prefix():
    texts = {core.NodeCoordinate(0, 0): "original"}
    view = core.IncrementalView(texts.get)
    view.append()
    before = view.read()
    texts[core.NodeCoordinate(0, 0)] = "changed"
    assert view.read() == before


@pytest.mark.parametrize(
    ("level", "index"), [(True, 0), (0, False), (-1, 0), (21, 0), (0, 1_000_000), (0.0, 0)]
)
def test_coordinate_rejects_invalid_or_unbounded_integers(level, index):
    with pytest.raises(core.InvalidViewError):
        core.NodeCoordinate(level, index)
