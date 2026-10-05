# Spike 001-clef-local — Cloudflare Clef-Flash on NixOS (CPU-only)

Validate that Cloudflare's Clef-Flash decision model runs locally fast enough to
drive Ragnarok Online bot decisions, exposed behind a SystemOne-compatible HTTP API.

## Addendum (2026-10-05): hosted Workers AI benchmark — VALIDATED

`bench_cloudflare.py` runs the identical 2390-token decision request against
the hosted models (auth via wrangler OAuth, token stays in local keyring):

| runtime | cold | p50 | p95 | in_tokens | cost/decision |
|---|---|---|---|---|---|
| local CPU (above) | — | 64.9s | 77.1s | 2390 | — |
| local CPU LCP-warm | — | 0.94s | — | ~249 | — |
| **@cf/cloudflare/clef-flash** | 0.30s | **0.26s** | **0.31s** | 2390 | **$0.000215** |
| **@cf/cloudflare/clef (27B)** | 0.71s | **0.91s** | **1.36s** | 2390 | **$0.000574** |

Gotchas: the request's `model` field must be `clef`/`clef-flash` to match the
URL's model (422 otherwise); answers are nested under `result.answers`.

**Verdict for hosted runtime: VALIDATED.** Per-event Clef decisions are
practical again — p50 0.26s (flash) / 0.91s (27B) at ~$0.22–0.57 per 1000
decisions. ADR-011's Tier-3 limitation is lifted: see ADR-011 addendum for
the revised tiering (hosted Clef becomes the default `DecisionModel`, local
CPU/LCP-warm path remains the offline fallback, GPU spike 005 still pending).

## Verdict: PARTIAL

The full stack works — llama.cpp master (a7fb71f) has a **native `POST /v1/systemone`
endpoint** (no wrapper needed), the flake builds it reproducibly, Clef-Flash Q4_K_M
answers 18 mixed RO questions in one joint pass, and it coexists with a Qwen3-4B
chat server in 35 GB of 93 GB RAM. But on this CPU (Ryzen AI 9 HX 370, no dGPU) a
realistic bot decision (~2400 tokens: state + 18 questions) takes **~60–90 s**,
roughly 1000x over the <1 s budget for bot ticks.

### What worked
- llama.cpp merged Clef in PR #29831 and the server exposes `/v1/systemone`
  (TypeSafe-compatible: `{model, state, questions}` → `{answers, usage}`).
  `joint_schema_model.py` from the HF card is *not* needed — the C++ server
  implements the same schema (`server-decision.cpp`).
- Reproducible build via flake: `nix build .#llama-cpp-clef` reuses nixpkgs'
  llama-cpp packaging (BLAS backend) with the Clef-capable master source.
- 18 questions (choice/noul/score) answered in ONE forward pass; sensible answers
  (HP 30/100 → hp_low 0.84; "heal plz" → reply_chat).
- Model downloads: Clef-Flash-Q4_K_M (6.5 GB) + Qwen3-4B-Instruct Q4_K_M (2.5 GB).
- Both servers run simultaneously: 34.6 GB used of 93 GB, no swap pressure.

### What didn't
- CPU prefill is the bottleneck: 9B backbone × ~2400 tokens. Measured
  `llama-bench`: pp512 ≈ 27 tok/s, pp2048 ≈ 31 tok/s (16 threads, BLAS build).
  End-to-end decisions: **p50 64.9 s / p95 77.1 s** over 20 runs (formal, see
  `bench_results.txt`).
- **Batching 8 bots via parallel HTTP slots does NOT work at this speed**: with
  `-np 4` and 8 concurrent requests, 4–5 of 8 requests exceeded the 300 s client
  timeout on every trial. llama-server has no single-pass batch endpoint for
  clef requests (unlike the reference `collate_records`); slots just serialize
  on CPU. Formal timeout, not a tuning issue.
- The default ggml-cpu (non-BLAS) build was ~7 tok/s — **10x slower**. nixpkgs'
  BLAS packaging fixed it. Without the user directive we'd have shipped a build
  10x off. (Pitfall: `-np 4` divides `-c` per slot; a 2400-token request needs
  `-c ≥ np × 4000` and `-b/-ub ≥ 4096` or the request 500s.)
- nixpkgs llama-cpp 0.5.0 (v0.5.0 tag, Sep 23 2026) predates the Clef merge
  (Oct 3) — verified: no `server-decision.cpp` in the tag. Source build required
  until nixpkgs bumps.

### Surprises
- One early observation of a 249-token decision in 0.94 s (~265 tok/s, `-np 4`,
  default `-ub 512`) vs 7 tok/s for the same request later (`-np 1` or
  `-ub 4096`). Not reproducible in isolation; the server logs "selected slot by
  LCP similarity" — there is a prefix/LCP KV-reuse path that may make
  *consecutive similar states* (a real bot tick!) far cheaper than cold requests.
  This is the single most promising follow-up: real bots resend ~90% identical
  state each tick.
- `-b/-ub 4096` (needed for big schemas) was slower than 512 on the pure-CPU
  build but roughly neutral on the BLAS build.
- The merged upstream renamed webui→ui (`LLAMA_BUILD_UI`); the flake disables it
  and drops the npm hash pinning (master's package-lock differs from 0.5.0's).

### Recommendation for the real build
1. Do NOT drive per-tick bot decisions with Clef-Flash on CPU. Even Vulkan on
   the 890M (~10x CPU) lands at 6–9 s/decision — still too slow for ticks.
2. Measure the LCP/prefix-cache fast path with a realistic tick loop (state
   diffs only). If tick decisions drop to <1 s, CPU-only becomes viable for
   low-frequency decisions (zone changes, chat triage) with a rules engine
   handling the hot loop.
3. Alternatively use a smaller backbone (Clef family may grow smaller models)
   or a hosted endpoint for decisions, keep Qwen3-4B local for chat (it is fine:
   ~2 s per 2-sentence reply idle, 8 threads).
4. Keep the flake; bump `llama.cpp` submodule pointer when nixpkgs updates.

## How to run

```bash
cd ~/dev/ro-bots/spikes/001-clef-local

# 1. Build (reproducible):
nix build .#llama-cpp-clef --out-link ./result

# 2. Models (already downloaded):
#    ~/dev/ro-bots/models/Clef-Flash-Q4_K_M.gguf
#      curl -L -o ~/dev/ro-bots/models/Clef-Flash-Q4_K_M.gguf \
#        https://huggingface.co/ggml-org/Clef-Flash-GGUF/resolve/main/Clef-Flash-Q4_K_M.gguf
#    ~/dev/ro-bots/models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf
#      curl -L -o ... https://huggingface.co/bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf

# 3. Start the Clef /v1/systemone service (port 8091):
./result/bin/llama-server \
  -m ~/dev/ro-bots/models/Clef-Flash-Q4_K_M.gguf \
  --port 8091 --host 127.0.0.1 \
  -c 16384 --threads 16 -fa on --no-webui \
  -np 4 -b 4096 -ub 4096

#    NOTE: -np 4 splits -c per slot (4096 each); a full RO decision is ~2.5k
#    tokens, so -c must be ≥ np × ~4200 and -b/-ub ≥ 4096 or requests 500.

# 4. Start the Qwen chat server (port 8092):
./result/bin/llama-server \
  -m ~/dev/ro-bots/models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf \
  --port 8092 --host 127.0.0.1 \
  -c 8192 --threads 8 -fa on --no-webui -np 2

# 5. Smoke test:
curl -s http://127.0.0.1:8091/v1/systemone -H 'Content-Type: application/json' -d '{
  "model":"clef-flash",
  "state":{"hp":30,"hp_max":100,"nearby":["Poring"]},
  "questions":{"hp_low":{"type":"noul","instructions":"Is the bot HP low?"}}}'
# → {"answers":{"hp_low":{"type":"noul","noul":0.99...}},"usage":{...}}

# 6. Benchmark:
python3 bench.py --url http://127.0.0.1:8091 --runs 20
```

## Files
- `flake.nix` — devShell + `packages.llama-cpp-clef` (nixpkgs packaging + Clef master src)
- `llama.cpp/` — vendored ggml-org/llama.cpp @ a7fb71f (Clef merge + fixes)
- `bench.py` — realistic RO bot decision generator (18 questions) + p50/p95 + 8-bot batch
- `probe_configs.py`, `probe2.py`, `probe3.py`, `probe4.py` — config/threading probes (evidence)
- `bench_results.txt`, `probe*_results.txt` — raw results

## Measured numbers (this host)

Formal = produced by `bench.py` / `llama-bench` against the final flake build and
server config above. Observed = one-off curl timings during debugging.

| Metric | Value | Status |
|---|---|---|
| Clef decision, full RO request (18 q, 2390 tok), cold-of-process | 68.1 s | formal (bench_results.txt) |
| Warm single decisions, 20 runs | **p50 64.9 s, p95 77.1 s**, mean 66.0 s (min 57.0, max 81.3) | formal |
| Input tokens, full RO request | 2390 (server-reported) | formal |
| 8-bot batch, 8 concurrent requests, `-np 4` | 4–5 of 8 requests > 300 s timeout, all 5 trials | formal (timeout) |
| llama-bench pp512 / pp2048 (Clef Q4_K_M, 16 thr, BLAS) | 27.2 / 30.8 tok/s (tg128 7.6 tok/s) | formal |
| llama-bench pp512, 24 threads | 21.4 tok/s (worse than 16 thr) | formal |
| Same model on non-BLAS ggml-cpu build | pp512 ≈ 7 tok/s (10x slower) | formal |
| Clef decision, tiny (2 q, 249 tok) | 0.94 s once (prefix-cache path?); ~7 s typical on CPU build | observed |
| Qwen3-4B chat, 2-sentence RO reply, idle machine | ~2 s; 5.9 s first cold; 28–30 s while Clef bench saturates CPU | observed |
| Both servers resident | 34.6 GB / 93 GB used — no memory pressure | observed |
| nixpkgs llama-cpp 0.5.0 | no Clef (verified against tag) — do not use until bump | verified |

### SystemOne API status
**No wrapper needed.** This llama.cpp build serves `POST /v1/systemone` natively
(`tools/server/server-decision.cpp`, routed in `server.cpp` at `/v1/systemone`).
Request shape: `{model, state, questions}` where `questions` maps ids to
`{type: noul|choice|score, instructions, criteria}`; response: `{answers: {id:
{...probabilities...}}, usage: {input_tokens, output_tokens: 0}}` — matching the
`joint_schema_model.py` / `systemone()` reference on the HF card. Clef answers
all questions in ONE forward pass (joint, unlike openjev/laya which score
independently). Errors seen: `400` if prompt ≥ context slot, `500` "too large to
process" if prompt > `-ub`.
