"""The loot seam: received 0x009D drops -> ItemDrop world events -> real pickups.

Leg 60 starved the sell arm because (a) the world-event producer minted
nothing off ``tracker.view.floor_items`` (zero ItemDrop-class events) and
(b) the pickup encode sent ``0x0362``, which the pinned MAIN 20180704
registers as ``clif_parse_DropItem`` (clif_packetdb.hpp:1561) — the real
CZ_ITEM_PICKUP is ``0x07E4`` (clif_packetdb.hpp:1560, clif.cpp:12006
``clif_parse_TakeItem`` reads the floor-item AID at offset 2), so every
loot choice's send was a silently-rejected drop request. These contracts
pin each hop of the repaired seam offline; no native sessions.
"""

import logging
import struct

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.native_gameplay import pickup
from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import playing_runtime as runtime
from robots.app.brain import EventDrivenBrain
from robots.domain.actions import Loot
from robots.domain.events import Heartbeat, ItemDrop
from tests.test_playing_runtime import Wire


def item_entry(aid: int = 321, nameid: int = 501, at: tuple[int, int] = (44, 40)) -> bytes:
    """ZC_ITEM_ENTRY 0x009D (17B, MAIN 20180704 uint16-itemId branch)."""
    x, y = at
    return struct.pack("<HIHBHHHBB", 0x009D, aid, nameid, 1, x, y, 3, 0, 0)


def test_pickup_encode_is_takeitem_07e4() -> None:
    """The pickup send is the pinned-era CZ_ITEM_PICKUP, not a drop request.

    The 20120418+ block re-registers 0x0362 as clif_parse_DropItem
    (clif_packetdb.hpp:1561) and moves TakeItem to 0x07E4 (line 1560) —
    the later registration wins in the compiled packetdb, so the old
    0x0362 pin asserted a guaranteed-rejected drop (leg 60: 16 loot
    choices, zero pickups, zero inventory delta). Leg 64: the SERVED
    packetdb declares 0x07E4 var-len (clif_packetdb.hpp:1268 -1 row; the
    leg-63 session killer), so the frame is type.W + len.W(8) + AID.L.
    """
    assert pickup(321) == bytes.fromhex("e407080041010000")


def test_item_drop_events_mint_off_received_009d() -> None:
    """Each newly surfaced floor item becomes exactly one ItemDrop event."""
    client = runtime.PlayingClient(Wire())
    wire = client.wire
    wire.add(item_entry())
    drops = [e for e in client.drain_native_events() if isinstance(e, ItemDrop)]
    assert len(drops) == 1
    drop = drops[0]
    assert (drop.nameid, drop.x, drop.y, drop.amount) == (501, 44, 40, 3)
    assert drop.floor_item_id == 321
    assert drop.map_name == "prontera"
    # once per presence: the next drain re-mints nothing
    assert not [e for e in client.drain_native_events() if isinstance(e, ItemDrop)]
    # the item leaves (0x00A1) and the aid is later reused: a real new drop
    wire.add(struct.pack("<HI", 0x00A1, 321))
    client.drain_native_events()
    wire.add(item_entry(aid=321, nameid=949, at=(45, 41)))
    drops = [e for e in client.drain_native_events() if isinstance(e, ItemDrop)]
    assert len(drops) == 1
    assert drops[0].nameid == 949


def test_loot_taps_surface_and_dispatch(caplog: pytest.LogCaptureFixture) -> None:
    """The two taps prove the hop live: one line per surfaced floor item,
    one per dispatched pickup (the leg-61 log reads these directly)."""
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    client = runtime.PlayingClient(Wire(), cache=cache)
    wire = client.wire
    wire.add(item_entry(aid=321, nameid=501, at=(43, 38)))
    with caplog.at_level(logging.WARNING):
        client.drain_native_events()
        surfaced = [
            r.getMessage() for r in caplog.records if "floor item surfaced" in r.getMessage()
        ]
        assert len(surfaced) == 1
        assert "nameid=501" in surfaced[0]
        assert "cell=(43,38)" in surfaced[0]
        client.perform_native(Loot())
    assert wire.sent == [bytes.fromhex("e407080041010000")]
    dispatched = [r.getMessage() for r in caplog.records if "pickup dispatched" in r.getMessage()]
    assert len(dispatched) == 1
    assert "fid=321" in dispatched[0]
    assert "nameid=501" in dispatched[0]


def test_decide_loot_choice_authors_pickup_action(state) -> None:
    """The decider's ``loot`` choice gets a REAL action behind it: Loot(),
    which the runtime dispatches as the CZ_ITEM_PICKUP send against the
    tracked floor item (leg 60: 16 loot choices, zero pickup actions)."""
    model = ScriptedDecisionModel(answers={"next_action": {"choice": "loot", "confidence": 1.0}})
    brain = EventDrivenBrain(model, StaticChatGenerator())
    result = brain.handle_event(state, Heartbeat(seq=1))
    assert any(isinstance(a, Loot) for a in result.actions)


def test_non_loot_choice_never_authors_pickup(state) -> None:
    """Fail closed: only an explicit ``loot`` answer mints the pickup."""
    model = ScriptedDecisionModel(answers={"next_action": {"choice": "grind", "confidence": 1.0}})
    brain = EventDrivenBrain(model, StaticChatGenerator())
    result = brain.handle_event(state, Heartbeat(seq=1))
    assert not any(isinstance(a, Loot) for a in result.actions)
