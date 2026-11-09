"""Leg 80 prep: travel authors wait; each perform names its actual result."""

import struct
from dataclasses import replace

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap, shortest_path
from robots.app import scripts
from robots.app.playing_runtime import PlayingClient
from robots.app.trace_log import TraceLog
from robots.domain.actions import MoveTo, Say
from robots.domain.model import Goal
from tests.test_merchant_travel_walkability import SAFE_DEST, _seller, _step
from tests.test_native_navigation import SOURCE
from tests.test_playing_runtime import Wire, entry_at, monster, walk_ack
from tests.test_trace_log import make_agent, read_lines


@pytest.fixture(autouse=True)
def _reset():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


@pytest.fixture(scope="module")
def public_cache():
    return MapCache.load(SOURCE / "db/map_cache.dat", SOURCE / "db/pre-re/map_cache.dat")


@pytest.mark.parametrize(
    ("map_name", "returning"),
    [(name, False) for name in scripts.MERCHANT_ROUTE if name != "prt_in"]
    + [(name, True) for name in scripts.MERCHANT_ROUTE_RETURN],
)
def test_travel_reaffirms_only_every_fifth_elapsed_evaluation(map_name, returning):
    state = _seller(
        map_name=map_name, merchant_returning=returning, inventory={} if returning else {"915": 2}
    )
    cell = (scripts.MERCHANT_ROUTE_RETURN if returning else scripts.MERCHANT_ROUTE)[map_name]
    for tick in range(16):
        outcome = scripts._merchant_step(state)
        assert outcome is not None
        assert outcome.actions == ((MoveTo(*cell),) if tick % 5 == 0 else ())


@pytest.mark.parametrize("change", ["map", "epoch", "destination", "hold", "reset", "inactive"])
def test_changed_travel_context_authors_immediately(change):
    state = _seller()
    assert scripts._merchant_travel_step(state, SAFE_DEST, None).actions
    assert scripts._merchant_travel_step(state, SAFE_DEST, None).actions == ()
    cell = SAFE_DEST
    if change == "map":
        state = replace(state, map_name="prontera")
    elif change == "epoch":
        state = replace(state, native_epoch=1)
    elif change == "destination":
        cell = (168, 377)
    elif change == "hold":
        assert scripts._merchant_travel_step(state, cell, lambda *_: None).actions == ()
    elif change == "inactive":
        assert scripts._merchant_step(replace(state, inventory={})) is None
    else:
        scripts.reset_merchant_talk()
    assert scripts._merchant_travel_step(state, cell, None).actions == (MoveTo(*cell),)


def _field_client(
    cache, start, name="travel_seller", *, bard=False
) -> tuple[PlayingClient, list[float]]:
    wire = Wire()
    wire.frames = []
    wire.map_name = "prt_fild08"
    wire.char_name = name
    wire.add(entry_at(*start), struct.pack("<H16sHH", 0x0091, b"prt_fild08", *start))
    if bard:
        wire.add(monster(kind=6, aid=110005545, at=(175, 374)))
    now = [0.0]
    client = PlayingClient(wire, cache=cache, monotonic=lambda: now[0])
    return client, now


@pytest.mark.parametrize(
    ("name", "start"),
    [("xXLunasongXx", (176, 374)), ("RinceNyan", (180, 350)), ("s00", (174, 355))],
)
def test_three_sellers_release_a_lost_walk_then_progress(public_cache, name, start):
    path = shortest_path(public_cache.get("prt_fild08"), start, SAFE_DEST)
    assert path[0] == start
    assert path[-1] == SAFE_DEST
    if start == (176, 374):
        assert path[1] == (175, 374)  # pinned Bard: occupied one-cell-west rejection
        path = shortest_path(
            public_cache.get("prt_fild08"), start, SAFE_DEST, blocked_visible=((175, 374),)
        )
    client, now = _field_client(public_cache, start, name, bard=True)
    state = _seller(name=name, x=start[0], y=start[1])
    assert client.merchant_reachable(state.map_name, start, SAFE_DEST) is True
    client.perform_native(_step(client, state).actions[0])
    assert client.wire.moves == [path[1]]
    assert client.last_move_outcome["reason"] == (
        "occupied_west_rerouted" if start == (176, 374) else "step"
    )
    # No walkok arrives for the first dispatch. Holding the author must not
    # leave that pending walk latched forever, even without an arrival frame.
    for tick in range(1, 5):
        now[0] = tick * 2.0
        assert _step(client, state).actions == ()
        client.drain_native_events()
    assert client._pending is None
    now[0] = 10.0
    client.perform_native(_step(client, state).actions[0])
    assert client.wire.moves == [path[1], path[1]]
    assert client.last_move_outcome["outcome"] == "dispatched"
    assert client.last_move_outcome["pending_outcome"] == "pending-cancelled"
    assert client.last_move_outcome["pending_reason"] == "no_progress(step)"
    # The retry's received walkok advances the SAME client grid position.
    client.wire.add(walk_ack(start, path[1]))
    received = client.build_native_state(Goal.GRIND)
    assert (received.x, received.y) == path[1] != start
    # Progress without a zero-length walk-end still expires on the stall clock.
    now[0] = 12.0
    client.perform_native(MoveTo(*SAFE_DEST))
    assert dict(client.last_move_outcome)["outcome"] == "pending"
    now[0] = 14.0
    client.perform_native(MoveTo(*SAFE_DEST))
    assert client.wire.moves[-1] == path[2]


def _pose(wire, kind) -> None:
    raw = bytearray(34)
    struct.pack_into("<HI", raw, 0, 0x08C8, wire.aid)
    raw[29] = kind
    wire.add(bytes(raw))


def test_trace_names_standing_pending_dispatch_refusal_and_stall(tmp_path, public_cache):
    trace = TraceLog(tmp_path, "p")
    agent, _, _ = make_agent(trace, tmp_path)
    client, now = _field_client(public_cache, (176, 374))
    agent.client = client
    _pose(client.wire, 2)
    agent.execute_actions((MoveTo(*SAFE_DEST),))
    assert client.wire.moves == []  # fail closed until received self standing
    _pose(client.wire, 3)
    agent.execute_actions((MoveTo(*SAFE_DEST), MoveTo(*SAFE_DEST)))
    now[0] = 2.0
    agent.execute_actions((MoveTo(*SAFE_DEST),))
    client.cache = None
    now[0] = 4.0
    agent.execute_actions((MoveTo(*SAFE_DEST), Say("hi")))
    trace.close()
    rows = read_lines(tmp_path, "p")
    performs = [row for row in rows if row["kind"] == "move_performed"]
    assert [row["outcome"] for row in performs] == [
        "standing-blocked",
        "dispatched",
        "pending",
        "dispatched",
        "refused",
    ]
    assert [row["reason"] for row in performs] == [
        "not_standing",
        "step",
        "await_pending",
        "step",
        "no_map_cache",
    ]
    assert performs[3]["pending_outcome"] == "pending-cancelled"
    assert performs[3]["pending_reason"] == "no_progress(step)"
    assert performs[1]["wire_target"] == list(client.wire.moves[0])
    for row in performs:
        assert row["params"] == {"x": 169, "y": 377}
        assert (row["map"], row["x"], row["y"]) == ("prt_fild08", 176, 374)
    for index, row in enumerate(rows):
        if row["kind"] == "move_performed":
            assert rows[index - 1]["kind"] == "action_executed"
            assert rows[index - 1]["action"] == "MoveTo"


@pytest.mark.parametrize("intercept", ["npc", "error"])
def test_move_trace_never_reuses_a_previous_dispatch(
    tmp_path, public_cache, monkeypatch, intercept
):
    trace = TraceLog(tmp_path, "p")
    agent, _, _ = make_agent(trace, tmp_path)
    client, now = _field_client(public_cache, (176, 374))
    agent.client = client
    agent.execute_actions((MoveTo(*SAFE_DEST),))
    if intercept == "npc":
        monkeypatch.setattr(client, "_retry_blocked_dialogue", lambda: True)
    else:

        def broken_move(*_args):
            message = "synthetic send failure"
            raise OSError(message)

        monkeypatch.setattr(client.wire, "move", broken_move)
    now[0] = 2.0
    agent.execute_actions((MoveTo(*SAFE_DEST),))
    trace.close()
    performs = [row for row in read_lines(tmp_path, "p") if row["kind"] == "move_performed"]
    assert performs[0]["outcome"] == "dispatched"
    assert performs[1]["outcome"] == "refused"
    assert performs[1]["reason"] == ("npc_intercepted" if intercept == "npc" else "perform_error")
    assert "wire_target" not in performs[1]


def test_move_trace_reads_cached_state_without_observing(tmp_path, public_cache, monkeypatch):
    trace = TraceLog(tmp_path, "p")
    agent, _, _ = make_agent(trace, tmp_path)
    client, _ = _field_client(public_cache, (176, 374))
    agent.client = client
    calls = []
    build = client.build_native_state

    def counted_build(goal):
        calls.append(goal)
        return build(goal)

    monkeypatch.setattr(client, "build_native_state", counted_build)
    agent.execute_actions((MoveTo(*SAFE_DEST),))
    trace.close()
    assert calls == [Goal.GRIND]  # only perform observes; neither trace row does
    assert read_lines(tmp_path, "p")[-1]["outcome"] == "dispatched"


def test_occupied_west_refusal_never_falls_back_to_a_blind_direct_send():
    tiles = bytearray([1]) * (400 * 400)
    for x in (174, 175, 176):
        tiles[x + 374 * 400] = 0
    cache = MapCache((WalkMap("prt_fild08", 400, 400, bytes(tiles)),))
    client, now = _field_client(cache, (176, 374), bard=True)
    for tick in range(3):
        now[0] = tick * 2.0
        client.perform_native(MoveTo(174, 374))
        assert client.last_move_outcome["outcome"] == "refused"
        assert client.last_move_outcome["reason"] == "occupied_west_no_route"
    assert client.wire.moves == []
    assert client._no_route_attempts == 0


def test_received_npc_vanish_releases_the_occupied_west_detour(public_cache):
    client, now = _field_client(public_cache, (176, 374), bard=True)
    client.perform_native(MoveTo(*SAFE_DEST))
    assert client.wire.moves[-1] != (175, 374)
    assert client.last_move_outcome["reason"] == "occupied_west_rerouted"
    client.wire.add(struct.pack("<HIB", 0x0080, 110005545, 0))
    now[0] = 2.0
    client.perform_native(MoveTo(*SAFE_DEST))
    assert client.wire.moves[-1] == (175, 374)
    assert dict(client.last_move_outcome)["reason"] == "step"
    assert public_cache.get("prt_fild08").walkable((175, 374)) is True
