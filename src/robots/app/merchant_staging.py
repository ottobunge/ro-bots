"""Runtime staging allocation on public geometry and this agent's received cells."""

import logging

from robots.adapters.native_navigation import NoRoute, WalkMap, shortest_path
from robots.app.scripts import MERCHANT_ROUTE, _approach_cell, _free_approach_cells
from robots.domain.model import BotState

logger = logging.getLogger(__name__)
Point = tuple[int, int]
STAGING_HOLD_SECONDS = 15 * 60


def _staging_blockers(grid: WalkMap, state: BotState) -> tuple[Point, ...]:
    occupied = set(state.occupied_cells)
    occupied.update(
        (actor.x, actor.y)
        for actor in state.nearby_players
        if actor.name != state.name and actor.x is not None and actor.y is not None
    )
    # prontera.txt:24: prt001's inclusive 3x2 field-return trigger.
    occupied.update((x, y) for x in range(153, 160) for y in range(20, 25))
    occupied.discard((state.x, state.y))
    return tuple(sorted(point for point in occupied if grid.contains(point)))


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
