"""The guild formation flow: the founder's packets + the runtime once-guards.

The wire layer was live-verified on the e2e world (the charter -> 0x0165 ->
the guild row; 0x0168 -> the member's 0x16a prompt -> 0x16b -> guild_id).
This pins the production policy: a formed party objective makes the leader
found the guild (alphanumeric name per char_name_option: 1) and invite the
online group members once each; the invitee accepts by the same group policy
as the party accept.
"""

from __future__ import annotations

from typing import Any

from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import FoundGuild, GuildInvite
from robots.society.objectives import BoundCoordinator, GroupCoordinator
from robots.society.relations import RelationshipLedger


def _bound(ledger: RelationshipLedger, persona: str, online: tuple[str, ...]) -> BoundCoordinator:
    return BoundCoordinator(
        GroupCoordinator(ledger, persona),
        online=lambda: online,
        meet_where="prontera",
        meet_when="20:00",
    )


def test_guild_formation_actions_found_and_invite_online_members() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("pop_lead", "NyxSong")
    ledger.register_persona("pop_mate", "RinceNyan")
    ledger.seed_group("g00", ("pop_lead", "pop_mate"))
    coord = _bound(ledger, "pop_lead", ("pop_lead", "pop_mate"))
    coord._coordinator.book.propose(
        "g00-hunt-1", "g00", "pop_lead", "hunt", "prontera", invited=("pop_mate",)
    )
    actions = coord.guild_formation_actions(("pop_lead", "pop_mate"))
    kinds = [type(a).__name__ for a in actions]
    assert kinds[0] == "FoundGuild", kinds
    found = actions[0]
    assert isinstance(found, FoundGuild)
    assert found.name == "NyxSongGuard"
    assert "GuildInvite" in kinds
    invites = [a for a in actions if isinstance(a, GuildInvite)]
    assert [i.player for i in invites] == ["RinceNyan"]


def test_guild_formation_actions_empty_without_an_objective() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("pop_lead", "NyxSong")
    coord = _bound(ledger, "pop_lead", ("pop_lead",))
    assert coord.guild_formation_actions(("pop_lead",)) == ()


def test_found_guild_limb_creates_once() -> None:
    class _Wire:
        def __init__(self) -> None:
            self.frames: list[tuple[str, object]] = []
            self.party_created = False
            self.guild_created = False

        def guild_create(self, name: str) -> None:
            self.frames.append(("create", name))

    wire = _Wire()
    runtime = PlayingClient.__new__(PlayingClient)
    runtime.wire = wire
    state: Any = None
    runtime._social(state, FoundGuild(name="NyxSongGuard"))
    runtime._social(state, FoundGuild(name="NyxSongGuard"))
    assert [k for k, _ in wire.frames] == ["create"]


def test_guild_invite_limb_resolves_the_aid_and_invites_once() -> None:
    class _Wire:
        def __init__(self) -> None:
            self.frames: list[tuple[int, int, int]] = []
            self.party_members = {"RinceNyan": 2000101}
            self.aid = 2000100
            self.gid = 150100

        def guild_invite(self, target: int, inviter_aid: int, inviter_gid: int) -> None:
            self.frames.append((target, inviter_aid, inviter_gid))

    wire = _Wire()
    runtime = PlayingClient.__new__(PlayingClient)
    runtime.wire = wire
    state: Any = None
    runtime._social(state, GuildInvite(player="RinceNyan"))
    runtime._social(state, GuildInvite(player="RinceNyan"))
    assert wire.frames == [(2000101, 2000100, 150100)]
