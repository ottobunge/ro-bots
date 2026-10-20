"""Command queue: JSONL persistence + the say/goal allowlist.

The queue is the dashboard's half of the command seam: it appends each
allowlisted operator command to ``commands.jsonl`` under a configurable
runtime root; the host-side poller consumes them and writes receipt lines
that flip the status from ``queued`` to ``applied``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dashboard_webapp.commands import (
    CommandNotAllowed,
    InMemoryCommandQueue,
    JsonlCommandQueue,
    QueuedCommandNotFound,
    parse_command,
)

ALLOWED_GOALS = ("grind", "farm_item", "idle_town", "quest", "social")


def _queue(tmp_path: Path) -> JsonlCommandQueue:
    return JsonlCommandQueue(tmp_path / "runtime" / "commands")


# ------------------------------------------------------------- parse_command


def test_parse_command_allows_say_with_text() -> None:
    assert parse_command("say hello there") == ("say", "hello there")


def test_parse_command_strips_surrounding_whitespace() -> None:
    assert parse_command("  say spaced  ") == ("say", "spaced")


def test_parse_command_allows_known_goal() -> None:
    for goal in ALLOWED_GOALS:
        assert parse_command(f"goal {goal}") == ("goal", goal)


@pytest.mark.parametrize(
    ("raw", "why"),
    [
        ("", "empty"),
        ("   ", "blank"),
        ("say", "say without text"),
        ("say   ", "say without text"),
        ("goal", "goal without a name"),
        ("goal transmog", "unknown goal"),
        ("SAY hi", "kinds are lowercase"),
        ("saymehi", "no kind separator"),
        ("/sit", "slash commands refused"),
        ("rm -rf /", "shell refused"),
        ("teleport prontera", "non-allowlisted kind"),
    ],
)
def test_parse_command_refuses_non_allowlisted(raw: str, why: str) -> None:
    with pytest.raises(CommandNotAllowed):
        parse_command(raw)


# --------------------------------------------------------- JsonlCommandQueue


def test_queue_persists_one_jsonl_line(tmp_path: Path) -> None:
    queue = _queue(tmp_path)

    queued = queue.queue(agent_id=150001, kind="say", text="hi", char_name="Fx_0")

    lines = (
        (tmp_path / "runtime" / "commands" / "commands.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert len(lines) == 1
    assert json.loads(lines[0]) == {
        "id": queued.id,
        "queued_ts": queued.queued_ts,
        "agent_id": 150001,
        "char_name": "Fx_0",
        "kind": "say",
        "text": "hi",
        "status": "queued",
    }
    assert queued.id.startswith("cmd-")
    assert queued.status == "queued"


def test_queue_defaults_char_name_to_none(tmp_path: Path) -> None:
    queue = _queue(tmp_path)

    assert queue.queue(agent_id=1, kind="goal", text="quest").char_name is None


def test_status_returns_the_persisted_command(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    queued = queue.queue(agent_id=7, kind="goal", text="quest")

    status = queue.status(queued.id)

    assert (status.kind, status.text, status.status, status.applied_ts) == (
        "goal",
        "quest",
        "queued",
        None,
    )


def test_status_flips_applied_once_receipt_written(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    queued = queue.queue(agent_id=7, kind="say", text="hi")
    receipts = tmp_path / "runtime" / "commands" / "receipts.jsonl"
    receipts.write_text(
        json.dumps({"id": queued.id, "applied_ts": 123.5, "ok": True, "detail": ""}) + "\n",
        encoding="utf-8",
    )

    status = queue.status(queued.id)

    assert status.status == "applied"
    assert status.applied_ts == 123.5


def test_status_keeps_queued_for_foreign_receipt_ids(tmp_path: Path) -> None:
    queue = _queue(tmp_path)
    queued = queue.queue(agent_id=7, kind="say", text="hi")
    receipts = tmp_path / "runtime" / "commands" / "receipts.jsonl"
    receipts.write_text(
        json.dumps({"id": "cmd-other", "applied_ts": 1.0, "ok": True, "detail": ""}) + "\n",
        encoding="utf-8",
    )

    assert queue.status(queued.id).status == "queued"


def test_unknown_command_id_raises(tmp_path: Path) -> None:
    with pytest.raises(QueuedCommandNotFound):
        _queue(tmp_path).status("cmd-does-not-exist")


def test_queue_rejects_non_allowlisted_kind(tmp_path: Path) -> None:
    with pytest.raises(CommandNotAllowed):
        _queue(tmp_path).queue(agent_id=1, kind="shell", text="rm -rf /")


def test_queue_rejects_unknown_goal(tmp_path: Path) -> None:
    with pytest.raises(CommandNotAllowed):
        _queue(tmp_path).queue(agent_id=1, kind="goal", text="transmog")


def test_queue_commands_survive_a_queue_restart(tmp_path: Path) -> None:
    first = _queue(tmp_path)
    queued = first.queue(agent_id=9, kind="say", text="persisted")

    reopened = JsonlCommandQueue(tmp_path / "runtime" / "commands")

    assert reopened.status(queued.id).text == "persisted"


# ------------------------------------------------------ InMemory test double


def test_inmemory_queue_keeps_legacy_double_shape() -> None:
    queue = InMemoryCommandQueue()

    queued = queue.queue(agent_id=5, kind="say", text="hi")

    assert queue.status(queued.id).text == "hi"
    with pytest.raises(QueuedCommandNotFound):
        queue.status("cmd-none")
