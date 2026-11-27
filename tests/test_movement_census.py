"""Movement-census contracts: purpose attribution, churn, empty-view positions.

The census is measurement-only: it classifies every windowed ``action_executed``
MoveTo by purpose from the trace's own rows (sampled script context, dispatch
reasons, target-offset signature) and never infers behavior the rows do not
carry. Attributed share must stay >= 95 percent; ``other`` is the honest
remainder.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from robots.app.movement_census import summarize_movement_traces

T0 = datetime(2026, 11, 27, 8, 0, tzinfo=UTC)


def write_trace(tmp_path: Path, persona: str, rows: list[dict]) -> Path:
    path = tmp_path / f"{persona}.jsonl"
    path.write_text(
        "".join(
            json.dumps(
                {
                    "t": (T0 + timedelta(seconds=i)).isoformat(),
                    "persona": persona,
                    **row,
                }
            )
            + "\n"
            for i, row in enumerate(rows)
        )
    )
    return path


def script_step(script: str, nearby_n: int = 0, nearest_monster_d: float | None = None) -> dict:
    return {
        "kind": "script_step",
        "script": script,
        "status": "ACTIVE",
        "actions": ["MoveTo"],
        "nearest_monster_d": nearest_monster_d,
        "nearby_n": nearby_n,
    }


def move_to(x: int, y: int, at_x: int = 100, at_y: int = 100, **fields) -> dict:
    return {
        "kind": "action_executed",
        "map": "prt_fild08",
        "x": at_x,
        "y": at_y,
        "action": "MoveTo",
        "params": {"x": x, "y": y},
        **fields,
    }


def move_performed(x: int, y: int, at_x: int = 100, at_y: int = 100, **fields) -> dict:
    return {
        "kind": "move_performed",
        "map": "prt_fild08",
        "x": at_x,
        "y": at_y,
        "action": "MoveTo",
        "params": {"x": x, "y": y},
        **fields,
    }


def position(map_name: str, x: int, y: int) -> dict:
    return {"kind": "state_tick", "map": map_name, "x": x, "y": y}


def fleet(result: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], result["agents"]["solo"])


def test_roam_patrol_offset_under_empty_farm_view(tmp_path):
    path = write_trace(
        tmp_path,
        "solo",
        [
            script_step("FarmScript"),
            move_to(108, 100),
            move_performed(108, 100, outcome="dispatched", reason="step"),
        ],
    )
    result = summarize_movement_traces([path])
    assert fleet(result)["purpose"]["roam_patrol"] == 1
    assert fleet(result)["move_total"] == 1


def test_merchant_drive_context_is_a_trip_leg(tmp_path):
    path = write_trace(
        tmp_path,
        "solo",
        [
            script_step("MerchantDrive", nearby_n=5),
            move_to(96, 95),
            move_performed(96, 95, outcome="dispatched", reason="step"),
        ],
    )
    result = summarize_movement_traces([path])
    assert fleet(result)["purpose"]["merchant_trip"] == 1


def test_merchant_dispatch_reason_beats_farm_context(tmp_path):
    path = write_trace(
        tmp_path,
        "solo",
        [
            script_step("FarmScript"),
            move_to(96, 95),
            move_performed(96, 95, outcome="dispatched", reason="trip_leg"),
        ],
    )
    result = summarize_movement_traces([path])
    assert fleet(result)["purpose"]["merchant_trip"] == 1


def test_reroll_reaim_is_its_own_class(tmp_path):
    path = write_trace(
        tmp_path,
        "solo",
        [
            script_step("FarmScript"),
            move_to(108, 100),
            move_performed(108, 100, outcome="dispatched", reason="target_unwalkable_rerolled"),
        ],
    )
    result = summarize_movement_traces([path])
    assert fleet(result)["purpose"]["reroll_reaim"] == 1


def test_approach_requires_a_visible_monster_not_a_nearby_player(tmp_path):
    rows = [script_step("FarmScript", nearby_n=2, nearest_monster_d=5.0), move_to(107, 99)]
    path = write_trace(tmp_path, "solo", rows)
    assert fleet(summarize_movement_traces([path]))["purpose"]["approach_engage"] == 1
    rows = [script_step("FarmScript", nearby_n=2, nearest_monster_d=None), move_to(108, 100)]
    path = write_trace(tmp_path, "solo", rows)
    assert fleet(summarize_movement_traces([path]))["purpose"]["roam_patrol"] == 1


def test_far_farm_offset_without_merch_is_travel(tmp_path):
    path = write_trace(
        tmp_path,
        "solo",
        [
            script_step("GrindScript"),
            move_to(100, 79),
            move_performed(100, 79, outcome="dispatched", reason="step"),
        ],
    )
    result = summarize_movement_traces([path])
    assert fleet(result)["purpose"]["travel_leg"] == 1


def test_unattributable_move_lands_in_other_and_dents_coverage(tmp_path):
    path = write_trace(tmp_path, "solo", [move_to(140, 88)])
    result = summarize_movement_traces([path])
    agent = fleet(result)
    assert agent["purpose"]["other"] == 1
    assert result["fleet"]["attribution_pct"] == 0.0


def test_repeat_churn_needs_no_intervening_arrival(tmp_path):
    churned = [
        script_step("FarmScript"),
        move_to(108, 100, at_x=100, at_y=100),
        position("prt_fild08", 100, 100),
        move_to(108, 100, at_x=100, at_y=100),
    ]
    path = write_trace(tmp_path, "solo", churned)
    assert fleet(summarize_movement_traces([path]))["repeat_churn"] == 1
    arrived = [
        script_step("FarmScript"),
        move_to(108, 100, at_x=100, at_y=100),
        position("prt_fild08", 108, 100),
        move_to(108, 100, at_x=108, at_y=100),
    ]
    path = write_trace(tmp_path, "solo", arrived)
    assert fleet(summarize_movement_traces([path]))["repeat_churn"] == 0


def test_abandoned_before_next_author(tmp_path):
    abandoned = [
        script_step("FarmScript"),
        move_to(108, 100, at_x=100, at_y=100),
        move_to(92, 100, at_x=100, at_y=100),
    ]
    path = write_trace(tmp_path, "solo", abandoned)
    agent = fleet(summarize_movement_traces([path]))
    assert agent["abandoned_before_next"] == 1
    assert agent["abandoned_compared"] == 1
    kept = [
        script_step("FarmScript"),
        move_to(108, 100, at_x=100, at_y=100),
        position("prt_fild08", 108, 100),
        move_to(92, 100, at_x=108, at_y=100),
    ]
    path = write_trace(tmp_path, "solo", kept)
    agent = fleet(summarize_movement_traces([path]))
    assert agent["abandoned_before_next"] == 0


def test_window_excludes_out_of_bounds_rows(tmp_path):
    rows = [
        script_step("FarmScript"),
        move_to(108, 100),
        move_to(109, 100),
    ]
    path = write_trace(tmp_path, "solo", rows)
    start = (T0 + timedelta(seconds=1)).isoformat()
    end = (T0 + timedelta(seconds=2)).isoformat()
    result = summarize_movement_traces([path], start=start, end=end)
    assert fleet(result)["move_total"] == 1


def test_dispatch_outcomes_are_counted(tmp_path):
    rows = [
        script_step("FarmScript"),
        move_to(108, 100),
        move_performed(108, 100, outcome="pending", reason="await_pending"),
        move_to(100, 108),
        move_performed(100, 108, outcome="refused", reason="npc_intercepted"),
        move_to(105, 105),
        move_performed(105, 105, outcome="dispatched", reason="step"),
    ]
    path = write_trace(tmp_path, "solo", rows)
    result = summarize_movement_traces([path])
    assert result["fleet"]["dispatch"] == {
        "dispatched": 1,
        "held_pending": 1,
        "refused": 1,
        "unjoined": 0,
    }


def test_empty_view_position_uses_tracked_position_stream(tmp_path):
    rows = [
        move_to(108, 100, at_x=210, at_y=365),
        {
            "kind": "script_step",
            "script": "FarmScript",
            "status": "ACTIVE",
            "actions": ["MoveTo"],
            "nearest_monster_d": None,
            "nearby_n": 0,
        },
    ]
    path = write_trace(tmp_path, "solo", rows)
    result = summarize_movement_traces([path])
    empty = result["fleet"]["empty_view"]
    assert empty["samples"] == 1
    assert {"map": "prt_fild08", "x": 210, "y": 365, "count": 1} in empty["top_positions"]


def test_action_census_and_schema(tmp_path):
    rows = [
        script_step("FarmScript"),
        move_to(108, 100),
        {
            "kind": "action_executed",
            "map": "prt_fild08",
            "x": 100,
            "y": 100,
            "action": "Say",
            "params": {"text": "gg"},
        },
    ]
    path = write_trace(tmp_path, "solo", rows)
    result = summarize_movement_traces([path])
    assert result["fleet"]["actions_by_name"] == {"MoveTo": 1, "Say": 1}
    assert result["schema"] == "movement_census_v1"
    json.dumps(result)


def test_attribution_threshold_holds_on_mixed_synthetic_fleet(tmp_path):
    rows = [script_step("FarmScript")]
    rows += [move_to(108, 100), move_performed(108, 100, outcome="dispatched", reason="step")] * 8
    rows += [
        script_step("MerchantDrive", nearby_n=4),
        move_to(96, 95),
        move_performed(96, 95, outcome="dispatched", reason="trip_leg"),
    ]
    path = write_trace(tmp_path, "solo", rows)
    result = summarize_movement_traces([path])
    assert result["fleet"]["attribution_pct"] >= 95.0


def test_held_re_aim_is_not_abandonment(tmp_path):
    """Leg-135 refinement: a consecutive authoring of the SAME cell is the
    held patrol waypoint re-aiming (the walk was not replaced - the runtime
    pacing holds the repeat), so it is not abandonment. Only a DIFFERENT next
    aim without an intervening arrival abandons the previous one."""
    rows = [
        script_step("FarmScript"),
        move_to(108, 100, at_x=100, at_y=100),
        move_to(108, 100, at_x=100, at_y=100),
        move_to(108, 100, at_x=100, at_y=100),
    ]
    path = write_trace(tmp_path, "solo", rows)
    agent = fleet(summarize_movement_traces([path]))
    assert agent["abandoned_before_next"] == 0
    assert agent["abandoned_compared"] == 2
    assert agent["repeat_churn"] == 2
