# ro-bots Wiki Index

> Design records and concept docs. ADRs in `decisions/` are normative and drive the code.
> Last updated: 2026-10-05 | Total pages: 6

## Decisions
- [[adr-000-hexagonal-architecture]] — ports & adapters; app core depends only on ports
- [[adr-001-event-driven-brain]] — scripts execute; Clef fires on events/reviews, never per tick
- [[adr-002-randomized-timers]] — time-based triggers with random delays (5–20 min class)
- [[adr-003-farm-plans]] — Clef authors farming sessions (duration, target mobs, interrupt rules)
- [[adr-004-isolated-agents-optchat-memory]] — per-agent OptChat memory: append-only log,
  summary tree, fixed-size view, zoom; schedules as experiences
- [[adr-005-society-groups-reputation]] — personas, friend groups + overlapping schedules,
  solo outsiders, SocialGraph affinity, human reputation with damped propagation
- [[adr-006-clef-context-selector]] — Clef ranks memory-line relevance (one pass, ≤64
  score questions) to pick the context view on busy ticks; tree-cover stays the default
- [[adr-007-rust-dashboard]] — Rust dashboard (Dioxus LiveView on Axum; no WASM) consuming
  a WorldFeed SSE/JSON contract; roster, live feed, agent inspector views
- [[adr-008-dashboard-control-plane]] — dashboard grows configurator (counts, ranges,
  generate), persona editing, force-action commands, character tracker; write path via
  a Command API on the WorldFeed contract; local Docker deployment
- [[adr-009-character-builds-item-cognition]] — agents author builds (class path, stats,
  skills, equip goals) via Clef; MechanicsPort pre-calculates item/skill digests so
  item decisions (equip/store/sell) are one Clef pass over normalized comparisons

## Concepts
- [[decision-flow]] — mermaid map of the whole loop: events, scripts, Clef, LLM escalation
- [[escalation-policy]] — when a decision leaves Clef and reaches the LLM
