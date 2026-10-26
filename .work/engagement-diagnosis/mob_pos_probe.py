#!/usr/bin/env python3
"""The mob-position staleness probe: WIRE frames vs the PRODUCTION tracker.

One bare client (the pinned spike BotClient) logs into the e2e world, stands
next to the prt_fild08 monsters and dumps, for ~3 minutes, every frame that
carries an actor id + coordinates, side by side with what the production
tracker projects for the SAME actor ids.

Read-only diagnostic with respect to production src/: it never writes to
src/, never loots, never chats. The only bytes it sends are the handshake
(login, char select, map enter, actor-init), the periodic keepalive the spike
client already owns, and - only under --chase, bounded by --max-attacks - the
production Attack packet, so the server's own verdict frame can be observed.
Credentials are read at runtime from the world manifest and are never printed.

The production projection is NOT re-implemented here: the probe imports
src/robots/adapters/native_gameplay.py (NativeGameplayTracker),
src/robots/app/playing_runtime.py (PlayingClient._nearby) and
src/robots/app/scripts.py (_melee_action, _approach_cell) from the checkout
under test and feeds them the very frames the wire delivered, in order.

Usage (inside the nix dev shell):

    python3 .work/engagement-diagnosis/mob_pos_probe.py \
        --manifest run/worlds/e2e/e2e-isolated/host-manifest.json \
        --seconds 180 --out .work/engagement-diagnosis/out/mobpos-run1

    python3 .work/engagement-diagnosis/mob_pos_probe.py \
        --manifest run/worlds/e2e/e2e-isolated/host-manifest.json \
        --seconds 180 --chase --max-attacks 8 \
        --out .work/engagement-diagnosis/out/mobpos-run3
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "spikes" / "003-clientless-limbs"))
sys.path.insert(0, str(REPO / "src"))

from client import BotClient  # noqa: E402  (the pinned spike client)
import packetdb  # noqa: E402  (the pinned spike packet db)
from robots.adapters.native_gameplay import NativeGameplayTracker  # noqa: E402

# --------------------------------------------------------------- wire decode
# rAthena e985006171d2 src/map/clif.cpp:177-185 (WBUFPOS2) and 213-239
# (RBUFPOS2): MoveData[0..2] = the CURRENT cell (x0,y0), MoveData[2..4] = the
# DESTINATION (x1,y1), MoveData[5] = the step sizes.
ACTOR_ENTRY_LEN = {0x09FD: 110, 0x09FE: 103, 0x09FF: 104}
FRAME_NAME = {
    0x09FD: "ZC_NOTIFY_MOVEENTRY(walking)",
    0x09FE: "ZC_NOTIFY_NEWENTRY(spawn)",
    0x09FF: "ZC_NOTIFY_STANDENTRY(stand)",
    0x0080: "ZC_NOTIFY_VANISH",
    0x0087: "ZC_NOTIFY_PLAYERMOVE(self walk)",
    0x08C8: "ZC_NOTIFY_ACT(damage)",
    0x0097: "ZC_MONSTER_HP",
}


def rbufpos(raw: bytes, off: int) -> tuple[int, int]:
    """RBUFPOS (clif.cpp:198-211): x = (p0<<2)|(p1>>6), y = ((p1&0x3f)<<4)|(p2>>4)."""
    return (raw[off] << 2) | (raw[off + 1] >> 6), ((raw[off + 1] & 0x3F) << 4) | (
        raw[off + 2] >> 4
    )


def rbufpos2(raw: bytes, off: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """RBUFPOS2 (clif.cpp:213-239): the from-cell and the destination."""
    x0, y0 = rbufpos(raw, off)
    x1 = ((raw[off + 2] & 0x0F) << 6) | (raw[off + 3] >> 2)
    y1 = ((raw[off + 3] & 0x03) << 8) | raw[off + 4]
    return (x0, y0), (x1, y1)


def decode_actor_frame(pid: int, raw: bytes) -> dict[str, Any] | None:
    """Header + coordinates of an actor presentation frame (0x09FD/0x09FE/0x09FF)."""
    if len(raw) != ACTOR_ENTRY_LEN.get(pid):
        return None
    objecttype = raw[4]
    aid = struct.unpack_from("<I", raw, 5)[0]
    char_id = struct.unpack_from("<I", raw, 9)[0]
    if pid == 0x09FD:
        frm, to = rbufpos2(raw, 63)
    else:
        frm = to = rbufpos(raw, 59)
    return {
        "objecttype": objecttype,
        "aid": aid,
        "char_id": char_id,
        "wire_from": list(frm),
        "wire_to": list(to),
    }


def decode_self_walk(raw: bytes) -> dict[str, Any]:
    """ZC_NOTIFY_PLAYERMOVE (0x0087): the from-cell and the walk destination."""
    frm = rbufpos(raw, 6)
    b, c, d = raw[8:11]
    to = (((b & 15) << 6) | (c >> 2), ((c & 3) << 8) | d)
    return {"wire_from": list(frm), "wire_to": list(to)}


def chebyshev(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _actor_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per actor id: frame counts and the tracked-vs-wire position deltas."""
    stats: dict[str, Any] = {}
    for row in rows:
        key = f"0x{row['aid']:x}"
        bucket = stats.setdefault(
            key,
            {
                "objecttype": row.get("objecttype"),
                "frames": {},
                "tracked_missing": 0,
                "max_delta_from": 0,
                "max_delta_to": 0,
                "samples": [],
            },
        )
        bucket["frames"][row["frame"]] = bucket["frames"].get(row["frame"], 0) + 1
        if row.get("tracked") is None:
            bucket["tracked_missing"] += 1
            continue
        for field in ("delta_from", "delta_to"):
            delta = row.get(field)
            if delta is None:
                continue
            bucket[f"max_{field}"] = max(
                bucket[f"max_{field}"], max(abs(delta[0]), abs(delta[1]))
            )
        if len(bucket["samples"]) < 40:
            bucket["samples"].append(
                {
                    "at": row["at"],
                    "frame": row["frame"],
                    "wire_from": row["wire_from"],
                    "wire_to": row["wire_to"],
                    "tracked": row["tracked"],
                    "delta_from": row.get("delta_from"),
                    "delta_to": row.get("delta_to"),
                }
            )
    return stats


# ------------------------------------------------------------ the probe client
class ProbeClient(BotClient):
    """The pinned spike client plus a frame tap that feeds the production tracker."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.frames: list[tuple[float, int, bytes]] = []
        self.tracker: NativeGameplayTracker | None = None
        self.seq = 0
        self.denied_at: float | None = None
        self.deny_reason: str | None = None
        self._t0 = time.monotonic()

    def _map_server(self, ip: str, port: int) -> None:
        """Start the production tracker with the map session, as production does."""
        if self.tracker is None:
            self.tracker = NativeGameplayTracker(own_actor_id=self.aid)
            self.tracker.consume_snapshot(1, 0, ())
        super()._map_server(ip, port)

    def _dispatch(self, pid: int, raw: bytes) -> None:
        super()._dispatch(pid, raw)
        at = time.monotonic() - self._t0
        self.frames.append((at, pid, raw))
        if self.tracker is None:
            return
        self.seq += 1
        try:
            accepted = self.tracker.consume_snapshot(1, 0, ((self.seq, at, pid, raw),))
        except ValueError as error:  # the production path denies on a bad frame
            self.denied_at = at
            self.deny_reason = f"ValueError: {error}"
            return
        if not accepted and self.denied_at is None:
            self.denied_at = at
            self.deny_reason = "consume_snapshot denied the frame"


def production_nearby(view: Any, pos: Any, map_name: str) -> tuple[Any, ...]:
    """The production state projection (PlayingClient._nearby) for the tracked view."""
    try:
        from robots.app.playing_runtime import PlayingClient
    except Exception:  # pragma: no cover - the fallback keeps the probe usable
        return tuple(view.actors)

    class _MobDb:
        catalog: dict[int, Any] = {}

        def observe(self, map_name: str, species: list[int]) -> None:
            return None

    class _Stub:
        _npc_names: dict[int, str] = {}
        _species: dict[int, int] = {}
        mob_db = _MobDb()

    return PlayingClient._nearby(_Stub(), view, pos, map_name)


class _StateStub:
    """The only BotState fields the production melee gate reads."""

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y


def production_melee_action(nearby: tuple[Any, ...], x: int, y: int) -> tuple[str, Any]:
    """Run the PRODUCTION melee gate over the production state projection.

    Returns ("Attack", target) or ("MoveTo", (x, y)) exactly as
    robots.app.scripts._engage/_melee_action would decide it.
    """
    from robots.app.scripts import _approach_cell, _melee_action

    monsters = sorted(
        (actor for actor in nearby if getattr(actor, "kind", None) == "monster"),
        key=lambda mob: mob.distance,
    )
    if not monsters:
        return ("Idle", None)
    state = _StateStub(x, y)
    target = monsters[0]
    action = _melee_action(target, state)
    if type(action).__name__ == "Attack":
        return ("Attack", action)
    cell = _approach_cell(target.x, target.y, state)
    return ("MoveTo", cell)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=180.0)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--account-index", type=int, default=0)
    parser.add_argument(
        "--goto",
        default="",
        help="optional 'x,y' cell to walk to after login (the capture runs during the walk)",
    )
    parser.add_argument(
        "--route",
        default="",
        help="optional ';'-separated 'x,y' waypoints to walk through during the capture",
    )
    parser.add_argument(
        "--chase",
        action="store_true",
        help=(
            "run the production melee gate over the production state projection "
            "and act on it (MoveTo / one Attack). The attack is bounded by "
            "--max-attacks so the disposable e2e world is not farmed."
        ),
    )
    parser.add_argument("--max-attacks", type=int, default=6)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    account = manifest["accounts"][args.account_index]
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    print("PROBE manifest:", args.manifest, flush=True)
    print(
        "PROBE world:",
        manifest.get("login_host"),
        manifest.get("login_port"),
        "account:",
        account.get("char_name"),
        flush=True,
    )

    bot = ProbeClient(
        user=account["account"],
        password=account["password"],
        char_name=account.get("char_name"),
        pincode=account.get("pincode"),
        login_ip=manifest["login_host"],
        login_port=manifest["login_port"],
        verbose=True,
    )
    bot.connect()
    time.sleep(3)
    print(
        "PROBE session:",
        "aid:",
        bot.aid,
        "gid:",
        bot.gid,
        "map:",
        bot.map_name,
        "pos:",
        (bot.x, bot.y),
        flush=True,
    )

    # The production tracker starts with the map session (see ProbeClient._map_server):
    # it is fed the very frames the wire delivered, in order (the production path
    # reads the same frames out of the client's native-frame ring).
    if bot.tracker is None:
        bot.tracker = NativeGameplayTracker(own_actor_id=bot.aid)
        bot.tracker.consume_snapshot(1, 0, ())
    tracker = bot.tracker

    if args.goto:
        gx, gy = (int(part) for part in args.goto.split(","))
        print("PROBE walking to", (gx, gy), flush=True)
        bot.move(gx, gy)

    route: list[tuple[int, int]] = []
    for chunk in args.route.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        rx, ry = (int(part) for part in chunk.split(","))
        route.append((rx, ry))

    frames_path = out / "frames.jsonl"
    samples_path = out / "samples.jsonl"
    t_end = time.monotonic() + args.seconds
    next_sample = time.monotonic()
    wire_mob: dict[int, dict[str, Any]] = {}
    wire_self: dict[str, Any] = {}
    counts: dict[str, int] = {}
    actor_rows: list[dict[str, Any]] = []

    with frames_path.open("w") as frames_out, samples_path.open("w") as samples_out:
        route_index = 0
        next_route = time.monotonic() + 12.0
        next_decide = time.monotonic() + 2.0
        next_keepalive = time.monotonic() + 8.0
        attacks: list[dict[str, Any]] = []
        pending_attack: dict[str, Any] | None = None
        while time.monotonic() < t_end:
            time.sleep(0.05)
            if route and time.monotonic() >= next_route:
                rx, ry = route[route_index % len(route)]
                route_index += 1
                print(f"PROBE route -> ({rx},{ry})", flush=True)
                bot.move(rx, ry)
                next_route = time.monotonic() + 12.0
            if time.monotonic() >= next_keepalive:
                # the server drops a silent session; the spike client's own
                # keepalive is the only client->server traffic a standing probe
                # sends (CZ_REQUEST_TIME 0x0360).
                bot.keepalive()
                next_keepalive = time.monotonic() + 8.0
            # ---- drain the frames captured since the last tick
            while bot.frames:
                at, pid, raw = bot.frames.pop(0)
                counts[FRAME_NAME.get(pid, hex(pid))] = (
                    counts.get(FRAME_NAME.get(pid, hex(pid)), 0) + 1
                )
                row: dict[str, Any] = {"at": round(at, 3), "pid": hex(pid), "len": len(raw)}
                if pid in ACTOR_ENTRY_LEN:
                    decoded = decode_actor_frame(pid, raw)
                    if decoded is None:
                        continue
                    aid = decoded["aid"]
                    wire_mob[aid] = {
                        "frame": FRAME_NAME[pid],
                        "from": decoded["wire_from"],
                        "to": decoded["wire_to"],
                        "at": at,
                        "objecttype": decoded["objecttype"],
                    }
                    observed = tracker.view.actors
                    tracked = next((a for a in observed if a.actor_id == aid), None)
                    row.update(decoded)
                    row["frame"] = FRAME_NAME[pid]
                    row["tracked"] = (
                        [tracked.position.x, tracked.position.y] if tracked is not None else None
                    )
                    row["tracked_walking"] = tracked.walking if tracked is not None else None
                    row["tracked_attackable"] = (
                        tracked.attackable if tracked is not None else None
                    )
                    row["tracked_objecttype"] = (
                        tracked.objecttype if tracked is not None else None
                    )
                    if tracked is not None:
                        tpos = (tracked.position.x, tracked.position.y)
                        row["delta_from"] = [
                            tpos[0] - decoded["wire_from"][0],
                            tpos[1] - decoded["wire_from"][1],
                        ]
                        row["delta_to"] = [
                            tpos[0] - decoded["wire_to"][0],
                            tpos[1] - decoded["wire_to"][1],
                        ]
                    actor_rows.append(row)
                    frames_out.write(json.dumps(row) + "\n")
                elif pid == 0x0087:
                    decoded = decode_self_walk(raw)
                    wire_self = {**decoded, "at": at}
                    view = tracker.view
                    row.update(decoded)
                    row["tracked_self"] = (
                        [view.position.x, view.position.y] if view.position else None
                    )
                    frames_out.write(json.dumps(row) + "\n")
                elif pid == 0x08C8:
                    src = struct.unpack_from("<I", raw, 2)[0]
                    tgt = struct.unpack_from("<I", raw, 6)[0]
                    damage = struct.unpack_from("<i", raw, 22)[0]
                    row.update({"src": src, "tgt": tgt, "damage": damage})
                    if pending_attack is not None and tgt == pending_attack["target_id"]:
                        pending_attack["verdict"] = "damage_landed"
                        pending_attack["damage"] = damage
                    frames_out.write(json.dumps(row) + "\n")
                elif pid == 0x0080:
                    aid = struct.unpack_from("<I", raw, 2)[0]
                    row.update({"aid": aid, "event": "vanish"})
                    wire_mob.pop(aid, None)
                    frames_out.write(json.dumps(row) + "\n")
                elif pid == 0x0139:
                    # ZC_ATTACK_FAILURE_FOR_DISTANCE: the server's out-of-range verdict.
                    row.update(
                        {
                            "target_aid": struct.unpack_from("<I", raw, 2)[0],
                            "target_xy": list(struct.unpack_from("<HH", raw, 6)),
                            "self_xy": list(struct.unpack_from("<HH", raw, 10)),
                            "atk_range": struct.unpack_from("<H", raw, 14)[0],
                        }
                    )
                    if pending_attack is not None:
                        pending_attack["verdict"] = "range_rejected_0x0139"
                        pending_attack["server_target_xy"] = row["target_xy"]
                        pending_attack["server_self_xy"] = row["self_xy"]
                        pending_attack["server_atk_range"] = row["atk_range"]
                    frames_out.write(json.dumps(row) + "\n")
            frames_out.flush()

            # ---- the production decide cadence: the production melee gate
            if pending_attack is not None and time.monotonic() - bot._t0 > (
                pending_attack["at"] + 2.5
            ):
                if pending_attack["verdict"] == "no_verdict_yet":
                    pending_attack["verdict"] = "silent_no_verdict"
                pending_attack = None
            if args.chase and time.monotonic() >= next_decide:
                next_decide = time.monotonic() + 2.0
                view = tracker.view
                pos = view.position
                if pos is not None:
                    nearby = production_nearby(view, pos, bot.map_name)
                    kind, payload = production_melee_action(nearby, pos.x, pos.y)
                    if kind == "Attack" and len(attacks) < args.max_attacks:
                        target_id = payload.target_id
                        wire = wire_mob.get(target_id)
                        record = {
                            "at": round(time.monotonic() - bot._t0, 3),
                            "target_id": target_id,
                            "tracked_self": [pos.x, pos.y],
                            "tracked_target": [
                                wire["from"][0],
                                wire["from"][1],
                            ]
                            if wire
                            else None,
                            "wire_target_from": wire["from"] if wire else None,
                            "wire_target_to": wire["to"] if wire else None,
                            "wire_self_from": wire_self.get("wire_from"),
                            "verdict": "no_verdict_yet",
                        }
                        attacks.append(record)
                        pending_attack = record
                        print("PROBE attack", json.dumps(record), flush=True)
                        bot._send(
                            packetdb.pack(
                                0x0437, struct.pack("<I", target_id) + bytes([0])
                            )
                        )
                    elif kind == "MoveTo" and payload is not None:
                        bot.move(payload[0], payload[1])

            # ---- periodic projection sample
            if time.monotonic() >= next_sample:
                next_sample = time.monotonic() + 0.5
                view = tracker.view
                pos = view.position
                tracked_self = (pos.x, pos.y) if pos else None
                mobs = []
                for actor in view.actors:
                    wire = wire_mob.get(actor.actor_id)
                    entry = {
                        "aid": actor.actor_id,
                        "objecttype": actor.objecttype,
                        "attackable": actor.attackable,
                        "tracked": [actor.position.x, actor.position.y],
                        "tracked_age_s": round(time.monotonic() - bot._t0 - actor.position.at, 3),
                        "wire": wire,
                    }
                    if wire and tracked_self:
                        tracked_cell = (actor.position.x, actor.position.y)
                        wire_from = tuple(wire["from"])
                        wire_to = tuple(wire["to"])
                        entry["tracked_vs_wire_from"] = chebyshev(tracked_cell, wire_from)
                        entry["tracked_vs_wire_to"] = chebyshev(tracked_cell, wire_to)
                        # the gate the production script reads (scripts.py:_melee_action)
                        entry["gate_tracked_cheb"] = chebyshev(tracked_cell, tracked_self)
                        # the gate the SERVER reads: the self cell it occupies
                        # (the last walk frame's from-cell) against the mob cell
                        self_wire_from = (
                            tuple(wire_self["wire_from"]) if wire_self.get("wire_from") else None
                        )
                        if self_wire_from is not None:
                            entry["gate_wire_from_cheb"] = chebyshev(wire_from, self_wire_from)
                            entry["gate_wire_to_cheb"] = chebyshev(wire_to, self_wire_from)
                            entry["would_attack_but_out_of_range"] = (
                                entry["gate_tracked_cheb"] <= 1
                                and entry["gate_wire_to_cheb"] > 1
                            )
                        entry["self_wire_from"] = wire_self.get("wire_from")
                        entry["self_tracked"] = list(tracked_self)
                        entry["self_wire_delta"] = (
                            [
                                tracked_self[0] - wire_self["wire_from"][0],
                                tracked_self[1] - wire_self["wire_from"][1],
                            ]
                            if wire_self.get("wire_from")
                            else None
                        )
                    mobs.append(entry)
                sample = {
                    "t": round(time.monotonic() - bot._t0, 3),
                    "map": bot.map_name,
                    "tracked_self": list(tracked_self) if tracked_self else None,
                    "wire_self": wire_self,
                    "tracker_denied_at": bot.denied_at,
                    "tracker_deny_reason": bot.deny_reason,
                    "mobs": mobs,
                }
                samples_out.write(json.dumps(sample) + "\n")
                samples_out.flush()

    summary = {
        "manifest": str(args.manifest),
        "seconds": args.seconds,
        "session": {
            "aid": bot.aid,
            "gid": bot.gid,
            "map": bot.map_name,
            "start_pos": [bot.x, bot.y],
        },
        "frame_counts": counts,
        "tracker_denied_at": bot.denied_at,
        "tracker_deny_reason": bot.deny_reason,
        "tracker_actors": {
            hex(a.actor_id): {
                "objecttype": a.objecttype,
                "attackable": a.attackable,
                "position": [a.position.x, a.position.y],
                "position_seq": a.position.seq,
                "position_age_s": round(time.monotonic() - bot._t0 - a.position.at, 3),
                "walking": a.walking,
            }
            for a in tracker.view.actors
        },
        "actor_frames": _actor_stats(actor_rows),
        "attacks": attacks,
        "wire_mobs": {hex(k): v for k, v in wire_mob.items()},
        "wire_self": wire_self,
        "spike_actor_count": len(bot.actors),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print("PROBE DONE ->", out, flush=True)
    print(json.dumps(summary["frame_counts"], indent=2), flush=True)
    try:
        bot.close()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
