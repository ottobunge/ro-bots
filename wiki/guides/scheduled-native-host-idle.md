---
title: Native scheduled-host idle lifecycle and journal restart
created: 2026-10-06
updated: 2026-10-06
type: guide
status: accepted
tags: [ops, testing, rathena, protocol]
---

# Native scheduled-host idle lifecycle and journal restart

This is a bounded host lifecycle/storage check, not Clef/LLM behavior or a complete
standing milestone. See [[goals-ledger]], [[two-bot-live-limbs]] and
[[adr-019-simple-volume-world-isolation]].

## Scope

After the authorization question timed out, the user's fresh direct instruction
was `continue, finish the work`. The coordinator applied it only to the previously
outlined idle-only test: two existing non-human fixtures, at most60 seconds total,
private per-agent session journals and fresh-process restoration. No new accounts,
manual SQL writes, resets, other-world service changes or provider calls.
Credentials and PINs remain private: [REDACTED].

## Prerequisites and discovered test mismatches

- The exact owned test-world containers were stopped at the fresh preflight.
  Labels, immutable image IDs, volume attachments and free loopback ports matched;
  only those four existing containers were resumed. No resources were created or
  reset. Why the services had stopped was not established.
- The first idle-host attempt used second-scale windows with the production
  `PersonaClock`, which truncates local time to minutes. Its window never opened;
  both journals stayed empty and both characters stayed offline. Failure evidence
  was preserved rather than claiming a successful login or changing expectations.
- The corrected bounded probe uses the existing `SocietyClock` injection seam with
  real local wall-clock seconds. It does not simulate time or change production
  clock semantics. Weekly production scheduling still uses the minute-resolution
  default unless a different clock is explicitly supplied.

## Actual host execution

Two fresh Python processes exercised the actual `AgentHost` and `ScheduledAgent`
with the declared native endpoint/PIN manifest and the same two owned fixtures.
The host used one shared schedule window per process, real native clients and
normal worker threads. Transport wrappers imposed one overall deadline and
refused connections outside the three approved native loopback endpoints.

Brains were disabled before live connection. Inference guards were supplied to
avoid provider autodetection, and the HTTP WorldFeed server was not started.
This intentionally verifies idle presence and lifecycle rather than AI behavior.

| Check | First process | Fresh second process |
|---|---|---|
| Schedule opens both native sessions | Passed | Passed |
| Exact account/character pairs and PIN exchange | Passed | Passed |
| Native SQL observes both characters online | Passed | Passed |
| Schedule closes both native sessions | Passed | Passed |
| Supported readers/workers/transports released | Passed | Passed |
| Per-agent journal notes before session | 0 each | 1 each |
| Per-agent journal notes after session | 1 each | 2 each |
| Prior session restored into memory view | Not applicable | Passed |
| Inspector sees current session notes | Passed | Passed |
| Inference calls | 0 | 0 |

The successful two-process run completed in22.678 seconds. Each process kept the
agents online for approximately6.6 seconds. The inspector and scheduled agent
shared the same private per-agent log; constructor-time brain/facade sharing was
also checked before brains were disabled. Session notes contain only the owning
fixture character, not the other agent's character.

## Durable readback and boundaries

Final readback verified two separate schema1 persona journals with two real
session notes each, correct persona ownership, operator ownership, file mode0600
and memory-root mode0700. The second process reopened storage after the first
process shut down normally. Both exact native characters were offline afterward,
with all four test-world services running and the database healthy.

The journals are in the private test-world **host stage**, not yet the production
host path mounted from its named world volume. Summaries used the existing local
deterministic summarizer; no LLM summary/cache-cost or human-relationship recall
claim is made. Supported normal cleanup was observed; inherited interruption and
unknown-callback storage-release limits remain unchanged.

## Evidence

Sanitized reports under `run/reviews/`:

- `scheduled-native-host-activation-permission.json`
- `scheduled-native-host-preflight-diagnostic.json`
- `scheduled-native-host-owned-world-resume.json`
- `scheduled-native-host-idle-failed.json`
- `scheduled-native-host-clock-granularity.json`
- `scheduled-native-host-idle-live.json`

Private manifests, raw logs and journals are not embedded or hashed in public
reports. Production source did not change during this test; the last configured
whole gate remains1,979 tests +65 subtests/94.46% coverage.

## Still open

Truthful native perception before real cognition; actual Clef and LLM escalation;
combat/XP/targeted loot; durable human/bot relationships; multiple characters;
summary-cache/provider behavior; named-volume host storage; dashboard activation
and clean repeatable E2E; legal builds for both rulesets; guilds/WoE; sustained
population and comparable benchmarks. No full standing milestone is closed.
