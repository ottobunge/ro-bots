"""Leg-131 pickup losses: deferred work and party-shared pickup receipts."""

import struct
from pathlib import Path

import pytest

from robots.app.farm_combat import COMBAT_INTENT_SECONDS, CombatIntent
from robots.app.swing_funnel import summarize_swing_traces
from robots.app.trace_log import TraceLog
from robots.domain.actions import Attack, Loot, MoveTo
from robots.domain.model import Goal
from tests.test_loot_attribution import ack
from tests.test_loot_priority import PICKUP, _clocked_client_with_floor_at, walk_ack
from tests.test_native_pose_recovery import pose
from tests.test_playing_runtime import monster
from tests.test_trace_log import make_agent
from tests.test_zc_item_entry_floor import zc_item_entry


@pytest.mark.parametrize("pump", ["drain", "keepalive"])
@pytest.mark.parametrize("source", ["threat", "authored"])
def test_log_only_deferrals_resume_without_another_decision(source, pump):
    client, _ = _clocked_client_with_floor_at(43, 38)
    if source == "threat":
        client.wire.add(monster(aid=560, at=(43, 38)))
    state = client.build_native_state(Goal.GRIND)
    actions = (Attack(560),) if source == "authored" else ()
    client.mechanical_actions(state, actions)
    assert client.wire.sent == []
    if source == "threat":
        client.wire.add(struct.pack("<HIB", 0x80, 560, 0))
    if pump == "drain":
        client.drain_native_events()
    else:
        client._pump_farm_combat_safely()
    assert client.wire.sent == [PICKUP]
    rows = client.loot_telemetry
    assert any(r.get("tap") == "drop_unattempted_reason" for r in rows)
    retried = [r for r in rows if r.get("tap") == "pickup_deferred_retried"]
    assert retried[-1]["deferred_reason"] == source.replace("authored", "authored_action")
    client.drain_native_events()
    assert client.wire.sent == [PICKUP]


def test_queued_approach_holds_farm_roam_budget_until_received_progress():
    client, _ = _clocked_client_with_floor_at(48, 43)
    state = client.build_native_state(Goal.GRIND)
    move = client.mechanical_actions(state, ())
    client.perform_native(move[0])
    state = client.build_native_state(Goal.GRIND)
    assert client.plan_actions(state, (MoveTo(80, 80),)) == ()
    for _ in range(8):
        if client.wire.sent:
            break
        point = client.wire.moves[-1]
        client.wire.add(walk_ack(point, point))
        client.drain_native_events()
    assert client.wire.sent == [PICKUP]


@pytest.mark.parametrize("order", ["take_only", "ack_then_take", "take_then_ack"])
def test_own_received_takeitem_releases_shared_party_ack_lane_once(order):
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.perform_native(Loot())
    take = pose(client.wire.aid, 1, 321)
    if order == "ack_then_take":
        client.wire.add(ack())
        client.build_native_state(Goal.GRIND)
    client.wire.add(take, struct.pack("<HI", 0xA1, 321))
    client.build_native_state(Goal.GRIND)
    if order == "take_then_ack":
        client.wire.add(ack())
        client.build_native_state(Goal.GRIND)
    assert client._loot_receipt.pending is None
    successes = [r for r in client.loot_telemetry if r["outcome"] in ("succeeded", "collected")]
    assert len(successes) == 1
    assert successes[0]["floor_item_id"] == 321
    if order == "take_then_ack":
        assert client.loot_telemetry[-1]["outcome"] == "received"
    if order == "take_only":
        assert not client._loot_stock.active  # collection never invents held inventory
    client.wire.add(zc_item_entry(aid=322, item=705, x=43, y=38))
    client.perform_native(Loot())
    assert client.wire.sent == [PICKUP, struct.pack("<HI", 0x0362, 322)]


def test_peer_takeitem_and_floor_absence_do_not_invent_own_pickup_success():
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.perform_native(Loot())
    client.wire.add(pose(12345, 1, 321), struct.pack("<HI", 0xA1, 321))
    client.build_native_state(Goal.GRIND)
    assert not any(r["outcome"] == "collected" for r in client.loot_telemetry)
    client.wire.add(ack(6))
    client.build_native_state(Goal.GRIND)
    assert client.loot_telemetry[-1]["tap"] == "pickup_race_expired"
    client.perform_native(Loot())
    assert client.wire.sent == [PICKUP]


def test_expired_threat_intent_names_loss_and_cannot_pick_up_reused_floor_id():
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.wire.add(monster(aid=560, at=(43, 38)))
    client.perform_native(Loot())
    client.wire.add(struct.pack("<HI", 0xA1, 321), struct.pack("<HIB", 0x80, 560, 0))
    client.drain_native_events()
    expired = [r for r in client.loot_telemetry if r.get("tap") == "pickup_race_expired"]
    assert expired[-1]["deferred_reason"] == "threat"
    client.wire.add(zc_item_entry(aid=321, item=705, x=43, y=38))
    client.drain_native_events()
    assert client.wire.sent == []


@pytest.mark.parametrize("barrier", ["pending", "rest", "passive", "npc", "threat"])
@pytest.mark.parametrize("pump", ["drain", "keepalive"])
def test_new_deferred_continuations_preserve_runtime_safety(barrier, pump):
    client, _ = _clocked_client_with_floor_at(43, 38)
    state = client.build_native_state(Goal.GRIND)
    client.mechanical_actions(state, (Attack(560),))
    if barrier == "pending":
        client.perform_native(MoveTo(43, 37))
    elif barrier == "rest":
        client._rest_seq = client._metadata_cursor
    elif barrier == "passive":
        client.mechanical_recovery_allowed = False
    elif barrier == "npc":
        client._npc.cancel_uncertain = True
    else:
        client.wire.add(monster(aid=560, at=(43, 38)))
    if pump == "drain":
        client.drain_native_events()
    else:
        client._pump_farm_combat_safely()
    assert PICKUP not in client.wire.sent


def test_receipt_funnel_counts_shared_collection_once_with_late_inventory_ack(tmp_path):

    trace = TraceLog(tmp_path, "Doramir-01")
    agent, _, _ = make_agent(trace, tmp_path)
    client, _ = _clocked_client_with_floor_at(43, 38)
    agent.client = client
    agent.execute_actions((Loot(),))
    client.wire.add(pose(client.wire.aid, 1, 321), struct.pack("<HI", 0xA1, 321))
    agent._trace_state_tick(client.build_native_state(Goal.GRIND))
    client.wire.add(ack())
    agent._trace_state_tick(client.build_native_state(Goal.GRIND))
    trace.close()
    result = summarize_swing_traces(list(tmp_path.glob("*.jsonl")))["agents"]["Doramir-01"]
    assert result["totals"]["pickup_attempts"] == result["totals"]["pickup_success"] == 1


def _mixed_replay(tmp_path: Path) -> dict[str, int | float]:
    """Trace-shaped wire twin; its rates are offline validation, not a live forecast."""

    modes = ("direct", "threat", "authored", "walk", "shared", "refusal", "ownership", "expires")
    for mode in modes:
        trace = TraceLog(tmp_path, mode)
        agent, _, _ = make_agent(trace, tmp_path)
        client, _ = _clocked_client_with_floor_at(43, 38)
        agent.client = client
        if mode in ("threat", "expires"):
            client.wire.add(monster(aid=560, at=(43, 38)))
        elif mode == "ownership":
            client.wire.add(monster(kind=0, aid=200, at=(43, 38)))
        state = client.build_native_state(Goal.GRIND)
        for event in client.drain_native_events():
            agent._trace_event(state, event)
        if mode == "walk":
            client.perform_native(MoveTo(43, 37))
        actions = client.mechanical_actions(state, (Attack(560),) if mode == "authored" else ())
        for action in actions:
            if isinstance(action, Loot):
                client.perform_native(action)
        if mode in ("threat", "expires"):
            client.wire.add(struct.pack("<HIB", 0x80, 560, 0))
        if mode == "expires":
            client.wire.add(struct.pack("<HI", 0xA1, 321))
        if mode == "walk":
            client.wire.add(walk_ack((43, 37), (43, 37)))
        client.drain_native_events()
        if PICKUP in client.wire.sent:
            response = (
                pose(client.wire.aid, 1, 321)
                if mode == "shared"
                else ack(6 if mode == "refusal" else 0)
            )
            client.wire.add(response, struct.pack("<HI", 0xA1, 321))
        agent._trace_state_tick(client.build_native_state(Goal.GRIND))
        trace.close()
    agents = summarize_swing_traces(list(tmp_path.glob("*.jsonl")))["agents"]
    totals = {
        key: sum(a["totals"][key] for a in agents.values())
        for key in ("drops_seen", "pickup_attempts", "pickup_success")
    }
    return {
        **totals,
        "attempt_rate": totals["pickup_attempts"] / totals["drops_seen"],
        "success_rate": totals["pickup_success"] / totals["pickup_attempts"],
    }


def test_mixed_wire_replay_meets_receipt_conversion_bars(tmp_path):
    result = _mixed_replay(tmp_path)
    assert result["drops_seen"] == 8
    assert result["pickup_attempts"] == 6
    assert result["pickup_success"] == 5
    assert result["attempt_rate"] >= 0.60
    assert result["success_rate"] >= 0.70


def test_live_authored_combat_target_holds_host_loot_continuation():

    client, now = _clocked_client_with_floor_at(43, 38)
    state = client.build_native_state(Goal.GRIND)
    client.mechanical_actions(state, (Attack(560),))
    client.wire.add(monster(aid=560, at=(48, 37)))
    client._combat_intent = CombatIntent(560, 1, "prontera", now[0] + COMBAT_INTENT_SECONDS)
    client.drain_native_events()
    assert PICKUP not in client.wire.sent
