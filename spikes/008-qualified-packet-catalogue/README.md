# 008 — Qualified packet candidate catalogue

## Scope

User-authorized offline contract/catalogue implementation, recorded in
`run/reviews/native-qualified-catalogue-implementation-scope.json`.
This is separate from the rejected original generator and its exhausted repairs.

Initial tranche: common/map packet declaration layouts under the actual map
profile of the separately built callback-qualified package. It does not replace
login/char/PIN/outgoing handling or establish complete wire/sender coverage.

## Two disjoint streams

- `contract.py`, `test_contract.py`, `CONTRACT.md`: strict typed provenance,
  profile/count/conflict validation and explicitly undischarged preconditions.
- `compiler_catalogue.py`, `test_compiler_catalogue.py`, `COMPILER.md`: actual
  active declaration discovery and fresh GCC/Clang measurements.
- `interface.json`: parent-owned interchange contract. Neither stream may change
  the other's files. Parent integration/replay and fresh review follow completion.

## Evidence boundaries

- Measured sizeof/alignment/offsets are **layout facts**, not wire lengths.
- Conventional header-name associations are **candidates**, not sender bindings.
- Invocation-local address/sizeof identities do not establish all header transfer
  or queue/lifetime behavior. Never join AST declaration IDs across invocations.
- Allocator, session and recipient-lifetime preconditions stay **undischarged**.
- Raw helpers, variable-size forms, aliases and unsupported measurements remain
  explicit unresolved/manual-review cases. No silent drops or guessed lengths.
- `sink_admission` and `runtime_admission` must remain false.

## Authority

Use the actual immutable callback-qualified package and its installed profiles,
recipes, source manifest and known public source fingerprint. The legacy runtime
macro dictionary is not authority; it differs on obfuscation flag presence.
No caller-supplied flags, response files, forced headers or plugins are permitted.
Hash identity alone does not authorize compiler effects.

## Verification

Each stream uses vertical RED→GREEN tests and unchanged Black/Ruff/strict-mypy
settings. Synthetic unit fixtures must be labelled and never published as compiler
observations. Real compilation failures and unmeasured records survive in evidence.
Coverage counts must account for every discovered record within declared scope.

## Current status

The frozen bounded offline common/map layout producer and non-admitting validator
are independently approved. Evidence:
`run/reviews/native-qualified-catalogue-approved.json` and final review
`216bae47f108122865ce506a364056c9a35b0396a025ac009317e6f77b227fcf`.

- 632 scope-qualified declarations,631 spellings,477 conventional header
  candidates and94 flexible tails retained;622 layout-only and10 manual rows.
- 78 scoped tests,54 fresh independent API/CLI probes and all five-file quality
  checks pass. Parent full gate:3681 physical+65 subtests/95%, audit0; the final
  reviewer reads/hashes that evidence but does not rerun the full root suite.
- Parent verifies252 reviewer-artifact hashes and268 frozen inputs before these
  post-approval documentation updates. Code/interface/tests are unchanged here.

Initial and repair1 rejected snapshots remain documented in their original
reports; both automatic NEWB1 repair cycles are used, with no historical budget
reset. Conventional header association and layout are not transmitted framing.
All six canonical conditions stay UNDISCHARGED; compiler-execution authentication,
sink admission and runtime admission stay false. No packet registration, package
activation, server/world/SQL/model changes or full-milestone closure follow.
Sender/framing and receiver migration policy are a separately scoped next stage.
