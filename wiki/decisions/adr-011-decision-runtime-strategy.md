---
title: ADR-011: Decision-model runtime strategy after spike 001
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [decision-model, ops, escalation]
---

# ADR-011: Decision-model runtime strategy after spike 001

## Context
Spike 001 (spikes/001-clef-local/README.md) measured Clef-Flash Q4_K_M via
llama.cpp `/v1/systemone` on this host (Ryzen AI 9 HX 370, BLAS build,
16 threads):

- Realistic bot decision (2390 tokens, 18 questions, one joint pass): **p50 64.9s / p95 77.1s**.
- Concurrent 8-bot batches time out (slots serialize on CPU; no true single-pass batch endpoint).
- Qwen3-4B chat escalation: ~2s idle, coexists in RAM (34.6/93GB total).
- LCP/prefix-KV observation: a repeated-prefix request dropped to **0.94s** — real bots resend ~90% identical state per event.

## Decision
**Clef is NOT the per-event decider on this host; it is the periodic planner.**
The brain's tiering changes from "Clef per event" to:

1. **Tier 1 — scripted reflexes (0 model calls)**: movement, attack/loot,
   rest, travel continue exactly per ADR-001 scripts. Unchanged.
2. **Tier 2 — rule-based event triage (0 model calls)**: event → action via
   deterministic domain rules (aggressive monster → attack or flee by level
   delta; damage → rest if hp low; party invite → accept if affinity ≥
   threshold). These are the rules Clef *would* have picked, encoded after
   measuring its answers; they carry a `rule_id` for auditability.
3. **Tier 3 — Clef, amortized**: goal reviews / heartbeat / farm-plan
   authoring / context selection run on a **randomized slow cadence**
   (ADR-002 timers, minutes-scale), taking the ~65s hit only occasionally,
   optionally batched across bots in sequence. Priority: farm plans and
   ADR-006 context selection benefit most (large prefixes, low frequency).
4. **Tier 4 — LLM chat** unchanged (Qwen ~2s, escalations rare per
   ADR-001's escalation counter).

**Prefix discipline** (enables the 0.94s LCP path): decision requests keep
their state keys in stable order, diffs (hp, position, nearby) go LAST in
the serialized state, and the questions block is byte-identical across
ticks per bot. The runner reuses llama-server slots one bot per slot.

**Adapter contract unchanged**: `DecisionModel` port still receives every
Tier-3 call; a remote/hosted Clef (Workers AI) or a smaller backbone can be
swapped in without touching the brain — and the e2e (ADR-010) defaults to
the stub so tests never wait on model latency. `CLEF_URL` enables real
decisions when available.

## Consequences

**ADDENDUM (2026-10-05, after hosted benchmark — spike 001 README addendum):**
Cloudflare Workers AI hosted Clef measured on the identical 2390-token
request: **clef-flash p50 0.26s / 27B p50 0.91s**, at $0.000215 / $0.000574
per decision. Tiering revised:

- `ClefRemote` (hosted) becomes the **default `DecisionModel`** — per-event
  decisions are practical again, including monster/damage reactions.
- Tier-2 rules remain as the offline/fallback path (API outage, budget cap,
  air-gapped demo) and as sub-100ms reflexes for movement/attack that need
  no model call at all.
- Local CPU llama.cpp Clef survives only via the LCP-warm path (0.94s) for
  air-gapped runs; ADR-002/003 amortization stays good practice.
- Spike 005 (Heavengraph GPU) still pending — if near-hosted latency, it
  becomes the zero-marginal-cost self-hosted option.

The `DecisionModel` port is unchanged by all of this — only the wiring
default changes.

Original CPU-era analysis, kept for the record:

- Event reactions stay sub-second regardless of model speed (Tier 1/2 are pure CPU).
- The "how fast can the world feel" metric becomes: Tier-2 rules for
  reflexes + Clef-reviewed plans at minutes cadence + Qwen chat at ~2s —
  still Clef-authorized behavior, implemented as rules *derived from* its
  measured judgments.
- Spike 001's prefix-KV observation becomes an optimization track: a
  follow-up spike should measure warm-slot repeated-decision latency with
  diff-last serialization before Tier-3 tuning.

Related: [[adr-001-event-driven-brain]], [[adr-006-clef-context-selector]],
[[adr-010-worlds-volumes-e2e]], [[escalation-policy]]
