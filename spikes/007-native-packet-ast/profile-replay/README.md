# Offline installed-profile replay

## Verdict: VALIDATED — bounded profile/layout/selected-AST scope only

This standalone CLI constructs a **reviewed reconstructed public configured closure**, not recovered exact binary-build source. It copies only the pinned public `src/` and `3rdparty/` inventory into a newly created private scratch root, extracts retained transformed Core and the immutable runtime header, and appends the exact verified late-custom-header undefinitions. It never executes the packaging patch script, production classifier, server binaries, generator or runtime.

## Run

From `/home/otto/dev/ro-bots`:

```sh
nix develop --offline --no-write-lock-file path:./spikes/007-native-packet-ast/toolchain -c env TMPDIR=/home/otto/.hermes/cache/scratch python3 spikes/007-native-packet-ast/profile-replay/replay.py
nix develop --offline --no-write-lock-file path:./spikes/007-native-packet-ast/toolchain -c env TMPDIR=/home/otto/.hermes/cache/scratch python3 spikes/007-native-packet-ast/profile-replay/test_replay.py
```

The CLI refuses existing destinations, checks immutable authority hashes and exact retained role flags before compilers, inventories all copied public files, and admits only these source differences:

- modified `src/common/core.cpp` — retained installed `core-start.cpp` bytes;
- added `src/common/runtime-root.hpp` — immutable retained header bytes;
- modified `src/custom/defines_post.hpp` — exact transform literal appended.

3205 original public files become 3206. `clif.cpp`, native packet headers, and every other copied file remain byte-identical. Inventory/source-closure hashes and executed command/stdout/stderr hashes are retained in private output; `latest.json` points at that actual result. The final review is `run/reviews/native-ast-profile-replay.json`.

## Measured results

- GCC 16.2.0 and Clang 21.1.8: all four retained roles (`common`, `login`, `char`, `map`) execute the unchanged retained oracle and match installed JSON: **8/8**.
- Separate guard and macro dumps reject both obfuscation macros and renewal/RE/ZERO families, including numeric family macros. PIN support and MAIN20180704 are checked.
- Original immutable upstream source fails the unchanged installed-profile oracle with both compilers: preserved negative controls, not overridden macros.
- GCC-primary layout oracle, independently repeated with Clang: emotion ID192, size7, offsets0/2/6; STOPMOVE ID136, size10, offsets0/2/6/8. FD walking110, FE spawn103, FF idle104.
- GCC syntax-checks the full unchanged `clif.cpp`. Clang preprocesses/parses its own unchanged full TU for each filtered AST: emotion54 nodes, name986 nodes, sitting79 nodes; each includes one actual function definition. No sender identity/dataflow admission is claimed.
- Measured dependency files: GCC468 paths, each Clang AST484 paths; source dependencies match the inventory, and every path resolves to the public scratch closure or Nix store. No host `/usr/include` fallback.
- Four genuine feature-missing RED stages and their GREEN logs retained; final four-test suite passed. The actual CLI separately exited0.
- All185 frozen production files and all51 previous compiler/bindings/toolchain files remained unchanged.

## Retained issues and boundaries

Two failed oracle attempts remain in scratch with diagnostics: a C++ assertion incorrectly referred to absent RE_NUM/ZERO_NUM identifiers; it was replaced with explicit macro-absence checks. A second assertion transposed idle/spawn names; pinned `packets_struct.hpp` enum definitions established FF=idle104 and FE=spawn103. Neither fix changed immutable source, expected per-ID sizes or retained profile body.

Commands use exact reduced retained role flags and explicit already-reviewed include roots. These are not the fully expanded historical map recipe or compiler-wrapper environment; this experiment does not assert historical PCRE substitution recovery or binary equivalence. The older GCC-preprocessed Clang bf16 failure is preserved unchanged, not token-repaired.

No complete catalogue, generator acceptance, production migration, live sink exception adoption, gameplay acceptance or world effects. The independently rejected production generator remains rejected. Parent review and replay are required before any further continuation.
