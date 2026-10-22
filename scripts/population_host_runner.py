"""Population live-run runner: the plain host + passive decide/memory sampling.

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
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--leg", default="leg")
    args = parser.parse_args(argv)
    args.duration = float(args.duration)

    # playing.parse_args owns validation; build_host consumes the namespace.
    args.runtime_root = Path(args.runtime_root)
    args.memory_root = Path(args.memory_root)
    args.schedule_file = Path(args.schedule_file) if args.schedule_file else None
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
    steps = 0
    errors = 0
    next_sample = 0.0

    print(
        f"POPULATION-RUNNER[{args.leg}]: duration {args.duration}s, agents {list(host.agents)}",
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
                }
                row[pid] = entry_sample
                summary_parts.append(
                    f"{pid[:14]}={int(entry_sample['online'])}/"
                    f"{entry_sample['decides']}/{entry_sample['pos']}"
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
