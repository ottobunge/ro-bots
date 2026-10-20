# Scratch-only callback qualification

## Verdict: VALIDATED (bounded types, whole-TU syntax, local bridge)

The reviewed configured public source closure was copied into a new private
scratch directory. Only `src/map/clif.cpp` changed, with precisely four
substitutions within the audited `clif_send_sub` body:

- `buf` becomes `const unsigned char*`;
- buffer retrieval is exactly `va_arg(ap,const void*)`, followed by an explicit
  `static_cast<const unsigned char*>` byte view;
- `src_bl` becomes `const block_list*`;
- source retrieval is exactly `va_arg(ap,const block_list*)`.

All integer retrievals, remaining callback tokens, C-style casts, conditions,
helpers, caller bodies, headers and configured source changes are preserved.
This is **not** a full const-correctness refactor: existing downstream casts are
unchanged. `nullpo_ret` is inactive under this profile, not a runtime null guard.

## Run

From `/home/otto/dev/ro-bots`:

```sh
nix develop --offline --no-write-lock-file path:./spikes/007-native-packet-ast/toolchain -c python3 -B spikes/007-native-packet-ast/callback-qualification/trial.py
```

The CLI has no output-path override. Each invocation creates a fresh private
`mkdtemp` directory beneath the established scratch root; no previous output or
baseline is reused as a writable destination. Dependencies come only from the
already-cached tiny Nix flake. No dependency fetches or installs are performed.

Tests can also run independently:

```sh
nix develop --offline --no-write-lock-file path:./spikes/007-native-packet-ast/toolchain -c python3 -B -m unittest discover -s spikes/007-native-packet-ast/callback-qualification -p test_trial.py -v
```

## Evidence

Completed final run:
`/home/otto/.hermes/cache/scratch/callback-qualification-c70gvqdr/output/result.json`.

- The initial unittest genuinely failed on the pristine source's missing
  `const block_list *src_bl;`; the final suite passes five tests. Each run also
  records an observed pristine source-contract failure and the corrected pass.
- All 3,206 physical public source files match the reviewed baseline before
  transformation. Afterwards exactly one path differs. Full inventory mappings,
  callback/file hashes and the four-line patch are retained.
- GCC 16.2.0 and Clang 21.1.8 both parse the **entire** corrected `clif.cpp` with
  the exact reviewed role flags/includes rebased to the trial. Server-role
  compilation uses `-fsyntax-only`; it neither links nor executes a server.
- Active expanded Clang AST verifies all four retrieval slots, the two qualified
  locals, the explicit const byte-view cast and both actual AREA forwarding
  calls. Declaration IDs are joined only inside this one compiler invocation.
- Clang's existing switch/wrapper warnings are retained. Pristine and patched
  diagnostics are byte-identical after replacing their source-root prefixes.
  GCC has no diagnostics. No const-related diagnostic is suppressed or repaired.
- The unchanged profile guard and GCC profile/layout oracle produce identical
  output to the reviewed baseline. Emotion remains ID 192, size 7, offsets
  `[0,2,6]`. Full-TU macro checks match the audited MAIN/pre-re 20180704 profile.
- Both compilers execute only a **defined, isolated type-bridge witness**, with
  an actual profile `int32` alias, source-extracted enum, seven readable source
  bytes and seven writable destination bytes. It retrieves exact pointer types,
  compares a null `const block_list*` without dereferencing it, checks length 7
  and AREA promotion to int value 2, and checks the copied bytes. It is not a
  real callback/FIFO/server simulator. Original mismatched varargs are never
  executed; static pointer-type inequality is retained as a negative control.
- The 189-file parent freeze, old experiment code/toolchain hashes and reviewed
  baseline source closure remain unchanged. Complete TU dependency hashes and
  command/log/artifact hashes are recorded.

## Limits

No package rebuild, deployment, server/model/SQL/container/config/network/world
operation occurred. No historical binary equivalence, recipient safety, packet
receipt, sink adoption, catalogue completeness or gameplay acceptance follows.
The allocator, indirect SendFunc, unlock, recipient and libc obligations (U2–U7)
remain unresolved. All six milestones remain open. Parent replay and independent
review, followed by fresh release authorization, are still required.
