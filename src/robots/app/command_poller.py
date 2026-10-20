"""Dashboard command seam: drain queued operator commands into a live host.

The dashboard persists allowlisted operator commands (``say``/``goal``) as
JSON lines under a configurable runtime root (dashboard default
``.work/runtime/ro-bots-test/commands``):

- ``commands.jsonl`` — one line per queued command
  (``id``, ``queued_ts``, ``agent_id``, ``char_name``, ``kind``, ``text``);
- ``receipts.jsonl`` — one line per consumed command (``id``, ``applied_ts``,
  ``ok``, ``detail``): the back-reference that flips the dashboard's
  ``GET /api/commands/{id}`` status from ``queued`` to ``applied``.

The window composition calls :func:`poll_once` once per scheduling tick
(``python -m robots.playing --command-root <runtime dir>``). Each drained
command is applied through the safe subset only: a chat ``say`` goes through
the host's locked chat-command dispatcher (same admission path as the
WorldFeed ``POST /commands``), a ``goal`` override sets the persona's
high-level drive. Any other kind is refused and receipted — never executed.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from robots.domain.model import Goal

COMMANDS_FILE = "commands.jsonl"
RECEIPTS_FILE = "receipts.jsonl"
ALLOWED_KINDS = ("say", "goal")


class CommandFormatError(Exception):
    """A persisted command line violates the allowlisted shape."""


class ChatDispatchTarget(Protocol):
    """The slice of ScheduledAgent the poller needs."""

    @property
    def entry(self) -> Any: ...

    @property
    def online(self) -> bool: ...

    goal: Any


class CommandHost(Protocol):
    """The slice of AgentHost the poller needs."""

    @property
    def agents(self) -> Mapping[str, ChatDispatchTarget]: ...

    @property
    def commands(self) -> Any: ...


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse a JSON-lines file, skipping blank and malformed lines."""
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            item = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            items.append(item)
    return items


def drain_commands(runtime_dir: Path) -> list[dict[str, Any]]:
    """Queued (not yet receipted) commands, oldest first.

    Raises :class:`CommandFormatError` for a non-allowlisted kind — the file is
    a control channel, so a malformed line must stop the tick loudly instead of
    being applied or silently dropped.
    """
    receipted = {str(item.get("id")) for item in _read_jsonl(runtime_dir / RECEIPTS_FILE)}
    drained: list[dict[str, Any]] = []
    for command in _read_jsonl(runtime_dir / COMMANDS_FILE):
        if str(command.get("id")) in receipted:
            continue
        if command.get("kind") not in ALLOWED_KINDS:
            msg = f"command kind not allowlisted: {command.get('kind')!r}"
            raise CommandFormatError(msg)
        drained.append(command)
    return drained


def write_receipts(runtime_dir: Path, receipts: Sequence[Mapping[str, Any]]) -> None:
    """Append the receipt lines; the dashboard polls this file for status."""
    runtime_dir.mkdir(parents=True, exist_ok=True)
    with (runtime_dir / RECEIPTS_FILE).open("a", encoding="utf-8") as handle:
        for receipt in receipts:
            handle.write(json.dumps(receipt) + "\n")


def _receipt(command: Mapping[str, Any], ok: bool, detail: str) -> dict[str, Any]:
    return {"id": str(command.get("id")), "applied_ts": time.time(), "ok": ok, "detail": detail}


def _resolve_persona(host: CommandHost, command: Mapping[str, Any]) -> str | None:
    """Persona id for a command: manifest char_name first, persona id second."""
    char_name = str(command.get("char_name") or "")
    if char_name:
        for persona_id, agent in host.agents.items():
            entry = getattr(agent, "entry", None)
            if getattr(entry, "char_name", None) == char_name:
                return persona_id
    fallback = str(command.get("agent_id") or "")
    if fallback in host.agents:
        return fallback
    return None


def apply_to_host(host: CommandHost, commands: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Apply the safe subset; every command gets exactly one receipt."""
    return [_apply_one(host, command) for command in commands]


def _apply_one(host: CommandHost, command: Mapping[str, Any]) -> dict[str, Any]:
    kind = command.get("kind")
    if kind not in ALLOWED_KINDS:
        return _receipt(command, False, f"command kind not allowlisted: {kind!r}")
    persona_id = _resolve_persona(host, command)
    if persona_id is None:
        return _receipt(command, False, "unknown persona for command target")
    agent = host.agents[persona_id]
    if kind == "goal":
        return _apply_goal(command, agent)
    return _apply_say(host, command, persona_id, agent)


def _apply_goal(command: Mapping[str, Any], agent: ChatDispatchTarget) -> dict[str, Any]:
    try:
        goal = Goal(str(command.get("text") or ""))
    except ValueError:
        return _receipt(command, False, f"unknown goal: {command.get('text')!r}")
    agent.goal = goal  # the persona's live high-level drive
    return _receipt(command, True, "")


def _apply_say(
    host: CommandHost, command: Mapping[str, Any], persona_id: str, agent: ChatDispatchTarget
) -> dict[str, Any]:
    if not getattr(agent, "online", False):
        return _receipt(command, False, "agent offline; say needs a live session")
    try:
        host.commands.submit(
            {
                "type": "force_action",
                "action": "chat",
                "command_id": str(command.get("id")),
                "persona_id": persona_id,
                "args": str(command.get("text") or ""),
            }
        )
    except Exception as exc:  # dispatcher admission errors are receipted, not raised
        return _receipt(command, False, f"chat dispatch failed: {exc}")
    return _receipt(command, True, "")


def poll_once(host: CommandHost, runtime_dir: Path) -> int:
    """One composition tick: drain, apply, receipt. Returns receipts written."""
    commands = drain_commands(runtime_dir)
    if not commands:
        return 0
    receipts = apply_to_host(host, commands)
    write_receipts(runtime_dir, receipts)
    return len(receipts)
