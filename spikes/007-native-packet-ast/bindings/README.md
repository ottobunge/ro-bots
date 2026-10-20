# Independent bounded AST bindings experiment

## Verdict: PARTIAL

A real Clang JSON AST can identify a local object, its header field assignment,
and a `sizeof` send argument by declaration identity without the failed textual
classifier. Useful coverage is nonzero, but deliberately narrow. This is not
production integration, generator approval, a real server-profile catalogue,
or whole-program C++ dataflow analysis.

## Executed results

| Measurement | Actual result |
|---|---:|
| Retained fresh physical C++ sources | 23 |
| Additional available prior sources | 7 |
| GCC compilation + execution successes | 29 / 30 |
| Fresh GCC stdout matches retained actual baseline | 23 / 23 |
| Real Clang frontend successes | 29 / 30 |
| Full AST semantic equality across two subprocesses | 29 / 29 successful cases |
| Expected unsafe cases, all candidates unresolved | 27 / 27 |
| Expected safe cases admitted | 1 / 2 |
| AST send candidates | 33: 1 FIXED_SIZEOF, 32 UNRESOLVED |
| Focused unittest methods | 10 passing |
| Frozen production inputs unchanged before/after | 185 / 185 |

The admitted case is `comments_strings_positive`: header 1, declaration-bound
`sizeof(PACKET_ZC_ONE)`, independent GCC stdout `1 66`. These are synthetic test
layouts, not server packet mappings. `ordinary_branch_positive` remains unresolved
because this policy does not analyze branches. All nine retained fresh failures
of the former classifier are unresolved here. The extra rereview source has
three send candidates and is one physical source, not three physical cases.

The sole compiler failure is the prior `owned/complete-header.cpp`, which requires
`config/core.hpp` and its original full-header include/profile closure. It is
reported as a compiler diagnostic, **not** counted as a parsed unsafe case or a
semantic-repeat success. That authority belongs to the separate compiler/profile
workstream. The old 71 production-generator metadata cases are not AST coverage
and were not rerun or relabeled by this experiment.

## Runnable commands

From `/home/otto/dev/ro-bots`:

```sh
nix develop --offline --no-write-lock-file path:./spikes/007-native-packet-ast/toolchain -c python3 spikes/007-native-packet-ast/bindings/resolve.py /home/otto/.hermes/cache/scratch/nmg-final/comments_strings_positive.cpp
nix develop --offline --no-write-lock-file path:./spikes/007-native-packet-ast/toolchain -c python3 spikes/007-native-packet-ast/bindings/test_bindings.py
nix develop --offline --no-write-lock-file path:./spikes/007-native-packet-ast/toolchain -c python3 spikes/007-native-packet-ast/bindings/run_retained.py
```

CLI accepts a C++ fixture path and emits JSON with source SHA, exact pinned
compiler command, AST semantic hash, send node/declaration IDs, object type,
identity-bound member-write evidence, alias/escape evidence, header constant,
framing decision and unresolved diagnostics. A compiler/AST error exits 2 and
preserves the diagnostic; unresolved candidates exit 0 but supply no admission.
Zero recognized candidates is no evidence of support. No caller compiler flags,
response files, plugins, production imports, installs or fallback classifier.

## Explicit admission bounds

* Only a direct top-level FunctionDecl body with a direct known `clif_send` call.
* Direct address of one nonstatic plain local aggregate value, initialized with
  a zero aggregate AST initializer. Its first unsigned-short `PacketType` field
  is bound by **FieldDecl ID**, not field spelling alone.
* Exactly one direct assignment of a literal or literal-initialized constexpr
  in uint16 range to that member before send. Assignment, send and sizeof bind
  the identical **VarDecl ID**; lambda ParmVarDecl IDs never borrow an outer value.
* Only explicitly whitelisted statement/initializer nodes are supported.
  Branches, lambdas, indirect sends, helper calls, object replacement, increments,
  unknown initializers, pointer/reference aliases and escapes remain unresolved.
* Parentheses and a bounded list of implicit cast kinds are stripped; explicit
  casts and unknown wrappers do not silently inherit support. No arbitrary
  arithmetic constant evaluator or alias/dataflow solver is claimed.
* The known synthetic sink has both a reviewed body SHA and an AST-shape SHA.
  The macro-mutated sink test demonstrates why source-body bytes alone are not
  sufficient. This is a **fixture-specific contract**, not approval of any real
  exceptional sender declaration. Binding is AST-derived; sink fingerprints
  restrict authority rather than supply textual binding inference.
* `FIXED_SIZEOF` is symbolic framing by identical local declaration. Numeric
  lengths are deliberately `null`: baseline GCC stdout is independent evidence,
  not injected into the resolver as a purported Clang layout result.

## Evidence and tests-first history

`run/reviews/native-ast-binding-feasibility.json` is the machine-readable report.
Its artifact directory is
`/home/otto/.hermes/cache/scratch/ast-binding-bj0_whhk`.
It contains real first/second complete Clang ASTs, per-run JSON, compiled GCC
binaries, GCC stdout/stderr and SHA256 entries. Semantic normalization renames
process-local hex IDs by first occurrence while preserving identity relationships;
it does not demand byte equality of AST addresses.

RED/GREEN logs are preserved under the report's `tdd_logs`. Tracer bullets were:
missing CLI admission → real local admission; missing lambda candidate → preserved
ParmVarDecl candidate denial; missing mutation/escape evidence → identity-bound
counts; unreviewed sink acceptance → denial; macro-mutated sink acceptance → AST
shape denial; missing full-AST repeat hash → semantic repeat evidence. The first
RED is an intentionally missing executable feature, not a fabricated AST result.
No failed assertion was loosened. Additional negative checks cover malformed AST,
real invalid-C++ diagnostics, and a missing compiler. Missing-compiler injection
changes only the dependency path for a negative test, never admission; malformed
AST is a rejection test, not accepted synthetic compiler proof.

## Remaining blockers

Full-TU/profile authority and real sender/layout extraction are unvalidated by
this independent fixture work. See the separate compiler-owned artifacts; no
new real `clif_send` exceptions are adopted here. Root runtime/client/packetdb,
old reports, native world, SQL, credentials and production generator remain
unchanged. This report authorizes no runtime migration. All execution uses the
already developed public-only offline Nix toolchain: Clang 21.1.8, GCC 16.2.0 and
Python 3.14.7. Authorizing record:
`run/reviews/native-ast-spike-authorization.json`.
