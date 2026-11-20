"""Leg 118: received drops own pickup, misc stock admits, trips return to farm."""

import struct
import threading
from dataclasses import replace

import pytest

from robots.adapters.merchant_stock import public_stock_ids
from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import scripts
from robots.app.brain import EventDrivenBrain
from robots.app.scripts import FarmScript
from robots.domain.actions import Attack, GameAction, Loot, MoveTo, NpcShopSell, NpcShopSellOpen
from robots.domain.farm import FarmPlan
from robots.domain.model import ActorRef, Goal
from tests.test_dealer_ring import _client
from tests.test_loot_priority import PICKUP
from tests.test_merchant_drive import _plan, _state
from tests.test_merchant_inflight_loot import client_with_loot
from tests.test_playing_runtime import monster
from tests.test_sell_drive_rearm import _s00_brain
from tests.test_shop_sell_loop import DEALER, _c4, _c7, _cb, _inv
from tests.test_trace_log import make_agent
from tests.test_zc_item_entry_floor import zc_item_entry


@pytest.fixture(autouse=True)
def _fresh_contacts():
    scripts.reset_merchant_talk()
    scripts._MERCHANT_DRIVE_TAPPED.clear()
    yield
    scripts.reset_merchant_talk()


def test_retained_empty_bag_plan_dispatches_received_drop(tmp_path, caplog):
    agent, _, _ = make_agent(None, tmp_path)
    client = client_with_loot(x=43)
    client.wire.add(_inv(((7, 1201, 1),)))
    client._zeny_seed = 0
    agent.client = client
    assert isinstance(agent.brain, EventDrivenBrain)
    agent.brain._plan = FarmPlan(1, "prt_fild08", ("Poring",), 300, 20)
    state = agent.build_state()
    assert state.merchant_inflight_visible == 1  # undersized batch cannot travel
    assert scripts.merchant_drive_cell(state) is None
    actions = agent._script_actions(state, (MoveTo(60, 60),))
    assert actions == (Loot(),)
    agent.execute_actions(actions)
    assert client.wire.sent == [PICKUP]
    assert "loot_arm_dispatched" in caplog.text


def test_no_stock_pickup_beats_active_buy_trip_and_pump(caplog):
    client = client_with_loot(x=43, item=1201)
    client.wire.add(_inv(()))
    client._zeny_seed = 80
    client._keepalive_thread = threading.current_thread()
    client.wire.keepalive = lambda: None
    state = client.build_native_state(Goal.GRIND)
    assert scripts._merchant_trip_allows(state, scripts.MERCHANT_ROUTE[state.map_name])
    client.drain_native_events()
    assert client.wire.moves == []
    state = client.build_native_state(Goal.GRIND)
    actions = client.mechanical_actions(state, (MoveTo(60, 60),))
    assert actions == (Loot(),)
    client.perform_native(actions[0])
    assert client.wire.sent == [PICKUP]
    assert "stage=approach reasons=pickup_required" in caplog.text


@pytest.mark.parametrize("item", [713, 915, 705, 711, 515])
def test_misc_admits_opens_and_sells_only_received_c7_rows(item, caplog):
    client, _ = _client(at=(171, 129))
    client._zeny_seed = 0
    client.wire.add(_inv(((6, item, 2), (7, 1201, 1))))
    state = client.build_native_state(Goal.GRIND)
    assert scripts.merchant_drive_cell(state) is not None
    assert f"merchant_stock_sellable_misc={item != 515}" in caplog.text
    # No C7 means no sale. Received dealer C4 can request its sell list.
    outcome = scripts._merchant_step(state)
    assert outcome is not None
    client.perform_native(outcome.actions[0])
    client.wire.add(_c4(DEALER))
    state = client.build_native_state(Goal.GRIND)
    actions = client.mechanical_actions(state, ())
    assert len(actions) == 1
    assert isinstance(actions[0], NpcShopSellOpen)
    client.perform_native(actions[0])
    client.wire.add(_c7(((6, 7, 9),)))  # received price, unrelated to public value
    state = client.build_native_state(Goal.GRIND)
    actions = client.mechanical_actions(state, ())
    assert len(actions) == 1
    assert isinstance(actions[0], NpcShopSell)
    assert actions[0].sales == ((6, 2),)
    client.perform_native(actions[0])
    assert client.wire.sent[-1] == struct.pack("<HHHH", 0xC9, 8, 6, 2)
    client.wire.add(_cb(0), struct.pack("<HHH", 0xAF, 6, 2))
    state = client.build_native_state(Goal.FARM_ITEM)
    assert state.merchant_returning
    assert scripts.merchant_drive_cell(state) is None
    assert "farm_arm_rearmed_post_trip" in caplog.text
    assert client.cache is not None
    client.cache = MapCache(
        (client.cache.get("prt_in"), WalkMap("prt_fild08", 200, 200, bytes(40000)))
    )
    client.wire.add(struct.pack("<H16sHH", 0x91, b"prt_fild08", 42, 37))
    state = client.build_native_state(Goal.FARM_ITEM)
    assert not state.merchant_returning
    assert scripts.merchant_arm_drained(state)
    # Received new stock funds the next trip after the farmer's return.
    client.wire.add(_inv(((6, item, 2), (7, 1201, 1))))
    assert scripts.merchant_drive_cell(client.build_native_state(Goal.FARM_ITEM)) is not None


def test_nosell_misc_and_wanted_weapon_do_not_admit():
    state = _state(inventory={"6000": 2, "1201": 1}, zeny=0)
    assert scripts.merchant_drive_cell(state) is None


def test_no_progress_cooldown_returns_immediately_then_farms(monkeypatch, caplog):
    now = [0.0]
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    state = _state(map_name="prontera", inventory={"909": 2, "1201": 1}, zeny=0)
    assert scripts._merchant_step(state) is not None
    trip = scripts._MERCHANT_TRIPS[state.name]
    now[0] = trip.no_progress_bound
    scripts._merchant_step(state)  # releases the failed outbound trip
    now[0] += 6
    outcome = scripts._merchant_step(state)
    assert outcome is not None
    assert outcome.actions == (MoveTo(*scripts.MERCHANT_ROUTE_RETURN["prontera"]),)
    field = replace(
        state, map_name="prt_fild08", nearby=(ActorRef(123, "Poring", "monster", 1, 171, 300),)
    )
    # Before the retry rate limit expires, a retained farm script owns combat.
    now[0] = trip.retry_at - 1
    brain = _s00_brain()
    brain._script = FarmScript(_plan())
    assert any(isinstance(a, Attack) for a in brain.step_script(field).actions)
    assert "farm_arm_rearmed_post_trip" in caplog.text
    now[0] = trip.retry_at + 300
    actions: list[GameAction] = []
    for _ in range(6):  # existing five-tick walk reaffirmation remains bounded
        outcome = scripts._merchant_step(state)
        assert outcome is not None
        actions.extend(outcome.actions)
    assert actions
    assert all(a == MoveTo(*scripts.MERCHANT_ROUTE_RETURN["prontera"]) for a in actions)


@pytest.mark.parametrize("reason", ["completed", "failed"])
def test_counter_trip_end_returns_even_with_stock_and_buy_budget(reason, caplog):
    client, _ = _client(at=(169, 126))
    client._zeny_seed = 80
    state = client.build_native_state(Goal.GRIND)
    client._counter_lease.reason = reason
    assert client.shop_actions(state, ()) == (MoveTo(*scripts.MERCHANT_ROUTE_RETURN["prt_in"]),)
    state = client.build_native_state(Goal.GRIND)
    assert state.merchant_returning
    assert scripts.merchant_drive_cell(state) is None
    outcome = scripts._merchant_step(state)
    assert outcome is not None
    assert outcome.actions == (MoveTo(*scripts.MERCHANT_ROUTE_RETURN["prt_in"]),)
    assert "farm_arm_rearmed_post_trip" in caplog.text


@pytest.mark.parametrize("nearer", [True, False])
def test_only_nearest_received_agent_picks_up(nearer, caplog):
    client = client_with_loot(x=43)
    client.wire.aid = 100
    client.wire.add(monster(kind=0, aid=200, at=(43, 38) if nearer else (50, 50)))
    state = client.build_native_state(Goal.FARM_ITEM)
    assert state.occupied_cells
    actions = client.plan_actions(state, ())
    assert (actions == (Loot(),)) == (not nearer)
    client.perform_native(Loot())  # send seam independently checks ownership
    assert (PICKUP in client.wire.sent) == (not nearer)
    if nearer:
        assert "nearer_agent" in caplog.text


@pytest.mark.parametrize("barrier", ["poison", "cancel", "passive", "rest", "pending", "threat"])
def test_retained_plan_loot_preserves_runtime_barriers(barrier):
    client = client_with_loot(x=43)
    state = client.build_native_state(Goal.FARM_ITEM)
    if barrier == "poison":
        client._npc._deny("send_failure")
    elif barrier == "cancel":
        client._npc.cancel_uncertain = True
    elif barrier == "passive":
        client.mechanical_recovery_allowed = False
    elif barrier == "rest":
        client._rest_seq = 0
    elif barrier == "pending":
        client._pending = ((43, 38), 100, client._now(), 0)
    else:
        client.wire.add(monster(kind=5, aid=555, at=(43, 38)))
        state = client.build_native_state(Goal.FARM_ITEM)
    assert client.plan_actions(state, ()) != (Loot(),)
    client.perform_native(Loot())
    assert PICKUP not in client.wire.sent


def test_public_misc_loader_excludes_nosell_and_negative_value(tmp_path):
    source = tmp_path / "misc.yml"
    assert public_stock_ids(source) == frozenset()
    source.write_text(
        "Body:\n"
        "  - {Id: 1, Type: Etc}\n"
        "  - {Id: 2, Type: Card}\n"
        "  - {Id: 3, Type: Etc, Trade: {NoSell: true}}\n"
        "  - {Id: 4, Type: Etc, Sell: -1}\n"
        "  - {Id: 5, Type: Weapon}\n"
    )
    assert public_stock_ids(source) == frozenset({1, 2})


def test_post_trip_return_keeps_collectible_inflight_pickup_leg():
    client, _ = _client(at=(169, 126))
    client._zeny_seed = 0
    client.wire.add(
        struct.pack("<HHH", 0xAF, 6, 1),
        zc_item_entry(aid=321, item=713, x=169, y=132),
    )
    client.perform_native(Loot())  # explicit unattempted intent, on our received floor
    state = client.build_native_state(Goal.FARM_ITEM)
    assert scripts.merchant_pickup_required(state)
    client._counter_lease.reason = "completed"
    actions = client.plan_actions(state, ())
    assert len(actions) == 1
    assert isinstance(actions[0], MoveTo)
    assert actions[0].y > state.y  # toward credited loot, away from the return door
    assert not client._merchant_returning
