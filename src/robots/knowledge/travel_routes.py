"""The travel routes: the seeded warp routes from the towns to the fields.

The emission-era travel injection proved this route live (prontera south warp
-> prt_fild08 entry). The table is the small seeded configuration the brain
consults when a grind goal fires on a map whose spawns are elsewhere.

Leg 37: the table needs EVERY map an agent can wake up on, not just the
town square. A char logs in where it LOGGED OUT (the char table's
``last_map``), so an agent left inside a building by an earlier merchant
trip wakes up in that interior every later leg. ``prt_in`` has no spawn
declaration (no farm plan) and, until now, no route either (no way out):
the goal script's plain GrindScript then patrolled the interior at random
for the whole window - leg 37: 117 distinct random MoveTo targets for one
agent, never the exit door. The route table is the general mechanism for
"a farming goal on a map whose spawns are elsewhere", and prt_in is
exactly such a map.

Pinned public warp bytes (rathena e985006171d2),
npc/warps/cities/prontera.txt:
- ``:24`` ``prontera,156,22,0  warp  prt001  3,2,prt_fild08,170,375`` - the
  field warp;
- ``:40`` ``prt_in,168,124,0  warp  prt05-1  2,1,prontera,174,218`` - the
  interior exit door (the mirror of the cited prt05 entry, :25), the same
  cell the merchant return leg already cites.
"""

from __future__ import annotations

TRAVEL_ROUTES: dict[str, tuple[tuple[str, int, int], ...]] = {
    "prontera": (
        ("prontera", 156, 22),
        ("prt_fild08", 170, 375),
    ),
    "prt_in": (
        ("prt_in", 168, 124),
        ("prontera", 156, 22),
        ("prt_fild08", 170, 375),
    ),
}
