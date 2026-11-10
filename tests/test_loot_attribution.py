"""LEG-90: synthetic pickup receipts and standing/range send barriers."""

import struct

import pytest

from robots.adapters.native_gameplay import NativeGameplayTracker
from robots.app.trace_log import TraceLog
from robots.domain.actions import Attack, Loot, MoveTo
from robots.domain.model import Goal
from tests.test_loot_priority import PICKUP, _clocked_client_with_floor_at, walk_ack
from tests.test_native_gameplay import pickup_ack
from tests.test_native_pose_recovery import pose
from tests.test_trace_log import make_agent, read_lines
from tests.test_zc_item_entry_floor import zc_item_entry


def ack(result: int = 0, item: int = 909, index: int = 2) -> bytes:
    raw = bytearray(pickup_ack(amount=1, result=result))
    struct.pack_into("<H", raw, 2, index)
    struct.pack_into("<H", raw, 6, item if result == 0 else 0)
    return bytes(raw)


@pytest.mark.parametrize("result", [0, 1, 6, 255])
def test_tracker_preserves_all_ack_results(result):
    tracker = NativeGameplayTracker(999)
    tracker.ingest(1, 1.0, 0x0A37, ack(result))
    receipt = tracker.view.pickup_acks[0]
    assert (receipt.raw_result, receipt.success) == (result, result == 0)
    assert bool(tracker.view.acquired_counts) == (result == 0)


@pytest.mark.parametrize("cell", [(42, 37), (43, 38), (44, 39)])
def test_standing_within_server_radius_attempts_once(cell):
    client, _ = _clocked_client_with_floor_at(*cell)
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (Loot(),)
    client.perform_native(Loot())
    assert client.wire.sent == [PICKUP]
    assert client.loot_telemetry[-1]["outcome"] == "attempted"


def test_walk_destination_in_range_is_not_arrival(caplog):
    client, now = _clocked_client_with_floor_at(44, 39)
    client.perform_native(MoveTo(43, 38))
    client.wire.add(walk_ack((42, 37), (43, 38)))
    # Even the pending no-progress timeout must not turn a moving walkok
    # destination into a received standing cell.
    now[0] += 10
    state = client.build_native_state(Goal.GRIND)
    assert not any(isinstance(a, Loot) for a in client.mechanical_actions(state, ()))
    client.perform_native(Loot())
    assert not client.wire.sent
    assert "pending_walk" in caplog.text
    client.wire.add(walk_ack((43, 38), (43, 38)))
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (Loot(),)
    client.perform_native(Loot())
    assert client.wire.sent == [PICKUP]


def test_pending_send_defers_even_before_walkok(caplog):
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.perform_native(MoveTo(43, 37))
    client.perform_native(Loot())
    assert not client.wire.sent
    assert "pending_walk" in caplog.text


def test_sitting_requests_stand_without_burning_attempt():
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.wire.add(pose())
    client.perform_native(Loot())
    assert client.wire.sent == ["stand"]
    client.wire.add(pose(kind=3))
    client.perform_native(Loot())
    assert client.wire.sent == ["stand", PICKUP]


@pytest.mark.parametrize("result", [0, 1, 6, 255])
def test_runtime_attributes_ack_after_floor_vanish_and_never_retries(result):
    client, now = _clocked_client_with_floor_at(43, 38)
    client.perform_native(Loot())
    if result == 0:
        client.wire.add(struct.pack("<HI", 0x00A1, 321))
    client.wire.add(ack(result))
    client.build_native_state(Goal.GRIND)
    row = client.loot_telemetry[-1]
    assert row["floor_item_id"] == 321
    assert row["item_id"] == 909
    assert row["outcome"] == ("succeeded" if result == 0 else "refused-by-server")
    assert row["reason_code"] == result
    for _ in range(8):
        now[0] += 300
        client.perform_native(Loot())
    assert client.wire.sent == [PICKUP]
    assert len([r for r in client.loot_telemetry if r["outcome"] == "attempted"]) == 1


def test_each_candidate_is_range_checked_after_previous_attempt():
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.wire.add(zc_item_entry(aid=322, item=512, x=55, y=50))
    client.perform_native(Loot())
    client.wire.add(ack())
    client.perform_native(Loot())
    assert client.wire.sent == [PICKUP]
    assert client.wire.moves


def test_single_pending_attempt_prevents_ambiguous_failure_attribution():
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.wire.add(zc_item_entry(aid=322, item=512, x=42, y=37))
    client.perform_native(Loot())
    client.perform_native(Loot())
    assert len(client.wire.sent) == 1
    client.wire.add(ack(6))
    client.perform_native(Loot())
    assert len(client.wire.sent) == 2
    assert [r["floor_item_id"] for r in client.loot_telemetry if r["outcome"] == "attempted"] == [
        322,
        321,
    ]


def test_unsolicited_success_is_not_attributed_to_floor_loot():
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.wire.add(ack())
    client.build_native_state(Goal.GRIND)
    assert not [r for r in client.loot_telemetry if r["outcome"] == "succeeded"]


def test_loot_priority_still_preempts_move_and_preserves_attack():
    client, _ = _clocked_client_with_floor_at(43, 38)
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, (MoveTo(55, 55),)) == (Loot(),)
    assert client.mechanical_actions(state, (Attack(123),)) == (Attack(123),)


@pytest.mark.parametrize("result", [0, 6])
def test_host_trace_emits_attempt_and_later_ack_without_new_loot(tmp_path, result):
    trace = TraceLog(tmp_path, "Doramir-01")
    agent, _, _ = make_agent(trace, tmp_path)
    client, _ = _clocked_client_with_floor_at(43, 38)
    agent.client = client
    agent.execute_actions((Loot(),))
    client.wire.add(ack(result))
    state = client.build_native_state(Goal.GRIND)
    agent._trace_state_tick(state)
    agent._trace_state_tick(state)  # receipt drain is independent of periodic throttling
    trace.close()
    rows = [r for r in read_lines(tmp_path, "Doramir-01") if r["kind"] == "loot_performed"]
    assert [r["outcome"] for r in rows] == [
        "attempted",
        "succeeded" if result == 0 else "refused-by-server",
    ]
    assert rows[-1]["reason_code"] == result
    assert all(r["floor_item_id"] == 321 for r in rows)


def test_real_walk_completion_requests_bounded_same_cell_confirmation():
    client, now = _clocked_client_with_floor_at(44, 39)
    client.perform_native(MoveTo(43, 38))
    client.wire.add(walk_ack((42, 37), (43, 38)))
    client.drain_native_events()
    now[0] += 2
    client.drain_native_events()  # existing pending-walk lifecycle releases
    client.perform_native(Loot())
    assert client.wire.sent == []
    assert client.wire.moves == [(43, 38), (43, 38)]
    # Pinned unit.cpp: a same-cell request elicits a zero-length walkok.
    client.wire.add(walk_ack((43, 38), (43, 38)))
    client.perform_native(Loot())
    assert client.wire.sent == [PICKUP]


def test_lost_walk_confirmation_exhausts_budget_without_pickup_spam():
    client, now = _clocked_client_with_floor_at(44, 39)
    client.wire.add(walk_ack((42, 37), (43, 38)))
    for _ in range(10):
        now[0] += 1.1
        client.drain_native_events()
        client.perform_native(Loot())
    assert not client.wire.sent
    assert client.wire.moves == [(43, 38), (43, 38)]
    assert client.loot_telemetry[-1]["reason"] == "arrival_confirmation_exhausted"


def test_fresh_drop_reusing_same_id_is_a_new_presence_epoch():
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.perform_native(Loot())
    client.wire.add(ack(6), struct.pack("<HI", 0x00A1, 321), zc_item_entry(aid=321, x=43, y=38))
    # Absence and re-entry arrive in one snapshot; the receipt sequence
    # distinguishes this presence even though no empty tick was seen.
    client.perform_native(Loot())
    assert client.wire.sent == [PICKUP, PICKUP]


def test_map_boundary_does_not_attribute_old_pending_ack_to_new_drop():
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.perform_native(Loot())
    client.wire.add(
        struct.pack("<H16sHH", 0x0091, b"prontera", 42, 37),
        ack(6),
        zc_item_entry(aid=321, x=43, y=38),
    )
    client.perform_native(Loot())
    assert client.wire.sent == [PICKUP, PICKUP]
    outcomes = [r["outcome"] for r in client.loot_telemetry]
    assert outcomes == ["attempted", "unconfirmed", "attempted"]


def test_unrelated_success_does_not_confirm_pending_loot():
    client, _ = _clocked_client_with_floor_at(43, 38)
    client.perform_native(Loot())
    client.wire.add(ack(item=501, index=3))
    client.build_native_state(Goal.GRIND)
    assert not [r for r in client.loot_telemetry if r["outcome"] == "succeeded"]
    client.wire.add(ack())
    client.build_native_state(Goal.GRIND)
    assert client.loot_telemetry[-1]["outcome"] == "succeeded"


def test_rest_latch_cannot_send_arrival_confirmation():
    client, _ = _clocked_client_with_floor_at(44, 39)
    client.wire.add(walk_ack((42, 37), (43, 38)))
    client.build_native_state(Goal.GRIND)
    client._rest_seq = client._metadata_cursor
    client.perform_native(Loot())
    assert not client.wire.moves
    assert not client.wire.sent
    assert client.loot_telemetry[-1]["reason"] == "resting"


def test_vanished_drop_refuses_stale_intent_with_named_reason(caplog):
    client, _ = _clocked_client_with_floor_at(43, 38)
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (Loot(),)
    client.wire.add(struct.pack("<HI", 0x00A1, 321))
    client.perform_native(Loot())
    client.perform_native(Loot())
    assert not client.wire.sent
    assert "no_floor_item" in caplog.text
    assert len([r for r in client.loot_telemetry if r.get("reason") == "no_floor_item"]) == 1
