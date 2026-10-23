"""Actions a bot can take. The brain emits these; a GameClient executes them."""

from dataclasses import dataclass

from robots.domain.planning import NpcIntent, PlanningIdentity


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
class FoundGuild:
    """Create the speaker's guild (the founder holds the Emperium charter)."""

    name: str


@dataclass(frozen=True, slots=True)
class GuildInvite:
    """Invite a player (by character name) to the speaker's guild."""

    player: str


@dataclass(frozen=True, slots=True)
class AcceptGuildInvite:
    """Accept the pending guild invitation."""


@dataclass(frozen=True, slots=True)
class UseWarp:
    map_name: str


@dataclass(frozen=True, slots=True)
class Rest:
    """Sit and regen — the classic RO 'novice sits when hurt' behavior."""


@dataclass(frozen=True, slots=True)
class TalkToNpc:
    npc_id: int


@dataclass(frozen=True, slots=True)
class NpcNext:
    npc_id: int


@dataclass(frozen=True, slots=True)
class NpcSelect:
    npc_id: int
    received_index: int


@dataclass(frozen=True, slots=True)
class NpcClose:
    npc_id: int


@dataclass(frozen=True, slots=True)
class NpcSubmitName:
    """Explicit intent to submit the selected character's name to this prompt."""

    npc_id: int
    epoch: int
    prompt_sequence: int


@dataclass(frozen=True, slots=True)
class NpcShopBuySelection:
    """Zero-spend BUY-list selection; unadvertised, current received UI only."""

    npc_id: int
    epoch: int
    prompt_sequence: int
    map_name: str
    opened_sequence: int


@dataclass(frozen=True, slots=True)
class NpcShopPurchase:
    """Unadvertised quantity-one intent; DTO equality is not owner authority."""

    npc_id: int
    epoch: int
    prompt_sequence: int
    map_name: str
    opened_sequence: int
    offer_sequence: int
    maximum_zeny: int
    item_id: int = 1201
    quantity: int = 1


@dataclass(frozen=True, slots=True)
class NpcShopSellOpen:
    """Unadvertised sell-list request bound to the received dealtype dialog.

    Field order mirrors NpcShopBuySelection: the received C4 marker names the
    actor (npc.cpp:2409 sets npc_shopid; clif.cpp:12259-12271 routes type 1
    to the sell list). DTO equality is not owner authority.
    """

    npc_id: int
    epoch: int
    prompt_sequence: int
    map_name: str
    opened_sequence: int


@dataclass(frozen=True, slots=True)
class NpcShopSell:
    """Sell request bound to one received C7 sell-list receipt in this epoch.

    A received ZC_PC_SELL_ITEMLIST carries no actor identity (clif.cpp:2265,
    packets.hpp:742-753), so ``npc_id`` stays None unless a dialog names one;
    ``sell_sequence`` is the received receipt the sale echoes. DTO equality is
    not owner authority.
    """

    npc_id: int | None
    epoch: int
    map_name: str
    sell_sequence: int
    sales: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class NpcRespond:
    """Explicit response bound to one caller identity and received NPC prompt."""

    identity: PlanningIdentity
    intent: NpcIntent


GameAction = (
    NpcRespond
    | NpcNext
    | NpcSelect
    | NpcClose
    | NpcSubmitName
    | NpcShopBuySelection
    | NpcShopPurchase
    | NpcShopSellOpen
    | NpcShopSell
    | TalkToNpc
    | MoveTo
    | Attack
    | Loot
    | Say
    | PartyChat
    | WhisperTo
    | InviteToParty
    | FoundGuild
    | GuildInvite
    | AcceptGuildInvite
    | AcceptInvite
    | UseWarp
    | Rest
)
