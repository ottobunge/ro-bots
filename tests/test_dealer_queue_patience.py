"""A vetoed dealer advance waits five evaluations, with perception release."""

from dataclasses import replace

import pytest

from robots.app import scripts
from robots.domain.actions import MoveTo
from tests.test_dealer_approach_cell import DEALER_CELL, _crowd, _dealer, _state


@pytest.fixture(autouse=True)
def _reset():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def test_vetoed_free_cells_are_rechecked_on_fifth_elapsed_evaluation():
    calls = []
    allowed = False

    def reachable(map_name, start, cell):
        calls.append(cell)
        return allowed

    state = _state(nearby=(_dealer(),))
    assert scripts._merchant_engage(state, DEALER_CELL, reachable).actions == ()
    assert len(calls) == 8
    allowed = True
    for _ in range(4):
        assert scripts._merchant_engage(state, DEALER_CELL, reachable).actions == ()
        assert len(calls) == 8
    assert scripts._merchant_engage(state, DEALER_CELL, reachable).actions == (MoveTo(173, 129),)
    assert len(calls) == 9


def test_full_ring_wait_bounds_changed_range_taps(caplog):
    state = _state(nearby=(_dealer(), *_crowd()))
    for _ in range(16):
        scripts._merchant_engage(state, DEALER_CELL)
    # Admission and range checks must not flip-flop with the full-ring hold.
    assert len([r for r in caplog.records if "hold dealer_occupied" in r.getMessage()]) == 1
    assert len([r for r in caplog.records if "dealer_talk_out_of_range" in r.getMessage()]) == 1


@pytest.mark.parametrize("change", ["vacancy", "position", "epoch", "reset"])
def test_changed_perception_or_session_rechecks_immediately(change):
    state = _state(nearby=(_dealer(), *_crowd()))
    assert scripts._merchant_engage(state, DEALER_CELL).actions == ()
    if change == "vacancy":
        state = replace(state, nearby=(_dealer(), *_crowd(except_cell=(173, 129))))
        assert scripts._merchant_engage(state, DEALER_CELL).actions == (MoveTo(173, 129),)
        return
    calls = []

    def veto(map_name, start, cell):
        calls.append(cell)
        return False

    state = _state(nearby=(_dealer(),))
    assert scripts._merchant_engage(state, DEALER_CELL, veto).actions == ()
    calls.clear()
    if change == "position":
        state = replace(state, x=175)
    elif change == "epoch":
        state = replace(state, native_epoch=2)
    else:
        scripts.reset_merchant_talk()
    assert scripts._merchant_engage(state, DEALER_CELL, veto).actions == ()
    assert len(calls) == 8
