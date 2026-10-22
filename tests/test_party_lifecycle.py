"""The party formation limb: create-then-invite.

rAthena's party_invite requires the INVITER to already lead a party
(party.cpp:383-386: ``p == nullptr -> return false`` with no client-visible
reply). A leader that invites without a party bounces silently — the leg 4-7
zero-party root cause after the 0x2c4 packet fix.
"""

from __future__ import annotations

from typing import Any

from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import InviteToParty


class _StubWire:
    def __init__(self) -> None:
        self.char_name = "NyxSong"
        self.frames: list[tuple[str, object]] = []
        self.party_created = False

    def party_create(self, name: str) -> None:
        self.frames.append(("create", name))

    def party_invite(self, player: str) -> None:
        self.frames.append(("invite", player))


def _runtime(wire: _StubWire) -> PlayingClient:
    runtime = PlayingClient.__new__(PlayingClient)  # the limb under test only
    runtime.wire = wire
    return runtime


def _invite(player: str) -> InviteToParty:
    return InviteToParty(player=player)


def test_first_invite_creates_the_party_then_invites() -> None:
    wire = _StubWire()
    runtime = _runtime(wire)
    state: Any = None
    runtime._social(state, _invite("RinceNyan"))
    kinds = [k for k, _ in wire.frames]
    assert kinds == ["create", "invite"], wire.frames
    name = wire.frames[0][1]
    assert isinstance(name, str), name
    assert name.startswith("NyxSong"), name
    # alphanumerics only: the pinned char_name_option: 1 forbids the hyphen
    assert "-" not in name, name


def test_subsequent_invites_do_not_recreate() -> None:
    wire = _StubWire()
    runtime = _runtime(wire)
    state: Any = None
    runtime._social(state, _invite("RinceNyan"))
    runtime._social(state, _invite("zeny_wing"))
    kinds = [k for k, _ in wire.frames]
    assert kinds == ["create", "invite", "invite"], wire.frames
