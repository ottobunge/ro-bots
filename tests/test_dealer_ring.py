"""LEG-89: received-cell allocation and the real host C4 -> C5 path."""

import struct
from dataclasses import replace

import pytest

from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app import scripts
from robots.app.agent_runtime import ManifestEntry, ScheduledAgent
from robots.app.playing_runtime import NPC_RETRY_BUDGET, PlayingClient
from robots.domain.actions import (
    GameAction,
    MoveTo,
    NpcClose,
    NpcShopSell,
    NpcShopSellOpen,
    TalkToNpc,
)
from robots.domain.model import ActorRef, BotState, Goal
from robots.society.models import Attitude, Playstyle, SocietyPersona
from tests.test_dealer_walkability import NEIGHBOURS
from tests.test_merchant_drive import _plan
from tests.test_playing_runtime import entry_at
from tests.test_sell_drive_rearm import _answers, _s00_brain
from tests.test_shop_sell_loop import DEALER, RecordingWire, _c4, _c7, _cb, _dealer, _inv, _weight


@pytest.fixture(autouse=True)
def _fresh_contacts():
    scripts.reset_merchant_talk()
    yield
    scripts.reset_merchant_talk()


def _client(
    name: str = "seller",
    at: tuple[int, int] = (170, 128),
    blocked: tuple[tuple[int, int], ...] = (),
    aid: int = 999,
) -> tuple[PlayingClient, list[float]]:
    wire = RecordingWire()
    wire.char_name = name
    wire.aid = aid
    wire.map_name = "prt_in"
    wire.add(
        entry_at(*at),
        struct.pack("<H16sHH", 0x91, b"prt_in", *at),
        _dealer((172, 130)),
        _inv(((6, 909, 1), (7, 1201, 1))),
        _weight(),
    )
    tiles = bytearray(200 * 200)
    for x, y in (*blocked, (172, 130)):
        tiles[x + y * 200] = 1
    now = [100.0]
    client = PlayingClient(
        wire,
        cache=MapCache((WalkMap("prt_in", 200, 200, bytes(tiles)),)),
        monotonic=lambda: now[0],
    )
    client.build_native_state(Goal.GRIND)
    client._npc_names[DEALER] = "Weapon Dealer#prt"
    return client, now


def _step(client: PlayingClient, state: BotState) -> tuple[GameAction, ...]:
    client._last_built_state = state
    outcome = scripts._merchant_step(
        state, reachable=client.merchant_reachable, travel_target=client.merchant_travel_target
    )
    assert outcome is not None
    return outcome.actions


@pytest.mark.parametrize("native_body", [False, True])
def test_two_received_sellers_allocate_distinct_walkable_ring_cells(native_body):
    targets = []
    for name, other, at, peer_at in (
        ("a", "b", (169, 128), (170, 128)),
        ("b", "a", (170, 128), (169, 128)),
    ):
        own_id, peer_id = (100, 200) if name == "a" else (200, 100)
        client, _ = _client(name, at, blocked=((171, 129),), aid=own_id)
        if native_body:
            body = bytearray(_dealer(peer_at, npc_id=peer_id))
            body[4] = 0
            client.wire.add(bytes(body))
        state = client.build_native_state(Goal.GRIND)
        peer = ActorRef(id=99, name=other, kind="player", distance=1, x=peer_at[0], y=peer_at[1])
        if not native_body:
            state = replace(state, nearby=(*state.nearby, peer))
        else:
            assert peer_at in state.occupied_cells
        (move,) = _step(client, state)
        assert isinstance(move, MoveTo)
        target = (move.x, move.y)
        assert target in NEIGHBOURS
        assert target != (171, 129)
        targets.append(target)
    assert targets[0] != targets[1]


def test_runtime_selection_keeps_own_received_cell_despite_other_ring_vacancies():
    client, _ = _client(at=(173, 129))
    state = client.build_native_state(Goal.GRIND)
    client._last_built_state = replace(state, occupied_cells=((171, 129),))
    assert client.merchant_travel_target("prt_in", (173, 129), (172, 130)) == (173, 129)
    client._last_built_state = state
    assert client.merchant_travel_target("prt_in", (173, 129), (172, 130)) == (173, 129)


def test_an_overlapping_received_body_requires_own_allocation_before_first_talk():
    client, _ = _client(at=(173, 129))
    body = bytearray(_dealer((173, 129), npc_id=99))
    body[4] = 0
    client.wire.add(bytes(body))
    state = client.build_native_state(Goal.GRIND)
    assert (173, 129) in state.occupied_cells
    (move,) = _step(client, state)
    assert isinstance(move, MoveTo)
    assert (move.x, move.y) in NEIGHBOURS
    assert (move.x, move.y) != (173, 129)


def test_overlapping_sellers_use_received_actor_ids_to_choose_distinct_recovery_cells():
    targets = []
    for own_id, peer_id in ((100, 200), (200, 100)):
        client, _ = _client(at=(173, 129), aid=own_id)
        body = bytearray(_dealer((173, 129), npc_id=peer_id))
        body[4] = 0
        client.wire.add(bytes(body))
        (move,) = _step(client, client.build_native_state(Goal.GRIND))
        assert isinstance(move, MoveTo)
        targets.append((move.x, move.y))
    assert targets[0] != targets[1]


def test_saturation_names_outward_hold_and_vacancy_is_handed_to_next_seller(caplog):
    client, _ = _client()
    state = replace(client.build_native_state(Goal.GRIND), occupied_cells=NEIGHBOURS)
    for _ in range(6):
        actions = _step(client, state)
        assert not any(isinstance(a, TalkToNpc) for a in actions)
        for action in actions:
            assert isinstance(action, MoveTo)
            assert max(abs(action.x - 172), abs(action.y - 130)) >= 2
    taps = [r.getMessage() for r in caplog.records if "dealer_ring_saturated" in r.getMessage()]
    assert len(taps) == 1
    assert "free=0/8" in taps[0]
    assert "preferred_chebyshev<=1=unavailable" in taps[0]
    freed = replace(state, occupied_cells=tuple(p for p in NEIGHBOURS if p != (171, 129)))
    assert _step(client, freed) == (MoveTo(171, 129),)


def test_received_owner_keeps_its_cell_until_vacate_then_waiter_takes_it():
    client, _ = _client(at=(173, 129))
    state = client.build_native_state(Goal.GRIND)
    assert _step(client, state) == (TalkToNpc(DEALER),)
    for _ in range(10):
        assert _step(client, state) == ()
    waiter, _ = _client("waiter", blocked=tuple(p for p in NEIGHBOURS if p != (173, 129)))
    waiting = replace(waiter.build_native_state(Goal.GRIND), occupied_cells=((173, 129),))
    assert not any(isinstance(a, TalkToNpc) for a in _step(waiter, waiting))
    assert _step(waiter, replace(waiting, occupied_cells=())) == (MoveTo(173, 129),)


def _host(client: PlayingClient, monkeypatch: pytest.MonkeyPatch) -> ScheduledAgent:
    brain = _s00_brain()
    brain._merchant_reachable = client.merchant_reachable
    brain._merchant_travel_target = client.merchant_travel_target
    state = client.build_native_state(Goal.GRIND)
    brain.sync_context(state)
    monkeypatch.setattr(brain, "_setup_farm_plan", lambda *_args: _plan())
    brain._run_review(state, _answers("grind"), [])
    assert brain.current_plan is not None
    persona = SocietyPersona("one", "one", Playstyle.MELEE, Attitude.GRINDER, 0.5, (1, 1))
    return ScheduledAgent(
        persona,
        ManifestEntry("one", "dummy", "dummy", client.wire.char_name),
        brain=brain,
        client=client,
        threaded=False,
    )


def test_authored_farm_plan_opens_first_c4_on_next_tick_and_sells_without_close(monkeypatch):
    client, now = _client(at=(173, 129))
    host = _host(client, monkeypatch)
    state = client.build_native_state(Goal.GRIND)
    # The runtime owns the approach even when a plan is retained.
    assert client.merchant_travel_target("prt_in", (173, 129), (172, 130)) == (173, 129)
    host._advance_script(state)
    assert host.brain is not None
    assert host.brain.current_plan is not None
    assert client.wire.sent == [struct.pack("<HIB", 0x90, DEALER, 1)]
    client.wire.add(_c4(DEALER))
    now[0] += 2
    state = client.build_native_state(Goal.GRIND)
    host._advance_script(state)
    assert client.wire.sent[-1] == struct.pack("<HIB", 0xC5, DEALER, 1)
    assert client._npc.view is not None
    assert state.npc_dialogue is not None
    assert client._npc.view.opened_sequence == state.npc_dialogue.opened_sequence
    for _ in range(3):
        host._advance_script(client.build_native_state(Goal.GRIND))
    assert len(client.wire.sent) == 2
    # Opening grants neither a sale nor a purchase without received rows.
    assert client.npc_shop_purchase(maximum_zeny=100) is None
    client.wire.add(_c7(((6, 12, 12),)))
    host._advance_script(client.build_native_state(Goal.GRIND))
    assert client.wire.sent[-1] == struct.pack("<HHHH", 0xC9, 8, 6, 1)
    client.wire.add(struct.pack("<HHH", 0xAF, 6, 1), _weight(), _cb(0))
    state = client.build_native_state(Goal.GRIND)
    assert state.npc_dialogue is None
    assert not any(f[:2] == b"\x46\x01" for f in client.wire.sent)
    assert sum(f[:2] == b"\x90\x00" for f in client.wire.sent) == 1


def test_missing_c7_still_exhausts_real_attempts_and_holds_for_retry_epoch(monkeypatch):
    client, now = _client(at=(173, 129))
    host = _host(client, monkeypatch)
    host._advance_script(client.build_native_state(Goal.GRIND))
    for attempt in range(NPC_RETRY_BUDGET + 1):
        client.wire.add(_c4(DEALER))
        host._advance_script(client.build_native_state(Goal.GRIND))
        assert client.wire.sent[-1] == struct.pack("<HIB", 0xC5, DEALER, 1)
        now[0] += 30
        state = client.build_native_state(Goal.GRIND)
        # Exercise the same timeout close + shared retry token as the host.
        client.perform_native(NpcClose(DEALER))
        client._rearm_closed_merchant(state)
        host._advance_script(client.build_native_state(Goal.GRIND))
        assert client._npc_retries == max(0, NPC_RETRY_BUDGET - attempt - 1)
    sent = tuple(client.wire.sent)
    for _ in range(20):
        host._advance_script(client.build_native_state(Goal.GRIND))
    assert tuple(client.wire.sent) == sent
    assert sum(f[:2] == b"\xc5\x00" for f in sent) == NPC_RETRY_BUDGET + 1
    assert not any(f[:2] == b"\xc9\x00" for f in sent)


@pytest.mark.parametrize("action_type", [NpcShopSellOpen, NpcShopSell])
def test_plan_does_not_authorize_unreceived_shop_actions(action_type, monkeypatch):
    client, _ = _client(at=(173, 129))
    host = _host(client, monkeypatch)
    state = client.build_native_state(Goal.GRIND)
    actions = host._script_actions(state, ())
    assert not any(isinstance(a, action_type) for a in actions)
    assert actions == ()
    assert client.wire.sent == []
