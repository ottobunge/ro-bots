"""Replay proof: the swing lease (leg-137) over one synthetic contest window.

The leg-137 churn engine, driven through the REAL runtime twice over the same
scenario: with the leg-137 shipped shape (displacement without the lease, the
field pump revoking the live intent every beat) and with the shipped fix (the
displacement leases the slot until the swing; the field pump only mints).
The real drained trace rows and receipt-style bucket deltas then run through
the attribution tool: pending_walk refusals collapse, the displacement churn
collapses, the re-authors back off behind named taps, the swing converts, and
every gate stays attributed.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from robots.adapters.native_gameplay import attack
from robots.adapters.native_navigation import MapCache, WalkMap
from robots.app.pendingwalk_attribution import summarize_pendingwalk
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import Attack, MoveTo
from robots.domain.farm import FarmPlan, MobInfo
from robots.domain.model import Goal
from tests.test_playing_runtime import Wire, entry_at, map_frame_at, monster, walk_ack

T0 = datetime(2026, 11, 28, 5, 0, tzinfo=UTC)
PERSONA = "pop_lease_replay"
TICKS = (2.1, 4.1, 6.1)
BUCKETS = (2.0, 4.0, 7.0)
_ORIGIN_AUTHORIZE = PlayingClient.authorize_farm_actions
_ORIGIN_LEASE = PlayingClient._lease
_ORIGIN_LEASE_REFUSAL = PlayingClient._swing_lease_refusal


def iso(seconds: float) -> str:
    return (T0 + timedelta(seconds=seconds)).isoformat()


class _InertLease:
    """The leg-137 shipped shape: the displacement arms nothing that enforces."""

    def arm(self, *args: object) -> None:
        pass

    def bind(self, *args: object) -> None:
        pass

    def release(self) -> None:
        pass

    def origin(self) -> str | None:
        return None

    def expiry(self, **kwargs: object) -> str | None:
        return None


def _world() -> tuple[Wire, PlayingClient, list[float]]:
    """The agent at (42, 37), an adjacent Poring, and a hand-driven clock."""
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
    return wire, client, now


def _drive(monkeypatch, *, lease: bool) -> tuple[PlayingClient, Wire, list[dict]]:
    """One synthetic contest window through the real runtime."""
    if lease:
        monkeypatch.setattr(PlayingClient, "authorize_farm_actions", _ORIGIN_AUTHORIZE)
        monkeypatch.setattr(PlayingClient, "_lease", _ORIGIN_LEASE)
        monkeypatch.setattr(PlayingClient, "_swing_lease_refusal", _ORIGIN_LEASE_REFUSAL)
    else:
        # the leg-137 shipped engine: the field beat revokes the intent it
        # cannot serve, and the displacement arms no enforcing reservation
        def _revoking(self, state, actions, *, renew=True, revoke=True):
            return _ORIGIN_AUTHORIZE(self, state, actions, renew=renew, revoke=True)

        monkeypatch.setattr(PlayingClient, "authorize_farm_actions", _revoking)
        monkeypatch.setattr(PlayingClient, "_lease", lambda *_: _InertLease())
        monkeypatch.setattr(PlayingClient, "_swing_lease_refusal", lambda *_: None)

    wire, client, now = _world()
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
    # the goal-travel pump: the beat the churn engine rode every 2 s; its leg
    # walks AWAY from the mob, so every dispatched step resets arrival truth
    client._field_pump_at = -2.0
    client._field_intent = SimpleNamespace(plan=SimpleNamespace(map_name="prontera"))  # type: ignore[assignment]
    client.field_travel_actions = lambda _state: (MoveTo(50, 38),)  # type: ignore[method-assign,assignment]

    beats = [0.0, *TICKS]

    def field_tick(t: float, body: int) -> None:
        now[0] = t
        tracker = client._tracker
        assert tracker is not None
        pos = tracker.view.position
        assert pos is not None
        # the previous walk completed server-side during the beat gap: its
        # end frame is the standing truth this beat starts from
        wire.add(walk_ack((pos.x, pos.y), (pos.x, pos.y)))
        client._pump_field_travel()
        # the world acks every dispatched walk: a moving walkok resets the
        # arrival truth exactly like the server's own stream does
        pending = client._pending
        if pending is not None and (pos.x, pos.y) != pending[0]:
            wire.add(walk_ack((pos.x, pos.y), pending[0]))
        # an aggressive spawn follows the contested walk (fresh body, fresh
        # sighting): the contest stays adjacent instead of drifting apart
        follow = pending[0] if pending is not None else (pos.x, pos.y)
        wire.add(monster(aid=body, at=(follow[0] + 1, follow[1])))
        client.drain_native_events()
        client._pump_farm_combat()
        collect(t)

    for index, t in enumerate(beats):
        body = 200 + index
        field_tick(t, body)
        if t not in TICKS:
            continue  # the host's first swing needs its brain tick: no 0.0 attack
        state = client.build_native_state(Goal.GRIND)
        actors = state.nearby_monsters
        if actors and actors[0].distance <= 1:
            target = actors[0].id
            client.authorize_farm_actions(state, (Attack(target),))
            client.perform_native(Attack(target))
            if wire.sent and wire.sent[-1] == attack(target):
                rows.append(
                    {
                        "t": iso(t),
                        "persona": PERSONA,
                        "kind": "action_executed",
                        "action": "Attack",
                        "params": {"target_id": target},
                        "map": "prontera",
                        "x": 42,
                        "y": 37,
                    }
                )
        collect(t)
    return client, wire, rows


def _bucket_cells(client: PlayingClient, reasons: str) -> dict[float, dict[str, int]]:
    """Per-bucket delta counts from the client's gate/displacement deques."""
    entries = sorted(getattr(client, reasons, ()))
    cells: dict[float, dict[str, int]] = {bound: {} for bound in BUCKETS}
    for entry in entries:
        at, reason = entry[0], entry[1]
        bound = next((b for b in BUCKETS if at <= b), None)
        if bound is None:
            continue
        bucket = cells[bound]
        bucket[reason] = bucket.get(reason, 0) + 1
    return cells


def _samples(client: PlayingClient) -> list[dict]:
    gates = _bucket_cells(client, "_attack_gate_reasons")
    displaced = _bucket_cells(client, "_walk_displacement_reasons")
    return [
        {
            "t": bound,
            PERSONA: {
                "attack_gates": gates[bound] or None,
                "walk_displaced_for_combat": displaced[bound] or None,
            },
        }
        for bound in BUCKETS
    ]


def test_replay_the_lease_collapses_the_churn_and_converts_the_swing(monkeypatch) -> None:
    pre_client, _pre_wire, pre_rows = _drive(monkeypatch, lease=False)
    post_client, _post_wire, post_rows = _drive(monkeypatch, lease=True)

    pre = summarize_pendingwalk(pre_rows, _samples(pre_client), iso(0), iso(7.0))
    post = summarize_pendingwalk(post_rows, _samples(post_client), iso(0), iso(7.0))

    # pending_walk refusals collapse (cited: the before/after numbers)
    pre_pw = pre["totals"]["pending_walk"]
    post_pw = post["totals"]["pending_walk"]
    assert pre_pw > post_pw >= 0, f"refusals must collapse: before={pre_pw} after={post_pw}"

    # the displacement churn collapses: fewer re-taken slots to displace
    pre_disp = sum(pre["totals"]["displacements"].values())
    post_disp = sum(post["totals"]["displacements"].values())
    assert pre_disp > post_disp >= 0, f"churn must collapse: before={pre_disp} after={post_disp}"

    # the lease backs the re-authors off behind named taps instead of churn
    post_funnel = post["agents"][PERSONA]["funnel"]
    assert post_funnel["lease_backoffs"] >= 1
    assert pre["agents"][PERSONA]["funnel"]["lease_backoffs"] == 0

    # the swing converts through the authored and pump limbs under the lease
    assert post["agents"][PERSONA]["funnel"]["swings"] >= 1

    # classification stays conserved and fully attributed in both arms
    assert sum(pre["totals"]["origins"].values()) == pre_pw
    assert sum(post["totals"]["origins"].values()) == post_pw
    assert pre["totals"]["origins"]["unattributed"] == 0
    assert post["totals"]["origins"]["unattributed"] == 0
