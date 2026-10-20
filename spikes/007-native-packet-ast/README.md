# 007: Native packet AST/hybrid feasibility

Authorization: `run/reviews/native-ast-spike-authorization.json`.
Standalone offline experiment; no production edits or world changes.
Rejected generator and all previous evidence remain unchanged.

| Workstream | Given / when / then | Main risk |
|---|---|---|
| compiler | Given immutable pinned source/build flags, when parsed by a Nix-managed compiler AST frontend, then actual sender declarations and profile provenance can be recovered without source surgery. | Compiler/profile compatibility |
| bindings | Given retained compiled C++ counterexamples, when AST declaration identity and a restricted mutation/escape policy are applied, then unsafe sends remain unresolved and an ordinary safe sender is distinguishable. | Unsound admission or zero useful coverage |

Shared toolchain copies only the public root nixpkgs lock into this tiny directory.
Use `nix develop --offline --no-write-lock-file path:./spikes/007-native-packet-ast/toolchain`.
Compiler and binding experiments have disjoint directories and reports.
An AST is not a complete C++ dataflow proof; uncertainty must remain explicit.

## Verdict: PARTIAL

The binding experiment denies all27 expected unsafe fixtures and admits1of2
expected safe fixtures. Numeric lengths and real-server sink authority are not
proved. The compiler experiment parses real emotion/name/sitting ASTs, but the
pristine source enables packet obfuscation whereas the installed package appends
undef directives to its custom header. Exact installed-profile equivalence fails.
Clang also rejects GCC-preprocessed full-TU output; diagnostics are preserved.

Parent reran3compiler+10binding tests and exercised freshClang emotion parsing,
allnine former failure fixtures (unresolved), and one safe fixture (admitted).
Verified44compiler+206binding artifacts and185 unchanged production inputs.
Evidence: `run/reviews/native-ast-parent-reconciliation.json`.
Read-only configured-source audit is complete. The reconstructed closure passed
fresh parent replay and independent bounded profile/layout/selected-AST review.
This does not approve sender semantics or the existing rejected generator.
Real emotion identity/header/send/sizeof tracing and real clif_send sink audit
now run in disjoint workstreams (`deleg_710856c6`); results are candidates only.
No production migration or game-world effects. See `native-ast-profile-replay-approved.json`.

