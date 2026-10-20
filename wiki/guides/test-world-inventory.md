---
title: Read-only test-world inventory
created: 2026-10-05
updated: 2026-10-05
type: guide
status: accepted
tags: [ops, testing]
---

# Read-only test-world inventory

Run from the project Nix development shell:

```sh
nix develop --offline -c task world:inventory
```

This extends the basic `world:inspect` listing with exact test-volume users and
selected container metadata. It does **not** implement or authorize the reset
executor described in [[adr-010-worlds-volumes-e2e]]. Acceptance remains in
[[goals-ledger]].

## Behavior

- Only exact read-only Docker `ls` / `inspect` command tuples are permitted.
  The project is `ro-bots-test`; the volume is `ro-bots-world-test`.
- Query both project-labelled containers and every user of the exact test volume.
  A foreign user must not disappear merely because its project label differs.
- Validate complete lowercase hexadecimal IDs before inspection and require the
  inspected identity to match. Bound each listing to 64 IDs; the union can have 128.
- Select only inspection metadata needed for identity/state/labels/mount checks.
  Do not request environment values. Output contains classifications, not raw
  foreign label values or source mount paths.
- Refuse malformed metadata, mismatching filters/mounts and differing observations.
  Two equal projected observations set `inventory_stable=true`; this is **not**
  an atomic snapshot, world lock, continuous observation or trusted ownership proof.
- Per-command engine timeout is 10 seconds. Inspect JSON parsing is capped at
  262,144 characters; this is not a hard cap on subprocess capture memory.
- Ordinary engine and strict decoding failures now use sanitized errors and exit 2;
  independent re-review logically closed WI-001. Successful inventory exits
  0 but always says `mutation_authorized=false`, including absent resources.

## Executed evidence

Parent executed 31 new inventory cases plus 90 existing task/isolation/seed safety
cases: **121 passed**. Scoped format/lint/types/complexity/security/dead-code/
duplicate-code gates passed. Those were the pre-repair scoped observations, not
the current combined checkpoint below.

Actual engine execution on 2026-10-05 returned no test volume, no selected test
containers and no volume users. No provisioning, shutdown, reset, SQL or seed
operation occurred. Existing-resource metadata and foreign-user behavior were
exercised with explicit test fixtures, not represented as live observations.

Evidence: `run/reviews/world-inventory-parent-verification.json`.
Independent `run/reviews/world-inventory-review.json` returned **passed=false**:
WI-001 reproduces invalid UTF-8 in captured stdout or stderr escaping the
sanitized CLI error boundary. No partial inventory or mutation authorization was
produced. Existing 121 scoped tests/gates and read-only allowlist probes passed,
but did not cover this defect. The first bounded decoding repair is now present;
real stdout/stderr RED→GREEN regressions and a parent rerun of **123 scoped tests**
passed. Independent defect-only `world-inventory-wi001-rereview.json` now records
`logical_defect_closed=true` and `scoped_defect_verification_passed=true`, with
33 inventory cases, 90 prior safety cases, scoped gates and independent real-byte
probes passing. That earlier report's **passed=false** retained missing snapshot
certification; it was not retrospectively promoted or edited.
The user subsequently granted explicit permission for combined verification.
New parent full gates passed **776 tests + 65 subtests / 93.97% coverage**, Rust
43 tests/six gates, and seven standalone spike cases. All 119 source fingerprints
matched before/after. Evidence: `run/reviews/authorized-combined-offline-checkpoint.json`.
Final `run/reviews/world-inventory-final-snapshot-review.json` now has
**passed=true** for the exact read-only inventory/error-handling scope. Its 121
fingerprints stayed unchanged and matched all 119 parent entries; parent checked
the old snapshot before later host-chat corrective edits. Earlier verification
gaps are closed for inventory only; no reset, SQL/account ownership, gameplay or
whole-repository approval is implied. Old reports remain unchanged.

## Remaining prerequisites

A locked executor still needs fresh, trusted world/container/network/database and
exact fixture-account ownership/offline evidence immediately before each mutation,
transactional failure handling and target readback. Labels and inventory data alone
are not that authority. All lifecycle/E2E entrypoints remain blocked.
