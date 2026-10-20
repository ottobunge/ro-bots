"""Behavior scripts: mechanical execution of a goal between events.

A script is the "autopilot" — it walks, attacks, loots, idles — and it stays
in charge until the world produces an event (see robots.domain.events) or it
completes/fails. No decision-model calls happen inside a script.
"""

import random
from collections.abc import Sequence
from enum import Enum, auto
from typing import TYPE_CHECKING, Protocol, assert_never, final

from robots.domain.actions import Attack, GameAction, Loot, MoveTo, Rest, TalkToNpc
from robots.domain.farm import FarmPlan
from robots.domain.model import ActorRef, Goal

if TYPE_CHECKING:
    from robots.domain.model import BotState


class ScriptStatus(Enum):
    ACTIVE = auto()
    DONE = auto()
    FAILED = auto()


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


def reset_merchant_talk() -> None:
    """Forget per-bot dealer contacts (new session epoch / test isolation)."""
    _DEALER_TALKED.clear()


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


SELLABLE_ITEM_IDS = (909, 915)
"""Looted drop species this slice sells to a merchant NPC: Jellopy 909 and
Chrysalis 915 (the window-26/27 Poring-field loots). The constant only decides
whether a sell leg is worth opening; sellability and prices always come from
the received ZC_PC_SELL_ITEMLIST rows (clif.cpp:2265-2280), never from here."""


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
(BotState.zeny) — an unknown balance never drives (fail-closed)."""

MERCHANT_ROUTE: dict[str, tuple[int, int]] = {
    "prt_fild08": (170, 378),
    "prontera": (177, 221),
    "prt_in": (172, 130),
}
"""Per-map engage cells of the dealer trip (window-29 merchant driver),
each pinned public rathena e985006171d2 bytes:
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

DEALER_TALK_RANGE = 2
"""Chebyshev distance from the cited dealer cell within which a received
npc actor counts as the dealer candidate; farther or position-less npcs are
never guessed — the step keeps walking instead (fail-closed)."""


def merchant_drive_cell(state: BotState) -> tuple[int, int] | None:
    """Engage cell of the want-driven dealer trip, else None (window-29).

    Fires only when the received state shows all of: a Novice, no wanted
    weapon known in inventory (a bought OR looted weapon — a worn weapon
    stays in received inventory — releases the drive), a KNOWN zeny balance
    >= MERCHANT_ZENY_MIN, known inventory, and a pinned route map. Anything
    else returns None and the field behavior is unchanged.
    """
    if state.job != "Novice" or not state.inventory_known:
        return None
    if any(str(item) in state.inventory for item in NOVICE_WANTED_WEAPONS):
        return None
    # Two reasons to walk to the dealer: affordable purchase (zeny >= 50) or
    # sellable stock (start_zeny is 0 in the owned world - the first trip
    # EARNS the zeny by selling; window-28 finding).
    sellables = {"909", "915"}  # Jellopy 909, Chrysalis 915 (pinned drops)
    affordable = type(state.zeny) is int and state.zeny >= MERCHANT_ZENY_MIN
    has_stock = any(str(item) in sellables for item in state.inventory)
    if not (affordable or has_stock):
        return None
    return MERCHANT_ROUTE.get(state.map_name)


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


def _merchant_step(state: BotState) -> ScriptOutcome | None:
    """The goal-level merchant interruption (windows 29-30), rest/loot class.

    Returns None when neither the outbound want nor a return leg holds (the
    caller's field behavior applies unchanged); otherwise one engagement
    toward the current route leg — outbound: a TalkToNpc once the dealer npc
    is received at the cited cell (the window-28 shop loop owns the
    exchange), return: the walk back to the field, one MoveTo per
    evaluation; warp map changes re-derive the next leg.
    """
    destination = merchant_drive_cell(state)
    if destination is not None:
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
        talk = _dealer_talk(state, destination)
        if talk is not None:
            # One talk per (bot, npc) contact: re-sending resets the server's
            # npc_shopid before the 0xC4 dealtype can be answered (window-29:
            # 2254 TalkToNpc resets). The hold lets the dialog stage machine
            # and the shop-loop mechanical own the exchange.
            bot = state.name
            npc_id = talk.npc_id
            if _DEALER_TALKED.get(bot) == npc_id:
                return ScriptOutcome((), ScriptStatus.ACTIVE)
            _DEALER_TALKED[bot] = npc_id
            return ScriptOutcome((talk,), ScriptStatus.ACTIVE)
    return ScriptOutcome((MoveTo(x=destination[0], y=destination[1]),), ScriptStatus.ACTIVE)


def _dealer_talk(state: BotState, dealer_cell: tuple[int, int]) -> TalkToNpc | None:
    """The received dealer npc nearest the cited cell, else None."""
    candidates = [
        actor
        for actor in state.nearby
        if actor.kind == "npc"
        and getattr(actor, "x", None) is not None
        and getattr(actor, "y", None) is not None
        and max(
            abs(actor.x - dealer_cell[0]),  # type: ignore[operator]
            abs(actor.y - dealer_cell[1]),  # type: ignore[operator]
        )
        <= DEALER_TALK_RANGE
    ]
    if not candidates:
        return None
    return TalkToNpc(min(candidates, key=lambda actor: actor.distance).id)


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
    return MoveTo(x=x, y=y)


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
        self, hp_rest_below: float = 0.25, commit_window: int = KILL_COMMIT_WINDOW
    ) -> None:
        self._hp_rest_below = hp_rest_below
        self._commit_window = commit_window

    def step(self, state: BotState) -> ScriptOutcome:
        if state.hp_ratio < self._hp_rest_below:
            _release_commitment(state, self._commit_window)
            return ScriptOutcome((Rest(),), ScriptStatus.ACTIVE)
        merchant = _merchant_step(state)  # window-29: want-driven dealer trip
        if merchant is not None:
            return merchant
        monsters = sorted(state.nearby_monsters, key=lambda m: m.distance)
        if monsters:
            return _engage(state, monsters, self._commit_window)
        _release_commitment(state, self._commit_window)
        if state.inventory:
            return ScriptOutcome((Loot(),), ScriptStatus.ACTIVE)
        return ScriptOutcome((), ScriptStatus.DONE)


@final
class IdleTownScript:
    """Stand around; occasionally shift position a step. Done never — events or a
    goal review end it."""

    def __init__(self, max_steps: int = 10) -> None:
        self._remaining = max_steps

    def step(self, state: BotState) -> ScriptOutcome:
        if self._remaining <= 0:
            return ScriptOutcome((), ScriptStatus.DONE)
        self._remaining -= 1
        return ScriptOutcome((MoveTo(x=state.x, y=state.y + 1),), ScriptStatus.ACTIVE)


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
    ) -> None:
        self.plan = plan
        self._hp_rest_below = hp_rest_below
        self._widen_steps = widen_steps
        self._commit_window = commit_window
        self._starved = 0
        self._roam_rng = random.Random(f"roam-{plan.plan_id}-{plan.map_name}")

    def step(self, state: BotState) -> ScriptOutcome:
        if state.hp_ratio < self._hp_rest_below:
            _release_commitment(state, self._commit_window)
            return ScriptOutcome((Rest(),), ScriptStatus.ACTIVE)
        merchant = _merchant_step(state)  # window-29: want-driven dealer trip
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
        if state.inventory:
            return ScriptOutcome((Loot(),), ScriptStatus.ACTIVE)
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
