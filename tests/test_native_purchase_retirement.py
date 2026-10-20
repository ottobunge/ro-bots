"""Observed transport loss retires unissued purchase authority, not just slots."""

import pytest

from robots.adapters.native_vitals import NativeTelemetryUnavailable
from tests.test_native_self_metadata_context import bind, proof_for
from tests.test_native_shop_purchase import known_facts, offered


@pytest.mark.parametrize("minted", [False, True])
@pytest.mark.parametrize("republish_slots", [False, True])
def test_common_health_loss_retires_pre_dispatch_authority(monkeypatch, minted, republish_slots):
    wire, client, _receive, sent = offered(monkeypatch)
    assert client.bind_shop_purchase_facts(known_facts(wire))
    action = client.npc_shop_purchase(maximum_zeny=61) if minted else None
    if minted:
        assert action is not None
    before = len(sent)
    wire.running = False
    with pytest.raises(NativeTelemetryUnavailable):
        client.planning_rest_observation()
    wire.running = True
    if republish_slots:
        assert bind(client, proof_for(wire))
    if action is not None:
        client.perform_native(action)
    assert len(sent) == before, "Read-only metadata revived a retired spending intent"
    assert (
        client.npc_shop_purchase(maximum_zeny=61) is None
    ), "Read-only metadata revived pre-dispatch qualification"
