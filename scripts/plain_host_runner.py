"""Plain-host window runner with passive receipt collection.

The control run (w66-analysis) proved the plain production host moves both
agents while the emission operator's tick layering froze them. This runner
steps the host directly and only READS state afterwards — nothing wraps,
counters, or re-observes the runtime.

Receipt: run/plain_host_receipts/receipt-<unix>.json with per-tick passive
samples: wire sent count, moves list, last built position, DB-visible state
is collected by the operator separately.
"""

import argparse
import json
import sys
import time
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--runtime-root", required=True)
    parser.add_argument("--memory-root", required=True)
    parser.add_argument("--decision-url", required=True)
    parser.add_argument("--chat-url", required=True)
    parser.add_argument("--duration", type=float, default=600)
    parser.add_argument("--playground", action="store_true")
    parser.add_argument("--out-dir", default="run/plain_host_receipts")
    parser.add_argument("--skill-knowledge", default=None)
    parser.add_argument("--worldfeed-port", type=int, default=8400)
    parser.add_argument("--command-root", default=None)
    parser.add_argument("--schedule-file", default=None)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--solo", action="store_true")
    parser.add_argument("--llm-planning", action="store_true")
    parser.add_argument("--planning-world", default="debug")
    args = parser.parse_args(argv)
    args.duration = float(args.duration)
    from pathlib import Path as _P

    args.runtime_root = _P(args.runtime_root)
    args.memory_root = _P(args.memory_root)
    if args.schedule_file:
        args.schedule_file = _P(args.schedule_file)

    from robots import playing

    host = playing.build_host(args)
    host.start_worldfeed()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    receipt_path = out / f"receipt-{int(time.time())}.json"

    started = time.time()
    deadline = started + args.duration
    samples: list[dict[str, object]] = []
    steps = 0
    errors = 0
    next_sample = 0.0

    print(f"PLAIN-RUNNER: duration {args.duration}s, agents {list(host.agents)}", flush=True)
    while time.time() < deadline:
        try:
            host.step()
            steps += 1
        except Exception as exc:  # recorded honestly, never silent
            errors += 1
            if errors <= 3:
                print(f"PLAIN-RUNNER: host.step raised {type(exc).__name__}: {exc}", flush=True)
        now = time.time()
        if now >= next_sample:
            next_sample = now + 30.0
            for pid, agent in host.agents.items():
                client = getattr(agent, "client", None)
                wire = getattr(client, "wire", None)
                state = getattr(client, "last_built_state", None)
                samples.append(
                    {
                        "t": round(now - started, 1),
                        "persona": pid,
                        "standing": getattr(client, "_standing", None),
                        "wire_sent": len(getattr(wire, "sent", []) or []),
                        "moves": len(getattr(wire, "moves", []) or []),
                        "frames": len(
                            (wire.native_frame_snapshot()[2])
                            if wire is not None and hasattr(wire, "native_frame_snapshot")
                            else []
                        ),
                        "pos": (state.x, state.y) if state is not None else None,
                        "xp_total": getattr(state, "xp_total", None),
                        "nearby_n": len(state.nearby_monsters) if state is not None else None,
                    }
                )
        time.sleep(0.25)

    receipt = {
        "runner": "plain_host",
        "duration_s": args.duration,
        "steps": steps,
        "step_errors": errors,
        "samples": samples,
        "passed": None,  # the operator asserts separately from the DB
    }
    receipt_path.write_text(json.dumps(receipt, indent=2))
    print(f"PLAIN-RUNNER DONE: steps {steps}, errors {errors}, receipt {receipt_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
