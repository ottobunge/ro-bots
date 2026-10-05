---
title: ADR-012: Decision backend benchmark framework
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [decision-model, ops, testing]
---

# ADR-012: Decision backend benchmark framework

## Context
Criterion 6: a benchmark framework comparing all decision backends — local
CPU (Framework), Heavengraph GPUs (2x RTX 8000), and Cloudflare hosted —
on identical workload, re-runnable as backends evolve.

## Decision

**One workload definition, N adapters, one comparison table.**

`spikes/001-clef-local/bench.py`'s `make_bot(seed)` is already the canonical
workload generator (realistic RO state + 18 mixed questions, 2390 tokens).
It becomes the shared fixture; every backend gets an adapter producing the
same three measurements:

1. **single** — cold, then p50/p95 over N runs of one bot's decision
2. **batch-8** — 8 distinct bots' decisions, wall time for all 8
3. **warm-prefix** — same request twice back-to-back (second call latency;
   captures KV/prefix-reuse and hosted route warmth)

plus `cost_per_1k_decisions` where a price applies.

**Backends** (`spikes/bench/`):

| adapter | endpoint | status |
|---|---|---|
| `cpu` | localhost llama.cpp /v1/systemone (spike 001 build) | measured (p50 64.9s) |
| `cpu-warm` | same, repeated-prefix workload | measured (0.94s) |
| `cloudflare-flash` | Workers AI @cf/cloudflare/clef-flash | measured (p50 0.26s, $0.000215/dec) |
| `cloudflare-27b` | Workers AI @cf/cloudflare/clef | measured (p50 0.91s, $0.000574/dec) |
| `heavengraph-flash` | GPU llama.cpp on Heavengraph (spike 005) | pending spike 005 |
| `heavengraph-27b` | same, full Clef 27B | pending spike 005 |

**Taskfile integration**: `task bench:decisions [backends=cpu,cloudflare-flash,...]`
runs the selected adapters and re-renders
`spikes/bench/RESULTS.md` (the comparison table, committed) with a date
column — historical rows accumulate so regressions are visible.

**Auth**: hosted adapters read `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN`
from `~/.hermes/.env` (user-owned, outside the repo); wrangler OAuth is the
interactive fallback for one-off runs. GPU adapters read
`HEAVENGRAPH_CLEF_URL` (set once spike 005 lands its server).

**Cost guard**: hosted adapters cap at `MAX_BENCH_CALLS` (default 50/run) so
a bad loop can't burn budget.

## Consequences
- Backend choice becomes a data-driven config decision per world:
  debug/test worlds default to stub or cheapest backend; prod can pin
  flash/27B/GPU per ADR-011.
- New backends (vLLM, different quant, Clef successor) = one adapter file +
  one Taskfile entry.

Related: [[adr-011-decision-runtime-strategy]], [[adr-010-worlds-volumes-e2e]]
