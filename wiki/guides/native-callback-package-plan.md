---
title: Staged callback-qualified server variant
created: 2026-10-07
updated: 2026-10-07
type: guide
status: proposed
tags: [protocol, rathena, testing, ops]
---

# Proposed next implementation boundary

See [[native-packet-sink-closure]], [[native-packet-tracer-callback-trial]] and
[[goals-ledger]]. The original callback qualification mismatch is not fixed in
the installed package. The scratch correction is separately validated; allocator,
session and recipient lifetime conclusions remain conditional. Further recursive
callee audits are not an implementation path by themselves.

## Observed package authority

Parent read the actual `nix/playable-world/flake.nix` and
`apply-runtime-root.py`, not a guessed build route. The package already fetches
pinned public rAthena source, applies the guarded runtime-root transformation,
records configured role profiles/recipes, and builds all three role executables.
The current transformation changes Core/runtime-root/custom defines, not clif.cpp.
No packaging or running-world changes have been made by this planning step.

## Stage A — offline package variant (requires explicit new authorization)

1. Reuse the existing tiny public playable-world flake/lock and public helper
   allowlist in a separately named variant. Preserve the canonical package, all
   old evidence, upstream revision, input pin, runtime-root behavior and profiles.
   Never import the whole checkout into Nix.
2. Add only the four already-reviewed pointer-local/retrieval substitutions in
   clif_send_sub. Guard original clif.cpp bytes and exact anchors; fail on drift.
   No allocator, lifetime, gameplay, packet-ID, obfuscation or ruleset changes.
3. Use RED→GREEN tests for pristine mismatch, exact correction, drift/refusal,
   preserved caller/remaining source, and unchanged Core startup tail.
4. Build the offline variant. Verify the actual configured source differences,
   GCC/Clang profile/layout/type evidence, generated recipes and resulting role
   artifacts. New source fingerprints and invocation-local caller identities are
   required: pristine AST IDs cannot be reused as variant admission evidence.
5. Exercise only source-proven early diagnostics/refusals; no SQL/socket/timer/
   server initialization. Independently review patch, package and evidence.
6. End Stage A at offline package approval. No image engine import, service
   replacement/restart, runtime packet registration or world activation follows.

## Stage B — framing/adoption and isolated-world validation (not authorized)

Choose a bounded source contract with explicit allocator/session/lifetime
conditions, and preserve negative/corruption/exhaustion limits. Conditional
source evidence is not a generic memory-safety theorem. Any contract narrowing
needs explicit review, not a silent waiver of existing obligations.

Fresh variant source/compiler evidence must then support the required catalogue
and separately reviewed runtime migration. Protect login/char/PIN/outgoing shuffle
and previously unresolved entries; do not adopt the rejected original generator.
Only after package/contract/catalogue/runtime reviews and fresh owned-world
preflight should isolated test-world activation and native copy/receipt/gameplay
verification be considered. Debug, production and human sessions remain protected.

## Current state

Stage A is now explicitly authorized by the user's choice **Authorize the offline
callback-qualified package variant**, recorded in
`native-callback-qualified-package-scope.json`. `deleg_293759b7` owns only a new
public tiny-flake package directory, guarded package tests and offline evidence.
The canonical five-file package, input lock/profile/runtime-root behavior and
existing frozen dependencies remain protected. The offline Nix build exited0;
parent read back the exact store output and three executable role ELF signatures
and hashes (`native-callback-qualified-package-build-receipt.json`). Source/profile/
diagnostic checks and independent review are still pending; this is not approval.

The author completed26 guarded tests and recorded9 source-proven early checks.
Parent now verifies77 evidence hashes,23 installed files and all3206 reconstructed
public source files; only clif.cpp differs from baseline and its public closure
matches the reviewed qualified trial. The manifest's10 generated Makefiles are
explicitly accounted for. Profiles/role recipes/Core/runtime-root artifacts remain
byte-identical. Actual NAR hashing matches the reported package identity.

Parent reruns26 tests and clean Black/Ruff/strict mypy. Full configured gate passes
3681 physical cases plus65 subtests at95% printed coverage; audit reports no known
vulnerabilities. One dependency deprecation warning is retained. All206 completed
review inputs remain stable. `deleg_a21c3d67` independently reviews the offline
package; evidence is `native-callback-qualified-package-parent-gate.json`.

Stage B remains unapproved: no deployment, service restart, image import, runtime
packet registration, server initialization or world changes. All six milestones
remain open; no damage/XP/loot or playing population is claimed.

Read-only receiver inventory and the proposed offline Stage B1 boundary are now
tracked in [[native-qualified-catalogue-readiness]]. Stage A does not authorize
that implementation, contract adoption or any runtime migration.

## Independent Stage A approval

Review `e9c4e6278e62962e46f6738b4f4a3b6405aecdf4725f67b4af8c4f6be5cdd6fe`
passes only the offline package. Parent verifies82 reviewer artifacts/206 frozen
inputs and records `native-callback-qualified-package-approved.json`. All26 tests,
8 fresh refusal cases and9 traced early checks passed; no runtime initialization.

Compiler evidence is explicitly CPP/profile/frontend/layout scoped. The saved
map recipe selects the NPC custom rule, not clif's complete CXX backend envelope.
CFLAGS mentioning fast-math does not establish clif CXXFLAGS. No binary-equivalence
or generic semantic guarantee is claimed. Stage B1 has a separate offline-only
implementation grant; deployment/runtime/world stages remain excluded.
