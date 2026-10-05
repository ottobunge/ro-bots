---
title: ADR-004: Isolated agents with OptChat-style episodic memory
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [memory, events, decision-model, llm]
---

# ADR-004: Isolated agents with OptChat-style episodic memory

## Context
Agents must be **isolated**: no global knowledge. Each knows only what it has
perceived. They must remember people (players and other agents) across
sessions — "Otto helped me yesterday", "that guild wiped us at Orc Dungeon" —
even after days offline.灵感: Victor Taelin's OptChat
(gist 91837951a5ce5b38f341ec1ba1df6449).

## Decision
Each agent owns a private `MemoryLog` built exactly on the OptChat spec:

1. **Append-only log (ROOT)**: every perceived experience is appended
   verbatim as a short note (`kind`, `ts`, `text`), never edited, never deleted.
2. **Summary tree**: node `(l, i)` covers messages `[i·2^l, (i+1)·2^l)`.
   Level 0 = one-line summary of one message; level `l` merges children
   `(l-1, 2i)` + `(l-1, 2i+1)`. Built bottom-up by a cheap summarizer
   (our local Qwen via `ChatGenerator`; a deterministic stub for tests).
3. **View**: a fixed byte budget (bots use ~4k chars, far below Clef's 16k
   encode limit) covering the WHOLE log: recent lines at full resolution,
   older ones coalesced many-per-line, oldest coarsest. Injected into the
   decision request as `state.memory_view` — so Clef sees the agent's whole
   past every decision, at constant size.
4. **Zoom**: when a view line is too vague and relevant (low decision
   confidence, or a name in the line matches someone in the current
   perception), the app resolves that node into its two children and
   re-renders the view — down to the original experience note.

Schedules live in the same log: connect/disconnect sessions are themselves
experiences ("played 21:00–23:30, partied with Mika"), so an agent that
returns after days reconstructs who it knows and what it was doing.

## Consequences
- Isolation is structural: nothing outside an agent's log can enter its brain.
- Memory cost per agent is constant regardless of lifetime (log grows, view doesn't).
- The summarizer is a port consumer (`ChatGenerator`) → local Qwen first, remote later.

Related: [[adr-000-hexagonal-architecture]], [[adr-001-event-driven-brain]],
[[adr-005-society-groups-reputation]]
