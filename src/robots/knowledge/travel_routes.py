"""The travel routes: the exit cells each map's interiors can use.

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

Leg 37, second pass: ``prt_in`` is not one room. It is 26 disconnected
building interiors, and each interior has its OWN exit cell - the 15 cells
below are the doors of the 15 interiors that lead straight to prontera.
A single hard-coded door therefore rescues only the agents that happen to
share that interior: leg 37 woke two agents in the prt05 interior (door
168,124) and one in the prt03 interior (door 53,105), so the one-door
route could only walk two of the three out. The exit is therefore
RESOLVED BY REACHABILITY from the agent's own position (see
``robots.app.travel_routing``): the door is a property of the interior
the agent stands in, not of the map.

Four of the interiors have no door of their own: they reach prontera
through a warp INSIDE prt_in (the prt15/prt16/prt17/prt18/prt19/prt20
hops). Those hops are the second table below; the hop CELL is the way out
of such an interior and the door beyond it is the next interior's
business, resolved when the agent stands there.

Pinned public warp bytes (rathena e985006171d2),
npc/warps/cities/prontera.txt:
- ``:24`` ``prontera,156,22,0  warp  prt001  3,2,prt_fild08,170,375`` - the
  field warp;
- ``:39`` ``prt_in,135,71,0  warp  prt04-1  1,2,prontera,136,219`` - the
  prt04 interior's exit door;
- ``:40`` ``prt_in,168,124,0  warp  prt05-1  2,1,prontera,174,218`` - the
  prt05 interior's exit door (the mirror of the cited prt05 entry, :25), the
  same cell the merchant return leg already cites;
- ``:41`` ``prt_in,172,33,0  warp  prt09-1  2,1,prontera,205,157``;
- ``:42`` ``prt_in,181,55,0  warp  prt07-1  1,2,prontera,192,264``;
- ``:43`` ``prt_in,183,97,0  warp  prt02-1  1,2,prontera,120,264``;
- ``:44`` ``prt_in,208,179,0  warp  prt12-1  3,1,prontera,76,102``;
- ``:47`` ``prt_in,240,141,0  warp  prt01-1  3,1,prontera,107,218``;
- ``:48`` ``prt_in,248,173,0  warp  prt13-1  3,2,prontera,77,93``;
- ``:56`` ``prt_in,282,179,0  warp  prt14  3,1,prontera,87,91``;
- ``:59`` ``prt_in,47,29,0  warp  prt10-1  2,1,prontera,46,67``;
- ``:61`` ``prt_in,53,105,0  warp  prt03-1  1,2,prontera,136,186``;
- ``:62`` ``prt_in,60,77,0  warp  prt06-1  2,1,prontera,175,188``;
- ``:63`` ``prt_in,68,130,0  warp  prt08-1  2,1,prontera,204,188``;
- ``:67`` ``prt_in,80,113,0  warp  prt11-1  2,1,prontera,48,343``;
- ``:69`` ``prt_in,227,15,0  warp  prt20-2  2,2,prontera,263,275``.

The internal prt_in hops (source cell -> the cell the hop delivers):
- ``:45`` ``prt_in,217,163,0  warp  prt15  1,3,prt_in,236,163``;
- ``:46`` ``prt_in,234,163,0  warp  prt15-1  1,3,prt_in,215,163``;
- ``:49`` ``prt_in,254,113,0  warp  prt16  3,2,prt_in,256,134``;
- ``:50`` ``prt_in,256,131,0  warp  prt16-1  2,2,prt_in,254,110``;
- ``:51`` ``prt_in,263,163,0  warp  prt17  1,3,prt_in,276,163``;
- ``:52`` ``prt_in,274,163,0  warp  prt17-1  1,3,prt_in,261,163``;
- ``:58`` ``prt_in,37,65,0  warp  prt18  1,3,prt_in,51,65``;
- ``:60`` ``prt_in,48,65,0  warp  prt18-1  1,3,prt_in,34,65``;
- ``:64`` ``prt_in,69,65,0  warp  prt19a  1,3,prt_in,84,65``;
- ``:65`` ``prt_in,70,143,0  warp  prt20  2,1,prt_in,70,165``;
- ``:66`` ``prt_in,70,162,0  warp  prt20-1  2,1,prt_in,70,140``;
- ``:68`` ``prt_in,82,65,0  warp  prt19b  1,3,prt_in,66,65``.
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
"""The seeded route per map: the ordered warp legs from that map to the
field. ``prt_in``'s first leg is the prt05 interior's door - the seeded
default for the interior the merchant trip leaves an agent in. The live
route RESOLVES the door by reachability (see ``robots.app.travel_routing``)
and falls back to this table when no grid is available."""

EXIT_CELLS: dict[str, tuple[tuple[int, int], ...]] = {
    "prontera": ((156, 22),),
    "prt_in": (
        (135, 71),
        (168, 124),
        (172, 33),
        (181, 55),
        (183, 97),
        (208, 179),
        (240, 141),
        (248, 173),
        (282, 179),
        (47, 29),
        (53, 105),
        (60, 77),
        (68, 130),
        (80, 113),
        (227, 15),
    ),
}
"""Per map: the exit cells the agent can walk to. A map with several exits
(prt_in's building interiors) has one per interior; the reachable one is
the exit of the interior the agent stands in."""

INTERNAL_WARPS: dict[str, tuple[tuple[tuple[int, int], tuple[int, int]], ...]] = {
    "prt_in": (
        ((217, 163), (236, 163)),
        ((234, 163), (215, 163)),
        ((254, 113), (256, 134)),
        ((256, 131), (254, 110)),
        ((263, 163), (276, 163)),
        ((274, 163), (261, 163)),
        ((37, 65), (51, 65)),
        ((48, 65), (34, 65)),
        ((69, 65), (84, 65)),
        ((70, 143), (70, 165)),
        ((70, 162), (70, 140)),
        ((82, 65), (66, 65)),
    ),
}
"""Per map: the warp hops INSIDE the map (source cell -> delivered cell). The
source cell is the way out of an interior that has no door of its own."""
