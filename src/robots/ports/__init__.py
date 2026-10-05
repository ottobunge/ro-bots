"""Ports: the interfaces the application core depends on. Nothing else.

An adapter that satisfies a port is any class implementing its protocol —
no inheritance required (structural typing via ``runtime_checkable`` only
where tests need isinstance).
"""

from typing import Any, Protocol, runtime_checkable

from robots.domain.actions import GameAction
from robots.domain.farm import MobInfo
from robots.domain.model import BotState


@runtime_checkable
class DecisionModel(Protocol):
    """A typed decision model (Clef/Jev SystemOne API shape).

    Given a SystemOne request (state + typed questions), return the answers
    mapping question id -> answer object, in ONE call. Implementations must
    be cheap enough to call every tick for every bot.
    """

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        """Return ``{"answers": {qid: {...}}}`` for a SystemOne request."""
        ...


@runtime_checkable
class ChatGenerator(Protocol):
    """Generates free-form chat text when the decision model escalated."""

    def generate_chat(self, prompt: str) -> str:
        """Return one short in-character chat line."""
        ...


@runtime_checkable
class ActionAdvisor(Protocol):
    """Optional reasoning advisor for complex, low-confidence decisions."""

    def advise(self, state: BotState, question: str, options: list[str]) -> int | None:
        """Return the chosen option index, or None to keep the model's answer."""
        ...


@runtime_checkable
class GameClient(Protocol):
    """The world as seen by one bot: send actions, receive state snapshots.

    Concrete adapter: the rAthena clientless wire-protocol session.
    Test double: a scripted fake.
    """

    def poll_state(self) -> BotState:
        """Snapshot the bot's current perception of the world."""
        ...

    def act(self, action: GameAction) -> None:
        """Execute one action in the world (send packets)."""
        ...


@runtime_checkable
class TickClock(Protocol):
    """Time source for the tick loop (separable for deterministic tests)."""

    def sleep(self, seconds: float) -> None: ...
    def monotonic(self) -> float: ...


@runtime_checkable
class MobDatabase(Protocol):
    """Read-only view over the server's mob DB (rAthena mob_db via adapter)."""

    def mobs_on_map(self, map_name: str) -> tuple[MobInfo, ...]:
        """Mob population of a map, strongest last."""
        ...

    def by_name(self, name: str) -> MobInfo | None:
        """Look one mob up by name; None if unknown."""
        ...
