# ro-bots Wiki Index

> Design records and concept docs. ADRs in `decisions/` are normative and drive the code.
> Last updated: 2026-10-05 | Total pages: 6

## Decisions
- [[adr-000-hexagonal-architecture]] — ports & adapters; app core depends only on ports
- [[adr-001-event-driven-brain]] — scripts execute; Clef fires on events/reviews, never per tick
- [[adr-002-randomized-timers]] — time-based triggers with random delays (5–20 min class)
- [[adr-003-farm-plans]] — Clef authors farming sessions (duration, target mobs, interrupt rules)

## Concepts
- [[decision-flow]] — mermaid map of the whole loop: events, scripts, Clef, LLM escalation
- [[escalation-policy]] — when a decision leaves Clef and reaches the LLM
