---
title: ADR-009: Character builds and item cognition
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [decision-model, architecture]
---

# ADR-009: Character builds and item cognition

## Decision
Each agent assigns a **Build** to every character it creates — the plan of
what the character will become.

- `Build` (domain): target class/job path (constrained by the persona's
  playstyle — e.g. `healer` → Acolyte→Priest line), stat allocation plan,
  target skill list, target equipment per slot, and milestone levels.
- **Builds are authored by the agent**: at character creation (and at
  milestone reviews), Clef receives the persona (playstyle/attitude), the
  class options allowed for that playstyle, and the item/skill catalog, and
  answers `choice` questions (class path, stat emphasis) + `score`
  questions (which equipment goals matter). A solo grinder builds differently
  from a clique healer.
- **Mechanics are pre-calculated, never modeled**: a `MechanicsPort`
  (adapter over rAthena item_db/skill_db, parsed from the repo's YAML) turns
  an item/skill into typed numbers — stats, effects, equip requirements,
  market price tiers. Agents see a **normalized digest** ("+4 STR, lvl req
  45, sells ~2k") without doing any math themselves.
- **Item decisions via Clef**: when the bot loots/buys an item, the decision
  request includes the digests of the new item, currently equipped items for
  that slot, and the build's equipment goals; Clef answers a `choice`
  question `item_action`: equip / store-for-build / sell / discard — with
  the pre-calculated comparisons in-state so one forward pass decides.
- The build lives on the agent (memory-adjacent, part of persona state),
  and its progress (equip goals met, skills learned) is an experience note
  stream feeding ADR-004 memory and ADR-006 selection.

## Consequences
- Agents get "a good notion of the rules and items" from curated digests +
  pre-computed comparisons, not from reasoning over raw databases — fast,
  deterministic, and testable.
- The `MechanicsPort` isolates rAthena data formats; a stub feeds tests and
  the mock dashboard.

Related: [[adr-005-society-groups-reputation]], [[adr-004-isolated-agents-optchat-memory]],
[[adr-001-event-driven-brain]]
