"""Offline funnel contracts: source AID, target species, and honest unknowns."""

import json
import struct
from datetime import UTC, datetime, timedelta
from pathlib import Path

from robots.app.swing_funnel import summarize_swing_traces
from robots.app.swing_telemetry import SwingTelemetry
from robots.app.trace_log import TraceLog
from robots.domain.actions import Attack
from tests.test_native_encounter_request import hit
from tests.test_native_rest_interrupt import replay


def write_trace(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / "trace.jsonl"
    path.write_text(
        "".join(
            json.dumps(
                {
                    "t": (
                        datetime(2026, 11, 12, 18, 30, tzinfo=UTC) + timedelta(seconds=i)
                    ).isoformat(),
                    "persona": "solo",
                    **row,
                }
            )
            + "\n"
            for i, row in enumerate(rows)
        )
    )
    return path


def event(event: str, **fields) -> dict:
    return {"kind": "swing_observation", "event": event, "epoch": 1, **fields}


def test_wire_funnel_credits_one_coattacked_death_not_two_exp_params(tmp_path):
    rows: list[dict] = [
        event("swing", target_id=20, species="Poring"),
        event("swing", target_id=21, species="Lunatic"),
        event("damage", sequence=1, source_id=999, own_id=999, target_id=20, damage=25),
        event("damage", sequence=2, source_id=888, own_id=999, target_id=20, damage=25),
        event("damage", sequence=3, source_id=999, own_id=999, target_id=21, damage=0),
        event("death", sequence=4, target_id=20),
        event("exp", sequence=5, parameter=1, delta=1),
        event("exp", sequence=6, parameter=2, delta=1),
        event("drop", sequence=7, floor_item_id=30, distance=2),
        event("drop", sequence=8, floor_item_id=31, distance=3),
        event("pickup_attempt", floor_item_id=30),
        event("pickup_success", floor_item_id=30),
    ]
    result = summarize_swing_traces([write_trace(tmp_path, rows)])["agents"]["solo"]
    assert result["totals"]["swings_sent"] == 2
    assert result["totals"]["damage_events_dealt"] == 1
    assert result["totals"]["kill_credits"] == 1
    assert result["totals"]["base_exp_delta"] == result["totals"]["job_exp_delta"] == 1
    assert result["totals"]["drops_seen"] == 1
    assert result["totals"]["pickup_attempts"] == result["totals"]["pickup_success"] == 1
    assert result["species"]["Poring"]["damage_events_dealt"] == 1
    assert result["species"]["Lunatic"]["damage_events_dealt"] == 0
    # Nearby broadcast drops have no killer/species wire identity.
    assert result["species"]["unknown"]["drops_seen"] == 1


def test_legacy_authored_is_not_sent_and_retained_hits_deduplicate(tmp_path):
    fact = {
        "epoch": 1,
        "sequence": 12,
        "actor_id": 20,
        "species_id": 1002,
        "damage": 25,
        "damage2": 0,
    }
    rows: list[dict] = [
        {"kind": "action_executed", "action": "Attack", "params": {"target_id": 20}},
        {"kind": "decide_request", "request": {"state": {"recent_encounters": [fact]}}},
        {"kind": "decide_request", "request": {"state": {"recent_encounters": [fact]}}},
        {"kind": "world_event", "event": "DamageTaken", "amount": 5, "from_id": 20},
        {"kind": "loot_performed", "outcome": "refused", "reason": "no_floor_item"},
    ]
    result = summarize_swing_traces([write_trace(tmp_path, rows)])["agents"]["solo"]
    assert result["totals"]["attacks_authored"] == 1
    assert result["totals"]["swings_sent"] is None
    assert result["totals"]["damage_events_dealt"] == 1
    assert result["totals"]["kill_credits"] is None
    assert result["totals"]["pickup_attempts"] == 0
    assert result["coverage"] == "legacy_partial"


def test_no_death_no_kill_hp_is_not_exp_and_peer_death_is_not_ours(tmp_path):
    rows: list[dict] = [
        event("damage", sequence=1, source_id=888, own_id=999, target_id=20, damage=50),
        event("death", sequence=2, target_id=20),
        event("exp", sequence=3, parameter=5, delta=99),
        event("exp", sequence=4, parameter=1, delta=2),
    ]
    result = summarize_swing_traces([write_trace(tmp_path, rows)])["agents"]["solo"]["totals"]
    assert result["damage_events_dealt"] == result["kill_credits"] == 0
    assert result["base_exp_delta"] == 2
    assert result["unattributed_exp_events"] == 1


def test_window_primes_old_facts_without_counting_them(tmp_path):
    fact = {"epoch": 1, "sequence": 12, "actor_id": 20, "species_id": 1002, "damage": 25}
    rows: list[dict] = [
        {"kind": "decide_request", "request": {"state": {"recent_encounters": [fact]}}}
    ] * 2
    result = summarize_swing_traces(
        [write_trace(tmp_path, rows)], start="2026-11-12T18:30:01+00:00"
    )["agents"]["solo"]["totals"]
    assert result["damage_events_dealt"] == 0


def test_exp_before_death_and_ambiguous_deaths_stay_honest(tmp_path):
    rows = [
        event("swing", target_id=20, species="Poring"),
        event("damage", sequence=1, source_id=999, own_id=999, target_id=20, damage=25),
        event("exp", sequence=2, parameter=1, delta=1),
        event("death", sequence=3, target_id=20),
    ]
    result = summarize_swing_traces([write_trace(tmp_path, rows)])["agents"]["solo"]["totals"]
    assert result["kill_credits"] == 1
    rows.insert(2, event("damage", sequence=4, source_id=999, own_id=999, target_id=21, damage=25))
    rows.insert(3, event("death", sequence=5, target_id=21))
    result = summarize_swing_traces([write_trace(tmp_path, rows)])["agents"]["solo"]["totals"]
    assert result["kill_credits"] == 0
    assert result["unattributed_exp_events"] == 1


def test_native_wire_and_decision_snapshot_do_not_double_count(tmp_path):
    rows = [
        {
            "kind": "decide_request",
            "request": {
                "state": {
                    "recent_encounters": [
                        {
                            "epoch": 1,
                            "sequence": 1,
                            "actor_id": 20,
                            "damage": 25,
                            "species_id": 1002,
                        }
                    ]
                }
            },
        },
        event("damage", sequence=1, source_id=999, own_id=999, target_id=20, damage=25),
    ]
    result = summarize_swing_traces([write_trace(tmp_path, rows)])["agents"]["solo"]["totals"]
    assert result["damage_events_dealt"] == 1


def test_process_restart_reusing_epoch_and_packet_sequences_counts_new_hits(tmp_path):
    fact = {"epoch": 1, "sequence": 12, "actor_id": 20, "species_id": 1002, "damage": 25}
    rows = [
        {
            "kind": "decide_request",
            "request": {
                "state": {
                    "recent_encounters": [fact],
                    "inventory_capacity": {
                        "native_capacity": {"weight": {"receipt_sequence": seq}}
                    },
                }
            },
        }
        for seq in (100, 100, 39, 39)
    ]
    result = summarize_swing_traces([write_trace(tmp_path, rows)])["agents"]["solo"]["totals"]
    assert result["damage_events_dealt"] == 2


def test_native_capture_uses_real_parsers_and_cached_agent_drain(tmp_path):

    wire, client, _, _, _, agent = replay()
    agent._trace = TraceLog(tmp_path, "solo")
    wire.add(struct.pack("<HHi", 0x00B0, 1, 42), struct.pack("<HHi", 0x00B0, 2, 27))
    agent.execute_actions((Attack(123),))
    wire.add(hit(amount=25), hit(source=888, amount=25))
    wire.add(struct.pack("<HHi", 0x00B0, 1, 43), struct.pack("<HHi", 0x00B0, 2, 28))
    wire.add(struct.pack("<HIB", 0x0080, 123, 1))
    client.build_native_state(agent.goal)
    cursor = client._metadata_cursor
    agent._trace_swing_receipts()
    agent._trace_swing_receipts()
    assert client._metadata_cursor == cursor
    agent._trace.close()
    result = summarize_swing_traces([tmp_path / "solo.jsonl"])["agents"]["solo"]["totals"]
    assert result["swings_sent"] == result["damage_events_dealt"] == result["kill_credits"] == 1
    assert result["base_exp_delta"] == result["job_exp_delta"] == 1


def test_native_sessions_and_agents_keep_reused_ids_separate(tmp_path):
    rows = [
        event(
            "damage",
            sequence=1,
            source_id=999,
            own_id=999,
            target_id=20,
            damage=25,
            session="first",
        ),
        event(
            "damage",
            sequence=1,
            source_id=999,
            own_id=999,
            target_id=20,
            damage=25,
            session="second",
        ),
        {
            **event("damage", sequence=1, source_id=999, own_id=777, target_id=20, damage=25),
            "persona": "peer",
        },
    ]
    result = summarize_swing_traces([write_trace(tmp_path, rows)])["agents"]
    assert result["solo"]["totals"]["damage_events_dealt"] == 2
    assert result["peer"]["totals"]["damage_events_dealt"] == 0


def test_native_telemetry_overflow_is_reported_as_partial(tmp_path):

    telemetry = SwingTelemetry()
    for _ in range(4100):
        telemetry.note("swing", target_id=20)
    rows = [{"kind": "swing_observation", **row} for row in telemetry.drain()]
    result = summarize_swing_traces([write_trace(tmp_path, rows)])["agents"]["solo"]
    assert result["coverage"] == "wire_partial"
    assert result["telemetry_dropped"] == 4
    assert telemetry.drain() == ()


def test_window_keeps_prior_own_damage_for_in_window_kill_credit(tmp_path):
    rows = [
        event("damage", sequence=1, source_id=999, own_id=999, target_id=20, damage=25),
        event("death", sequence=2, target_id=20),
        event("exp", sequence=3, parameter=1, delta=1),
    ]
    result = summarize_swing_traces(
        [write_trace(tmp_path, rows)], start="2026-11-12T18:30:01+00:00"
    )["agents"]["solo"]["totals"]
    assert result["damage_events_dealt"] == 0
    assert result["kill_credits"] == 1
