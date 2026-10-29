"""IdleTownScript must not hammer one impossible cell (leg 37 defect 2).

g00m02 authored 3,210 MoveTos to (159,194) — unwalkable in the client grid —
and stood 117 minutes re-authoring the same impossible move; s00 never moved
at all (its own cell (204,165) is unwalkable in the client grid, the client's
map picture and the server's disagree). The twin roam paths (FarmScript/
GrindScript) vary their step among several directions and the runtime filters
walkability (w59); IdleTownScript emitted MoveTo(x, y+1) unconditionally —
one wall locked the whole script lifetime onto a single impossible target.
"""

from __future__ import annotations

from robots.app.scripts import IdleTownScript
from robots.domain.actions import MoveTo
from tests.conftest import make_state


def test_idle_town_steps_vary_direction_not_one_column() -> None:
    """A wall north must not consume every step on the same blocked cell."""
    script = IdleTownScript(max_steps=4)
    state = make_state(x=159, y=193)
    targets = []
    for _ in range(4):
        (action,) = script.step(state).actions
        assert isinstance(action, MoveTo)
        targets.append((action.x, action.y))
    assert len(set(targets)) > 1, f"all steps hit one target: {targets}"


def test_idle_town_first_step_is_the_north_neighbor() -> None:
    """The unchanged happy path: the first shift is still one cell north."""
    script = IdleTownScript(max_steps=2)
    (action,) = script.step(make_state(x=159, y=193)).actions
    assert isinstance(action, MoveTo)
    assert (action.x, action.y) == (159, 194)


def test_idle_town_steps_stay_bounded_at_zero() -> None:
    """The variation must not walk a coordinate negative (map edge)."""
    script = IdleTownScript(max_steps=8)
    state = make_state(x=0, y=0)
    for _ in range(8):
        (action,) = script.step(state).actions
        assert isinstance(action, MoveTo)
        assert action.x >= 0
        assert action.y >= 0
