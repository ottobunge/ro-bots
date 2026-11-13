"""Rank public species rewards without discovering actors or map membership."""

import logging
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from robots.app.trace_log import TraceLog
    from robots.ports import MobDatabase

logger = logging.getLogger(__name__)


def species_score(name: str, mob_db: MobDatabase | None) -> tuple[bool, int]:
    """Minimize: confirmed exp-less last, then greatest base + job EXP.

    Missing species or reward data earn no bonus and are never classified as
    exp-less. This is only a preference: even a confirmed zero remains eligible.
    """
    info = mob_db.by_name(name) if mob_db is not None else None
    if info is None or info.base_exp is None or info.job_exp is None:
        return (False, 0)
    return (info.base_exp == 0 and info.job_exp == 0, -(info.base_exp + info.job_exp))


def trace_expless_skips(
    candidates: Iterable[str],
    selected: str,
    mob_db: MobDatabase | None,
    trace: TraceLog | None,
    *,
    source: str,
    map_name: str,
) -> None:
    """Name each rejected zero-EXP species; held targets never call this."""
    if species_score(selected, mob_db)[0]:
        return
    for name in dict.fromkeys(candidates):
        if not species_score(name, mob_db)[0]:
            continue
        reason = "zero_base_and_job_exp"
        logger.info(
            "target_species_skipped_expless species=%s reason=%s "
            "selected_species=%s source=%s map=%s",
            name,
            reason,
            selected,
            source,
            map_name,
        )
        if trace is not None:
            trace.log(
                "target_species_skipped_expless",
                species=name,
                reason=reason,
                selected_species=selected,
                source=source,
                map=map_name,
            )
