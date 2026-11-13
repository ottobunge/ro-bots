"""Conservative engagement admission from received SELF HP and species hits."""

import logging
from collections import deque
from typing import TYPE_CHECKING

from robots.app.target_species import species_score

if TYPE_CHECKING:
    from robots.adapters.native_gameplay import ObservedDamage
    from robots.app.trace_log import TraceLog
    from robots.domain.model import ActorRef, BotState
    from robots.ports import MobDatabase

logger = logging.getLogger(__name__)
RECENT_SPECIES_DAMAGE_S = 120.0
MIN_ENGAGE_HP_RATIO = 0.40
MAX_HIT_HP_RATIO = 0.30


class SpeciesDamage:
    """Bounded session-local hits; warps/respawns cannot erase recent species risk."""

    def __init__(self) -> None:
        self._hits: deque[tuple[float, str, int]] = deque(maxlen=128)

    def clear(self) -> None:
        self._hits.clear()

    def receive(
        self, hit: ObservedDamage, own_id: int, species: dict[int, str], now: float
    ) -> None:
        name = species.get(hit.source_id)
        amount = max(0, hit.damage) + max(0, hit.damage2)
        if (
            name is not None
            and hit.target_id in (own_id, (-own_id) & 0xFFFFFFFF)
            and not hit.is_sp_damage
            and hit.damage_type not in (2, 3)
            and amount > 0
        ):
            self._hits.append((now, name, amount))

    def snapshot(self, now: float) -> tuple[tuple[str, int], ...]:
        while self._hits and now - self._hits[0][0] >= RECENT_SPECIES_DAMAGE_S:
            self._hits.popleft()
        peaks: dict[str, int] = {}
        for _, name, amount in self._hits:
            peaks[name] = max(peaks.get(name, 0), amount)
        return tuple(peaks.items())


def survivability_refusal(state: BotState, species: str, mob_db: MobDatabase | None) -> str | None:
    """Unknown species remain eligible; confirmed zero-EXP resources are exempt.

    No catalogue combat stats, projected damage or server internals enter this
    decision. The hit ceiling uses current HP, not maximum HP.
    """
    if species_score(species, mob_db)[0]:
        return None
    if state.hp_ratio < MIN_ENGAGE_HP_RATIO:
        return "low_hp"
    peak = max(
        (amount for name, amount in state.recent_species_damage if name == species), default=0
    )
    return "recent_species_hit" if peak > state.hp * MAX_HIT_HP_RATIO else None


def survivable_targets(
    state: BotState, candidates: list[ActorRef], mob_db: MobDatabase | None, trace: TraceLog | None
) -> list[ActorRef]:
    safe = []
    for target in candidates:
        detail = survivability_refusal(state, str(target.name), mob_db)
        if detail is None:
            safe.append(target)
            continue
        logger.warning(
            "attack_refused reason=no_survivability detail=%s species=%s target_id=%s bot=%s",
            detail,
            target.name,
            target.id,
            state.name,
        )
        if trace is not None:
            trace.log(
                "attack_refused",
                reason="no_survivability",
                detail=detail,
                species=target.name,
                target_id=target.id,
            )
    return safe
