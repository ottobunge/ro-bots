"""Shop/economy slice: received sell leg + deterministic shop loop (window 28).

The buy-side C4/C5/C6/C8/0xCA contracts already exist (native_shop.py,
native_purchase.py). This slice adds the received sell-list path
(ZC_PC_SELL_ITEMLIST 0xc7, CZ_PC_SELL_ITEMLIST 0xc9, sell result 0xcb) and
the loop rule: sell the received sellable rows while stock lasts, then buy
the affordable wanted weapon through the existing owner-minted purchase
machinery. Pinned rathena e985006171d2 (MAIN/pre-re 20180704).
"""

import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for candidate in (str(REPO / "src"), str(REPO), str(REPO / "tests")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from robots.adapters import native_gameplay as ng  # noqa: E402
from robots.adapters.native_gameplay import NativeGameplayTracker  # noqa: E402
from robots.adapters.native_shop import PurchaseEntry, encode_purchase  # noqa: E402
from robots.app import playing_runtime as runtime  # noqa: E402
from robots.app import scripts  # noqa: E402
from robots.domain.actions import NpcShopSell, NpcShopSellOpen  # noqa: E402
from robots.domain.model import Goal  # noqa: E402
from tests.test_playing_runtime import Wire, entry, map_frame, walk_ack  # noqa: E402


class RecordingWire(Wire):
    def __init__(self) -> None:
        super().__init__()
        self.frames = []
        self.sent = []

    def _send(self, raw: bytes) -> None:
        self.sent.append(raw)


def _inv(rows: tuple[tuple[int, int, int], ...]) -> bytes:
    body = b"".join(struct.pack("<HHBh17x", i, item, 0, n) for i, item, n in rows)
    return struct.pack("<HH", 0x0991, 4 + len(body)) + body


def _weight() -> bytes:
    return struct.pack("<HHi", 0x00B0, 24, 100)


def _c7(rows: tuple[tuple[int, int, int], ...]) -> bytes:
    body = b"".join(struct.pack("<HII", i, p, o) for i, p, o in rows)
    return struct.pack("<HH", 0x00C7, 4 + len(body)) + body


def _cb(result: int) -> bytes:
    return struct.pack("<HB", 0x00CB, result)


def _fed(frames: tuple[bytes, ...], own: int = 17) -> NativeGameplayTracker:
    tracker = NativeGameplayTracker(own)
    seqs = tuple(
        (i + 1, float(i + 1), int.from_bytes(f[:2], "little"), f) for i, f in enumerate(frames)
    )
    assert tracker.consume_snapshot(1, 0, seqs)
    return tracker


# --- adapter encoders (pinned MAIN 20180704 wire layouts) ---


def test_sell_open_is_c5_type_one() -> None:
    """CZ_ACK_SELECT_DEALTYPE type **1** asks for the sell list.

    Live wire 2026-10-26, BOTH worlds on the same pinned image
    (rathena-playable:20180704-e985006171d2, sha256 3a0e4fcf...): a type-0 C5
    is answered with the BUY list 0xc6 (the dealer's stock, knife 1201 @ 50z
    in its price/discount/type/nameid rows), a type-1 C5 with the SELL list
    0xc7 (player inventory rows, index/price/overcharge). The pinned binary
    follows npc.cpp:2411 source semantics (type==0 -> clif_buylist); the
    earlier "w84 inversion" note had decoded a C6 buy list as a C7 — a real
    C7 row has no nameid field, so "knife 1201" is unseeable in one.
    """
    assert ng.sell_open(4123) == struct.pack("<HIB", 0xC5, 4123, 1)


def test_sell_open_rejects_bad_npc_id() -> None:
    bad_ids: list[object] = [0, -1, 2**32, True]
    for bad in bad_ids:
        try:
            ng.sell_open(bad)  # type: ignore[arg-type]
        except ValueError:
            pass
        else:
            raise AssertionError(bad)


def test_sell_encodes_c9_entries() -> None:
    assert ng.sell(((5, 3), (7, 1))) == struct.pack("<HHHHHH", 0x00C9, 12, 5, 3, 7, 1)


def test_sell_rejects_bad_entries() -> None:
    bad_entries: list[object] = [(), ((0, 0),), ((5, -1),), ((5, 65536),), ((5, 1),) * 65, "nope"]
    for bad in bad_entries:
        try:
            ng.sell(bad)  # type: ignore[arg-type]
        except ValueError:
            pass
        else:
            raise AssertionError(bad)


def test_buy_delegates_to_existing_c8_encoder() -> None:
    assert ng.buy(1201, 1) == encode_purchase((PurchaseEntry(1201, 1),))


# --- tracker ingestion of the received sell leg ---


def test_tracker_ingests_sell_list_rows() -> None:
    tracker = _fed((_c7(((6, 12, 12), (9, 10, 10))),))
    (listing,) = tracker.view.sell_lists
    assert listing.rows == ((6, 12, 12), (9, 10, 10))


def test_tracker_ingests_sell_result_success_semantics() -> None:
    tracker = _fed((_cb(0),))
    (ack,) = tracker.view.sell_results
    assert ack.raw_result == 0
    assert ack.success is True
    tracker = _fed((_cb(1),))
    (ack,) = tracker.view.sell_results
    assert ack.raw_result == 1
    assert ack.success is False


def test_tracker_denies_malformed_sell_list() -> None:
    tracker = NativeGameplayTracker(17)
    frame = struct.pack("<HH", 0x00C7, 999) + b"\x00" * 10
    seqs = ((1, 1.0, 0x00C7, frame),)
    assert tracker.consume_snapshot(1, 0, seqs) is False
    assert tracker.view.sell_lists == ()


def test_tracker_denies_wrong_sized_sell_result() -> None:
    tracker = NativeGameplayTracker(17)
    seqs = ((1, 1.0, 0x00CB, b"\xcb\x00\x00\x00"),)
    assert tracker.consume_snapshot(1, 0, seqs) is False


# --- pure loop rules (scripts.py) ---


def test_shop_affordable_weapon_from_received_rows() -> None:
    rows = ((50, 50, 4, 1201), (500, 500, 4, 1101))
    assert scripts.shop_affordable_weapon(rows, 50) == 1201
    assert scripts.shop_affordable_weapon(rows, 49) is None
    assert scripts.shop_affordable_weapon(rows, None) is None
    assert scripts.shop_affordable_weapon(((1900, 1900, 4, 990),), 10**6) is None


def test_shop_sellable_stock_counts_received_inventory() -> None:
    assert scripts.shop_sellable_stock(((909, 5), (915, 2), (1202, 1))) == 7
    assert scripts.shop_sellable_stock(((1202, 1),)) == 0
    assert scripts.shop_sellable_stock(None) == 0


def test_shop_sell_entries_bound_by_received_stock() -> None:
    rows = ((6, 12, 12), (9, 10, 10))
    stock = ((6, 909, 5), (9, 915, 0), (2, 1202, 1))
    assert scripts.shop_sell_entries(rows, stock) == ((6, 5),)
    assert scripts.shop_sell_entries((), stock) == ()


# --- runtime loop seam (mechanical_actions) ---


def _client_with(*extra: bytes) -> runtime.PlayingClient:
    wire = RecordingWire()
    wire.add(entry(), map_frame(), *extra)
    return runtime.PlayingClient(wire)


def test_mechanical_seam_sells_the_received_sell_list() -> None:
    client = _client_with(_inv(((6, 909, 5),)), _weight(), _c7(((6, 12, 12),)))
    state = client.build_native_state(Goal.GRIND)
    out = client.mechanical_actions(state, ())
    assert len(out) == 1
    (action,) = out
    assert isinstance(action, NpcShopSell)
    assert action.sales == ((6, 5),)
    assert action.sell_sequence == 5  # the 5th received frame
    client.perform_native(action)
    assert client.wire.sent == [ng.sell(((6, 5),))]
    assert client.mechanical_actions(state, ()) == ()  # sold once per C7 receipt


def test_mechanical_seam_is_inert_without_a_shop_context() -> None:
    client = _client_with()
    state = client.build_native_state(Goal.GRIND)
    assert client.mechanical_actions(state, ()) == ()


def test_unbound_sell_request_dispatch_sends_nothing() -> None:
    client = _client_with()
    action = NpcShopSell(None, 1, "prontera", 99, ((6, 5),))
    client.perform_native(action)
    assert client.wire.sent == []


def test_sell_open_is_fail_closed_without_a_received_dialog() -> None:
    client = _client_with(_inv(((6, 909, 5),)), _weight())
    state = client.build_native_state(Goal.GRIND)
    out = client.mechanical_actions(state, ())
    assert not any(type(a).__name__ == "NpcShopSellOpen" for a in out)


# --- the sell-completion gate (leg 28: 32 opens, zero sells) ---

DEALER = 4123


def _c4(npc_id: int) -> bytes:
    """ZC_SELECT_DEALTYPE 0x00C4: 6B total — id.W + npc gid.L at offset 2."""
    return struct.pack("<HI", 0x00C4, npc_id)


def _dealer(at: tuple[int, int], npc_id: int = DEALER) -> bytes:
    """A 0x09FE dealer presentation (objecttype 6) standing at `at`."""
    size, offset = 103, 59
    raw = bytearray(size)
    struct.pack_into("<HHBII", raw, 0, 0x09FE, size, 6, npc_id, 77)
    raw[offset + 0] = at[0] >> 2
    raw[offset + 1] = ((at[0] & 3) << 6) | (at[1] >> 4)
    raw[offset + 2] = (at[1] & 15) << 4
    return bytes(raw)


def _armed(client: runtime.PlayingClient, npc_id: int = DEALER) -> None:
    """The click arms the dialogue (native_npc_dialogue.begin) — the C4 is
    only ingested for the npc the client clicked. The 5s dialog deadline is
    armed on the CLIENT's monotonic, not a test-time zero."""
    client._npc.begin(npc_id, 1, "prontera", 0, client._now())


def test_sell_open_is_sent_after_a_real_walk_to_the_dealer() -> None:
    """T1, the leg-28 regression: a REAL walk leaves arrival_confirmed False
    forever (only a zero-length walkok proves arrival), and the sell limb
    gated the 0xC5 on it — 32 mints, zero sends. Readiness is tracked
    adjacency to the received dealer, never the walk-arrival flag."""
    client = _client_with(
        walk_ack((42, 37), (43, 37)),  # a real walk: from != to
        _dealer((43, 37)),
        _inv(((6, 909, 5),)),
        _weight(),
    )
    state = client.build_native_state(Goal.GRIND)  # the epoch initialises
    _armed(client)
    client.wire.add(_c4(DEALER))  # the dealer answers the click
    state = client.build_native_state(Goal.GRIND)
    out = client.mechanical_actions(state, ())
    assert len(out) == 1
    assert isinstance(out[0], NpcShopSellOpen)
    client.perform_native(out[0])
    assert ng.sell_open(DEALER) in client.wire.sent


def test_sell_open_is_minted_once_per_dialog_epoch() -> None:
    """T3: the epoch latches at the MINT, not after the send guard — a guard
    failure (no adjacency, no arrival proof) must not re-mint the same
    epoch's open every tick (leg 28: 32 opens)."""
    client = _client_with(
        _dealer((43, 37)),
        _inv(((6, 909, 5),)),
        _weight(),
    )
    state = client.build_native_state(Goal.GRIND)
    _armed(client)
    client.wire.add(_c4(DEALER))
    state = client.build_native_state(Goal.GRIND)
    first = client.mechanical_actions(state, ())
    assert len(first) == 1
    assert isinstance(first[0], NpcShopSellOpen)
    second = client.mechanical_actions(state, ())
    assert not any(isinstance(a, NpcShopSellOpen) for a in second)  # not re-minted


def test_a_new_dialog_epoch_mints_a_new_sell_open() -> None:
    """T4: the latch is per-epoch (a fresh received C4 = a fresh epoch) —
    the dedupe must not over-suppress the next dialogue."""
    client = _client_with(
        _dealer((43, 37)),
        _inv(((6, 909, 5),)),
        _weight(),
    )
    state = client.build_native_state(Goal.GRIND)
    _armed(client)
    client.wire.add(_c4(DEALER))
    state = client.build_native_state(Goal.GRIND)
    assert len(client.mechanical_actions(state, ())) == 1
    client.wire.add(_c4(DEALER))  # a fresh dialog epoch (a new received C4)
    state = client.build_native_state(Goal.GRIND)
    second = client.mechanical_actions(state, ())
    assert len(second) == 1
    assert isinstance(second[0], NpcShopSellOpen)


def test_the_sell_request_is_fail_closed_on_a_rejected_target() -> None:
    """T11: `_send_sell` compared a bool guard to None — the guard NEVER
    fired, so a rejected 0xC9 went out anyway (fail-open where the
    codebase's convention is fail-closed)."""
    client = _client_with(
        _inv(((6, 909, 5),)),
        _weight(),
        _c7(((6, 12, 12),)),
    )
    state = client.build_native_state(Goal.GRIND)
    (action,) = client.mechanical_actions(state, ())
    assert isinstance(action, NpcShopSell)
    # the local guards reject this 0xc9 (the epoch moved under it, the
    # receipt is gone — any False from `_sell_request_target` must close)
    client._sell_request_target = lambda *_a, **_k: False  # type: ignore[method-assign]
    client.perform_native(action)
    assert client.wire.sent == []
