"""Click and shop continuation must share received Chebyshev-one adjacency."""

import pytest

from robots.domain.actions import NpcShopSellOpen
from robots.domain.model import Goal
from tests.test_shop_sell_loop import DEALER, _armed, _c4, _client_with, _dealer, _inv, _weight


@pytest.mark.parametrize("offset", [(2, 2), (2, 0), (-2, 0), (0, -2), (1, 1), (-1, -1)])
def test_received_shop_adjacency_uses_chebyshev_one(offset):
    dx, dy = offset
    client = _client_with(_dealer((42 + dx, 37 + dy)))
    client.build_native_state(Goal.GRIND)
    tracker = client._tracker
    assert tracker is not None
    assert client._dealer_adjacent(tracker, DEALER) == (max(abs(dx), abs(dy)) <= 1)


def test_radius_two_received_dealtype_cannot_send_sell_open():
    client = _client_with(_dealer((44, 39)), _inv(((6, 909, 5),)), _weight())
    client.build_native_state(Goal.GRIND)
    _armed(client)
    client.wire.add(_c4(DEALER))
    state = client.build_native_state(Goal.GRIND)
    actions = client.mechanical_actions(state, ())
    assert any(isinstance(a, NpcShopSellOpen) for a in actions)
    for action in actions:
        client.perform_native(action)
    assert client.wire.sent == []
