# Decision backend benchmark results (ADR-012)

Canonical workload: `spikes/001-clef-local/bench.py make_bot` — realistic RO
bot state + 18 mixed questions (2390 input tokens). One row per backend per
run date. `$/1k` = USD per 1000 decisions (hosted only).

| date | backend | cold | p50 | p95 | batch-8 | warm-prefix | $/1k | notes |
|---|---|---|---|---|---|---|---|---|
| 2026-10-05 | cpu (Framework, BLAS, 16thr) | — | 64.9s | 77.1s | timeout | 0.94s | — | spike 001 formal run |
| 2026-10-05 | cloudflare-flash | 0.40s | 0.24s | 0.31s* | 3.83s | 0.41s | $0.215 | *p95 outlier 52.4s in this run (route cold-spot); median set stable |
| 2026-10-05 | cloudflare-27b | 0.90s | 0.73s | 1.04s | 6.03s | 0.58s | $0.574 | |
| 2026-10-05 | heavengraph-flash | — | — | — | — | — | — | pending spike 005 |
| 2026-10-05 | heavengraph-27b | — | — | — | — | — | — | pending spike 005 |

Run it yourself:

```
task bench:decisions backends=cloudflare-flash,cloudflare-27b runs=10
```

Interpretation notes:
- Hosted `batch-8` is sequential HTTP (8 calls); the 27B at ~6s for 8 bots
  means ~0.75s/bot amortized — acceptable for event-driven brains.
- `warm-prefix` captures route/KV warmth; hosted shows little reuse benefit,
  the local CPU build shows 65s → 0.94s (prefix KV is the whole game there).
- flash p95 outliers (occasional ~50s call) appeared once in 12 calls; the
  runner should keep its per-call timeout at 60s and retry once.
