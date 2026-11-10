"""Runtime staging allocation on public geometry and this agent's received cells."""

import logging

from robots.adapters.native_navigation import NoRoute, WalkMap, shortest_path
from robots.app.scripts import MERCHANT_ROUTE, _approach_cell, _free_approach_cells
from robots.domain.model import BotState

logger = logging.getLogger(__name__)
Point = tuple[int, int]
Body = tuple[int, Point]
STAGING_HOLD_SECONDS = 15 * 60


def _ring_reachable(grid: WalkMap, origin: Point, cell: Point, blocked: set[Point]) -> bool:
    try:
        shortest_path(grid, origin, cell, blocked_visible=blocked - {origin})
    except NoRoute:
        return False
    return True


def _staging_blockers(grid: WalkMap, state: BotState) -> tuple[Point, ...]:
    occupied = set(state.occupied_cells)
    occupied.update(
        (actor.x, actor.y)
        for actor in state.nearby_players
        if actor.name != state.name and actor.x is not None and actor.y is not None
    )
    occupied.update(_static_blockers(state.map_name))
    occupied.discard((state.x, state.y))
    return tuple(sorted(point for point in occupied if grid.contains(point)))


def _static_blockers(map_name: str) -> tuple[Point, ...]:
    if map_name == "prontera":
        # prontera.txt:24: prt001's inclusive 3x2 field-return trigger.
        return tuple((x, y) for x in range(153, 160) for y in range(20, 25))
    if map_name == "prt_in":
        return (MERCHANT_ROUTE["prt_in"],)
    return ()


def _queue_cell(point: Point) -> bool:
    x, y = MERCHANT_ROUTE["prt_in"]
    return 2 <= max(abs(point[0] - x), abs(point[1] - y)) <= 4


def _queue_origins(
    position: Point, blocked: set[Point], own_id: int | None, bodies: tuple[Body, ...]
) -> tuple[tuple[Point, bool], ...]:
    if own_id is not None and bodies:
        origins = {aid: p for aid, p in bodies if _queue_cell(p) or p == position}
        origins[own_id] = position
        return tuple((p, aid == own_id) for aid, p in sorted(origins.items()))
    cells = {p for p in blocked if _queue_cell(p)} | {position}
    return tuple((p, p == position) for p in sorted(cells))


def _ring_allocation(
    grid: WalkMap,
    position: Point,
    cells: set[Point],
    blocked: set[Point],
    origins: tuple[tuple[Point, bool], ...],
) -> Point | None:
    blocked.add(position)
    for origin, is_self in origins:
        candidates = sorted(
            cells,
            key=lambda p: (
                max(abs(p[0] - origin[0]), abs(p[1] - origin[1])),
                (p[0] - origin[0]) ** 2 + (p[1] - origin[1]) ** 2,
                p,
            ),
        )
        chosen = next((p for p in candidates if _ring_reachable(grid, origin, p, blocked)), None)
        if is_self:
            return chosen
        if chosen is not None:
            cells.remove(chosen)
    return None


def dealer_entry_cell(map_name: str, cell: Point) -> bool:
    """prt05's inclusive 2x2 trigger, prontera.txt:25 at the pinned revision.

    (177,221) is the entry WARP, not a separate mandatory staging stop.
    Its eight neighbours and outer trigger cells all enter the dealer room.
    """
    x, y = MERCHANT_ROUTE["prontera"]
    return map_name == "prontera" and abs(cell[0] - x) <= 2 and abs(cell[1] - y) <= 2


class MerchantStaging:
    """Same local free-neighbour allocation as the dealer; no shared reservations.

    Geometry/path authority stays here. A full ring waits honestly, then may
    use another independently reachable cell of the existing prt05 trigger.
    There is no cross-map MoveTo or invented direct route to the dealer.
    """

    def __init__(self) -> None:
        self._identity: tuple[str, str, int | None] | None = None
        self._hold_since: float | None = None
        self._bypass_tapped = False
        self._path_context: tuple[object, ...] = ()
        self._paths: dict[Point, tuple[Point, ...] | None] = {}
        self._dealer_selection: Point | None = None
        self._dealer_saturation: tuple[object, ...] | None = None

    def observe(self, state: BotState) -> None:
        identity = (state.name, state.map_name, state.native_epoch)
        if self._identity != identity:
            self.release()
            self._identity = identity

    def release(self) -> None:
        self._hold_since = None
        self._bypass_tapped = False
        self._path_context = ()
        self._paths.clear()
        self._dealer_selection = None
        self._dealer_saturation = None

    def path(self, grid: WalkMap, state: BotState, cell: Point) -> tuple[Point, ...] | None:
        """Avoid received bodies AND the field-return trigger on an outbound walk."""
        self.observe(state)
        blocked = _staging_blockers(grid, state)
        context = (id(grid), state.x, state.y, blocked)
        if self._path_context != context:
            self._paths.clear()
            self._path_context = context
        if cell not in self._paths:
            try:
                self._paths[cell] = shortest_path(
                    grid, (state.x, state.y), cell, blocked_visible=blocked
                )
            except NoRoute:
                self._paths[cell] = None
        return self._paths[cell]

    def target(self, grid: WalkMap, state: BotState, now: float) -> Point | None:
        self.observe(state)
        destination = MERCHANT_ROUTE["prontera"]

        def reachable(map_name: str, position: Point, cell: Point) -> bool:
            del map_name, position
            return self.path(grid, state, cell) is not None

        cell = _approach_cell(*destination, state, reachable=reachable)
        if cell is not None:
            self._hold_since = None
            self._bypass_tapped = False
            return cell
        if self._hold_since is None:
            self._hold_since = now
            logger.warning(
                "merchant-drive: hold staging_occupied (bot=%s free=%s/8 agent=(%s,%s))",
                state.name,
                len(_free_approach_cells(*destination, state)),
                state.x,
                state.y,
            )
        if now - self._hold_since < STAGING_HOLD_SECONDS:
            return None
        return self._direct_dealer_entry(grid, state, destination)

    def dealer_target(
        self,
        grid: WalkMap,
        state: BotState,
        *,
        own_id: int | None = None,
        bodies: tuple[Body, ...] = (),
    ) -> Point | None:
        """Prefer talk-range cells; outer cells are an honest congestion queue."""
        self.observe(state)
        x, y = MERCHANT_ROUTE["prt_in"]
        cell = self._dealer_ring_target(grid, state, own_id, bodies)
        if cell is not None:
            self._dealer_selection = None
            self._dealer_saturation = None
            return cell
        self._note_ring_saturation(grid, state)
        cells = [
            (x + dx, y + dy)
            for dx in range(-4, 5)
            for dy in range(-4, 5)
            if max(abs(dx), abs(dy)) >= 2
        ]
        cells.sort(
            key=lambda p: (
                max(abs(p[0] - x), abs(p[1] - y)),
                max(abs(p[0] - state.x), abs(p[1] - state.y)),
                p,
            )
        )
        cell = next((p for p in cells if self.path(grid, state, p) is not None), None)
        if cell is not None and cell != self._dealer_selection:
            logger.warning(
                "merchant-drive: dealer_outer_fallback "
                "(bot=%s cell=%s chebyshev=%s preferred_chebyshev<=1=unavailable)",
                state.name,
                cell,
                max(abs(cell[0] - x), abs(cell[1] - y)),
            )
        self._dealer_selection = cell
        return cell

    def _dealer_ring_target(
        self, grid: WalkMap, state: BotState, own_id: int | None, bodies: tuple[Body, ...]
    ) -> Point | None:
        """Allocate from received bodies, never another client's private intent.

        A body already in the ring owns that cell until received movement or
        vanish releases it. Outside bodies within the approach area share a
        deterministic cell matching, so two approaching sellers do not both
        pick the nearest entrance. Type-0 bodies need no inferred identity,
        inventory or out-of-game reservations. Received actor IDs break ties
        even for overlapping bodies. Geometry remains runtime-owned.
        """
        x, y = MERCHANT_ROUTE["prt_in"]
        position = (state.x, state.y)
        blocked = set(_staging_blockers(grid, state))
        cells = {cell for cell in _free_approach_cells(x, y, state) if grid.walkable(cell)}
        # Own received presence is the stable allocation throughout dialogue.
        if position in cells:
            return position
        origins = _queue_origins(position, blocked, own_id, bodies)
        return _ring_allocation(grid, position, cells, blocked, origins)

    def _note_ring_saturation(self, grid: WalkMap, state: BotState) -> None:
        destination = MERCHANT_ROUTE["prt_in"]
        free = _free_approach_cells(*destination, state)
        detail = (tuple(sorted(free)), tuple(_staging_blockers(grid, state)))
        if detail == self._dealer_saturation:
            return
        self._dealer_saturation = detail
        logger.warning(
            "merchant-drive: hold dealer_ring_saturated "
            "(bot=%s free=%s/8 walkable_free=%s/8 "
            "preferred_chebyshev<=1=unavailable agent=(%s,%s))",
            state.name,
            len(free),
            sum(grid.walkable(cell) for cell in free),
            state.x,
            state.y,
        )

    def _direct_dealer_entry(
        self, grid: WalkMap, state: BotState, destination: Point
    ) -> Point | None:
        x, y = destination
        # The staging ring may be full while an OUTER warp-trigger cell is
        # independently reachable. Stay inside the pinned existing prt05 route.
        cells = [(x + dx, y + dy) for dx in range(-2, 3) for dy in range(-2, 3)]
        cells.sort(key=lambda cell: (max(abs(cell[0] - state.x), abs(cell[1] - state.y)), cell))
        cell = next((cell for cell in cells if self.path(grid, state, cell) is not None), None)
        if cell is not None and not self._bypass_tapped:
            self._bypass_tapped = True
            logger.warning(
                "merchant-drive: staging_hold_expired_direct_dealer (bot=%s entry=%s via=prt05)",
                state.name,
                cell,
            )
        return cell


class MerchantWarpCrossings:
    """Passive received-map evidence per client/window; intent never counts."""

    def __init__(self) -> None:
        self.count = 0
        self._map: str | None = None

    def observe(self, map_name: str, bot: str) -> None:
        if self._map != map_name and {self._map, map_name} == {"prontera", "prt_fild08"}:
            self.count += 1
            if self.count == 4:
                logger.warning("merchant_warp_ping_pong (bot=%s crossings=%s)", bot, self.count)
        self._map = map_name
