"""Behavior scripts: mechanical execution of a goal between events.

A script is the "autopilot" — it walks, attacks, loots, idles — and it stays
in charge until the world produces an event (see robots.domain.events) or it
completes/fails. No decision-model calls happen inside a script.
"""

import logging
import random
from collections.abc import Sequence
from enum import Enum, auto
from typing import TYPE_CHECKING, Protocol, assert_never, final

from robots.domain.actions import Attack, GameAction, MoveTo, Rest, TalkToNpc
from robots.domain.farm import FarmPlan
from robots.domain.model import ActorRef, Goal

if TYPE_CHECKING:
    from robots.domain.model import BotState


logger = logging.getLogger(__name__)


class ScriptStatus(Enum):
    ACTIVE = auto()
    DONE = auto()
    FAILED = auto()


class TravelResolver(Protocol):
    """The route out of the map the agent is standing on, resolved live.

    ``(map_name, x, y) -> the ordered [(map, x, y)] warp legs | None``. The
    resolver exists because the way out of a map can depend on WHERE in it
    the agent stands: ``prt_in`` is 26 disconnected building interiors,
    each with its own door, and only one of them is reachable from the
    agent's own interior (leg 37).
    """

    def __call__(
        self, map_name: str, x: int, y: int
    ) -> tuple[tuple[str, int, int], ...] | None: ...


class MerchantReachable(Protocol):
    """Whether a pinned leg's cell is walkable from the agent's own region.

    ``(map_name, position, cell) -> True | False | None`` — None when the
    grid carries no authority for the map (the caller keeps its pinned leg;
    the client grid is a lossy picture of the server's, so only an explicit
    False vetoes a leg).
    """

    def __call__(
        self, map_name: str, position: tuple[int, int], cell: tuple[int, int]
    ) -> bool | None: ...


class BehaviorScript(Protocol):
    """Anything that can run as a bot's autopilot between events."""

    def step(self, state: BotState) -> ScriptOutcome: ...


@final
class ScriptOutcome:
    """What one script step produced."""

    __slots__ = ("actions", "status")

    def __init__(self, actions: tuple[GameAction, ...], status: ScriptStatus) -> None:
        self.actions = actions
        self.status = status


MELEE_RANGE = 1
# The recovery latch may break when hurt-but-able with the fight in melee
# range (window 35: rest dominance vs engagement).
REST_BREAK_HP_FLOOR = 0.25
# The novice bootstrap stat plan (criterion 9): the sidecar allocation
# (run/knowledge/builds/pre-re/novice-bootstrap.json, str 9 / dex 9) keyed by
# the wire stat ids. Spent one point per CZ_STATUS_CHANGE until the targets
# hold; generalization to class builds arrives with the build-plan wiring.
NOVICE_STAT_TARGETS = {13: 9, 17: 9}
"""Verified melee range at the pinned rAthena e985006171d2 (flake.nix:10-16,
MAIN/pre-re 20180704): the unarmed right-hand range floors at 1
(src/map/status.cpp:4216), player attacks range-check with the circular
client metric (src/map/battle.cpp:8215-8224, path.hpp:48) and are accepted
outright below distance 2 (battle.cpp:8226-8228). There is no attack_range
battle config at this pin, and 2 straight tiles (client-metric 2) still draw
ZC_ATTACK_FAILURE_FOR_DISTANCE 0x0139 — so 1 on the server's own metric is
the only known-accepted boundary."""


TARGET_WIDEN_STEPS = 20
"""Consecutive plan-target-absent evaluations after which FarmScript's own
target filter widens to the observed attackable species (window-14 gap 1:
fixture_0 saw only Lunatics for 1780 script steps while its plan target was
absent and never attacked). The plan object is never rewritten; the widening
is bounded and counted, prefers the plan species the moment it is present
again, and resets the streak whenever a plan target is observed."""


KILL_COMMIT_WINDOW = 30

# Pinned mob HP (rathena e985006171d2 db/pre-re/mob_db.yml): a Novice deals
# ~1 damage per hit, so kills only close on the lowest-HP species. The
# unheld commitment pick prefers these values before distance; unknown
# species sort after all known ones (fail-closed: closest-pick among them).
_PINNED_MOB_HP: dict[str, int] = {
    "Poring": 50,  # 1002, mob_db.yml Hp: 50
    "Lunatic": 60,  # 1063
    "Drops": 60,  # 1013
    "Pupa": 427,  # 1008
}
_UNKNOWN_MOB_HP = 10**9
"""Consecutive script evaluations a grasp goal script keeps attacking its
most recently attacked, still-visible target id before closest-picking
resumes. Window 22 proved the attributed kill chain live but closed without
a kill: each Novice hit lands ~1 damage (fixture_0: 19 attacks -> 18
bot-dealt damage) while every evaluation re-picked the closest mob, so no
single Poring ever accumulated the pinned server's lethal pool (pinned
rathena db/pre-re/mob_db.yml:134-140, `Id: 1002 ... Hp: 50`; the official-iRO
figure 60 does not describe this server). The commitment is armed by every
landed attack, counts only approach evaluations against the window, and
releases when the id leaves the received state (death/vanish), on rest and
on loot. Because the brain re-installs the goal script on every heartbeat
review (brain.py:305, brain.py:460), the commitment lives in a per-bot-name
registry — not on the script instance — so it survives re-creation.
FarmScript holds only ids that pass its CURRENT effective plan filter
(strict targeting and the bounded widening are unchanged)."""


class _KillCommitment:
    """Bounded per-bot keep-attacking commitment (see KILL_COMMIT_WINDOW)."""

    __slots__ = ("_since_attack", "_target_id", "_window")

    def __init__(self, window: int) -> None:
        self._window = window
        self._target_id: int | None = None
        self._since_attack = 0

    def hold(self, candidates: Sequence[ActorRef]) -> ActorRef | None:
        """The committed actor among the given candidates, else None.

        ``None`` means closest-picking resumes: the window of evaluations
        without a landed attack is exhausted, or the committed id has left
        the received state (death/vanish) and the commitment is released.
        """
        if self._target_id is None or self._since_attack >= self._window:
            return None
        for actor in candidates:
            if actor.id == self._target_id:
                self._since_attack += 1  # an evaluation without a landed attack
                return actor
        self.release()
        return None

    def commit(self, target_id: int) -> None:
        """A landed attack on this id: adopt it and rearm the window."""
        self._target_id = target_id
        self._since_attack = 0

    def release(self) -> None:
        """Forget the commitment entirely (rest, loot, or target gone)."""
        self._target_id = None
        self._since_attack = 0


_KILL_COMMITMENTS: dict[str, _KillCommitment] = {}

_DEALER_TALKED: dict[str, int] = {}
"""Per-bot npc id of the last dealer TalkToNpc (one talk per contact; the
entry is replaced when a different dealer npc becomes the candidate)."""

_DEALER_RANGE_TAPPED: dict[str, str] = {}
"""Per-bot detail of the last ``dealer_talk_out_of_range`` tap (leg-71
frontier b): the memo is keyed on the FULL detail (agent cell, dealer cell,
distance) so a steady out-of-range park logs one bounded line while a real
change of position re-names itself — unlike the shared verdict-term memo,
whose per-term dedupe would flip-flop fire every drive tick here."""


def reset_merchant_talk() -> None:
    """Forget per-bot dealer contacts (new session epoch / test isolation)."""
    _DEALER_TALKED.clear()
    _DEALER_RANGE_TAPPED.clear()


"""Per-bot-name commitment registry; one entry per agent in the process."""


def _kill_commitment(bot: str, window: int) -> _KillCommitment:
    commitment = _KILL_COMMITMENTS.get(bot)
    if commitment is None:
        commitment = _KillCommitment(window)
        _KILL_COMMITMENTS[bot] = commitment
    return commitment


def _release_commitment(state: BotState, window: int) -> None:
    _kill_commitment(state.name, window).release()


NOVICE_WANTED_WEAPONS = (1201, 1202, 1204)
"""Pinned pre-re daggers the Novice build wears on first pickup. 1201 Knife
(Atk 17, Slots 3) and 1204 Cutter (Atk 30) at rathena db/pre-re/
item_db_equip.yml:2262/2366, and 1202 (AegisName ``Knife_``, Atk 17,
item_db_equip.yml:2297-2298) — 1202 is the actual field drop: the pinned
Poring row (mob_db.yml ``Id: 1002``, ``Drops: - Item: Knife_  Rate: 100``)
names the AegisName ``Knife_``, not ``Knife``. All three list
``Novice: true`` under Jobs, ``Right_Hand: true`` under Locations and
``EquipLevelMin: 1``. The window-26 Novice deals ~1 damage unarmed; any of
these multiplies per-hit damage an order of magnitude."""


def novice_weapon_index(
    indexed_inventory: tuple[tuple[int, int, int], ...] | None,
    worn: tuple[tuple[int, int], ...],
    *,
    job: str,
) -> int | None:
    """Inventory index of the first unworn wanted weapon, else None.

    ``indexed_inventory`` is the tracker's detached current stock
    ((client-side inventory index, item id, count)); ``worn`` is
    ``NativeGameplayView.worn`` ((index, wear location) from received
    successful equip acks). Unknown stock (None) and non-Novice jobs never
    return an index; an index already known worn is never re-emitted.
    """
    if job != "Novice" or indexed_inventory is None:
        return None
    worn_indices = {index for index, _location in worn}
    for index, item, _count in sorted(indexed_inventory):
        if item in NOVICE_WANTED_WEAPONS and index not in worn_indices:
            return index
    return None


SELLABLE_ITEM_IDS = (
    509,
    510,
    511,
    512,
    514,
    529,
    531,
    603,
    604,
    610,
    619,
    620,
    694,
    695,
    700,
    705,
    713,
    714,
    720,
    722,
    909,
    910,
    912,
    914,
    915,
    917,
    938,
    949,
    983,
    1002,
    1039,
    1059,
    1207,
    1602,
    2116,
    2254,
    2255,
    2257,
    2274,
    2282,
    2324,
    2336,
    4001,
    4004,
    4033,
    4047,
    4054,
    4174,
    4196,
    4197,
    5035,
    7023,
)
"""Looted drop species this slice sells to a merchant NPC: Clover 705,
Jellopy 909, Fluff 914, Chrysalis 915, Talon 917, Sticky Mucus 938, Feather
949 (window-26/27 Poring-field loots) plus Empty Bottle 713 and Iron Ore 1002
(leg 41: RinceNyan carried exactly these, held the trip at the dealer, and
its sell never opened because this constant lacked them — the drive fires on
merchant_drive_cell's sellables set but the shop loop filters the sale here).
Leg 67 re-derives the set from pay_fild04's pinned spawn declarations
(npc/pre-re/mobs/fields/payon.txt:63-70: Poring 1002, Drops 1113, Poporing
1031, Marin 1242, Ghostring 1120, Mastering 1090, Angeling 1096, Deviling
1582) through their served db/pre-re/mob_db.yml Drops rows resolved against
the pre-re item dbs: White_Herb 509, Blue_Herb 510, Green_Herb 511, Apple
512, Grape 514, Candy 529, Apple_Juice 531, Old_Blue_Box 603,
Branch_Of_Dead_Tree 604, Leaf_Of_Yggdrasil 610, Unripe_Apple 619,
Orange_Juice 620, Ghost scrolls 694/695, Cold_Scroll 700, Emperium 714,
jewels 720/722, Black_Dyestuffs 983, Petite wing 1039, Transparent_Cloth
1059, looted dagger/rod 1207/1602, garments 2116/2254/2255/2257/2274/2282/
2324/2336, Poring_Hat 5035, cards 4001/4004/4033/4047/4054/4174/4196/4197
and Blade_Lost_In_Darkness 7023 (s00 held 511x2 the whole leg — the drive
never armed). The drop KNIFE_ 1202 is deliberately EXCLUDED: it is a
NOVICE_WANTED_WEAPONS member the setup phase WEARS, and a worn weapon
stays in received inventory — inside the set it would read as sellable
stock on every equipped Novice and false-arm the sell arm forever (the
leg-40 weapon release pins tests/test_merchant_drive.py).
The constant only decides whether a sell leg is worth opening;
sellability and prices always come from the received ZC_PC_SELL_ITEMLIST
rows (clif.cpp:2265-2280), never from here. The drive's sellables set in
merchant_drive_cell MUST carry the same ids — extend both together (the
leg-46 twin-set law)."""


def shop_sellable_stock(
    inventory_counts: tuple[tuple[int, int], ...] | None,
    sellable_ids: tuple[int, ...] = SELLABLE_ITEM_IDS,
) -> int:
    """Total received stock of the sellable drop species; 0 when unknown."""
    if inventory_counts is None:
        return 0
    return sum(count for item, count in inventory_counts if item in sellable_ids)


def shop_affordable_weapon(
    offer_rows: tuple[tuple[int, int, int, int], ...],
    zeny: int | None,
    wanted: tuple[int, ...] = NOVICE_WANTED_WEAPONS,
) -> int | None:
    """First wanted weapon whose RECEIVED price fits the received zeny balance.

    ``offer_rows`` are received ZC_PC_PURCHASE_ITEMLIST rows
    ((price, discount_price, item_type, item_id), clif.cpp:2234-2238). An
    unknown zeny balance never buys. The owner-minted purchase path re-checks
    the row against the bound stable facts at dispatch (native_purchase).
    """
    if type(zeny) is not int or zeny < 0:
        return None
    for price, _discount, _item_type, item_id in offer_rows:
        if item_id in wanted and price <= zeny:
            return item_id
    return None


def shop_sell_entries(
    sell_rows: tuple[tuple[int, int, int], ...],
    stock: tuple[tuple[int, int, int], ...],
) -> tuple[tuple[int, int], ...]:
    """C9 entries ((client index, amount)) bounded by received stock.

    ``sell_rows`` are received ZC_PC_SELL_ITEMLIST rows ((index, price,
    overcharge)); ``stock`` is the tracker's detached indexed inventory
    ((client index, item id, count)). Zero-stock rows are skipped; amounts
    are the received counts, never invented.
    """
    counts = {index: count for index, _item, count in stock}
    return tuple(
        (index, counts[index])
        for index, _price, _overcharge in sell_rows
        if counts.get(index, 0) > 0
    )


MERCHANT_ZENY_MIN = 50
"""Known zeny balance below which the Novice keeps farming (window-28 gap).
The Weapon Dealer's Knife (1201) is the wanted item this budget buys; the
balance itself always comes from received 0x00B1 param-20 receipts
(BotState.zeny) — an unknown balance never drives (fail-closed).
Leg 67 reading: this floor is the BUY arm's travel-cost guard ONLY (the
spending trip needs the budget it will spend). The SELL arm is admitted by
sellable stock through the ``affordable or has_stock`` gate at zeny 0 —
the sell trip EARNS the zeny, so the floor must never grow back into the
sell arm's admission (pinned by tests/test_s00_sell_trip_route.py)."""

MERCHANT_ROUTE: dict[str, tuple[int, int]] = {
    "pay_fild04": (17, 165),
    "moc_fild01": (239, 382),
    "prt_fild08": (170, 378),
    "prontera": (177, 221),
    "prt_in": (172, 130),
}
"""Per-map engage cells of the dealer trip (window-29 merchant driver),
each pinned public rathena e985006171d2 bytes:
- ``npc/pre-re/warps/fields/payon_fild.txt:30``: ``pay_fild04,17,165,0
  warp payf002 2,8,moc_fild01,376,162`` — leg 67: the Archer-village
  field's dealer-bound way out (its other exit, payon_fild.txt:31, leads
  into the moc_fild02 desert chain, not toward the dealer map set); s00's
  field-side sell trip walks INTO this warp;
- ``npc/pre-re/warps/fields/morroc_fild.txt:24``: ``moc_fild01,239,382,0
  warp mocf006 12,1,prt_fild08,233,20`` — the mid-chain leg that lands ON
  prt_fild08, joining the proven field->town arc;
- ``npc/pre-re/warps/fields/prontera_fild.txt:65``: ``prt_fild08,170,378,0
  warp prtf004 3,2,prontera,156,26`` — the field leg walks into the return
  warp (arrival prontera,156,26);
- ``npc/warps/cities/prontera.txt:25``: ``prontera,177,221,0 warp prt05
  2,2,prt_in,168,128`` — the town leg walks into the prt_in entry;
- ``npc/merchants/shops.txt:255``: ``prt_in,172,130,0 shop Weapon
  Dealer#prt 54,...,1201:-1,1204:-1`` — the dealer cell (wanted ids on the
  received offer are the only purchase authority, window-28 loop).
Unknown maps are absent: the drive never engages there (fail-closed)."""

MERCHANT_ROUTE_RETURN: dict[str, tuple[int, int]] = {
    "prt_in": (168, 124),
    "prontera": (156, 22),
}
"""Per-map walk-home cells of the dealer trip (window-30 return legs), each
pinned public rathena e985006171d2 bytes (npc/warps/cities/prontera.txt, the
same file that carries the outbound legs):
- ``:40`` ``prt_in,168,124,0 warp prt05-1 2,1,prontera,174,218`` — the
  interior exit door, mirror of the cited prt05 entry (:25); walking into it
  arrives prontera,174,218;
- ``:24`` ``prontera,156,22,0 warp prt001 3,2,prt_fild08,170,375`` — the
  field warp; walking into it arrives prt_fild08,170,375, beside the cited
  outbound field leg (170,378), where the farm behavior resumes.
The field itself is absent: prt_fild08 behavior never changes, and unknown
maps stay absent (fail-closed)."""

DEALER_TALK_RANGE = 1
"""Chebyshev radius for matching the received dealer npc to the cited
cell. The shop interior's Item Guide sits 2 cells from the cited Weapon
Dealer cell (170,130 vs 172,130) — a radius of 2 captured it and the
talk latched on a dialog that never opens (the w79 empty hold)."""
"""Chebyshev distance from the cited dealer cell within which a received
npc actor counts as the dealer candidate; farther or position-less npcs are
never guessed — the step keeps walking instead (fail-closed)."""


# Two reasons to walk to the dealer: affordable purchase (zeny >= 50) or
# sellable stock (start_zeny is 0 in the owned world - the first trip
# EARNS the zeny by selling; window-28 finding). The stock set is the
# pinned mob_db drops of the prt_fild08 field species (all non-equipment
# loot is dealer stock; leg 39: RinceNyan carried 713+1002 and no trip
# engaged because the set only knew 909/915):
#   Pupa 1008 -> Chrysalis 915, Sticky_Mucus 938, Iron_Ore 1002
#   Drops 1113 -> Jellopy 909, Empty_Bottle 713
#   Lunatic 1063 -> Clover 705, Feather 949
#   Poring 1009 -> Talon 917;  Fabre 1007 -> Fluff 914
# (rathena db/pre-re/mob_db.yml + item_db_etc.yml, pinned e985006171d2)
DRIVE_SELLABLES = {
    # The SAME ids SELLABLE_ITEM_IDS carries (the leg-46 twin-set law):
    # the prt_fild08 species (window-28/leg-41) plus the leg-67
    # pay_fild04 derivation (spawn file payon.txt:63-70 -> served
    # mob_db.yml Drops -> pre-re item dbs; see SELLABLE_ITEM_IDS).
    "909",
    "915",
    "938",
    "1002",
    "713",
    "705",
    "949",
    "917",
    "914",
    "509",
    "510",
    "511",
    "512",
    "514",
    "529",
    "531",
    "603",
    "604",
    "610",
    "619",
    "620",
    "694",
    "695",
    "700",
    "714",
    "720",
    "722",
    "910",
    "912",
    "983",
    "1039",
    "1059",
    "1207",
    "1602",
    "2116",
    "2254",
    "2255",
    "2257",
    "2274",
    "2282",
    "2324",
    "2336",
    "4001",
    "4004",
    "4033",
    "4047",
    "4054",
    "4174",
    "4196",
    "4197",
    "5035",
    "7023",
}
"""The drive's stock set: the SAME ids SELLABLE_ITEM_IDS carries (the
leg-46 twin-set law - extend both together); the leg-67 pay_fild04
derivation rides the SELLABLE_ITEM_IDS docstring. Extracted to module
level by the leg-68 admission tap so ``merchant_admission_refusal`` reads
the same set the drive admits on."""


_MERCHANT_DRIVE_TAPPED: dict[str, str] = {}
"""bot -> last tapped admission verdict (change-only cadence). A verdict
line fires on the FIRST evaluation of a presence and on every term change
thereafter; steady-state refusals stay silent so a whole window logs
bounded lines while still proving the drive was reached (the leg-68
instrument gap: ZERO lines could not tell "evaluated and refused" from
"never evaluated" - now any evaluation logs at least once)."""


def _tap_merchant_drive(bot: str, term: str, detail: str) -> None:
    """One merchant-drive line per (bot, verdict term) change (leg 68
    defect 1): the admission's refusals name themselves instead of leaving
    a zero-line receipt that reads as "never evaluated"."""
    if _MERCHANT_DRIVE_TAPPED.get(bot) == term:
        return
    _MERCHANT_DRIVE_TAPPED[bot] = term
    logger.warning("merchant-drive: sell arm %s (%s)", term, detail)


def merchant_admission_refusal(state: BotState) -> tuple[str, str] | None:
    """The named-term verdict of the sell-arm admission (leg 68 defect 1).

    ``merchant_drive_cell``'s silent ``return None`` gates, decomposed:
    ``not_novice`` / ``inventory_unknown`` (the precondition pair),
    ``no_stock_below_zeny_floor`` (the combined affordable-or-stock gate -
    the detail names which sub-fact failed), ``weapon_release`` (the leg-40
    wanted-weapon hold) and ``map_not_on_merchant_route`` (the pinned route
    lookup). ``(term, detail)`` with the detail carrying the full guard
    state; None when the drive admits. Verdicts only - the behavior
    authority stays in ``merchant_drive_cell``.
    """
    refusal = _precondition_refusal(state)
    affordable = type(state.zeny) is int and state.zeny >= MERCHANT_ZENY_MIN
    has_stock = any(str(item) in DRIVE_SELLABLES for item in state.inventory)
    if refusal is None:
        refusal = _want_refusal(state, affordable, has_stock)
    if refusal is not None:
        return refusal, _admission_detail(state, affordable, has_stock)
    return None


def _admission_detail(state: BotState, affordable: bool, has_stock: bool) -> str:
    """The full guard state one admission tap line carries."""
    stock = sum(count for item, count in state.inventory.items() if item in DRIVE_SELLABLES)
    return (
        f"map={state.map_name} zeny={state.zeny} floor={MERCHANT_ZENY_MIN} "
        f"job={state.job} inv_known={state.inventory_known} "
        f"stock={stock} has_stock={has_stock} affordable={affordable}"
    )


def _precondition_refusal(state: BotState) -> str | None:
    """The sell-arm admission's precondition pair, named."""
    if state.job != "Novice":
        return "not_novice"
    if not state.inventory_known:
        return "inventory_unknown"
    return None


def _want_refusal(state: BotState, affordable: bool, has_stock: bool) -> str | None:
    """The want terms, named: the combined stock/zeny gate, the leg-40
    weapon hold, the route map."""
    if not (affordable or has_stock):
        return "no_stock_below_zeny_floor"
    if not has_stock and any(str(item) in state.inventory for item in NOVICE_WANTED_WEAPONS):
        return "weapon_release"
    if MERCHANT_ROUTE.get(state.map_name) is None:
        return "map_not_on_merchant_route"
    return None


def merchant_drive_cell(state: BotState) -> tuple[int, int] | None:
    """Engage cell of the want-driven dealer trip, else None (window-29).

    Two arms: the BUY arm (a Novice with no wanted weapon and a KNOWN zeny
    >= MERCHANT_ZENY_MIN) and the SELL arm (a Novice holding sellable
    stock, weapon or not — leg 40: the fixture knife in every inventory
    kept the old single release from ever firing the trip). Both need a
    KNOWN inventory and a pinned route map; anything else returns None and
    the field behavior is unchanged.
    """
    refusal = merchant_admission_refusal(state)
    if refusal is not None:
        term, detail = refusal
        _tap_merchant_drive(state.name, term, detail)
        return None
    destination = MERCHANT_ROUTE.get(state.map_name)
    stock = sum(count for item, count in state.inventory.items() if item in DRIVE_SELLABLES)
    _tap_merchant_drive(
        state.name,
        "admitted",
        f"map={state.map_name} dest={destination} zeny={state.zeny} stock={stock}",
    )
    return destination


def merchant_return_cell(state: BotState) -> tuple[int, int] | None:
    """Walk-home cell when the dealer want does not hold (window-30).

    Fires for the farm/grind goal scripts (the only ``_merchant_step``
    callers) when the received state shows all of: a Novice, KNOWN inventory
    with no wanted weapon (a worn weapon stays in received inventory — its
    presence releases the return exactly like the drive), no outbound want
    (the drive owns the engagement while it holds), and a pinned return map
    beyond the field. Anything else returns None: the field behavior and the
    drive stay unchanged; unknown maps fail closed.
    """
    if state.job != "Novice" or not state.inventory_known:
        return None
    if any(str(item) in state.inventory for item in NOVICE_WANTED_WEAPONS):
        return None
    if merchant_drive_cell(state) is not None:
        return None
    return MERCHANT_ROUTE_RETURN.get(state.map_name)


def _merchant_step(
    state: BotState,
    resolver: TravelResolver | None = None,
    reachable: MerchantReachable | None = None,
) -> ScriptOutcome | None:
    """The goal-level merchant interruption (windows 29-30), rest/loot class.

    Returns None when neither the outbound want nor a return leg holds (the
    caller's field behavior applies unchanged); otherwise one engagement
    toward the current route leg — outbound: a TalkToNpc once the dealer npc
    is received at the cited cell (the window-28 shop loop owns the
    exchange), return: the walk back to the field, one MoveTo per
    evaluation; warp map changes re-derive the next leg.

    leg 37's merchant half: when the reachability authority says the pinned
    leg sits in ANOTHER interior component, the walk starts with the agent's
    OWN door (the resolver's first current-map leg) — from prontera the
    route's own prontera leg re-enters through the dealer's warp.
    """
    destination = merchant_drive_cell(state)
    if destination is not None:
        if (
            reachable is not None
            and resolver is not None
            and reachable(state.map_name, (state.x, state.y), destination) is False
        ):
            plan = resolver(state.map_name, state.x, state.y) or ()
            for leg_map, leg_x, leg_y in plan:
                if leg_map == state.map_name and (leg_x, leg_y) != (state.x, state.y):
                    return ScriptOutcome((MoveTo(x=leg_x, y=leg_y),), ScriptStatus.ACTIVE)
            _tap_merchant_drive(
                state.name,
                "merchant_route_unresolved",
                f"map={state.map_name} dest={destination}",
            )
        return _merchant_engage(state, destination)
    home = merchant_return_cell(state)
    if home is None:
        return None
    # Heading home ends the dealer contact: the next outbound visit is a
    # fresh (bot, npc) contact and may talk again, so the sell-and-buy
    # cycle can repeat across trips (window-30 return legs).
    _DEALER_TALKED.pop(state.name, None)
    return ScriptOutcome((MoveTo(x=home[0], y=home[1]),), ScriptStatus.ACTIVE)


def _merchant_engage(state: BotState, destination: tuple[int, int]) -> ScriptOutcome:
    """The outbound dealer engagement (window-29): walk the leg, or talk
    once at the dealer and hold for the dealtype."""
    if state.map_name == "prt_in":
        # LEG 53: a BOUND offer means the exchange is in flight — the
        # mechanical purchase path owns it and any fresh click here opens a
        # new round that kills the bound offer (moved-on) before the
        # decide-paced mint ever sees it. Hold the click; author nothing.
        if state.shop_offer is not None:
            return ScriptOutcome((), ScriptStatus.ACTIVE)
        talk = _dealer_talk(state, destination)
        if talk is None and _DEALER_TALKED.get(state.name) is not None:
            # The dealer npc is no longer received: any latch is stale (the
            # npc actor expired / the relog closed the dialog). Clear it so
            # the walk resumes and a fresh contact can talk again (w76).
            _DEALER_TALKED.pop(state.name, None)
        if talk is not None:
            # One talk per (bot, npc) contact: re-sending resets the server's
            # npc_shopid before the 0xC4 dealtype can be answered (window-29:
            # 2254 TalkToNpc resets). The hold lets the dialog stage machine
            # and the shop-loop mechanical own the exchange.
            bot = state.name
            npc_id = talk.npc_id
            if _DEALER_TALKED.get(bot) == npc_id:
                # One talk per (bot, npc) contact; the shop-loop mechanical
                # owns the exchange while the dealer npc stays received.
                return ScriptOutcome((), ScriptStatus.ACTIVE)
            _DEALER_TALKED[bot] = npc_id
            return ScriptOutcome((talk,), ScriptStatus.ACTIVE)
        # leg-71 frontier b: the walk-to-dealer targets the APPROACH CELL
        # (the dealer's neighbouring cell nearest the agent, the proven
        # ``_approach_cell`` intercept from the attack scripts). The dealer's
        # own cell can never be entered (the shop npc holds it), so the old
        # direct target stopped the server walk 2 cells out and the
        # adjacency-gated talk silently never fired (xXLunasongXx parked at
        # Chebyshev 2, MoveTo every tick, npc rows []). Field/town legs are
        # untouched: a warp must be ENTERED, so those keep the pinned cell.
        walk_cell = _approach_cell(destination[0], destination[1], state)
        return ScriptOutcome((MoveTo(x=walk_cell[0], y=walk_cell[1]),), ScriptStatus.ACTIVE)
    return ScriptOutcome((MoveTo(x=destination[0], y=destination[1]),), ScriptStatus.ACTIVE)


def _dealer_talk(state: BotState, dealer_cell: tuple[int, int]) -> TalkToNpc | None:
    """The received dealer npc AT the cited cell, else None.

    The match must be tight (Chebyshev <= 1, both against the cited cell
    and against the agent): a loose radius captures whatever other npc
    stands near the cited cell, and a talk at range never lands. With the
    dealer received but the agent beyond the click range, the range tap
    names the distance (leg-71 frontier b) and the step keeps walking."""
    at_cell = [actor for actor in state.nearby if _received_dealer_at_cell(actor, dealer_cell)]
    if not at_cell:
        return None
    candidates = [actor for actor in at_cell if _within_talk_range(actor, state)]
    if not candidates:
        _tap_dealer_range(state, at_cell)
        return None
    return TalkToNpc(min(candidates, key=lambda actor: actor.distance).id)


def _received_dealer_at_cell(actor: ActorRef, dealer_cell: tuple[int, int]) -> bool:
    """A name-matched Weapon Dealer npc with a tracked position within
    ``DEALER_TALK_RANGE`` of the cited cell (the w79/w80 tight match: the
    Item Guide 2 cells away is never the dealer; position-less npcs are
    never guessed — fail closed)."""
    return (
        actor.kind == "npc"
        and getattr(actor, "name", "").startswith("Weapon Dealer")
        and getattr(actor, "x", None) is not None
        and getattr(actor, "y", None) is not None
        and max(
            abs(actor.x - dealer_cell[0]),  # type: ignore[operator]
            abs(actor.y - dealer_cell[1]),  # type: ignore[operator]
        )
        <= DEALER_TALK_RANGE
    )


def _within_talk_range(actor: ActorRef, state: BotState) -> bool:
    """The agent stands within ``DEALER_TALK_RANGE`` (Chebyshev) of the
    actor: rAthena's npc_click range check silently rejects clicks from 2+
    cells and the latch would hold on a shop that never opens (the w81
    null-offer trace)."""
    return (
        max(
            abs(actor.x - state.x),  # type: ignore[operator]
            abs(actor.y - state.y),  # type: ignore[operator]
        )
        <= DEALER_TALK_RANGE
    )


def _tap_dealer_range(state: BotState, at_cell: list[ActorRef]) -> None:
    """Tap-before-fix (leg-71 frontier b): the dealer is received at the
    cited cell but the talk cannot fire — the agent stands beyond the click
    range. Name the distance so a residual range-2 park (the xXLunasongXx
    shape: MoveTo every tick, npc rows [], zeny never moved) shows up in the
    window log instead of reading as a silent no-op."""
    nearest = min(
        at_cell,
        key=lambda actor: max(
            abs(actor.x - state.x),  # type: ignore[operator]
            abs(actor.y - state.y),  # type: ignore[operator]
        ),
    )
    distance = max(
        abs(nearest.x - state.x),  # type: ignore[operator]
        abs(nearest.y - state.y),  # type: ignore[operator]
    )
    detail = f"agent=({state.x},{state.y}) dealer=({nearest.x},{nearest.y}) chebyshev={distance}"
    if _DEALER_RANGE_TAPPED.get(state.name) == detail:
        return
    _DEALER_RANGE_TAPPED[state.name] = detail
    # The merchant-drive tap line with a DETAIL-keyed memo of its own: the
    # shared per-term memo would flip-flop with the per-tick ``admitted``
    # line and log every drive tick.
    logger.warning("merchant-drive: sell arm %s (%s)", "dealer_talk_out_of_range", detail)


def _engage(state: BotState, candidates: list[ActorRef], window: int) -> ScriptOutcome:
    """Keep hitting the committed candidate; closest-pick when unheld.

    A landed attack (in melee range) arms/rearms the commitment; an approach
    MoveTo consumes one window evaluation.
    """
    commitment = _kill_commitment(state.name, window)
    target = commitment.hold(candidates)
    if target is None:
        target = min(
            candidates,
            key=lambda mob: (
                _PINNED_MOB_HP.get(str(mob.name), _UNKNOWN_MOB_HP),
                mob.distance,
            ),
        )
    action = _melee_action(target, state)
    if isinstance(action, Attack):
        commitment.commit(target.id)
    return ScriptOutcome((action,), ScriptStatus.ACTIVE)


def _approach_cell(tx: int, ty: int, state: BotState) -> tuple[int, int]:
    """The neighbouring cell of the target nearest the bot (the intercept).

    Walking to the target's own cell lands the bot where a wandering mob WAS
    (leg 18: 31 near samples, zero adjacent). A one-cell mob shift from an
    adjacent-cell walk still ends in melee range. Deterministic tie-break on
    the cell coordinates."""
    best: tuple[int, int] | None = None
    best_key: tuple[int, int, int] | None = None
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            cell = (tx + dx, ty + dy)
            cheb = max(abs(cell[0] - state.x), abs(cell[1] - state.y))
            euclid = (cell[0] - state.x) ** 2 + (cell[1] - state.y) ** 2
            key = (cheb, euclid, cell[0] * 1000 + cell[1])
            if best_key is None or key < best_key:
                best_key = key
                best = cell
    if best is None:  # drift-guard: 8 candidates always run; the old
        # sentinel default (tx+1, ty) re-introduced the >99-cell artifact
        return (tx + 1, ty)
    return best


def _melee_action(target: ActorRef, state: BotState) -> GameAction:
    """Attack within melee range; otherwise walk toward the target's cell.

    The cell is read fresh from the handed-in state on every evaluation, so
    the approach re-follows a moved target and never commits to a stale
    destination. A state monster without a tracked position keeps the honest
    legacy behavior: attack anyway and let the server's range check fail
    closed (the tracked 0x0139 is that feedback).
    """
    x = getattr(target, "x", None)
    y = getattr(target, "y", None)
    if x is None or y is None:
        return Attack(target_id=target.id)
    if max(abs(x - state.x), abs(y - state.y)) <= MELEE_RANGE:
        return Attack(target_id=target.id)
    cell = _approach_cell(x, y, state)
    return MoveTo(x=cell[0], y=cell[1])


@final
class TravelScript:
    """Walk toward a destination; DONE on arrival."""

    def __init__(self, x: int, y: int) -> None:
        self._target = (x, y)

    def step(self, state: BotState) -> ScriptOutcome:
        tx, ty = self._target
        if (state.x, state.y) == (tx, ty):
            return ScriptOutcome((), ScriptStatus.DONE)
        dx = (tx > state.x) - (tx < state.x)
        dy = (ty > state.y) - (ty < state.y)
        return ScriptOutcome((MoveTo(x=state.x + dx, y=state.y + dy),), ScriptStatus.ACTIVE)


@final
class GrindScript:
    """Attack the closest monster, loot after kills, rest when hurt.

    Within ``commit_window`` script evaluations the most recently attacked,
    still-visible target keeps the hits (KILL_COMMIT_WINDOW) so a low-damage
    attacker can accumulate a kill instead of re-picking closest each tick.
    """

    def __init__(
        self,
        hp_rest_below: float = 0.25,
        commit_window: int = KILL_COMMIT_WINDOW,
        travel_plan: tuple[tuple[str, int, int], ...] = (),
        travel_resolver: TravelResolver | None = None,
        merchant_reachable: MerchantReachable | None = None,
    ) -> None:
        self._hp_rest_below = hp_rest_below
        self._commit_window = commit_window
        self._travel_plan = travel_plan
        self._travel_resolver = travel_resolver
        self._merchant_reachable = merchant_reachable

    def step(self, state: BotState) -> ScriptOutcome:
        if state.hp_ratio < self._hp_rest_below:
            _release_commitment(state, self._commit_window)
            return ScriptOutcome((Rest(),), ScriptStatus.ACTIVE)
        merchant = _merchant_step(
            state, self._travel_resolver, self._merchant_reachable
        )  # window-29: want-driven dealer trip
        if merchant is not None:
            return merchant
        monsters = sorted(state.nearby_monsters, key=lambda m: m.distance)
        if monsters:
            return _engage(state, monsters, self._commit_window)
        _release_commitment(state, self._commit_window)
        # the travel leg (leg 20): a grind goal on a mobless map walks the
        # route toward the known field instead of patrolling the town (the
        # Loot branch is pointless while the bot is off-field)
        plan = self._travel_plan_for(state)
        if plan:
            leg = self._travel_leg(state, plan)
            if leg is not None:
                return ScriptOutcome((MoveTo(x=leg[0], y=leg[1]),), ScriptStatus.ACTIVE)
        # w65-69 roam leg (mirrors FarmScript): an empty view must not
        # complete as DONE — the goal-grind agent would churn DONE forever
        # standing in a mobless patch. Patrol a bounded step instead.
        dx, dy = random.choice(((8, 0), (-8, 0), (0, 8), (0, -8), (5, 5), (-5, -5)))
        return ScriptOutcome(
            (MoveTo(max(0, state.x + dx), max(0, state.y + dy)),),
            ScriptStatus.ACTIVE,
        )

    def _travel_plan_for(self, state: BotState) -> tuple[tuple[str, int, int], ...]:
        """The route legs to follow from where the agent stands NOW.

        The resolver is AUTHORITATIVE when there is one: the way out of a
        map can depend on the agent's own cell (leg 37's prt_in interiors),
        so a resolver that names no route means exactly that - there is no
        way out from here - and the seeded plan must NOT be substituted
        for it (the seeded plan names one door, and from another interior
        that door cannot be reached at all). The seeded plan is the
        fallback only for a world with NO resolver.
        """
        if self._travel_resolver is not None:
            return self._travel_resolver(state.map_name, state.x, state.y) or ()
        return self._travel_plan

    def _travel_leg(
        self, state: BotState, plan: tuple[tuple[str, int, int], ...]
    ) -> tuple[int, int] | None:
        """The first unmet route cell on the bot's current map; None = arrived.

        The plan is the ordered [(map, x, y)] warp route from the knowledge
        surface (route_hint). Legs on other maps are already behind the bot."""
        for leg_map, x, y in plan:
            if leg_map != state.map_name:
                continue
            if (state.x, state.y) == (x, y):
                continue
            return (x, y)
        return None


@final
class IdleTownScript:
    """Stand around; occasionally shift position a step. Done never — events or a
    goal review end it.

    Leg 37: the step used to be MoveTo(x, y+1) unconditionally, so one wall
    locked the whole script lifetime onto a single impossible cell (g00m02
    authored 3,210 MoveTos to an unwalkable (159,194) and stood 117 minutes).
    The steps now cycle the four directions deterministically — the runtime's
    walkability/route handling stays the single authority on whether a cell
    can actually be walked (the w59 split: scripts author, the grid gates)."""

    _DIRECTIONS: tuple[tuple[int, int], ...] = ((0, 1), (1, 0), (0, -1), (-1, 0))

    def __init__(self, max_steps: int = 10) -> None:
        self._remaining = max_steps
        self._tick = 0

    def step(self, state: BotState) -> ScriptOutcome:
        if self._remaining <= 0:
            return ScriptOutcome((), ScriptStatus.DONE)
        self._remaining -= 1
        dx, dy = self._DIRECTIONS[self._tick % len(self._DIRECTIONS)]
        self._tick += 1
        return ScriptOutcome(
            (MoveTo(max(0, state.x + dx), max(0, state.y + dy)),),
            ScriptStatus.ACTIVE,
        )


@final
class FarmScript:
    """Plan-driven variant of GrindScript: attack only the plan's target mobs,
    ignore everything else (interrupts are the brain's/plan's business). The
    target commitment (KILL_COMMIT_WINDOW) applies inside the CURRENT
    effective filter — strict plan targets, or the widened observed species
    after the bounded starvation streak — never an out-of-filter id."""

    def __init__(
        self,
        plan: FarmPlan,
        hp_rest_below: float = 0.25,
        widen_steps: int = TARGET_WIDEN_STEPS,
        commit_window: int = KILL_COMMIT_WINDOW,
        initial_starved: int = 0,
        *,
        travel_resolver: TravelResolver | None = None,
        merchant_reachable: MerchantReachable | None = None,
    ) -> None:
        self.plan = plan
        self._hp_rest_below = hp_rest_below
        self._widen_steps = widen_steps
        self._commit_window = commit_window
        self._starved = max(0, int(initial_starved))
        self._roam_rng = random.Random(f"roam-{plan.plan_id}-{plan.map_name}")
        self._travel_resolver = travel_resolver
        self._merchant_reachable = merchant_reachable

    def step(self, state: BotState) -> ScriptOutcome:
        if state.hp_ratio < self._hp_rest_below:
            _release_commitment(state, self._commit_window)
            return ScriptOutcome((Rest(),), ScriptStatus.ACTIVE)
        merchant = _merchant_step(
            state, self._travel_resolver, self._merchant_reachable
        )  # window-29: want-driven dealer trip
        if merchant is not None:
            return merchant
        monsters = sorted(state.nearby_monsters, key=lambda a: a.distance)
        targets = [m for m in monsters if m.name in self.plan.target_mobs]
        if targets:
            self._starved = 0
        else:
            # Species starvation (window-14 gap 1): hold the plan's strict
            # target only for a bounded, counted streak of absent-species
            # evaluations; then widen this script's filter to whatever the
            # received state actually shows. The plan itself is unchanged and
            # is preferred again as soon as one of its species is present.
            self._starved += 1
            if self._starved >= self._widen_steps:
                targets = monsters
        if targets:
            return _engage(state, targets, self._commit_window)
        _release_commitment(state, self._commit_window)
        # w59/w60 roam leg: an empty view must not stand still. Emit a bounded
        # patrol step near the current cell so the agent walks to find its
        # plan's species (the runtime's pending-walk pacing throttles the
        # re-sends; deterministic per plan for testability).
        dx, dy = self._roam_rng.choice(((8, 0), (-8, 0), (0, 8), (0, -8), (5, 5), (-5, -5)))
        return ScriptOutcome(
            (MoveTo(max(0, state.x + dx), max(0, state.y + dy)),),
            ScriptStatus.ACTIVE,
        )


@final
class NpcGuidanceScript:
    """Ask an observed guide; no hidden NPC catalogue or assumed reward."""

    def step(self, state: BotState) -> ScriptOutcome:
        status = self._dialog_status(state)
        if state.hp_ratio < 0.25:
            return ScriptOutcome((Rest(),), status)
        if state.npc_dialogue is not None:
            return ScriptOutcome((), status)
        npcs = sorted((a for a in state.nearby if a.kind == "npc"), key=lambda a: a.distance)
        return ScriptOutcome((TalkToNpc(npcs[0].id),) if npcs else (), ScriptStatus.ACTIVE)

    @staticmethod
    def _dialog_status(state: BotState) -> ScriptStatus:
        if state.npc_dialogue is None:
            return ScriptStatus.ACTIVE
        return {
            "close_requested": ScriptStatus.DONE,
            "cancel_abandoned": ScriptStatus.FAILED,
        }.get(state.npc_dialogue.stage, ScriptStatus.ACTIVE)


def needs_npc_preparation(state: BotState) -> bool:
    received_instruction = state.npc_instructions_received
    return (
        state.native_epoch is not None
        and state.job == "Novice"
        and state.inventory_known
        and not state.inventory
        and not received_instruction
    )


def script_for(goal: Goal, state: BotState) -> BehaviorScript:
    """Factory: pick the autopilot matching the chosen goal."""
    if needs_npc_preparation(state):
        return NpcGuidanceScript()
    match goal:
        case Goal.GRIND | Goal.FARM_ITEM:
            return GrindScript()
        case Goal.IDLE_TOWN | Goal.SOCIAL:
            return IdleTownScript()
        case Goal.QUEST:
            return NpcGuidanceScript()
        case _:
            assert_never(goal)
