"""The sell-arm admission tap (leg 68 defect 1): every refusal names itself.

Leg 68: s00 sealed at pay_fild04 (226,317) 88min, the sell arm NEVER
evaluated (npc_stage/shop_offer None x210, ZERO drive lines) - the
admission (``merchant_drive_cell``) returns None through FIVE silent
gates and the receipt could not tell "evaluated and refused" from "never
reached". The taps name each refusing term (stock / zeny floor / route
map / route resolution / the two precondition gates) with full guard
state, change-only per bot so a whole window of steady-state refusals
logs bounded lines. TAP-ONLY slice: zero admission behavior change -
every term here maps to the exact pre-existing early return.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for candidate in (str(REPO / "src"), str(REPO), str(REPO / "tests")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import pytest  # noqa: E402

from robots.app import scripts  # noqa: E402
from robots.app.scripts import (  # noqa: E402
    _MERCHANT_DRIVE_TAPPED,
    MERCHANT_ROUTE,
    GrindScript,
    ScriptStatus,
    merchant_admission_refusal,
    merchant_drive_cell,
)
from robots.domain.actions import MoveTo  # noqa: E402
from robots.domain.model import BotState, Goal  # noqa: E402


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


@pytest.fixture(autouse=True)
def _fresh_tap_memo():
    scripts.reset_merchant_talk()
    _MERCHANT_DRIVE_TAPPED.clear()
    yield
    scripts.reset_merchant_talk()
    _MERCHANT_DRIVE_TAPPED.clear()


# --- the named terms ---


def test_not_novice_names_itself() -> None:
    verdict = merchant_admission_refusal(_state(job="Swordsman", zeny=60))
    assert verdict is not None
    assert verdict[0] == "not_novice"


def test_inventory_unknown_names_itself() -> None:
    verdict = merchant_admission_refusal(_state(inventory_known=False, zeny=60))
    assert verdict is not None
    assert verdict[0] == "inventory_unknown"


def test_no_stock_below_zeny_floor_names_itself() -> None:
    """No sellable id carried (the worn knife is not stock) and zeny 0 -
    the combined gate fires first and names both sub-facts in its detail."""
    verdict = merchant_admission_refusal(_state(zeny=0, inventory={"1201": 1}))
    assert verdict is not None
    assert verdict[0] == "no_stock_below_zeny_floor"
    assert "has_stock=False" in verdict[1]
    assert "affordable=False" in verdict[1]


def test_weapon_release_names_itself() -> None:
    """Funded but stockless with the wanted weapon carried: the stock gate
    passes on zeny, then the leg-40 weapon hold names itself."""
    verdict = merchant_admission_refusal(_state(zeny=60, inventory={"1201": 1}))
    assert verdict is not None
    assert verdict[0] == "weapon_release"


def test_map_not_on_merchant_route_names_itself() -> None:
    verdict = merchant_admission_refusal(_state(map_name="g00m02", zeny=0, inventory={"511": 2}))
    assert verdict is not None
    assert verdict[0] == "map_not_on_merchant_route"


def test_admit_is_none_and_names_the_sellable_stock_of_s00() -> None:
    """s00's live shape (leg 68): 511x2 carried at zeny 0 on pay_fild04 -
    the stock term admits (the trip EARNS the zeny) and the verdict is the
    pinned payf002 engage cell."""
    state = _state(map_name="pay_fild04", zeny=0, inventory={"511": 2, "1201": 1})
    assert merchant_admission_refusal(state) is None
    assert merchant_drive_cell(state) == MERCHANT_ROUTE["pay_fild04"] == (17, 165)


# --- behavior unchanged: every term still refuses the drive cell ---


def test_drive_cell_refusal_behavior_unchanged() -> None:
    assert merchant_drive_cell(_state(job="Swordsman", zeny=60)) is None
    assert merchant_drive_cell(_state(inventory_known=False, zeny=60)) is None
    assert merchant_drive_cell(_state(zeny=0)) is None
    assert merchant_drive_cell(_state(zeny=0, inventory={"1201": 1})) is None
    assert merchant_drive_cell(_state(map_name="g00m02", zeny=0, inventory={"511": 2})) is None


# --- the tap lines ---


def _merchant_lines(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if "merchant-drive:" in r.getMessage()]


def test_first_evaluation_logs_the_named_verdict_with_guard_state(caplog) -> None:
    with caplog.at_level("WARNING"):
        merchant_drive_cell(_state(map_name="pay_fild04", zeny=0))
    lines = _merchant_lines(caplog)
    assert len(lines) == 1
    assert "no_stock_below_zeny_floor" in lines[0]
    assert "pay_fild04" in lines[0]
    assert "zeny=0" in lines[0]


def test_repeated_same_refusal_does_not_spam(caplog) -> None:
    state = _state(map_name="pay_fild04", zeny=0)
    with caplog.at_level("WARNING"):
        for _ in range(5):
            merchant_drive_cell(state)
    assert len(_merchant_lines(caplog)) == 1


def test_verdict_change_logs_the_new_term(caplog) -> None:
    broke = _state(map_name="pay_fild04", zeny=0)
    funded = _state(map_name="pay_fild04", zeny=60)
    with caplog.at_level("WARNING"):
        merchant_drive_cell(broke)
        merchant_drive_cell(broke)
        merchant_drive_cell(funded)
    lines = _merchant_lines(caplog)
    assert len(lines) == 2
    assert "no_stock_below_zeny_floor" in lines[0]
    assert "admitted" in lines[1]


def test_admit_line_names_the_destination(caplog) -> None:
    with caplog.at_level("WARNING"):
        merchant_drive_cell(_state(map_name="pay_fild04", zeny=60))
    lines = _merchant_lines(caplog)
    assert len(lines) == 1
    assert "admitted" in lines[0]
    assert "(17, 165)" in lines[0]


# --- the route-resolution term ---


def test_route_unresolved_taps_when_no_resolver_leg_exists(caplog) -> None:
    """The drive admitted, the reachability authority says another interior
    component, and the resolver names no usable leg on this map - the step
    used to fall through to a blind engage untapped. Behavior stays exact
    (the blind engage MoveTo); the tap names the unresolved resolution."""
    script = GrindScript(
        travel_resolver=lambda _map, _x, _y: (),
        merchant_reachable=lambda _map, _from, _to: False,
    )
    state = _state(map_name="pay_fild04", zeny=60)
    with caplog.at_level("WARNING"):
        outcome = script.step(state)
    assert outcome.actions == (MoveTo(x=17, y=165),)
    assert outcome.status == ScriptStatus.ACTIVE
    lines = _merchant_lines(caplog)
    assert any("merchant_route_unresolved" in line for line in lines)


def test_resolved_route_leg_walks_without_the_unresolved_tap(caplog) -> None:
    script = GrindScript(
        travel_resolver=lambda _map, _x, _y: (("pay_fild04", 17, 165),),
        merchant_reachable=lambda _map, _from, _to: False,
    )
    state = _state(map_name="pay_fild04", zeny=60, x=200, y=300)
    with caplog.at_level("WARNING"):
        outcome = script.step(state)
    assert outcome.actions == (MoveTo(x=17, y=165),)
    assert not any("merchant_route_unresolved" in line for line in _merchant_lines(caplog))


def test_scripts_logger_is_the_tap_channel() -> None:
    """The runner log is the receipt's tap surface (the loot-debug law):
    the admission taps ride a logger, not print."""
    assert scripts.logger.name.endswith("scripts")
