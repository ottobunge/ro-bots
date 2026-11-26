"""Leg-133 reason evidence and the difference between a cohort and a residual."""

from pathlib import Path
from typing import Any

import pytest

from robots.app.loot_attribution import LootAttribution
from robots.app.swing_funnel import summarize_swing_traces
from robots.domain.model import Goal
from tests.test_fleet_pickup_denominator import drop, loot, proof
from tests.test_loot_priority import _clocked_client_with_floor_at
from tests.test_swing_funnel import event, write_trace


def coverage(tmp_path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = summarize_swing_traces([write_trace(tmp_path, rows)])["pickup"][
        "drop_coverage"
    ]
    return result


@pytest.mark.parametrize(
    ("rows", "reason"),
    [
        ([drop(), loot("deferred", reason="out_of_range")], "out_of_approach_range_owned"),
        ([drop(map_event="other.gat")], "map_transition_blindness"),
        ([loot("expired", reason="presence_epoch_expired"), drop()], "despawn_before_observation"),
        ([drop()], "unknown"),
        ([drop(), loot("deferred", reason="threat")], "unknown"),
    ],
)
def test_uncovered_sighting_requires_positive_reason_evidence(tmp_path, rows, reason):
    result = coverage(tmp_path, rows)
    assert result["unattempted_reason_counts"][reason] == 1
    assert result["unattempted_drops"][0]["reason_class"] == reason
    assert sum(result["unattempted_reason_counts"].values()) == 1


def test_far_timeout_requires_an_explicit_timeout_receipt(tmp_path):
    # Ordinary far visibility or a bare disappearance cannot prove spawn timeout.
    rows = [drop(), loot("expired", reason="spawn_timeout", drop_x=10, drop_y=11)]
    result = coverage(tmp_path, rows)
    assert result["unattempted_reason_counts"]["spawn_timeout_far_kill"] == 1


def test_later_combat_gate_does_not_indict_an_earlier_approach(tmp_path):
    rows = [drop(), loot("deferred", reason="out_of_range"), loot("deferred", reason="threat")]
    result = coverage(tmp_path, rows)
    lost = result["unattempted_drops"][0]
    assert lost["reason_class"] == "unknown"
    assert lost["last_gate"] == "threat"
    assert lost["gate_classes"] == ["combat_priority", "out_of_approach_range_owned"]


def test_cohort_partition_never_subtracts_unrelated_attempts(tmp_path):
    rows = [drop(), loot("attempted", floor_item_id=999)]
    result = coverage(tmp_path, rows)
    assert result["nearby_sightings"] == 1
    assert result["cohort_attempted"] == 0
    assert result["attempts_outside_cohort"] == 1
    assert result["unattempted_count"] == 1
    assert result["legacy_residual"] == 0


def test_reconnect_sighting_does_not_borrow_a_later_local_attempt(tmp_path):
    rows = [
        event("session", session="old"),
        drop(),
        loot("deferred", reason="pending_walk"),
        event("session", session="new"),
        drop(),
        loot("attempted", drop_seq=2),
    ]
    result = coverage(tmp_path, rows)
    assert result["cohort_attempted"] == 1
    assert result["unattempted_count"] == 1


def test_leg133_original_replay_preserves_the_missed_bar_and_partitions_sightings():
    path = Path(__file__).parent / "fixtures" / "leg133_pickup.jsonl"
    pickup = summarize_swing_traces([path])["pickup"]
    assert pickup["drops_seen"] == 87
    assert pickup["agent_attempted"]["attempted"] == 43
    assert pickup["fleet_attempted"]["attempted"] == 57
    assert pickup["fleet_attempted"]["attempt_rate"] == 57 / 87
    split = pickup["drop_coverage"]
    assert split["cohort_attempted"] == 37
    assert split["fleet_credited"] == 14
    assert split["attempts_outside_cohort"] == 6
    assert split["unattempted_count"] == 36
    assert split["legacy_residual"] == 30
    assert split["unattempted_reason_counts"] == {
        "out_of_approach_range_owned": 0,
        "spawn_timeout_far_kill": 0,
        "map_transition_blindness": 0,
        "despawn_before_observation": 5,
        "unknown": 31,
    }


@pytest.mark.parametrize(
    ("gate", "reason_class"),
    [
        ("out_of_range", "out_of_approach_range_owned"),
        ("nearer_agent", "ownership_ceded"),
        ("threat", "combat_priority"),
        ("authored_action", "authored_action"),
        ("pending_walk", "walk_arrival_gate"),
        ("walking", "walk_arrival_gate"),
        ("resting", "pose_gate"),
        ("awaiting_pickup_ack", "pickup_ack_gate"),
        ("unrecognized", "unknown"),
    ],
)
def test_runtime_defer_tap_has_a_reason_class_without_changing_dispatch(gate, reason_class):
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.build_native_state(Goal.GRIND)
    assert client._tracker is not None
    item = client._tracker.view.floor_items[0]
    receipt = LootAttribution()
    receipt.defer(item, gate)
    assert receipt.rows[-1]["reason_class"] == reason_class
    assert receipt.rows[-1]["reason"] == gate
    assert client.wire.sent == []


def test_expiry_after_sighting_and_map_exit_do_not_prove_a_loss_cause(tmp_path):
    result = coverage(tmp_path, [drop(), loot("expired", reason="map_changed", map="other")])
    assert result["unattempted_drops"][0]["reason_class"] == "unknown"
    result = coverage(tmp_path, [drop(), loot("expired", reason="presence_epoch_expired")])
    assert result["unattempted_drops"][0]["reason_class"] == "unknown"


def test_far_visibility_and_expiry_do_not_manufacture_a_spawn_timeout(tmp_path):
    result = coverage(
        tmp_path, [drop(x_event=25), loot("expired", reason="presence_epoch_expired")]
    )
    assert result["nearby_sightings"] == result["unattempted_count"] == 0
    assert result["unattempted_reason_counts"]["spawn_timeout_far_kill"] == 0


def test_raw_collection_proof_without_existing_conversion_does_not_inflate_the_rate(tmp_path):
    # Splitting reasons must not silently weaken the established fleet proof rules.
    rows = [drop(), loot("deferred", reason="walking"), proof("animation")]
    result = summarize_swing_traces([write_trace(tmp_path, rows)])["pickup"]
    assert result["fleet_attempted"]["attempted"] == 0
    assert result["drop_coverage"]["unattempted_count"] == 1


def test_reused_drop_sequence_cannot_borrow_another_sessions_fleet_credit(tmp_path):
    rows = [
        event("session", session="old"),
        drop(),
        loot("deferred", reason="nearer_agent"),
        proof("animation"),
        loot("expired", reason="presence_epoch_expired"),
        event("session", session="new"),
        drop(),
        loot("deferred", reason="nearer_agent"),
        loot("expired", reason="presence_epoch_expired"),
    ]
    result = coverage(tmp_path, rows)
    assert result["fleet_credited"] == 1
    assert result["unattempted_count"] == 1
