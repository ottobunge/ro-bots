"""Deterministic decision model for tests and dry runs."""

from typing import Any, final


@final
class ScriptedDecisionModel:
    """Returns canned answers, one per call (cycled), or a fixed mapping."""

    def __init__(
        self, answers: dict[str, Any] | None = None, queue: list[dict[str, Any]] | None = None
    ) -> None:
        self._answers = answers or {}
        self._queue = list(queue or [])
        self.calls = 0

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        if self._queue:
            return {"answers": self._queue.pop(0)}
        return {"answers": dict(self._answers)}
