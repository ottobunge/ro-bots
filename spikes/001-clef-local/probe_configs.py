#!/usr/bin/env python3
"""Probe llama-server config matrix for clef prompt latency at ~400 tokens."""
import json, subprocess, time, urllib.request, sys

BASE = "/home/otto/dev/ro-bots/spikes/001-clef-local/llama.cpp/build/bin"
MODEL = "/home/otto/dev/ro-bots/models/Clef-Flash-Q4_K_M.gguf"

req_small = json.load(open("/tmp/req_test.json"))  # ~2390 tokens - too big for probe
import random
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

req400 = req_of(400)

def start_server(extra):
    p = subprocess.Popen([f"{BASE}/llama-server", "-m", MODEL, "--port", "8092",
                          "--host", "127.0.0.1", "-c", "16384", "--threads", "16",
                          "--no-webui", "-np", "1"] + extra,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        time.sleep(1)
        try:
            urllib.request.urlopen("http://127.0.0.1:8092/health", timeout=2)
            return p
        except Exception:
            pass
    p.kill()
    raise RuntimeError("server did not start")

def timed(body, timeout=300):
    data = json.dumps(body).encode()
    r = urllib.request.Request("http://127.0.0.1:8092/v1/systemone", data=data,
                               headers={"Content-Type":"application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        out = json.loads(resp.read())
    return out, time.perf_counter() - t0

configs = [
    ("fa-on-ub512",  ["-fa", "on",  "-b", "512", "-ub", "512"]),
    ("fa-on-ub4096", ["-fa", "on",  "-b", "4096", "-ub", "4096"]),
    ("fa-off-ub512", ["-b", "512", "-ub", "512"]),
    ("fa-off-ub4096",["-b", "4096", "-ub", "4096"]),
]

results = {}
for name, extra in configs:
    p = start_server(extra)
    try:
        # warmup small
        _, t_warm = timed(req_of(250), timeout=120)
        # probe ~400 tokens
        out, t400 = timed(req400, timeout=300)
        toks = out["usage"]["input_tokens"]
        # probe ~800 tokens only if 400 was fast-ish
        t800 = None
        if t400 < 20:
            out2, t800 = timed(req_of(800), timeout=300)
            t800 = (t800, out2["usage"]["input_tokens"])
        results[name] = (t_warm, t400, toks, t800)
        print(f"{name:14s} warm250={t_warm*1000:6.0f}ms  ~400tok({toks})={t400:6.2f}s  "
              + (f"~800tok({t800[1]})={t800[0]:6.2f}s" if t800 else ""), flush=True)
    except Exception as e:
        results[name] = ("ERR", repr(e))
        print(f"{name:14s} ERROR: {e!r}", flush=True)
    finally:
        p.terminate()
        try: p.wait(5)
        except Exception: p.kill()

print("\nDONE")
