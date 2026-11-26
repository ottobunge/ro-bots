"""Receipt-only fleet conversion: ceded/consumed floor identities need proof."""

import json
import struct
from pathlib import Path
from typing import Any

import pytest

from robots.app.swing_funnel import summarize_swing_traces
from robots.app.trace_log import TraceLog
from robots.domain.actions import Loot
from robots.domain.model import Goal
from tests.test_loot_attribution import ack
from tests.test_loot_priority import _clocked_client_with_floor_at
from tests.test_native_pose_recovery import pose
from tests.test_playing_runtime import monster
from tests.test_swing_funnel import event, write_trace
from tests.test_trace_log import make_agent


def drop(fid: int = 321, **fields: Any) -> dict[str, Any]:
    return {
        "kind": "world_event",
        "event": "ItemDrop",
        "floor_item_id": fid,
        "map": "field",
        "x": 10,
        "y": 10,
        "x_event": 10,
        "y_event": 11,
        **fields,
    }


def loot(outcome: str, **fields: Any) -> dict[str, Any]:
    return {
        "kind": "loot_performed",
        "map": "field",
        "floor_item_id": 321,
        "drop_seq": 1,
        "drop_x": 10,
        "drop_y": 11,
        "outcome": outcome,
        **fields,
    }


def proof(source: str) -> dict[str, Any]:
    if source == "animation":
        return {
            **event("damage", target_id=321, source_id=222, own_id=111, damage_type=1, damage=0),
            "map": "field",
        }
    return loot("succeeded" if source == "ack" else "collected", persona="peer")


@pytest.mark.parametrize("source", ["ack", "take", "animation"])
@pytest.mark.parametrize("reason", ["nearer_agent", "pending_walk"])
def test_confirmed_cede_or_consumed_drop_converts_only_fleet(tmp_path, source, reason):
    rows = [
        drop(),
        loot("deferred", reason=reason),
        proof(source),
        loot("expired", reason="presence_epoch_expired", deferred_reason=reason),
    ]
    result = summarize_swing_traces([write_trace(tmp_path, rows)])
    pickup = result["agents"]["solo"]["pickup"]
    assert pickup["agent_attempted"]["attempted"] == 0
    assert pickup["agent_attempted"]["success_rate"] is None
    assert pickup["fleet_attempted"] == {
        "attempted": 1,
        "success": 1,
        "attempt_rate": 1.0,
        "success_rate": 1.0,
    }
    assert pickup["converted_drops"][0]["floor_item_id"] == 321
    assert pickup["converted_drops"][0]["tap"] == "pickup_fleet_converted"
    assert pickup["converted_drops"][0]["reason"] == (
        "nearer_agent" if reason == "nearer_agent" else "peer_consumed"
    )


@pytest.mark.parametrize("unmatched", ["absent", "wrong_id", "wrong_map", "late", "refusal"])
def test_cede_and_expiry_require_matching_collection_evidence(tmp_path, unmatched):
    evidence = proof("ack")
    if unmatched == "wrong_id":
        evidence["floor_item_id"] = 322
    elif unmatched == "wrong_map":
        evidence["map"] = "other"
    elif unmatched == "late":
        evidence["t"] = "2026-11-12T18:32:00+00:00"
    elif unmatched == "refusal":
        evidence["outcome"] = "refused-by-server"
    rows = [
        drop(),
        loot("deferred", reason="nearer_agent"),
        loot("expired", reason="presence_epoch_expired"),
    ]
    if unmatched != "absent":
        rows.append(evidence)
    result = summarize_swing_traces([write_trace(tmp_path, rows)])["pickup"]
    assert result["fleet_attempted"]["attempted"] == 0
    assert result["converted_drops"] == []


def test_proofs_and_duplicate_cedes_do_not_double_count_or_credit_far_drops(tmp_path):
    rows = [
        drop(),
        drop(322, x_event=20),
        loot("deferred", reason="nearer_agent"),
        loot("deferred", reason="nearer_agent"),
        loot("deferred", floor_item_id=322, drop_x=20, reason="nearer_agent"),
        proof("ack"),
        proof("take"),
        proof("animation"),
        loot("succeeded", persona="peer", floor_item_id=322, drop_x=20),
    ]
    result = summarize_swing_traces([write_trace(tmp_path, rows)])["agents"]["solo"]["pickup"]
    assert result["fleet_attempted"]["attempted"] == 1
    assert len(result["converted_drops"]) == 1


def test_peer_winning_attempted_race_only_changes_fleet_success(tmp_path):
    rows = [drop(), loot("attempted"), loot("refused-by-server"), proof("animation")]
    pickup = summarize_swing_traces([write_trace(tmp_path, rows)])["pickup"]
    assert pickup["agent_attempted"]["attempted"] == 1
    assert pickup["agent_attempted"]["success"] == 0
    assert pickup["fleet_attempted"]["attempted"] == 1
    assert pickup["fleet_attempted"]["success"] == 1


def test_reused_floor_id_and_new_presence_cannot_borrow_old_proof(tmp_path):
    rows = [
        drop(),
        loot("deferred", reason="nearer_agent"),
        proof("animation"),
        loot("expired", reason="presence_epoch_expired"),
        drop(x_event=11),
        loot("deferred", reason="nearer_agent", drop_seq=10, drop_x=11),
        loot("expired", reason="presence_epoch_expired", drop_seq=10, drop_x=11),
    ]
    pickup = summarize_swing_traces([write_trace(tmp_path, rows)])["pickup"]
    assert pickup["drops_seen"] == 2
    assert pickup["fleet_attempted"]["attempted"] == 1
    assert len(pickup["converted_drops"]) == 1


def test_window_does_not_borrow_post_close_peer_success(tmp_path):
    rows = [drop(), loot("deferred", reason="nearer_agent"), proof("ack")]
    pickup = summarize_swing_traces([write_trace(tmp_path, rows)], end="2026-11-12T18:30:02+00:00")[
        "pickup"
    ]
    assert pickup["fleet_attempted"]["attempted"] == 0


@pytest.mark.parametrize("response", ["ack", "animation"])
def test_live_receipt_path_preserves_nearest_agent_ownership(tmp_path, response):
    trace = TraceLog(tmp_path, "solo")
    agent, _, _ = make_agent(trace, tmp_path)
    client, _ = _clocked_client_with_floor_at(43, 38)
    agent.client = client
    client.wire.add(monster(kind=0, aid=200, at=(43, 38)))
    state = client.build_native_state(Goal.GRIND)
    for observed in client.drain_native_events():
        agent._trace_event(state, observed)
    agent.execute_actions((Loot(),))
    assert client.wire.sent == []
    if response == "ack":
        # A peer's own 0x0A37 is attributed by its existing single-send lane.
        peer_trace = TraceLog(tmp_path, "peer")
        peer, _, _ = make_agent(peer_trace, tmp_path)
        peer_client, _ = _clocked_client_with_floor_at(43, 38)
        peer.client = peer_client
        peer.execute_actions((Loot(),))
        peer_client.wire.add(ack())
        peer._trace_state_tick(peer_client.build_native_state(Goal.GRIND))
        peer_trace.close()
    else:
        client.wire.add(pose(200, 1, 321))
    client.wire.add(struct.pack("<HI", 0xA1, 321))
    agent._trace_state_tick(client.build_native_state(Goal.GRIND))
    trace.close()
    result = summarize_swing_traces(list(tmp_path.glob("*.jsonl")))["agents"]["solo"]
    assert result["totals"]["pickup_success"] == 0
    assert result["pickup"]["fleet_attempted"]["success"] == 1
    assert client.wire.sent == []
    assert not client._loot_stock.active


def test_leg132_receipt_shape_replay_meets_fleet_attempt_bar(tmp_path):
    fixture = Path(__file__).parent / "fixtures" / "leg132_pickup.jsonl"
    rows = [json.loads(line) for line in fixture.read_text().splitlines()]
    result = summarize_swing_traces([write_trace(tmp_path, rows)])["pickup"]
    assert result["drops_seen"] == 51
    assert result["agent_attempted"] == {
        "attempted": 23,
        "success": 19,
        "attempt_rate": 23 / 51,
        "success_rate": 19 / 23,
    }
    assert result["fleet_attempted"] == {
        "attempted": 38,
        "success": 37,
        "attempt_rate": 38 / 51,
        "success_rate": 37 / 38,
    }
    assert result["fleet_attempted"]["attempt_rate"] >= 0.70
    assert len(result["converted_drops"]) == 18


def test_successful_own_lane_after_cede_stays_one_success(tmp_path):
    rows = [
        drop(),
        loot("deferred", reason="nearer_agent"),
        loot("attempted"),
        loot("collected"),
        loot("received"),
        proof("animation"),
    ]
    pickup = summarize_swing_traces([write_trace(tmp_path, rows)])["pickup"]
    assert pickup["fleet_attempted"] == pickup["agent_attempted"]
    assert pickup["fleet_attempted"]["success"] == 1
    assert pickup["converted_drops"] == []


def test_new_sessions_can_reuse_floor_id_and_drop_sequence(tmp_path):
    rows = []
    for session in ("first", "second"):
        rows.extend(
            [
                event("session", session=session),
                drop(),
                loot("deferred", reason="nearer_agent"),
                proof("animation"),
                loot("expired", reason="presence_epoch_expired"),
            ]
        )
    pickup = summarize_swing_traces([write_trace(tmp_path, rows)])["pickup"]
    assert pickup["drops_seen"] == pickup["fleet_attempted"]["attempted"] == 2
    assert pickup["fleet_attempted"]["success"] == 2


def test_empty_trace_has_explicit_unknown_rates():
    pickup = summarize_swing_traces([])["pickup"]
    assert pickup["drops_seen"] == 0
    assert pickup["agent_attempted"] == pickup["fleet_attempted"]
    assert pickup["fleet_attempted"]["attempt_rate"] is None
    assert pickup["fleet_attempted"]["success_rate"] is None


def test_reused_presence_cannot_borrow_previous_nearby_sighting(tmp_path):
    rows = [
        drop(),
        loot("deferred", reason="nearer_agent"),
        proof("animation"),
        loot("expired", reason="presence_epoch_expired"),
        # Same floor ID/cell, but no nearby sighting of the new presence.
        loot("deferred", reason="nearer_agent", drop_seq=10),
        {**proof("animation"), "sequence": 11},
        loot("expired", reason="presence_epoch_expired", drop_seq=10),
    ]
    pickup = summarize_swing_traces([write_trace(tmp_path, rows)])["pickup"]
    assert pickup["drops_seen"] == pickup["fleet_attempted"]["attempted"] == 1
    assert pickup["fleet_attempted"]["success"] == 1


def test_legacy_drop_without_floor_identity_keeps_agent_counts(tmp_path):
    row = drop()
    del row["floor_item_id"]
    pickup = summarize_swing_traces([write_trace(tmp_path, [row])])["pickup"]
    assert pickup["drops_seen"] == 1
    assert pickup["fleet_attempted"]["attempted"] == 0
