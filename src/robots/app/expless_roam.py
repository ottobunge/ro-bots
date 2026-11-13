"""Per-client escape from a received, sustained zero-EXP combat patch."""

import logging
from typing import TYPE_CHECKING

from robots.app.target_species import species_score
from robots.domain.model import Goal

if TYPE_CHECKING:
    from robots.adapters.native_gameplay import NativeGameplayView, ObservedDamage
    from robots.app.scripts import MerchantReachable
    from robots.domain.model import BotState
    from robots.ports import MobDatabase

logger = logging.getLogger(__name__)

EXPLESS_ROAM_HITS = 20
EXPLESS_ROAM_RADIUS = 24
EXPLESS_ROAM_STALL_S = 60.0
_DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1))


class ExplessRoam:
    """Count landed hits, never authored attacks; suspend commitments while escaping.

    A death among struck actors or a non-zero/unknown-reward hit breaks the
    streak. The outward leg survives script recreation, but no map/epoch
    boundary. Only received positions complete it; a bounded stall rotates
    the next deterministic direction rather than guessing movement.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._hits = 0
        self._struck: set[int] = set()
        self._target: tuple[int, int] | None = None
        self._deadline = 0.0
        self._direction = 0

    def receive(
        self,
        frame: tuple[int, float, int, bytes],
        view: NativeGameplayView,
        own_id: int,
        species: dict[int, str],
        mob_db: MobDatabase,
    ) -> None:
        seq, _, pid, raw = frame
        if pid == 0x0080 and raw[6] == 1:
            target = int.from_bytes(raw[2:6], "little")
            if target in self._struck or target == own_id:
                self.reset()
        if pid == 0x08C8:
            for hit in view.damage:
                if hit.seq == seq and hit.source_id == own_id:
                    self._landed(hit, species.get(hit.target_id, ""), mob_db)

    def _landed(self, hit: ObservedDamage, species: str, mob_db: MobDatabase) -> None:
        if hit.is_sp_damage or hit.damage_type in (2, 3) or hit.damage + hit.damage2 <= 0:
            return
        if not species_score(species, mob_db)[0]:
            self.reset()
        elif self._hits < EXPLESS_ROAM_HITS:
            self._hits += 1
            self._struck.add(hit.target_id)

    def target(
        self, state: BotState, now: float, reachable: MerchantReachable
    ) -> tuple[int, int] | None:
        if self._hits < EXPLESS_ROAM_HITS or state.goal not in (Goal.GRIND, Goal.FARM_ITEM):
            return None
        if self._target == (state.x, state.y):
            self.reset()
            return None
        if self._target is not None and now < self._deadline:
            return self._target
        self._target = self._next_target(state, reachable)
        self._deadline = now + EXPLESS_ROAM_STALL_S
        if self._target is not None:
            logger.warning(
                "roam_anchor_widened_expless bot=%s map=%s landed_hits=%s "
                "radius=%s target=%s rule=sustained_zero_exp_hits",
                state.name,
                state.map_name,
                self._hits,
                EXPLESS_ROAM_RADIUS,
                self._target,
            )
        return self._target

    def _next_target(self, state: BotState, reachable: MerchantReachable) -> tuple[int, int] | None:
        for _ in _DIRECTIONS:
            dx, dy = _DIRECTIONS[self._direction % len(_DIRECTIONS)]
            self._direction += 1
            cell = (state.x + dx * EXPLESS_ROAM_RADIUS, state.y + dy * EXPLESS_ROAM_RADIUS)
            if reachable(state.map_name, (state.x, state.y), cell) is not False:
                return cell
        return None
