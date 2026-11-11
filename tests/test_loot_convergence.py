"""Offline wire twin: deferred intent survives arrival without another decide."""

import struct

import pytest

from robots.app.brain import EventDrivenBrain
from robots.app.trace_log import TraceLog
from robots.domain.actions import Loot, MoveTo
from robots.domain.farm import FarmPlan
from robots.domain.model import Goal
from tests.test_loot_attribution import ack
from tests.test_loot_priority import PICKUP, _clocked_client_with_floor_at, walk_ack
from tests.test_native_pose_recovery import pose
from tests.test_playing_runtime import monster
from tests.test_trace_log import make_agent, read_lines
from tests.test_zc_item_entry_floor import zc_item_entry


def test_deferred_pickup_refires_on_received_arrival_without_another_loot():
    client, now = _clocked_client_with_floor_at(44, 39)
    client.perform_native(MoveTo(43, 38))
    client.perform_native(Loot())
    client.wire.add(walk_ack((42, 37), (43, 38)))
    client.drain_native_events()
    assert client.wire.sent == []  # moving destination is never pickup authority
    now[0] += 2
    client.drain_native_events()  # bounded same-cell confirmation after silent completion
    assert client.wire.moves == [(43, 38), (43, 38)]
    client.wire.add(walk_ack((43, 38), (43, 38)))
    client.drain_native_events()
    assert client.wire.sent == [PICKUP]
    rows = client.loot_telemetry
    assert [row["outcome"] for row in rows] == ["deferred", "deferred", "refired", "attempted"]
    assert rows[-2]["reason"] == "loot_refired_after_walk"
    assert len({row["drop_seq"] for row in rows}) == 1
    client.wire.add(ack(6))
    for _ in range(4):
        now[0] += 2
        client.drain_native_events()
    assert client.wire.sent == [PICKUP]  # a real refusal never rearms this epoch


def test_approach_continues_toward_drop_across_more_than_two_received_steps():
    client, _ = _clocked_client_with_floor_at(48, 43)
    client.perform_native(Loot())
    for _ in range(6):
        if client.wire.sent:
            break
        point = client.wire.moves[-1]
        client.wire.add(walk_ack(point, point))
        client.drain_native_events()
    assert client.wire.sent == [PICKUP]
    assert len(client.wire.moves) >= 4
    assert all(x <= 48 and y <= 43 for x, y in client.wire.moves)
    state = client.build_native_state(Goal.GRIND)
    assert max(abs(state.x - 48), abs(state.y - 43)) <= 2


def test_rest_defer_survives_until_recovery_releases_latch():
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.build_native_state(Goal.GRIND)
    client._rest_seq = client._metadata_cursor
    client.perform_native(Loot())
    client.drain_native_events()
    assert not client.wire.sent
    client._rest_seq = None  # the existing recovery owner, never the loot seam
    client.wire.add(pose(kind=3))
    client.drain_native_events()
    assert client.wire.sent == [PICKUP]
    assert client.loot_telemetry[-2]["reason"] == "loot_refired_after_rest"


@pytest.mark.parametrize("replacement", [False, True])
def test_deferred_presence_expiry_is_named_and_does_not_pick_up_reused_id(replacement):
    client, _ = _clocked_client_with_floor_at(44, 39)
    client.perform_native(MoveTo(43, 38))
    client.perform_native(Loot())
    client.wire.add(struct.pack("<HI", 0x00A1, 321))
    if replacement:
        client.wire.add(zc_item_entry(aid=321, x=43, y=38))
    client.wire.add(walk_ack((43, 38), (43, 38)))
    client.drain_native_events()
    client.drain_native_events()
    assert not client.wire.sent
    expired = [row for row in client.loot_telemetry if row["outcome"] == "expired"]
    assert len(expired) == 1
    assert expired[0]["reason"] == "presence_epoch_expired"


def test_approach_silence_does_not_author_unbounded_walks():
    client, now = _clocked_client_with_floor_at(48, 43)
    client.perform_native(Loot())
    for _ in range(10):
        now[0] += 2
        client.drain_native_events()
    assert len(client.wire.moves) <= 2
    assert not client.wire.sent


def test_deferred_arrival_under_threat_waits_until_threat_leaves():
    client, _ = _clocked_client_with_floor_at(44, 39)
    client.perform_native(MoveTo(43, 38))
    client.perform_native(Loot())
    client.wire.add(walk_ack((43, 38), (43, 38)), monster(aid=560, at=(43, 38)))
    client.drain_native_events()
    assert not client.wire.sent
    client.wire.add(struct.pack("<HIB", 0x0080, 560, 0))
    client.drain_native_events()
    assert client.wire.sent == [PICKUP]


def test_map_boundary_expires_deferred_intent_without_rearming_it():
    client, _ = _clocked_client_with_floor_at(44, 39)
    client.perform_native(MoveTo(43, 38))
    client.perform_native(Loot())
    client.wire.add(
        struct.pack("<H16sHH", 0x0091, b"prontera", 42, 37),
        zc_item_entry(aid=321, x=43, y=38),
    )
    client.drain_native_events()
    assert not client.wire.sent
    assert client.loot_telemetry[-1]["outcome"] == "expired"
    assert client.loot_telemetry[-1]["reason"] == "map_changed"


def test_mechanical_approach_resumes_without_another_authored_move():
    client, _ = _clocked_client_with_floor_at(48, 43)
    state = client.build_native_state(Goal.GRIND)
    actions = client.mechanical_actions(state, ())
    assert actions == (MoveTo(48, 43),)
    client.perform_native(actions[0])
    for _ in range(6):
        if client.wire.sent:
            break
        point = client.wire.moves[-1]
        client.wire.add(walk_ack(point, point))
        client.drain_native_events()
    assert client.wire.sent == [PICKUP]


def test_offline_host_traces_arrival_refire_without_a_new_decision(tmp_path):
    trace = TraceLog(tmp_path, "Doramir-01")
    agent, _, _ = make_agent(trace, tmp_path)
    client, _ = _clocked_client_with_floor_at(44, 39)
    agent.client = client
    agent.execute_actions((MoveTo(43, 38), Loot()))
    assert isinstance(agent.brain, EventDrivenBrain)
    agent.brain._plan = FarmPlan(1, "prontera", ("Poring",), 300, 20)
    # Retained farm plans bypass mechanical loot authoring in the live host.
    state = client.build_native_state(Goal.GRIND)
    assert agent._script_actions(state, (MoveTo(80, 80),)) == (MoveTo(80, 80),)
    client.wire.add(walk_ack((43, 38), (43, 38)))
    agent._drain_events()
    agent._trace_state_tick(client.build_native_state(Goal.GRIND))
    assert agent.brain.decision_count == 0
    trace.close()
    rows = [row for row in read_lines(tmp_path, "Doramir-01") if row["kind"] == "loot_performed"]
    assert [row["outcome"] for row in rows] == ["deferred", "refired", "attempted"]
    assert rows[-2]["reason"] == "loot_refired_after_walk"


def test_host_trace_names_both_conversions_when_second_refire_loses_pending(tmp_path):
    trace = TraceLog(tmp_path, "Doramir-01")
    agent, _, _ = make_agent(trace, tmp_path)
    client, _ = _clocked_client_with_floor_at(43, 38)
    agent.client = client
    client.perform_native(Loot())
    client.wire.add(zc_item_entry(aid=322, item=705, x=43, y=38))
    client.perform_native(Loot())  # second drop defers behind the first ack
    client.wire.add(struct.pack("<HI", 0x00A1, 321), ack())
    client.drain_native_events()
    assert len(client.wire.sent) == 2
    assert client.loot_telemetry[-2]["reason"] == "loot_refired_after_ack"
    client._loot_receipt._pending.clear()  # lost lane, retained per-attempt context
    client.wire.add(ack(item=705, index=3))
    agent._trace_state_tick(client.build_native_state(Goal.GRIND))
    agent._trace_state_tick(client.build_native_state(Goal.GRIND))
    trace.close()
    rows = [r for r in read_lines(tmp_path, "Doramir-01") if r["kind"] == "loot_performed"]
    successes = [r for r in rows if r["outcome"] == "succeeded"]
    assert [r["attempt"] for r in successes] == [1, 2]
    assert [r["floor_item_id"] for r in successes] == [321, 322]
    assert [r["received_item_id"] for r in successes] == [909, 705]
    assert successes[-1]["reason"] == "attributed_by_item"
    assert len(client.wire.sent) == 2


def test_boundary_does_not_replay_an_already_consumed_ack():
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.perform_native(Loot())
    client.wire.add(ack())
    client.build_native_state(Goal.GRIND)
    client.wire.add(struct.pack("<H16sHH", 0x0091, b"prontera", 42, 37), ack(6))
    client.build_native_state(Goal.GRIND)
    rows = [r for r in client.loot_telemetry if "ack_seq" in r]
    assert len(rows) == 2
    assert rows[-1]["outcome"] == "unattributed_ack"
    assert len({r["ack_seq"] for r in rows}) == 2


def test_runtime_item_fallback_expires_before_ack_after_same_snapshot_id_reuse():
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.perform_native(Loot())
    client._loot_receipt._pending.clear()
    client.wire.add(struct.pack("<HI", 0x00A1, 321), zc_item_entry(aid=321, x=43, y=38), ack())
    client.build_native_state(Goal.GRIND)
    assert client.loot_telemetry[-1]["outcome"] == "unattributed_ack"
