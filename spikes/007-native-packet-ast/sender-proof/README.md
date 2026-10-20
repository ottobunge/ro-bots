# Standalone real sender proof (candidate only)

## Verdict: PARTIAL

The fresh full Clang 21.1.8 translation unit binds the actual clif_emotion local declaration, packetType FieldDecl, HEADER_ZC_EMOTION initializer, send address and sizeof operand by IDs from ONE compiler invocation. Fresh GCC 16.2 execution measures header 192, size 7, offsets 0/2/6 under the independently reviewed MAIN20180704 pre-re source/profile closure. No production/catalogue/runtime integration.

```sh
nix develop --offline --no-write-lock-file path:./spikes/007-native-packet-ast/toolchain -c python3 spikes/007-native-packet-ast/sender-proof/cli.py clif_emotion
nix develop --offline --no-write-lock-file path:./spikes/007-native-packet-ast/toolchain -c python3 -m unittest discover -s spikes/007-native-packet-ast/sender-proof -v
nix develop --offline --no-write-lock-file path:./spikes/007-native-packet-ast/toolchain -c python3 spikes/007-native-packet-ast/sender-proof/run_proof.py
```

CLI reads exact hash-pinned scratch artifacts, validates public source inventory and denies changed profile/authority/layout/AST. It never opens connections. Artifacts are NOT self-contained distribution: scratch preservation is required. The exact compiler command and acquired/extracted AST artifacts are retained; acquisition/extraction scripts are not included in the report artifact list. The full dump is 2.12GB and remains unchanged. Object/header/field IDs originate in the full dump, not stitched filtered ASTs.

Bounded grammar: first fresh zero aggregate, direct scalar field assignments, one constant header assignment and one final top-level send. Unknown calls, aliases, reset, lambdas, branches, reassignment, unevaluated payloads and post-send writes are unresolved. No CFG solver. Numeric test dictionaries are trusted internal unit-test oracles, not a caller-facing measurement API: floats, bools, empty offsets and malformed metadata are outside that API's supported scope. Only the report's fresh GCC execution supplies real measurement authority; the CLI accepts no caller metadata and its authority/AST/layout pins are unchanged. Every final send argument is inspected for unsupported expressions, helpers, mutation and packet aliases; headers require immutable integral const/constexpr declarations, and casts are validated by kind, type and context. The exact pinned emotion enum IntegralCast and address-to-const-void sink conversion remain supported. L1/L2/L3 each have separate compiled RED→GREEN logs in the new repair report. Prior failed reports remain unchanged; this repair is not independent approval.

27 owned compiled negative fixtures and 30 retained prior C++ cases were exercised. Retained cases without numeric joins are not counted as structural numeric coverage. clif_name and clif_sitting remain unresolved. Source coverage is exactly three selected functions, not all 517 sites.

## Second and last renewed-prototype repair (L4)

Before header lookup, metadata joins or field transfer, the recognizer requires compiler AST evidence of a plain, standard-layout, trivial scalar aggregate: no unions, bases, anonymous members, bitfields, nested/array/reference/volatile representations or unsupported attributes. Only ordinary integral fields are supported. Record `PackedAttr` and pragma-pack `MaxFieldAlignmentAttr` remain allowed; packing does not make these ordinary fields overlap. The header must desugar to `short` or `unsigned short`, whose two-byte representation is separately compiler-checked on the pinned target, not inferred from an alias spelling. This is not a general record-layout solver or a name whitelist.

The L4 regression compiles and executes an owned union witness using a defined `memcpy` byte observation: GCC still reports header constant 1, size 4, offsets 0/0, but observes transmitted header 2. Genuine failing/passing tests and fresh replay evidence are retained in `run/reviews/native-ast-real-sender-record-shape-repair.json`. Unsupported record shapes fail before metadata even when supplied internal layout evidence. The previous ten test methods remain byte-preserved; added compiled guards retain signed/unsigned short packed positive controls. Old evidence is preserved, not overwritten. This is repair cycle 2 of 2, self-verification only; parent replay and a fresh independent review must decide approval. No third automatic repair is authorized.

## Explicit bounded cleanup (not a reset of the exhausted repair budget)

The separate user authorization permits one cleanup and fresh review. Field-level `PackedAttr` now fails the record-shape guard before header lookup or metadata, both with and without a real GCC measurement. Record-level packing remains supported. A new compiled test records the genuine RED→GREEN transition; its defined byte observation still sends header 1 correctly (size 6, offsets 0/2), so this is a supported-grammar discrepancy, not a false-header exploit.

The standalone Python files are Black-formatted and carry typed known measurement/result state; heterogeneous Clang JSON uses an explicit node alias. Existing fourteen test bodies/assertions are preserved modulo formatting and type-only expressions, verified by normalized Python AST comparison. The new report `run/reviews/native-ast-real-sender-explicit-cleanup.json` records quality diagnostics by kind and metrics, remaining unwaived debt, fresh compiled controls, and preserved evidence hashes. Self-verification is not independent approval; any remaining quality regression keeps the cleanup verdict false. Do not rerun `run_proof.py` against historical evidence.

Sink contract UNREVIEWED; sender semantic admission and runtime admission remain false. All milestones and combat/XP/loot acceptance remain open. Parent replay and independent review are required before any further decision. If that review rejects this explicitly authorized attempt, stop and escalate; no additional cleanup is authorized.

## Separately authorized quality-only refactoring

The later explicit authorization permits coherent helper extraction and equivalent
test-style changes, not another behavior repair or a reset of automatic cycles.
The tracer separates send/object binding, record storage, header resolution, GCC
layout joins, final-argument checks, initialization and assignment validation.
Private unresolved outcomes preserve the first failure reason and metadata already
established at that point. Public `trace`/`walk` contracts and supported grammar
remain unchanged.

The fifteen unittest scenarios remain discoverable with bare toolchain Python;
lowercase names and plain assertions do not require pytest. Assertions require
normal Python execution (not `python -O`). Normalized whole-test-body comparisons
include the original fixture strings, loops, conditions, expected outputs and
diagnostic messages, rather than just counting test methods.

`run/reviews/native-ast-real-sender-quality-refactor.json` records the original
67 Ruff diagnostics and clean final Black/Ruff/strict-mypy checks, fresh Clang/GCC
replays of all twenty retained fixtures, whole-result before/after comparisons on
the same invocation-local AST, and the retained real emotion CLI candidate.
Historical evidence is preserved; do not rerun `run_proof.py` to update it.
These are self-verification results only. Parent verification and a fresh
independent review remain required; sink/runtime/milestone admission is unchanged.
