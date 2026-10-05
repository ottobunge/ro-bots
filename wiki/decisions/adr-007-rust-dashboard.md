---
title: ADR-007: Rust web dashboard (Dioxus family)
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [architecture, ops]
---

# ADR-007: Rust web dashboard (Dioxus family)

## Decision
The world is observed and (later) interacted with through a **Rust web
dashboard** living in `dashboard/` (its own Cargo workspace, wired into the
nix devShell). Framework comparison for THIS use case (live-fed observer UI:
agent online/offline by schedule, chat feed, event stream, per-agent memory
& reputation inspector):

| Option | Fit | Notes |
|---|---|---|
| **Dioxus LiveView on Axum** (chosen) | server-rendered RSX, interactions over WebSocket, **no WASM toolchain** in nix | component model + single-language server; can graduate to fullstack WASM later without redesign |
| Dioxus Fullstack (WASM) | same DX, richer client | needs wasm32 target + dx CLI in nix — heavier toolchain for a dashboard |
| Leptos | similar model | smaller ecosystem for WS-driven live UI |
| Axum + htmx | rock solid, minimal | not Rust-authored UI; fallback if LiveView friction appears |

The dashboard is a **consumer adapter**, not the core: it reads a
`WorldFeed` (SSE/JSON) exposed by the bot runtime and a small JSON query API.
While the real runner feed lands, a `MockWorldFeed` (driven by the society
roster, seeded) makes the dashboard demoable and testable offline.

Views (MVP):
1. **Roster** — agents online/offline now, per friend group (schedule-aware).
2. **Live feed** — chat lines + world events as they stream.
3. **Agent inspector** — persona, current goal/script/plan, memory view
   (ADR-004 lines, zoomable), Clef context-selection log (ADR-006),
   reputation ledger (ADR-005).

## Consequences
- Python side stays the source of truth; Rust touches only presentation.
- Rust static analysis matches the Python pipeline's comprehensiveness:
  `task dashboard:check` runs **fmt, clippy (pedantic, `-D warnings`), tests,
  cargo-audit (CVEs), unused-dependency check, and `cargo doc`**; workspace
  lints deny `unsafe_code`, `unwrap_used`, `expect_used`, `panic`, and
  `indexing_slicing` — the observer must never crash the loop it watches.
- `task dashboard:serve` runs it locally.
- If Dioxus LiveView proves unmaintained, fall back to Axum+htmx — the
  WorldFeed contract is the stable boundary either way.

Related: [[adr-000-hexagonal-architecture]], [[adr-005-society-groups-reputation]],
[[adr-006-clef-context-selector]]
