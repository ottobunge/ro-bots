"""Leg-98 plant-patch escape and merchant travel ownership, offline only."""

import struct
from dataclasses import replace

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import scripts
from robots.app.merchant_trip import MerchantTrip
from robots.app.playing_runtime import ObservedMobDatabase, PlayingClient
from robots.app.scripts import FarmScript, GrindScript
from robots.domain.actions import Attack, MoveTo, Rest
from robots.domain.farm import FarmPlan, MobInfo
from robots.domain.model import Goal
from tests.test_playing_runtime import Wire, entry, monster, walk_ack


def hit(source: int = 999, target: int = 123, amount: int = 1, damage_type: int = 0) -> bytes:
    raw = bytearray(34)
    struct.pack_into("<HII", raw, 0, 0x08C8, source, target)
    struct.pack_into("<i", raw, 22, amount)
    raw[29] = damage_type
    return bytes(raw)


def death(target: int = 123) -> bytes:
    return struct.pack("<HIB", 0x0080, target, 1)


def setup() -> tuple[Wire, PlayingClient, list[float]]:
    wire = Wire()
    wire.frames = []
    wire.add(
        entry(), struct.pack("<H16sHH", 0x0091, b"pay_fild04", 200, 200), monster(at=(201, 200))
    )
    now = [0.0]
    catalog = ObservedMobDatabase((MobInfo(1002, "Green Plant", 1, base_exp=0, job_exp=0),))
    client = PlayingClient(
        wire,
        mob_db=catalog,
        cache=MapCache((WalkMap("pay_fild04", 400, 400, bytes(160000)),)),
        monotonic=lambda: now[0],
    )
    client.build_native_state(Goal.GRIND)
    return wire, client, now


def script(kind: str, catalog: ObservedMobDatabase) -> FarmScript | GrindScript:
    if kind == "farm":
        return FarmScript(FarmPlan(1, "pay_fild04", ("Green Plant",), 300, 42), mob_db=catalog)
    return GrindScript(mob_db=catalog)


@pytest.fixture(autouse=True)
def fresh_memos():
    scripts.reset_merchant_talk()
    scripts._KILL_COMMITMENTS.clear()
    yield
    scripts.reset_merchant_talk()
    scripts._KILL_COMMITMENTS.clear()


@pytest.mark.parametrize("kind", ["farm", "grind"])
def test_twenty_received_expless_hits_widen_anchor_and_keep_commitment(kind, caplog):
    wire, client, _ = setup()
    farm = script(kind, client.mob_db)
    state = replace(client.build_native_state(Goal.GRIND), job="Swordsman")
    assert farm.step(state).actions == (Attack(123),)
    wire.add(*(hit() for _ in range(19)))
    state = replace(client.build_native_state(Goal.GRIND), job="Swordsman")
    assert farm.step(state).actions == (Attack(123),)
    wire.add(hit())
    state = replace(client.build_native_state(Goal.GRIND), job="Swordsman")
    outcome = farm.step(state)
    assert len(outcome.actions) == 1
    move = outcome.actions[0]
    assert isinstance(move, MoveTo)
    assert max(abs(move.x - state.x), abs(move.y - state.y)) == 24
    assert "roam_anchor_widened_expless" in caplog.text
    assert "landed_hits=20" in caplog.text
    # Re-reading a snapshot cannot count another hit or reroll the leg.
    assert farm.step(replace(client.build_native_state(Goal.GRIND), job="Swordsman")).actions == (
        move,
    )
    assert scripts._KILL_COMMITMENTS[state.name]._target_id == 123
    assert farm.step(replace(state, hp=1)).actions == (Rest(),)
    wire.add(walk_ack((move.x, move.y), (move.x, move.y)))
    arrived = client.build_native_state(Goal.GRIND)
    assert arrived.roam_escape_target is None


@pytest.mark.parametrize("reset", ["kill", "reward", "map"])
def test_kills_rewarding_hits_and_map_changes_reset_expless_streak(reset):
    wire, client, _ = setup()
    wire.add(*(hit() for _ in range(19)))
    client.build_native_state(Goal.GRIND)
    if reset == "kill":
        wire.add(death())
    elif reset == "reward":
        client.mob_db = ObservedMobDatabase((MobInfo(1002, "Poring", 1, base_exp=2, job_exp=1),))
        wire.add(hit())
        client.build_native_state(Goal.GRIND)
        client.mob_db = ObservedMobDatabase(
            (MobInfo(1002, "Green Plant", 1, base_exp=0, job_exp=0),)
        )
    else:
        wire.add(struct.pack("<H16sHH", 0x0091, b"pay_fild04", 200, 200))
    wire.add(monster(at=(201, 200)), hit())
    assert client.build_native_state(Goal.GRIND).roam_escape_target is None


@pytest.mark.parametrize("bad_hit", [hit(source=777), hit(amount=0), hit(damage_type=3)])
def test_only_own_landed_hits_can_widen(bad_hit):
    wire, client, _ = setup()
    wire.add(*(bad_hit for _ in range(30)))
    assert client.build_native_state(Goal.GRIND).roam_escape_target is None


def test_escape_replans_after_bounded_stall_and_never_invents_a_position():
    wire, client, now = setup()
    wire.add(*(hit() for _ in range(20)))
    state = client.build_native_state(Goal.GRIND)
    target = state.roam_escape_target
    assert target is not None
    now[0] = 60.0
    stalled = client.build_native_state(Goal.GRIND)
    assert stalled.roam_escape_target is not None
    assert stalled.roam_escape_target != target
    assert (stalled.x, stalled.y) == (200, 200)


@pytest.mark.parametrize("kind", ["farm", "grind"])
@pytest.mark.parametrize("map_name", ["pay_fild04", "prt_fild08"])
def test_active_trip_owns_empty_ticks_ahead_of_script_and_runtime_roaming(
    kind, map_name, monkeypatch
):
    wire, client, now = setup()
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    state = replace(
        client.build_native_state(Goal.GRIND),
        map_name=map_name,
        inventory_known=True,
        inventory={"511": 2},
        nearby=(),
    )
    client.cache = MapCache((WalkMap(map_name, 400, 400, bytes(160000)),))
    farm = script(kind, client.mob_db)
    route = farm.step(state)
    assert route.actions == (MoveTo(*scripts.MERCHANT_ROUTE[map_name]),)
    # Patience ticks contain no action: no competing farm/patrol MoveTo may fill them.
    for _ in range(3):
        outcome = farm.step(state)
        assert outcome.actions == ()
        assert client.mechanical_actions(state, outcome.actions) == ()
    assert not wire.moves
    assert client._patrol is None


def test_merchant_travel_preempts_armed_escape(monkeypatch):
    wire, client, now = setup()
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    wire.add(*(hit() for _ in range(20)))
    state = replace(
        client.build_native_state(Goal.GRIND), inventory_known=True, inventory={"511": 2}
    )
    assert state.roam_escape_target is not None
    assert script("farm", client.mob_db).step(state).actions == (MoveTo(17, 165),)


def test_route_distance_scales_bound_but_stall_still_releases(caplog):
    trip = MerchantTrip(3, 233, 0.0)
    assert trip.advance("s00", 3, 233, 60.0)
    assert trip.advance("s00", 3, 400, 232.9)  # backtracking cannot inflate the bound
    assert not trip.advance("s00", 3, 233, 233.0)
    assert "bound_s=233" in caplog.text
    assert "rule=route_distance_scaled" in caplog.text
    assert trip.cooling_down(234.0)


@pytest.mark.parametrize(
    ("distance", "bound"), [(0, 60.0), (20, 60.0), (233, 233.0), (2000, 300.0)]
)
def test_route_bound_has_floor_and_ceiling(distance, bound):
    trip = MerchantTrip(3, distance, 0.0)
    assert trip.advance("s00", 3, distance, bound - 0.1)
    assert not trip.advance("s00", 3, distance, bound)


def test_escape_memory_is_per_client_and_target_is_deterministic():
    wire, first, _ = setup()
    _, second, _ = setup()
    wire.add(*(hit() for _ in range(20)))
    target = first.build_native_state(Goal.GRIND).roam_escape_target
    assert target is not None
    assert second.build_native_state(Goal.GRIND).roam_escape_target is None
    other_wire, third, _ = setup()
    other_wire.add(*(hit() for _ in range(20)))
    assert third.build_native_state(Goal.GRIND).roam_escape_target == target


def test_escape_uses_runtime_reachability_and_skips_blocked_direction():
    wire, client, _ = setup()
    tiles = bytearray(160000)
    tiles[224 + 200 * 400] = 1
    client.cache = MapCache((WalkMap("pay_fild04", 400, 400, bytes(tiles)),))
    wire.add(*(hit() for _ in range(20)))
    assert client.build_native_state(Goal.GRIND).roam_escape_target == (200, 224)


def test_missing_rewards_do_not_label_received_hits_expless():
    wire, client, _ = setup()
    client.mob_db = ObservedMobDatabase((MobInfo(1002, "Unknown", 1),))
    wire.add(*(hit() for _ in range(30)))
    assert client.build_native_state(Goal.GRIND).roam_escape_target is None


def test_new_native_epoch_discards_armed_escape():
    wire, client, _ = setup()
    wire.add(*(hit() for _ in range(20)))
    assert client.build_native_state(Goal.GRIND).roam_escape_target is not None
    wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    wire.frames = []
    wire.add(entry(), struct.pack("<H16sHH", 0x0091, b"pay_fild04", 200, 200))
    assert client.build_native_state(Goal.GRIND).roam_escape_target is None
