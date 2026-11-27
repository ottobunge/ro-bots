"""Replay proof: the leg-136 displacement rule over one synthetic contest window.

Mechanism 1 (the goal-travel pump's field-route legs re-aimed every 2 s pump
tick while an adjacent mob contests the slot), driven through the REAL
runtime twice over the same scenario: with the displacement authority
disabled (the leg-136 behavior) and with the shipped rule. The real drained
trace rows and receipt-style bucket deltas then run through the attribution
tool: ``pending_walk`` collapses, the executed-attack funnel recovers, and
``walk_displaced_for_combat`` names each released hold class.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from robots.adapters.native_gameplay import attack
from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app.pendingwalk_attribution import summarize_pendingwalk
from robots.app.playing_runtime import PlayingClient
from robots.app.scripts import _melee_action
from robots.domain.actions import Attack, MoveTo
from robots.domain.farm import FarmPlan, MobInfo
from robots.domain.model import Goal
from tests.test_playing_runtime import Wire, entry_at, map_frame_at, monster, walk_ack

T0 = datetime(2026, 11, 28, 5, 0, tzinfo=UTC)
PERSONA = "pop_replay"
TICKS = (2.1, 4.1, 6.1)
BUCKETS = (2.0, 4.0, 7.0)
_ORIGINAL_DISPLACE = PlayingClient._displace_pending_for_combat


def iso(seconds: float) -> str:
    return (T0 + timedelta(seconds=seconds)).isoformat()


def _drive(monkeypatch, *, displace: bool) -> tuple[PlayingClient, Wire, list[dict]]:
    """One synthetic contest window through the real runtime."""
    # the leg-136 A/B: with the authority disabled combat authorship never
    # releases the slot; with it, the shipped rule applies
    monkeypatch.setattr(
        PlayingClient,
        "_displace_pending_for_combat",
        (lambda _self: None) if not displace else _ORIGINAL_DISPLACE,
    )
    now = [0.0]
    wire = Wire()
    wire.frames = []
    wire.add(entry_at(42, 37), map_frame_at(42, 37), monster(at=(43, 37)))
    client = PlayingClient(
        wire,
        cache=MapCache(
            tuple(WalkMap(name, 100, 100, bytes(10000)) for name in ("prontera", "prt_fild08"))
        ),
        monotonic=lambda: now[0],
    )
    rows: list[dict] = []

    def collect(t: float) -> None:
        rows.extend(
            {"t": iso(t), "persona": PERSONA, "kind": "swing_observation", **drained}
            for drained in client.drain_swing_telemetry()
        )

    state = client.build_native_state(Goal.GRIND)
    client.mob_db.catalog[1002] = MobInfo(1002, "Poring", 1)
    client.authorize_farm_sightings(
        state, FarmPlan(1, state.map_name, ("Poring",), 900, 1), remaining_s=900
    )
    # the goal-travel pump: re-aims its field-route leg every 2 s tick
    # (-2 arms the first tick at t=0)
    client._field_pump_at = -2.0
    client._field_intent = SimpleNamespace(plan=SimpleNamespace(map_name="prontera"))  # type: ignore[assignment]
    client.field_travel_actions = lambda _state: (MoveTo(41, 37),)  # type: ignore[method-assign,assignment]

    def field_tick(t: float) -> None:
        now[0] = t
        client._pump_field_travel()
        collect(t)

    field_tick(0.0)  # the field-route leg takes the slot
    now[0] = 0.1
    client.drain_native_events()  # the sighting contests the held slot
    collect(0.1)
    wire.add(walk_ack((42, 37), (42, 37)))  # the field step lands: standing truth
    for t in TICKS:
        field_tick(t)  # re-aims into the slot (mechanism 1)
        state = client.build_native_state(Goal.GRIND)
        swing = _melee(state)
        client.authorize_farm_actions(state, (swing,))  # the authored attack
        client.perform_native(swing)
        if wire.sent and wire.sent[-1] == attack(123):
            rows.append(
                {
                    "t": iso(t),
                    "persona": PERSONA,
                    "kind": "action_executed",
                    "action": "Attack",
                    "params": {"target_id": 123},
                    "map": "prontera",
                    "x": 42,
                    "y": 37,
                }
            )
        collect(t)
    return client, wire, rows


def _melee(state) -> Attack:
    action = _melee_action(state.nearby_monsters[0], state)
    assert isinstance(action, Attack)
    return action


def _bucket_cells(client: PlayingClient, reasons: str, event: str) -> dict[float, dict[str, int]]:
    """Per-bucket delta counts from the client's gate/displacement deques."""
    entries = sorted(getattr(client, reasons, ()))
    cells: dict[float, dict[str, int]] = {bound: {} for bound in BUCKETS}
    for at, reason in entries:
        bound = next((b for b in BUCKETS if at <= b), None)
        if bound is None:
            continue
        bucket = cells[bound]
        bucket[reason] = bucket.get(reason, 0) + 1
    return cells


def _samples(client: PlayingClient, persona: str) -> list[dict]:
    gates = _bucket_cells(client, "_attack_gate_reasons", "attack_gates")
    displaced = _bucket_cells(client, "_walk_displacement_reasons", "walk_displaced")
    return [
        {
            "t": bound,
            persona: {
                "attack_gates": gates[bound] or None,
                "walk_displaced_for_combat": displaced[bound] or None,
            },
        }
        for bound in BUCKETS
    ]


def test_replay_pending_walk_collapses_and_the_counters_name_each_class(monkeypatch) -> None:
    pre_client, pre_wire, pre_rows = _drive(monkeypatch, displace=False)
    post_client, post_wire, post_rows = _drive(monkeypatch, displace=True)

    # the funnel: none land before the rule; under it the 0.1 mint converts
    # immediately (adjacent mob, standing truth, slot freed) and every
    # contest-tick authored attack lands
    assert len(pre_wire.sent) == 0
    assert len(post_wire.sent) == 1 + len(TICKS)

    pre = summarize_pendingwalk(pre_rows, _samples(pre_client, PERSONA), iso(0), iso(7.0))
    post = summarize_pendingwalk(post_rows, _samples(post_client, PERSONA), iso(0), iso(7.0))

    assert pre["totals"]["pending_walk"] == 3
    assert post["totals"]["pending_walk"] == 0
    assert post["totals"]["pending_walk"] < pre["totals"]["pending_walk"]

    # the new census counter names each displaced hold class
    assert pre["totals"].get("displacements", {}) == {}
    assert post["totals"]["displacements"] == {"field_route": 4}
    agent = post["agents"][PERSONA]
    assert agent["displacements"] == {"field_route": 4}
    assert agent["receipt_displacements"] == {"field_route": 4}

    # conservation: every pre-fix gate attributes to the field-route hold
    assert sum(pre["totals"]["origins"].values()) == pre["totals"]["pending_walk"]
    assert pre["totals"]["origins"]["attack_deferred_behind_field_route"] == 3
