"""Core domain types: the state of a bot and the world it perceives.

These are the facts the decision model reasons over. Everything is immutable;
a new perception tick produces a new ``BotState``.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from robots.domain.capacity import ReceivedCapacity
from robots.domain.npc import NpcDialogue
from robots.domain.self_metadata import ServerSelfSlots
from robots.domain.shop import ReceivedShopOffer, ReceivedZeny
from robots.domain.skill_knowledge import PublicSkillKnowledge
from robots.domain.skills import ReceivedSkillContextReadOnly


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
class PartyObservation:
    """One party-relevant wire observation, actors named by AID.

    The human-contribution ear's row type (drained once per tick from the
    native view): ``damage`` rows carry amount dealt source->target, ``skill``
    rows a heal/buff cast (``failed`` marks the server-rejected ones), ``exp``
    rows a positive shared-exp delta the bot received while partied.
    """

    kind: Literal["damage", "skill", "exp"]
    source_id: int
    target_id: int
    amount: int
    skill_id: int = 0
    failed: bool = False


@dataclass(frozen=True, slots=True)
class ActorRef:
    """Something visible near the bot.

    ``x``/``y`` carry the last observed cell when the tracker has one, so
    range-aware goal scripts can approach the target (window-14 frontier);
    ``None`` keeps the fail-closed range-blind behavior.
    """

    id: int
    name: str
    kind: ActorKind
    distance: float
    x: int | None = None
    y: int | None = None


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
    pending_guild_invite: str | None = None
    inventory_known: bool = True
    alive_known: bool = True
    alive: bool | None = True
    native_epoch: int | None = None
    progression_source: str = "legacy"
    recent_encounters: tuple[dict[str, int | str | None], ...] = ()
    npc_dialogue: NpcDialogue | None = None
    npc_instructions_received: bool = False
    received_skills: ReceivedSkillContextReadOnly | None = None
    public_skill_knowledge: PublicSkillKnowledge | None = None
    shop_offer: ReceivedShopOffer | None = None
    zeny: int | None = None
    zeny_receipt: ReceivedZeny | None = None
    weight: int | None = None
    max_weight: int | None = None
    capacity_receipt: ReceivedCapacity | None = None
    inventory_slots: int | None = None
    server_self_slots: ServerSelfSlots | None = None
    received_stats: tuple[int, ...] | None = None  # 0x00BD: str agi vit int dex luk

    @property
    def hp_ratio(self) -> float:
        return self.hp / self.max_hp if self.max_hp > 0 else 0.0

    @property
    def nearby_players(self) -> tuple[ActorRef, ...]:
        return tuple(a for a in self.nearby if a.kind == "player")

    @property
    def nearby_monsters(self) -> tuple[ActorRef, ...]:
        return tuple(a for a in self.nearby if a.kind == "monster")
