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
from robots.domain.actions import NpcShopSell  # noqa: E402
from robots.domain.model import Goal  # noqa: E402
from tests.test_playing_runtime import Wire, entry, map_frame  # noqa: E402


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
