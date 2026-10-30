"""Population live-run runner: the plain host + passive decide/memory sampling.
import json

Same composition as scripts/plain_host_runner.py (playing.build_host, direct
host.step(), nothing wraps or re-observes the runtime) with three additive
passive samples per 30s tick, read from LIVE ``host.agents`` attributes only:

- ``brain.decision_count`` (per-agent decide counter; acceptance: decides > 0)
- ``agent.online`` + tick_count (schedule-window connect/disconnect edges)
- memory-journal byte/line sizes read from disk (reconnect-continuity diff)

Never holds construction-time client/brain references and never calls
``build_native_state`` (the observing read that starves event windows); the
position comes from the cached ``client.last_built_state`` exactly like the
plain runner.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


def _reason_summary(reasons: Any) -> dict[str, int] | None:
    """Count the recorded gate reasons: {'pending_walk': 12, ...} or None."""
    if not reasons:
        return None
    counts: dict[str, int] = {}
    for _, reason in reasons:
        counts[str(reason)] = counts.get(str(reason), 0) + 1
    return counts


def _error_text(exc: Any) -> str | None:
    """The transport's failure reason, as text.

    Leg 35: the rx thread died on "unknown packet 0x0999" and the whole
    window froze with nothing in the receipt, the log or the trace naming
    it. The receipt must carry the reason, so it is recorded as
    "<ExceptionType>: <message>" - never the traceback.
    """
    if exc is None:
        return None
    message = str(exc)
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def _dispatch_error_summary(errors: Any) -> dict[str, int] | None:
    """Count the per-pid dispatch errors: {'0x0099': 3, ...} or None."""
    if not errors:
        return None
    counts: dict[str, int] = {}
    for pid, _ in errors:
        key = f"0x{int(pid):04X}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _memory_stats(memory_root: Path | None, persona_id: str) -> dict[str, int] | None:
    if memory_root is None:
        return None
    journal = memory_root / f"{persona_id}.jsonl"
    if not journal.is_file():
        return {"lines": 0, "bytes": 0}
    with journal.open("rb") as handle:
        lines = 0
        last = b""
        for raw in handle:
            stripped = raw.strip()
            if stripped:
                lines += 1
                last = stripped
    return {"lines": lines, "bytes": journal.stat().st_size, "last_len": len(last)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--memory-root", required=True)
    parser.add_argument("--decision-url", required=True)
    parser.add_argument("--chat-url", required=True)
    parser.add_argument("--duration", type=float, default=600)
    parser.add_argument("--out-dir", default="run/plain_host_receipts")
    parser.add_argument("--worldfeed-port", type=int, default=8402)
    parser.add_argument("--schedule-file", default=None)
    parser.add_argument("--population-file", default=None)
    parser.add_argument("--heartbeat-min-s", type=float, default=None)
    parser.add_argument("--heartbeat-max-s", type=float, default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--seed-zeny-file", type=Path, default=None)
    parser.add_argument("--leg", default="leg")
    parser.add_argument(
        "--trace-dir",
        default=None,
        help="Per-agent full-trace JSONL directory (<persona>.jsonl). Default: no tracing.",
    )
    args = parser.parse_args(argv)
    args.duration = float(args.duration)

    # playing.parse_args owns validation; build_host consumes the namespace.
    args.runtime_root = Path(args.runtime_root)
    args.memory_root = Path(args.memory_root)
    args.trace_dir = Path(args.trace_dir) if args.trace_dir else None
    args.schedule_file = Path(args.schedule_file) if args.schedule_file else None
    args.population_file = Path(args.population_file) if args.population_file else None
    args.playground = False
    args.command_root = None
    args.skill_knowledge = None
    args.solo = False
    args.llm_planning = False
    args.planning_world = None

    from robots import playing  # noqa: PLC0415 (heavy import kept out of --help)

    host = playing.build_host(args)
    host.start_worldfeed()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt_path = out / f"population-receipt-{args.leg}-{int(time.time())}.json"

    started = time.time()
    deadline = started + args.duration
    samples: list[dict[str, object]] = []
    # The distinct transport-failure reasons already reported (leg 35: a
    # dead transport must be loud in the log, once per distinct reason).
    reported_rx_errors: set[str] = set()
    steps = 0
    errors = 0
    next_sample = 0.0

    print(
        f"POPULATION-RUNNER[{args.leg}]: duration {args.duration}s, agents {list(host.agents)}",
        flush=True,
    )
    _now = host.clock.local_now()
    print("CLOCK:", _now, flush=True)
    print(
        "SCHED:",
        {pid: host._scheduled_on(pid, _now) for pid in host.agents},
        "windows:",
        {
            g.group_id: (getattr(g.schedule, "windows", None), getattr(g, "member_ids", None))
            for g in host.roster.groups
        },
        "configured:",
        (json.loads(args.schedule_file.read_text()) if args.schedule_file else None) is not None,
        flush=True,
    )
    while time.time() < deadline:
        try:
            host.step()
            steps += 1
        except Exception as exc:  # recorded honestly, never silent
            errors += 1
            if errors <= 3:
                print(
                    f"POPULATION-RUNNER[{args.leg}]: host.step raised "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )
        now = time.time()
        if now >= next_sample:
            next_sample = now + 30.0
            row: dict[str, object] = {"t": round(now - started, 1)}
            summary_parts: list[str] = []
            for pid, agent in host.agents.items():
                brain = getattr(agent, "brain", None)
                client = getattr(agent, "client", None)
                wire = getattr(client, "wire", None)
                state = getattr(client, "last_built_state", None)
                entry_sample = {
                    "online": bool(getattr(agent, "online", False)),
                    "decides": getattr(brain, "decision_count", None),
                    "ticks": getattr(agent, "tick_count", None),
                    "standing": getattr(client, "_standing", None),
                    "wire_sent": len(getattr(wire, "sent", []) or []),
                    "moves": len(getattr(wire, "moves", []) or []),
                    "pos": (state.x, state.y) if state is not None else None,
                    "xp_total": getattr(state, "xp_total", None),
                    "nearby_n": len(state.nearby_monsters) if state is not None else None,
                    "memory": _memory_stats(args.memory_root, pid),
                    # the sell-chain state (leg 22: the shop-offer -> the sell
                    # submission hop needs the per-tick visibility)
                    "npc_stage": getattr(
                        getattr(
                            getattr(getattr(client, "_npc", None), "view", None),
                            "stage",
                            None,
                        ),
                        "value",
                        getattr(
                            getattr(getattr(client, "_npc", None), "view", None),
                            "stage",
                            None,
                        ),
                    ),
                    "shop_offer": (
                        "rows=%d" % len(getattr(state.shop_offer, "rows", []))
                        if state is not None and getattr(state, "shop_offer", None)
                        else None
                    ),
                    # the attack-gate telemetry (leg 33: 516 approaches, 6
                    # swings — the receipt must name the drop reason)
                    "attack_gates": _reason_summary(getattr(client, "_attack_gate_reasons", None)),
                    # the move-gate telemetry (w58, leg 38: the unwalkable
                    # deadlock + the ground correction must name themselves)
                    "move_gates": _reason_summary(getattr(client, "_move_gate_reasons", None)),
                    # The transport's own failure reason (leg 35: all seven
                    # agents froze because the rx thread died on an unknown
                    # packet - "unknown packet 0x0999" - and NOTHING in the
                    # receipt, the log or the trace named it. The agent's
                    # tick early-returned on NativeTelemetryUnavailable
                    # forever, so a whole window died silently. The receipt
                    # must carry the reason the transport went down.
                    "rx_error": _error_text(getattr(client, "rx_error", None)),
                    "dispatch_errors": _dispatch_error_summary(
                        getattr(client, "dispatch_errors", None)
                    ),
                }
                row[pid] = entry_sample
                summary_parts.append(
                    f"{pid[:14]}={int(entry_sample['online'])}/"
                    f"{entry_sample['decides']}/{entry_sample['pos']}"
                )
                # A transport that died must be LOUD, once, in the runner log
                # (leg 35: the whole window froze on "unknown packet 0x0999"
                # and the log never said so). Print it the first time each
                # distinct reason appears.
                reason = entry_sample["rx_error"]
                if reason is not None and reason not in reported_rx_errors:
                    reported_rx_errors.add(reason)
                    print(
                        f"POPULATION-RUNNER[{args.leg}] TRANSPORT DOWN "
                        f"pid={pid}: {reason}",
                        flush=True,
                    )
            samples.append(row)
            print(
                f"POPULATION-RUNNER[{args.leg}] t={row['t']}: {' '.join(summary_parts)}",
                flush=True,
            )
        time.sleep(0.25)

    receipt = {
        "runner": "population_host",
        "leg": args.leg,
        "duration_s": args.duration,
        "steps": steps,
        "step_errors": errors,
        "trace_dir": str(args.trace_dir) if args.trace_dir else None,
        "samples": samples,
        "passed": None,  # the operator asserts separately from the DB
    }
    receipt_path.write_text(json.dumps(receipt, indent=2))
    print(
        f"POPULATION-RUNNER[{args.leg}] DONE: steps {steps}, errors {errors}, "
        f"receipt {receipt_path}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
