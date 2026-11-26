"""Leg-134 gate evidence must resolve the unattempted cohort, not just its tap."""

import hashlib
import json
from pathlib import Path

import pytest

from robots.app.drop_coverage import DropReasonClass
from robots.app.swing_funnel import summarize_swing_traces
from tests.test_drop_coverage_split import coverage
from tests.test_fleet_pickup_denominator import drop, loot

FIXTURES = Path(__file__).parent / "fixtures"
VERIFICATION = json.loads((FIXTURES / "leg134_pickup_verification.json").read_text())


@pytest.mark.parametrize(
    ("gate", "reason_class"),
    [
        ("out_of_range", "out_of_approach_range_owned"),
        ("spawn_timeout", "spawn_timeout_far_kill"),
        ("nearer_agent", "ownership_ceded"),
        ("threat", "combat_priority"),
        ("authored_action", "authored_action"),
        ("pending_walk", "walk_arrival_gate"),
        ("walking", "walk_arrival_gate"),
        ("awaiting_walk_arrival", "walk_arrival_gate"),
        ("arrival_confirmation_exhausted", "walk_arrival_gate"),
        ("resting", "pose_gate"),
        ("not_standing", "pose_gate"),
        ("awaiting_pickup_ack", "pickup_ack_gate"),
        ("unrecognized", "unknown"),
    ],
)
@pytest.mark.parametrize("outcome", ["deferred", "expired"])
def test_gate_reason_resolves_even_when_only_expiry_retains_the_defer(
    tmp_path, gate, reason_class, outcome
):
    detail = (
        {"reason": gate}
        if outcome == "deferred"
        else {"reason": "presence_epoch_expired", "deferred_reason": gate}
    )
    result = coverage(tmp_path, [drop(), loot(outcome, **detail)])
    lost = result["unattempted_drops"][0]
    assert lost["reason_class"] == reason_class
    assert lost["last_gate"] == gate
    assert lost["gate_classes"] == [reason_class]
    assert lost["evidence"][0].items() >= detail.items()
    assert result["unattempted_reason_counts"][reason_class] == 1
    assert sum(result["unattempted_reason_counts"].values()) == 1


def test_expiry_first_defer_cannot_override_the_latest_observed_gate(tmp_path):
    rows = [
        drop(),
        loot("deferred", reason="threat", t="2026-11-12T18:30:01+00:00"),
        loot("deferred", reason="authored_action", t="2026-11-12T18:30:02+00:00"),
        loot("expired", reason="presence_epoch_expired", deferred_reason="threat"),
    ]
    lost = coverage(tmp_path, rows)["unattempted_drops"][0]
    assert lost["reason_class"] == "authored_action"
    assert lost["last_gate"] == "authored_action"
    assert lost["gate_classes"] == ["authored_action", "combat_priority"]


def test_unsupported_latest_gate_does_not_borrow_an_earlier_known_class(tmp_path):
    rows = [
        drop(),
        loot("deferred", reason="threat", t="2026-11-12T18:30:01+00:00"),
        loot("deferred", reason="unrecognized", t="2026-11-12T18:30:02+00:00"),
    ]
    assert coverage(tmp_path, rows)["unattempted_drops"][0]["reason_class"] == "unknown"


@pytest.fixture(scope="module")
def leg134_pickup():
    path = FIXTURES / "leg134_pickup.jsonl"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == VERIFICATION["fixture_sha256"]
    return summarize_swing_traces([path], start=VERIFICATION["start"], end=VERIFICATION["end"])[
        "pickup"
    ]


def test_leg134_gate_resolution_preserves_pickup_accounting_and_passes_the_bar(leg134_pickup):
    assert {k: v for k, v in leg134_pickup.items() if k != "drop_coverage"} == VERIFICATION[
        "original_pickup"
    ]
    split = leg134_pickup["drop_coverage"]
    assert {
        k: v
        for k, v in split.items()
        if k not in ("unattempted_reason_counts", "unattempted_drops")
    } == {
        k: v
        for k, v in VERIFICATION["original_coverage"].items()
        if k != "unattempted_reason_counts"
    }
    expected = dict.fromkeys((reason.value for reason in DropReasonClass), 0)
    expected.update(
        despawn_before_observation=3,
        ownership_ceded=12,
        combat_priority=7,
        authored_action=4,
        walk_arrival_gate=2,
        unknown=11,
    )
    assert split["unattempted_reason_counts"] == expected
    assert sum(expected.values()) == split["unattempted_count"] == 39
    assert expected["unknown"] / split["unattempted_count"] < 0.5


@pytest.mark.parametrize(
    "case",
    VERIFICATION["hand_verified"],
    ids=lambda c: f"{c['persona']}-{c['floor_item_id']}-{c['expected_class']}",
)
def test_leg134_hand_verified_raw_rows(leg134_pickup, case):
    lost = next(
        r
        for r in leg134_pickup["drop_coverage"]["unattempted_drops"]
        if (r["persona"], r["t"], r["floor_item_id"])
        == (case["persona"], case["t"], case["floor_item_id"])
    )
    assert (lost["drop_x"], lost["drop_y"]) == (case["drop_x"], case["drop_y"])
    assert lost["reason_class"] == case["expected_class"]
    assert lost["last_gate"] == case["last_gate"]
    if case["expected_class"] == "unknown":
        assert lost["evidence"] == []
    else:
        assert len(lost["evidence"]) == len(case["evidence_lines"])
