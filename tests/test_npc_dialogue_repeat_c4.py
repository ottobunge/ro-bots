"""The repeated dealtype marker must not kill an in-flight buy binding.

Leg 46 (the buy chain): the dealer's C4 (ZC_SELECT_DEALTYPE) arrived a second
time 0.5ms before the C5 buy-selection dispatched. The repeat re-bumped the
dialogue's prompt sequence, and the shop context's guard compared
dialog.sequence to action.prompt_sequence - the mismatch invalidated the
issued binding, so the C6 buy list that followed found `_issued is None` and
dropped silently. The buy never bound.

Two laws must hold together:
- Law A (here): a repeat C4 does NOT invalidate an issued binding - the C6
  still binds. The C4 re-marker changes no prompt semantics (same stage, same
  npc, same opened dialogue, same map).
- Law B (test_native_shop_selection drift test): the repeat still moves the
  dialogue's sequence so a STALE action cannot re-dispatch a second C5 - that
  guard lives in the dialogue's _encode_request, untouched.
"""

from __future__ import annotations

import struct
from dataclasses import replace

from robots.adapters.native_npc_dialogue import NativeNpcDialogue
from robots.adapters.native_shop_context import NativeShopContext
from robots.domain.actions import NpcShopBuySelection

NPC = 110001762
NOW = 100.0


def _c4(seq: int) -> tuple[int, float, int, bytes]:
    # ZC_SELECT_DEALTYPE 0x00C4: <packetType>.H <GID>.L, 6 bytes, no len field
    return (seq, NOW + seq, 0xC4, struct.pack("<HI", 0xC4, NPC))


def _c6(seq: int) -> tuple[int, float, int, bytes]:
    # ZC_PC_PURCHASE_ITEMLIST 0x00C6, len-prefixed: declared len.W = len(raw),
    # pid.W, then 11-byte rows <price>.L <discount>.L <type>.B <nameid>.H
    # (decode_shop_offer's exact geometry, native_shop.py)
    row = struct.pack("<IIBH", 50, 50, 0, 1201)
    # decode_shop_offer's geometry: pid.W first, then the declared total len.W
    body = struct.pack("<HH", 0xC6, 4 + len(row)) + row
    return (seq, NOW + 2.5, 0xC6, body)  # 'at' inside the issued window


def _action(prompt_sequence: int) -> NpcShopBuySelection:
    # opened_sequence=7 -> must match begin()'s sequence below
    return NpcShopBuySelection(NPC, 1, prompt_sequence, "prontera", 10)


def test_repeat_dealtype_marker_does_not_invalidate_the_issued_binding() -> None:
    dialogue = NativeNpcDialogue()
    dialogue.begin(NPC, 1, "prontera", 10, NOW)
    dialogue.consume((_c4(41),), NOW + 1.0)
    assert dialogue.view is not None
    assert dialogue.view.stage == "unsupported_shop"

    context = NativeShopContext()
    context.issued(_action(41), after=41, sent_at=NOW + 1.5, deadline=NOW + 20.0)
    # the dealer re-sends the SAME dealtype marker (leg 46: 0.5ms before the
    # C5): the sequence moves, nothing else about the prompt does
    dialogue.consume((_c4(42),), NOW + 2.0)
    assert dialogue.view is not None
    assert dialogue.view.sequence == 42
    # the C5's send moves the dialogue to "waiting" (the _commit_request flow)
    view_mid = dialogue.view
    assert view_mid is not None
    waiting = replace(view_mid, stage="waiting")
    context.check(waiting, True, NOW + 2.5)
    # Law A: the binding SURVIVES the re-marker...
    context.consume(_c6(43), 1)
    assert context.offer is not None
    rows = context.offer.rows
    assert len(rows) == 1


def test_repeat_dealtype_marker_does_not_kill_a_bound_offer(monkeypatch) -> None:
    """Leg 50: bf93474a's moved-on terms reintroduced the repeat-C4 misread -
    the re-marker bumps dialog.sequence, check() read a NEW exchange round,
    and the bound offer died (bound-deal-lost moved-on=True) before the
    decide-paced mint ever saw shop_offer. The marker is the SAME prompt: the
    offer must survive it; a REAL new prompt (a menu stage) must still die."""
    dialogue = NativeNpcDialogue()
    dialogue.begin(NPC, 1, "prontera", 10, NOW)
    dialogue.consume((_c4(41),), NOW + 1.0)
    context = NativeShopContext()
    context.issued(_action(41), after=41, sent_at=NOW + 1.5, deadline=NOW + 200.0)
    dialogue.consume((_c4(42),), NOW + 2.0)  # the vendor re-sends the marker
    view_bound = dialogue.view
    assert view_bound is not None
    waiting = replace(view_bound, stage="waiting")
    context.check(waiting, True, NOW + 2.5)
    context.consume(_c6(43), 1)
    assert context.offer is not None  # bound (the leg-49 law)
    # the marker arrives AGAIN post-bind (leg 50's live shape)
    dialogue.consume((_c4(44),), NOW + 3.0)
    view_after = dialogue.view
    assert view_after is not None
    waiting2 = replace(view_after, stage="waiting")
    context.check(waiting2, True, NOW + 3.5, context_ok=True)
    assert context.offer is not None  # the re-marker must NOT kill the deal
    # a REAL new prompt (a menu) still ends it
    view_late = dialogue.view
    assert view_late is not None
    menu = replace(view_late, stage="menu")
    context.check(menu, True, NOW + 4.0, context_ok=True)
    assert context.offer is None
