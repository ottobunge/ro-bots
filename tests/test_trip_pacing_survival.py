"""Leg-99 regressions on a simulated wire; no live population effects."""

import struct
from dataclasses import replace
from typing import Any

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import scripts
from robots.app.playing_runtime import ObservedMobDatabase, PlayingClient
from robots.app.scripts import FarmScript, GrindScript
from robots.app.trace_log import TraceLog
from robots.domain.actions import Attack, Rest
from robots.domain.farm import FarmPlan, MobInfo
from robots.domain.model import Goal
from tests.test_playing_runtime import Wire, entry, monster, walk_ack
from tests.test_roam_trip_priority import hit


@pytest.fixture(autouse=True)
def clean_scripts():
    scripts.reset_merchant_talk()
    scripts._KILL_COMMITMENTS.clear()
    yield
    scripts.reset_merchant_talk()
    scripts._KILL_COMMITMENTS.clear()


class TripWire(Wire):
    def keepalive(self):
        pass


class WalkingWire(TripWire):
    """Destination packet with a finite server path and real walk duration.

    Normal walking emits an initial 0x0087, never a terminal walkok. An
    already-reached destination request receives a zero-length walkok.
    """

    def simulate(self, now: list[float], start: tuple[int, int]) -> None:
        self.clock = now
        self.actual = self.destination = start
        self.arrives_at = 0.0
        self.cells_sent: list[int] = []

    def advance(self) -> None:
        if self.clock[0] >= self.arrives_at:
            self.actual = self.destination

    def move(self, x: int, y: int) -> None:
        self.advance()
        # No next chunk should cancel an executing path at this cadence.
        assert self.clock[0] >= self.arrives_at
        destination = (x, y)
        distance = max(abs(x - self.actual[0]), abs(y - self.actual[1]))
        assert distance < 32
        self.cells_sent.append(distance)
        self.moves.append((x, y))
        self.add(walk_ack(self.actual, destination))
        self.destination = destination
        self.arrives_at = self.clock[0] + distance * 0.15


def setup(start=(250, 165), wire_type=TripWire) -> tuple[Any, PlayingClient, list[float]]:
    wire = wire_type()
    wire.frames = []
    wire.add(entry(), struct.pack("<H16sHH", 0x0091, b"pay_fild04", *start))
    now = [0.0]
    catalog = ObservedMobDatabase((MobInfo(1002, "Deviling", 1, base_exp=100, job_exp=50),))
    client = PlayingClient(
        wire,
        mob_db=catalog,
        cache=MapCache((WalkMap("pay_fild04", 400, 400, bytes(160000)),)),
        monotonic=lambda: now[0],
    )
    client.build_native_state(Goal.GRIND)
    return wire, client, now


def test_233_cell_trip_arrives_within_bound_at_leg99_script_cadence(monkeypatch, caplog):
    wire, client, now = setup(wire_type=WalkingWire)
    wire.simulate(now, (250, 165))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    tiles = bytearray([1]) * 160000
    tiles[165 * 400 : 166 * 400] = bytes(400)
    client.cache = MapCache((WalkMap("pay_fild04", 400, 400, bytes(tiles)),))
    farm = GrindScript(merchant_travel_target=client.merchant_travel_target)
    # Real script ticks are 2.3s; merchant patience reaffirms every five ticks.
    for tick in range(130):
        now[0] = tick * 2.3
        client.drain_native_events()
        state = replace(
            client.build_native_state(Goal.GRIND), inventory_known=True, inventory={"511": 2}
        )
        wire.advance()
        if wire.actual == (17, 165):
            break
        for action in farm.step(state).actions:
            client.perform_native(action)
    assert client.build_native_state(Goal.GRIND).x == 17
    assert wire.actual == (17, 165)
    assert now[0] < 233.0
    assert sum(wire.cells_sent) == 233
    assert len(wire.cells_sent) <= 14
    assert "trip_pace=destination_chunks" in caplog.text
    assert "trip_leg_cells_sent=17" in caplog.text


def test_trip_walk_destination_is_received_and_never_authorizes_an_inflight_swing(monkeypatch):
    wire, client, now = setup((100, 165))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    state = replace(
        client.build_native_state(Goal.GRIND), inventory_known=True, inventory={"511": 2}
    )
    action = GrindScript().step(state).actions[0]
    client.perform_native(action)
    destination = wire.moves[-1]
    assert destination[0] == 83
    assert client.build_native_state(Goal.GRIND).x == 100  # no send-based position
    wire.add(walk_ack((100, 165), destination), monster(at=(destination[0] + 1, destination[1])))
    assert client.build_native_state(Goal.GRIND).x == 83  # 0x0087 destination contract
    client.perform_native(Attack(123))
    now[0] = 2.0
    client.drain_native_events()
    now[0] = 4.0
    client.drain_native_events()  # expire pending without receiving arrival
    client.perform_native(Attack(123))
    assert not any(isinstance(row, bytes) and row[:2] == b"\x37\x04" for row in wire.sent)
    wire.add(walk_ack(destination, destination))
    client.drain_native_events()
    client.perform_native(Attack(123))
    assert wire.sent[-1] == bytes.fromhex("37047b00000000")


def farm_for(kind, catalog, trace=None) -> FarmScript | GrindScript:
    if kind == "farm":
        return FarmScript(
            FarmPlan(1, "pay_fild04", ("Deviling",), 300, 42), mob_db=catalog, trace=trace
        )
    return GrindScript(mob_db=catalog, trace=trace)


@pytest.mark.parametrize("kind", ["farm", "grind"])
def test_received_species_spike_refuses_before_authorship_and_at_wire(kind, tmp_path, caplog):
    wire, client, _ = setup((100, 165))
    wire.add(monster(at=(101, 165)), hit(source=123, target=999, amount=31))
    trace = TraceLog(tmp_path, "trace")
    state = client.build_native_state(Goal.GRIND)
    outcome = farm_for(kind, client.mob_db, trace).step(state)
    assert not any(isinstance(action, Attack) for action in outcome.actions)
    assert "attack_refused" in caplog.text
    assert "reason=no_survivability" in caplog.text
    assert "Deviling" in caplog.text
    assert '"no_survivability"' in (tmp_path / "trace.jsonl").read_text()
    client.perform_native(Attack(123))
    assert any(row.get("reason") == "no_survivability" for row in client.drain_swing_telemetry())
    assert not any(isinstance(row, bytes) and row[:2] == b"\x37\x04" for row in wire.sent)
    # Evidence applies to the species, including a different newly received actor.
    wire.add(struct.pack("<HIB", 0x0080, 123, 1), monster(aid=456, at=(101, 165)))
    outcome = farm_for(kind, client.mob_db).step(client.build_native_state(Goal.GRIND))
    assert Attack(456) not in outcome.actions


@pytest.mark.parametrize("kind", ["farm", "grind"])
def test_fresh_unknown_species_is_attackable_and_low_hp_skips_it(kind):
    wire, client, _ = setup((100, 165))
    client.mob_db = ObservedMobDatabase(())
    wire.add(monster(at=(101, 165)))
    state = client.build_native_state(Goal.GRIND)
    script = farm_for(kind, client.mob_db)
    if kind == "farm":
        script = FarmScript(
            FarmPlan(1, "pay_fild04", ("monster#1002",), 300, 42), mob_db=client.mob_db
        )
    assert script.step(state).actions == (Attack(123),)
    assert Attack(123) not in script.step(replace(state, hp=39)).actions
    assert script.step(replace(state, hp=1)).actions == (Rest(),)


@pytest.mark.parametrize(
    ("amount", "hp", "allowed"), [(30, 100, True), (31, 100, False), (20, 60, False)]
)
def test_hit_ceiling_uses_current_hp_and_strict_thirty_percent(amount, hp, allowed):
    wire, client, _ = setup((100, 165))
    wire.status_params[5] = hp
    wire.add(monster(at=(101, 165)), hit(source=123, target=999, amount=amount))
    outcome = farm_for("grind", client.mob_db).step(client.build_native_state(Goal.GRIND))
    assert (Attack(123) in outcome.actions) is allowed


@pytest.mark.parametrize("boundary", ["expiry", "epoch"])
def test_received_damage_expires_without_snapshot_refresh_and_resets_at_boundaries(boundary):
    wire, client, now = setup((100, 165))
    wire.add(monster(at=(101, 165)), hit(source=123, target=999, amount=31))
    assert client.build_native_state(Goal.GRIND).recent_species_damage == (("Deviling", 31),)
    now[0] = 119.0
    assert client.build_native_state(Goal.GRIND).recent_species_damage == (("Deviling", 31),)
    if boundary == "expiry":
        now[0] = 120.0
    else:
        wire.native_epoch += 1
        wire.selection_epoch = wire.map_epoch = wire.native_epoch
        wire.frames = []
        wire.add(entry(), struct.pack("<H16sHH", 0x0091, b"pay_fild04", 100, 165))
    assert client.build_native_state(Goal.GRIND).recent_species_damage == ()


@pytest.mark.parametrize("case", ["peer_target", "unknown_source", "miss", "sp", "zero"])
def test_only_received_own_positive_hp_damage_teaches_species_risk(case):
    wire, client, _ = setup((100, 165))
    raw = bytearray(hit(source=123, target=999, amount=31))
    if case == "peer_target":
        struct.pack_into("<I", raw, 6, 777)
    elif case == "unknown_source":
        struct.pack_into("<I", raw, 2, 777)
    elif case == "miss":
        raw[29] = 3
    elif case == "sp":
        raw[26] = 1
    else:
        struct.pack_into("<i", raw, 22, 0)
    wire.add(monster(at=(101, 165)), bytes(raw))
    state = client.build_native_state(Goal.GRIND)
    assert state.recent_species_damage == ()
    assert farm_for("grind", client.mob_db).step(state).actions == (Attack(123),)


def test_refused_committed_species_yields_to_another_species_and_resources_stay_exempt():
    wire, client, _ = setup((100, 165))
    wire.add(monster(at=(101, 165)))
    script = farm_for("grind", client.mob_db)
    assert script.step(client.build_native_state(Goal.GRIND)).actions == (Attack(123),)
    client.mob_db = ObservedMobDatabase(
        (
            MobInfo(1002, "Deviling", 1, base_exp=100, job_exp=50),
            MobInfo(1003, "Green Plant", 1, base_exp=0, job_exp=0),
        )
    )
    plant = bytearray(monster(aid=456, at=(101, 165)))
    struct.pack_into("<H", plant, 23, 1003)
    script = farm_for("grind", client.mob_db)
    wire.add(bytes(plant), hit(source=123, target=999, amount=31))
    state = client.build_native_state(Goal.GRIND)
    assert script.step(state).actions == (Attack(456),)
    assert script.step(replace(state, hp=39)).actions == (Attack(456),)
    assert script.step(replace(state, hp=1)).actions == (Rest(),)


def test_other_walks_keep_single_step_pacing():
    _, client, _ = setup((100, 165))
    state = client.build_native_state(Goal.GRIND)
    client._perform_move(state, (17, 165))
    assert client._pending is not None
    assert max(abs(client._pending[0][0] - state.x), abs(client._pending[0][1] - state.y)) == 1
    assert "trip_pace" not in client.last_move_outcome


def test_recent_species_risk_survives_warp_and_received_self_respawn():
    wire, client, _ = setup((100, 165))
    wire.add(monster(at=(101, 165)), hit(source=123, target=999, amount=64))
    assert client.build_native_state(Goal.GRIND).recent_species_damage == (("Deviling", 64),)
    wire.add(struct.pack("<HIB", 0x0080, 999, 1))
    wire.add(struct.pack("<H16sHH", 0x0091, b"pay_fild04", 100, 165))
    wire.add(monster(aid=456, at=(101, 165)))
    state = client.build_native_state(Goal.GRIND)
    assert state.recent_species_damage == (("Deviling", 64),)
    assert Attack(456) not in farm_for("grind", client.mob_db).step(state).actions


def test_far_town_trip_uses_chunks_but_preserves_local_dealer_steps(monkeypatch):
    wire, client, now = setup((177, 100))
    wire.add(struct.pack("<H16sHH", 0x0091, b"prontera", 177, 100))
    client.cache = MapCache((WalkMap("prontera", 400, 400, bytes(160000)),))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    state = replace(
        client.build_native_state(Goal.GRIND), inventory_known=True, inventory={"511": 2}
    )
    action = (
        GrindScript(merchant_travel_target=client.merchant_travel_target).step(state).actions[0]
    )
    client.perform_native(action)
    first = wire.moves[-1]
    assert max(abs(first[0] - 177), abs(first[1] - 100)) == 17
    assert client.last_move_outcome["trip_pace"] == "destination_chunks"
    # At the occupied dealer entrance, retain the staging allocator's exact
    # single steps instead of letting the server choose a path through bodies.
    wire.add(struct.pack("<H16sHH", 0x0091, b"prontera", 177, 214))
    client.perform_native(action)
    second = wire.moves[-1]
    assert max(abs(second[0] - 177), abs(second[1] - 214)) == 1
    assert "trip_pace" not in client.last_move_outcome


def test_town_chunks_cannot_bypass_a_received_body_detour(monkeypatch):
    wire, client, now = setup((177, 100))
    wire.add(struct.pack("<H16sHH", 0x0091, b"prontera", 177, 100))
    wire.add(monster(kind=0, aid=456, at=(177, 110)))
    client.cache = MapCache((WalkMap("prontera", 400, 400, bytes(160000)),))
    monkeypatch.setattr(scripts, "_merchant_now", lambda: now[0])
    state = replace(
        client.build_native_state(Goal.GRIND), inventory_known=True, inventory={"511": 2}
    )
    assert (177, 110) in state.occupied_cells
    action = (
        GrindScript(merchant_travel_target=client.merchant_travel_target).step(state).actions[0]
    )
    client.perform_native(action)
    point = wire.moves[-1]
    assert max(abs(point[0] - 177), abs(point[1] - 100)) == 1
    assert client.last_move_outcome["reason"] == "step"
