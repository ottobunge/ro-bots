"""Offline movement census for one population window; measurement-only.

Classifies every windowed ``action_executed`` MoveTo by purpose from the
trace's own rows and never opens a client, DB, runner or network. The per-
action evidence is: the sampled ``script_step`` context (10 s telemetry
throttle, so context is carried forward between samples), the paired
``move_performed`` dispatch reason, and the authored target's offset from the
standing cell. Churn counts repeat authorings of one (map, target) with no
intervening arrival, where an arrival is any position-bearing row standing on
that exact cell. Abandoned-before-next counts authorings whose aim was
REPLACED by a different target before any arrival at it; a consecutive
authoring of the SAME cell is the held patrol waypoint re-aiming (leg-135
fix), not a replaced walk. Empty-view positions interpolate the tracked
position stream
because ``script_step`` rows carry no coordinates.
"""

import bisect
import json
from collections import Counter, defaultdict
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = "movement_census_v1"
ROAM_OFFSETS = frozenset({(8, 0), (-8, 0), (0, 8), (0, -8), (5, 5), (-5, -5)})
FARM_SCRIPTS = frozenset({"FarmScript", "GrindScript"})
MERCHANT_SCRIPT = "MerchantDrive"
MERCHANT_REASONS = frozenset(
    {"trip_leg", "staging_occupied", "occupied_west_rerouted", "npc_intercepted"}
)
REROLL_REASONS = frozenset(
    {"target_unwalkable_rerolled", "escalated", "stuck_cell_escalated", "single_cell_path"}
)
TRAVEL_MIN_CELLS = 12
JOIN_ROWS = 6
TOP_FLEET_POSITIONS = 10
TOP_AGENT_POSITIONS = 3
PURPOSES = (
    "roam_patrol",
    "merchant_trip",
    "approach_engage",
    "travel_leg",
    "reroll_reaim",
    "other",
)
DISPATCH_KEYS = ("dispatched", "held_pending", "refused", "unjoined")


def classify_move(
    *,
    script: str | None,
    nearest_monster_d: float | None,
    offset: tuple[int, int],
    reason: str | None,
) -> str:
    """One authored MoveTo's purpose from dispatch reason, script and offset."""
    if reason in MERCHANT_REASONS or script == MERCHANT_SCRIPT:
        return "merchant_trip"
    if reason in REROLL_REASONS:
        return "reroll_reaim"
    if script in FARM_SCRIPTS and nearest_monster_d is not None:
        return "approach_engage"
    if script in FARM_SCRIPTS and offset in ROAM_OFFSETS:
        return "roam_patrol"
    if script in FARM_SCRIPTS and max(abs(offset[0]), abs(offset[1])) >= TRAVEL_MIN_CELLS:
        return "travel_leg"
    return "other"


class _AgentCensus:
    """One persona's windowed movement evidence."""

    def __init__(self) -> None:
        self.actions_by_name: Counter[str] = Counter()
        self.purpose: Counter[str] = Counter()
        self.dispatch: Counter[str] = Counter()
        self.script_samples: Counter[str] = Counter()
        self.empty_positions: Counter[tuple[str, int, int]] = Counter()
        self.empty_samples = 0
        self.script_step_samples = 0
        self.authorings: list[tuple[int, tuple[str, int, int]]] = []
        self.arrivals: dict[tuple[str, int, int], list[int]] = defaultdict(list)
        self._ctx_script: str | None = None
        self._ctx_monster_d: float | None = None
        self._pos: tuple[str, int, int] | None = None

    def consume_rows(self, rows: list[dict[str, Any]]) -> None:
        """One pass over the persona's windowed rows, in file order."""
        for index, row in enumerate(rows):
            self._observe_position(index, row)
            kind = row.get("kind")
            if kind == "script_step":
                self._observe_script_step(row)
            elif kind == "action_executed":
                self._observe_action(index, rows, row)

    def _observe_position(self, index: int, row: dict[str, Any]) -> None:
        if not {"map", "x", "y"} <= row.keys():
            return
        cell = (str(row["map"]), int(row["x"]), int(row["y"]))
        self._pos = cell
        self.arrivals[cell].append(index)

    def _observe_script_step(self, row: dict[str, Any]) -> None:
        self.script_step_samples += 1
        script = row.get("script")
        self.script_samples[str(script)] += 1
        self._ctx_script = str(script) if script is not None else None
        monster_d = row.get("nearest_monster_d")
        self._ctx_monster_d = float(monster_d) if monster_d is not None else None
        if row.get("nearby_n") == 0 and self._pos is not None:
            self.empty_samples += 1
            self.empty_positions[self._pos] += 1

    def _observe_action(self, index: int, rows: list[dict[str, Any]], row: dict[str, Any]) -> None:
        action = str(row.get("action"))
        self.actions_by_name[action] += 1
        if action != "MoveTo":
            return
        params = row.get("params") or {}
        target = (int(params.get("x", 0)), int(params.get("y", 0)))
        origin = (int(row.get("x", 0)), int(row.get("y", 0)))
        offset = (target[0] - origin[0], target[1] - origin[1])
        reason, outcome = self._paired_dispatch(rows, index)
        self.purpose[
            classify_move(
                script=self._ctx_script,
                nearest_monster_d=self._ctx_monster_d,
                offset=offset,
                reason=reason,
            )
        ] += 1
        self.dispatch[self._dispatch_key(outcome)] += 1
        cell = self._pos or ("", origin[0], origin[1])
        self.authorings.append((index, (str(cell[0]), target[0], target[1])))

    @staticmethod
    def _paired_dispatch(rows: list[dict[str, Any]], index: int) -> tuple[str | None, str | None]:
        """The move_performed sibling logged right after the authored action."""
        for row in rows[index + 1 : index + 1 + JOIN_ROWS]:
            if row.get("kind") == "move_performed":
                reason = row.get("reason")
                outcome = row.get("outcome")
                return (
                    str(reason) if reason is not None else None,
                    str(outcome) if outcome is not None else None,
                )
        return None, None

    @staticmethod
    def _dispatch_key(outcome: str | None) -> str:
        if outcome == "pending":
            return "held_pending"
        if outcome in ("dispatched", "refused"):
            return outcome
        return "unjoined"

    def summary(self, top_positions: int) -> dict[str, Any]:
        churn, abandoned, compared = self._churn()
        moves = sum(self.purpose.values())
        return {
            "actions_total": sum(self.actions_by_name.values()),
            "actions_by_name": dict(self.actions_by_name.most_common()),
            "move_total": moves,
            "purpose": {name: self.purpose[name] for name in PURPOSES},
            "dispatch": {key: self.dispatch[key] for key in DISPATCH_KEYS},
            "repeat_churn": churn,
            "repeat_churn_share_pct": _pct(churn, moves),
            "abandoned_before_next": abandoned,
            "abandoned_compared": compared,
            "abandoned_share_pct": _pct(abandoned, compared),
            "script_samples": dict(self.script_samples.most_common()),
            "script_step_samples": self.script_step_samples,
            "empty_view_samples": self.empty_samples,
            "empty_view_sample_share_pct": _pct(self.empty_samples, self.script_step_samples),
            "top_empty_positions": self._top_empty(top_positions),
        }

    def _top_empty(self, limit: int) -> list[dict[str, Any]]:
        return [
            {"map": cell[0], "x": cell[1], "y": cell[2], "count": count}
            for cell, count in self.empty_positions.most_common(limit)
        ]

    def _churn(self) -> tuple[int, int, int]:
        previous: dict[tuple[str, int, int], int] = {}
        churn = 0
        for index, cell in self.authorings:
            earlier = previous.get(cell)
            if earlier is not None and not self._arrived_between(cell, earlier, index):
                churn += 1
            previous[cell] = index
        abandoned = 0
        for (prev_index, prev_cell), (this_index, this_cell) in zip(
            self.authorings, self.authorings[1:], strict=False
        ):
            # Leg-135 refinement: a consecutive authoring of the SAME cell is
            # the held patrol waypoint re-aiming (the walk was not replaced -
            # the runtime pacing holds the repeat), so it is not abandonment.
            # Only a DIFFERENT next aim without an intervening arrival
            # abandons the previous one ("walk replaced unreached").
            if prev_cell != this_cell and not self._arrived_between(
                prev_cell, prev_index, this_index
            ):
                abandoned += 1
        return churn, abandoned, max(0, len(self.authorings) - 1)

    def _arrived_between(self, cell: tuple[str, int, int], lower: int, upper: int) -> bool:
        arrivals = self.arrivals.get(cell, [])
        spot = bisect.bisect_right(arrivals, lower)
        return spot < len(arrivals) and arrivals[spot] < upper


def _pct(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 2) if denominator else 0.0


def _window_rows_by_persona(
    paths: list[Path], lower: float, upper: float, date_gate: str | None
) -> Iterator[tuple[str, list[dict[str, Any]]]]:
    """Group (persona, rows) pairs inside [lower, upper) preserving file order.

    Trace files are append-only across legs: when both bounds share one ISO
    date, lines without that date substring are skipped without parsing (the
    multi-gigabyte pre-window history stays on disk).
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        with path.open() as source:
            for line in source:
                if date_gate is not None and date_gate not in line:
                    continue
                if '"t"' not in line:
                    continue
                try:
                    row: dict[str, Any] = json.loads(line)
                except json.JSONDecodeError:
                    continue
                at = datetime.fromisoformat(str(row.get("t"))).timestamp()
                if lower <= at < upper:
                    grouped[str(row.get("persona"))].append(row)
    yield from grouped.items()


def summarize_movement_traces(
    paths: list[Path], *, start: str | None = None, end: str | None = None
) -> dict[str, Any]:
    """Attribute every windowed authored MoveTo; start inclusive, end exclusive."""
    lower = datetime.fromisoformat(start).timestamp() if start else float("-inf")
    upper = datetime.fromisoformat(end).timestamp() if end else float("inf")
    gate = start[:10] if start and end and start[:10] == end[:10] else None
    censuses: dict[str, _AgentCensus] = defaultdict(_AgentCensus)
    for persona, rows in _window_rows_by_persona(paths, lower, upper, gate):
        censuses[persona].consume_rows(rows)
    summaries = {
        name: census.summary(TOP_AGENT_POSITIONS) for name, census in sorted(censuses.items())
    }
    return {
        "schema": SCHEMA,
        "start": start,
        "end": end,
        "fleet": _fleet(censuses, summaries),
        "agents": summaries,
    }


def _fleet(
    censuses: dict[str, _AgentCensus], summaries: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    actions_by_name: Counter[str] = Counter()
    purpose: Counter[str] = Counter()
    dispatch: Counter[str] = Counter()
    maps: Counter[str] = Counter()
    positions: Counter[tuple[str, int, int]] = Counter()
    for census in censuses.values():
        actions_by_name.update(census.actions_by_name)
        purpose.update(census.purpose)
        dispatch.update(census.dispatch)
        positions.update(census.empty_positions)
        _absorb_empty_maps(maps, census)
    churn, abandoned, compared, empty_samples, script_steps = _fleet_scalars(summaries)
    moves = sum(purpose.values())
    top = [
        {"map": cell[0], "x": cell[1], "y": cell[2], "count": count}
        for cell, count in positions.most_common(TOP_FLEET_POSITIONS)
    ]
    return {
        "actions_total": sum(actions_by_name.values()),
        "actions_by_name": dict(actions_by_name.most_common()),
        "move_total": moves,
        "purpose": {name: purpose[name] for name in PURPOSES},
        "attribution_pct": _pct(moves - purpose["other"], moves),
        "dispatch": {key: dispatch[key] for key in DISPATCH_KEYS},
        "repeat_churn": churn,
        "repeat_churn_share_pct": _pct(churn, moves),
        "abandoned_before_next": abandoned,
        "abandoned_compared": compared,
        "abandoned_share_pct": _pct(abandoned, compared),
        "empty_view": {
            "samples": empty_samples,
            "script_step_samples": script_steps,
            "fleet_sample_share_pct": _pct(empty_samples, script_steps),
            "maps": dict(maps.most_common()),
            "top_positions": top,
        },
    }


def _absorb_empty_maps(maps: Counter[str], census: _AgentCensus) -> None:
    """Sum empty-view sample counts per map (dict keys would collapse them)."""
    for cell, count in census.empty_positions.items():
        maps[cell[0]] += count


def _fleet_scalars(summaries: dict[str, dict[str, Any]]) -> tuple[int, int, int, int, int]:
    """Fleet churn/abandonment/empty-view totals across per-agent summaries."""
    churn = abandoned = compared = empty_samples = script_steps = 0
    for agent in summaries.values():
        churn += int(agent["repeat_churn"])
        abandoned += int(agent["abandoned_before_next"])
        compared += int(agent["abandoned_compared"])
        empty_samples += int(agent["empty_view_samples"])
        script_steps += int(agent["script_step_samples"])
    return churn, abandoned, compared, empty_samples, script_steps
