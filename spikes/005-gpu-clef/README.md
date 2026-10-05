# Spike 005-gpu-clef — Clef decision models on Heavengraph GPUs (2x Quadro RTX 8000)

Move the Clef decision runtime off the local CPU (spike 001: p50 64.9 s/decision,
ADR-011 demoted Clef to amortized planner) onto Heavengraph's 2x RTX 8000 (48 GB
each) and measure whether per-event bot decisions become viable.

## Verdict: SUCCESS (with a caveat on the 27B)

CUDA build works, `/v1/systemone` is served natively, both models answer, and
**Clef-Flash on GPU drops the full 2390-token decision from p50 64.9 s to
p50 1.12 s (~58x)** — with zero errors on the 8-bot concurrent batch that timed
out on CPU. But 1.1 s is still >10x over a <100 ms bot tick budget, so this does
NOT justify undoing ADR-011's tiering on its own: per-event decisions remain
infeasible at tick rate; what changes is that GPU Clef is now fast enough to sit
at Tier 2/3 boundaries (every event, not every 5th) and that 8-bot batches
actually work. Recommendation: **keep ADR-011 tiering, upgrade the GPU Clef
tiers** (Tier-3 planner per event, rules still for reflexes). The 27B at
p50 3.6 s is a quality fallback, not a decision-loop participant.

## Measured numbers (formal — bench.py/lcp_warm.py output in bench_results.txt)

| Metric | CPU (spike 001) | GPU Clef-Flash Q4_K_M | GPU Clef-27B Q4_K_M |
|---|---|---|---|
| Cold decision (warm model) | 68.1 s | 2.86 s | 5.08 s |
| Warm p50 (20 runs) | 64.9 s | **1.12 s** | 3.58 s |
| Warm p95 | 77.1 s | 3.36 s | 5.77 s |
| 8-bot concurrent batch | 4–5 of 8 > 300 s timeout | **8.8 s wall (~1.1 s/bot), 0 errors** | 28.6 s wall (~3.6 s/bot), 0 errors |
| LCP second-call p50 | — | 1.20 s (no gain) | 3.76 s (no gain) |
| pp512 prefill | 27.2 tok/s | 2320 tok/s (~85x) | — |
| VRAM | — | 6.9 GB (GPU 0) | 18.0 GB (GPU 1) |

Speedup vs CPU: Flash **58x** on p50; the 27B is 18x slower than CPU and fits
comfortably on one 48 GB GPU (18 GB) — no need for the 2-GPU row split, which
was measured in a pre-pinning config and gave the same p50.

### LCP/prefix-cache note
The spike-001 hypothesis (second identical request much cheaper via prefix
cache) did NOT reproduce on GPU: second-call p50 ≈ first-call p50 for both
models. Either the LCP path needs smaller state deltas to matter or it doesn't
trigger for /v1/systemone at this size. Not a blocker — cold GPU numbers are
already decision-loop grade for planner-tier use.

### Escalation path (verified end-to-end)
- Remote decision to heavengraph Clef-Flash: 205–430 ms (small request)
- Local Qwen3-4B chat on this host (127.0.0.1:8092): 1.9 s for a 2-sentence reply
- Combination works back-to-back in one runner process.

## Persistent provider (ADR-012 benchmark table row)

Heavengraph is a **standing Clef provider**, not a one-off bench. Everything
lives in `/datamirror/otto/repos/framework-agents/`:

- `flake.nix` + `llama.cpp/` (vendored a7fb71f) — `nix build .#llama-cpp-clef-cuda`
- `serve.sh` (+ `nix run .#serve`) — idempotent, nohup/setsid, survives SSH
- `clef-serve.service` — optional systemd --user unit (`loginctl enable-linger
  otto; systemctl --user enable --now clef-serve.service`)
- weights: `Clef-Flash-Q4_K_M.gguf` (6.5 GB), `Clef-27B-Q4_K_M.gguf` (19.2 GB)

### Reachable URLs (verified from the local host)

| Port | Model | URL |
|---|---|---|
| 8091 | Clef-Flash Q4_K_M | `http://192.168.1.156:8091` (also `http://10.8.0.3:8091`) |
| 8092 | Clef-27B Q4_K_M | `http://192.168.1.156:8092` (also `http://10.8.0.3:8092`) |

**HEAVENGRAPH_CLEF_URL=http://192.168.1.156:8091** — both IPs verified reachable
from the local host; 192.168.1.156 (eno1 LAN, /16) and 10.8.0.3 (tun0 VPN) both
answer.

### Restart commands (after reboot)

On heavengraph:
```bash
cd /datamirror/otto/repos/framework-agents
nix run .#serve          # or: bash serve.sh
```
From the local host:
```bash
ssh heavengraph 'cd /datamirror/otto/repos/framework-agents && nix run .#serve'
```
Health check: `curl -s http://192.168.1.156:8091/v1/systemone -H 'Content-Type: application/json' -d '{"model":"clef","state":{"hp":30,"hp_max":100},"questions":{"hp_low":{"type":"noul","instructions":"low?"}}}'`

Local host restart (Qwen chat): `~/dev/ro-bots/spikes/001-clef-local/result/bin/llama-server -m ~/dev/ro-bots/models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf --port 8092 --host 127.0.0.1 -c 8192 --threads 8 -fa on --no-webui -np 2`

### GPU utilization evidence
nvidia-smi during a full decision: GPU0 max 100% / mean 25%, GPU1 max 73% /
mean 18% (sampled ~0.5 s over SSH — single 2–3 s decision can't sustain 100%
between kernel launches). Idle VRAM: 6.9 GB (GPU0, Flash) + 18.0 GB (GPU1, 27B).

## Build details / pitfalls

- flake reuses nixpkgs `llama-cpp` packaging with `cudaSupport = true` and the
  vendored Clef-capable source (nixpkgs 0.5.0 predates PR #29831 — no
  `server-decision.cpp`, no `/v1/systemone`).
- CUDA EULA is unfree → the flake imports nixpkgs with
  `config.allowUnfree = true`. Note: doing this via `pkgs.extend`/overlay breaks
  on current nixpkgs (stage.nix `attrPathsDisallowedForInternalUse`) — must be a
  fresh `import nixpkgs { config.allowUnfree = true; }`.
- `-DCMAKE_CUDA_ARCHITECTURES=75` (Turing). `-sm none -mg N` pins each model to
  its own GPU; without it both servers split across both GPUs.
- `-np 8` with `-c 65536` (context is divided per slot: 8192/slot, plenty for
  the 2.4k-token request).
- SSH from the local host hits fish as login shell on heavengraph — use
  `ssh heavengraph "bash -c '...'"` for anything nontrivial.
- 27B GGUF is `ggml-org/Clef-GGUF` → `Clef-Q4_K_M.gguf` (19,232,219,104 bytes;
  there is no "Clef-27B-Q4_K_M.gguf" filename upstream).

## Recommendation

1. **ADR-011 tiering stands**, upgraded: GPU Clef-Flash becomes the Tier-3
   planner (per-event, 1.1 s) and can absorb some Tier-2 rule decisions where
   latency ≤1.5 s is tolerable. Reflex tier stays rules-based.
2. Wire `HEAVENGRAPH_CLEF_URL=http://192.168.1.156:8091` into the runner;
   8092 (27B) stays available as the high-quality / arbitration endpoint.
3. Investigate the LCP path with real state-delta requests (90% shared prefix)
   — if tick requests with tiny diffs hit the prefix cache, per-event cost may
   drop well below the 1.1 s cold-ish figure.

## Files (this directory)
- `flake.nix` — CUDA llama.cpp build (spike-local copy; canonical copy is in
  `/datamirror/otto/repos/framework-agents/flake.nix` with `llama.cpp/` + `serve.sh`)
- `serve.sh`, `clef-serve.service` — persistent server launch
- `bench_flash.txt`, `bench_27b.txt`, `lcp_flash.txt`, `lcp_27b.txt`,
  `bench_flash_ip156.txt`, `bench_flash_ip10.txt` — raw results
- `bench_results.txt` — summarized numbers incl. CPU comparison
- `lcp_warm.py` — repeated-prefix measurement helper
