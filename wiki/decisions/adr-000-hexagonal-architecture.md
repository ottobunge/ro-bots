---
title: ADR-000: Hexagonal architecture (ports & adapters)
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [architecture, decision-model, llm]
---

# ADR-000: Hexagonal architecture (ports & adapters)

## Decision
The application core (`robots.app`) depends only on **ports**
(`robots.ports`, structural `Protocol`s) and the **domain**
(`robots.domain`, pure data). Every technology is an **adapter**
(`robots.adapters`):

| Port | Local adapter | Remote adapter | Test double |
|---|---|---|---|
| `DecisionModel` | `ClefLocal` (llama.cpp /v1/systemone) | `ClefRemote` (Workers AI) | `ScriptedDecisionModel` |
| `ChatGenerator` | `LocalChatServer` (Qwen llama-server) | `ChatRemote` (OpenAI-compatible) | `StaticChatGenerator` |
| `GameClient` | rAthena clientless session (spike 003) | — | `FakeGameClient` |
| `TickClock` | system clock | — | `FakeClock` |
| `MobDatabase` | rAthena mob_db YAML reader (pending) | — | in-memory dict |

## Consequences
- Swapping Clef-local ↔ Clef-remote, or local ↔ hosted LLM, touches zero app code.
- The whole brain is unit-testable offline; HTTP is mocked at the adapter boundary.
- Static analysis (mypy strict) verifies port conformance structurally.

Related: [[decision-flow]], [[adr-001-event-driven-brain]], [[escalation-policy]]
