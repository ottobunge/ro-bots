"""MechanicsPort (ADR-009): pre-calculated item/skill views for agents.

Mechanics are never modeled by the agent — an adapter over the rAthena
item_db/skill_db turns raw rows into typed digests. One port, three reads.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from robots.domain.build import ItemDigest, SkillDigest


@runtime_checkable
class MechanicsPort(Protocol):
    """Read-only catalog of items and skills, as normalized digests."""

    def item_by_name(self, name: str) -> ItemDigest | None:
        """Look one item up by name; None if unknown."""
        ...

    def items_for_slot(self, slot: str) -> tuple[ItemDigest, ...]:
        """All known items for a slot, weakest (lowest req level) first."""
        ...

    def skills_for_class(self, cls: str) -> tuple[SkillDigest, ...]:
        """Skills learnable by that class, in learn order."""
        ...


def digests_summary(digests: Sequence[ItemDigest]) -> str:
    """Render a sequence of digests as one comma-separated digest-text line."""
    return "; ".join(d.digest_text for d in digests)
