"""The travel routes: the seeded warp routes from the towns to the fields.

The emission-era travel injection proved this route live (prontera south warp
-> prt_fild08 entry). The table is the small seeded configuration the brain
consults when a grind goal fires on a map whose spawns are elsewhere."""

from __future__ import annotations

TRAVEL_ROUTES: dict[str, tuple[tuple[str, int, int], ...]] = {
    "prontera": (
        ("prontera", 156, 22),
        ("prt_fild08", 170, 375),
    ),
}
