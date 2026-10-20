"""Actual host construction; synthetic offline effect boundaries only."""

import json
import zlib
from pathlib import Path

import pytest

from robots import playing
from robots.adapters.native_navigation import ENTRY, HEADER
from robots.app import agent_runtime
from robots.app.brain import EventDrivenBrain
from robots.app.planning_brain import PlannedBrain
from robots.domain.model import BotState, Goal


def host_arguments(root: Path) -> list[str]:
    (root / "db/pre-re").mkdir(parents=True)
    body = zlib.compress(bytes(4))
    data = ENTRY.pack(b"prontera", 2, 2, len(body)) + body
    for relative in ("db/map_cache.dat", "db/pre-re/map_cache.dat"):
        (root / relative).write_bytes(HEADER.pack(HEADER.size + len(data), 1) + data)
    (root / "db/pre-re/mob_db.yml").write_text("Body: []\n")
    manifest = root / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "accounts": [
                    {
                        "persona_id": "one",
                        "account": "dummy",
                        "password": "dummy",
                        "char_name": "WireNovice",
                    }
                ]
            }
        )
    )
    return [
        "--manifest",
        str(manifest),
        "--runtime-root",
        str(root),
        "--memory-root",
        str(root / "memory"),
        "--decision-url",
        "http://127.0.0.1:8091/v1/systemone",
    ]


def test_opt_in_builds_real_host_without_effects_and_default_stays_legacy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def forbid(*args: object, **kwargs: object) -> None:
        calls.append("effect")
        message = "construction effect"
        raise AssertionError(message)

    monkeypatch.setattr("httpx.Client.send", forbid)
    monkeypatch.setattr("threading.Thread.start", forbid)
    monkeypatch.setattr("socket.socket.connect", forbid)
    monkeypatch.setattr(playing, "LocalPlanningModel", forbid)
    monkeypatch.setattr(agent_runtime, "_BotClient", forbid)
    argv = host_arguments(tmp_path)
    legacy = playing.build_host(playing.parse_args(argv))
    planned = None
    try:
        assert isinstance(legacy.agents["one"].brain, EventDrivenBrain)
        args = playing.parse_args(
            [
                *argv,
                "--llm-planning",
                "--planning-world",
                "offline-test",
                "--memory-root",
                str(tmp_path / "planned-memory"),
            ]
        )
        planned = playing.build_host(args)
        brain = planned.agents["one"].brain
        assert isinstance(brain, PlannedBrain)
        assert brain.mechanical_fallback_allowed is False
        assert not calls
    finally:
        legacy.stop()
        if planned is not None:
            planned.stop()


def test_unreceived_opt_in_context_refused_without_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    calls: list[str] = []

    def forbid(*args: object, **kwargs: object) -> None:
        calls.append("effect")
        message = "opt-in scaffold effect"
        raise AssertionError(message)

    monkeypatch.setattr("httpx.Client.send", forbid)
    monkeypatch.setattr("threading.Thread.start", forbid)
    monkeypatch.setattr("socket.socket.connect", forbid)
    monkeypatch.setattr(playing, "LocalPlanningModel", forbid)
    monkeypatch.setattr(agent_runtime, "_BotClient", forbid)
    args = playing.parse_args(
        [
            *host_arguments(tmp_path),
            "--llm-planning",
            "--planning-world",
            "offline-test",
        ]
    )
    host = playing.build_host(args)
    try:
        brain = host.agents["one"].brain
        assert isinstance(brain, PlannedBrain)
        state = BotState(
            name="WireNovice",
            job="Novice",
            base_level=1,
            hp=10,
            max_hp=10,
            sp=1,
            max_sp=1,
            map_name="prontera",
            x=0,
            y=0,
            goal=Goal.GRIND,
            in_party=False,
            nearby=(),
            inventory={},
            pending_invites=(),
            recent_chat=(),
        )
        with pytest.raises(RuntimeError, match=r"^planning context unavailable$"):
            brain.start(state)
        assert not calls
    finally:
        host.stop()
