"""Deterministic chat generator for tests and dry runs."""

from typing import final


@final
class StaticChatGenerator:
    """Replies from a fixed pool, in order (cycled)."""

    def __init__(self, replies: list[str] | None = None) -> None:
        self._replies = replies or ["ok!", "ha, nice", "brb"]
        self._next = 0

    def generate_chat(self, prompt: str) -> str:
        reply = self._replies[self._next % len(self._replies)]
        self._next += 1
        return reply
