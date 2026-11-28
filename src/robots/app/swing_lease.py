"""The swing lease: the displaced slot stays combat-reserved until the swing.

Leg-137's verdict: displacement-as-instant-release churns - the freed slot was
re-contested by non-combat re-authorship before the authoring combat swung.
The lease reuses the disengage-step lease shape (``CombatDisengage``'s
engage/bounded-``_until``/reset): the displacement arms a bounded reservation,
every authoring tick re-proves the combat it serves, and the swing (or the
honest horizon timeout) releases it.
"""

from typing import Any

#: The bounded reservation horizon (the ROAM_REAIM_HORIZON pattern: a fixed,
#: honest bound - a never-swinging combat intent cannot starve travel forever).
SWING_LEASE_HORIZON_S = 10.0


class SwingLease:
    """One displacement, one bounded reservation; expiry needs a fresh arm.

    ``arm`` names the reservation (the displaced walk class it backs off),
    ``bind`` re-targets a live reservation at a freshly minted combat intent,
    ``expiry`` answers WHY the reservation died (``None`` while it holds) and
    ``release`` clears it plain. The runtime owns the taps; this class owns
    only the lifecycle facts.
    """

    __slots__ = ("_intent", "_map_name", "_origin", "_until")

    def __init__(self) -> None:
        self._origin: str | None = None
        self._intent: Any = None
        self._map_name: str | None = None
        self._until: float | None = None

    def arm(self, origin: str, intent: Any, map_name: str, now: float) -> None:
        self._origin = origin
        self._intent = intent
        self._map_name = map_name
        self._until = now + SWING_LEASE_HORIZON_S

    def bind(self, intent: Any, map_name: str, now: float) -> None:
        """A fresh mint re-targets the reservation (or opens one: the mint is
        the combat authorship the slot must survive until its swing)."""
        self.arm(self._origin or "combat_approach", intent, map_name, now)

    def release(self) -> None:
        self._origin = None
        self._intent = None
        self._map_name = None
        self._until = None

    def origin(self) -> str | None:
        """The reserved walk class the re-authors back off behind."""
        return self._origin

    def expiry(
        self, *, now: float, intent: Any, map_name: str, resting: bool, dead: bool
    ) -> str | None:
        """Why the reservation died: None while every arming condition holds."""
        if self._origin is None or self._until is None:
            return None
        if resting or dead:
            return "rest" if resting else "dead"
        if map_name != self._map_name:
            return "map"
        if intent is not self._intent:
            return "intent"
        if now >= self._until:
            return "timeout"
        return None
