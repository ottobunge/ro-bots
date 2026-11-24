"""Leg 123: authored field plans and confirmed loot survive slow cognition."""

import struct
from dataclasses import replace

import pytest

from robots.adapters.native_gameplay import attack
from robots.app import scripts
from robots.app.agent_runtime import ScheduledAgent
from robots.domain.actions import Loot, MoveTo, NpcShopSell, Say
from robots.domain.farm import FarmPlan, MobInfo
from robots.domain.model import Goal
from tests.test_city_field_travel import _brain
from tests.test_dealer_ring import _client as dealer_client
from tests.test_farm_combat_pump import _client
from tests.test_loot_attribution import ack
from tests.test_merchant_inflight_loot import client_with_loot
from tests.test_playing_runtime import monster
from tests.test_shop_sell_loop import DEALER, _c4, _c7, _cb, _inv, _weight
from tests.test_zc_item_entry_floor import zc_item_entry


@pytest.fixture(autouse=True)
def fresh_trips():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def test_authored_field_plan_beats_buy_only_trip_and_runs_without_decides(caplog):
    client, wire, now = _client()
    # No monsters in town; an equipped novice still lacks the other wanted knife.
    wire.add(struct.pack("<HIB", 0x80, 123, 0), _inv(((7, 1201, 1),)), _weight())
    client._zeny_seed = 203
    state = client.build_native_state(Goal.GRIND)
    brain = _brain()
    brain.start(state)
    agent = ScheduledAgent.__new__(ScheduledAgent)
    agent.client, agent.brain = client, brain
    agent._sync_farm_travel(state)
    now[0] = 2
    client._pump_farm_combat_safely()  # the keepalive beat; no host tick/decide
    assert wire.moves
    assert wire.moves[-1][1] < state.y  # toward field exit, away from shop
    assert "goal_field_routed" in caplog.text
    assert client.field_travel_actions(state) == (MoveTo(156, 22),)
    # Chat and repeated authoring cannot renew the same plan's wall-clock lease.
    client.perform_native(Say("hi"))
    agent._sync_farm_travel(state)
    now[0] = 301
    assert client.field_travel_actions(state) is None


def test_field_intent_revoked_when_goal_plan_ends():
    client, _wire, _now = _client()
    brain = _brain()
    state = client.build_native_state(Goal.GRIND)
    brain.start(replace(state, nearby=()))
    agent = ScheduledAgent.__new__(ScheduledAgent)
    agent.client, agent.brain = client, brain
    agent._sync_farm_travel(state)
    brain._plan = None
    agent._sync_farm_travel(state)
    assert client.field_travel_actions(state) is None


def test_confirmed_single_loot_admits_live_pump_stock_and_names_receipt(caplog, monkeypatch):
    client = client_with_loot(x=43)
    client.wire.add(_inv(((7, 1201, 1),)), _weight())
    client._zeny_seed = 0
    before = client.build_native_state(Goal.GRIND)
    assert scripts._merchant_stock(before) == 0
    client.perform_native(Loot())
    client.wire.add(ack(0))
    client._observe()  # receipt consumer advanced, cached BotState still predates ACK
    captured = []
    monkeypatch.setattr(
        client, "_advance_admitted_trip", lambda state, _tracker: captured.append(state)
    )
    client._advance_merchant_approach_on_tick()
    assert captured
    state = captured[-1]
    assert scripts._merchant_stock(state) == 1
    assert scripts.merchant_admission_refusal(state) is None
    assert "stock_admission_fired" in caplog.text
    assert "ack_seq=" in caplog.text
    # A received deletion revokes credit; a repeated snapshot never duplicates it.
    client.wire.add(struct.pack("<HHH", 0xAF, 2, 1))
    state = client.build_native_state(Goal.GRIND)
    assert scripts._merchant_stock(state) == 0
    refusal = scripts.merchant_admission_refusal(state)
    assert refusal is not None
    assert refusal[0] == "no_stock_below_zeny_floor"


def test_field_arrival_authors_attack_from_retained_plan_without_decide():
    client, wire, now = _client()
    state = client.build_native_state(Goal.GRIND)
    brain = _brain()
    client.mob_db.catalog[1002] = MobInfo(1002, "Poring", 1)
    brain._spawn_species = lambda map_name: ("Poring",) if map_name == "prt_fild08" else ()
    brain.start(replace(state, nearby=()))
    agent = ScheduledAgent.__new__(ScheduledAgent)
    agent.client, agent.brain = client, brain
    agent._sync_farm_travel(state)
    wire.add(struct.pack("<H16sHH", 0x91, b"prt_fild08", 42, 37))

    wire.add(monster(at=(43, 37)))
    now[0] = 2
    client._pump_farm_combat_safely()

    assert attack(123) in wire.sent


def test_field_arrival_pump_retargets_expless_plan_without_decide():
    client, wire, now = _client()
    state = client.build_native_state(Goal.GRIND)
    brain = _brain()
    planner = brain._field_travel
    assert planner is not None
    client.mob_db.catalog[1002] = MobInfo(1002, "Green Plant", 1, base_exp=0, job_exp=0)
    client.mob_db.catalog[1003] = MobInfo(1003, "Poring", 1, base_exp=2, job_exp=1)
    plan = FarmPlan(1, "prt_fild08", ("Green Plant",), 900, 1)
    client.authorize_field_travel(state, (plan, planner))
    poring = bytearray(monster(aid=456, at=(43, 37)))
    struct.pack_into("<H", poring, 23, 1003)
    wire.add(
        struct.pack("<H16sHH", 0x91, b"prt_fild08", 42, 37),
        monster(at=(43, 37)),
        bytes(poring),
    )
    now[0] = 2
    client._pump_farm_combat_safely()
    assert attack(456) in wire.sent
    assert attack(123) not in wire.sent


def test_field_pump_retarget_approach_revokes_previous_plant_swings():
    client, wire, now = _client()
    state = client.build_native_state(Goal.GRIND)
    planner = _brain()._field_travel
    assert planner is not None
    client.mob_db.catalog[1002] = MobInfo(1002, "Green Plant", 1, base_exp=0, job_exp=0)
    client.mob_db.catalog[1003] = MobInfo(1003, "Poring", 1, base_exp=2, job_exp=1)
    client.authorize_field_travel(
        state, (FarmPlan(1, "prt_fild08", ("Green Plant",), 900, 1), planner)
    )
    wire.add(struct.pack("<H16sHH", 0x91, b"prt_fild08", 42, 37), monster(at=(43, 37)))
    now[0] = 2
    client._pump_farm_combat_safely()
    assert wire.sent.count(attack(123)) == 1
    poring = bytearray(monster(aid=456, at=(47, 37)))
    struct.pack_into("<H", poring, 23, 1003)
    wire.add(bytes(poring))
    now[0] = 4
    client._pump_farm_combat_safely()
    assert wire.sent.count(attack(123)) == 1
    assert client._combat_intent is not None
    assert client._combat_intent.target_id == 456


@pytest.mark.parametrize(
    "barrier", ["rest", "dead", "low_hp", "disabled", "epoch", "reverse", "expired"]
)
def test_field_pump_yields_at_runtime_boundaries(barrier):
    client, wire, now = _client()
    state = client.build_native_state(Goal.GRIND)
    brain = _brain()
    brain.start(replace(state, nearby=()))
    agent = ScheduledAgent.__new__(ScheduledAgent)
    agent.client, agent.brain = client, brain
    agent._sync_farm_travel(state)
    now[0] = 2
    if barrier == "rest":
        client._rest_seq = 1
    elif barrier == "dead":
        wire.add(struct.pack("<HIB", 0x80, wire.aid, 1))
    elif barrier == "low_hp":
        wire.status_params[5] = 1
    elif barrier == "disabled":
        client.mechanical_recovery_allowed = False
    elif barrier == "epoch":
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    elif barrier == "reverse":
        now[0] = -1
    else:
        now[0] = 300
    client._pump_farm_combat_safely()
    assert not wire.moves


def test_new_loot_converts_through_received_dealer_sale():

    client, _now = dealer_client(at=(171, 129))
    client._zeny_seed = 0
    client.wire.add(
        struct.pack("<HHH", 0xAF, 6, 1),
        _inv(((7, 1201, 1),)),
        zc_item_entry(aid=321, item=909, x=171, y=129),
    )
    client.perform_native(Loot())
    client.wire.add(ack(0))
    state = client.build_native_state(Goal.GRIND)
    assert state.merchant_loot_stock == 1
    outcome = scripts._merchant_step(state)
    assert outcome is not None
    client.perform_native(outcome.actions[0])
    client.wire.add(_c4(DEALER))
    state = client.build_native_state(Goal.GRIND)
    client.perform_native(client.mechanical_actions(state, ())[0])
    client.wire.add(_c7(((2, 3, 3),)))
    state = client.build_native_state(Goal.GRIND)
    sale = client.mechanical_actions(state, ())[0]
    assert isinstance(sale, NpcShopSell)
    assert sale.sales == ((2, 1),)
    client.perform_native(sale)
    client.wire.add(_cb(0), struct.pack("<HHH", 0xAF, 2, 1), struct.pack("<HHi", 0xB1, 20, 3))
    state = client.build_native_state(Goal.GRIND)
    assert state.zeny == 3
    assert state.merchant_loot_stock == 0
    assert scripts._merchant_stock(state) == 0


def test_confirmed_loot_sell_continues_on_keepalive_without_host_steps():
    client, now = dealer_client(at=(171, 129))
    client._zeny_seed = 0
    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1), zc_item_entry(aid=321, item=909, x=171, y=129))
    client.perform_native(Loot())
    client.wire.add(ack(0))
    client._pump_farm_combat_safely()
    assert any(frame[:2] == struct.pack("<H", 0x90) for frame in client.wire.sent)
    client.wire.add(_c4(DEALER))
    now[0] += 2
    client._pump_farm_combat_safely()
    assert client.wire.sent[-1] == struct.pack("<HIB", 0xC5, DEALER, 1)
    client.wire.add(_c7(((2, 3, 3),)))
    now[0] += 2
    client._pump_farm_combat_safely()
    assert client.wire.sent[-1] == struct.pack("<HHHH", 0xC9, 8, 2, 1)


@pytest.mark.parametrize("boundary", ["expired", "reverse", "unknown", "epoch", "replaced"])
def test_pickup_batch_credit_requires_current_bounded_inventory(boundary):
    client = client_with_loot(x=43)
    now = [100.0]
    client._now = lambda: now[0]
    client._zeny_seed = 0
    client.wire.add(_inv(((7, 1201, 1),)), _weight())
    client.perform_native(Loot())
    client.wire.add(ack(0))
    state = client.build_native_state(Goal.GRIND)
    assert state.merchant_loot_stock == 1
    assert client.build_native_state(Goal.GRIND).merchant_loot_stock == 1
    if boundary == "expired":
        now[0] += 900
    elif boundary == "reverse":
        now[0] -= 1
    elif boundary == "unknown":
        tracker = client._tracker
        assert tracker is not None
        tracker._inventory_known = False
    elif boundary == "epoch":
        client.wire.native_epoch = client.wire.selection_epoch = client.wire.map_epoch = 2
    else:
        client.wire.add(_inv(((2, 1202, 1),)))
    state = client.build_native_state(Goal.GRIND)
    assert state.merchant_loot_stock == 0


@pytest.mark.parametrize("result", [0, 1, 6])
def test_unsolicited_or_refused_ack_cannot_grant_small_batch_admission(result, caplog):
    client = client_with_loot(x=43)
    client._zeny_seed = 0
    client.wire.add(_inv(((7, 1201, 1),)), _weight(), struct.pack("<HI", 0xA1, 321), ack(result))
    state = client.build_native_state(Goal.GRIND)
    assert state.merchant_loot_stock == 0
    assert scripts.merchant_admission_refusal(state) is not None
    assert "stock_admission_fired" not in caplog.text
