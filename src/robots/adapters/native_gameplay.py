"""Received-wire facts, pinned e985 MAIN/pre-re20180704, no sends/inference.

consume_snapshot(*client.native_frame_snapshot()) pumps sequenced ring frames.
Coordinates are last observed, never atomic current-world position. Parent must
require known alive/healthy transport and compute distance from observations.
Type5 combat eligibility excludes ownAID and exact negative alias: clif.cpp
345-383,1197-1209,1343-1360,1453-1465; type0 remains ambiguous. Encoders enforce
representation, not target policy. Initial alive remains unknown until receipt.
Inventory known only after contiguous auth->LoadEnd inventory->WEIGHT barrier
(clif.cpp10782-10794); no absence-only empty inventory fallback.
"""

import math
import struct
from collections import deque
from dataclasses import dataclass

from robots.adapters.native_actor_presentation import parse_actor_presentation
from robots.adapters.native_equipment import decode_equip_ack, encode_equip_request
from robots.adapters.native_shop import PurchaseEntry, encode_purchase

# Retained event tuples are a tail, not complete epoch history. Wire seq stays
# lifetime-monotonic within the epoch so consumers can detect retention gaps.
MAX_EVENTS = 1024
MAX_FLOOR_ITEMS = 4096
MAX_ITEM_TYPES = 4096
MAX_INVENTORY_SLOTS = 4096

EQP_HAND_R = 0x0002
"""Right-hand equip position bitmask (pinned e985006171d2 src/common/mmo.hpp:340,
``EQP_HAND_R = 0x000002`` inside ``enum equip_pos``; pc.hpp:1130 ``EQP_WEAPON
EQP_HAND_R``). The wire default for the one-handed weapons the progression rule
wears."""


def equip(index: int, *, position: int = EQP_HAND_R) -> bytes:
    """CZ_REQ_WEAR_EQUIP_V5 request bytes, pinned MAIN 20180704.

    packets.hpp:1503-1509 (``PACKETVER >= 20120925`` branch: id 0x998,
    ``<int16 packetType><uint16 index><uint32 position>``), registered at
    clif_packetdb.hpp:58, 8 bytes per the measured
    protocol/main-20180704-pre-re-equipment.json ``requests['0x0998'].size``.
    ``index`` is the received client-side inventory index: inventory lists fill
    ``client_index(i)`` (clif.cpp:3084-3099) and the server converts back with
    ``server_index`` = index-2 (clif.cpp:122-127, clif.cpp:12124). Byte layout
    and integer bounds are delegated to native_equipment.encode_equip_request.
    """
    return encode_equip_request(index, position)


MAX_SHOP_ROWS = 64
"""Sell-list row bound mirroring the existing C6 offer policy in
native_shop.decode_shop_offer: an engineering bound, not a server maximum."""


def buy(item_id: int, amount: int = 1) -> bytes:
    """CZ_PC_PURCHASE_ITEMLIST request bytes, pinned MAIN 20180704.

    clif.cpp:12298 (``00c8 <packet len>.W { <amount>.W <name id>.W }*``).
    The wire carries only amount/nameid pairs; the NPC id and price are
    admission facts on the existing NativePurchase path (bind/mint/prepare),
    never wire content. Byte layout is delegated to
    native_shop.encode_purchase.
    """
    return encode_purchase((PurchaseEntry(item_id, amount),))


def npc_close(npc_id: int) -> bytes:
    """CZ_CLOSE_DIALOG 0x00b9 (packetdb size 6): <H len+pid, <I npc id.

    clif_parse_NpcCloseClick (clif.cpp): closes the open dialog for npc_id;
    the server then frees the unit from npc-interactive state so walks act.
    """
    error = "Expected positive uint32 npc id"
    if type(npc_id) is not int or not 1 <= npc_id <= 0xFFFFFFFF:
        raise ValueError(error)
    return struct.pack("<HI", 0x00B9, npc_id)


def sell_open(npc_id: int) -> bytes:
    """CZ_ACK_SELECT_DEALTYPE type 1 (sell-list request), pinned MAIN 20180704.

    packets.hpp:1519-1524 (``<packetType>.W <GID>.L <type>.B``, 7 bytes);
    clif.cpp:12255-12271 documents ``1 = sell`` and npc.cpp:2387-2418 sets
    ``npc_shopid`` then answers ZC_PC_SELL_ITEMLIST 0xc7. The id bound is
    positive-uint, mirroring native_shop.encode_buy_selection.
    """
    error = "Expected positive uint32 npc id"
    if type(npc_id) is not int or not 1 <= npc_id <= 0xFFFFFFFF:
        raise ValueError(error)
    return struct.pack("<HIB", 0xC5, npc_id, 1)


def sell(entries: tuple[tuple[int, int], ...]) -> bytes:
    """CZ_PC_SELL_ITEMLIST request bytes, pinned MAIN 20180704.

    clif.cpp:12345-12361 (``00c9 <packet len>.W { <index>.W <amount>.W }*``),
    packets.hpp:301-311. Indices are the received client-side indices echoed
    back from the received 0xc7 list; npc.cpp:3031-3138 verifies stock,
    deletes items and pays zeny, and clif.cpp:12333-12342 always answers
    0xcb ``<result>.B`` (0 = success, 1 = deal failed). Bounded to 64 entries
    (MAX_SHOP_ROWS engineering policy, not a server maximum).
    """
    error = "sell requires 1..64 (index, amount) entries"
    rows = tuple(entries)
    if not 1 <= len(rows) <= MAX_SHOP_ROWS:
        raise ValueError(error)
    for index, amount in rows:
        if type(index) is not int or type(amount) is not int:
            raise ValueError(error)
        # Client indices start at 2 (clif.cpp:122-127 client_index; npc.cpp
        # 3053 converts back with index-2) and a zero amount is a guaranteed
        # server reject (pc.cpp:6107 pc_delitem), so both bound positively.
        if not 2 <= index <= 0xFFFF or not 1 <= amount <= 0xFFFF:
            raise ValueError(error)
    payload = b"".join(struct.pack("<HH", index, amount) for index, amount in rows)
    return struct.pack("<HH", 0xC9, 4 + len(payload)) + payload


def _uint32(value: int) -> int:
    error = "Expected exact uint32"
    if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(error)
    return value


def attack(target_id: int, *, continuous: bool = False) -> bytes:
    """CZ_REQUEST_ACT2 normal0/repeat7; not sit2/stand3."""
    return struct.pack("<HIB", 0x0437, _uint32(target_id), 7 if continuous else 0)


def pickup(floor_item_id: int) -> bytes:
    return struct.pack("<HI", 0x0362, _uint32(floor_item_id))


def respawn() -> bytes:
    return struct.pack("<HB", 0x00B2, 0)


def party_chat(text: str, *, speaker_name: str) -> bytes:
    """20180704 non-NUL exact selected name : message (clif_process_message)."""
    error = "Invalid UTF8 party chat"
    if type(text) is not str or type(speaker_name) is not str:
        raise ValueError(error)
    message, name = text.encode("utf-8"), speaker_name.encode("utf-8")
    if (
        b"\0" in message
        or b"\0" in name
        or not 1 <= len(name) <= 23
        or not 1 <= len(message) <= 254
    ):
        raise ValueError(error)
    body = name + b" : " + message
    return struct.pack("<HH", 0x0108, len(body) + 4) + body


@dataclass(frozen=True)
class ObservedPosition:
    x: int
    y: int
    seq: int
    at: float


@dataclass(frozen=True)
class ObservedActor:
    actor_id: int
    character_id: int
    objecttype: int
    position: ObservedPosition
    walking: bool
    attackable: bool


@dataclass(frozen=True)
class ObservedFloorItem:
    floor_item_id: int
    item_id: int
    item_type: int
    amount: int
    position: ObservedPosition


@dataclass(frozen=True)
class ObservedPickup:
    seq: int
    at: float
    inventory_index: int
    item_id: int
    amount: int


@dataclass(frozen=True)
class ObservedDamage:
    seq: int
    at: float
    source_id: int
    target_id: int
    damage_type: int
    damage: int
    damage2: int
    is_sp_damage: bool


@dataclass(frozen=True)
class ObservedXP:
    seq: int
    at: float
    parameter: int
    value: int
    delta: int | None


@dataclass(frozen=True)
class ObservedDeath:
    seq: int
    at: float
    actor_id: int


@dataclass(frozen=True)
class ObservedNpcDialog:
    """A server NPC-dialog frame that opened a deal (ZC_SAY/WAIT/CLOSE_DIALOG).

    clif: ZC_SAY_DIALOG 0x00b4, ZC_WAIT_DIALOG 0x00b5, ZC_CLOSE_DIALOG 0x00b7
    all carry the npc id at offset 2. The client answers an open deal with
    CZ_CLOSE_DIALOG 0x00b9; walks sent while a deal is open are ignored by
    the server (npc-interactive state), which trapped a bot in the prt_in
    shop interior (windows 43-49).
    """

    npc_id: int
    seq: int
    at: float


@dataclass(frozen=True)
class ObservedEquipAck:
    """One received ZC_ACK_WEAR_EQUIP_V5, preserved raw (never inferred)."""

    seq: int
    at: float
    inventory_index: int
    wear_location: int
    raw_result: int
    success: bool


@dataclass(frozen=True)
class ObservedSellList:
    """One received ZC_PC_SELL_ITEMLIST (0xc7), preserved raw (never inferred)."""

    seq: int
    at: float
    rows: tuple[tuple[int, int, int], ...]  # (client index, price, overcharge)


@dataclass(frozen=True)
class ObservedSellAck:
    """One received NPC sell result (0xcb); raw byte, success only when 0."""

    seq: int
    at: float
    raw_result: int
    success: bool


@dataclass(frozen=True)
class ObservedStatAck:
    """One ZC_STATUS_CHANGE_ACK: the spend verdict for a single stat."""

    seq: int
    at: float
    stat_id: int
    ok: bool
    value: int


@dataclass(frozen=True)
class NativeGameplayView:
    actors: tuple[ObservedActor, ...]
    floor_items: tuple[ObservedFloorItem, ...]
    observed_inventory_counts: tuple[tuple[int, int], ...]
    inventory_counts: tuple[tuple[int, int], ...] | None
    acquired_counts: tuple[tuple[int, int], ...]
    pickups: tuple[ObservedPickup, ...]
    position: ObservedPosition | None
    map_name: str | None
    arrival_confirmed: bool
    inventory_known: bool
    alive_known: bool
    alive: bool | None
    perception_ready: bool
    damage: tuple[ObservedDamage, ...]
    xp: tuple[ObservedXP, ...]
    deaths: tuple[ObservedDeath, ...]
    worn: tuple[tuple[int, int], ...]
    equip_acks: tuple[ObservedEquipAck, ...]
    sell_lists: tuple[ObservedSellList, ...]
    sell_results: tuple[ObservedSellAck, ...]
    status_points: int | None
    base_level: int | None
    stats: tuple[int, ...] | None
    stat_acks: tuple[ObservedStatAck, ...]


def _position(raw: bytes, offset: int, seq: int, at: float) -> ObservedPosition:
    a, b, c = raw[offset : offset + 3]
    return ObservedPosition((a << 2) | (b >> 6), ((b & 63) << 4) | (c >> 4), seq, at)


class NativeGameplayTracker:
    """Pure per-agent collector; use snapshot pumping for gap safety."""

    def __init__(self, own_actor_id: int) -> None:
        self.own_actor_id = _uint32(own_actor_id)
        self._epoch: int | None = None
        self._cursor = 0
        self._reset()

    def _reset(self) -> None:
        self._actors: dict[int, ObservedActor] = {}
        self._floor: dict[int, ObservedFloorItem] = {}
        self._inventory: dict[int, tuple[int, int]] = {}
        self._acquired: dict[int, int] = {}
        self._pickups: deque[ObservedPickup] = deque(maxlen=MAX_EVENTS)
        self._position: ObservedPosition | None = None
        self._map_name: str | None = None
        self._arrival = False
        self._inventory_known = False
        self._inventory_initial = False
        self._alive: bool | None = None
        self._ready = True
        self._damage: deque[ObservedDamage] = deque(maxlen=MAX_EVENTS)
        self._xp: deque[ObservedXP] = deque(maxlen=MAX_EVENTS)
        self._xp_values: dict[int, int] = {}
        self._deaths: deque[ObservedDeath] = deque(maxlen=MAX_EVENTS)
        # Worn state is known ONLY from received successful equip acks in this
        # epoch. Pre-worn items at login stay unknown: the inventory lists'
        # wear bitmasks are not decoded here.
        self._worn: dict[int, int] = {}
        self._equip_acks: deque[ObservedEquipAck] = deque(maxlen=MAX_EVENTS)
        self._npc_dialog: ObservedNpcDialog | None = None
        # Received sell lists/results are a bounded tail, like every event class.
        self._sell_lists: deque[ObservedSellList] = deque(maxlen=MAX_EVENTS)
        self._sell_results: deque[ObservedSellAck] = deque(maxlen=MAX_EVENTS)
        # Criterion-9 observation: status points (0x00B0 param 9, signed;
        # negative = retained raw, never spend-ready), base level (param 11),
        # the six basic stats (params 13-18 / the 0x00BD table), and the
        # bounded 0x00BC ack tail.
        self._status_points: int | None = None
        self._base_level: int | None = None
        self._stats: dict[int, int] | None = None
        self._stat_acks: deque[ObservedStatAck] = deque(maxlen=MAX_EVENTS)

    @property
    def indexed_inventory(self) -> tuple[tuple[int, int, int], ...] | None:
        """Detached current stock only; historical acquisitions are not bag contents."""
        if not self._inventory_known or not self._ready:
            return None
        return tuple(
            sorted((index, item, count) for index, (item, count) in self._inventory.items())
        )

    @property
    def npc_dialog_open(self) -> ObservedNpcDialog | None:
        """The latest server NPC-dialog frame, if no close has been sent since."""
        return self._npc_dialog

    def clear_npc_dialog(self) -> None:
        """Record the client-side CZ_CLOSE_DIALOG 0x00b9 send."""
        self._npc_dialog = None

    @property
    def view(self) -> NativeGameplayView:
        counts: dict[int, int] = {}
        for item, count in self._inventory.values():
            counts[item] = counts.get(item, 0) + count
        observed = tuple(sorted(counts.items()))
        return NativeGameplayView(
            tuple(self._actors.values()),
            tuple(self._floor.values()),
            observed,
            observed if self._inventory_known else None,
            tuple(sorted(self._acquired.items())),
            tuple(self._pickups),
            self._position,
            self._map_name,
            self._arrival,
            self._inventory_known,
            self._alive is not None,
            self._alive,
            self._ready and self._position is not None,
            tuple(self._damage),
            tuple(self._xp),
            tuple(self._deaths),
            tuple(sorted(self._worn.items())),
            tuple(self._equip_acks),
            tuple(self._sell_lists),
            tuple(self._sell_results),
            self._status_points,
            self._base_level,
            None if self._stats is None else tuple(self._stats.get(i, 1) for i in range(6)),
            tuple(self._stat_acks),
        )

    def consume_snapshot(
        self, epoch: int, base_seq: int, frames: tuple[tuple[int, float, int, bytes], ...]
    ) -> bool:
        """Base is last sequence before retained frames; gaps deny until new epoch."""
        if epoch != self._epoch:
            self._reset()
            self._epoch, self._cursor = epoch, base_seq
        if self._cursor < base_seq:
            return self._deny()
        if not self._ready:
            return False
        for seq, at, pid, raw in frames:
            if seq <= self._cursor:
                continue
            if seq != self._cursor + 1:
                return self._deny()
            try:
                self.ingest(seq, at, pid, raw)
            except ValueError:
                return self._deny()
            self._cursor = seq
        return True

    def _deny(self) -> bool:
        self._reset()
        self._ready = False
        return False

    def _receipt_ready(self, seq: int, at: float, pid: int, raw: bytes) -> bool:
        error = "Invalid receipt metadata"
        if type(seq) is not int or seq < 0 or not math.isfinite(at) or at < 0:
            raise ValueError(error)
        self._validate(pid, raw)
        return self._ready

    def ingest(self, seq: int, at: float, pid: int, raw: bytes) -> None:
        if not self._receipt_ready(seq, at, pid, raw):
            return
        if pid in (0x0991, 0x0A0D):
            self._inventory_list(pid, raw)
        elif pid == 0x0ADD:
            self._floor_item(seq, at, raw)
        elif pid == 0x009D:
            self._floor_item_entry(seq, at, raw)
        elif pid == 0x00A1:
            self._floor.pop(int.from_bytes(raw[2:6], "little"), None)
        elif pid == 0x0A37:
            self._pickup(seq, at, raw)
        elif pid in (0x09FD, 0x09FE, 0x09FF):
            self._actor(seq, at, raw)
        elif pid == 0x00C7:
            self._sell_list(seq, at, raw)
        elif pid == 0x00CB:
            self._sell_result(seq, at, raw)
        else:
            self._other(seq, at, pid, raw)

    @staticmethod
    def _validate(pid: int, raw: bytes) -> None:
        error = "Malformed native gameplay frame"
        if type(raw) is not bytes or len(raw) < 2 or int.from_bytes(raw[:2], "little") != pid:
            raise ValueError(error)
        sizes = {
            0x0ADD: 22,
            0x00A1: 6,
            0x0A37: 59,
            0x02EB: 13,
            0x0091: 22,
            0x0087: 12,
            0x0080: 7,
            0x0148: 8,
            0x08C8: 34,
            0x00B0: 8,
            0x00AF: 6,
            0x07FA: 8,
            0x00B1: 8,
            0x0ACB: 12,
            # ZC_ACK_WEAR_EQUIP_V5: <index>.W <wear location>.L <view id>.W
            # <result>.B = 11 bytes (packets_struct.hpp:1270-1276, the
            # PACKETVER_MAIN_NUM >= 20121205 branch = MAIN 20180704).
            0x0999: 11,
            # ZC sell result: <result>.B = 3 bytes (clif.cpp:12333-12342).
            0x00CB: 3,
            # ZC_STATUS_CHANGE_ACK: <stat>.W <ok>.B <value>.B = 6 bytes
            # (packets_struct.hpp:4219-4225); failures carry value 0.
            0x00BC: 6,
            # ZC_STATUS (clif_initialstatus at LoadEnd, clif.cpp:4123-4146):
            # <points>.W + 6x(<value>.B <cost>.B) + 14 derived shorts = 44.
            0x00BD: 44,
        }
        if pid in sizes and len(raw) != sizes[pid]:
            raise ValueError(error)

    def _inventory_list(self, pid: int, raw: bytes) -> None:
        error = "Malformed inventory list"
        size = 24 if pid == 0x0991 else 57
        if len(raw) < 4 or int.from_bytes(raw[2:4], "little") != len(raw) or (len(raw) - 4) % size:
            raise ValueError(error)
        pending: dict[int, tuple[int, int]] = {}
        for offset in range(4, len(raw), size):
            index, item = struct.unpack_from("<HH", raw, offset)
            amount = struct.unpack_from("<h", raw, offset + 5)[0] if pid == 0x0991 else 1
            if amount <= 0 or index in pending:
                raise ValueError(error)
            pending[index] = (item, amount)
        self._capacity(len(self._inventory.keys() | pending.keys()), MAX_INVENTORY_SLOTS)
        self._inventory.update(pending)

    def _capacity(self, size: int, limit: int) -> None:
        if size > limit:
            self._deny()
            error = "Native gameplay capacity exceeded; new epoch required"
            raise ValueError(error)

    def _floor_item_entry(self, seq: int, at: float, raw: bytes) -> None:
        # ZC_ITEM_ENTRY (0x009D, 17B) at MAIN 20180704: uint16 itemId branch
        # (PACKETVER_MAIN_NUM < 20181121 in the pinned packets_struct.hpp).
        _, aid, item, _identify, x, y, amount, _sub_x, _sub_y = struct.unpack_from(
            "<HIHBHHHBB", raw
        )
        # Zero-filler frames are authority-neutral (the audited framing
        # contract feeds all-zero payloads): ignore, never invent, never raise.
        if amount <= 0 or x < 0 or y < 0:
            return
        self._capacity(len(self._floor) + int(aid not in self._floor), MAX_FLOOR_ITEMS)
        self._floor[aid] = ObservedFloorItem(aid, item, 0, amount, ObservedPosition(x, y, seq, at))

    def _floor_item(self, seq: int, at: float, raw: bytes) -> None:
        _, aid, item, kind, _, x, y, _, _, amount = struct.unpack_from("<HIHHBhhBBh", raw)
        error = "Malformed floor item"
        if amount <= 0 or x < 0 or y < 0:
            raise ValueError(error)
        self._capacity(len(self._floor) + int(aid not in self._floor), MAX_FLOOR_ITEMS)
        self._floor[aid] = ObservedFloorItem(
            aid, item, kind, amount, ObservedPosition(x, y, seq, at)
        )

    def _pickup(self, seq: int, at: float, raw: bytes) -> None:
        if raw[24] != 0:
            return
        index, amount, item = struct.unpack_from("<HhH", raw, 2)
        error = "Successful pickup requires positive signed amount"
        previous = self._inventory.get(index, (item, 0))
        if amount <= 0 or previous[0] != item:
            raise ValueError(error)
        self._capacity(
            len(self._inventory) + int(index not in self._inventory), MAX_INVENTORY_SLOTS
        )
        self._capacity(len(self._acquired) + int(item not in self._acquired), MAX_ITEM_TYPES)
        self._inventory[index] = (item, previous[1] + amount)
        self._acquired[item] = self._acquired.get(item, 0) + amount
        self._pickups.append(ObservedPickup(seq, at, index, item, amount))

    def _actor(self, seq: int, at: float, raw: bytes) -> None:
        p = parse_actor_presentation(raw)
        offset = 63 if p.packet_id == 0x09FD else 59
        aid = p.actor_id
        self._actors[aid] = ObservedActor(
            aid,
            p.character_id,
            p.objecttype,
            _position(raw, offset, seq, at),
            p.packet_id == 0x09FD,
            p.objecttype == 5 and aid not in (self.own_actor_id, (-self.own_actor_id) & 0xFFFFFFFF),
        )
        if len(self._actors) > 4096:
            self._actors.pop(next(iter(self._actors)))

    def _seed_stat(self, index: int, value: int) -> None:
        if self._stats is None:
            self._stats = {}
        self._stats[index] = value

    def _status_table(self, raw: bytes) -> None:
        """ZC_STATUS at LoadEnd seeds points and the six stat values."""
        self._status_points = int.from_bytes(raw[2:4], "little")
        stats = self._stats if self._stats is not None else {}
        for index, offset in enumerate((4, 6, 8, 10, 12, 14)):
            stats[index] = raw[offset]
        self._stats = stats

    def _stat_ack(self, seq: int, at: float, raw: bytes) -> None:
        stat_id = int.from_bytes(raw[2:4], "little")
        ok = raw[4] == 1
        value = raw[5]
        self._stat_acks.append(ObservedStatAck(seq, at, stat_id, ok, value))
        if ok and 13 <= stat_id <= 18:
            self._seed_stat(stat_id - 13, value)

    def _other(self, seq: int, at: float, pid: int, raw: bytes) -> None:
        if pid in (0x00AF, 0x07FA):
            # pc_checkitem can delete between inventorylist and SP_WEIGHT.
            # Historical rows remain observable, but cannot become current stock.
            self._inventory_initial = False
            self._inventory_known = False
        elif pid in (0x02EB, 0x0091, 0x0087):
            self._self_position(seq, at, pid, raw)
        elif pid in (0x00B4, 0x00B5, 0x00B7):
            self._npc_dialog = ObservedNpcDialog(int.from_bytes(raw[2:6], "little"), seq, at)
        elif pid in (0x0080, 0x0148):
            self._life(seq, at, pid, raw)
        elif pid in (0x00B0, 0x00B1, 0x0ACB):
            self._status(seq, at, pid, raw)
        elif pid == 0x00BD:
            self._status_table(raw)
        elif pid == 0x00BC:
            self._stat_ack(seq, at, raw)
        elif pid == 0x08C8:
            self._damage.append(
                ObservedDamage(
                    seq,
                    at,
                    int.from_bytes(raw[2:6], "little"),
                    int.from_bytes(raw[6:10], "little"),
                    raw[29],
                    struct.unpack_from("<i", raw, 22)[0],
                    struct.unpack_from("<i", raw, 30)[0],
                    bool(raw[26]),
                )
            )
        elif pid == 0x0999:
            self._equip_ack(seq, at, raw)

    def _equip_ack(self, seq: int, at: float, raw: bytes) -> None:
        ack = decode_equip_ack(raw)
        # Success semantics are the MAIN>=20121205 enum sent verbatim by
        # clif_equipitemack (clif.hpp:523-532 ITEM_EQUIP_ACK_OK=0, FAIL=2,
        # FAILLEVEL=1; clif.cpp:4313-4326 ``p.result = flag``). The
        # clif.cpp:4308-4312 doc comment values describe the pre-20121205
        # branch only. Failures and unknown raw values leave worn unchanged.
        success = ack.raw_result == 0
        if success:
            self._worn[ack.inventory_index] = ack.wear_location
        self._equip_acks.append(
            ObservedEquipAck(
                seq, at, ack.inventory_index, ack.wear_location, ack.raw_result, success
            )
        )

    def _sell_list(self, seq: int, at: float, raw: bytes) -> None:
        error = "Malformed sell list"
        if len(raw) < 4 or int.from_bytes(raw[2:4], "little") != len(raw) or (len(raw) - 4) % 10:
            raise ValueError(error)
        rows = tuple(
            (index, price, overcharge)
            for index, price, overcharge in struct.iter_unpack("<HII", raw[4:])
        )
        if len(rows) > MAX_SHOP_ROWS:
            raise ValueError(error)
        self._sell_lists.append(ObservedSellList(seq, at, rows))

    def _sell_result(self, seq: int, at: float, raw: bytes) -> None:
        # clif.cpp:12333-12342: byte result, 0 = success, 1 = deal failed;
        # npc_selllist (npc.cpp:3031-3138) returns 0 only after the items
        # were deleted and the zeny paid.
        self._sell_results.append(ObservedSellAck(seq, at, raw[2], raw[2] == 0))

    def _self_position(self, seq: int, at: float, pid: int, raw: bytes) -> None:
        if pid == 0x0091:
            name = raw[2:18].split(b"\0", 1)[0].decode("ascii")
            x, y = struct.unpack_from("<HH", raw, 18)
            self._actors.clear()
            self._floor.clear()
            self._map_name = name
            self._position = ObservedPosition(x, y, seq, at)
            self._arrival = True
        else:
            position = _position(raw, 6, seq, at)
            self._position = position
            self._arrival = pid == 0x02EB
            if pid == 0x02EB:
                self._inventory.clear()
                self._inventory_initial = True
                self._inventory_known = False
            else:
                b, c, d = raw[8:11]
                destination = (((b & 15) << 6) | (c >> 2), ((c & 3) << 8) | d)
                self._arrival = (position.x, position.y) == destination

    def _life(self, seq: int, at: float, pid: int, raw: bytes) -> None:
        aid = int.from_bytes(raw[2:6], "little")
        own = aid in (self.own_actor_id, (-self.own_actor_id) & 0xFFFFFFFF)
        if pid == 0x0148:
            if own:
                self._alive = True
        else:
            self._actors.pop(aid, None)
            if raw[6] == 1:
                self._deaths.append(ObservedDeath(seq, at, aid))
                if own:
                    self._alive = False

    def _status(self, seq: int, at: float, pid: int, raw: bytes) -> None:
        parameter = int.from_bytes(raw[2:4], "little")
        if pid == 0x00B0:
            if parameter == 24 and self._inventory_initial and self._ready:
                self._inventory_known = True
                self._inventory_initial = False
            elif parameter == 9:
                # Status points, signed: negative values are retained raw and
                # never spend-ready (the setup phase gates on points > 0).
                self._status_points = struct.unpack_from("<i", raw, 4)[0]
            elif parameter == 11:
                self._base_level = int.from_bytes(raw[4:], "little")
            elif 13 <= parameter <= 18:
                self._seed_stat(parameter - 13, int.from_bytes(raw[4:], "little"))
        elif parameter in (1, 2):
            value = int.from_bytes(raw[4:], "little", signed=True)
            previous = self._xp_values.get(parameter)
            self._xp.append(
                ObservedXP(
                    seq, at, parameter, value, None if previous is None else value - previous
                )
            )
            self._xp_values[parameter] = value
