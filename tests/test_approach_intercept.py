"""The approach intercept: walk to a cell ADJACENT to the target, not into it.

Leg 18's telemetry: 31 samples at distance 2-5, ZERO at <=1. The approach
walked to the mob's own cell; a wandering mob moves during the walk, so the
bot lands where the mob WAS, forever 2-3 cells off. Walking to the target's
nearest-to-the-bot neighbouring cell means a one-cell mob shift still ends
the walk in melee range."""

from __future__ import annotations

from types import SimpleNamespace

from robots.app.scripts import _approach_cell


def _target(x: int, y: int):
    return SimpleNamespace(x=x, y=y)


def test_intercept_cell_is_adjacent_to_target_not_the_target_cell() -> None:
    bot = _target(7, 10)
    cell = _approach_cell(10, 10, bot)
    assert cell == (9, 10)


def test_intercept_prefers_the_nearest_neighbour_to_the_bot() -> None:
    bot = _target(8, 8)
    cell = _approach_cell(10, 10, bot)
    assert cell == (9, 9)


def test_intercept_from_due_north_takes_the_north_neighbour() -> None:
    bot = _target(10, 5)
    cell = _approach_cell(10, 10, bot)
    assert cell == (10, 9)


def test_intercept_between_two_equal_neighbours_is_deterministic() -> None:
    bot = _target(7, 10)
    first = _approach_cell(10, 10, bot)
    second = _approach_cell(10, 10, bot)
    assert first == second
