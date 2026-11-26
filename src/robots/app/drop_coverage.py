"""Receipt-only reason evidence for nearby floor sightings.

The historic pickup rate mixes nearby sightings with *all* local sends. Its
subtraction is not a set of drops. Keep those counters intact and expose an
independent, session-bound partition, including sends outside that cohort.
Unknown is intentional: disappearance cannot prove TTL, a far kill, ownership,
or a safe opportunity. Gate observations describe barriers, not lost revenue.
"""

from collections import Counter, defaultdict
from datetime import datetime
from enum import StrEnum
from typing import Any


class DropReasonClass(StrEnum):
    OUT_OF_APPROACH_RANGE_OWNED = "out_of_approach_range_owned"
    SPAWN_TIMEOUT_FAR_KILL = "spawn_timeout_far_kill"
    MAP_TRANSITION_BLINDNESS = "map_transition_blindness"
    DESPAWN_BEFORE_OBSERVATION = "despawn_before_observation"
    UNKNOWN = "unknown"
    OWNERSHIP_CEDED = "ownership_ceded"
    COMBAT_PRIORITY = "combat_priority"
    AUTHORED_ACTION = "authored_action"
    WALK_ARRIVAL_GATE = "walk_arrival_gate"
    POSE_GATE = "pose_gate"
    PICKUP_ACK_GATE = "pickup_ack_gate"


TERMINAL_CLASSES = tuple(DropReasonClass)[:5]
_GATE_CLASSES = {
    "out_of_range": DropReasonClass.OUT_OF_APPROACH_RANGE_OWNED,
    "spawn_timeout": DropReasonClass.SPAWN_TIMEOUT_FAR_KILL,
    "nearer_agent": DropReasonClass.OWNERSHIP_CEDED,
    "threat": DropReasonClass.COMBAT_PRIORITY,
    "authored_action": DropReasonClass.AUTHORED_ACTION,
    "pending_walk": DropReasonClass.WALK_ARRIVAL_GATE,
    "walking": DropReasonClass.WALK_ARRIVAL_GATE,
    "awaiting_walk_arrival": DropReasonClass.WALK_ARRIVAL_GATE,
    "arrival_confirmation_exhausted": DropReasonClass.WALK_ARRIVAL_GATE,
    "resting": DropReasonClass.POSE_GATE,
    "not_standing": DropReasonClass.POSE_GATE,
    "awaiting_pickup_ack": DropReasonClass.PICKUP_ACK_GATE,
}


def defer_reason_class(reason: str) -> DropReasonClass:
    return _GATE_CLASSES.get(reason, DropReasonClass.UNKNOWN)


def _at(row: dict[str, Any]) -> float:
    return datetime.fromisoformat(row["t"]).timestamp()


def _near(row: dict[str, Any]) -> bool:
    return bool(max(abs(row["x_event"] - row["x"]), abs(row["y_event"] - row["y"])) <= 2)


def _map(row: dict[str, Any]) -> str:
    return str(row.get("map") or "").removesuffix(".gat")


def _reason(sight: dict[str, Any], rows: list[dict[str, Any]]) -> DropReasonClass:
    landed = str(sight.get("map_event") or sight.get("map") or "").removesuffix(".gat")
    if landed != _map(sight):
        return DropReasonClass.MAP_TRANSITION_BLINDNESS
    if _expired_before_observation(sight, rows):
        return DropReasonClass.DESPAWN_BEFORE_OBSERVATION
    if any(r.get("reason") == "spawn_timeout" for r in rows):
        return DropReasonClass.SPAWN_TIMEOUT_FAR_KILL
    return _last_approach_class(rows)


def _last_approach_class(rows: list[dict[str, Any]]) -> DropReasonClass:
    gates = [r for r in rows if r.get("outcome") == "deferred"]
    if gates and gates[-1].get("reason") == "out_of_range":
        return DropReasonClass.OUT_OF_APPROACH_RANGE_OWNED
    return DropReasonClass.UNKNOWN


def _expired_before_observation(sight: dict[str, Any], rows: list[dict[str, Any]]) -> bool:
    return any(r.get("reason") == "presence_epoch_expired" and _at(r) < _at(sight) for r in rows)


class DropCoverage:
    def __init__(self) -> None:
        self._sessions: dict[str, tuple[str, int]] = {}
        self._generation: Counter[str] = Counter()
        self._sights: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
        self._loot: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)

    def consume(self, row: dict[str, Any], *, active: bool) -> None:
        persona = row["persona"]
        if row.get("session"):
            session = (row["session"], row.get("epoch", 0))
            self._generation[persona] += self._sessions.get(persona, session) != session
            self._sessions[persona] = session
        if not active or row.get("floor_item_id") is None:
            return
        key = (persona, self._generation[persona], row["floor_item_id"])
        if row.get("event") == "ItemDrop":
            self._sights[key].append(row)
        elif row.get("kind") == "loot_performed":
            self._loot[key].append(row)

    def summary(
        self, converted: list[dict[str, Any]], *, persona: str | None = None
    ) -> dict[str, Any]:
        counts: Counter[str] = Counter()
        lost: list[dict[str, Any]] = []
        for key in self._sights.keys() | self._loot.keys():
            if persona is None or persona == key[0]:
                self._partition(key, converted, counts, lost)
        reasons = Counter(row["reason_class"] for row in lost)
        return {
            "nearby_sightings": counts["nearby_sightings"],
            "cohort_attempted": counts["cohort_attempted"],
            "fleet_credited": counts["fleet_credited"],
            "attempts_outside_cohort": counts["attempts_outside_cohort"],
            "unattempted_count": len(lost),
            "legacy_residual": len(lost) - counts["attempts_outside_cohort"],
            "unattempted_reason_counts": {
                reason.value: reasons[reason] for reason in TERMINAL_CLASSES
            },
            "unattempted_drops": sorted(lost, key=lambda r: (r["t"], r["persona"])),
        }

    def _partition(
        self,
        key: tuple[str, int, int],
        converted: list[dict[str, Any]],
        counts: Counter[str],
        lost: list[dict[str, Any]],
    ) -> None:
        sights = self._sights[key]
        related, outside = _associate(sights, self._loot[key])
        counts["attempts_outside_cohort"] += outside
        for i, sight in enumerate(sights):
            if not _near(sight):
                continue
            counts["nearby_sightings"] += 1
            rows = sorted(related[i], key=_at)
            if any(r["outcome"] == "attempted" for r in rows):
                counts["cohort_attempted"] += 1
            elif _converted(sight, rows, converted, key[1]):
                counts["fleet_credited"] += 1
            else:
                lost.append(_loss(sight, rows, key[1]))


def _associate(
    sights: list[dict[str, Any]], rows: list[dict[str, Any]]
) -> tuple[dict[int, list[dict[str, Any]]], int]:
    related: dict[int, list[dict[str, Any]]] = defaultdict(list)
    outside = 0
    for row in rows:
        candidates = [i for i, sight in enumerate(sights) if _matches(sight, row)]
        nearby = False
        if candidates:
            index = min(candidates, key=lambda i: abs(_at(sights[i]) - _at(row)))
            related[index].append(row)
            nearby = _near(sights[index])
        if row["outcome"] == "attempted" and not nearby:
            outside += 1
    return related, outside


def _matches(sight: dict[str, Any], row: dict[str, Any]) -> bool:
    return (
        abs(_at(sight) - _at(row)) <= 62
        and (sight["x_event"], sight["y_event"]) == (row.get("drop_x"), row.get("drop_y"))
        and (_map(sight) == _map(row) or row.get("reason") in ("map_changed", "session_changed"))
    )


def _converted(
    sight: dict[str, Any],
    rows: list[dict[str, Any]],
    converted: list[dict[str, Any]],
    generation: int,
) -> bool:
    sequences = {r.get("drop_seq") for r in rows}
    return any(
        c["persona"] == sight["persona"]
        and c["floor_item_id"] == sight["floor_item_id"]
        and _map(c) == _map(sight)
        and c.get("drop_seq") in sequences
        and c.get("presence_generation") == generation
        for c in converted
    )


def _loss(sight: dict[str, Any], rows: list[dict[str, Any]], generation: int) -> dict[str, Any]:
    gates = [r for r in rows if r.get("outcome") == "deferred"]
    return {
        "tap": "drop_unattempted_reason",
        "t": sight["t"],
        "persona": sight["persona"],
        "generation": generation,
        "map": sight.get("map"),
        "map_event": sight.get("map_event"),
        "floor_item_id": sight["floor_item_id"],
        "drop_x": sight["x_event"],
        "drop_y": sight["y_event"],
        "reason_class": _reason(sight, rows).value,
        "last_gate": gates[-1].get("reason") if gates else None,
        "gate_classes": sorted({defer_reason_class(r.get("reason", "")).value for r in gates}),
        "evidence": [
            {k: r[k] for k in ("t", "outcome", "reason", "drop_seq", "map") if k in r} for r in rows
        ],
    }
