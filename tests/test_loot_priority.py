"""Loot priority over starting a new approach (window-24 frontier).

Window 22-23 proved kills land (attributed damage >= pinned HP) and window
23's overlay saw zero pickups: ``_legacy_mechanical`` injected ``Loot()``
only when the authored actions were EMPTY, but on the dense field monsters
are always visible so the scripts always author an engagement (an approach
MoveTo at minimum) and the drop never gets picked. Loot must take priority
over STARTING a new approach, never over an in-melee exchange (Attack).
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for candidate in (str(REPO / "src"), str(REPO), str(REPO / "tests")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from robots.adapters.native_navigation import MapCache, WalkMap  # noqa: E402
from robots.app import playing_runtime as runtime  # noqa: E402
from robots.domain.actions import Attack, Loot, MoveTo  # noqa: E402
from robots.domain.model import Goal  # noqa: E402
from tests.test_playing_runtime import Wire, entry, map_frame  # noqa: E402
from tests.test_zc_item_entry_floor import zc_item_entry  # noqa: E402


def _client_with_floor_at(x: int, y: int) -> runtime.PlayingClient:
    wire = Wire()
    wire.frames = []
    wire.add(entry(), map_frame(), zc_item_entry(aid=510001, item=909, x=x, y=y))
    cache = MapCache((WalkMap("prontera", 400, 400, bytes(160000)),))
    return runtime.PlayingClient(wire, cache=cache)


def test_loot_priority_over_a_new_approach() -> None:
    client = _client_with_floor_at(44, 40)
    state = client.build_native_state(Goal.GRIND)
    authored = (MoveTo(x=44, y=40),)
    assert client.mechanical_actions(state, authored) == (Loot(),)


def test_loot_never_interrupts_a_melee_exchange() -> None:
    client = _client_with_floor_at(44, 40)
    state = client.build_native_state(Goal.GRIND)
    authored = (Attack(target_id=123),)
    assert client.mechanical_actions(state, authored) == authored


def test_loot_over_empty_actions_still_holds() -> None:
    client = _client_with_floor_at(44, 40)
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == (Loot(),)
