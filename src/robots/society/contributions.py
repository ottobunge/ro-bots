"""Human-player contribution observation folded into the relationship ledger.

The wire-facing half of the human friendship score (the ledger stays
world-state-free, its own documented contract): every tick the runtime hands
this observer the live party roster (char name -> AID) plus the drained
:class:`~robots.domain.model.PartyObservation` rows, and the observer decides

- **who is a human**: the persona roster — names registered on the ledger are
  agents (``seed_roster`` registers the whole population); every other party
  member is a human player. The bot's own name is a roster name, so it can
  never credit itself.
- **what counts**: human damage on non-party targets (the bot-dealt damage
  rows already exist on the wire; the human-dealt ones name the human as the
  source), human heal/buff casts on party members (ZC_USE_SKILL), and the
  party's shared exp flowing in while a human is present (exp-share
  participation). Each folds into ``record_contribution`` — useful play
  raises the score.
- **dead weight**: a party window (``DEAD_WEIGHT_WINDOW_S``) with a human
  present and nothing contributed scores one dead-weight step and restarts
  the window; the score itself decays toward neutral on the ledger's weekly
  half-life.

At the review cadence (the brain's heartbeat review) accumulated material
deltas (``|delta| >= GOSSIP_THRESHOLD``) are published to the ledger's group
rows and their allied-group gossip hop, and returned as report lines — which
the brain emits ONLY as in-game party/public chat premades. No other agent's
ledger is ever touched from here: they update from what they HEAR.
"""

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, final

from robots.domain.model import PartyObservation
from robots.society.relations import (
    GOSSIP_THRESHOLD,
    RelationshipLedger,
    human_report_line,
)

DEAD_WEIGHT_WINDOW_S: Final = 600.0  # one quiet party window = one dead-weight step
MAX_REPORTS_PER_REVIEW: Final = 1  # one gossip line per review: no chat floods
HUMAN_LINES_CAP: Final = 4  # the bounded party-human decide lines
HEAL_SKILL_IDS: Final = frozenset({28})  # AL_HEAL: the cast-on-party heal skill
PARTY_HUMAN_EPS: Final = 1e-9


@final
@dataclass(frozen=True, slots=True)
class HumanReport:
    """One reviewed human verdict, with its in-game premade line."""

    human_name: str
    delta: float
    line: str


@final
class HumanContributionObserver:
    """One agent's witnessed human-party contributions -> RelationshipLedger."""

    def __init__(
        self,
        ledger: RelationshipLedger,
        persona_id: str,
        *,
        dead_weight_window_s: float = DEAD_WEIGHT_WINDOW_S,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._ledger = ledger
        self._persona_id = persona_id
        self._window_s = dead_weight_window_s
        self._clock = clock
        self._presence: dict[str, float] = {}  # human -> window start ts
        self._contributed: dict[str, float] = {}  # human -> last contribution ts
        self._pending: set[str] = set()  # humans with an unpublished material crossing
        self._reported: dict[str, float] = {}  # human -> score level at last publication

    # -- per-tick ingest -------------------------------------------------------

    def observe(
        self,
        *,
        party: Mapping[str, int],
        observations: Sequence[PartyObservation] = (),
        ts: float | None = None,
    ) -> None:
        """Fold one tick's party roster and wire observations into the ledger."""
        now = self._clock() if ts is None else ts
        by_aid = {aid: name for name, aid in party.items()}
        self._update_presence(party, now)
        for row in observations:
            self._fold(row, by_aid, now)

    def _update_presence(self, party: Mapping[str, int], now: float) -> None:
        """Track the humans currently in the party; departures leave cleanly."""
        humans = {name for name in party if self._ledger.persona_of(name) is None}
        for name in humans:
            self._presence.setdefault(name, now)
        for departed in list(self._presence):
            if departed not in humans:
                del self._presence[departed]
                self._contributed.pop(departed, None)

    def _fold(self, row: PartyObservation, by_aid: Mapping[int, str], now: float) -> None:
        if row.kind == "exp":
            self._fold_exp(row, now)
            return
        source = by_aid.get(row.source_id)
        if source is None or self._ledger.persona_of(source) is not None:
            return  # not a party member, or an agent (never a human, never me)
        if row.kind == "damage":
            if row.target_id not in by_aid:
                self._record(source, "damage", now)
        elif row.kind == "skill":
            self._fold_skill(row, by_aid, source, now)

    def _fold_exp(self, row: PartyObservation, now: float) -> None:
        """The party's shared exp: no source actor on the wire, so every
        present human is credited before any source-attribution gate."""
        if row.amount > 0:
            for human in sorted(self._presence):
                self._record(human, "exp_share", now)

    def _fold_skill(
        self, row: PartyObservation, by_aid: Mapping[int, str], source: str, now: float
    ) -> None:
        """A cast by a human: on a party member it's a heal/buff, on a mob it
        is offensive contribution too."""
        if row.failed:
            return
        if row.target_id in by_aid:
            kind = "heal" if row.skill_id in HEAL_SKILL_IDS else "buff"
        else:
            kind = "damage"
        self._record(source, kind, now)

    def _record(self, human_name: str, kind: str, now: float) -> None:
        self._ledger.record_contribution(human_name, kind, ts=now)
        self._contributed[human_name] = now
        share = self._ledger.human_score(human_name) - self._reported.get(human_name, 0.0)
        if abs(share) >= GOSSIP_THRESHOLD:
            self._pending.add(human_name)

    # -- review cadence ----------------------------------------------------------

    def review(self, *, ts: float | None = None) -> tuple[HumanReport, ...]:
        """The review-cadence pass: dead-weight windows, then the gossip reports.

        Publishing a report moves the ledger's group row and its allied-group
        gossip hop (the reporter's own belief); the returned reports are the
        in-game premade lines the brain must emit as party/public chat —
        never a direct mutation of anyone else's ledger.
        """
        now = self._clock() if ts is None else ts
        for human, window_start in sorted(self._presence.items()):
            quiet_since = max(window_start, self._contributed.get(human, 0.0))
            if now - quiet_since >= self._window_s:
                self._record(human, "dead_weight", now)
                self._presence[human] = now  # the window restarts from the verdict
        # The share carries everything scored since the last publication, so
        # the group row mirrors the score instead of lagging behind it.
        shares = [
            (human, self._ledger.human_score(human) - self._reported.get(human, 0.0))
            for human in self._pending
        ]
        shares.sort(key=lambda item: (-abs(item[1]), item[0]))
        reports: list[HumanReport] = []
        for human, delta in shares[:MAX_REPORTS_PER_REVIEW]:
            group_id = self._ledger.group_of(self._persona_id)
            if group_id is not None:
                self._ledger.gossip_human(human, delta, group_id=group_id, ts=now)
            reports.append(HumanReport(human, delta, human_report_line(human, delta)))
            self._reported[human] = self._ledger.human_score(human)
            self._pending.discard(human)
        return tuple(reports)

    # -- decide context ----------------------------------------------------------

    def party_human_lines(self) -> list[str]:
        """The bounded standing lines for the humans currently in the party."""
        lines = [
            (name, self._ledger.human_score(name))
            for name in self._presence
            if self._ledger.persona_of(name) is None
        ]
        lines.sort(key=lambda item: (-abs(item[1]), item[0]))
        return [f"party human {name} {value:+.2f}" for name, value in lines[:HUMAN_LINES_CAP]]
