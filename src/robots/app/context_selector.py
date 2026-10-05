"""ADR-006: Clef as a context selector for agent memory.

The structural view (ADR-004) decides *resolution*; this module decides
*relevance*. A :class:`ContextSelector` picks which memory lines reach the
decision request:

- :class:`TreeCoverSelector` — the default: the structural OptChat tree-cover
  view, zero model calls.
- :class:`ClefContextSelector` — one SystemOne forward pass: up to 64 ``score``
  questions, one per candidate line ("how relevant is this memory to my
  current situation?"), ranked by expected score, top lines kept under a char
  budget. Lines scoring below :data:`RELEVANCE_EPSILON` are actively
  suppressed — suppression is information too. Any model failure falls back to
  the tree-cover order: the tick never crashes on a bad selector.

After selection, ``level > 0`` lines are zoomed into their two children while
the expansion fits the budget (zoom-after-selection), and the whole outcome is
reported as a :class:`ContextSelection` so the runner can log a "recalled X"
experience note — memory about memory, which compounds.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, final, runtime_checkable

from robots.domain.decisions import build_decision_request
from robots.society.memory import (
    VIEW_BUDGET_CHARS,
    Memory,
    MemoryLog,
    fit_budget,
    render_view,
    zoom,
)

if TYPE_CHECKING:
    from robots.domain.model import BotState
    from robots.ports import DecisionModel

logger = logging.getLogger(__name__)

RELEVANCE_EPSILON = 0.25
MAX_RELEVANCE_QUESTIONS = 64
RELEVANCE_INSTRUCTIONS = "How relevant is this memory to my current situation?"
RELEVANCE_CRITERIA = ["Irrelevant now", "Somewhat relevant", "Essential context"]

_NODE_ID = re.compile(r"L(\d+):(\d+)")


@dataclass(frozen=True, slots=True)
class ContextSelection:
    """Outcome of one context selection (ADR-006: memory about memory)."""

    selected: list[str] = field(default_factory=list)
    dropped_below_epsilon: list[str] = field(default_factory=list)
    zoomed: list[str] = field(default_factory=list)
    fallback: bool = False


@runtime_checkable
class ContextSelector(Protocol):
    """Selects the memory lines to inject into one decision request."""

    def select(self, state: BotState, candidates: list[str], budget_chars: int) -> list[str]:
        """Return the memory lines for this tick's decision request."""
        ...


@runtime_checkable
class _DetailedSelector(Protocol):
    """A selector that also reports the full selection outcome."""

    def select_detailed(
        self, state: BotState, candidates: list[str], budget_chars: int
    ) -> ContextSelection: ...


def node_id(line: str) -> str:
    """The addressable id (``'L2:3'``) prefixing a view line."""
    return line.split(" ", 1)[0]


def _node_level(line: str) -> int:
    """Tree level of a view line's id, or -1 if the line is not addressable."""
    match = _NODE_ID.fullmatch(node_id(line))
    return int(match.group(1)) if match else -1


@final
class TreeCoverSelector:
    """Default selector: the structural OptChat tree-cover view (zero model calls)."""

    def select(self, _state: BotState, candidates: list[str], budget_chars: int) -> list[str]:
        """Trim the structural view to the budget; oldest lines drop first."""
        return self.select_detailed(_state, candidates, budget_chars).selected

    def select_detailed(
        self, _state: BotState, candidates: list[str], budget_chars: int
    ) -> ContextSelection:
        return ContextSelection(selected=fit_budget(candidates, budget_chars))


@final
class ClefContextSelector:
    """Ranks candidate memory lines by relevance in ONE Clef forward pass.

    Builds a SystemOne request whose state is the bot's current state summary
    and whose questions are one ``score`` question per candidate line, keyed by
    the line's addressable id. The candidate texts ride along in
    ``state['memory_candidates']`` so the model can actually judge them.
    """

    def __init__(self, model: DecisionModel) -> None:
        self._model = model

    def select(self, state: BotState, candidates: list[str], budget_chars: int) -> list[str]:
        return self.select_detailed(state, candidates, budget_chars).selected

    def select_detailed(
        self, state: BotState, candidates: list[str], budget_chars: int
    ) -> ContextSelection:
        try:
            ranked, tail = self._rank(state, candidates)
        except Exception as exc:
            logger.warning("context selection failed; using tree cover: %s", exc)
            return ContextSelection(selected=fit_budget(candidates, budget_chars), fallback=True)
        selected: list[str] = []
        used = 0
        dropped: list[str] = []
        for line, score in ranked:
            if score < RELEVANCE_EPSILON:
                dropped.append(line)
                continue
            extra = len(line) + (1 if selected else 0)
            if used + extra > budget_chars:
                continue  # over budget: try smaller, lower-ranked lines
            selected.append(line)
            used += extra
        if tail:  # unscored lines survive as the structural tail
            allowed = budget_chars - used - (1 if selected else 0)
            selected.extend(fit_budget(tail, max(allowed, 0)))
        kept = set(selected)
        ordered = [c for c in candidates if c in kept]  # keep structural order
        return ContextSelection(selected=ordered, dropped_below_epsilon=dropped)

    def _rank(
        self, state: BotState, candidates: list[str]
    ) -> tuple[list[tuple[str, float]], list[str]]:
        """One forward pass: score each candidate line; unscored lines tail on."""
        scoreable = [c for c in candidates if _node_level(c) >= 0]
        asked = scoreable[:MAX_RELEVANCE_QUESTIONS]
        tail = scoreable[MAX_RELEVANCE_QUESTIONS:] + [c for c in candidates if _node_level(c) < 0]
        request = {
            "model": "clef",
            "state": {
                **build_decision_request(state)["state"],
                "memory_candidates": {node_id(line): line for line in asked},
            },
            "questions": {
                node_id(line): {
                    "type": "score",
                    "instructions": RELEVANCE_INSTRUCTIONS,
                    "criteria": list(RELEVANCE_CRITERIA),
                }
                for line in asked
            },
        }
        response = self._model.decide(request)
        answers: dict[str, Any] = response.get("answers", {})
        scored = [(line, float(answers.get(node_id(line), {}).get("score", 0.0))) for line in asked]
        scored.sort(key=lambda pair: pair[1], reverse=True)  # stable: ties keep view order
        return scored, tail


def select_with_zoom(
    selector: ContextSelector,
    log: MemoryLog,
    state: BotState,
    budget_chars: int,
    candidates: list[str] | None = None,
) -> tuple[list[str], ContextSelection]:
    """Select context, then zoom level>0 lines into their children (ADR-006).

    Zoom-after-selection: any chosen line whose id is a level>0 node is
    expanded into its two children when the expansion still fits the budget.
    Without explicit ``candidates`` the tree-cover view of ``log`` is used.
    """
    view = candidates if candidates is not None else render_view(log, budget_chars)
    if isinstance(selector, _DetailedSelector):
        selection = selector.select_detailed(state, view, budget_chars)
    else:
        selection = ContextSelection(selected=selector.select(state, view, budget_chars))
    lines = list(selection.selected)
    zoomed: list[str] = []
    for line in list(lines):
        if _node_level(line) <= 0:
            continue
        expanded = zoom(log, lines, node_id(line))
        if expanded == lines or _total_chars(expanded) > budget_chars:
            continue
        lines = expanded
        zoomed.append(node_id(line))
    return lines, ContextSelection(
        selected=lines,
        dropped_below_epsilon=selection.dropped_below_epsilon,
        zoomed=zoomed,
        fallback=selection.fallback,
    )


def _total_chars(lines: list[str]) -> int:
    return len("\n".join(lines))


@final
class MemoryContextBridge:
    """Composes a Memory with a ContextSelector and logs the selection (ADR-006).

    The selection itself becomes an experience note in the agent's own log —
    memory about memory.
    """

    def __init__(self, memory: Memory, selector: ContextSelector) -> None:
        self._memory = memory
        self._selector = selector

    def recall(
        self, state: BotState, budget_chars: int = VIEW_BUDGET_CHARS, now: float | None = None
    ) -> tuple[list[str], ContextSelection]:
        """Select context for this tick; append a 'recalled X' note to the log."""
        lines, selection = select_with_zoom(self._selector, self._memory.log, state, budget_chars)
        if lines:
            reason = "structural fallback" if selection.fallback else "ranked relevant"
            ids = ", ".join(node_id(line) for line in lines)
            self._memory.remember(
                "other", f"recalled {ids} because {reason}", ts=now if now is not None else 0.0
            )
        return lines, selection
