"""Pending-walk attribution contracts: origin classes, flight register, buckets.

Measurement-only: the tool classifies each leg-136 ``pending_walk`` attack gate
by the walk that held the pending slot when the gate fired, from the trace's
own rows (move dispatches, farm-pump taps, receipt sample buckets). It never
opens a client, runner, DB or network, and never changes production behavior.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from robots.app.pendingwalk_attribution import (
    SCHEMA,
    FlightRegister,
    summarize_pendingwalk,
)

T0 = datetime(2026, 11, 27, 19, 0, tzinfo=UTC)


def iso(seconds: float) -> str:
    return (T0 + timedelta(seconds=seconds)).isoformat()


def epoch(seconds: float) -> float:
    return (T0 + timedelta(seconds=seconds)).timestamp()


def row(seconds: float, persona: str = "pop_a", **fields: Any) -> dict:
    return {"t": iso(seconds), "persona": persona, **fields}


def move_performed(seconds: float, x: int, y: int, outcome: str, reason: str) -> dict:
    return row(
        seconds,
        kind="move_performed",
        map="prt_fild08",
        x=50,
        y=50,
        action="MoveTo",
        params={"x": x, "y": y},
        outcome=outcome,
        reason=reason,
    )


def tap(seconds: float, tap_name: str, dest: tuple[int, int], outcome: dict | None = None) -> dict:
    fields: dict = {
        "kind": "swing_observation",
        "map": "prt_fild08",
        "x": 50,
        "y": 50,
        "event": "field_travel" if tap_name == "goal_field_routed" else "combat_approach",
        "tap": tap_name,
        "destination": list(dest),
    }
    if outcome is not None:
        fields["outcome"] = outcome
    return row(seconds, **fields)


def attack_gate(seconds: float) -> dict:
    return row(
        seconds,
        kind="swing_observation",
        map="prt_fild08",
        x=50,
        y=50,
        event="attack_refused",
        tap="attack_gate_pending_walk",
        reason="pending_walk",
        target_id=110161864,
    )


def attack_action(seconds: float) -> dict:
    return row(
        seconds,
        kind="action_executed",
        map="prt_fild08",
        x=50,
        y=50,
        action="Attack",
        params={"target_id": 110161864},
    )


class TestFlightRegisterClasses:
    """The register names the walk class holding the pending slot."""

    def test_script_walk_defaults_to_roam_hold(self) -> None:
        register = FlightRegister()
        register.consume([move_performed(1.0, 51, 50, "dispatched", "step")])
        assert register.origin_at(epoch(1.5)) == "attack_deferred_behind_roam_hold"

    def test_field_tap_upgrades_the_hold(self) -> None:
        register = FlightRegister()
        register.consume(
            [
                tap(1.0, "goal_field_routed", (51, 50)),
                move_performed(1.05, 51, 50, "dispatched", "step"),
            ]
        )
        assert register.origin_at(epoch(1.5)) == "attack_deferred_behind_field_route"

    def test_field_tap_alone_opens_a_tentative_hold(self) -> None:
        # The field pump dispatches through _perform_move directly: the tap is
        # the only trace evidence, and the gate can fire while it holds.
        register = FlightRegister()
        register.consume([tap(1.0, "goal_field_routed", (51, 50))])
        assert register.origin_at(epoch(1.5)) == "attack_deferred_behind_field_route"

    def test_combat_approach_dispatch_is_its_own_class(self) -> None:
        register = FlightRegister()
        register.consume(
            [
                tap(1.0, "farm_approach", (51, 50), {"outcome": "dispatched", "reason": "step"}),
                move_performed(1.05, 51, 50, "dispatched", "step"),
            ]
        )
        assert register.origin_at(epoch(1.5)) == "attack_deferred_behind_own_approach"

    def test_merchant_and_loot_origins(self) -> None:
        register = FlightRegister()
        register.consume([move_performed(1.0, 51, 50, "dispatched", "trip_leg")])
        assert register.origin_at(epoch(1.5)) == "attack_deferred_behind_other_walk"
        register.consume([move_performed(3.0, 52, 50, "dispatched", "loot_arrival_confirmation")])
        assert register.origin_at(epoch(3.5)) == "attack_deferred_behind_other_walk"

    def test_stuck_recovery_is_other(self) -> None:
        register = FlightRegister()
        register.consume([move_performed(1.0, 51, 50, "dispatched", "stuck_cell_escalated")])
        assert register.origin_at(epoch(1.5)) == "attack_deferred_behind_other_walk"

    def test_no_flight_open_is_unattributed(self) -> None:
        register = FlightRegister()
        assert register.origin_at(epoch(1.0)) == "unattributed"

    def test_hold_survives_the_arrival_release_lag(self) -> None:
        # The runtime clears _pending on the NEXT pump tick after the arrival
        # frame; gates fire inside that gap (playing_runtime _await_pending).
        register = FlightRegister()
        register.consume(
            [
                move_performed(1.0, 51, 50, "dispatched", "step"),
                row(2.0, kind="state_tick", map="prt_fild08", x=51, y=50),
            ]
        )
        assert register.origin_at(epoch(2.5)) == "attack_deferred_behind_roam_hold"

    def test_reissue_of_the_same_cell_is_one_hold(self) -> None:
        # The 1s no-progress release re-sends the same held target; the hold
        # is one continuous slot occupation, not a new flight per re-send.
        register = FlightRegister()
        register.consume(
            [
                tap(1.0, "goal_field_routed", (51, 50)),
                move_performed(1.05, 51, 50, "dispatched", "step"),
                move_performed(2.2, 51, 50, "dispatched", "step"),
            ]
        )
        assert register.origin_at(epoch(2.5)) == "attack_deferred_behind_field_route"

    def test_stale_hold_closes(self) -> None:
        register = FlightRegister()
        register.consume([move_performed(1.0, 51, 50, "dispatched", "step")])
        assert register.origin_at(epoch(30.0)) == "unattributed"


class TestTracedGates:
    """Traced attack_gate rows classify directly against the register."""

    def test_traced_gate_behind_field_route(self) -> None:
        register = FlightRegister()
        events = register.consume(
            [
                tap(1.0, "goal_field_routed", (51, 50)),
                move_performed(1.05, 51, 50, "dispatched", "step"),
                attack_action(1.99),
                attack_gate(2.0),
            ]
        )
        assert events[0].origin == "attack_deferred_behind_field_route"
        assert events[0].site == "authored_attack"

    def test_site_split_by_adjacent_authoring(self) -> None:
        register = FlightRegister()
        events = register.consume(
            [
                move_performed(1.0, 51, 50, "dispatched", "step"),
                attack_gate(2.0),  # no authored Attack row adjacent: pump swing limb
                attack_action(4.0),
                attack_gate(4.01),  # authored Attack 10ms earlier: _attack limb
            ]
        )
        assert events[0].site == "pump_swing"
        assert events[1].site == "authored_attack"

    def test_blocked_approach_proves_a_noncombat_hold(self) -> None:
        register = FlightRegister()
        events = register.consume(
            [
                tap(1.0, "goal_field_routed", (51, 50)),
                move_performed(1.05, 51, 50, "dispatched", "step"),
                tap(
                    2.0,
                    "farm_approach",
                    (51, 50),
                    {"outcome": "pending", "reason": "await_pending"},
                ),
            ]
        )
        assert events[0].kind == "approach_refused"
        assert events[0].holder == "attack_deferred_behind_field_route"


class TestReceiptBuckets:
    """Sample-bucket counts allocate across the holding classes in time."""

    def test_bucket_gates_split_by_hold_time(self) -> None:
        rows = [
            # roam hold for the whole bucket
            move_performed(1.0, 51, 50, "dispatched", "step"),
            move_performed(28.0, 51, 50, "dispatched", "step"),
        ]
        register = FlightRegister()
        register.consume(rows)
        allocation = register.allocate_bucket(epoch(0), epoch(30), 4)
        assert allocation["attack_deferred_behind_roam_hold"] == 4

    def test_allocation_conserves_the_total(self) -> None:
        rows = [
            move_performed(1.0, 51, 50, "dispatched", "step"),
            tap(10.0, "goal_field_routed", (55, 55)),
            move_performed(10.05, 51, 50, "dispatched", "step"),
            move_performed(20.0, 51, 50, "dispatched", "step"),
        ]
        register = FlightRegister()
        register.consume(rows)
        allocation = register.allocate_bucket(epoch(0), epoch(30), 7)
        assert sum(allocation.values()) == 7
        assert set(allocation) <= {
            "attack_deferred_behind_roam_hold",
            "attack_deferred_behind_field_route",
            "attack_deferred_behind_own_approach",
            "attack_deferred_behind_other_walk",
            "unattributed",
        }

    def test_receipt_releases_name_the_holder_class(self) -> None:
        # A no-progress release proves the walk flew the 1 s stall budget; the
        # pumps dispatch their walks without move_performed rows, so these are
        # the only holder evidence in trace-silent spans.
        register = FlightRegister()
        allocation = register.allocate_bucket(
            epoch(0), epoch(30), 5, {"merchant": 3.0, "movement": 2.0}
        )
        assert sum(allocation.values()) == 5
        assert allocation["attack_deferred_behind_other_walk"] >= 2
        assert allocation["attack_deferred_behind_movement_walk"] >= 1

    def test_zero_hold_time_goes_unattributed(self) -> None:
        register = FlightRegister()
        allocation = register.allocate_bucket(epoch(0), epoch(30), 3)
        assert allocation == {"unattributed": 3}


class TestSummarize:
    """The window summary carries the verdict's census and the routing data."""

    def _samples(self) -> list[dict]:
        # Two buckets; the agent holds a roam walk through both.
        return [
            {
                "t": 30.0,
                "pop_a": {"attack_gates": {"pending_walk": 3}, "move_gates": {}},
            },
            {
                "t": 60.0,
                "pop_a": {"attack_gates": {"pending_walk": 2}, "move_gates": {}},
            },
        ]

    def test_census_total_matches_the_receipt(self) -> None:
        traces = [
            row(
                1.0,
                kind="move_performed",
                map="prt_fild08",
                x=50,
                y=50,
                action="MoveTo",
                params={"x": 51, "y": 50},
                outcome="dispatched",
                reason="step",
            ),
        ]
        result = summarize_pendingwalk(traces, samples=self._samples(), start=iso(0), end=iso(90))
        agent = result["agents"]["pop_a"]
        assert agent["pending_walk"] == 5
        assert sum(agent["origins"].values()) == 5
        assert result["totals"]["pending_walk"] == 5
        assert result["schema"] == SCHEMA

    def test_traced_gates_calibrate_the_allocation(self) -> None:
        traces = [
            move_performed(1.0, 51, 50, "dispatched", "step"),
            tap(3.0, "goal_field_routed", (51, 50)),
            attack_action(3.99),
            attack_gate(4.0),
        ]
        result = summarize_pendingwalk(traces, samples=self._samples(), start=iso(0), end=iso(90))
        agent = result["agents"]["pop_a"]
        assert agent["traced_gates"] == 1
        assert agent["traced_sites"]["authored_attack"] == 1
        # The traced gate sits inside a hold whose taps attest the field route.
        assert agent["traced_origins"]["attack_deferred_behind_field_route"] == 1

    def test_funnel_counters_are_reported(self) -> None:
        traces = [
            move_performed(1.0, 51, 50, "dispatched", "step"),
            tap(2.0, "farm_approach", (52, 55), {"outcome": "dispatched", "reason": "step"}),
            tap(4.0, "farm_approach", (53, 55), {"outcome": "pending", "reason": "await_pending"}),
            row(
                5.0,
                kind="swing_observation",
                map="prt_fild08",
                x=50,
                y=50,
                event="combat_intent",
                tap="farm_target_authored",
                target_id=1,
            ),
            attack_action(6.0),
            row(
                7.0,
                kind="swing_observation",
                map="prt_fild08",
                x=50,
                y=50,
                event="swing",
                target_id=1,
            ),
        ]
        result = summarize_pendingwalk(traces, samples=self._samples(), start=iso(0), end=iso(90))
        funnel = result["agents"]["pop_a"]["funnel"]
        assert funnel["combat_intents"] == 1
        assert funnel["attacks_executed_rows"] == 1
        assert funnel["swings"] == 1
        assert funnel["approach_dispatched"] == 1
        assert funnel["approach_refused"] == 1

    def test_window_filters_rows(self) -> None:
        traces = [
            move_performed(-3600.0, 51, 50, "dispatched", "step"),
            attack_gate(-3599.0),
        ]
        result = summarize_pendingwalk(traces, samples=self._samples(), start=iso(0), end=iso(90))
        assert result["agents"] == {}
