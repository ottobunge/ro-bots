---
title: Matched gameplay decision-provider latency
created: 2026-10-07
updated: 2026-10-07
type: guide
status: proposed
tags: [clef, testing, ops]
---

# Matched gameplay decision-provider latency

An executed matched-request comparison for [[adr-012-benchmark-framework]] and
[[goals-ledger]]. Full hardware/population benchmark acceptance remains open.

## Corrected workload — all three providers succeeded

- Identical synthetic Novice state and actual EventDrivenBrain Heartbeat schema.
- Eleven questions; not the earlier eighteen-question legacy benchmark.
- All providers used the matching clef-flash selector.
- One loaded-service first request, then twenty identical-prefix warm repeats.
- Providers measured sequentially; elapsed time includes HTTP/client overhead.
- The CPU quality suite ran concurrently on Framework; host conditions were not isolated.
- No native clients, game actions, service restarts or dependency changes in the benchmark.
- Raw samples and checks: `run/reviews/matched-playing-backend-benchmark-corrected.json`.

| Provider | Successful / attempted calls | Loaded first | Warm p50 | Warm p95 |
|---|---:|---:|---:|---:|
| framework | 21 / 21 | 6.073s | 5.796s | 6.162s |
| heavengraph | 21 / 21 | 0.704s | 0.642s | 0.710s |
| cloudflare | 21 / 21 | 0.651s | 0.374s | 0.804s |

All returned the expected eleven answer keys. This proves request compatibility,
not decision accuracy. p95 uses nearest rank over twenty warm samples. Framework
GPU activity peaked at100%; device-wide correlation is not per-process proof.

Non-interactive Heavengraph SSH remained unavailable, so remote GPU utilization,
checkpoint/quantization parity and offload were not independently reverified.
Repeated prefixes favour caches. These are not population-scale throughput,
varied-state or true model-cold-start measurements. CPU contention makes the
Framework timings unsuitable as a hardware ceiling or isolated final comparison.

## Preserved original rejection and repair

The earlier malformed request measured Framework/Heavengraph but Cloudflare
returned HTTP422/code5012, naming unsupported top-level `goal_criterion_grind`.
Two bounded diagnostic requests confirmed input validation, not an auth failure.
Preserved evidence: `matched-playing-backend-benchmark-original-rejected.json`
and `matched-cloudflare-failure-diagnostic.json` under `run/reviews/`.

The builder added that helper-derived field and its old exact-key test required
it. Cloudflare's published request examples use model, state and questions. Local
server tolerance was not portable compatibility. TDD removed only that top-level
field, preserving state/questions/helpers; the corrected payload was remeasured
on every provider, rather than comparing new hosted data to the invalid payload.
Source evidence: `systemone-request-schema-repair.json`; combined configured gate
passes3483 unique tests +65 subtests/94.78%. Independent schema review remains a
separate source-review record; successful inference is not its substitute.

[[decision-flow]] remains event-driven; this measurement does not authorize
per-tick inference. Credentials and connection values: [REDACTED].
