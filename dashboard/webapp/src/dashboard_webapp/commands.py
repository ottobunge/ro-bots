"""Operator command queue: JSONL persistence + the say/goal allowlist.

The dashboard appends each allowlisted operator command to
``commands.jsonl`` under a configurable runtime root (default
``.work/runtime/ro-bots-test/commands``); the host-side poller
(``robots.app.command_poller``) drains that file each tick, applies the safe
subset to live agents and appends receipt lines to ``receipts.jsonl``. A
receipt carrying the command id is the back-reference that flips
:meth:`JsonlCommandQueue.status` from ``queued`` to ``applied``.

Allowlist: ``say <text>`` and ``goal <goal>`` (goal in the domain's drive
set). Anything else raises :class:`CommandNotAllowed` — the endpoint answers
422 and nothing is persisted.
"""

from __future__ import annotations

import json
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

COMMANDS_FILE = "commands.jsonl"
RECEIPTS_FILE = "receipts.jsonl"
ALLOWED_KINDS = ("say", "goal")
ALLOWED_GOALS = frozenset({"grind", "farm_item", "idle_town", "quest", "social"})


class QueuedCommandNotFound(Exception):
    pass


class CommandNotAllowed(Exception):
    """The command is outside the operator allowlist (say/goal only)."""


def parse_command(raw: str) -> tuple[str, str]:
    """Split ``say <text>`` / ``goal <goal>``; refuse everything else."""
    text = raw.strip()
    kind, _, argument = text.partition(" ")
    argument = argument.strip()
    if kind == "say" and argument:
        return kind, argument
    if kind == "goal" and argument in ALLOWED_GOALS:
        return kind, argument
    raise CommandNotAllowed(f"command not allowlisted (say <text> | goal <goal>): {raw[:40]!r}")


def _validate(kind: str, text: str) -> None:
    if kind not in ALLOWED_KINDS:
        raise CommandNotAllowed(f"command kind not allowlisted: {kind!r}")
    if kind == "goal" and text not in ALLOWED_GOALS:
        raise CommandNotAllowed(f"unknown goal: {text!r}")


@dataclass(frozen=True)
class QueuedCommand:
    id: str
    agent_id: int
    kind: str
    text: str
    char_name: str | None
    status: str
    queued_ts: float
    applied_ts: float | None = None

    @property
    def command(self) -> str:
        return f"{self.kind} {self.text}"


class CommandQueue(Protocol):
    def queue(
        self, agent_id: int, kind: str, text: str, char_name: str | None = None
    ) -> QueuedCommand: ...

    def status(self, command_id: str) -> QueuedCommand: ...


class JsonlCommandQueue:
    """Append-only ``commands.jsonl``; receipts flip the status to ``applied``.

    State lives in the runtime dir (survives dashboard restarts) so the host
    poller and the status endpoint share one source of truth.
    """

    def __init__(self, runtime_root: Path) -> None:
        self._runtime_root = Path(runtime_root)

    @property
    def commands_file(self) -> Path:
        return self._runtime_root / COMMANDS_FILE

    @property
    def receipts_file(self) -> Path:
        return self._runtime_root / RECEIPTS_FILE

    def queue(
        self, agent_id: int, kind: str, text: str, char_name: str | None = None
    ) -> QueuedCommand:
        _validate(kind, text)
        queued = QueuedCommand(
            id=f"cmd-{uuid4().hex[:12]}",
            agent_id=agent_id,
            kind=kind,
            text=text,
            char_name=char_name,
            status="queued",
            queued_ts=time.time(),
        )
        self._runtime_root.mkdir(parents=True, exist_ok=True)
        with self.commands_file.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "id": queued.id,
                        "queued_ts": queued.queued_ts,
                        "agent_id": queued.agent_id,
                        "char_name": queued.char_name,
                        "kind": queued.kind,
                        "text": queued.text,
                        "status": queued.status,
                    }
                )
                + "\n"
            )
        return queued

    def status(self, command_id: str) -> QueuedCommand:
        for line in reversed(self._read_lines(self.commands_file)):
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("id") == command_id:
                return self._with_receipt(item)
        raise QueuedCommandNotFound(f"unknown command: {command_id}")

    def _with_receipt(self, item: dict[str, Any]) -> QueuedCommand:
        applied_ts = self._applied_ts(str(item["id"]))
        return QueuedCommand(
            id=str(item["id"]),
            agent_id=int(item.get("agent_id", 0)),
            kind=str(item.get("kind", "")),
            text=str(item.get("text", "")),
            char_name=item.get("char_name"),
            status="applied" if applied_ts is not None else "queued",
            queued_ts=float(item.get("queued_ts", 0.0)),
            applied_ts=applied_ts,
        )

    def _applied_ts(self, command_id: str) -> float | None:
        applied_ts = None
        for line in self._read_lines(self.receipts_file):
            try:
                receipt = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(receipt, dict) and receipt.get("id") == command_id:
                applied_ts = receipt.get("applied_ts")
        return applied_ts

    @staticmethod
    def _read_lines(path: Path) -> list[str]:
        try:
            return path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []


class InMemoryCommandQueue:
    """Process-local double for tests; the real seam is :class:`JsonlCommandQueue`."""

    def __init__(self, capacity: int = 1000) -> None:
        self._capacity = capacity
        self._items: OrderedDict[str, QueuedCommand] = OrderedDict()

    def queue(
        self, agent_id: int, kind: str, text: str, char_name: str | None = None
    ) -> QueuedCommand:
        _validate(kind, text)
        queued = QueuedCommand(
            id=f"cmd-{uuid4().hex[:12]}",
            agent_id=agent_id,
            kind=kind,
            text=text,
            char_name=char_name,
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
