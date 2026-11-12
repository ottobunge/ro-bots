"""Offline, receipt-ready swing conversion; missing wire evidence stays null.

Kill credits mean an own-damaged target's received death with a positive exp
update within two seconds (base/job updates count once). Exp is never divided
by a species' full reward: co-attack shares are retained as received. Multiple
candidate deaths stay uncredited rather than assigning the same exp twice.
Drops have no killer ID: nearby means Chebyshev <= 2, species stays unknown.
Legacy decision snapshots contain bounded own-source-filtered hit facts, so
those counts are lower bounds, deduplicated by persona/session/sequence.
"""

import json
from collections import Counter, defaultdict
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

COUNTS = (
    "attacks_authored",
    "swings_sent",
    "damage_events_dealt",
    "damage_dealt",
    "kill_credits",
    "base_exp_delta",
    "job_exp_delta",
    "drops_seen",
    "pickup_attempts",
    "pickup_success",
    "unattributed_exp_events",
)


class _AgentFunnel:
    def __init__(self) -> None:
        self.species: dict[str, Counter[str]] = defaultdict(Counter)
        self.names: dict[int, str] = {}
        self.seen: set[tuple[Any, ...]] = set()
        self.damaged: set[tuple[str, int, int]] = set()
        self.deaths: dict[tuple[str, int, int], tuple[float, str]] = {}
        self.credited: set[tuple[str, int, int]] = set()
        self.gates: Counter[str] = Counter()
        self.dropped = 0
        self.wire = False
        self._legacy_sequence = 0
        self._exp_rows: list[dict[str, Any]] = []

    def add(self, species: str, count: str, value: int = 1) -> None:
        self.species[species][count] += value

    def consume(self, row: dict[str, Any], *, active: bool) -> None:
        kind = row.get("kind")
        if kind == "swing_observation":
            self.wire = self.wire or active
            self._wire(row, active=active)
        elif kind == "decide_request":
            self._legacy_hits(row, active=active)
        elif active or row.get("event") == "MonsterSpotted":
            self._legacy(row)

    def _legacy(self, row: dict[str, Any]) -> None:
        if row.get("event") == "MonsterSpotted":
            self.names[row["monster_id"]] = row["monster"]
        elif row.get("action") == "Attack" and row["kind"] == "action_executed":
            self.add(self.names.get(row["params"]["target_id"], "unknown"), "attacks_authored")
        elif row.get("event") == "ItemDrop":
            distance = max(abs(row["x_event"] - row["x"]), abs(row["y_event"] - row["y"]))
            if distance <= 2:
                self.add("unknown", "drops_seen")
        elif row["kind"] == "loot_performed":
            count = {"attempted": "pickup_attempts", "succeeded": "pickup_success"}.get(
                row["outcome"]
            )
            if count:
                self.add("unknown", count)

    def _legacy_hits(self, row: dict[str, Any], *, active: bool) -> None:
        state = row["request"]["state"]
        capacity = state.get("inventory_capacity", {}).get("native_capacity") or {}
        sequence = (capacity.get("weight") or {}).get("receipt_sequence", self._legacy_sequence)
        if sequence < self._legacy_sequence:
            self.seen.clear()  # Process restarts reuse native_epoch=1 and packet sequences.
        self._legacy_sequence = sequence
        facts = [] if self.wire else state.get("recent_encounters", [])
        for fact in facts:
            key = (fact["epoch"], fact["sequence"], "damage")
            if key in self.seen:
                continue
            self.seen.add(key)
            amount = max(0, fact["damage"]) + max(0, fact.get("damage2", 0))
            if active and amount:
                species = self.names.get(fact["actor_id"], str(fact.get("species_id") or "unknown"))
                self.add(species, "damage_events_dealt")
                self.add(species, "damage_dealt", amount)

    def _wire(self, row: dict[str, Any], *, active: bool) -> None:
        event = row["event"]
        if self._duplicate(row):
            return
        target = row.get("target_id", 0)
        species = row.get("species") or self.names.get(target, "unknown")
        if target and row.get("species"):
            self.names[target] = species
        identity = (row.get("session", ""), row["epoch"], target)
        if event == "damage":
            self._damage(row, identity, species, active=active)
        elif event == "death" and identity in self.damaged:
            self.deaths[identity] = (_time(row), species)
        elif active:
            self._count_wire(row, species)

    def _count_wire(self, row: dict[str, Any], species: str) -> None:
        if row["event"] == "exp":
            self._exp_rows.append(row)
        else:
            self._simple(row, species)

    def _duplicate(self, row: dict[str, Any]) -> bool:
        key = (row.get("session", ""), row["epoch"], row.get("sequence"), row["event"])
        if row.get("sequence") is None:
            return False
        if key in self.seen:
            return True
        self.seen.add(key)
        return False

    def _damage(
        self, row: dict[str, Any], identity: tuple[str, int, int], species: str, *, active: bool
    ) -> None:
        amount = max(0, row["damage"]) + max(0, row.get("damage2", 0))
        if row["source_id"] == row["own_id"] and amount and not row.get("is_sp_damage", False):
            self.damaged.add(identity)
            if active:
                self.add(species, "damage_events_dealt")
                self.add(species, "damage_dealt", amount)

    def _exp(self, row: dict[str, Any]) -> None:
        parameter, delta = row["parameter"], row.get("delta")
        if parameter not in (1, 2) or delta is None or delta <= 0:
            return
        count = "base_exp_delta" if parameter == 1 else "job_exp_delta"
        candidates = [
            key
            for key, (at, _) in self.deaths.items()
            if key[:2] == (row.get("session", ""), row["epoch"]) and abs(_time(row) - at) <= 2
        ]
        if len(candidates) != 1:
            self.add("unknown", count, delta)
            self.add("unknown", "unattributed_exp_events")
            return
        key = candidates[0]
        species = self.deaths[key][1]
        self.add(species, count, delta)
        if key not in self.credited:
            self.credited.add(key)
            self.add(species, "kill_credits")

    def _simple(self, row: dict[str, Any], species: str) -> None:
        event = row["event"]
        if event == "swing":
            self.add(species, "swings_sent")
        elif event == "telemetry_gap":
            self.dropped += row["dropped"]
        elif event == "attack_refused":
            self.gates[row["reason"]] += 1
        elif event == "drop" and row["distance"] <= 2:
            self.add("unknown", "drops_seen")
        elif event in ("pickup_attempt", "pickup_success"):
            self.add("unknown", "pickup_attempts" if event == "pickup_attempt" else event)

    def summary(self) -> dict[str, Any]:
        for exp_row in self._exp_rows:
            self._exp(exp_row)
        species = {name: self._counts(counts) for name, counts in self.species.items()}
        totals: Counter[str] = Counter()
        for counts in self.species.values():
            totals.update(counts)
        return {
            "totals": self._counts(totals),
            "species": species,
            "attack_refusals": dict(self.gates),
            "coverage": self._coverage(),
            "telemetry_dropped": self.dropped,
        }

    def _counts(self, counts: Counter[str]) -> dict[str, int | None]:
        unknown = {"swings_sent", "kill_credits", "base_exp_delta", "job_exp_delta"}
        return {key: None if not self.wire and key in unknown else counts[key] for key in COUNTS}

    def _coverage(self) -> str:
        if self.dropped:
            return "wire_partial"
        return "wire_observations" if self.wire else "legacy_partial"


def _time(row: dict[str, Any]) -> float:
    return float(row["at"]) if "at" in row else datetime.fromisoformat(row["t"]).timestamp()


def summarize_swing_traces(
    paths: list[Path], *, start: str | None = None, end: str | None = None
) -> dict[str, Any]:
    """Stream chronological JSONL shards; start inclusive, end exclusive, ISO UTC.

    Read pre-window snapshots to prime deduplication; never count authored
    Attack as a send. No live client, DB, runner or network access.
    """
    agents: dict[str, _AgentFunnel] = defaultdict(_AgentFunnel)
    lower = datetime.fromisoformat(start).timestamp() if start else float("-inf")
    upper = datetime.fromisoformat(end).timestamp() if end else float("inf")
    for persona in _wire_personas(paths, lower, upper):
        agents[persona].wire = True
    for row in _trace_rows(paths):
        at = datetime.fromisoformat(row["t"]).timestamp()
        if at < upper:
            agents[row["persona"]].consume(row, active=at >= lower)
    return {
        "schema": "swing_conversion_v1",
        "start": start,
        "end": end,
        "agents": {name: agent.summary() for name, agent in agents.items()},
    }


def _trace_rows(paths: list[Path]) -> Iterator[dict[str, Any]]:
    for path in paths:
        with path.open() as source:
            for line in source:
                yield json.loads(line)


def _wire_personas(paths: list[Path], lower: float, upper: float) -> set[str]:
    # First pass avoids counting decision snapshots before that tick's drain.
    personas: set[str] = set()
    for path in paths:
        with path.open() as source:
            for line in source:
                if "swing_observation" not in line:
                    continue
                row = json.loads(line)
                at = datetime.fromisoformat(row["t"]).timestamp()
                if row.get("kind") == "swing_observation" and lower <= at < upper:
                    personas.add(row["persona"])
    return personas
