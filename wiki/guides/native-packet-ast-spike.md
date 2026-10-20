---
title: Native packet AST hybrid feasibility experiment
created: 2026-10-07
updated: 2026-10-07
type: guide
status: proposed
tags: [protocol, testing, ops]
---

# Authorized offline experiment, not runtime integration

After [[native-packet-manifest-review-blocker]], the user explicitly chose
**Proceed with the offline AST/hybrid experiment**. Exact scope is recorded in
`run/reviews/native-ast-spike-authorization.json`. See [[goals-ledger]] for the
remaining playable-world criteria; the rejected generator is still rejected.

The standalone experiment lives in `spikes/007-native-packet-ast/`.
It preserves production code, root pins, prior counterexamples and failed reviews.
It is not a third automatic repair and cannot launch bots or mutate world data.

## Separate feasibility questions

- **Compiler/profile:** can the approved immutable rAthena source/build environment
  produce useful AST identities for actual sender functions without source surgery?
- **Bindings:** can a bounded AST policy distinguish safe local sends from retained
  lambda, parenthesized-write, helper and alias counterexamples, leaving uncertainty
  unresolved rather than making false fixed claims?

`deleg_241d374a` runs these in disjoint `compiler/` and `bindings/` directories.
Synthetic fixture results are not actual-sender coverage. AST extraction alone is
not mutation/dataflow proof, nor does denying all candidates establish useful coverage.

## Verified tool prerequisite

The tiny public-only toolchain flake copies the existing root nixpkgs lock,
revision `a7868a727837f3c09cee2ce0ca671c76b1589fed`; root inputs are unchanged.
Parent executed its offline shell successfully: Clang21.1.8, GCC16.2.0, Python3.14.7.
GCC remains the server-layout authority. A different AST frontend must demonstrate
its parsing/profile assumptions rather than silently replace the server compiler.
185 production/gate inputs were hash-verified and frozen before dispatch.

## Acceptance and limits

Required evidence: real commands/AST output, exercised CLI, preserved RED/GREEN,
retained negative cases, supported/unsupported counts, artifact hashes and exact
blocking command/header/source authority for any partial verdict. The parent will
verify returned artifacts and replay commands before summarizing feasibility.
No production migration or reviewed-exception admission follows automatically.

## Measured outcome: PARTIAL

Parent verifies44 compiler and206 binding artifacts and185 unchanged production
inputs; reruns3compiler and10binding unit methods successfully. FreshClang parsing
of real `clif_emotion` succeeds. FreshCLI replay denies allnine former failing
fixtures and admits the supported safe fixture.

Across30 retained CPPsources,27 expected unsafe cases remain unresolved; only1of2
expected safe cases is admitted. The ordinary branch stays unsupported. All23
fresh GCC oracle comparisons match; numeric lengths remain unknown and the sink
contract is synthetic, not real-server authority.

Exact-profile blocker: the original source enables packet obfuscation, whereas
installed `apply-runtime-root.py` lines32–33 append undef directives to
`src/custom/defines_post.hpp`. Pinned source plus recorded map flags therefore
is not the full configured build closure. This is not permission for arbitrary
-U/forced-header overrides. Clang also fails on GCC-preprocessed full-TU output;
its own preprocessing parses three real senders but does not waive profile drift.

Read-only audit `deleg_f36704d3` identifies the actual configured-source authority
and available artifacts before any reconstruction. Parent reconciliation report:
`run/reviews/native-ast-parent-reconciliation.json`. Both workstream PARTIAL reports,
profile guard failure and original generator rejections remain preserved.

## Configured-source audit and bounded replay

Read-only audit completes: no built custom header/source archive is retained in the
inspected package output. The installed derivation and immutable transform explain
three source/header changes. Parent verifies the transform/header/profile-script,
derivation and retained evidence hashes, plus predicted appended-header bytes.

Clarification: `src/config/packets.hpp` defines obfuscation; the original custom
header is empty customization, and the installed patch appends late undefinitions.
The upstream source profile is different, not the installed server's configuration.

Within the authorized offline experiment, parent scopes a separate public-source
replay: extract retained transformed Core and runtime header, replay the exact
hashed custom append, prove only these three source paths differ, and execute
profile/layout oracles plus selected sender ASTs. No command-line profile override,
production changes, package rebuild, server execution or binary-equivalence claim.

`deleg_3a238a19` owns only new `profile-replay/` code/tests and scratch closure.
Evidence: `native-ast-configured-source-audit.json`, `native-ast-profile-replay-scope.json`.
The reconstructed-profile results remain pending and cannot approve the old generator.

## Profile replay reproduced; independent review pending

The separate reconstructed public closure passes the bounded profile/layout/AST
experiment. Parent reruns the realCLI (exit0) and four unit methods, checks all3206
copied files against the inventory, and verifies exactly two modified files plus
one added runtime header. Source fingerprint matches the author's independent run.

All8 GCC/Clang × four-role profile oracles match installed JSON. Executed emotion
andSTOPMOVE IDs/sizes/offsets and actor FD/FE/FF sizes agree between both compilers.
The original upstream profile failure remains a negative control. GCC checks the
fullclif.cpp; Clang's own preprocessing yields emotion/name/sitting ASTs under the
reconstructed no-obfuscation profile. No sender dataflow/framing admission follows.

Parent verifies106 fresh artifacts and189 frozen critical inputs. Fresh replay
reads its exact returned output root, not the shared latest.json pointer; prior
pointer bytes and original results are preserved. `deleg_3d442bb5` performs fresh
independent review. Evidence: `native-ast-profile-replay.json` and
`native-ast-profile-replay-parent.json`. Binary equivalence, old generator approval,
complete catalogue, runtime and gameplay remain unclaimed.

## Bounded prerequisite approved; real sender/sink proof underway

Independent review passes ONLY the reconstructed profile/layout/selected-AST scope.
Parent verifies linked artifact hashes,44 fresh commands,12 precompiler denial cases,
12 real guard probes and189 stable critical inputs. Evidence:
`native-ast-profile-replay-independent-review.json`, `native-ast-profile-replay-approved.json`.

Next, `deleg_710856c6` runs disjoint experiments: a TDD real-sender identity/header/
send/sizeof tracer starting with emotion, and a read-only audit of actual clif_send
buffer/length handling and helper dependencies. Candidate output is not sender
semantic admission, and a source-body hash alone cannot approve the real sink.

Only new `sender-proof/` code and scratch/audit artifacts are allowed. Existing
profile/compiler/binding code, rejected generator and runtime stay unchanged.
Scope recorded in `native-ast-real-sender-scope.json`; all gameplay criteria remain open.

## First real sender candidate and conditional sink audit

The tracer returns an emotion identity/layout candidate: same-invocation object,
header FieldDecl/constant initializer, send-address and sizeof joins; fresh GCC
measures ID192/size7/offsets0,2,6. Parent verifies158 artifacts with streaming hashes,
reruns4tests and the actual candidate CLI. 27 owned compiled structural negatives
remain unresolved; 30 previous cases are retained, not relabelled numeric proof.
Name and sitting remain unresolved; the candidate admits no runtime framing.

The independent sink audit inventories8 successful compiler commands and12 direct
memcpy sites in active bodies. It supports only conditional copy/queue-request
identity for AREA/recursiveSELF—not delivery, counts, general purity or adoption.
Seven dependency groups remain, including a narrow variadic pointer qualification
question. A successful compile cannot settle that language contract.

`deleg_6b515863` now independently reviews the candidate/audit and investigates that
one variadic contract from primary specifications. No further parser patch or
server change is authorized by these results. Evidence: `native-ast-real-sender-parent.json`,
`native-ast-real-sender-proof.json`, `native-ast-real-sink-audit.json`.

## Recognizer rejected; narrow source-contract issue identified

Independent review verifies the exact pinned emotion identity/layout facts and
factual assumption-limited sink audit, but rejects the general tracer: unchecked
extra send arguments can mutate the header, mutable globals are treated as
constants, and unsupported casts are admitted. The three compiled counterexamples
and prior positives remain preserved; the recognizer is not approved.

Separate primary-specification review identifies pointer type/qualification
mismatches in the AREA variadic callback. This is a standards-text assessment,
not an observed runtime-failure cause; successful GCC assembly does not establish
language-defined retrieval. No callback patch or sink adoption has occurred.

Parent verifies82 review artifacts, official specification snapshots and probe
source/assembly hashes;189 critical inputs remain unchanged. Implementation pauses
for a scope decision on tracer fixes and a separate scratch-only callback correction
experiment. Evidence: `native-ast-sender-review-blocker.json`,
`native-ast-real-sender-independent-review.json`, `native-ast-varargs-contract.json`.

## Freshly authorized scoped continuation

User explicitly chooses **Authorize tracer fixes and the offline callback experiment**.
`native-ast-tracer-callback-renewed-scope.json` preserves that decision and boundaries.
`deleg_5850c4a0` runs two disjoint workstreams: only L1/L2/L3 TDD fixes in the new
standalone tracer, and a scratch-source callback qualification experiment.

The callback trial may change only the audited pointer declarations/retrievals in
its copied clif.cpp and validate active types, full-TU syntax and a defined local
bridge probe. It may not patch the baseline, installed package or production source,
rebuild/deploy server roles, change pins, adopt the sink or touch world data.
Old rejected generator and prior failure reports remain unchanged; results pending.

Parent replay now passes; detailed outcome and independent review boundary are
tracked in [[native-packet-tracer-callback-trial]]. No runtime or world admission.







