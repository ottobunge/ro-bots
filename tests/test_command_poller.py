"""Command-poller seam: dashboard commands.jsonl -> live AgentHost actions.

The dashboard persists allowlisted operator commands (``say``/``goal``) as
JSON lines under the runtime root; the host side drains that file once per
scheduling tick, applies the safe subset to live agents, and writes a receipt
line per command. The receipt is the back-reference that flips the dashboard's
command status from ``queued`` to ``applied``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from robots import playing
from robots.app.command_poller import (
    CommandFormatError,
    apply_to_host,
    drain_commands,
    poll_once,
    write_receipts,
)
from robots.domain.model import Goal


class FakeDispatcher:
    """Records HostChatCommands.submit payloads."""

    def __init__(self, error: Exception | None = None) -> None:
        self.submitted: list[dict[str, Any]] = []
        self.error = error

    def submit(self, command: dict[str, Any]) -> dict[str, Any]:
        if self.error is not None:
            raise self.error
        self.submitted.append(dict(command))
        return {"command_id": command["command_id"], "status": "queued"}


class FakeEntry:
    def __init__(self, char_name: str) -> None:
        self.char_name = char_name


class FakeAgent:
    def __init__(self, char_name: str, online: bool = True) -> None:
        self.entry = FakeEntry(char_name)
        self.online = online
        self.goal: Goal = Goal.GRIND


class FakeHost:
    def __init__(self, agents: dict[str, FakeAgent], dispatcher: FakeDispatcher) -> None:
        self.agents = agents
        self.commands = dispatcher
        self.steps = 0

    def start_worldfeed(self) -> None:
        pass

    def step(self) -> None:
        self.steps += 1

    def stop(self) -> None:
        pass


def write_command(runtime_dir: Path, **fields: Any) -> dict[str, Any]:
    command_id = fields.pop("id", "aaaaaaaaaaaa")
    command: dict[str, Any] = {
        "id": "cmd-" + command_id,
        "queued_ts": fields.pop("queued_ts", time.time()),
        "agent_id": fields.pop("agent_id", 150001),
        "char_name": fields.pop("char_name", "Fx_0"),
        "kind": fields.pop("kind", "say"),
        "text": fields.pop("text", "hello"),
        "status": "queued",
        **fields,
    }
    runtime_dir.mkdir(parents=True, exist_ok=True)
    with (runtime_dir / "commands.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(command) + "\n")
    return command


# --------------------------------------------------------------------- drain


def test_drain_missing_runtime_dir_returns_empty(tmp_path: Path) -> None:
    assert drain_commands(tmp_path / "absent") == []


def test_drain_returns_queued_commands_oldest_first(tmp_path: Path) -> None:
    first = write_command(tmp_path, id="first000001")
    second = write_command(tmp_path, id="second00002", kind="goal", text="quest")

    drained = drain_commands(tmp_path)

    assert [item["id"] for item in drained] == [first["id"], second["id"]]
    assert drained[1]["kind"] == "goal"
    assert drained[1]["text"] == "quest"


def test_drain_skips_blank_and_malformed_lines(tmp_path: Path) -> None:
    (tmp_path / "commands.jsonl").write_text(
        'not json\n\n{"id": "cmd-ok00000001", "kind": "say"}\n', encoding="utf-8"
    )

    drained = drain_commands(tmp_path)

    assert [item["id"] for item in drained] == ["cmd-ok00000001"]


def test_drain_excludes_receipted_commands(tmp_path: Path) -> None:
    command = write_command(tmp_path, id="done00000001")
    write_command(tmp_path, id="pending000001")
    write_receipts(
        tmp_path, [{"id": command["id"], "applied_ts": time.time(), "ok": True, "detail": ""}]
    )

    drained = drain_commands(tmp_path)

    assert [item["id"] for item in drained] == ["cmd-pending000001"]


def test_write_receipts_appends_jsonl(tmp_path: Path) -> None:
    write_receipts(tmp_path, [{"id": "cmd-a", "applied_ts": 1.0, "ok": True, "detail": ""}])
    write_receipts(tmp_path, [{"id": "cmd-b", "applied_ts": 2.0, "ok": False, "detail": "x"}])

    lines = (tmp_path / "receipts.jsonl").read_text(encoding="utf-8").splitlines()

    assert [json.loads(line)["id"] for line in lines] == ["cmd-a", "cmd-b"]


def test_drain_rejects_command_with_unknown_kind(tmp_path: Path) -> None:
    write_command(tmp_path, kind="shell", text="rm -rf /")

    with pytest.raises(CommandFormatError):
        drain_commands(tmp_path)


# ---------------------------------------------------------------------- apply


def test_apply_say_submits_force_action_chat_for_online_agent(tmp_path: Path) -> None:
    dispatcher = FakeDispatcher()
    host = FakeHost({"fx0": FakeAgent("Fx_0", online=True)}, dispatcher)
    command = write_command(tmp_path, id="say000000001", char_name="Fx_0")

    receipts = apply_to_host(host, drain_commands(tmp_path))

    assert len(receipts) == 1
    assert receipts[0]["id"] == command["id"]
    assert receipts[0]["ok"] is True
    assert dispatcher.submitted == [
        {
            "type": "force_action",
            "action": "chat",
            "command_id": command["id"],
            "persona_id": "fx0",
            "args": "hello",
        }
    ]


def test_apply_say_offline_agent_fails_without_dispatch(tmp_path: Path) -> None:
    dispatcher = FakeDispatcher()
    host = FakeHost({"fx0": FakeAgent("Fx_0", online=False)}, dispatcher)
    command = write_command(tmp_path, char_name="Fx_0")

    receipts = apply_to_host(host, drain_commands(tmp_path))

    assert dispatcher.submitted == []
    assert receipts[0]["id"] == command["id"]
    assert receipts[0]["ok"] is False
    assert "offline" in receipts[0]["detail"]


def test_apply_say_unknown_persona_fails_without_dispatch(tmp_path: Path) -> None:
    dispatcher = FakeDispatcher()
    host = FakeHost({}, dispatcher)
    write_command(tmp_path, char_name="Nobody")

    receipts = apply_to_host(host, drain_commands(tmp_path))

    assert dispatcher.submitted == []
    assert receipts[0]["ok"] is False
    assert "unknown persona" in receipts[0]["detail"]


def test_apply_say_dispatcher_error_is_receipted_not_raised(tmp_path: Path) -> None:
    dispatcher = FakeDispatcher(error=RuntimeError("queue full"))
    host = FakeHost({"fx0": FakeAgent("Fx_0")}, dispatcher)
    command = write_command(tmp_path, char_name="Fx_0")

    receipts = apply_to_host(host, drain_commands(tmp_path))

    assert receipts[0]["id"] == command["id"]
    assert receipts[0]["ok"] is False
    assert "queue full" in receipts[0]["detail"]


def test_apply_goal_overrides_online_agent_goal(tmp_path: Path) -> None:
    dispatcher = FakeDispatcher()
    agent = FakeAgent("Fx_0")
    host = FakeHost({"fx0": agent}, dispatcher)
    write_command(tmp_path, kind="goal", text="quest")

    receipts = apply_to_host(host, drain_commands(tmp_path))

    assert agent.goal is Goal.QUEST
    assert receipts[0]["ok"] is True
    assert dispatcher.submitted == []  # goal override never touches chat


def test_apply_goal_applies_to_offline_agent_too(tmp_path: Path) -> None:
    """Goal override is persistent persona state; it must not need a session."""
    agent = FakeAgent("Fx_0", online=False)
    host = FakeHost({"fx0": agent}, FakeDispatcher())
    write_command(tmp_path, kind="goal", text="farm_item")

    receipts = apply_to_host(host, drain_commands(tmp_path))

    assert agent.goal is Goal.FARM_ITEM
    assert receipts[0]["ok"] is True


def test_apply_goal_unknown_goal_refused(tmp_path: Path) -> None:
    agent = FakeAgent("Fx_0")
    host = FakeHost({"fx0": agent}, FakeDispatcher())
    write_command(tmp_path, kind="goal", text="transmog")

    receipts = apply_to_host(host, drain_commands(tmp_path))

    assert agent.goal is Goal.GRIND
    assert receipts[0]["ok"] is False
    assert "goal" in receipts[0]["detail"]


def test_apply_non_allowlisted_kind_refused(tmp_path: Path) -> None:
    """The apply-layer guard (defense in depth behind drain's loud refusal)."""
    host = FakeHost({"fx0": FakeAgent("Fx_0")}, FakeDispatcher())

    receipts = apply_to_host(
        host, [{"id": "cmd-tel00000001", "kind": "teleport", "text": "prontera"}]
    )

    assert receipts[0]["id"] == "cmd-tel00000001"
    assert receipts[0]["ok"] is False
    assert "allowlisted" in receipts[0]["detail"]


# ------------------------------------------------------------------ poll_once


def test_poll_once_applies_once_then_reports_zero(tmp_path: Path) -> None:
    dispatcher = FakeDispatcher()
    host = FakeHost({"fx0": FakeAgent("Fx_0")}, dispatcher)
    write_command(tmp_path, char_name="Fx_0")

    assert poll_once(host, tmp_path) == 1
    assert poll_once(host, tmp_path) == 0
    assert len(dispatcher.submitted) == 1


def test_poll_once_mixed_batch_receipts_each_command(tmp_path: Path) -> None:
    dispatcher = FakeDispatcher()
    agents = {"fx0": FakeAgent("Fx_0"), "off": FakeAgent("Off_1", online=False)}
    host = FakeHost(agents, dispatcher)
    write_command(tmp_path, id="say000000001", char_name="Fx_0")
    write_command(tmp_path, id="goal00000001", char_name="Fx_0", kind="goal", text="social")
    write_command(tmp_path, id="gone00000001", char_name="Ghost", agent_id=999999)

    assert poll_once(host, tmp_path) == 3

    receipts = {
        json.loads(line)["id"]: json.loads(line)
        for line in (tmp_path / "receipts.jsonl").read_text(encoding="utf-8").splitlines()
    }
    assert receipts["cmd-say000000001"]["ok"] is True
    assert receipts["cmd-goal00000001"]["ok"] is True
    assert receipts["cmd-gone00000001"]["ok"] is False


# ------------------------------------------------- playing composition wiring


def test_run_host_polls_command_root_each_tick(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dispatcher = FakeDispatcher()
    host = FakeHost({"fx0": FakeAgent("Fx_0")}, dispatcher)
    write_command(tmp_path, char_name="Fx_0")
    monkeypatch.setattr("robots.playing.time.sleep", lambda _seconds: None)

    playing.run_host(host, 0.05, command_root=tmp_path)  # type: ignore[arg-type]

    assert len(dispatcher.submitted) == 1
    assert (tmp_path / "receipts.jsonl").exists()


def test_run_host_without_command_root_never_touches_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    host = FakeHost({}, FakeDispatcher())
    monkeypatch.setattr("robots.playing.time.sleep", lambda _seconds: None)

    playing.run_host(host, 0.05)  # type: ignore[arg-type]

    assert not (tmp_path / "commands.jsonl").exists()


def test_parse_args_command_root_defaults_off() -> None:
    argv = [
        "--manifest",
        "m.json",
        "--runtime-root",
        "rt",
        "--memory-root",
        "mem",
        "--decision-url",
        "http://127.0.0.1:8091",
    ]
    args = playing.parse_args(argv)

    assert args.command_root is None
    provided = playing.parse_args([*argv, "--command-root", "run/runtime/commands"])

    assert provided.command_root == Path("run/runtime/commands")
