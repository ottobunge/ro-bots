"""Actions a bot can take. The brain emits these; a GameClient executes them."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MoveTo:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class Attack:
    target_id: int


@dataclass(frozen=True, slots=True)
class Loot:
    pass


@dataclass(frozen=True, slots=True)
class Say:
    text: str


@dataclass(frozen=True, slots=True)
class PartyChat:
    text: str


@dataclass(frozen=True, slots=True)
class WhisperTo:
    to: str
    text: str


@dataclass(frozen=True, slots=True)
class InviteToParty:
    player: str


@dataclass(frozen=True, slots=True)
class AcceptInvite:
    pass


@dataclass(frozen=True, slots=True)
class UseWarp:
    map_name: str


@dataclass(frozen=True, slots=True)
class Rest:
    """Sit and regen — the classic RO 'novice sits when hurt' behavior."""


GameAction = (
    MoveTo
    | Attack
    | Loot
    | Say
    | PartyChat
    | WhisperTo
    | InviteToParty
    | AcceptInvite
    | UseWarp
    | Rest
)
