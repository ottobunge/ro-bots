"""Multi-character switching (feature/character-switching).

The model slice (the persona owns 1-N characters, the play-style limits
class choice), the flow slice (the CharSwitch itch crosses its threshold or
the schedule window ends -> clean logout via the schedule-close path ->
the next window-open logs in as the NEXT roster character; the CharSwitch
itch is consumed by the switch), and the wire slice (the login flow takes a
target character id from the manifest roster).

The memory/goals/relationships belong to the PERSONA and persist across the
switch; the runtime game-state (the client's world model: position, actors,
chat) belongs to the CHARACTER and is rebuilt — the tests assert the split.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, cast

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.app.agent_runtime import AgentHost, ManifestEntry, load_manifest
from robots.domain.model import Goal
from robots.popgen import CLASS_FAMILIES
from robots.society.models import (
    Attitude,
    CharacterIdentity,
    Playstyle,
    SocietyPersona,
    playstyle_class_families,
)
from robots.society.society import SocietyRoster
from robots.society.wants import CHAR_SWITCH_ROLL_THRESHOLD, Want

PRIMARY = "Prim"
ALT = "Secundus"
ALT_CHAR_ID = 424242


# ------------------------------------------------------------- the model


def test_persona_owns_its_character_roster() -> None:
    persona = SocietyPersona(
        "p1",
        PRIMARY,
        Playstyle.MAGE,
        Attitude.SOLO,
        0.5,
        (1, 99),
        characters=(
            CharacterIdentity(PRIMARY, 0, "mage-grinder", 300001),
            CharacterIdentity(ALT, 1, "mage-aoe-control", 400000),
        ),
    )
    assert [c.name for c in persona.characters] == [PRIMARY, ALT]
    assert persona.characters[0].primary
    assert not persona.characters[1].primary
    assert persona.characters[1].build == "mage-aoe-control"


def test_default_persona_keeps_the_single_character_constructor() -> None:
    persona = SocietyPersona("p1", PRIMARY, Playstyle.MAGE, Attitude.SOLO, 0.5, (1, 99))
    assert persona.characters == ()


def test_playstyle_limits_class_choice() -> None:
    assert playstyle_class_families(Playstyle.TANK) == ("swordman",)
    assert playstyle_class_families(Playstyle.MAGE) == ("mage",)
    assert playstyle_class_families(Playstyle.HUNTER) == ("archer",)
    assert playstyle_class_families(Playstyle.HEALER) == ("acolyte",)
    assert playstyle_class_families(Playstyle.SUPPORT) == ("acolyte",)
    assert set(playstyle_class_families(Playstyle.MELEE)) == {"swordman", "thief"}
    for playstyle in Playstyle:
        families = playstyle_class_families(playstyle)
        assert families, "every playstyle constrains class choice to something"
        assert set(families) <= set(CLASS_FAMILIES)


# ------------------------------------------------------- the manifest roster


def multi_char_manifest(tmp_path: Path) -> str:
    data = {
        "accounts": [
            {
                "persona_id": "p1",
                "account": "e2e_p1",
                "password": "pw",
                "char_name": PRIMARY,
                "pincode": "0000",
                "char_id": 300001,
                "characters": [
                    {"name": PRIMARY, "char_id": 300001, "slot": 0, "build": "swordman-tank"},
                    {"name": ALT, "char_id": ALT_CHAR_ID, "slot": 1, "build": "swordman-grinder"},
                ],
            }
        ]
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    return str(path)


def test_load_manifest_parses_the_target_character_roster(tmp_path: Path) -> None:
    entries = load_manifest(multi_char_manifest(tmp_path))
    entry = entries["p1"]
    assert entry.char_id == 300001
    assert [c.char_name for c in entry.roster] == [PRIMARY, ALT]
    assert [c.char_id for c in entry.roster] == [300001, ALT_CHAR_ID]
    assert all(c.account == entry.account for c in entry.roster)
    assert all(c.password == entry.password for c in entry.roster)
    assert all(c.login_host == entry.login_host for c in entry.roster)


def test_load_manifest_legacy_rows_keep_single_character_behavior(
    tmp_path: Path,
) -> None:
    data = {
        "accounts": [
            {"persona_id": "p1", "account": "e2e_p1", "password": "pw", "char_name": PRIMARY}
        ]
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    entry = load_manifest(path)["p1"]
    assert entry.roster == ()
    assert entry.char_id == 0
    assert entry.char_name == PRIMARY


def test_load_manifest_rejects_a_malformed_character_id(tmp_path: Path) -> None:
    data = {
        "accounts": [
            {
                "persona_id": "p1",
                "account": "e2e_p1",
                "password": "pw",
                "char_name": PRIMARY,
                "char_id": "three hundred thousand",
            }
        ]
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="char_id"):
        load_manifest(path)


# ----------------------------------------------------------------- the flow


class FakeSocietyClock:
    """SocietyClock pinned to a (weekday, hour) the test moves by hand."""

    def __init__(self, now: tuple[int, float]) -> None:
        self.now = now

    def local_now(self) -> tuple[int, float]:
        return self.now


class RecordingWire:
    """Stub wire client: records the entry the login flow selected."""

    def __init__(self, entry: ManifestEntry) -> None:
        self.entry = entry
        self.char_name = entry.char_name
        self.connected = False
        self.closes = 0
        # the character-owned runtime state (rebuilt per login)
        self.actors: dict[int, dict[str, Any]] = {}
        self.chat: list[tuple[int, str]] = []
        self.x = 0
        self.y = 0

    def connect(self) -> RecordingWire:
        self.connected = True
        return self

    def close(self) -> None:
        self.connected = False
        self.closes += 1


class WireFactory:
    """client_factory double: every login builds a fresh wire for the entry."""

    def __init__(self) -> None:
        self.wires: list[RecordingWire] = []

    def __call__(self, entry: ManifestEntry) -> RecordingWire:
        wire = RecordingWire(entry)
        self.wires.append(wire)
        return wire


def wait_until(predicate: Any, timeout_s: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def build_host(
    tmp_path: Path,
    *,
    characters: list[dict[str, Any]] | None = None,
) -> tuple[AgentHost, Any, WireFactory, FakeSocietyClock, str]:
    """A one-agent host on a fake clock inside its schedule window."""
    roster = SocietyRoster.build(random.Random(42), n_groups=1)
    persona_id = sorted(roster.personas)[0]
    group = next(g for g in roster.groups if persona_id in g.member_ids)
    window = next(w for w in group.schedule.windows if w[1] < w[2])
    clock = FakeSocietyClock((window[0], window[1] + 0.1))

    row: dict[str, Any] = {
        "persona_id": persona_id,
        "account": f"e2e_{persona_id}",
        "password": "pw",
        "char_name": PRIMARY,
    }
    if characters is not None:
        row["characters"] = characters
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"accounts": [row]}))

    factory = WireFactory()
    host = AgentHost(
        roster,
        str(manifest),
        clock=clock,
        client_factory=factory,
        brain_factory=cast(Any, lambda *_args: None),
        chat_generator=StaticChatGenerator(),
        run_worldfeed=False,
        memory_root=tmp_path / "memory",
        tick_seconds=0.01,
    )
    return host, host.agents[persona_id], factory, clock, persona_id


def test_itch_crosses_threshold_logout_relogin_as_the_next_character(
    tmp_path: Path,
) -> None:
    host, agent, factory, _clock, _persona_id = build_host(
        tmp_path,
        characters=[
            {"name": PRIMARY, "char_id": 300001, "slot": 0, "build": "swordman-tank"},
            {"name": ALT, "char_id": ALT_CHAR_ID, "slot": 1, "build": "swordman-grinder"},
        ],
    )
    try:
        host.step()
        assert agent.online
        assert factory.wires[0].entry.char_name == PRIMARY
        factory.wires[0].actors[7] = {"name": "LivedHere"}  # the character's state
        factory.wires[0].x = 199

        memory = agent.memory
        goal_before = agent.goal
        agent.wants.scores[Want.CHAR_SWITCH] = CHAR_SWITCH_ROLL_THRESHOLD + 5.0
        assert wait_until(lambda: agent.pending_switch), "the hot itch arms a switch"

        host.step()  # the itch logout + the same-pass relogin
        assert factory.wires[0].connected is False, "the switch logs the character out"
        assert len(factory.wires) == 2
        second = factory.wires[1]
        assert second.entry.char_name == ALT, "the relogin returns as the NEXT character"
        assert second.entry.char_id == ALT_CHAR_ID, "the login flow carries the target id"
        assert agent.online
        assert agent.entry.char_name == ALT

        # the CharSwitch itch consumed by the switch (the pinned +60 satisfaction)
        assert agent.wants.scores[Want.CHAR_SWITCH] == 100.0

        # persona-level continuity: same memory object, the clean session note kept
        assert agent.memory is memory
        notes = [note.text for note in memory.log.notes()]
        assert any(t.startswith("session ended") and t.endswith(f"as {PRIMARY}") for t in notes)
        assert agent.goal == goal_before

        # character-level split: the new wire holds none of the old game-state
        assert second.actors == {}
        assert (second.x, second.y) == (0, 0)

        # the consumed itch stays consumed while its score is still hot
        assert not wait_until(lambda: agent.pending_switch, timeout_s=0.3)
    finally:
        host.stop()


def test_window_end_rotates_the_roster_at_the_next_window_open(tmp_path: Path) -> None:
    host, agent, factory, clock, persona_id = build_host(
        tmp_path,
        characters=[
            {"name": PRIMARY, "char_id": 300001, "slot": 0, "build": "swordman-tank"},
            {"name": ALT, "char_id": ALT_CHAR_ID, "slot": 1, "build": "swordman-grinder"},
        ],
    )
    try:
        host.step()
        assert agent.entry.char_name == PRIMARY

        group = next(g for g in host.roster.groups if persona_id in g.member_ids)
        window = next(w for w in group.schedule.windows if w[1] < w[2])
        clock.now = (window[0], (window[2] + 0.1) % 24.0)
        host.step()  # the schedule-close path (a clean logout)
        assert not agent.online
        assert factory.wires[0].connected is False

        clock.now = (window[0], window[1] + 0.2)
        host.step()  # the next window-open resumes as the NEXT character
        assert agent.online
        assert factory.wires[1].entry.char_name == ALT
        assert agent.entry.char_name == ALT

        # and the roster wraps: the window after that is the primary again
        clock.now = (window[0], (window[2] + 0.2) % 24.0)
        host.step()
        clock.now = (window[0], window[1] + 0.3)
        host.step()
        assert factory.wires[2].entry.char_name == PRIMARY
    finally:
        host.stop()


def test_single_character_persona_never_switches(tmp_path: Path) -> None:
    host, agent, factory, clock, _persona_id = build_host(tmp_path)
    try:
        host.step()
        assert agent.online
        assert len(factory.wires) == 1
        agent.wants.scores[Want.CHAR_SWITCH] = 100.0
        assert not wait_until(
            lambda: agent.pending_switch, timeout_s=0.3
        ), "one character: the itch has nothing to switch to"
        # a window close + reopen resumes the SAME character
        group = next(g for g in host.roster.groups)
        window = next(w for w in group.schedule.windows if w[1] < w[2])
        clock.now = (window[0], (window[2] + 0.1) % 24.0)
        host.step()
        clock.now = (window[0], window[1] + 0.2)
        host.step()
        assert agent.online
        assert len(factory.wires) == 1, "the closed wire is reused without a roster"
        assert factory.wires[0].entry.char_name == PRIMARY
    finally:
        host.stop()


def test_goal_enum_unaffected_by_switch_imports() -> None:
    # a sentinel against accidental Goal default drift in the flow fixtures
    assert Goal.GRIND.value == "grind"
