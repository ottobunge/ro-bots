"""Visible EXP alternatives for plans authored on an exp-less species."""

from typing import TYPE_CHECKING

from robots.app.combat_survival import survivable_targets
from robots.app.target_species import species_score, trace_expless_skips

if TYPE_CHECKING:
    from robots.app.trace_log import TraceLog
    from robots.domain.model import ActorRef, BotState
    from robots.ports import MobDatabase


def visible_farm_targets(
    state: BotState,
    species: tuple[str, ...],
    mob_db: MobDatabase | None,
    trace: TraceLog | None = None,
) -> list[ActorRef]:
    """Retarget confirmed exp-less plans; unknown rewards retain their contract.

    Plant-only views remain viable. Only received, survivable EXP alternatives
    can displace them; runtime dispatch retains ownership of walkability.
    """
    targets = [actor for actor in state.nearby_monsters if actor.name in species]
    if not species or not all(species_score(name, mob_db)[0] for name in species):
        return targets
    alternatives = survivable_targets(
        state,
        [actor for actor in state.nearby_monsters if species_score(str(actor.name), mob_db)[1] < 0],
        mob_db,
        trace,
    )
    if not alternatives:
        return targets
    best = min(alternatives, key=lambda actor: species_score(str(actor.name), mob_db))
    trace_expless_skips(
        (str(actor.name) for actor in targets),
        str(best.name),
        mob_db,
        trace,
        source="farm_retarget",
        map_name=state.map_name,
    )
    return alternatives
