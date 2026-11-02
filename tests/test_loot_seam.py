"""The loot seam: received 0x009D drops -> ItemDrop world events -> real pickups.

Leg 60 starved the sell arm because (a) the world-event producer minted
nothing off ``tracker.view.floor_items`` (zero ItemDrop-class events) and
(b) the pickup encode sent ``0x0362``, which the pinned MAIN 20180704
registers as ``clif_parse_DropItem`` (clif_packetdb.hpp:1561) — the leg-61
rewrite then moved the send to ``0x07E4``, which the served image parses as
ItemListWindowSelected (leg 63: -1 length-word disconnect; leg 64: harmless
window selections, zero inventory). Leg 65 read the COMPILED table:
packetdb_readdb (clif.cpp:25845-25847) includes clif_shuffle.hpp after the
plain table and packetdb_addpacket is last-write-wins, so 20180704 ends at
the shuffle's final rows -- ``0x0362,6,clif_parse_TakeItem,2`` and
``0x07E4,-1,clif_parse_ItemListWindowSelected,2,4,8,12``. These contracts
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


def test_pickup_encode_is_takeitem_0362() -> None:
    """The pickup send is the pinned-era CZ_ITEM_PICKUP 0x0362, fixed 6.

    The leg-61 "0x0362 is DropItem" reading was a PLAIN-TABLE reading: the
    clif_packetdb.hpp 20120418 block does re-register 0x0362 as DropItem
    (line 1561), but packetdb_readdb (clif.cpp:25845-25847) includes
    clif_shuffle.hpp AFTER the plain table and packetdb_addpacket is
    last-write-wins, so the compiled 20180704-PRERE table ends at the
    shuffle's ``#elif PACKETVER > 20180307`` final row:
    ``parseable_packet(0x0362,6,clif_parse_TakeItem,2)``. The leg-61
    rewrite to 0x07E4 landed on the served image's ItemListWindowSelected
    row (leg 63: the -1 length-word disconnect; leg 64: harmless no-op
    window selections, zero inventory). The REAL frame is type.W + AID.L,
    6 bytes, no len.W (fixed-size C->S rows carry no length word).
    """
    assert pickup(321) == bytes.fromhex("620341010000")


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
    assert wire.sent == [bytes.fromhex("620341010000")]  # 0x0362 + AID 321 (fixed 6)
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
