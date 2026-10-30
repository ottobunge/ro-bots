"""Criterion-9 stat setup: production observation + CZ_STATUS_CHANGE dispatch.

Wire contracts (source-verified in the pinned rathena submodule and pinned by
the stat-allocation lane's twin): 0x00BB send is ``<HHB`` (pid, stat id,
amount 1); 0x00BC ack is ``<HHBB`` (pid, stat, ok, value — failures carry 0);
0x00BD session table is ``<HH12B14h`` (points u16 @2, stat values B
@4,6,8,10,12,14, costs B, derived padding). 0x00B0 param 9 = status points
(signed; negative = retained, never spend-ready), param 11 = base level,
params 13-18 = STR..LUK.
"""

from __future__ import annotations

import struct

from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import Attack
from robots.domain.model import Goal
from tests.test_native_gameplay_equip import auth
from tests.test_playing_runtime import Wire

STR, DEX = 13, 17


def status_table(points: int, stats: dict[int, int]) -> bytes:
    body: list[int] = [points]
    for stat in (STR, 14, 15, 16, DEX, 18):
        body += [stats.get(stat, 1), 2]
    body += [0] * 14
    return struct.pack("<HH12B14h", 0x00BD, *body)


def b0(param: int, value: int) -> bytes:
    return struct.pack("<HHi", 0x00B0, param, value)


def stat_ack(stat: int, value: int, *, ok: bool = True) -> bytes:
    return struct.pack("<HHBB", 0x00BC, stat, 1 if ok else 0, value)


def stat_sends(wire: Wire) -> list[bytes]:
    return [s for s in wire.sent if isinstance(s, bytes) and s[:2] == b"\xbb\x00"]


def test_session_table_seeds_points_and_stats() -> None:
    client = PlayingClient(Wire())
    wire = client.wire
    wire.add(auth(), status_table(32, {STR: 1, DEX: 3}), b0(11, 4))
    client.perform_native(Attack(123))
    tracker = client._tracker
    assert tracker is not None
    view = tracker.view
    assert view.status_points == 32
    assert view.base_level == 4
    assert view.stats == (1, 1, 1, 1, 3, 1)  # STR AGI VIT INT DEX LUK


def test_param_nine_points_retained_signed() -> None:
    client = PlayingClient(Wire())
    wire = client.wire
    wire.add(auth(), b0(9, -3))
    client.perform_native(Attack(123))
    tracker = client._tracker
    assert tracker is not None
    assert tracker.view.status_points == -3
    wire.add(b0(9, 12))
    client.perform_native(Attack(123))
    assert tracker.view.status_points == 12


def test_ack_ok_advances_stat_failure_does_not() -> None:
    client = PlayingClient(Wire())
    wire = client.wire
    wire.add(auth(), status_table(32, {STR: 1}), stat_ack(STR, 2))
    client.perform_native(Attack(123))
    tracker = client._tracker
    assert tracker is not None
    view = tracker.view
    stats = view.stats
    assert stats is not None
    assert stats[0] == 2
    assert len(view.stat_acks) == 1
    wire.add(stat_ack(DEX, 0, ok=False))
    stats_after = tracker.view.stats
    assert stats_after is not None
    assert stats_after[4] == 1  # failure acks never advance


def test_runtime_spends_stat_points_in_sidecar_order() -> None:
    client = PlayingClient(Wire())
    wire = client.wire
    wire.add(auth(), status_table(48, {STR: 1, DEX: 1}), b0(11, 2), b0(9, 48))

    client.perform_native(Attack(123))

    sends = stat_sends(wire)
    assert len(sends) == 8, "first batch: STR 1->9 = 8 one-point spends"
    for raw in sends:
        assert struct.unpack("<HHB", raw) == (0x00BB, STR, 1)

    # The batch paces on acks: the server acks all eight, the next dispatch
    # continues with the next sidecar leg (DEX 1->9).
    wire.add(*[stat_ack(STR, value) for value in range(2, 10)])
    client.perform_native(Attack(123))
    dex_sends = stat_sends(wire)[8:]
    assert len(dex_sends) == 8
    for raw in dex_sends:
        assert struct.unpack("<HHB", raw) == (0x00BB, DEX, 1)

    # Points exhausted: the setup stays quiet.
    wire.add(b0(9, 0))
    wire.add(*[stat_ack(DEX, value) for value in range(2, 10)])
    client.perform_native(Attack(123))
    assert len(stat_sends(wire)) == 16


def test_runtime_failure_ack_stops_spending_that_stat() -> None:
    client = PlayingClient(Wire())
    wire = client.wire
    wire.add(auth(), status_table(48, {STR: 1}), b0(9, 8), stat_ack(STR, 0, ok=False))

    client.perform_native(Attack(123))

    str_sends = [s for s in stat_sends(wire) if struct.unpack("<HHB", s)[1] == STR]
    assert str_sends == [], "a failed stat must not be re-spent this epoch"


def test_runtime_without_point_observation_sends_nothing() -> None:
    client = PlayingClient(Wire())
    client.perform_native(Attack(123))
    assert stat_sends(client.wire) == []


def test_sp_zeny_param_twenty_seeds_the_view_balance() -> None:
    """The login zeny arrives as 0x00B0 parameter 20 (SP_ZENY; the pinned
    rathena enum src/map/map.hpp:501 places SP_ZENY at 20 in _sp). Leg 43:
    no handler existed, state.zeny stayed None the whole window, and the
    merchant drive's affordable gate (zeny >= 50) could never arm."""
    client = PlayingClient(Wire())
    wire = client.wire
    wire.add(auth(), b0(20, 60))
    client.perform_native(Attack(123))
    tracker = client._tracker
    assert tracker is not None
    assert tracker.view.zeny == 60


def test_build_native_state_prefers_the_tracked_zeny() -> None:
    """The tracked login zeny is the balance authority; the shop-context
    balance stays the fallback for wires that never delivered param 20."""
    client = PlayingClient(Wire())
    client.wire.add(auth(), b0(20, 60))
    client.perform_native(Attack(123))
    state = client.build_native_state(Goal.GRIND)
    assert state.zeny == 60
