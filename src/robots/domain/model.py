"""Core domain types: the state of a bot and the world it perceives.

These are the facts the decision model reasons over. Everything is immutable;
a new perception tick produces a new ``BotState``.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class Goal(StrEnum):
    """High-level drives a bot can pursue. The persona weights these."""

    GRIND = "grind"
    FARM_ITEM = "farm_item"
    IDLE_TOWN = "idle_town"
    QUEST = "quest"
    SOCIAL = "social"


ActorKind = Literal["player", "monster", "npc"]
ChatChannel = Literal["public", "party", "guild", "whisper"]


@dataclass(frozen=True, slots=True)
class ActorRef:
    """Something visible near the bot."""

    id: int
    name: str
    kind: ActorKind
    distance: float


@dataclass(frozen=True, slots=True)
class ChatLine:
    """One chat message the bot heard."""

    channel: ChatChannel
    sender: str
    text: str
    at: float


@dataclass(frozen=True, slots=True)
class PartyInvite:
    """A pending party invitation."""

    from_name: str
    at: float


@dataclass(frozen=True, slots=True)
class BotState:
    """Complete perception snapshot feeding one decision tick."""

    name: str
    job: str
    base_level: int
    hp: int
    max_hp: int
    sp: int
    max_sp: int
    map_name: str
    x: int
    y: int
    goal: Goal
    in_party: bool
    nearby: tuple[ActorRef, ...]
    inventory: dict[str, int]
    pending_invites: tuple[PartyInvite, ...]
    recent_chat: tuple[ChatLine, ...]

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp if self.max_hp > 0 else 0.0

    @property
    def nearby_players(self) -> tuple[ActorRef, ...]:
        return tuple(a for a in self.nearby if a.kind == "player")

    @property
    def nearby_monsters(self) -> tuple[ActorRef, ...]:
        return tuple(a for a in self.nearby if a.kind == "monster")
