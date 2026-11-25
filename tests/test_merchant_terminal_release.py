"""Pump-only completion/refusal must not leave a stale outbound trip lease."""

from dataclasses import replace

import pytest

from robots.app import scripts
from robots.app.playing_runtime import PlayingClient
from robots.domain.model import BotState
from tests.test_dealer_ring import _client
from tests.test_merchant_drive import _state


@pytest.fixture(autouse=True)
def fresh_trips():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _outbound(client: PlayingClient) -> BotState:
    state = _state(name=client.wire.char_name, inventory={"511": 2, "1201": 1}, zeny=125)
    assert scripts._merchant_step(state) is not None
    assert scripts.merchant_trip_active(state.name)
    return state


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"job": "Thief"}, "not_novice"),
        ({"map_name": "moc_fild02"}, "map_not_on_merchant_route"),
        ({"inventory": {"1201": 1, "1202": 1, "1204": 1}}, "weapon_release"),
        ({"inventory": {"1201": 1}, "merchant_buy_suspended": True}, "buy_suspended"),
    ],
)
def test_pump_terminal_refusal_releases_before_another_script_tick(changes, reason, caplog):
    client, _ = _client()
    state = _outbound(client)
    refused = replace(state, **changes)
    assert client._merchant_pump_destination(refused) is None
    assert not scripts.merchant_trip_active(state.name)
    assert state.name not in scripts._MERCHANT_TRAVEL_WALKS
    assert "merchant_trip_budget_released" in caplog.text
    assert f"reason={reason}" in caplog.text
    assert refused.inventory == changes.get("inventory", state.inventory)
    # A repeated pump refusal does not produce repeated release taps.
    before = caplog.text.count("merchant_trip_budget_released")
    assert client._merchant_pump_destination(refused) is None
    assert caplog.text.count("merchant_trip_budget_released") == before


def test_runtime_completion_releases_outbound_lease_immediately(caplog):
    client, _ = _client()
    state = _outbound(client)
    client._rearm_farm_after_trip("completed")
    assert client._merchant_returning
    assert not scripts.merchant_trip_active(state.name)
    assert "reason=completed" in caplog.text


@pytest.mark.parametrize("transient", ["inventory_unknown", "cooldown"])
def test_transient_refusal_preserves_receipt_and_retry_barriers(transient):
    client, _ = _client()
    state = _outbound(client)
    trip = scripts._MERCHANT_TRIPS[state.name]
    if transient == "inventory_unknown":
        state = replace(state, inventory_known=False)
    else:
        assert scripts.merchant_release_contact_walk(state.name)
    assert client._merchant_pump_destination(state) is None
    assert scripts._MERCHANT_TRIPS[state.name] is trip
