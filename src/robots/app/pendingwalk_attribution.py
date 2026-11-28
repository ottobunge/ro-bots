"""Offline pending-walk attribution for one population window; measurement-only.

Names the walk that held the pending-walk slot when every windowed
``pending_walk`` attack gate fired (leg-136 census follow-up). The evidence is
the trace's own rows: ``move_performed`` dispatch outcomes (the script path),
the farm pump's ``combat_approach`` taps (the only trace evidence of
runtime-dispatched approach walks) and ``goal_field_routed`` taps (the only
trace evidence of runtime-dispatched field-route walks), plus the receipt's
per-sample ``attack_gates`` buckets. The tool never opens a client, runner,
DB or network and never changes production behavior.

Origin classes: a holding walk is a FIELD-ROUTE leg (the goal-travel pump's
held re-aims), the combat approach itself (self-paced: the swing lands at
arrival), a roam patrol step (the _RoamWaypoint hold), another walk class
(merchant/loot/stuck recovery), or nothing attributable (register gap). The
traced ``attack_gate_pending_walk`` rows carry per-gate timestamps and
classify directly; the receipt's per-sample counts allocate across the
holding classes by open-hold time (largest remainder), conserved exactly.
"""

import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = "pendingwalk_attribution_v1"

ORIGIN_FIELD = "attack_deferred_behind_field_route"
ORIGIN_APPROACH = "attack_deferred_behind_own_approach"
ORIGIN_ROAM = "attack_deferred_behind_roam_hold"
ORIGIN_OTHER = "attack_deferred_behind_other_walk"
ORIGIN_MOVEMENT = "attack_deferred_behind_movement_walk"
ORIGIN_NONE = "unattributed"
ORIGIN_ORDER = (
    ORIGIN_FIELD,
    ORIGIN_APPROACH,
    ORIGIN_ROAM,
    ORIGIN_OTHER,
    ORIGIN_MOVEMENT,
    ORIGIN_NONE,
)

SITE_AUTHORED = "authored_attack"
SITE_PUMP = "pump_swing"

#: Dispatch-origin strings that name a non-combat walk class directly
#: (playing_runtime ``_pending_origin`` assignments).
_TRIP_ORIGINS = frozenset({"trip_leg", "trip_arrival_confirmation"})
_LOOT_ORIGINS = frozenset({"loot_arrival_confirmation"})
_STUCK_ORIGINS = frozenset(
    {"stuck_cell_detected", "stuck_cell_escalated", "escalated", "rerolled", "repositioned"}
)
#: Dispatch-origin strings the leg-136 displacement rule adds (the
#: field-route tag and the two combat-authored walk classes).
_FIELD_ORIGIN = "field_route"
_APPROACH_ORIGIN = "combat_approach"
_SURVIVAL_ORIGIN = "disengage_step"

#: The displacement tap prefix: ``walk_displaced_for_combat(<origin>)``.
_DISPLACEMENT_PREFIX = "walk_displaced_for_combat("

#: The swing-lease taps (leg-137): the displacement ARMS a bounded combat
#: reservation, the back-offs prove it alive, and the swing (or the honest
#: release tap) ends it. The reservation serves the approach -> swing, so its
#: register class is the combat approach.
_LEASE_RELEASE_PREFIX = "swing_lease_release("
_LEASE_BACKOFF_PREFIX = "swing_lease_hold("
_LEASE_CLS = "own_approach"

#: The walk class each named dispatch origin maps to; the fallback is the
#: unnamed movement class (step/direct).
_NAMED_ORIGINS: dict[str, str] = {
    **dict.fromkeys(_TRIP_ORIGINS, "merchant"),
    **dict.fromkeys(_LOOT_ORIGINS, "loot"),
    **dict.fromkeys(_STUCK_ORIGINS, "stuck"),
    _FIELD_ORIGIN: "field_route",
    _APPROACH_ORIGIN: "own_approach",
    _SURVIVAL_ORIGIN: "combat_survival",
}

#: The slot is considered held for this long after the last evidence row: a
#: release lands on the next 2 s pump tick following an arrival frame
#: (``_await_pending`` one-shot handoff), and the 1 s no-progress release
#: re-sends rather than drops the hold.
OPEN_TTL_S = 4.0
#: An authored Attack action row this close before its gate names the
#: ``_attack`` limb; anything else is the pump's swing continuation.
SITE_WINDOW_S = 0.1


_RELEASE_REASON = "walk_released_no_progress("


def _release_class(reason: str) -> str | None:
    """The walk class a receipt ``walk_released_no_progress(<origin>)`` names.

    A no-progress release proves the walk flew at least the 1 s stall budget,
    so each release contributes that much holder time to the bucket.
    """
    if not reason.startswith(_RELEASE_REASON):
        return None
    return _origin_name(reason[len(_RELEASE_REASON) :].rstrip(")"))


def _origin_name(origin: str) -> str:
    """The walk class one dispatch-origin string names."""
    return _NAMED_ORIGINS.get(origin, "movement")


def _origin_for_class(cls: str | None) -> str:
    if cls == "movement":
        return ORIGIN_MOVEMENT
    if cls == "field_route":
        return ORIGIN_FIELD
    if cls == "own_approach":
        return ORIGIN_APPROACH
    if cls in ("merchant", "loot", "stuck", "combat_survival"):
        return ORIGIN_OTHER
    return ORIGIN_ROAM


class HoldEvent:
    """One traced gate or refused combat authoring, with its holder."""

    __slots__ = ("holder", "kind", "origin", "site", "t")

    def __init__(self, t: float, kind: str, origin: str, holder: str, site: str | None) -> None:
        self.t = t
        self.kind = kind
        self.origin = origin
        self.holder = holder
        self.site = site


class FlightRegister:
    """Reconstructs the pending-slot occupation from one agent's rows.

    The runtime keeps exactly one pending walk; the register tracks the same
    lifecycle from the rows: a dispatch opens the hold (same-target re-sends
    extend it), a blocked re-authoring proves it busy, a position frame on the
    target marks arrival (the hold persists until the next pump tick releases
    it), a map change or 4 s of silence closes it.
    """

    def __init__(self) -> None:
        self._flight: dict[str, Any] | None = None
        self._segments: list[tuple[float, float, str]] = []  # (start, end, cls)
        self._segment_start = 0.0
        self._last_attack_t: float | None = None
        self.displaced: Counter[str] = Counter()
        self.hold_reissues = 0
        self.script_walks_dispatched = 0
        self.script_walks_blocked = 0
        self.field_authorships = 0
        self.approach_dispatched = 0
        self.approach_refused = 0
        self.combat_intents = 0
        self.swings = 0
        self.attacks_executed_rows = 0
        self.lease_backoffs = 0

    # -- row consumption ---------------------------------------------------

    def consume(self, rows: list[dict[str, Any]]) -> list[HoldEvent]:
        events: list[HoldEvent] = []
        for row in rows:
            events.extend(self._consume_row(self._seconds(row["t"]), row))
        return events

    def _consume_row(self, t: float, row: dict[str, Any]) -> list[HoldEvent]:
        kind = row.get("kind")
        if kind == "move_performed":
            return self._on_move(t, row)
        if kind == "swing_observation":
            return self._on_tap(t, row)
        if kind == "action_executed" and row.get("action") == "Attack":
            self.attacks_executed_rows += 1
            self._last_attack_t = t
            return []
        self._on_position(t, row)
        return []

    def _on_move(self, t: float, row: dict[str, Any]) -> list[HoldEvent]:
        outcome = row.get("outcome")
        target = self._target(row)
        if outcome == "dispatched":
            self.script_walks_dispatched += 1
            if self._flight is not None and target == self._flight["target"]:
                self.hold_reissues += 1
                self._extend(t)
            else:
                self._close(t)
                self._open(t, target, self._class_for_reason(row.get("reason")))
        elif outcome == "pending" and self._alive(t):
            self.script_walks_blocked += 1
            self._extend(t)  # a blocked re-authoring proves the slot busy
        self._on_position(t, row)
        return []

    def _on_tap(self, t: float, row: dict[str, Any]) -> list[HoldEvent]:
        tap = row.get("tap")
        if tap == "farm_target_authored":
            self.combat_intents += 1
            return []
        if row.get("event") == "swing":
            self.swings += 1
            self._close(t)  # the swing ends the hold it served (slot proven free)
            return []
        if row.get("event") == "attack_refused" and row.get("reason") == "pending_walk":
            return [self._on_gate_row(t)]
        if self._on_lease_tap(t, tap):
            return []
        if tap == "goal_field_routed":
            return self._on_field_tap(t, row)
        return self._on_approach_tap(t, row) if tap == "farm_approach" else []

    def _on_gate_row(self, t: float) -> HoldEvent:
        origin = self.origin_at(t)
        site = SITE_AUTHORED
        if self._last_attack_t is None or not (0 <= t - self._last_attack_t <= SITE_WINDOW_S):
            # No authored Attack row just before the gate: the pump's swing
            # continuation limb refused on the unconfirmed arrival instead.
            site = SITE_PUMP
        return HoldEvent(t, "attack_gate", origin, origin, site)

    def _on_lease_tap(self, t: float, tap: Any) -> bool:
        """The swing-lease taps (leg-137): a displacement LEASES the register
        hold to the combat it serves, the back-offs prove it alive, and the
        swing or the honest release ends it. True when the row was one."""
        if isinstance(tap, str) and tap.startswith(_DISPLACEMENT_PREFIX):
            origin = tap[len(_DISPLACEMENT_PREFIX) :].rstrip(")")
            self.displaced[origin] += 1
            self._close(t)  # the displacement released the displaced walk's hold
            self._open(t, (None, None), _LEASE_CLS)  # ... and LEASED the slot
            return True
        if isinstance(tap, str) and tap.startswith(_LEASE_RELEASE_PREFIX):
            self._close(t)  # the honest release ends the reservation
            return True
        if isinstance(tap, str) and tap.startswith(_LEASE_BACKOFF_PREFIX):
            self.lease_backoffs += 1
            if self._flight is None:
                self._open(t, (None, None), _LEASE_CLS)
            else:
                self._extend(t)
            return True
        return False

    def _on_field_tap(self, t: float, row: dict[str, Any]) -> list[HoldEvent]:
        self.field_authorships += 1
        dest = self._dest(row)
        if self._flight is not None and dest == self._flight["target"] and self._alive(t):
            if self._flight["cls"] in (None, "roam"):
                self._reclassify(t, "field_route")
            # a same-target re-aim IS the hold continuing (the pump re-fires
            # every 2 s): extend it like a move_performed reissue
            self._extend(t)
        elif self._flight is None:
            # The field pump dispatches through _perform_move directly: its
            # authoring tap is the only trace evidence of the walk.
            self._open(t, dest, "field_route")
        return []

    def _on_approach_tap(self, t: float, row: dict[str, Any]) -> list[HoldEvent]:
        dest = self._dest(row)
        outcome = (row.get("outcome") or {}).get("outcome")
        if outcome == "dispatched":
            self.approach_dispatched += 1
            if self._flight is not None and dest == self._flight["target"] and self._alive(t):
                self._reclassify(t, "own_approach")
            else:
                self._close(t)
                self._open(t, dest, "own_approach")
            return []
        if outcome == "pending":
            self.approach_refused += 1
            if self._alive(t) and self._flight is not None:
                holder = _origin_for_class(self._flight["cls"])
                self._extend(t)
                return [HoldEvent(t, "approach_refused", holder, holder, None)]
        return []

    def _on_position(self, t: float, row: dict[str, Any]) -> None:
        if self._flight is None:
            return
        map_name = row.get("map")
        if map_name is not None:
            held_map = self._flight["map"]
            if held_map is None:
                self._flight["map"] = map_name
            elif held_map != map_name:
                self._close(t)
                return
        if (
            not self._flight.get("arrived")
            and row.get("x") is not None
            and (row.get("x"), row.get("y")) == self._flight["target"]
        ):
            self._flight["arrived"] = True
            self._extend(t)

    # -- flight lifecycle ---------------------------------------------------

    @staticmethod
    def _seconds(iso_t: str) -> float:
        return datetime.fromisoformat(str(iso_t)).timestamp()

    @staticmethod
    def _target(row: dict[str, Any]) -> tuple[Any, Any]:
        params = row.get("params") or {}
        return (params.get("x"), params.get("y"))

    @staticmethod
    def _dest(row: dict[str, Any]) -> tuple[Any, Any]:
        dest = row.get("destination") or []
        return (dest[0], dest[1]) if len(dest) == 2 else (None, None)

    @staticmethod
    def _class_for_reason(reason: str | None) -> str | None:
        if reason is None:
            return None
        return _origin_name(reason) if reason not in ("step", "direct") else None

    def _alive(self, t: float) -> bool:
        return self._flight is not None and t - self._flight["t_last"] <= OPEN_TTL_S

    def _open(self, t: float, target: tuple[Any, Any], cls: str | None) -> None:
        self._flight = {"t_open": t, "t_last": t, "target": target, "cls": cls, "map": None}
        self._segment_start = t

    def _extend(self, t: float) -> None:
        if self._flight is not None:
            self._flight["t_last"] = t

    def _reclassify(self, t: float, cls: str) -> None:
        if self._flight is None or self._flight["cls"] == cls:
            return
        self._segments.append((self._segment_start, t, self._flight["cls"] or "roam"))
        self._flight["cls"] = cls
        self._segment_start = t

    def _close(self, t: float) -> None:
        if self._flight is not None:
            self._segments.append(
                (
                    self._segment_start,
                    min(t, self._flight["t_last"] + OPEN_TTL_S),
                    self._flight["cls"] or "roam",
                )
            )
            self._flight = None

    # -- queries -------------------------------------------------------------

    def origin_at(self, t: float) -> str:
        if self._flight is None or not self._alive(t):
            return ORIGIN_NONE
        return _origin_for_class(self._flight["cls"])

    def _hold_weights(self, t0: float, t1: float) -> tuple[dict[str, float], float]:
        """Open-hold seconds per origin class inside [t0, t1], plus the total."""
        if self._flight is not None and self._flight["t_last"] + OPEN_TTL_S < t1:
            self._close(self._flight["t_last"] + OPEN_TTL_S)
        weights: dict[str, float] = {}
        covered = 0.0
        for start, end, cls in self._segments:
            origin = _origin_for_class(cls)
            lo, hi = max(start, t0), min(end, t1)
            if hi > lo:
                weights[origin] = weights.get(origin, 0.0) + (hi - lo)
                covered += hi - lo
        if self._flight is not None:
            origin = _origin_for_class(self._flight["cls"])
            lo = max(self._segment_start, self._flight["t_open"], t0)
            hi = min(self._flight["t_last"] + OPEN_TTL_S, t1)
            if hi > lo:
                weights[origin] = weights.get(origin, 0.0) + (hi - lo)
                covered += hi - lo
        return weights, covered

    def allocate_bucket(
        self,
        t0: float,
        t1: float,
        gates: int,
        release_seconds: dict[str, float] | None = None,
    ) -> dict[str, int]:
        """Split one bucket's gate count by open-hold time per class.

        ``release_seconds`` carries holder seconds parsed from the receipt's
        per-sample ``move_gates`` (walk classes whose no-progress releases
        landed in the bucket) for spans the trace rows cannot see: the pumps
        dispatch their walks without leaving ``move_performed`` rows.
        """
        weights, covered = self._hold_weights(t0, t1)
        for cls, seconds in (release_seconds or {}).items():
            origin = _origin_for_class(cls)
            if seconds > 0:
                weights[origin] = weights.get(origin, 0.0) + seconds
                covered += seconds
        if gates <= 0:
            return {}
        if covered <= 0.0:
            return {ORIGIN_NONE: gates}
        return _largest_remainder(weights, covered, gates)


def _largest_remainder(weights: dict[str, float], total: float, gates: int) -> dict[str, int]:
    shares = {origin: weights.get(origin, 0.0) / total * gates for origin in weights}
    out = {origin: int(share) for origin, share in shares.items()}
    remainder = gates - sum(out.values())
    order = sorted(shares, key=lambda o: (-(shares[o] - out[o]), ORIGIN_ORDER.index(o)))
    for origin in order[:remainder]:
        out[origin] += 1
    return out


def _bucket_releases(data: dict[str, Any] | None) -> tuple[int, dict[str, float]]:
    """One receipt sample cell's pending_walk count and holder seconds.

    The holder seconds fold two receipt-side evidences: the no-progress
    releases (each proves >= 1 s of the released walk's hold) and the
    ``walk_displaced_for_combat`` census cells -- the trace taps under-sample
    that census (leg-137: 148 traced taps vs 1,846 receipt cells), and each
    displaced walk held the slot for at least the 1 s stall budget before its
    displacement. Both allocate across the displaced class, conserving the
    register-gap gates the sparse trace cannot see.
    """
    if not isinstance(data, dict):
        return 0, {}
    gates = (data.get("attack_gates") or {}).get("pending_walk", 0)
    release_seconds: dict[str, float] = {}
    for reason, count in (data.get("move_gates") or {}).items():
        cls = _release_class(str(reason))
        if cls is not None and isinstance(count, (int, float)):
            # Each no-progress release proves >= 1 s of hold.
            release_seconds[cls] = release_seconds.get(cls, 0.0) + float(count)
    release_seconds.update(_displacement_seconds(data))
    return gates, release_seconds


def _displacement_seconds(data: dict[str, Any]) -> dict[str, float]:
    """Holder seconds the receipt's displacement census cells prove: each
    displaced walk held the slot for at least the 1 s stall budget."""
    seconds: dict[str, float] = {}
    for origin, count in (data.get("walk_displaced_for_combat") or {}).items():
        if isinstance(count, (int, float)) and count > 0:
            cls = _origin_name(str(origin))
            seconds[cls] = seconds.get(cls, 0.0) + float(count)
    return seconds


def _receipt_displacements(samples: list[dict[str, Any]], persona: str) -> Counter[str]:
    """The receipt's per-sample ``walk_displaced_for_combat`` cells, summed."""
    counts: Counter[str] = Counter()
    for sample in samples:
        cell = sample.get(persona)
        if isinstance(cell, dict):
            for origin, count in (cell.get("walk_displaced_for_combat") or {}).items():
                if isinstance(count, (int, float)) and count > 0:
                    counts[str(origin)] += int(count)
    return counts


def _has_evidence(summary: dict[str, Any]) -> bool:
    """Keep agents with attributed gates, traced gates or displacement rows."""
    agent = summary["agent"]
    return bool(
        summary["total"]
        or agent["traced_gates"]
        or agent["displacements"]
        or agent["receipt_displacements"]
    )


def _agent_summary(
    persona: str,
    rows: list[dict[str, Any]],
    samples: list[dict[str, Any]],
    origin_s: float,
) -> dict[str, Any]:
    """Attribute one persona's receipt gates against its flight register."""
    register = FlightRegister()
    events = register.consume(rows)
    traced = [e for e in events if e.kind == "attack_gate"]
    buckets: list[dict[str, Any]] = []
    prev_t = 0.0
    agent_total = 0
    allocated: Counter[str] = Counter()
    for sample in samples:
        sample_t = float(sample["t"])
        gates, releases = _bucket_releases(sample.get(persona))
        if gates:
            allocation = register.allocate_bucket(
                origin_s + prev_t, origin_s + sample_t, gates, releases
            )
            buckets.append(
                {
                    "t0": prev_t,
                    "t1": sample_t,
                    "gates": gates,
                    "origins": allocation,
                }
            )
            allocated.update(allocation)
            agent_total += gates
        prev_t = sample_t
    traced_origins = Counter(e.origin for e in traced)
    traced_sites = Counter(e.site for e in traced if e.site)
    receipt_displacements = _receipt_displacements(samples, persona)
    return {
        "agent": {
            "pending_walk": agent_total,
            "origins": {origin: allocated.get(origin, 0) for origin in ORIGIN_ORDER},
            "displacements": {
                origin: register.displaced.get(origin, 0) for origin in sorted(register.displaced)
            },
            "receipt_displacements": dict(receipt_displacements),
            "traced_gates": len(traced),
            "traced_origins": dict(traced_origins),
            "traced_sites": dict(traced_sites),
            "funnel": {
                "combat_intents": register.combat_intents,
                "attacks_executed_rows": register.attacks_executed_rows,
                "swings": register.swings,
                "approach_dispatched": register.approach_dispatched,
                "approach_refused": register.approach_refused,
                "field_authorships": register.field_authorships,
                "lease_backoffs": register.lease_backoffs,
                "script_walks_dispatched": register.script_walks_dispatched,
                "script_walks_held_reissues": register.hold_reissues,
                "script_walks_blocked": register.script_walks_blocked,
            },
            "buckets": buckets,
        },
        "total": agent_total,
        "allocated": allocated,
        "traced_sites": traced_sites,
    }


def summarize_pendingwalk(
    traces: list[dict[str, Any]],
    samples: list[dict[str, Any]],
    start: str,
    end: str,
    bucket_origin: str | None = None,
) -> dict[str, Any]:
    """Attribute every receipt ``pending_walk`` gate to its holding walk class.

    ``traces`` are windowed row dicts (one stream, any number of personas);
    ``samples`` is the receipt's per-sample list whose ``attack_gates`` carry
    the authoritative per-bucket gate deltas. ``bucket_origin`` is the wall
    clock instant of bucket second zero (the runner launch) mapping the
    runner-relative sample ``t`` onto the trace timeline.
    """
    lo_dt = datetime.fromisoformat(start)
    hi_dt = datetime.fromisoformat(end)
    origin_s = (
        datetime.fromisoformat(bucket_origin) if bucket_origin is not None else lo_dt
    ).timestamp()

    rows_by_persona: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in traces:
        t = datetime.fromisoformat(str(row["t"]))
        if lo_dt <= t < hi_dt:
            rows_by_persona[str(row.get("persona"))].append(row)
    for rows in rows_by_persona.values():
        rows.sort(key=lambda r: str(r["t"]))

    agents: dict[str, Any] = {}
    totals_origins: Counter[str] = Counter()
    totals_sites: Counter[str] = Counter()
    totals_displaced: Counter[str] = Counter()
    grand_total = 0
    for persona in sorted(rows_by_persona):
        summary = _agent_summary(persona, rows_by_persona[persona], samples, origin_s)
        if not _has_evidence(summary):
            continue
        agents[persona] = summary["agent"]
        totals_origins.update(summary["allocated"])
        totals_sites.update(summary["traced_sites"])
        totals_displaced.update(summary["agent"]["displacements"])
        grand_total += summary["total"]
    return {
        "schema": SCHEMA,
        "window": {"start": start, "end": end, "bucket_origin": bucket_origin},
        "totals": {
            "pending_walk": grand_total,
            "origins": {origin: totals_origins.get(origin, 0) for origin in ORIGIN_ORDER},
            "traced_sites": dict(totals_sites),
            "displacements": {
                origin: totals_displaced.get(origin, 0) for origin in sorted(totals_displaced)
            },
        },
        "agents": agents,
    }


def load_traces(paths: list[Path], start: str, end: str) -> list[dict[str, Any]]:
    """Read the windowed rows from population trace files, oldest first."""
    lo_dt = datetime.fromisoformat(start)
    hi_dt = datetime.fromisoformat(end)
    lo_key, hi_key = lo_dt.isoformat(), hi_dt.isoformat()
    rows: list[dict[str, Any]] = []
    for path in paths:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                marker = line[7:20]  # the row's ISO hour, as written
                if not (lo_key[:13] <= marker <= hi_key[:13]):
                    continue
                row = json.loads(line)
                t = str(row.get("t", ""))
                if not t:
                    continue
                if lo_dt <= datetime.fromisoformat(t) < hi_dt:
                    rows.append(row)
    rows.sort(key=lambda r: (str(r.get("persona")), str(r["t"])))
    return rows
