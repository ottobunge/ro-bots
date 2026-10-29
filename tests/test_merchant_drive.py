"""Goal-level merchant driver (window 29): want-driven dealer travel.

When the received state shows (a) a Novice with no known wanted weapon,
(b) a KNOWN zeny balance >= 50 (0x00B1 param 20 receipts), and (c) the map
on a pinned route leg, the goal scripts engage toward the cited Weapon
Dealer (npc/merchants/shops.txt:255: ``prt_in,172,130,0 shop
Weapon Dealer#prt ... 1201:-1,1204:-1``) instead of attacking. Once the
dealer dialog opens, the landed window-28 shop loop owns the exchange.
Fail-closed everywhere: unknown zeny, non-Novice, inventory-unknown,
unknown maps and any known wanted weapon (bought OR looted — a worn weapon
stays in received inventory) keep the exact field behavior. The pinned farm
plan is never rewritten; the driver is a want-driven interruption like
rest/loot, evaluated per step and released by the state itself.

Route legs are pinned public warp/shop bytes (rathena e985006171d2):
- ``npc/pre-re/warps/fields/prontera_fild.txt:65``
  ``prt_fild08,170,378,0  warp  prtf004  3,2,prontera,156,26``
- ``npc/warps/cities/prontera.txt:25``
  ``prontera,177,221,0  warp  prt05  2,2,prt_in,168,128``
- ``npc/merchants/shops.txt:255`` dealer cell ``prt_in,172,130``.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for candidate in (str(REPO / "src"), str(REPO), str(REPO / "tests")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from robots.app import scripts  # noqa: E402
from robots.app.scripts import (  # noqa: E402
    _DEALER_TALKED,
    MERCHANT_ROUTE,
    MERCHANT_ROUTE_RETURN,
    MERCHANT_ZENY_MIN,
    FarmScript,
    GrindScript,
    ScriptStatus,
    _dealer_talk,
    _merchant_engage,
    merchant_drive_cell,
    merchant_return_cell,
)
from robots.domain.actions import Attack, MoveTo, Rest, TalkToNpc  # noqa: E402
from robots.domain.farm import FarmPlan  # noqa: E402
from robots.domain.model import ActorRef, BotState, Goal  # noqa: E402


def _state(**over: object) -> BotState:
    base: dict[str, object] = {
        "name": "fixture_0",
        "job": "Novice",
        "base_level": 1,
        "hp": 40,
        "max_hp": 40,
        "sp": 10,
        "max_sp": 10,
        "map_name": "prt_fild08",
        "x": 170,
        "y": 300,
        "goal": Goal.FARM_ITEM,
        "in_party": False,
        "nearby": (),
        "inventory": {},
        "pending_invites": (),
        "recent_chat": (),
    }
    base.update(over)
    return BotState(**base)  # type: ignore[arg-type]


def _poring(x: int | None = 171, y: int | None = 300, id: int = 150001) -> ActorRef:
    return ActorRef(id=id, name="Poring", kind="monster", distance=1.0, x=x, y=y)


def _plan() -> FarmPlan:
    return FarmPlan(
        plan_id=1,
        map_name="prt_fild08",
        target_mobs=("Poring",),
        duration_s=600,
        interrupt_level_above=1,
    )


# --- route table (pinned cells) ---


def test_route_cites_field_warp_cell() -> None:
    assert MERCHANT_ROUTE["prt_fild08"] == (170, 378)
    assert MERCHANT_ROUTE["prontera"] == (177, 221)
    assert MERCHANT_ROUTE["prt_in"] == (172, 130)


def test_zeny_threshold_is_50() -> None:
    assert MERCHANT_ZENY_MIN == 50


# --- want-driven predicate: fire ---


def test_drive_engages_on_field_leg() -> None:
    assert merchant_drive_cell(_state(zeny=60)) == (170, 378)


def test_drive_engages_at_exact_threshold() -> None:
    assert merchant_drive_cell(_state(zeny=50)) == (170, 378)


def test_drive_engages_on_town_leg() -> None:
    assert merchant_drive_cell(_state(map_name="prontera", x=156, y=26, zeny=60)) == (
        177,
        221,
    )


def test_drive_engages_on_dealer_leg() -> None:
    assert merchant_drive_cell(_state(map_name="prt_in", x=168, y=128, zeny=60)) == (
        172,
        130,
    )


# --- want-driven predicate: fail-closed / release ---


def test_unknown_zeny_keeps_farming() -> None:
    assert merchant_drive_cell(_state(zeny=None)) is None


def test_zeny_below_threshold_keeps_farming() -> None:
    assert merchant_drive_cell(_state(zeny=49)) is None


def test_non_novice_never_drives() -> None:
    assert merchant_drive_cell(_state(job="Swordsman", zeny=5000)) is None


def test_wanted_weapon_in_inventory_releases() -> None:
    # bought OR looted: a worn weapon stays in received inventory, so its
    # presence is the honest received release signal.
    assert merchant_drive_cell(_state(zeny=60, inventory={"1202": 1})) is None
    assert merchant_drive_cell(_state(zeny=60, inventory={"1201": 1})) is None
    assert merchant_drive_cell(_state(zeny=60, inventory={"1204": 1})) is None


def test_inventory_unknown_fails_closed() -> None:
    assert merchant_drive_cell(_state(zeny=60, inventory_known=False)) is None


def test_unknown_map_never_drives() -> None:
    assert merchant_drive_cell(_state(map_name="prt_fild00", zeny=60)) is None


# --- goal-script engagement (the interruption lives in the scripts) ---


def test_grind_script_engages_dealer_instead_of_attacking() -> None:
    state = _state(zeny=60, nearby=(_poring(),))
    outcome = GrindScript().step(state)
    assert outcome.status == ScriptStatus.ACTIVE
    assert outcome.actions == (MoveTo(x=170, y=378),)


def test_farm_script_engages_dealer_instead_of_attacking() -> None:
    state = _state(zeny=60, nearby=(_poring(),))
    outcome = FarmScript(_plan()).step(state)
    assert outcome.actions == (MoveTo(x=170, y=378),)


def test_grind_script_field_unchanged_when_zeny_unknown() -> None:
    state = _state(zeny=None, nearby=(_poring(),))
    outcome = GrindScript().step(state)
    assert any(isinstance(a, Attack) for a in outcome.actions)


def test_drive_releases_once_weapon_is_known() -> None:
    state = _state(zeny=60, inventory={"1201": 1}, nearby=(_poring(),))
    outcome = GrindScript().step(state)
    assert any(isinstance(a, Attack) for a in outcome.actions)
    assert not any(isinstance(a, MoveTo) and (a.x, a.y) == (170, 378) for a in outcome.actions)


def test_rest_still_precedes_the_drive() -> None:
    state = _state(zeny=60, hp=2, max_hp=40)
    outcome = GrindScript().step(state)
    assert outcome.actions == (Rest(),)


def test_farm_script_drive_ignores_loot_idle() -> None:
    # No mobs, empty inventory: legacy outcome is keep-farming-active; with
    # the want active the step must move toward the dealer instead.
    state = _state(zeny=60)
    assert FarmScript(_plan()).step(state).actions == (MoveTo(x=170, y=378),)
    assert GrindScript().step(state).actions == (MoveTo(x=170, y=378),)


# --- dealer contact on prt_in ---


def _dealer(id: int = 55, x: int | None = 172, y: int | None = 130) -> ActorRef:
    return ActorRef(id=id, name="Weapon Dealer#prt", kind="npc", distance=1.0, x=x, y=y)


def test_dealer_talk_when_npc_at_dealer_cell() -> None:
    state = _state(map_name="prt_in", x=172, y=129, zeny=60, nearby=(_dealer(),))
    outcome = GrindScript().step(state)
    assert outcome.actions == (TalkToNpc(npc_id=55),)


def test_dealer_walks_when_no_npc_visible() -> None:
    state = _state(map_name="prt_in", x=168, y=128, zeny=60)
    outcome = GrindScript().step(state)
    assert outcome.actions == (MoveTo(x=172, y=130),)


def test_dealer_talk_ignores_positionless_npc() -> None:
    state = _state(map_name="prt_in", x=172, y=129, zeny=60, nearby=(_dealer(x=None, y=None),))
    outcome = GrindScript().step(state)
    assert outcome.actions == (MoveTo(x=172, y=130),)


def test_dealer_talk_ignores_far_npc() -> None:
    state = _state(
        map_name="prt_in",
        x=172,
        y=129,
        zeny=60,
        nearby=(_dealer(id=77, x=150, y=110),),
    )
    outcome = GrindScript().step(state)
    assert outcome.actions == (MoveTo(x=172, y=130),)


# --- sellable-stock drive (window-28 finding: start_zeny is 0) ---


def test_drive_engages_with_sellables_below_zeny_threshold() -> None:
    """The first dealer trip EARNS the zeny: sellable stock (Jellopy 909 /
    Chrysalis 915, the pinned Poring/Pupa drops) fires the drive even with
    zero balance (the owned world pins start_zeny 0)."""
    state = _state(zeny=0, inventory={"909": 3})
    assert merchant_drive_cell(state) == (170, 378)
    state = _state(zeny=0, inventory={"915": 1})
    assert merchant_drive_cell(state) == (170, 378)


def test_no_stock_and_no_zeny_stays_farming() -> None:
    assert merchant_drive_cell(_state(zeny=0, inventory={})) is None


def test_dealer_talk_sends_once_then_holds_for_the_dealtype() -> None:
    """Window-29 finding: re-sending TalkToNpc every evaluation (2254 sends)
    resets the server's npc_shopid before the 0xC4 dealtype can be answered.
    One talk per (bot, npc) contact, then an empty hold while the dialog
    stage machine takes over."""
    scripts.reset_merchant_talk()
    script = GrindScript()
    state = _state(map_name="prt_in", x=172, y=129, zeny=60, nearby=(_dealer(),))
    assert script.step(state).actions == (TalkToNpc(npc_id=55),)
    follow = script.step(_state(map_name="prt_in", x=172, y=129, zeny=60, nearby=(_dealer(),)))
    assert follow.actions == ()
    assert follow.status == ScriptStatus.ACTIVE


def test_dealer_talk_rearms_when_the_npc_leaves_and_returns() -> None:
    scripts.reset_merchant_talk()
    script = GrindScript()
    script.step(_state(map_name="prt_in", x=172, y=129, zeny=60, nearby=(_dealer(),)))
    script.step(_state(map_name="prt_in", x=172, y=129, zeny=60))
    again = script.step(_state(map_name="prt_in", x=172, y=129, zeny=60, nearby=(_dealer(id=99),)))
    assert again.actions == (TalkToNpc(npc_id=99),)


# --- return legs (window 30): a spent bot walks home to the field ---

# Pinned public warp bytes (rathena e985006171d2), npc/warps/cities/prontera.txt:
# :40 ``prt_in,168,124,0  warp  prt05-1  2,1,prontera,174,218`` — the interior
# exit door (mirror of the cited prt05 entry, :25);
# :24 ``prontera,156,22,0  warp  prt001  3,2,prt_fild08,170,375`` — the field
# warp (arrival prt_fild08,170,375, beside the cited outbound leg cell).


def test_return_route_cites_exit_door_and_field_warp_cells() -> None:
    assert MERCHANT_ROUTE_RETURN["prt_in"] == (168, 124)
    assert MERCHANT_ROUTE_RETURN["prontera"] == (156, 22)
    assert "prt_fild08" not in MERCHANT_ROUTE_RETURN


def test_trapped_dealer_interior_state_returns_exit_door() -> None:
    """The exact window-29 trapped shape: Novice in prt_in, empty inventory,
    zeny 0 (start_zeny), no wanted weapon. The drive correctly refuses and
    the return hands the exit door."""
    state = _state(map_name="prt_in", x=172, y=130, zeny=0)
    assert merchant_return_cell(state) == (168, 124)


def test_spent_town_state_returns_field_warp_cell() -> None:
    """The town leg after the exit warp (prt05-1 arrival 174,218): walk to
    the field warp prt001 at 156,22."""
    state = _state(map_name="prontera", x=174, y=218, zeny=0)
    assert merchant_return_cell(state) == (156, 22)


def test_return_never_fires_on_the_field() -> None:
    assert merchant_return_cell(_state(map_name="prt_fild08", zeny=0)) is None


def test_return_released_by_wanted_weapon() -> None:
    """A worn wanted weapon stays in received inventory: it releases the
    drive AND the return."""
    state = _state(map_name="prt_in", x=172, y=130, zeny=0, inventory={"1201": 1})
    assert merchant_return_cell(state) is None
    town = _state(map_name="prontera", x=174, y=218, zeny=0, inventory={"1202": 1})
    assert merchant_return_cell(town) is None


def test_return_fails_closed_on_unknown_map() -> None:
    assert merchant_return_cell(_state(map_name="prt_fild00", zeny=0)) is None


def test_return_fails_closed_when_inventory_unknown() -> None:
    state = _state(map_name="prt_in", x=172, y=130, zeny=0, inventory_known=False)
    assert merchant_return_cell(state) is None


def test_return_stays_down_while_the_drive_holds() -> None:
    """An affordable/stocked bot belongs to the outbound drive, never the
    return (it walks TO the dealer, not away)."""
    assert merchant_return_cell(_state(map_name="prt_in", x=172, y=130, zeny=60)) is None
    stocked = _state(map_name="prt_in", x=172, y=130, zeny=0, inventory={"909": 3})
    assert merchant_return_cell(stocked) is None


def test_trapped_bot_walks_home_from_the_dealer_interior() -> None:
    """Window-30 acceptance: the trapped prt_in bot emits the exit-door
    MoveTo instead of idling under the 60s idle-kick."""
    state = _state(map_name="prt_in", x=172, y=130, zeny=0)
    outcome = GrindScript().step(state)
    assert outcome.status == ScriptStatus.ACTIVE
    assert outcome.actions == (MoveTo(x=168, y=124),)


def test_trapped_bot_walks_the_town_field_warp_leg() -> None:
    state = _state(map_name="prontera", x=174, y=218, zeny=0)
    assert GrindScript().step(state).actions == (MoveTo(x=156, y=22),)
    assert FarmScript(_plan()).step(state).actions == (MoveTo(x=156, y=22),)


def test_farm_script_walks_home_from_the_dealer_interior() -> None:
    state = _state(map_name="prt_in", x=168, y=128, zeny=0)
    outcome = FarmScript(_plan()).step(state)
    assert outcome.actions == (MoveTo(x=168, y=124),)


def test_spent_field_keeps_legacy_behavior() -> None:
    """Guard: on prt_fild08 the spent shape keeps the exact field behavior
    (attack when a mob is visible, never a return/warp MoveTo)."""
    state = _state(zeny=0, nearby=(_poring(),))
    outcome = GrindScript().step(state)
    assert any(isinstance(a, Attack) for a in outcome.actions)
    assert not any(isinstance(a, MoveTo) for a in outcome.actions)


def test_returning_bot_does_not_retalk_the_dealer() -> None:
    """A returning bot walking past the dealer toward the exit door must
    keep walking, never re-open the shop dialog."""
    scripts.reset_merchant_talk()
    script = GrindScript()
    script.step(_state(map_name="prt_in", x=172, y=129, zeny=60, nearby=(_dealer(),)))
    spent = _state(map_name="prt_in", x=172, y=129, zeny=0, nearby=(_dealer(),))
    assert script.step(spent).actions == (MoveTo(x=168, y=124),)


def test_return_ends_the_contact_so_the_next_visit_retalks() -> None:
    """Heading home ends the dealer contact: after a return leg, a fresh
    outbound visit talks to the SAME dealer npc id again (the first visit's
    hold must not stall the sell-and-buy cycle)."""
    scripts.reset_merchant_talk()
    script = GrindScript()
    first = _state(map_name="prt_in", x=172, y=129, zeny=60, nearby=(_dealer(),))
    assert script.step(first).actions == (TalkToNpc(npc_id=55),)
    assert script.step(_state(map_name="prt_in", x=172, y=129, zeny=0)).actions == (
        MoveTo(x=168, y=124),
    )
    back = _state(map_name="prt_in", x=172, y=129, zeny=60, nearby=(_dealer(),))
    assert script.step(back).actions == (TalkToNpc(npc_id=55),)


def test_stale_dealer_latch_clears_when_dealer_absent() -> None:
    """w76: the talk-once latch held forever after the dealer npc actor
    expired from view — the hold requires the dealer received; without it
    the latch is stale and must clear so the walk resumes."""
    state = _state(map_name="prt_in", x=168, y=128, inventory={"915": 1})
    _DEALER_TALKED[state.name] = 110013036  # the stale latch: the dealer actor is gone
    outcome = _merchant_engage(state, (172, 130))
    moves = [a for a in outcome.actions if isinstance(a, MoveTo)]
    assert moves, "a stale latch must resume the dealer walk"
    assert _DEALER_TALKED.get(state.name) is None, "the stale latch must clear"


def test_dealer_match_excludes_the_item_guide_two_cells_away() -> None:
    """w79: the range-2 match captured the Item Guide npc (170,130) for the
    cited dealer cell (172,130) — the talk latched on a dialog that never
    opens and the drive emitted empty actions forever. The match is tight
    (radius 1); the guide must not be a candidate, the walk must resume."""
    state = _state(
        map_name="prt_in",
        x=168,
        y=128,
        inventory={"915": 1},
        nearby=(_dealer(id=110013036, x=170, y=130),),
    )
    _DEALER_TALKED[state.name] = 110013036  # the talk happened AT the guide
    assert (
        _dealer_talk(state, (172, 130)) is None
    ), "the Item Guide 2 cells from the cited cell is not the dealer"


def test_dealer_talk_matches_by_name_not_position() -> None:
    """w80: position matching talked at whatever shop npc stood near the
    cited cell and latched on a dialog that never opens. The dealer is
    identified BY NAME (Weapon Dealer#prt, the rathena npc declaration);
    other shop npcs (Item Guide, Armor Dealer) are never candidates."""
    state = _state(
        map_name="prt_in",
        x=170,
        y=129,
        inventory={"915": 1},
        nearby=(ActorRef(110013036, "Item Guide#knife1201", "npc", 1.4, 170, 130),),
    )
    assert _dealer_talk(state, (172, 130)) is None
    dealer_nearby = (ActorRef(110001762, "Weapon Dealer#prt", "npc", 1.4, 172, 130),)
    state2 = _state(
        map_name="prt_in",
        x=171,
        y=129,  # adjacent (Chebyshev 1): the click is in range
        inventory={"915": 1},
        nearby=dealer_nearby,
    )
    talk = _dealer_talk(state2, (172, 130))
    assert talk is not None
    assert talk.npc_id == 110001762


def test_dealer_talk_requires_adjacency_to_the_agent() -> None:
    """w81 trace: the offer (0xC7) never arrived because the click went out
    at Chebyshev 2-3 — rAthena's npc_click range check rejects it silently
    and the latch held on a shop that never opened. The talk requires the
    agent ADJACENT to the dealer; at distance the drive keeps walking."""
    far = _state(
        map_name="prt_in",
        x=169,
        y=128,  # Chebyshev 3 from the dealer at (172,130)
        inventory={"915": 1},
        nearby=(ActorRef(110001762, "Weapon Dealer#prt", "npc", 3.6, 172, 130),),
    )
    assert _dealer_talk(far, (172, 130)) is None
    near = _state(
        map_name="prt_in",
        x=171,
        y=130,  # adjacent
        inventory={"915": 1},
        nearby=(ActorRef(110001762, "Weapon Dealer#prt", "npc", 1.0, 172, 130),),
    )
    talk = _dealer_talk(near, (172, 130))
    assert talk is not None
    assert talk.npc_id == 110001762


def test_field_loot_species_count_as_sellable_stock() -> None:
    """Leg 39: RinceNyan carried Empty Bottle (713) + Iron Ore (1002) from
    the field and NO sell trip ever engaged - the sellables set only knew
    Jellopy (909) and Chrysalis (915). The pinned mob_db drops of the
    prt_fild08 species are ALL sellable stock (Pupa 1008: Chrysalis/
    Sticky_Mucus/Iron_Ore; Drops 1113: Jellopy/Empty_Bottle; Lunatic 1063:
    Clover/Feather; the leg-38 inventory carried 713+1002)."""
    state = _state(zeny=0, inventory={"713": 2, "1002": 1})
    assert merchant_drive_cell(state) is not None
    state = _state(zeny=0, inventory={"938": 1, "705": 1})
    assert merchant_drive_cell(state) is not None
    state = _state(zeny=0, inventory={"949": 1, "917": 1, "914": 1})
    assert merchant_drive_cell(state) is not None


def test_sell_want_fires_even_with_the_wanted_weapon_held() -> None:
    """Leg 40: the sell trip never engaged because merchant_drive_cell
    RELEASES the whole drive when a wanted weapon is held - and every agent
    has carried the fixture knife (1201) since 2b0f249e. The weapon check
    gates only the BUY arm; sellable stock fires the SELL arm regardless."""
    armed = _state(zeny=0, inventory={"1201": 1, "713": 2, "1002": 1})
    assert merchant_drive_cell(armed) is not None


def test_weapon_alone_still_releases_the_drive() -> None:
    """A knife with NO sellable stock and no zeny: the buy want is satisfied
    and there is nothing to sell - the field behavior stays."""
    armed = _state(zeny=0, inventory={"1201": 1})
    assert merchant_drive_cell(armed) is None
