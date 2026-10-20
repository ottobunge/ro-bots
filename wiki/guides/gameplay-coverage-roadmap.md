---
title: Gameplay coverage roadmap — player capabilities and native receipts
created: 2026-10-08
updated: 2026-10-08
type: guide
status: proposed
confidence: medium
tags: [architecture, protocol, testing]
sources: [run/reviews/ro-gameplay-coverage-catalogue.json]
---

# Gameplay coverage roadmap

The five recovered audits supply **104 unique candidate requirement rows**, not
an exhaustive inventory of enabled server content or a completion percentage.
See [[goals-ledger]] for current acceptance and
[[native-mechanics-and-encounter-context]] for received-state boundaries.

## Support tiers at the audit snapshot

| Tier | Rows |
|---|---:|
| Missing | 55 |
| Unknown | 14 |
| Offline model | 10 |
| Codec only | 7 |
| Offline pipeline | 12 |
| Historical native primitive | 5 |
| Not applicable | 1 |

No row is classified as a complete native behavior. The five historical native
primitives are observed targeting/approach, normal attack damage, inventory
completion, public chat and party membership; each has explicit limitations.
Rows are identified by feature IDs, with observations, prerequisites, legal
actions, positive native receipts, negative tests, source references and priority.
The CSV is a planning view; the JSON preserves full evidence and caveats.

## Confirmed code gaps

- `src/robots/domain/actions.py:79-94` has no typed item-use, equipment,
  stat/skill allocation or shop transaction action. Encoders elsewhere do not
  make these actions executable through the agent pipeline.
- `src/robots/adapters/native_session_progression.py:74-94` requires raw job 0;
  `:58-64` projects Novice. Other class templates are not native class support.
- `src/robots/domain/model.py:57-83` does not yet carry current base/bonus stats,
  free budgets, learned skills or owned equipment instances.
- The first guarded real NPC click reached missing illustration framing
  `0x01b3`; no subsequent text/menu/private instruction or reward was accepted.
  Framing and actual dialogue acceptance remain prerequisites, not proof of quests.

## Finite implementation order

1. **P0: Finish NPC conversation.** Compiler-proven illustration framing, stable
   independent/project gates, then actual received pages/menu and private notes.
2. **P1: Retain authoritative character resources.** Current stats/bonuses/free
   points/learned skills plus item instances, mutation deltas, zeny and weight.
   Preserve explicit zero; missing/stale stays unknown.
3. **P2: Execute ordinary-player progression.** Legal use/equip/stat/skill actions,
   correlated server responses and state changes, survival, XP and targeted loot.
4. **P3: Complete NPC economic/progression services.** Numeric/text input, real
   quotes/shop transactions, quest prerequisites/rewards, legal warps and an
   authoritative class-refresh path beyond Novice.
5. **P4: Useful group play and repeatability.** Party roles/support, observed
   contributions, private channels, reconnect memory, human playtest and clean E2E.
6. **P5: Broader scope.** Actual dashboard population reconciliation, specialist
   classes/companions, guilds/WoE, sustained populations and matched benchmarks.

These are dependency phases, not a waiver of any standing goal. All six full
milestones remain open; [[playable-world-acceptance]] remains receipt-based.
No changes to immutable ADRs or production code follow from this research guide.

## Evidence and applicability limits

The parent verified five report JSON row counts, all required row fields,
unique IDs and 110 cache-integrity receipts. This is integrity verification,
not an independent semantic approval of every mechanical claim. Economic guide
caches 11–13 differ from their original retrieval digests; they remain quarantined
and excluded from feature claims. Checking their current cache hashes does not
restore retrieval integrity. Some original
citation ledgers contain copyright-only quotes; exact substantive source ranges
are required for implementation decisions, never placeholder evidence alone.

Active MAIN20180704/pre-Renewal and Renewal guide/source evidence are distinct.
Public class keys, scripts and handlers do not establish deployed enablement.
Unavailable or failed sources and unknown configuration remain explicit.
The original batch exited before final reports; recovery used cached evidence.

## Artefacts

- `run/reviews/ro-gameplay-coverage-summary.md` — concise findings and domain gaps
- `run/reviews/ro-gameplay-coverage-catalogue.json` — all 104 rows and provenance
- `run/reviews/ro-gameplay-coverage-catalogue.csv` — compact requirement backlog
- `run/reviews/ro-gameplay-audit-*-recovered.{json,md}` — five source audits
