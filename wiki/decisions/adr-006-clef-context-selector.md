---
title: ADR-006: Clef as a context selector for agent memory
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [memory, decision-model, events]
---

# ADR-006: Clef as a context selector for agent memory

## Context
ADR-004's view is a purely *structural* zoom mechanism (OptChat spec): the
tree geometry decides resolution, and zoom happens on explicit address. It
has no notion of *relevance* — a line about yesterday's party is "kept" only
because it is recent, not because it matters for what is happening now.

## Decision
Add a `ContextSelector` step between the agent's memory and its decision
request. Two interchangeable implementations behind one Protocol:

| Selector | Mechanism | Cost | Use |
|---|---|---|---|
| `TreeCoverSelector` (default) | OptChat tree-cover view (ADR-004) | zero model calls | idle, cheap ticks |
| `ClefContextSelector` | one SystemOne pass: up to 64 `score` questions, one per candidate line — "how relevant is this memory to my current situation?" — rank by expected score, keep top-K | 1 forward pass | busy ticks: combat, chat storms, reputation moments |

- **Candidates** = the TreeCover view lines PLUS zoom-expanded children for
  any line the cheap pass flags as interesting (addressable ids `L2:3` from
  ADR-004 make zoom-after-selection possible).
- The selected lines go into `state.memory_view` (ADR-004 wiring), replacing
  the default view for that decision; the request also keeps a compact
  structural tail (most recent N notes verbatim) so recency is never lost.
- **The same selector output feeds zoom policy**: a line chosen as relevant
  but whose children carry more detail is zoomed before inclusion, bounded
  by the same char budget.
- Selection is itself logged as an experience note (`kind: 'other'`,
  "recalled X because Y") — memory about memory, which compounds.

## Consequences
- Relevance-aware memory costs one extra Clef pass only when the world is
  actually interesting — consistent with ADR-001's economy.
- Clef's calibrated scores make a natural threshold: lines scoring below
  epsilon are actively *not* recalled (suppression is information too).
- Failure mode: a mis-ranked view starves the decision of context. Mitigate
  by keeping the structural tail and measuring recall of seeded facts in tests.

Related: [[adr-004-isolated-agents-optchat-memory]], [[adr-001-event-driven-brain]],
[[decision-flow]]
