#!/usr/bin/env python3
"""Thread scaling probe for clef prompt eval, ~400-token requests, one server at a time."""
import json, subprocess, time, urllib.request, sys, random

BASE = "/home/otto/dev/ro-bots/spikes/001-clef-local/llama.cpp/build/bin"
MODEL = "/home/otto/dev/ro-bots/models/Clef-Flash-Q4_K_M.gguf"
sys.path.insert(0, "/home/otto/dev/ro-bots/spikes/001-clef-local")
from bench import make_bot

rng = random.Random(7)
base = make_bot(999, rng)
qs = {"hp_low": {"type":"noul","instructions":"Is HP low?"},
      "next_action": base["questions"]["next_action"]}
def req_of(ntok_target):
    words = max(1, (ntok_target - 120))
    return {"model":"clef-flash",
            "state":{"pad": " ".join(["monster attack player item level zone gold"] * (words//6))},
            "questions": qs}
req250 = req_of(250)
req450 = req_of(450)

def start_server(thr):
    p = subprocess.Popen([f"{BASE}/llama-server", "-m", MODEL, "--port", "8095",
                          "--host", "127.0.0.1", "-c", "8192", "--no-webui",
                          "-np", "4", "--threads", str(thr)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(120):
        time.sleep(1)
        try:
            urllib.request.urlopen("http://127.0.0.1:8095/health", timeout=2)
            return p
        except Exception:
            pass
    p.kill()
    raise RuntimeError("server did not start")

def timed(body, timeout=200):
    data = json.dumps(body).encode()
    r = urllib.request.Request("http://127.0.0.1:8095/v1/systemone", data=data,
                               headers={"Content-Type":"application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        out = json.loads(resp.read())
    return out, time.perf_counter() - t0

for thr in [4, 8, 16, 24]:
    p = start_server(thr)
    try:
        out1, t1 = timed(req250, timeout=120)   # includes 4-slot warmup
        out2, t2 = timed(req250, timeout=120)   # warm slot
        out2b, t2b = timed(req250, timeout=120) # warm slot repeat
        out3, t3 = timed(req450, timeout=200)
        n = out3["usage"]["input_tokens"]
        print(f"thr={thr:2d}: 250tok cold4slots={t1:6.1f}s warm={t2*1000:6.0f}ms {t2b*1000:6.0f}ms  "
              f"{n}tok={t3:6.2f}s ({n/t3:5.1f} tok/s)", flush=True)
    except Exception as e:
        print(f"thr={thr:2d}: ERROR {e!r}", flush=True)
    finally:
        p.terminate()
        try: p.wait(5)
        except Exception: p.kill()
print("DONE")
