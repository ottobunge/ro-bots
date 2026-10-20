"""ActorRef carries the observed cell so range-aware approach can follow.

Window 13 proved attacks on the wire (0x437 x1853); the approach slice walks
into range when the state monster carries a cell. This pins the projection:
the monster cell observed on the wire must survive into
BotState.nearby_monsters (ActorRef.x/y), so live behavior stops falling back
to the doomed range-blind attack. The wire is the emission namespace's
live-shaped twin, inlined so the root-gate mypy run resolves it (attribution:
.work/playing-grind-emission/offline_twin.py).
"""

import struct
import sys
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
for candidate in (str(REPO / "src"), str(REPO)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from robots.adapters.native_progression import SelectedCharacterSnapshot  # noqa: E402
from robots.app.playing_runtime import PlayingClient  # noqa: E402
from robots.domain.model import Goal  # noqa: E402

MAP = "prt_fild08"


def _position(x: int = 42, y: int = 37) -> bytes:
    return bytes((x >> 2, ((x & 3) << 6) | (y >> 4), (y & 15) << 4))


def _entry_frame() -> bytes:
    return b"\xeb\x02" + bytes(4) + _position() + bytes(4)


def _map_frame() -> bytes:
    return struct.pack("<H16sHH", 0x0091, MAP.encode(), 42, 37)


def _monster_frame(kind: int = 5, aid: int = 123, species: int = 1002) -> bytes:
    raw = bytearray(103)
    struct.pack_into("<HHBII", raw, 0, 0x09FE, 103, kind, aid, 77)
    raw[59:62] = _position(45, 41)
    struct.pack_into("<H", raw, 23, species)
    return bytes(raw)


def _weight_status_frame() -> bytes:
    return struct.pack("<HHI", 0x00B0, 24, 0)


def _life_frame(aid: int = 999) -> bytes:
    return struct.pack("<HI", 0x0148, aid) + b"\x00\x00"


class LiveShapedWire:
    """FakeWire (cadence shape) plus the live inventory/life frames, knobbed."""

    def __init__(self, *, with_monster: bool = True) -> None:
        self.aid = 999
        self.gid = 77
        self.char_name = "WireNovice"
        self.running = self.connected_map = True
        self.sock = object()
        self.rx_thread = SimpleNamespace(is_alive=lambda: True)
        self.rx_error = None
        self.dispatch_errors: list[object] = []
        self.native_epoch = self.selection_epoch = self.map_epoch = 1
        self.class_fresh = True
        self.selected_character_snapshot = SelectedCharacterSnapshot(77, 0, 10, 10, 0, 0)
        self.status_params = {5: 100, 6: 100, 7: 20, 8: 20}
        self.map_name = MAP
        self.chat: list[tuple[int, str]] = []
        self.actors: dict[int, object] = {}
        self.party_id = 0
        self.party_members: list[dict[str, object]] = []
        self.party_invite_pid = 0
        self.party_invite_from = ""
        self.frames: list[tuple[int, float, int, bytes]] = []
        self.sent: list[object] = []
        self.moves: list[tuple[int, int]] = []
        self.login_ip = "127.0.0.1"
        self.login_port = 6900
        opening = [_map_frame(), _entry_frame()]
        if with_monster:
            opening.append(_monster_frame())
        opening.append(_life_frame(self.aid))
        opening.append(_weight_status_frame())
        self.add(*opening)

    def add(self, *raws: bytes) -> None:
        for raw in raws:
            seq = len(self.frames) + 1
            self.frames.append((seq, float(seq), int.from_bytes(raw[:2], "little"), raw))

    def native_frame_snapshot(self):
        return self.native_epoch, 0, tuple(self.frames)

    def _send(self, raw: object) -> None:
        self.sent.append(raw)

    def move(self, x: int, y: int) -> None:
        self.moves.append((x, y))

    def say(self, text: str) -> None:
        self.sent.append(text)

    def sit(self) -> None:
        self.sent.append("sit")

    def stand(self) -> None:
        self.sent.append("stand")


def test_state_monsters_carry_observed_cells() -> None:
    wire = LiveShapedWire(with_monster=True)
    client = PlayingClient(wire)
    state = client.build_native_state(Goal.GRIND)
    monsters = [m for m in state.nearby_monsters if m.kind == "monster"]
    assert monsters, state.nearby_monsters
    first = monsters[0]
    assert (first.x, first.y) == (45, 41)


def test_no_monster_frames_project_no_monsters() -> None:
    wire = LiveShapedWire(with_monster=False)
    client = PlayingClient(wire)
    state = client.build_native_state(Goal.GRIND)
    assert not [m for m in state.nearby_monsters if m.kind == "monster"]
