"""OFFLINE probe: WHY the leg-28 sell-open never reached the wire.

READ-ONLY against production src/. Reproduces the leg-28 state faithfully:
  the agent WALKED to the dealer (a real 0x0087 walk frame), clicked it
  (0x0090), the server answered ZC_SELECT_DEALTYPE 0x00C4, and the runtime
  minted NpcShopSellOpen.

Prints each guard of _sell_open_request_ready separately so the failing
one is NAMED, not guessed. It also prints the SECOND mint of the SAME
dialog epoch to show whether the once-per-epoch dedupe held.
"""
import os
import struct
import sys
from pathlib import Path

# the repo root is parents[2] for .work/engagement-diagnosis/<file>.py
REPO = Path(os.environ.get("RO_BOTS_REPO", Path(__file__).resolve().parents[2]))
for candidate in (str(REPO / "src"), str(REPO), str(REPO / "tests")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from robots.adapters import native_gameplay as ng  # noqa: E402
from robots.app import playing_runtime as runtime  # noqa: E402
from robots.domain.model import Goal  # noqa: E402
from tests.test_playing_runtime import Wire, entry, map_frame, position  # noqa: E402

DEALER = 110001762
AGENT_CELL = (173, 130)
DEALER_CELL = (172, 130)


class RecordingWire(Wire):
    def __init__(self) -> None:
        super().__init__()
        self.sent = []

    def _send(self, raw):
        self.sent.append(raw)


def _inv(rows):
    body = b"".join(struct.pack("<HHBh17x", i, item, 0, n) for i, item, n in rows)
    return struct.pack("<HH", 0x0991, 4 + len(body)) + body


def _weight():
    return struct.pack("<HHi", 0x00B0, 24, 100)


def _c4(npc_id):
    """ZC_SELECT_DEALTYPE: 6 bytes -> the 'unsupported_shop' stage."""
    return struct.pack("<HI", 0x00C4, npc_id)


def _c7(rows):
    """ZC_PC_SELL_ITEMLIST: 4-byte header + 10 bytes per row."""
    body = b"".join(struct.pack("<HII", i, p, o) for i, p, o in rows)
    return struct.pack("<HH", 0x00C7, 4 + len(body)) + body


def _npc_actor(actor_id, at, objecttype=6):
    """0x09FE: the NPC presentation frame (length 103)."""
    raw = bytearray(103)
    struct.pack_into("<HHBII", raw, 0, 0x09FE, 103, objecttype, actor_id, 77)
    raw[59:62] = position(*at)
    struct.pack_into("<H", raw, 23, 1002)
    return bytes(raw)


def _walk_ack(start, end):
    """0x0087: a REAL walk (from != to) -> the tracked position is the
    DESTINATION and arrival_confirmed stays False (native_gameplay.py:756)."""
    x, y = start
    tx, ty = end
    data = bytes(
        (
            x >> 2,
            ((x & 3) << 6) | (y >> 4),
            ((y & 15) << 4) | (tx >> 6),
            ((tx & 63) << 2) | (ty >> 8),
            ty & 255,
            0,
        )
    )
    return b"\x87\0" + bytes(4) + data


def build(*, walked):
    """The leg-28 shape: the agent WALKED to the dealer (or stood there)."""
    wire = RecordingWire()
    wire.add(entry(), map_frame())
    if walked:
        # a real walk: from (170,120) to the dealer-adjacent cell
        wire.add(_walk_ack((170, 120), AGENT_CELL))
    else:
        # a zero-length walkok: the arrival IS proven
        wire.add(_walk_ack(AGENT_CELL, AGENT_CELL))
    wire.add(_npc_actor(DEALER, DEALER_CELL), _inv(((6, 909, 5),)), _weight())
    return wire


def scenario(name, *, walked, with_c7=False):
    wire = build(walked=walked)
    now = [1000.0]
    client = runtime.PlayingClient(wire, monotonic=lambda: now[0])

    # the click: begin() at the current metadata cursor
    client.build_native_state(Goal.GRIND)
    cursor = client._metadata_cursor
    client._npc.begin(DEALER, wire.native_epoch, "prontera", cursor, now[0])
    print(f"--- {name} ---")

    # the server answers the click with the C4
    wire.add(_c4(DEALER))
    state = client.build_native_state(Goal.GRIND)
    if with_c7:
        wire.add(_c7(((6, 12, 12),)))
        state = client.build_native_state(Goal.GRIND)

    tracker = client._tracker
    view = tracker.view
    dialog = client._npc.view
    print("  npc.view              =", dialog)
    print("  stage                 =", None if dialog is None else dialog.stage)
    print("  arrival_confirmed     =", view.arrival_confirmed)
    print("  position              =", view.position)
    print("  _pending              =", client._pending)
    print("  _standing             =", client._standing)
    print("  _life(view)           =", client._life(view))
    print("  _npc_motion_ready     =", client._npc_motion_ready())
    print("  _sell_actuation_ready =", client._sell_actuation_ready(view))
    print("  npc.requests          =", client._npc.requests)
    print("  inventory_counts      =", view.inventory_counts)
    print("  sell_lists            =", view.sell_lists)

    out = client.mechanical_actions(state, ())
    print("  mechanical_actions ->", out)
    for action in out:
        print("  action                =", action)
        client.perform_native(action)
    print("  wire.sent             =", client.wire.sent)
    print("  C5 (0xC5 type 1) sent?=", ng.sell_open(DEALER) in client.wire.sent)
    print("  C9 (sell request) sent?=", any(
        isinstance(r, bytes) and r[:2] == b"\xc9\x00" for r in client.wire.sent))
    print("  _sell_open_issued     =", client._sell_open_issued)

    # the SECOND tick of the SAME epoch: does the once-per-epoch dedupe hold?
    out2 = client.mechanical_actions(state, ())
    print("  2nd tick mechanical_actions ->", out2)
    for action in out2:
        client.perform_native(action)
    print("  wire.sent after 2nd   =", client.wire.sent)
    print()


def main():
    scenario("CASE A: the agent WALKED to the dealer (the leg-28 shape)", walked=True)
    scenario("CASE B: the agent STOOD at the dealer (zero-length walkok)", walked=False)
    scenario("CASE C: WALKED + the C7 arrived (does the SELL go out?)",
             walked=True, with_c7=True)


if __name__ == "__main__":
    main()
