"""ADR-006: Clef as a context selector for agent memory."""

from typing import Any

from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.context_selector import (
    MAX_RELEVANCE_QUESTIONS,
    RELEVANCE_EPSILON,
    ClefContextSelector,
    ContextSelection,
    ContextSelector,
    MemoryContextBridge,
    TreeCoverSelector,
    node_id,
    select_with_zoom,
)
from robots.society.memory import Memory, StubSummarizer, render_view
from tests.conftest import make_state


def make_memory(n: int, text: str = "note {}") -> Memory:
    memory = Memory(StubSummarizer())
    for i in range(n):
        memory.remember("chat", text.format(i), ts=1000.0 + i)
    return memory


def view(memory: Memory) -> list[str]:
    return render_view(memory.log)


def answers_for(lines: list[str], scores: dict[str, float]) -> dict[str, Any]:
    """Scripted answers: one score per question id, keyed by addressable id."""
    return {node_id(line): {"score": scores.get(node_id(line), 0.0)} for line in lines}


class ExplodingModel:
    """A DecisionModel that is down — the selector must survive it."""

    def decide(self, _request: dict[str, Any]) -> dict[str, Any]:
        msg = "clef down"
        raise RuntimeError(msg)


# -- TreeCoverSelector -----------------------------------------------------


def test_tree_cover_returns_view_within_budget() -> None:
    lines = view(make_memory(9))
    got = TreeCoverSelector().select(make_state(), lines, budget_chars=200)
    assert got
    assert len("\n".join(got)) <= 200
    assert got[-1] == lines[-1]  # oldest dropped first; newest survives at full resolution


def test_tree_cover_detailed_marks_no_fallback() -> None:
    selection = TreeCoverSelector().select_detailed(make_state(), ["L0:0 hi"], 100)
    assert selection == ContextSelection(selected=["L0:0 hi"], fallback=False)


# -- ClefContextSelector: ranking, budget, suppression ----------------------


def test_clef_selector_ranks_by_expected_score() -> None:
    lines = view(make_memory(3))  # [L1:0, L0:2]
    ids = [node_id(line) for line in lines]
    model = ScriptedDecisionModel(answers=answers_for(lines, {ids[0]: 0.0, ids[1]: 1.0}))
    selection = ClefContextSelector(model).select_detailed(make_state(), lines, 10_000)
    # structural order preserved; the line scoring below epsilon is suppressed
    assert selection.selected == [lines[1]]
    assert lines[0] in selection.dropped_below_epsilon
    assert model.calls == 1  # ONE forward pass


def test_clef_selector_respects_budget() -> None:
    lines = view(make_memory(4))
    model = ScriptedDecisionModel(
        answers=answers_for(lines, {node_id(line): 2.0 for line in lines})
    )
    budget = len(lines[-1]) + 1  # room for exactly one line
    selection = ClefContextSelector(model).select_detailed(make_state(), lines, budget)
    assert len(selection.selected) == 1
    assert len("\n".join(selection.selected)) <= budget


def test_clef_selector_drops_below_epsilon() -> None:
    lines = view(make_memory(3))  # [L1:0, L0:2]
    ids = [node_id(line) for line in lines]
    scores = {ids[0]: 2.0, ids[1]: RELEVANCE_EPSILON - 0.01}
    model = ScriptedDecisionModel(answers=answers_for(lines, scores))
    selection = ClefContextSelector(model).select_detailed(make_state(), lines, 10_000)
    assert lines[1] in selection.dropped_below_epsilon
    assert lines[1] not in selection.selected
    assert selection.selected == [lines[0]]


# -- request shape -----------------------------------------------------------


class CapturingModel:
    """Records the last request, then answers every question with 0.0."""

    def __init__(self) -> None:
        self.last_request: dict[str, Any] = {}

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        self.last_request = request
        questions = request.get("questions", {})
        assert isinstance(questions, dict)
        return {"answers": {qid: {"score": 0.0} for qid in questions}}


def test_clef_selector_request_shape() -> None:
    lines = view(make_memory(2))
    model = CapturingModel()
    selection = ClefContextSelector(model).select_detailed(make_state(), lines, 10_000)

    questions = model.last_request["questions"]
    assert set(questions) == {node_id(line) for line in lines}
    for question in questions.values():
        assert question["type"] == "score"
        assert question["instructions"] == "How relevant is this memory to my current situation?"
        assert question["criteria"] == [
            "Irrelevant now",
            "Somewhat relevant",
            "Essential context",
        ]
    state = model.last_request["state"]
    assert state["bot"]["name"] == "SpikeBot01"  # the bot's own state summary
    assert set(state["memory_candidates"]) == {node_id(line) for line in lines}
    assert selection.dropped_below_epsilon == lines  # all scored 0.0


def test_clef_selector_caps_questions_at_64() -> None:
    # synthetic candidates: the structural cover of a realistic log is far
    # below 64 lines, so the cap is exercised with many addressable lines
    lines = [f"L0:{i} note {i}" for i in range(70)]
    model = CapturingModel()
    ClefContextSelector(model).select(make_state(), lines, 10_000)
    questions = model.last_request["questions"]
    assert len(questions) == MAX_RELEVANCE_QUESTIONS
    assert set(questions) == {f"L0:{i}" for i in range(64)}
    assert model.last_request["state"]["memory_candidates"] == {
        f"L0:{i}": f"L0:{i} note {i}" for i in range(64)
    }


# -- fallback ---------------------------------------------------------------


def test_clef_selector_falls_back_on_model_failure() -> None:
    lines = view(make_memory(3))
    selection = ClefContextSelector(ExplodingModel()).select_detailed(make_state(), lines, 10_000)
    assert selection.fallback is True
    assert selection.selected == lines  # structural view, order intact


# -- zoom-after-selection ----------------------------------------------------


def test_zoom_after_selection_expands_level_positive_node() -> None:
    memory = make_memory(8)
    lines = view(memory)  # 8 notes -> L2:0 + L1:2 + L0:6 + L0:7
    parent = next(line for line in lines if node_id(line) == "L2:0")
    model = ScriptedDecisionModel(answers=answers_for(lines, {node_id(parent): 2.0}))
    selected, selection = select_with_zoom(
        ClefContextSelector(model), memory.log, make_state(), 10_000
    )
    assert selection.zoomed == ["L2:0"]
    assert "L2:0" not in {node_id(line) for line in selected}
    assert {"L1:0", "L1:1"} <= {node_id(line) for line in selected}
    assert len("\n".join(selected)) <= 10_000


def test_zoom_skipped_when_children_do_not_fit() -> None:
    memory = make_memory(8)
    lines = view(memory)
    parent = next(line for line in lines if node_id(line) == "L2:0")
    model = ScriptedDecisionModel(
        answers=answers_for(lines, {node_id(line): 2.0 for line in lines})
    )
    # children replace the parent, so the budget must cover both: a budget
    # that fits the parent line alone cannot fit the two children
    tight = len(parent)
    selected, selection = select_with_zoom(
        ClefContextSelector(model), memory.log, make_state(), tight
    )
    assert selection.zoomed == []
    assert {node_id(line) for line in selected} == {"L0:6", "L0:7"}
    assert "L2:0" not in {node_id(line) for line in selected}


def test_zoom_not_applied_to_level_zero_lines() -> None:
    memory = make_memory(2)
    lines = view(memory)  # two L0 lines only
    model = ScriptedDecisionModel(
        answers=answers_for(lines, {node_id(line): 2.0 for line in lines})
    )
    selected, selection = select_with_zoom(
        ClefContextSelector(model), memory.log, make_state(), 10_000
    )
    assert selection.zoomed == []
    assert selected == lines


# -- MemoryContextBridge -----------------------------------------------------


def test_bridge_appends_selection_note_to_log() -> None:
    memory = make_memory(3)
    lines = view(memory)
    ids = [node_id(line) for line in lines]
    model = ScriptedDecisionModel(answers=answers_for(lines, {ids[0]: 2.0, ids[1]: 1.0}))
    bridge = MemoryContextBridge(memory, ClefContextSelector(model))
    selected, selection = bridge.recall(make_state(), budget_chars=10_000, now=2000.0)
    assert selection.selected == selected
    notes = memory.log.notes()
    last = notes[-1]
    assert last.kind == "other"
    assert "recalled" in last.text
    for line in selected:
        assert node_id(line) in last.text
    assert len(notes) == 4  # 3 planted + 1 selection note


def test_bridge_note_on_fallback() -> None:
    memory = make_memory(2)
    view(memory)
    bridge = MemoryContextBridge(memory, ClefContextSelector(ExplodingModel()))
    _lines, selection = bridge.recall(make_state(), budget_chars=10_000, now=2000.0)
    assert selection.fallback
    assert "structural fallback" in memory.log.notes()[-1].text


# -- protocol conformance -----------------------------------------------------


def test_selectors_satisfy_protocol() -> None:
    assert isinstance(TreeCoverSelector(), ContextSelector)
    assert isinstance(ClefContextSelector(ScriptedDecisionModel()), ContextSelector)


# -- seeded recall -------------------------------------------------------------


def _planted() -> Memory:
    memory = Memory(StubSummarizer())
    memory.remember("chat", "met TraderMika near prontera", ts=1000.0)
    for i in range(5):
        memory.remember("combat", f"fought monster {i}", ts=1001.0 + i)
    return memory


def test_seeded_fact_recalled_when_state_references_it() -> None:
    memory = _planted()
    lines = view(memory)
    seeded = [line for line in lines if "TraderMika" in line]
    assert seeded, "seeded fact must appear in the structural view"
    # the state references the name; the model scores the seeded line essential
    state = make_state(name="TraderMika-follower")
    scores = {node_id(line): (2.0 if "TraderMika" in line else 0.0) for line in lines}
    model = ScriptedDecisionModel(answers=answers_for(lines, scores))
    selection = ClefContextSelector(model).select_detailed(state, lines, 10_000)
    assert seeded[0] in selection.selected


def test_seeded_fact_dropped_when_state_unrelated_and_budget_tight() -> None:
    memory = _planted()
    lines = view(memory)
    seeded = next(line for line in lines if "TraderMika" in line)
    others = [line for line in lines if "TraderMika" not in line]
    # unrelated state: nothing scores; tight budget so suppression is visible
    model = ScriptedDecisionModel(answers={})
    selection = ClefContextSelector(model).select_detailed(
        make_state(), lines, budget_chars=len(others[0]) + 1
    )
    assert seeded not in selection.selected
    assert seeded in selection.dropped_below_epsilon
