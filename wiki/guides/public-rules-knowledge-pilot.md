---
title: Public rules knowledge pilot
created: 2026-10-07
updated: 2026-10-07
type: guide
status: proposed
tags: [rathena, decision-model, llm, testing]
---

# Public rules knowledge pilot

This is a working **offline lookup**, not full iRO Wiki access or live bot wiring.
It is separate from private [[adr-004-isolated-agents-optchat-memory]] and from the
mechanical/current-state authority in [[native-mechanics-and-encounter-context]].

## Implemented artifact

- `src/robots/adapters/rules_knowledge.py`: explicit catalog loading and selection.
- `knowledge/iro-rules-seed.json`: four short advisory stats cards, two per ruleset.
- `tests/test_rules_knowledge.py`: 28 passing parent-tested cases.
- `run/reviews/playing-mvp-rules-knowledge-pilot.json`: source snapshots, physical
  vertical RED/GREEN evidence and artifact hashes.
- `run/reviews/playing-mvp-rules-knowledge-parent-gate.json`: parent verification.

`RulesKnowledge.load(path).select(ruleset)` selects only the matching `pre-re` or
`renewal` cards. Topics without seed content, including skills/equipment, return
no advice. `serialize_cards` accounts for canonical UTF-8 JSON including source
provenance and the advisory flags. The real default lookup emitted 1,120 bytes
for pre-Renewal and 1,128 for Renewal; both are below the 2,048-byte budget.

The loader rejects duplicate JSON keys/card IDs, unsupported schema versions,
unrecognized/mismatched source metadata and exceeded input/card/string bounds.
Card/count limits are separate from byte limits. Empty selection is no advisory
payload; explicitly serializing it produces `[]`, not a zero-byte JSON array.

## Trust boundary

Every returned card is labelled `authority=advice`, `mechanically_verified=false`
and `private_context=false`. The adapter fetches nothing, creates no providers,
performs no native actions and appends no experiences. Public advice does not
establish actual stats, learned skill levels, equipment or allocation legality.

The checked source snapshots are iRO Wiki Stats revision 86935 and Classic Stats
revision 23836, fetched on 2026-10-07; their content hashes are retained in the
seed and report. Source provenance identifies the supporting pages, not semantic
verification of arbitrary edited card text. Freeze/review the exact catalog
before future runtime integration. No full articles, tables, images or raw HTML
are shipped with this pilot, and no bulk mirroring/licensing assurance is made.

## Verification and remaining work

The parent reran all 28 tests and scoped Black, Ruff and strict mypy, and executed
both real lookup paths. It also checked the author RED/GREEN XML and source/seed
hashes. Independent review passed 28 regressions and eight fresh probes on eight
unchanged frozen inputs; physical evidence hashes and XML were checked. Receipt:
`run/reviews/playing-mvp-rules-knowledge-approved.json`. The reviewer's source-only
mypy invocation does not replace the parent's full strict checks on both owned
files or the pending whole-tree gate.

The pilot is **not wired into Clef, LLM prompts or live private memories**. Later
integration must preserve the ruleset and source labels, impose an explicit
context budget, treat guide text as data/advice, and retain pinned MechanicsPort
validation before effects. This does not satisfy all of criterion 10 or close any
milestone in [[goals-ledger]].
