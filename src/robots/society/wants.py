"""Sims-style wants (docs/wants-design.md): 0-100 scores, decay, satisfaction.

Each agent carries nine wants; scores decay per game-hour at personality-
modulated rates and game actions satisfy them. The decide context carries a
compact want block (``decide_block``, <=150 tokens) so Clef can choose
actions that serve the most-pressing want. CharSwitch is special: an itch
with session/group/grass-is-greener triggers, satisfied only by actually
switching or creating a character, with a vanishing-probability creation
roll (``roll_character_choice``) gated on ``itch > 80``.

Pure module: no I/O, no world state — the tests stay offline. The runtime
observes events and calls :meth:`WantSatisfier.apply` /
:meth:`WantState.decay`; actuation (the actual switch/creation packets) is a
later slice per design section 5 item 4.
"""

import math
import random
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Protocol, final

OFFLINE_DECAY_FACTOR: Final = 0.25  # offline wants decay at 25% rate
DEFAULT_SCORE: Final = 50.0  # fresh agent: neither satisfied nor starving
WANT_LINE_COUNT: Final = 5  # the decide block's wants line shows the lowest N
TOP_URGENCY_COUNT: Final = 3  # criteria offered to which_want_to_serve
SESSION_FREE_HOURS: Final = 2.0  # itch hours are free up to the second hour
SESSION_ITCH_RATE: Final = 2.0  # +2/h per full session hour beyond the second
NEW_GROUP_ITCH_RATE: Final = 5.0  # +5/h while no member has a level-30 char
GRASS_IS_GREENER_RATE: Final = 2.0  # +2/h when another char is within 5 levels
GRASS_IS_GREENER_LEVELS: Final = 5
FRIEND_ANNOUNCE_ITCH: Final = 3.0  # one-shot, on a friend's announced switch
CHAR_SWITCH_ROLL_THRESHOLD: Final = 80.0  # the creation roll gates on itch > 80
CREATE_ROLL_BASE: Final = 0.10  # p_create = 0.10 * create_factor * headroom
FAST_DECAY_ARROW_RATIO: Final = 1.25  # "↓↓" above 1.25x the personality base
STABLE_ARROW_MIN_RATE: Final = 0.5  # below this per-hour decay shows "→"


class Want(StrEnum):
    """The nine wants; scores are 0 (unsatisfied) .. 100 (satisfied)."""

    POWER = "Power"
    WEALTH = "Wealth"
    EQUIPMENT = "Equipment"
    SOCIAL = "Social"
    NOVELTY = "Novelty"
    COMFORT = "Comfort"
    COMPETENCE = "Competence"
    FRIENDSHIP = "Friendship"
    CHAR_SWITCH = "CharSwitch"


# Design section 1: base decay per game-hour while online.
BASE_DECAY_PER_HOUR: Final[dict[Want, float]] = {
    Want.POWER: 6.0,
    Want.WEALTH: 4.0,
    Want.EQUIPMENT: 3.0,
    Want.SOCIAL: 5.0,
    Want.NOVELTY: 4.0,
    Want.COMFORT: 3.0,
    Want.COMPETENCE: 4.0,
    Want.FRIENDSHIP: 2.0,
    Want.CHAR_SWITCH: 1.0,
}

# CharSwitch is reported on its own decide line, so urgency ranking and the
# wants line cover the other eight.
RANKED_WANTS: Final[tuple[Want, ...]] = tuple(want for want in Want if want is not Want.CHAR_SWITCH)

# One-line notes for the review's which_want_to_serve criteria (brain wiring).
WANT_SERVE_CRITERIA: Final[dict[Want, str]] = {
    Want.POWER: "Level up: grind mobs, share party EXP, do quests.",
    Want.WEALTH: "Accumulate zeny: loot, sell, avoid purchases.",
    Want.EQUIPMENT: "Advance the build: buy/loot/equip planned gear.",
    Want.SOCIAL: "Belong: join a party, chat, buff friends.",
    Want.NOVELTY: "Variety: travel, try a new map or activity.",
    Want.COMFORT: "Safety and downtime: idle in town, rest, avoid danger.",
    Want.COMPETENCE: "Mastery: solo kills, fight above my level.",
    Want.FRIENDSHIP: "Bonds: meet friends on their map, help them.",
    Want.CHAR_SWITCH: "Play another roster character (or create one).",
}


@final
@dataclass(frozen=True, slots=True)
class PersonalityProfile:
    """Decay multipliers (higher = that want starves faster) + roster cap."""

    multipliers: dict[Want, float]
    char_cap: int
    create_factor: float


class Personality(StrEnum):
    """The six personality types of design section 3."""

    ACHIEVER = "Achiever"
    SOCIALIZER = "Socializer"
    EXPLORER = "Explorer"
    TYCOON = "Tycoon"
    CASUAL = "Casual"
    COMPETITOR = "Competitor"

    @property
    def profile(self) -> PersonalityProfile:
        """The design-table row for this personality."""
        return PERSONALITY_PROFILES[self]


# Verbatim rows from docs/wants-design.md section 3: (Power, Wealth, Equip,
# Social, Novelty, Comfort, Competence, Friend, CharSwitch, cap, create).
_DESIGN_ROWS: Final[dict[Personality, tuple[float, ...]]] = {
    Personality.ACHIEVER: (2.0, 1.2, 1.3, 0.6, 0.8, 0.5, 1.5, 0.7, 1.0, 4, 0.6),
    Personality.SOCIALIZER: (0.5, 0.7, 0.8, 2.0, 1.0, 1.2, 0.6, 2.0, 1.4, 6, 1.2),
    Personality.EXPLORER: (1.0, 0.8, 1.0, 0.8, 2.0, 0.4, 1.2, 0.9, 1.3, 5, 1.0),
    Personality.TYCOON: (0.8, 2.0, 1.5, 0.7, 1.2, 0.8, 0.9, 0.8, 0.9, 4, 0.5),
    Personality.CASUAL: (0.4, 0.6, 0.7, 1.2, 1.5, 2.0, 0.5, 1.1, 1.2, 6, 1.1),
    Personality.COMPETITOR: (1.5, 1.0, 1.1, 0.9, 0.9, 0.3, 2.0, 0.8, 0.8, 5, 0.7),
}

PERSONALITY_PROFILES: Final[dict[Personality, PersonalityProfile]] = {
    personality: PersonalityProfile(
        multipliers={
            want: row[index] for index, want in enumerate(Want) if want is not Want.CHAR_SWITCH
        }
        | {Want.CHAR_SWITCH: row[8]},
        char_cap=int(row[9]),
        create_factor=row[10],
    )
    for personality, row in _DESIGN_ROWS.items()
}


def assign_personalities(rng: random.Random, count: int) -> tuple[Personality, ...]:
    """Draw ``count`` personalities; friend groups are guaranteed a mix.

    Design section 3: groups mix personalities ("a Socializer in an Achiever
    group is the interesting case"), so any draw of two or more contains at
    least two distinct personalities.
    """
    if count <= 0:
        return ()
    pool = list(Personality)
    first = rng.choice(pool)
    if count == 1:
        return (first,)
    second = rng.choice([p for p in pool if p is not first])
    rest = tuple(rng.choice(pool) for _ in range(count - 2))
    return (first, second, *rest)


class RandomSource(Protocol):
    """The one method WantState needs from random.Random (test-seedable)."""

    def random(self) -> float: ...


@final
@dataclass(frozen=True, slots=True)
class WantEvent:
    """One observed game event, normalized for the satisfaction map.

    ``name`` carries the map/species name for first-seen novelty; ``zeny``
    the sell/buy amount; ``level_gap`` mob level minus agent level; ``solo``
    and ``higher_level`` qualify kills.
    """

    kind: str
    zeny: int = 0
    level_gap: int = 0
    solo: bool = False
    higher_level: bool = False
    name: str = ""


@final
class WantState:
    """One agent's nine want scores plus its CharSwitch itch bookkeeping."""

    def __init__(
        self,
        personality: Personality,
        *,
        scores: dict[Want, float] | None = None,
        roster_size: int = 1,
        other_char_levels: tuple[int, ...] = (),
        current_level: int = 10,
        group_is_new: bool = False,
        partyless_hours: float = 0.0,
        online_friends: tuple[str, ...] = (),
    ) -> None:
        self.personality = personality
        given = scores or {}
        self.scores: dict[Want, float] = {
            want: float(given.get(want, DEFAULT_SCORE)) for want in Want
        }
        self.roster_size = roster_size
        self.other_char_levels = other_char_levels
        self.current_level = current_level
        self.group_is_new = group_is_new
        self.partyless_hours = partyless_hours
        self.online_friends = online_friends
        self.session_hours = 0.0
        self.reasons: deque[tuple[str, float, str]] = deque(maxlen=32)
        self.seen_maps: set[str] = set()
        self.seen_species: set[str] = set()
        # want -> (applied decay per hour of the last decay() call, base rate)
        self._trend: dict[Want, tuple[float, float]] = dict.fromkeys(Want, (0.0, 0.0))

    # ------------------------------------------------------------ decay
    def decay(self, hours_online: float, offline_hours: float = 0.0) -> None:
        """Apply one interval of want decay (design section 1 and 2).

        Online wants decay at the personality-modulated base rate; offline
        hours decay at 25% ("characters miss their agent"). The CharSwitch
        itch adds its session-length / group-new / grass-is-greener rates on
        top of its base before the personality multiplier.
        """
        if hours_online < 0 or offline_hours < 0:
            msg = "decay hours must be non-negative"
            raise ValueError(msg)
        boost_hours = float(self._grow_session(hours_online))
        multipliers = self.personality.profile.multipliers
        for want in Want:
            base = BASE_DECAY_PER_HOUR[want] * multipliers[want]
            delta = base * hours_online
            if want is Want.CHAR_SWITCH:
                # design section 2: the trigger rates add to the base decay
                # before the personality multiplier; the session boost accrues
                # per full hour beyond the second.
                trigger_rate = BASE_DECAY_PER_HOUR[want]
                if self.group_is_new:
                    trigger_rate += NEW_GROUP_ITCH_RATE
                if self.grass_is_greener():
                    trigger_rate += GRASS_IS_GREENER_RATE
                delta = multipliers[want] * (
                    trigger_rate * hours_online + SESSION_ITCH_RATE * boost_hours
                )
            delta += base * OFFLINE_DECAY_FACTOR * offline_hours
            self._apply(want, -delta, max(hours_online + offline_hours, 1e-9))

    def _grow_session(self, hours_online: float) -> int:
        """Full session hours beyond the second, accrued by this interval."""
        before = max(0, math.floor(self.session_hours) - int(SESSION_FREE_HOURS))
        self.session_hours += hours_online
        after = max(0, math.floor(self.session_hours) - int(SESSION_FREE_HOURS))
        return after - before

    def _apply(self, want: Want, delta: float, hours: float) -> None:
        before = self.scores[want]
        self.scores[want] = min(100.0, max(0.0, before + delta))
        self._trend[want] = (abs(self.scores[want] - before) / hours, BASE_DECAY_PER_HOUR[want])

    # -------------------------------------------------------- satisfaction
    def satisfy(self, want: Want, amount: float, reason: str) -> None:
        """Add ``amount`` to one want, clamped to [0, 100]; record the why."""
        self.scores[want] = min(100.0, max(0.0, self.scores[want] + amount))
        self.reasons.append((want.value, amount, reason))

    def note_friend_switch_announce(self) -> None:
        """One-shot itch when a friend announces a character change in chat."""
        self.satisfy(Want.CHAR_SWITCH, FRIEND_ANNOUNCE_ITCH, "friend announced a character change")

    # ------------------------------------------------------------- urgency
    def _urgency(self, want: Want) -> float:
        """score x decay pressure: lower means more urgent (section 4)."""
        return (
            self.scores[want]
            * BASE_DECAY_PER_HOUR[want]
            * self.personality.profile.multipliers[want]
        )

    def top_wants(self, count: int = TOP_URGENCY_COUNT) -> list[tuple[Want, float]]:
        """The ``count`` most urgent non-CharSwitch wants, most urgent first."""
        ranked = sorted(RANKED_WANTS, key=self._urgency)[:count]
        return [(want, self.scores[want]) for want in ranked]

    def top_want(self) -> tuple[Want, float]:
        """The single most urgent want and its current score."""
        return self.top_wants(1)[0]

    # -------------------------------------------------------- decide block
    def decide_block(self) -> str:
        """The <=150-token want block injected into every decide request."""
        lowest = sorted(RANKED_WANTS, key=lambda want: self.scores[want])[:WANT_LINE_COUNT]
        parts = [f"{want.value} {self.scores[want]:.0f}{self._arrow(want)}" for want in lowest]
        itch = self.scores[Want.CHAR_SWITCH]
        group_note = " (group is new: no member >= level 30)" if self.group_is_new else ""
        return "\n".join(
            (
                "wants: " + " ".join(parts),
                "top_want: " + self._top_want_line(),
                f"char_switch_itch: {itch:.0f}{group_note}",
            )
        )

    def _top_want_line(self) -> str:
        want, score = self.top_want()
        text = f"{want.value} {score:.0f}"
        context = "; ".join(self._situational_notes())
        return f"{text} ({context})" if context else text

    def _situational_notes(self) -> list[str]:
        notes: list[str] = []
        if self.partyless_hours >= 1.0:
            notes.append(f"partyless for {self.partyless_hours:.0f}h")
        if self.online_friends:
            notes.append(f"friends {'+'.join(self.online_friends)} online")
        return notes

    def _arrow(self, want: Want) -> str:
        rate, base = self._trend[want]
        if rate < STABLE_ARROW_MIN_RATE:
            return "→"
        if base > 0 and rate > base * FAST_DECAY_ARROW_RATIO:
            return "↓↓"
        return "↓"

    # ------------------------------------------------------ creation roll
    def grass_is_greener(self) -> bool:
        """True when another roster character is within 5 levels of mine."""
        return any(
            abs(level - self.current_level) <= GRASS_IS_GREENER_LEVELS
            for level in self.other_char_levels
        )

    def creation_probability(self) -> float:
        """p_create; zero unless the itch exceeds the roll threshold."""
        if self.scores[Want.CHAR_SWITCH] <= CHAR_SWITCH_ROLL_THRESHOLD:
            return 0.0
        headroom = max(0.0, 1.0 - self.roster_size / self.personality.profile.char_cap)
        return CREATE_ROLL_BASE * self.personality.profile.create_factor * headroom

    def roll_character_choice(self, rng: RandomSource) -> str:
        """The vanishing roll: "create", "switch", or "none" below threshold.

        A failed roll means the agent switches to an existing roster
        character instead (actuation is the later slice; design section 5).
        """
        if self.scores[Want.CHAR_SWITCH] <= CHAR_SWITCH_ROLL_THRESHOLD:
            return "none"
        return "create" if rng.random() < self.creation_probability() else "switch"


# -- the event -> satisfaction map (design section 1 "Satisfied by") --------


def _satisfy_combat(want_state: WantState, event: WantEvent) -> None:
    match event.kind:
        case "kill":
            want_state.satisfy(Want.POWER, 3.0 if event.higher_level else 1.0, "kill")
            if event.solo:
                want_state.satisfy(Want.COMPETENCE, 2.0, "solo kill")
            if event.level_gap >= 5:
                want_state.satisfy(Want.COMPETENCE, 10.0, "killed 5+ levels above")
        case "quest_turn_in":
            want_state.satisfy(Want.POWER, 20.0, "quest turn-in")
        case "level_up":
            want_state.satisfy(Want.POWER, 25.0, "level up")
        case "death":
            want_state.satisfy(Want.COMFORT, -25.0, "died")
            want_state.satisfy(Want.WEALTH, -5.0, "death penalty")
            want_state.satisfy(Want.EQUIPMENT, -4.0, "death setback")
            want_state.satisfy(Want.COMPETENCE, -15.0, "died")
        case "hp_low":
            want_state.satisfy(Want.COMFORT, -3.0, "HP below 25%")
        case _:
            msg = f"unknown want event kind: {event.kind}"
            raise ValueError(msg)


def _satisfy_social(want_state: WantState, event: WantEvent) -> None:
    amounts: dict[str, tuple[Want, float, str]] = {
        "party_join": (Want.SOCIAL, 15.0, "joined a party"),
        "invite_received": (Want.SOCIAL, 8.0, "received a party invite"),
        "chat_exchange": (Want.SOCIAL, 3.0, "party chat exchange"),
        "buff_friend": (Want.SOCIAL, 4.0, "buffed or healed a friend"),
        "group_objective": (Want.SOCIAL, 5.0, "group objective step"),
        "friend_copresence": (Want.FRIENDSHIP, 1.0, "co-present on a map"),
        "friend_joint_kill": (Want.FRIENDSHIP, 2.0, "joint kill"),
        "friend_party": (Want.FRIENDSHIP, 4.0, "partied together"),
        "friend_gift": (Want.FRIENDSHIP, 6.0, "received help or a gift"),
    }
    match = amounts.get(event.kind)
    if match is None:
        msg = f"unknown want event kind: {event.kind}"
        raise ValueError(msg)
    want, amount, reason = match
    want_state.satisfy(want, amount, reason)
    if event.kind == "party_join":
        want_state.partyless_hours = 0.0


def _satisfy_economy(want_state: WantState, event: WantEvent) -> None:
    amounts: dict[str, tuple[Want, float, str]] = {
        "buy": (Want.WEALTH, -10.0, "bought an item"),
        "buy_failed": (Want.EQUIPMENT, -5.0, "failed purchase"),
        "loot_valuable": (Want.WEALTH, 2.0, "looted something valuable"),
        "loot_wanted": (Want.EQUIPMENT, 8.0, "looted a wanted item"),
        "equip_planned": (Want.EQUIPMENT, 20.0, "equipped a planned item"),
        "budget_tier": (Want.EQUIPMENT, 10.0, "zeny crossed a budget tier"),
        "quest_reward": (Want.WEALTH, 10.0, "quest reward"),
    }
    if event.kind == "sell":
        want_state.satisfy(Want.WEALTH, event.zeny / 10.0, "sold items")
        return
    match = amounts.get(event.kind)
    if match is None:
        msg = f"unknown want event kind: {event.kind}"
        raise ValueError(msg)
    want, amount, reason = match
    want_state.satisfy(want, amount, reason)


def _satisfy_exploration(want_state: WantState, event: WantEvent) -> None:
    if event.kind == "map_change":
        if event.name not in want_state.seen_maps:
            want_state.seen_maps.add(event.name)
            want_state.satisfy(Want.NOVELTY, 12.0, f"new map {event.name}")
        return
    if event.kind == "new_species":
        if event.name not in want_state.seen_species:
            want_state.seen_species.add(event.name)
            want_state.satisfy(Want.NOVELTY, 6.0, f"new monster {event.name}")
        return
    amounts: dict[str, tuple[Want, float, str]] = {
        "quest_new": (Want.NOVELTY, 15.0, "new quest"),
        "activity_change": (Want.NOVELTY, 4.0, "changed activity"),
        "rest_town": (Want.COMFORT, 2.0, "idling in town"),
        "kafra_rest": (Want.COMFORT, 10.0, "Kafra rest"),
        "safe_activity": (Want.COMFORT, 1.0, "safe low-risk activity"),
    }
    match = amounts.get(event.kind)
    if match is None:
        msg = f"unknown want event kind: {event.kind}"
        raise ValueError(msg)
    want, amount, reason = match
    want_state.satisfy(want, amount, reason)


def _satisfy_char_switch(want_state: WantState, event: WantEvent) -> None:
    amounts: dict[str, tuple[float, str]] = {
        "roster_switch": (60.0, "logged another roster character"),
        "character_created": (100.0, "created a new character"),
    }
    match = amounts.get(event.kind)
    if match is None:
        msg = f"unknown want event kind: {event.kind}"
        raise ValueError(msg)
    amount, reason = match
    want_state.satisfy(Want.CHAR_SWITCH, amount, reason)


_HANDLERS: Final[dict[str, Callable[[WantState, WantEvent], None]]] = {
    "kill": _satisfy_combat,
    "level_up": _satisfy_combat,
    "quest_turn_in": _satisfy_combat,
    "death": _satisfy_combat,
    "hp_low": _satisfy_combat,
    "party_join": _satisfy_social,
    "invite_received": _satisfy_social,
    "chat_exchange": _satisfy_social,
    "buff_friend": _satisfy_social,
    "group_objective": _satisfy_social,
    "friend_copresence": _satisfy_social,
    "friend_joint_kill": _satisfy_social,
    "friend_party": _satisfy_social,
    "friend_gift": _satisfy_social,
    "sell": _satisfy_economy,
    "buy": _satisfy_economy,
    "buy_failed": _satisfy_economy,
    "loot_valuable": _satisfy_economy,
    "loot_wanted": _satisfy_economy,
    "equip_planned": _satisfy_economy,
    "budget_tier": _satisfy_economy,
    "quest_reward": _satisfy_economy,
    "map_change": _satisfy_exploration,
    "new_species": _satisfy_exploration,
    "quest_new": _satisfy_exploration,
    "activity_change": _satisfy_exploration,
    "rest_town": _satisfy_exploration,
    "kafra_rest": _satisfy_exploration,
    "safe_activity": _satisfy_exploration,
    "roster_switch": _satisfy_char_switch,
    "character_created": _satisfy_char_switch,
}


@final
class WantSatisfier:
    """The pure event -> want-satisfaction map (design section 5 item 2)."""

    @staticmethod
    def apply(want_state: WantState, event: WantEvent) -> None:
        """Apply one observed event to a want state (offline-testable)."""
        handler = _HANDLERS.get(event.kind)
        if handler is None:
            msg = f"unknown want event kind: {event.kind}"
            raise ValueError(msg)
        handler(want_state, event)
