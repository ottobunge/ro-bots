"""In-memory command queue — STUB ONLY for v1.

Commands are accepted and queued with an id; nothing is delivered to a live
agent. The wire-up to the real command seam (WorldFeed ``POST /commands``) is a
later slice; this module deliberately has no network or DB write path.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


class QueuedCommandNotFound(Exception):
    pass


@dataclass(frozen=True)
class QueuedCommand:
    id: str
    agent_id: int
    command: str
    status: str
    queued_ts: float


class CommandQueue(Protocol):
    def queue(self, agent_id: int, command: str) -> QueuedCommand: ...

    def status(self, command_id: str) -> QueuedCommand: ...


class InMemoryCommandQueue:
    """Bounded FIFO of queued commands; process-local, lost on restart."""

    def __init__(self, capacity: int = 1000) -> None:
        self._capacity = capacity
        self._items: OrderedDict[str, QueuedCommand] = OrderedDict()

    def queue(self, agent_id: int, command: str) -> QueuedCommand:
        queued = QueuedCommand(
            id=f"cmd-{uuid4().hex[:12]}",
            agent_id=agent_id,
            command=command,
            status="queued",
            queued_ts=time.time(),
        )
        self._items[queued.id] = queued
        while len(self._items) > self._capacity:
            self._items.popitem(last=False)
        return queued

    def status(self, command_id: str) -> QueuedCommand:
        try:
            return self._items[command_id]
        except KeyError:
            raise QueuedCommandNotFound(f"unknown command: {command_id}") from None
