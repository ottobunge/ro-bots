"""Offline source-shaped frames; not native receipt/gameplay acceptance."""

import struct

import pytest

from robots.adapters import native_gameplay as gameplay


def actor(pid: int = 0x09FD, actor_id: int = 123, objecttype: int = 5) -> bytes:
    size, offset = {0x09FD: (110, 63), 0x09FE: (103, 59), 0x09FF: (104, 59)}[pid]
    raw = bytearray(size)
    struct.pack_into("<HHBII", raw, 0, pid, size, objecttype, actor_id, 77)
    raw[offset : offset + 3] = bytes([10, 0x82, 0x50])  # observed 42,37
    if pid == 0x09FD:
        # The move entry carries WBUFPOS2 (from, destination); encode the
        # same cell as the destination (a stationary spawn) so the frame is
        # wire-shaped: raw[offset+2] is the shared nibble byte.
        raw[offset + 2 : offset + 5] = bytes([0x50, 42 << 2, 37])
    return bytes(raw)


def move_entry(from_xy: tuple[int, int], to_xy: tuple[int, int], actor_id: int = 123) -> bytes:
    """A walking mob's 0x09FD: WBUFPOS2 from-cell then destination."""
    size, offset = 110, 63
    raw = bytearray(size)
    struct.pack_into("<HHBII", raw, 0, 0x09FD, size, 5, actor_id, 77)
    (x1, y1), (x2, y2) = from_xy, to_xy
    raw[offset + 0] = x1 >> 2
    raw[offset + 1] = ((x1 << 6) | (y1 >> 4)) & 0xFF
    raw[offset + 2] = ((y1 << 4) | (x2 >> 6)) & 0xFF
    raw[offset + 3] = ((x2 << 2) | (y2 >> 8)) & 0xFF
    raw[offset + 4] = y2 & 0xFF
    return bytes(raw)


@pytest.mark.parametrize("pid", [0x09FD, 0x09FE, 0x09FF])
def test_actor_to_attack_vertical(pid):
    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 4.0, pid, actor(pid))
    observed = tracker.view.actors[0]
    assert (observed.actor_id, observed.character_id) == (123, 77)
    assert (observed.position.x, observed.position.y) == (42, 37)
    assert observed.walking == (pid == 0x09FD)
    assert observed.attackable
    assert gameplay.attack(observed.actor_id) == bytes.fromhex("37047b00000000")


def test_move_entry_tracks_walk_destination():
    """A walking mob is tracked at its walk DESTINATION, not the from-cell.

    The 0x09FD move entry carries WBUFPOS2 (from, destination) — one frame
    per walk (unit.cpp:238-246, clif.cpp:1369+). Tracking the from-cell put
    the mob's believed cell up to a walk-cycle behind its true cell, so the
    melee gate compared the agent's future cell with the mob's past cell and
    every believed-adjacent swing landed 4-6 cells off (the leg-27 probe:
    8/8 gate-approved swings rejected 0x0139; 138 attacks, 3 landed hits).
    """
    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 4.0, 0x09FD, move_entry((42, 37), (45, 39)))
    observed = tracker.view.actors[0]
    assert (observed.position.x, observed.position.y) == (45, 39)


def test_move_entry_stationary_spawn_unchanged():
    """A stationary 0x09FD (from == destination) tracks the same cell."""
    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 4.0, 0x09FD, move_entry((42, 37), (42, 37)))
    observed = tracker.view.actors[0]
    assert (observed.position.x, observed.position.y) == (42, 37)


@pytest.mark.parametrize("kind", [0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 255])
def test_other_presentations_not_combat(kind):
    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 1.0, 0x09FE, actor(0x09FE, objecttype=kind))
    assert not tracker.view.actors[0].attackable


@pytest.mark.parametrize("aid", [999, (-999) & 0xFFFFFFFF])
def test_self_alias_excluded(aid):
    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 1.0, 0x09FE, actor(0x09FE, aid))
    assert not tracker.view.actors[0].attackable


@pytest.mark.parametrize("target", [0, 0xFFFFFFFF, 123])
def test_uint32_attack(target):
    assert gameplay.attack(target) == struct.pack("<HIB", 0x0437, target, 0)


@pytest.mark.parametrize("target", [-1, 2**32, True, 1.0, "123", None])
def test_attack_rejects_non_uint32(target):
    with pytest.raises(ValueError, match="uint32"):
        gameplay.attack(target)


def floor() -> bytes:
    raw = bytearray(22)
    struct.pack_into("<HIHHBhhBBh", raw, 0, 0x0ADD, 321, 501, 0, 1, 42, 37, 0, 0, 3)
    return bytes(raw)


def pickup_ack(amount: int = 3, result: int = 0) -> bytes:
    raw = bytearray(59)
    struct.pack_into("<HHHH", raw, 0, 0x0A37, 2, amount & 0xFFFF, 501)
    raw[24] = result
    return bytes(raw)


def test_floor_pickup_vertical():
    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 1.0, 0x0ADD, floor())
    assert tracker.view.floor_items[0].floor_item_id == 321
    assert gameplay.pickup(321) == bytes.fromhex("620341010000")
    tracker.ingest(2, 2.0, 0x0A37, pickup_ack())
    assert tracker.view.acquired_counts == ((501, 3),)
    assert tracker.view.inventory_counts is None
    assert tracker.view.pickups[0].amount == 3
    tracker.ingest(3, 3.0, 0x00A1, struct.pack("<HI", 0x00A1, 321))
    assert not tracker.view.floor_items


@pytest.mark.parametrize("result", [1, 2, 3, 4, 5, 6, 255])
def test_failed_pickup_is_not_acquired(result):
    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 1.0, 0x0A37, pickup_ack(result=result))
    assert not tracker.view.pickups
    assert not tracker.view.acquired_counts


@pytest.mark.parametrize("amount", [0, -1, -32768])
def test_success_pickup_positive_signed_count_required(amount):
    tracker = gameplay.NativeGameplayTracker(999)
    with pytest.raises(ValueError, match=r".+"):
        tracker.ingest(1, 1.0, 0x0A37, pickup_ack(amount=amount))
    assert not tracker.view.acquired_counts


@pytest.mark.parametrize(("pid", "size"), [(0x0991, 24), (0x0A0D, 57)])
def test_initial_inventory_partial_not_known(pid, size):
    tracker = gameplay.NativeGameplayTracker(999)
    raw = bytearray(4 + size)
    struct.pack_into("<HHHH", raw, 0, pid, len(raw), 2, 501)
    if pid == 0x0991:
        struct.pack_into("<h", raw, 9, 3)
    tracker.ingest(1, 1.0, pid, bytes(raw))
    assert tracker.view.inventory_counts is None
    assert tracker.view.observed_inventory_counts == ((501, 3 if pid == 0x0991 else 1),)


def auth() -> bytes:
    raw = bytearray(13)
    struct.pack_into("<H", raw, 0, 0x02EB)
    raw[6:9] = bytes([10, 0x82, 0x50])
    return bytes(raw)


def test_snapshot_epoch_replay_gap_denies():
    tracker = gameplay.NativeGameplayTracker(999)
    frames = ((101, 1.0, 0x02EB, auth()), (102, 2.0, 0x09FD, actor()))
    assert tracker.consume_snapshot(1, 100, frames)
    position = tracker.view.position
    assert position is not None
    assert position.x == 42
    assert tracker.view.alive_known is False
    before = tracker.view
    assert tracker.consume_snapshot(1, 100, frames)
    assert tracker.view == before
    assert not tracker.consume_snapshot(1, 104, ((105, 3.0, 0x09FD, actor()),))
    assert not tracker.view.actors
    assert not tracker.view.perception_ready
    assert tracker.consume_snapshot(2, 105, ((106, 4.0, 0x09FE, actor(0x09FE)),))
    assert tracker.view.position is None
    assert len(tracker.view.actors) == 1


def test_unknown_framed_event_is_ignored():
    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 1.0, 0x099B, struct.pack("<HHI", 0x099B, 0, 0))
    assert not tracker.view.actors


def test_map_move_and_self_walk_tracks_destination():
    """A clientless client has no walk interpolation: the 0x0087 move-end
    tracks the walk DESTINATION so approaches chain instead of re-walking
    the stale from-cell (the w65-78 crawl fix). The walk is still in
    flight (from != to), so arrival is not confirmed."""
    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 1.0, 0x0091, struct.pack("<H16sHH", 0x0091, b"prontera.gat", 42, 37))
    assert tracker.view.map_name == "prontera.gat"
    # start (42,37) -> destination (43,37)
    move = bytes((42 >> 2, ((42 & 3) << 6) | (37 >> 4), (37 & 15) << 4 | (43 >> 6)))
    move += bytes((((43 & 63) << 2) | (37 >> 8), 37 & 255, 0))
    tracker.ingest(2, 2.0, 0x0087, struct.pack("<HI", 0x0087, 0) + move)
    position = tracker.view.position
    assert position is not None
    assert (position.x, position.y) == (43, 37)
    assert not tracker.view.arrival_confirmed


def test_peer_walking_presentation_never_becomes_own_position():
    """ZC_NOTIFY_PLAYERMOVE has no AID and is sent SELF (clif.cpp2051-2061);
    another actor's walk arrives as 0x09FD unit walking (clif.cpp2088). A peer
    frame encoding the walk destination must not update own position, must not
    confirm arrival, and must not advance the own-position sequence."""

    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 1.0, 0x0091, struct.pack("<H16sHH", 0x0091, b"prontera.gat", 42, 37))
    move = bytes((42 >> 2, ((42 & 3) << 6) | (37 >> 4), (37 & 15) << 4 | (43 >> 6)))
    move += bytes(
        (((43 & 63) << 2) | (37 >> 8), 37 & 255, 0)
    )  # start (42,37) -> destination (43,37)
    tracker.ingest(2, 2.0, 0x0087, struct.pack("<HI", 0x0087, 0) + move)
    peer = bytearray(110)
    struct.pack_into("<HHBII", peer, 0, 0x09FD, 110, 5, 555, 77)
    x, y = 43, 37
    peer[63:66] = bytes((x >> 2, ((x & 3) << 6) | (y >> 4), (y & 15) << 4))
    tracker.ingest(3, 3.0, 0x09FD, bytes(peer))
    position = tracker.view.position
    assert position is not None
    # the peer frame must not advance own position past the tracked destination
    assert (position.x, position.y, position.seq) == (43, 37, 2)
    assert not tracker.view.arrival_confirmed
    assert any(a.actor_id == 555 and a.walking for a in tracker.view.actors)


def test_initial_inventory_weight_barrier_no_absence_fallback():
    tracker = gameplay.NativeGameplayTracker(999)
    weight = struct.pack("<HHi", 0x00B0, 24, 0)
    tracker.ingest(1, 1.0, 0x00B0, weight)
    assert tracker.view.inventory_counts is None
    tracker.ingest(2, 2.0, 0x02EB, auth())
    assert tracker.view.inventory_counts is None
    tracker.ingest(3, 3.0, 0x00B0, weight)
    complete = tracker.view
    assert complete.inventory_counts == ()
    assert complete.inventory_known


def test_damage_xp_death_resurrection_receipts():
    tracker = gameplay.NativeGameplayTracker(999)
    raw = bytearray(34)
    struct.pack_into("<HII", raw, 0, 0x08C8, 999, 123)
    struct.pack_into("<i", raw, 22, 18)
    raw[29] = 0
    struct.pack_into("<i", raw, 30, 4)
    tracker.ingest(1, 1.0, 0x08C8, bytes(raw))
    assert (tracker.view.damage[0].source_id, tracker.view.damage[0].target_id) == (999, 123)
    assert (tracker.view.damage[0].damage, tracker.view.damage[0].damage2) == (18, 4)
    tracker.ingest(2, 2.0, 0x0ACB, struct.pack("<HHq", 0x0ACB, 1, 10))
    first_xp = tracker.view.xp[-1]
    assert first_xp.delta is None
    tracker.ingest(3, 3.0, 0x0ACB, struct.pack("<HHq", 0x0ACB, 1, 25))
    assert tracker.view.xp[-1].delta == 15
    tracker.ingest(4, 4.0, 0x0080, struct.pack("<HIB", 0x0080, 999, 1))
    death_view = tracker.view
    assert death_view.alive_known
    assert not death_view.alive
    assert death_view.deaths[-1].actor_id == 999
    tracker.ingest(5, 5.0, 0x0148, struct.pack("<HIH", 0x0148, 999, 0))
    revived_view = tracker.view
    assert revived_view.alive_known
    assert revived_view.alive
    assert gameplay.respawn() == bytes.fromhex("b20000")


# -- ZC_USE_SKILL (0x09CB): the heal/buff observation source -----------------


def use_skill_frame(
    skill_id: int = 28,
    skill_lv: int = 9,
    target_id: int = 555,
    source_id: int = 4242,
    failed: int = 0,
) -> bytes:
    raw = bytearray(17)
    struct.pack_into("<HHHIIB", raw, 0, 0x09CB, skill_id, skill_lv, target_id, source_id, failed)
    return bytes(raw)


def test_zc_use_skill_receipt_parses_the_skill_fields():
    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 1.0, 0x09CB, use_skill_frame())
    use = tracker.view.skill_uses[0]
    assert (use.skill_id, use.skill_lv, use.target_id, use.source_id) == (28, 9, 555, 4242)
    assert use.failed is False
    tracker.ingest(2, 2.0, 0x09CB, use_skill_frame(skill_id=34, failed=1))
    second = tracker.view.skill_uses[1]
    assert (second.skill_id, second.failed) == (34, True)


def test_zc_use_skill_wrong_length_rejected():
    tracker = gameplay.NativeGameplayTracker(999)
    with pytest.raises(ValueError, match="Malformed"):
        tracker.ingest(1, 1.0, 0x09CB, use_skill_frame()[:-1])
    assert tracker.view.skill_uses == ()


@pytest.mark.parametrize("text", ["hello", "é", "x" * 254])
def test_party_chat_native_nonterminated(text):
    raw = gameplay.party_chat(text, speaker_name="Novice")
    assert (
        raw
        == struct.pack("<HH", 0x0108, 4 + len(("Novice : " + text).encode()))
        + ("Novice : " + text).encode()
    )


@pytest.mark.parametrize("text", ["a\x00b", "x" * 255, "é" * 128])
def test_chat_invalid(text):
    with pytest.raises(ValueError, match=r".+"):
        gameplay.party_chat(text, speaker_name="Novice")


@pytest.mark.parametrize(
    ("pid", "size"),
    [
        (0x0ADD, 22),
        (0x0A37, 59),
        (0x0087, 12),
        (0x0091, 22),
        (0x02EB, 13),
        (0x0080, 7),
        (0x0148, 8),
        (0x08C8, 34),
        (0x0ACB, 12),
    ],
)
def test_known_size_rejected_before_mutation(pid, size):
    tracker = gameplay.NativeGameplayTracker(999)
    raw = struct.pack("<H", pid) + bytes(size - 3)
    before = tracker.view
    with pytest.raises(ValueError, match=r".+"):
        tracker.ingest(1, 1.0, pid, raw)
    assert tracker.view == before


@pytest.mark.parametrize("coordinate", [(0, 0), (42, 37), (1023, 1023)])
def test_self_arrival_exact_packed(coordinate):
    x, y = coordinate
    move = bytes(
        [
            x >> 2,
            ((x << 6) | (y >> 4)) & 255,
            ((y << 4) | (x >> 6)) & 255,
            ((x << 2) | (y >> 8)) & 255,
            y & 255,
            0x88,
        ]
    )
    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 1.0, 0x0087, struct.pack("<HI", 0x0087, 0) + move)
    assert tracker.view.arrival_confirmed


@pytest.mark.parametrize("encoder", [gameplay.attack, gameplay.pickup])
@pytest.mark.parametrize("identifier", [-1, True, 2**32])
def test_identifier_encoder_range(encoder, identifier):
    with pytest.raises(ValueError, match="uint32"):
        encoder(identifier)


def test_corrupt_initial_list_denies_barrier():
    tracker = gameplay.NativeGameplayTracker(999)
    frames = (
        (1, 1.0, 0x02EB, auth()),
        (2, 2.0, 0x0991, bytes.fromhex("9109050000")),
        (3, 3.0, 0x00B0, struct.pack("<HHi", 0x00B0, 24, 0)),
    )
    assert not tracker.consume_snapshot(1, 0, frames)
    assert tracker.view.inventory_counts is None


@pytest.mark.parametrize(("pid", "size"), [(0x00AF, 6), (0x07FA, 8)])
def test_inventory_mutation_invalidates_unimplemented_counts(pid, size):
    tracker = gameplay.NativeGameplayTracker(999)
    tracker.ingest(1, 1.0, 0x02EB, auth())
    tracker.ingest(2, 2.0, 0x00B0, struct.pack("<HHi", 0x00B0, 24, 0))
    tracker.ingest(3, 3.0, pid, struct.pack("<H", pid) + bytes(size - 2))
    assert tracker.view.inventory_counts is None


def test_continuous_attack_is_seven():
    assert gameplay.attack(123, continuous=True)[-1] == 7


@pytest.mark.parametrize("cut", [0, 1, 4, 13, 70, 102, 109])
def test_malformed_actor_no_mutation(cut):
    tracker = gameplay.NativeGameplayTracker(999)
    before = tracker.view
    with pytest.raises(ValueError, match=r".+"):
        tracker.ingest(1, 1.0, 0x09FD, actor()[:cut])
    assert tracker.view == before
