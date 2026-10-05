"""World events: the things that wake a bot up while a script runs.

The loop never calls the decision model "just because a tick passed" — only
events, timers, and periodic goal reviews reach Clef. While traveling,
grinding, or farming, the behavior script runs; events interrupt it (subject
to the active FarmPlan's interrupt rules).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Union

from robots.domain.model import ActorRef, ChatLine, PartyInvite


@dataclass(frozen=True, slots=True)
class MonsterSpotted:
    """A monster entered perception radius (aggressive=None: unknown yet)."""

    actor: ActorRef
    aggressive: bool | None = None


@dataclass(frozen=True, slots=True)
class DamageTaken:
    amount: int
    from_id: int | None = None


@dataclass(frozen=True, slots=True)
class ChatHeard:
    line: ChatLine


@dataclass(frozen=True, slots=True)
class ItemSeen:
    item: str
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class InviteReceived:
    invite: PartyInvite


@dataclass(frozen=True, slots=True)
class Arrived:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class ScriptFailed:
    reason: str


@dataclass(frozen=True, slots=True)
class Heartbeat:
    """Periodic review trigger — the only non-event that reaches Clef."""

    seq: int


@dataclass(frozen=True, slots=True)
class TimerFired:
    """A randomized timer elapsed (e.g. 'time since last action')."""

    name: str
    seq: int


@dataclass(frozen=True, slots=True)
class PlanExpired:
    """A farming (or other planned) session ran out its Clef-chosen duration."""

    plan_id: int


# Union written explicitly (not `|`) so pattern matching sees a plain union
# type; ruff's UP007 is deliberately ignored for this alias.
WorldEvent = Union[  # noqa: UP007
    MonsterSpotted,
    DamageTaken,
    ChatHeard,
    ItemSeen,
    InviteReceived,
    Arrived,
    ScriptFailed,
    Heartbeat,
    TimerFired,
    PlanExpired,
]


_MOOD = {True: "aggressive", False: "passive", None: "unknown"}


def _summary_monster(event: MonsterSpotted) -> str:
    mood = _MOOD.get(event.aggressive, "unknown")
    return f"monster {event.actor.name} ({mood}) at distance {event.actor.distance:.0f}"


def _summary_damage(event: DamageTaken) -> str:
    src = event.from_id if event.from_id is not None else "unknown"
    return f"took {event.amount} damage from {src}"


def _summary_chat(event: ChatHeard) -> str:
    return f"[{event.line.channel}] {event.line.sender} said: {event.line.text}"


def _summary_item(event: ItemSeen) -> str:
    return f"item {event.item} dropped at ({event.x},{event.y})"


def _summary_invite(event: InviteReceived) -> str:
    return f"party invite from {event.invite.from_name}"


def _summary_arrived(event: Arrived) -> str:
    return f"arrived at ({event.x},{event.y})"


def _summary_failed(event: ScriptFailed) -> str:
    return f"current plan failed: {event.reason}"


def _summary_heartbeat(event: Heartbeat) -> str:
    return f"periodic review #{event.seq}"


def _summary_timer(event: TimerFired) -> str:
    return f"timer '{event.name}' fired (#{event.seq})"


def _summary_plan_expired(event: PlanExpired) -> str:
    return f"farming session #{event.plan_id} ended"


_SUMMARY_BY_KIND: dict[type[Any], Callable[[Any], str]] = {
    MonsterSpotted: _summary_monster,
    DamageTaken: _summary_damage,
    ChatHeard: _summary_chat,
    ItemSeen: _summary_item,
    InviteReceived: _summary_invite,
    Arrived: _summary_arrived,
    ScriptFailed: _summary_failed,
    Heartbeat: _summary_heartbeat,
    TimerFired: _summary_timer,
    PlanExpired: _summary_plan_expired,
}


def event_summary(event: WorldEvent) -> str:
    """Compact one-line description injected into the decision state."""
    summary_fn: Callable[[Any], str] = _SUMMARY_BY_KIND[type(event)]
    return summary_fn(event)
