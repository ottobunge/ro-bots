"""Synthetic wire contracts, NOT live gameplay evidence."""

import argparse
import json
import struct
import zlib
from types import SimpleNamespace
from typing import Any, cast

import pytest

from robots import playing
from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.native_gameplay import npc_close
from robots.adapters.native_navigation import ENTRY, HEADER, MapCache, WalkMap
from robots.adapters.native_progression import SelectedCharacterSnapshot
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.adapters.playing_backends import PlayingChat, PlayingDecision
from robots.app import agent_runtime
from robots.app import playing_runtime as runtime
from robots.app.agent_runtime import AgentHost, ManifestEntry, PersonaClock, ScheduledAgent
from robots.app.brain import EventDrivenBrain
from robots.app.scripts import GrindScript
from robots.domain.actions import Attack, Loot, MoveTo, PartyChat, Rest, Say
from robots.domain.decisions import build_decision_request
from robots.domain.events import DamageTaken, MonsterSpotted
from robots.domain.model import BotState, Goal
from robots.society.models import Attitude, Playstyle, SocietyPersona


def position(x=42, y=37) -> bytes:
    return bytes((x >> 2, ((x & 3) << 6) | (y >> 4), (y & 15) << 4))


def entry() -> bytes:
    return b"\xeb\x02" + bytes(4) + position() + bytes(4)


def map_frame() -> bytes:
    return struct.pack("<H16sHH", 0x0091, b"prontera", 42, 37)


def monster(kind=5, aid=123, at=(45, 41)) -> bytes:
    raw = bytearray(103)
    struct.pack_into("<HHBII", raw, 0, 0x09FE, 103, kind, aid, 77)
    raw[59:62] = position(*at)
    struct.pack_into("<H", raw, 23, 1002)
    return bytes(raw)


class Wire:
    def __init__(self) -> None:
        self.aid = 999
        self.gid = 77
        self.char_name = "WireNovice"
        self.running = self.connected_map = True
        self.sock = object()
        self.rx_thread = SimpleNamespace(is_alive=lambda: True)
        self.rx_error = None
        self.dispatch_errors: list[Any] = []
        self.native_epoch = self.selection_epoch = self.map_epoch = 1
        self.class_fresh = True
        self.selected_character_snapshot = SelectedCharacterSnapshot(77, 0, 10, 10, 0, 0)
        self.status_params = {5: 100, 6: 100, 7: 20, 8: 20}
        self.map_name = "prontera"
        self.chat: list[tuple[int, str]] = []
        self.actors: dict[int, Any] = {}
        self.party_id = 0
        self.party_members: list[dict[str, Any]] = []
        self.party_invite_pid = 0
        self.party_invite_from = ""
        self.frames: list[tuple[int, float, int, bytes]] = []
        self.sent: list[Any] = []
        self.moves: list[tuple[int, int]] = []
        self.add(entry(), map_frame(), monster())

    def add(self, *raws: bytes) -> None:
        for raw in raws:
            seq = len(self.frames) + 1
            self.frames.append((seq, float(seq), int.from_bytes(raw[:2], "little"), raw))

    def native_frame_snapshot(self):
        return self.native_epoch, 0, tuple(self.frames)

    def _send(self, raw):
        self.sent.append(raw)

    def move(self, x, y):
        self.moves.append((x, y))

    def say(self, text):
        self.sent.append(text)

    def sit(self):
        self.sent.append("sit")

    def stand(self):
        self.sent.append("stand")


def test_standing_recovery_rearms_indefinitely_and_names_block() -> None:
    """w65: a join-era sit pose (0x08C8 raw[29]==2) can flip standing False
    after the 0x02EB baseline. The old recovery sent wire.stand() three
    times within a 3s window, then went permanently silent — every perform
    dropped as not_standing for the rest of the window with no telemetry.
    The recovery must keep re-arming (bounded backoff, unbounded epochs)
    while the agent is alive, and expose a stall reason."""
    wire = Wire()
    wire.add(map_frame())
    clock = {"t": 100.0}
    client = runtime.PlayingClient(wire)
    client._now = lambda: clock["t"]
    client.build_native_state(Goal.GRIND)
    # the join-era sit pose flips standing off AFTER the entry baseline
    sit = bytearray(34)
    struct.pack_into("<HI", sit, 0, 0x08C8, wire.aid)
    sit[29] = 2
    wire.add(bytes(sit))
    client.drain_native_events()

    # three recovery attempts exhaust the first epoch; the old code stopped here
    for i in range(3):
        if i:
            clock["t"] += 1.1
        client.perform_native(MoveTo(46, 41))
    sent_after_first_epoch = len([f for f in wire.sent if f == "stand"])
    assert sent_after_first_epoch >= 3

    # a later epoch still re-arms: the recovery is never permanently silent
    for _ in range(3):
        clock["t"] += 4.0
        client.perform_native(MoveTo(46, 41))
    sent_after_second_epoch = len([f for f in wire.sent if f == "stand"])
    assert sent_after_second_epoch > sent_after_first_epoch

    # the block NAMES itself in the movement telemetry
    reasons = getattr(client, "_move_gate_reasons", ()) or ()
    assert any("standing" in str(r) for r in reasons), reasons


def test_last_built_state_reads_without_reobserving() -> None:
    """w65-67 root cause: an instrumentation read that re-observes advances
    the metadata cursor and empties the runtime's event windows. The cached
    accessor must return the same state object without a second observe."""
    wire = Wire()
    wire.add(map_frame())
    client = runtime.PlayingClient(wire)
    assert client.last_built_state is None  # nothing built yet
    state = client.build_native_state(Goal.GRIND)
    assert client.last_built_state is state


def test_grind_script_roams_when_no_mobs_in_view() -> None:
    """w65-69: the goal-grind path (GrindScript, no authored plan) must roam
    when the view is empty — the FarmScript got the roam leg; the GrindScript
    still stood still, which is exactly what the goal-assigned agents run."""
    script = GrindScript()
    state = BotState(
        name="bot",
        job="Novice",
        base_level=1,
        hp=100,
        max_hp=100,
        sp=10,
        max_sp=10,
        map_name="prt_fild08",
        x=100,
        y=100,
        goal=Goal.GRIND,
        in_party=False,
        nearby=(),
        inventory={},
        pending_invites=(),
        recent_chat=(),
    )
    outcome = script.step(state)
    moves = [a for a in outcome.actions if isinstance(a, MoveTo)]
    assert moves, "the GrindScript empty view must roam, not stand"


def test_wire_state_not_persona_truth():
    client = runtime.PlayingClient(Wire())
    state = client.build_native_state(Goal.GRIND)
    assert (state.job, state.base_level, state.x, state.y) == ("Novice", 10, 42, 37)
    assert state.nearby[0].kind == "monster"
    assert state.nearby[0].distance == 5.0
    assert not state.inventory_known
    assert build_decision_request(state)["state"]["inventory"] == "unknown"


@pytest.mark.parametrize("flag", ["running", "connected_map", "class_fresh"])
def test_unhealthy_never_builds_state(flag):
    wire = Wire()
    setattr(wire, flag, False)
    with pytest.raises(NativeTelemetryUnavailable):
        runtime.PlayingClient(wire).build_native_state(Goal.GRIND)


@pytest.mark.parametrize("kind", [0, 6, 12, 255])
def test_unproven_actor_is_not_player_or_monster(kind):
    wire = Wire()
    wire.frames = []
    wire.add(entry(), map_frame(), monster(kind))
    state = runtime.PlayingClient(wire).build_native_state(Goal.GRIND)
    assert state.nearby_players == ()
    assert state.nearby_monsters == ()
    if kind in (6, 12):
        assert len(state.nearby) == 1
        actor = state.nearby[0]
        assert (actor.id, actor.name, actor.kind, actor.distance) == (123, "NPC#123", "npc", 5.0)
    else:
        assert state.nearby == ()


def test_native_attack_bytes_and_death_denial():

    wire = Wire()
    client = runtime.PlayingClient(wire)
    client.perform_native(Attack(123))
    assert wire.sent == [bytes.fromhex("37047b00000000")]
    wire.add(struct.pack("<HIB", 0x0080, 999, 1))
    client.perform_native(Attack(123))
    assert len(wire.sent) == 1
    assert client.build_native_state(Goal.GRIND).alive is False


@pytest.mark.parametrize("target", [999, (-999) & 0xFFFFFFFF, 0, 321])
def test_attack_denies_unseen_and_self(target):

    wire = Wire()
    runtime.PlayingClient(wire).perform_native(Attack(target))
    assert not wire.sent


def test_party_chat_is_not_public():

    wire = Wire()
    wire.party_members = [{"aid": 999}]
    runtime.PlayingClient(wire).perform_native(PartyChat("hello"))
    assert wire.sent[0][:2] == b"\x08\x01"
    assert b"WireNovice : hello" in wire.sent[0]


def test_loot_uses_visible_floor_id_without_claiming_inventory():

    wire = Wire()
    wire.add(struct.pack("<HIHHBhhBBh", 0x0ADD, 321, 501, 0, 1, 42, 37, 0, 0, 3) + bytes(3))
    client = runtime.PlayingClient(wire)
    client.perform_native(Loot())
    assert wire.sent == [bytes.fromhex("620341010000")]
    assert not client.build_native_state(Goal.GRIND).inventory_known


def test_host_delegates_native_state_and_actions():

    persona = SocietyPersona("one", "one", Playstyle.MELEE, Attitude.GRINDER, 0.5, (99, 99))
    wire = Wire()
    agent = ScheduledAgent(
        persona,
        ManifestEntry("one", "dummy", "dummy", "WireNovice"),
        client=runtime.PlayingClient(wire),
        threaded=False,
    )
    assert agent.build_state().base_level == 10
    agent.execute_actions((Attack(123),))
    assert wire.sent == [bytes.fromhex("37047b00000000")]


def walk_ack(start, end) -> bytes:
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


def test_movement_waits_for_same_target_receipt():
    """A same-target walk that is EXECUTING waits (no canceling re-send);
    when its position frames stall past 1s the slot releases for a fresh
    approach from the current geometry (w57's crawl fix)."""

    wire = Wire()
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    now = [0.0]
    client = runtime.PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    client.perform_native(MoveTo(43, 37))
    client.perform_native(MoveTo(44, 37))
    assert wire.moves == [(43, 37)]
    wire.add(walk_ack((42, 37), (43, 37)))
    now[0] = 2.0
    client.perform_native(MoveTo(44, 37))
    # The moving walkok means the walk is EXECUTING: no canceling re-send.
    assert wire.moves == [(43, 37)]
    now[0] = 3.5
    client.perform_native(MoveTo(44, 37))
    # The frames stalled 1.5s with the point unproven: the release + the
    # fresh approach FROM THE TRACKED DESTINATION (the 0x0087 tracks the
    # walk's to-cell, so the chain advances instead of re-walking the
    # stale from-cell — the w65-78 crawl fix).
    assert wire.moves == [(43, 37), (44, 37)]
    assert client.build_native_state(Goal.GRIND).x == 43
    wire.add(walk_ack((44, 37), (44, 37)))
    client.perform_native(MoveTo(44, 37))
    assert wire.moves[-1] == (44, 37)


def test_drained_receipt_releases_pending_walk_without_new_dispatch():
    """Window-3 live shape: one dispatched walk, then the host dispatches nothing.

    clif_walkok (pinned e985 clif.cpp2051-2061) answers a real walk with
    start != destination, and the server sends nothing when the walk completes.
    The bounded re-request must therefore be paced on the received-frame drain
    path; otherwise a host that stops dispatching freezes the single pending
    slot and starves every later attack/move/loot send.
    """

    wire = Wire()
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    now = [0.0]
    client = runtime.PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    client.perform_native(MoveTo(43, 37))
    assert wire.moves == [(43, 37)]
    wire.add(walk_ack((42, 37), (43, 37)))
    now[0] = 1.5
    client.drain_native_events()
    # The moving walkok means the walk is EXECUTING: no stale re-send.
    assert wire.moves == [(43, 37)]
    # The frames then stall (the host dispatches nothing and the walk ends
    # silently): the 1s frame-stall (the ack frame is at t=4.0 in the
    # fixture's seq-clock) releases the slot for a fresh approach.
    now[0] = 5.1
    client.drain_native_events()
    assert client._pending is None
    assert wire.moves == [(43, 37)]
    client.perform_native(MoveTo(44, 37))
    # The tracked position is the walk's destination (43,37): a fresh
    # MoveTo advances to the NEXT cell instead of re-walking the stale
    # from-cell (the w65-78 crawl fix).
    assert wire.moves == [(43, 37), (44, 37)]
    wire.add(walk_ack((44, 37), (44, 37)))
    client.drain_native_events()
    assert client.build_native_state(Goal.GRIND).x == 44
    client.perform_native(Attack(123))
    assert wire.sent == [bytes.fromhex("37047b00000000")]


def test_walk_that_executed_but_did_not_prove_point_releases_for_fresh_approach():
    """Mobs wander: a moved-but-unproven walk must release the slot so the
    script re-approaches from the current geometry, instead of re-moving to
    the stale point until exhaustion (the 8-walks-per-30-minutes crawl)."""
    wire = Wire()
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    now = [0.0]
    client = runtime.PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    client.perform_native(MoveTo(43, 37))
    # The char walked (the position advanced along the path) but stopped
    # short of the requested point: (44, 37) instead of (43, 37).
    now[0] = 1.5
    wire.add(walk_ack((44, 37), (44, 37)))
    client.drain_native_events()
    assert client._pending is None, "the moved walk must release the slot"
    # The next approach emits a FRESH move without any exhaust exception.
    client.perform_native(MoveTo(46, 37))
    assert wire.moves[-1] == (
        45,
        37,
    ), "the fresh approach walks the first step toward the new point"


def test_move_gate_reason_recorded_for_blocked_move():
    """w58: the receipt must name WHY a scripted MoveTo sent nothing."""
    wire = Wire()
    now = [0.0]
    client = runtime.PlayingClient(wire, monotonic=lambda: now[0])
    client.cache = None
    wire.frames = []
    wire.add(entry(), map_frame(), monster())
    client.perform_native(MoveTo(44, 37))
    assert "no_map_cache" in getattr(client, "_move_gate_reasons", ()) or any(
        reason == "no_map_cache" for _, reason in getattr(client, "_move_gate_reasons", [])
    )


def blocked_map(blocked: tuple[int, int], name: str = "prontera") -> MapCache:
    """A 12x12 all-walkable grid with exactly one blocked cell."""
    size = 12
    tiles = bytearray(size * size)
    tiles[blocked[0] + blocked[1] * size] = 1
    return MapCache((WalkMap(name, size, size, bytes(tiles)),))


def entry_at(x: int, y: int) -> bytes:
    return b"\xeb\x02" + bytes(4) + position(x, y) + bytes(4)


def map_frame_at(x: int, y: int) -> bytes:
    return struct.pack("<H16sHH", 0x0091, b"prontera", x, y)


def test_no_route_walks_direct_at_the_target():
    """leg 28: the field warp cell (170,378) is unwalkable in the client
    grid, so shortest_path raised NoRoute and _move sent NOTHING - the
    server never moved the unit, the warp never fired, and the script
    re-authored the same MoveTo 97 times. The clientless client must send
    the walk DIRECTLY at the target on NoRoute: the server path-finds its
    own side (the spike clients always worked this way), and the pending
    lifecycle paces the retries."""

    wire = Wire()
    now = [0.0]
    client = runtime.PlayingClient(wire, cache=blocked_map((5, 5)), monotonic=lambda: now[0])
    wire.frames = []
    wire.add(entry_at(2, 2), map_frame_at(2, 2))
    client.perform_native(MoveTo(5, 5))
    assert wire.moves == [(5, 5)]
    assert any(reason == "no_route_direct" for _, reason in client._move_gate_reasons)
    assert client._pending is not None


def test_no_route_direct_sends_are_bounded():
    """A cell unreachable on BOTH sides must not be retried forever: the
    direct sends are capped per (map, target); the exhaustion fails the
    patrol so the goal layer re-rolls a reachable target."""

    wire = Wire()
    now = [0.0]
    client = runtime.PlayingClient(wire, cache=blocked_map((5, 5)), monotonic=lambda: now[0])
    wire.frames = []
    wire.add(entry_at(2, 2), map_frame_at(2, 2))
    for _ in range(runtime.NO_ROUTE_DIRECT_SENDS):
        client.perform_native(MoveTo(5, 5))
        client._pending = None  # the drain released the slot
    sent = len(wire.moves)
    assert sent == runtime.NO_ROUTE_DIRECT_SENDS
    client.perform_native(MoveTo(5, 5))
    assert len(wire.moves) == sent  # exhausted: nothing more is sent
    assert any(reason == "no_route_exhausted" for _, reason in client._move_gate_reasons)


def test_no_route_attempts_reset_when_a_route_exists():
    """A target that was once unreachable re-sends from a fresh budget once
    the grid finds a route to it: the cap counts CONSECUTIVE no-route
    attempts per (map, target), not lifetime."""

    wire = Wire()
    now = [0.0]
    client = runtime.PlayingClient(wire, cache=blocked_map((5, 5)), monotonic=lambda: now[0])
    wire.frames = []
    wire.add(entry_at(2, 2), map_frame_at(2, 2))
    for _ in range(runtime.NO_ROUTE_DIRECT_SENDS):
        client.perform_native(MoveTo(5, 5))
        client._pending = None
    client.perform_native(MoveTo(6, 6))  # walkable: a route exists
    client._pending = None
    client.perform_native(MoveTo(5, 5))
    assert len(wire.moves) == runtime.NO_ROUTE_DIRECT_SENDS + 2


def test_drain_paced_walk_releases_on_stall_without_stale_resend():
    """The walk stalls with the point unproven: the slot releases so the next
    scripted approach is a FRESH move from the current geometry — the old
    bounded re-send re-moved to the stale point and crawled the approach
    (w57). The drain itself stays the pacing point on the received path."""

    wire = Wire()
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    now = [0.0]
    client = runtime.PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    client.perform_native(MoveTo(43, 37))
    now[0] = 3.5  # the last position frame (the 0x0091) at t=2.0: the 1.5s stall
    client.drain_native_events()
    # No position frames since the send: the walk is done, blocked, or the
    # ack was lost — the slot released either way.
    assert client._pending is None
    assert wire.moves == [(43, 37)]
    now[0] = 3.0
    client.perform_native(MoveTo(44, 37))
    assert wire.moves == [(43, 37), (43, 37)]
    now[0] = 5.0
    client.drain_native_events()
    wire.add(walk_ack((43, 37), (43, 37)))
    client.drain_native_events()
    client.perform_native(Attack(123))
    assert wire.sent == [bytes.fromhex("37047b00000000")]


def test_peer_walk_presentation_cannot_release_pending_or_own_position():
    """0x0087 is SELF-scoped with no AID (clif.cpp2051-2061); other actors'
    walks arrive as 0x09FD unit walking (clif.cpp2088). A peer walking frame
    that encodes the pending destination must not become own position and must
    never release the pending gate: only the self zero-cell walkok can."""

    wire = Wire()
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    now = [0.0]
    client = runtime.PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    client.perform_native(MoveTo(43, 37))
    peer = bytearray(110)
    struct.pack_into("<HHBII", peer, 0, 0x09FD, 110, 5, 555, 77)
    x, y = 43, 37
    peer[63:66] = bytes((x >> 2, ((x & 3) << 6) | (y >> 4), (y & 15) << 4))
    wire.add(bytes(peer))
    # The peer frame neither moved the own position nor released the gate on
    # its own; the 1s walk stall did (the position never advanced after the
    # entry frame at t=1.0). The slot releases so the next scripted approach
    # is a FRESH move.
    now[0] = 3.5  # the position frame is the 0x0091 at t=2.0: 3.5-2.0 = the 1.5s stall
    client.drain_native_events()
    assert client._pending is None
    assert wire.moves == [(43, 37)]
    assert client.build_native_state(Goal.GRIND).x == 42
    # The stall released the stale slot; the peer frame never claimed it.


def test_denied_frame_continuity_never_releases_and_new_epoch_drops_pending(
    monkeypatch: pytest.MonkeyPatch,
):
    """Gap-denied epochs stay fail-closed; only a fresh epoch re-arms motion.

    The drain-paced gate leans on the existing one-shot consumption contract:
    a release receipt inside a denied snapshot (base above retained frames)
    must not release, must not pace a re-request, and a new epoch drops the
    stale pending slot entirely.
    """

    wire = Wire()
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    now = [0.0]
    client = runtime.PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    client.perform_native(MoveTo(43, 37))
    wire.add(walk_ack((43, 37), (43, 37)))
    now[0] = 1.0
    monkeypatch.setattr(wire, "native_frame_snapshot", lambda: (1, 10, ()))
    with pytest.raises(NativeTelemetryUnavailable):
        client.drain_native_events()
    assert wire.moves == [(43, 37)]
    monkeypatch.undo()
    with pytest.raises(NativeTelemetryUnavailable):
        client.drain_native_events()
    assert wire.moves == [(43, 37)]
    wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
    wire.frames = []
    wire.add(entry(), map_frame())
    client.drain_native_events()
    client.perform_native(MoveTo(44, 37))
    assert wire.moves == [(43, 37), (43, 37)]


def test_events_are_once_per_native_receipt():

    wire = Wire()
    client = runtime.PlayingClient(wire)
    events = client.drain_native_events()
    assert len(events) == 1
    assert isinstance(events[0], MonsterSpotted)
    assert client.drain_native_events() == ()
    raw = bytearray(34)
    struct.pack_into("<HII", raw, 0, 0x08C8, 123, 999)
    struct.pack_into("<i", raw, 22, 5)
    wire.add(bytes(raw))
    assert client.drain_native_events() == (DamageTaken(5, 123),)


def test_cli_constructs_existing_host_with_real_providers(tmp_path, monkeypatch):

    (tmp_path / "db/pre-re").mkdir(parents=True)
    for relative in ("db/map_cache.dat", "db/pre-re/map_cache.dat"):
        body = zlib.compress(bytes(4))
        data = ENTRY.pack(b"prontera", 2, 2, len(body)) + body
        (tmp_path / relative).write_bytes(HEADER.pack(HEADER.size + len(data), 1) + data)
    (tmp_path / "db/pre-re/mob_db.yml").write_text("Body: []\n")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "accounts": [
                    {
                        "persona_id": "one",
                        "account": "dummy",
                        "password": "dummy",
                        "char_name": "WireNovice",
                    }
                ]
            }
        )
    )
    args = playing.parse_args(
        [
            "--manifest",
            str(manifest),
            "--runtime-root",
            str(tmp_path),
            "--memory-root",
            str(tmp_path / "memory"),
            "--decision-url",
            "http://127.0.0.1:8091/v1/systemone",
        ]
    )
    host = playing.build_host(args)
    try:
        assert set(host.agents) == {"one"}
        assert isinstance(host.chat, PlayingChat)
        assert isinstance(host._decision_factory(), PlayingDecision)
        assert host.client_factory is not None
        captured = {}

        def native(*args, **kwargs):
            captured.update(kwargs)
            return Wire()

        monkeypatch.setattr(agent_runtime, "_BotClient", native)
        client = host.client_factory(host.manifest["one"])
        assert isinstance(client, runtime.PlayingClient)
        assert captured["create_char"] is False
        monkeypatch.setattr(agent_runtime, "_BotClient", None)
        with pytest.raises(RuntimeError, match="refusing fake fallback"):
            host.client_factory(host.manifest["one"])
    finally:
        host.stop()


def test_health_survives_historical_dispatch_errors():
    """One unparseable frame must not starve telemetry forever (fx0, w43-48)."""
    wire = Wire()
    wire.dispatch_errors = [("0x09fd", "unexpected length")]
    client = runtime.PlayingClient(wire)
    client.perform_native(Attack(123))
    assert wire.sent, "a live reader with a parse-error history must keep acting"


@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("running", 1),
        ("connected_map", 1),
        ("sock", None),
        ("rx_thread", None),
        ("rx_error", "error"),
        ("selection_epoch", 0),
        ("selection_epoch", 2),
        ("map_epoch", None),
        ("map_epoch", 2),
        ("native_epoch", 0),
        ("gid", 78),
        ("selected_character_snapshot", None),
        ("class_fresh", 1),
    ],
)
def test_health_and_progression_deny_all_actions(attribute, value):
    wire = Wire()
    setattr(wire, attribute, value)
    client = runtime.PlayingClient(wire)
    with pytest.raises(NativeTelemetryUnavailable):
        client.perform_native(Attack(123))
    assert not wire.sent


def test_move_to_closes_open_npc_dialog_first():
    """fx0's trap: walks sent while an NPC deal is open are server-ignored."""
    wire = Wire()
    wire.frames = []
    dialog = struct.pack("<HI", 0x00B4, 1350503)  # fixture frames are pid-first
    wire.add(entry(), map_frame(), dialog)
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    client = runtime.PlayingClient(wire, cache=cache)
    client.perform_native(MoveTo(43, 37))
    assert wire.sent[0] == npc_close(1350503), "the close must precede the walk"
    # The close clears the tracker marker; the same dispatch may still be
    # npc-gated once, but the close itself is on the wire.
    assert wire.sent[0] == npc_close(1350503)
    client.perform_native(MoveTo(44, 37))
    assert wire.sent.count(npc_close(1350503)) == 1, "one close per open deal"


@pytest.mark.parametrize("kind", list(range(15)))
def test_only_type_five_is_combat_eligible(kind):
    wire = Wire()
    wire.frames = []
    wire.add(entry(), map_frame(), monster(kind))
    runtime.PlayingClient(wire).perform_native(Attack(123))
    assert bool(wire.sent) == (kind == 5)


@pytest.mark.parametrize("result", [0, 1, 2, 3, 4, 5, 6, 255])
def test_pickup_ack_not_send_defines_acquisition(result):
    wire = Wire()
    raw = bytearray(59)
    struct.pack_into("<HHHH", raw, 0, 0x0A37, 2, 3, 501)
    raw[24] = result
    wire.add(bytes(raw))
    client = runtime.PlayingClient(wire)
    state = client.build_native_state(Goal.GRIND)
    assert not state.inventory_known
    assert client._tracker is not None
    assert client._tracker.view.acquired_counts == (((501, 3),) if result == 0 else ())


@pytest.mark.parametrize("level", [0, -1, True, 1.5, None])
def test_invalid_level_never_reverts_to_persona(level):
    wire = Wire()
    wire.status_params[11] = level
    with pytest.raises(NativeTelemetryUnavailable):
        runtime.PlayingClient(wire).build_native_state(Goal.GRIND)


@pytest.mark.parametrize("kind", ["death", "warp", "authless", "resurrection"])
def test_life_authority_never_from_positive_hp(kind):
    wire = Wire()
    if kind == "authless":
        wire.frames = []
        wire.add(map_frame(), monster())
    else:
        wire.add(struct.pack("<HIB", 0x0080, 999, 1))
        if kind == "warp":
            wire.add(map_frame(), monster())
        if kind == "resurrection":
            wire.add(struct.pack("<HIH", 0x0148, 999, 0))
    client = runtime.PlayingClient(wire)
    state = client.build_native_state(Goal.GRIND)
    assert state.hp > 0
    assert state.alive is (
        True if kind == "resurrection" else None if kind == "authless" else False
    )
    client.perform_native(Attack(123))
    if kind == "resurrection":
        # Life is received, but a stand request is not a SELF pose receipt.
        assert wire.sent == ["stand"]
        standing = bytearray(34)
        struct.pack_into("<HI", standing, 0, 0x08C8, wire.aid)
        standing[29] = 3
        wire.add(bytes(standing))
        client.perform_native(Attack(123))
        assert wire.sent == ["stand", struct.pack("<HIB", 0x0437, 123, 0)]
    else:
        assert not wire.sent


@pytest.mark.parametrize(
    "args",
    [
        ["--duration", "0"],
        ["--duration", "nan"],
        ["--duration", "-1"],
        ["--playground"],
        ["--worldfeed-port", "0"],
        ["--worldfeed-port", "65536"],
    ],
)
def test_cli_rejects_invalid_lifecycle_options(args):
    with pytest.raises(SystemExit):
        playing.parse_args(
            [
                "--manifest",
                "dummy",
                "--runtime-root",
                "dummy",
                "--memory-root",
                "dummy",
                "--decision-url",
                "http://127.0.0.1:8091/v1/systemone",
                *args,
            ]
        )


@pytest.mark.parametrize("goal", list(Goal))
def test_mechanical_navigation_respects_goal(goal):
    wire = Wire()
    wire.frames = []
    wire.add(entry(), map_frame())
    cache = MapCache(
        (
            WalkMap("prontera", 400, 400, bytes(160000)),
            WalkMap("prt_fild08", 400, 400, bytes(160000)),
        )
    )
    client = runtime.PlayingClient(wire, cache=cache)
    state = client.build_native_state(goal)
    actions = client.mechanical_actions(state, ())
    assert bool(actions) == (goal in (Goal.GRIND, Goal.FARM_ITEM))


def test_public_catalog_does_not_expose_hidden_spawns(tmp_path):
    path = tmp_path / "mob.yml"
    path.write_text(
        "Body:\n - Id: 1002\n   Name: Poring\n   Level: 1\n   Boss: true\n"
        " - Id: 1003\n   Name: MVP\n   Level: 50\n   MvpExp: 1\n"
    )
    db = runtime.ObservedMobDatabase.load(path)
    assert not db.mobs_on_map("prontera")
    db.observe("prontera", (1002, 1002, 9999))
    assert [mob.name for mob in db.mobs_on_map("prontera")] == ["Poring"]
    poring = db.by_name("Poring")
    mvp = db.by_name("MVP")
    assert poring is not None
    assert mvp is not None
    assert not poring.is_mvp
    assert mvp.is_mvp
    assert db.by_name("absent") is None
    assert db.mobs_on_map("other") == ()


def test_bounded_cli_stops_on_exception():
    class Host:
        stopped = False

        def start_worldfeed(self):
            pass

        def step(self):
            message = "owned failure"
            raise RuntimeError(message)

        def stop(self):
            self.stopped = True

    host = Host()
    with pytest.raises(RuntimeError, match="owned failure"):
        playing.run_host(cast(AgentHost, host), 1)
    assert host.stopped


def test_operator_say_has_same_native_health_gate():
    wire = Wire()
    wire.running = False
    with pytest.raises(NativeTelemetryUnavailable):
        runtime.PlayingClient(wire).say("operator")
    assert not wire.sent


@pytest.mark.parametrize("playground", [False, True])
@pytest.mark.parametrize("solo", [False, True])
def test_roster_maps_literal_manifest_ids_with_real_clock(tmp_path, playground, solo):
    args = argparse.Namespace(
        seed=0, solo=solo, playground=playground, duration=120, schedule_file=None
    )
    entries = {pid: ManifestEntry(pid, "dummy", "dummy", pid) for pid in ("alice", "bob")}
    roster = playing.build_roster(entries, args)
    assert set(roster.personas) == set(entries)
    if playground:
        assert len(roster.online_personas(PersonaClock().local_now())) == 2
    assert roster.graph.friends_of("alice") == (() if solo else ("bob",))


def test_configured_schedule_is_used(tmp_path):
    path = tmp_path / "schedules.json"
    path.write_text(json.dumps({"alice": [[0, 1, 2]]}))
    args = argparse.Namespace(
        seed=0, solo=True, playground=False, duration=None, schedule_file=path
    )
    roster = playing.build_roster(
        {"alice": ManifestEntry("alice", "dummy", "dummy", "Alice")}, args
    )
    assert roster.groups[0].schedule.windows == ((0, 1, 2),)


def test_main_cleans_bounded_host(monkeypatch):
    host = SimpleNamespace(start_worldfeed=lambda: None, step=lambda: None, stop=lambda: None)
    monkeypatch.setattr(playing, "build_host", lambda _args: host)
    argv = [
        "--manifest",
        "dummy",
        "--runtime-root",
        "dummy",
        "--memory-root",
        "dummy",
        "--decision-url",
        "http://127.0.0.1:8091/v1/systemone",
        "--duration",
        "0.001",
    ]
    assert playing.main(argv) == 0


@pytest.mark.parametrize("action", [Say("hello"), Rest(), PartyChat("not in party")])
def test_social_native_limbs(action):
    wire = Wire()
    runtime.PlayingClient(wire).perform_native(action)
    assert wire.sent == (
        [] if isinstance(action, PartyChat) else ["sit"] if isinstance(action, Rest) else ["hello"]
    )


def test_default_native_client_is_not_legacy_perception(monkeypatch):
    monkeypatch.setattr(agent_runtime, "_BotClient", lambda *_args, **_kwargs: Wire())
    persona = SocietyPersona("one", "one", Playstyle.MELEE, Attitude.GRINDER, 0.5, (99, 99))
    agent = ScheduledAgent(
        persona, ManifestEntry("one", "dummy", "dummy", "WireNovice"), threaded=False
    )
    client = agent._new_client()
    assert isinstance(client, runtime.PlayingClient)


def test_distant_loot_walks_using_public_geometry():
    wire = Wire()
    wire.add(struct.pack("<HIHHBhhBBh", 0x0ADD, 321, 501, 0, 1, 48, 37, 0, 0, 3) + bytes(3))
    cache = MapCache((WalkMap("prontera", 100, 100, bytes(10000)),))
    client = runtime.PlayingClient(wire, cache=cache)
    client.perform_native(Loot())
    assert wire.moves == [(43, 37)]
    assert not wire.sent


def test_initial_model_social_goal_is_not_forced_to_grind():
    persona = SocietyPersona("one", "one", Playstyle.MELEE, Attitude.GRINDER, 0.5, (99, 99))
    wire = Wire()
    wire = cast(Any, wire)
    wire.connect = lambda: None
    wire.close = lambda: None
    model = ScriptedDecisionModel(answers={"change_goal": {"choice": "social"}})
    brain = EventDrivenBrain(model, StaticChatGenerator())
    agent = ScheduledAgent(
        persona,
        ManifestEntry("one", "dummy", "dummy", "WireNovice"),
        client=runtime.PlayingClient(wire),
        brain=brain,
        threaded=False,
    )
    try:
        assert agent.connect()
        assert agent.goal == Goal.SOCIAL
    finally:
        agent.disconnect()
