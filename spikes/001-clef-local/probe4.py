#!/usr/bin/env python3
"""Clean single-config scaling measurement for clef prompt eval.
Server config identical to the original fast run: defaults (server forces ubatch 512),
np 4, c 8192, fa on. No other llama processes. Monitors CPU MHz via /proc/cpuinfo.
"""
import json, subprocess, time, urllib.request, sys, random, threading, os

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

def cpu_mhz_avg():
    vals = []
    with open("/proc/cpuinfo") as f:
        for line in f:
            if line.startswith("cpu MHz"):
                vals.append(float(line.split(":")[1]))
    return sum(vals)/len(vals)

stop = False
samples = []
def monitor():
    while not stop:
        samples.append((cpu_mhz_avg(), os.getloadavg()[0]))
        time.sleep(2)

p = subprocess.Popen([f"{BASE}/llama-server", "-m", MODEL, "--port", "8095",
                      "--host", "127.0.0.1", "-c", "8192", "--no-webui",
                      "-np", "4", "--threads", "16", "-fa", "on"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(120):
    time.sleep(1)
    try:
        urllib.request.urlopen("http://127.0.0.1:8095/health", timeout=2)
        break
    except Exception:
        pass
else:
    p.kill(); sys.exit("server did not start")

print("server up. loadavg now:", os.getloadavg(), flush=True)

def timed(body, timeout=300):
    data = json.dumps(body).encode()
    r = urllib.request.Request("http://127.0.0.1:8095/v1/systemone", data=data,
                               headers={"Content-Type":"application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        out = json.loads(resp.read())
    return out, time.perf_counter() - t0

mon = threading.Thread(target=monitor, daemon=True)
mon.start()

try:
    for target in [250, 250, 500, 1000, 2000]:
        try:
            out, dt = timed(req_of(target), timeout=300)
            n = out["usage"]["input_tokens"]
            print(f"target~{target:5d} tokens={n:5d} lat={dt:7.2f}s -> {n/dt:6.1f} tok/s", flush=True)
        except Exception as e:
            print(f"target~{target}: ERROR {e!r} after {time.perf_counter()-t0:.0f}s", flush=True)
finally:
    stop = True
    time.sleep(0.5)
    p.terminate()
    try: p.wait(5)
    except Exception: p.kill()

mhz = [s[0] for s in samples]
print(f"\nCPU MHz during test: min={min(mhz):.0f} avg={sum(mhz)/len(mhz):.0f} max={max(mhz):.0f}", flush=True)
print("DONE")
