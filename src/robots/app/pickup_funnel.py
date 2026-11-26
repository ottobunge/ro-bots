"""Receipt-only fleet pickup accounting over the existing per-agent sightings.

A cede/expired presence is credited only with a floor-ID-matched collection,
never bare disappearance or an unbound inventory ACK. Correlation is bounded by
rAthena's 60-second floor lifetime, the next local presence and a two-second
trace-drain allowance. Cross-agent packet sequences/session IDs are incomparable.
The old attempted/success counters retain their original meaning, including
attempts outside the nearby-sighting cohort.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

FLOOR_LIFETIME_SECONDS = 60
DRAIN_ALLOWANCE_SECONDS = 2


def _at(row: dict[str, Any]) -> float:
    return datetime.fromisoformat(row["t"]).timestamp()


def _identity(row: dict[str, Any]) -> tuple[str, int]:
    return row.get("map", "").removesuffix(".gat"), row["floor_item_id"]


@dataclass
class _Presence:
    row: dict[str, Any]
    first: float
    last: float
    outcomes: set[str] = field(default_factory=set)
    ceded: bool = False
    expired: bool = False

    def update(self, row: dict[str, Any]) -> None:
        self.first = min(self.first, _at(row))
        self.last = max(self.last, _at(row))
        self.outcomes.add(row["outcome"])
        self.ceded |= row.get("reason") == "nearer_agent"
        self.expired |= row.get("reason") == "presence_epoch_expired"

    def needs_confirmation(self) -> bool:
        return not self.outcomes & {"succeeded", "collected"} and bool(
            "attempted" in self.outcomes or self.ceded or self.expired
        )


class PickupFunnel:
    def __init__(self) -> None:
        self._sessions: dict[str, tuple[str, int]] = {}
        self._generations: Counter[str] = Counter()
        self._presences: dict[tuple[Any, ...], _Presence] = {}
        self._sightings: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
        self._proofs: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)

    def consume(self, row: dict[str, Any], *, active: bool) -> None:
        self._session(row)
        if not active:
            return
        if row.get("kind") == "loot_performed" and row.get("floor_item_id") is not None:
            self._presence(row)
        elif row.get("event") == "ItemDrop":
            self._sighting(row)
        elif _collection_animation(row):
            self._proofs[(row.get("map", "").removesuffix(".gat"), row["target_id"])].append(row)

    def _session(self, row: dict[str, Any]) -> None:
        if row.get("session"):
            persona = row["persona"]
            session = (row["session"], row.get("epoch", 0))
            previous = self._sessions.get(persona, session)
            self._generations[persona] += previous != session
            self._sessions[persona] = session

    def _presence(self, row: dict[str, Any]) -> None:
        persona = row["persona"]
        identity = _identity(row)
        key = (persona, *identity, self._generations[persona], row.get("drop_seq"))
        presence = self._presences.setdefault(key, _Presence(row, _at(row), _at(row)))
        presence.update(row)
        if row["outcome"] in ("succeeded", "collected"):
            self._proofs[identity].append(row)

    def _sighting(self, row: dict[str, Any]) -> None:
        if row.get("floor_item_id") is None:
            return  # Legacy sightings have no correlatable floor identity.
        if max(abs(row["x_event"] - row["x"]), abs(row["y_event"] - row["y"])) <= 2:
            self._sightings[(row["persona"], *_identity(row))].append(row)

    def conversions(self) -> dict[str, list[dict[str, Any]]]:
        groups: dict[tuple[str, str, int], list[_Presence]] = defaultdict(list)
        for key, presence in self._presences.items():
            groups[key[:3]].append(presence)
        converted: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for key, presences in groups.items():
            ordered = sorted(presences, key=lambda p: p.first)
            previous_end = float("-inf")
            for i, presence in enumerate(ordered):
                lower = max(previous_end, presence.first - DRAIN_ALLOWANCE_SECONDS)
                upper = presence.first + FLOOR_LIFETIME_SECONDS + DRAIN_ALLOWANCE_SECONDS
                if i + 1 < len(ordered):
                    upper = min(upper, ordered[i + 1].first)
                sightings = self._nearby(
                    key,
                    presence.row,
                    max(
                        previous_end,
                        presence.first - FLOOR_LIFETIME_SECONDS - DRAIN_ALLOWANCE_SECONDS,
                    ),
                    upper,
                )
                proof = self._confirmation(key, presence, lower, upper, sightings)
                if proof is not None:
                    converted[key[0]].append(self._conversion(presence, proof))
                previous_end = presence.last
        return converted

    def _confirmation(
        self,
        key: tuple[str, str, int],
        presence: _Presence,
        lower: float,
        upper: float,
        sightings: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        attempted = "attempted" in presence.outcomes
        if not presence.needs_confirmation():
            return None
        return next(
            (
                proof
                for proof in self._proofs[key[1:]]
                if lower <= _at(proof) < upper
                and self._matches(presence.row, proof)
                and _seen_before_collection(attempted, sightings, proof)
            ),
            None,
        )

    def _nearby(
        self, key: tuple[str, str, int], row: dict[str, Any], lower: float, upper: float
    ) -> list[dict[str, Any]]:
        return [
            sight
            for sight in self._sightings[key]
            if (sight["x_event"], sight["y_event"]) == (row.get("drop_x"), row.get("drop_y"))
            and lower < _at(sight) <= upper
        ]

    @staticmethod
    def _matches(row: dict[str, Any], proof: dict[str, Any]) -> bool:
        if proof.get("kind") == "loot_performed":
            return (row.get("drop_x"), row.get("drop_y")) == (
                proof.get("drop_x"),
                proof.get("drop_y"),
            ) and row.get("item_id") == proof.get("item_id")
        if row["persona"] == proof["persona"]:
            return bool(proof.get("sequence", float("inf")) > row.get("drop_seq", 0))
        return True

    @staticmethod
    def _conversion(presence: _Presence, proof: dict[str, Any]) -> dict[str, Any]:
        row = presence.row
        return {
            "tap": "pickup_fleet_converted",
            "reason": "nearer_agent" if presence.ceded else "peer_consumed",
            "persona": row["persona"],
            "map": row.get("map"),
            "floor_item_id": row["floor_item_id"],
            "drop_seq": row.get("drop_seq"),
            "agent_attempted": "attempted" in presence.outcomes,
            "proof_persona": proof["persona"],
            "proof": proof.get("outcome", "collection_animation"),
            "proof_t": proof["t"],
        }


def pickup_summary(totals: dict[str, Any], converted: list[dict[str, Any]]) -> dict[str, Any]:
    drops = totals.get("drops_seen", 0)
    attempts, success = totals.get("pickup_attempts", 0), totals.get("pickup_success", 0)
    additional = sum(not row["agent_attempted"] for row in converted)
    return {
        "drops_seen": drops,
        "agent_attempted": _rates(drops, attempts, success),
        "fleet_attempted": _rates(drops, attempts + additional, success + len(converted)),
        "converted_drops": converted,
    }


def _rates(drops: int, attempts: int, success: int) -> dict[str, int | float | None]:
    return {
        "attempted": attempts,
        "success": success,
        "attempt_rate": attempts / drops if drops else None,
        "success_rate": success / attempts if attempts else None,
    }


def attach_pickup_summary(agents: dict[str, Any], funnel: PickupFunnel) -> dict[str, Any]:
    converted = funnel.conversions()
    totals: Counter[str] = Counter()
    for persona, agent in agents.items():
        agent["pickup"] = pickup_summary(agent["totals"], converted[persona])
        totals.update(
            {k: agent["totals"][k] for k in ("drops_seen", "pickup_attempts", "pickup_success")}
        )
    return pickup_summary(dict(totals), [row for rows in converted.values() for row in rows])


def _collection_animation(row: dict[str, Any]) -> bool:
    return bool(
        row.get("kind") == "swing_observation"
        and row.get("event") == "damage"
        and row.get("damage_type") == 1
        and row.get("source_id")
    )


def _seen_before_collection(
    attempted: bool, sightings: list[dict[str, Any]], proof: dict[str, Any]
) -> bool:
    return attempted or any(_at(s) <= _at(proof) + DRAIN_ALLOWANCE_SECONDS for s in sightings)
