"""The FULL host, stepped manually, with the ring/exception visibility."""

import sys, time, json, traceback

sys.argv = [
    "probe",
    "--manifest",
    "run/worlds/test-first-live-86e7c36895db/host-idle-3c6ada4253/host-manifest.json",
    "--runtime-root",
    ".work/runtime/ro-bots-test",
    "--memory-root",
    ".work/playing-grind-operator/memory",
    "--decision-url",
    "http://192.168.1.156:8091/v1/systemone",
    "--chat-url",
    "http://127.0.0.1:8300/v1/chat/completions",
    "--playground",
    "--duration",
    "150",
]
from robots import playing

args = playing.parse_args(sys.argv[1:])
host = playing.build_host(args)
host.start_worldfeed()

print("PROBE starting; agents:", list(host.agents), flush=True)
t0 = time.time()
n = 0
while time.time() - t0 < 130:
    n += 1
    try:
        host.step()
    except Exception as e:
        print(f"step {n}: HOST STEP RAISED {type(e).__name__}: {str(e)[:120]}", flush=True)
        time.sleep(1)
        continue
    if n % 40 == 0:
        for pid, agent in host.agents.items():
            cl = agent.client
            snap = cl.native_frame_snapshot() if hasattr(cl, "native_frame_snapshot") else None
            inner = getattr(cl, "_client", None)
            ring = None
            if inner is not None and hasattr(inner, "native_frame_snapshot"):
                ring = len(inner.native_frame_snapshot()[2])
            elif snap is not None:
                ring = len(snap[2])
            print(
                json.dumps(
                    {
                        "step": n,
                        "pid": pid,
                        "client_type": type(cl).__name__ if cl else None,
                        "ring": ring,
                        "standing": getattr(cl, "_standing", None),
                        "ticks": getattr(agent, "_session_ticks", None),
                        "tick_count": getattr(agent, "tick_count", None),
                    },
                    default=str,
                ),
                flush=True,
            )
    time.sleep(0.25)
print("PROBE DONE", flush=True)
