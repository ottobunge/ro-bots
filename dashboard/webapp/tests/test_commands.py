"""Command queue stub tests: queue, status, unknown id, capacity."""

from __future__ import annotations

import pytest

from dashboard_webapp.commands import InMemoryCommandQueue, QueuedCommandNotFound


def test_queue_assigns_distinct_ids_and_defaults() -> None:
    queue = InMemoryCommandQueue()
    first = queue.queue(agent_id=150001, command="/hi there")
    second = queue.queue(agent_id=150002, command="/sit")

    assert first.id != second.id
    assert first.id.startswith("cmd-")
    assert first.status == "queued"
    assert first.agent_id == 150001
    assert first.command == "/hi there"
    assert first.queued_ts > 0


def test_status_returns_queued_command() -> None:
    queue = InMemoryCommandQueue()
    queued = queue.queue(agent_id=7, command="/heal")

    assert queue.status(queued.id).command == "/heal"


def test_unknown_command_id_raises() -> None:
    queue = InMemoryCommandQueue()
    with pytest.raises(QueuedCommandNotFound):
        queue.status("cmd-does-not-exist")


def test_queue_is_bounded_and_keeps_newest() -> None:
    queue = InMemoryCommandQueue(capacity=3)
    ids = [queue.queue(agent_id=i, command=f"c{i}").id for i in range(5)]

    assert queue.status(ids[-1]).command == "c4"
    with pytest.raises(QueuedCommandNotFound):
        queue.status(ids[0])
