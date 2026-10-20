# Compiler/profile feasibility — PARTIAL

Standalone offline experiment, not a repair or approval of the existing generator.
No production or immutable source files were edited. No runtime/compiler change,
native game, SQL, model, container, network startup, or dependency installation.

## What was actually measured

- Trusted installed map flags and include-authority helper were read from
  `scripts/generate_native_packet_manifest.py`, unchanged. Its textual classifier
  was not called. Source pin is `e985006171d2eb320ee512a653f4c83aea3d81b6`.
- GCC 16.2.0 preprocessed the entire original `src/map/clif.cpp`; GCC syntax-check
  of that unchanged preprocessed TU succeeded.
- Clang 21.1.8 **cannot parse the GCC-preprocessed TU**: GCC-selected libstdc++
  branches contain the unsupported `0.0bf16` suffix and GCC-only type builtins.
  Exact diagnostics and command remain in `clang-gcc-full-tu.*` / `commands.json`.
- Clang separately preprocessed and parsed the complete original TU successfully,
  with its own driver/header branches. Filtered compiler-generated JSON retains
  actual `clif_emotion` (line 9412), `clif_name` (line 9928), and `clif_sitting`
  (line 5329) definitions, declaration IDs, references, call arguments/types,
  ranges, and sizeof expression/type nodes. IDs are invocation-local.
- **Exact installed profile verification failed.** Both original-source frontends
  define `PACKET_OBFUSCATION` and `PACKET_OBFUSCATION_WARN`; installed immutable
  `profiles.json` says false. Installed `apply-runtime-root.py` lines 32–33 append
  undef directives to `src/custom/defines_post.hpp` during the package build.
  The original immutable source plus map flags is therefore not the complete
  installed package's configured header closure. The guarded anchor compilation
  failed; its executable was not run and no layout sizes are claimed here.
- MAIN20180704 / PRERE / no RE / no ZERO / no RENEWAL agree between both
  preprocessors. Actual macro dumps, complete driver options and dependency hashes
  are retained. This does **not** waive the obfuscation mismatch.

## Reproduce

From `/home/otto/dev/ro-bots`, enter only the tiny public pinned flake:

```sh
nix develop --offline --no-write-lock-file path:./spikes/007-native-packet-ast/toolchain
python3 spikes/007-native-packet-ast/compiler/test_sender_ast.py
python3 spikes/007-native-packet-ast/compiler/sender_ast.py clif_emotion
python3 spikes/007-native-packet-ast/compiler/sender_ast.py clif_name
python3 spikes/007-native-packet-ast/compiler/sender_ast.py clif_sitting
```

`commands.json` contains exact argv arrays, compiler exits, original paths, trusted
flags, and source include paths. To rerun one compiler step inside that shell:

```sh
python3 -c 'import json,subprocess; j=json.load(open("spikes/007-native-packet-ast/compiler/commands.json")); s=next(s for s in j["steps"] if s["name"]=="clang-original-emotion"); raise SystemExit(subprocess.run(s["command"]).returncode)' > /home/otto/.hermes/cache/scratch/reproduced-emotion-ast.json
```

Replace the named step for name/sitting or the failing GCC-preprocessed route.
The AST display CLI reads retained physical compiler artifacts; it is not a new
compiler trust/admission pipeline. Three subprocess unittest cases pass; each
new behavior has retained RED then GREEN logs. Wrong-profile and missing-AST
cases fail closed. No synthetic compiler JSON was created.

## Verdict: PARTIAL

Real unchanged full-TU AST extraction for the selected three senders works with
Clang's own preprocessing. Exact installed no-obfuscation build identity is
**not verified**. GCC-preprocessed-to-Clang compatibility is **invalidated** for
this toolchain without source/token changes. No headers were removed, constants
invented, or flags/forced headers added to hide either blocker.

Frontier: recover/review the actual configured package header/source closure
(including the package-produced `src/custom/defines_post.hpp`) and compare it to
immutable installed profile evidence before admission. This workstream did not
reconstruct or modify that closure under its no-source-edit authorization.
No CFG, aliases, escape effects, mutation ordering, interprocedural effects,
all-site coverage, catalogue approval, runtime overlay, or native admission is
proved. Coverage is three selected sender functions, not the full catalogue.
