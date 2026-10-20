# Offline compiler-backed layout candidates

This is a new standalone producer, not a repair of either rejected generator.
It imports no old catalogue rows, runtime packet database, tracer or contract module.
Its output is `qualified-packet-candidate-facts/v1`; sink/runtime admission is always
false. No native server executables, role initialization, source implementations or
network/world routines are run. Executed binaries are generated small constant and
sizeof/alignof/offsetof/printf oracles over full unchanged configured headers.

## Run

From `/home/otto/dev/ro-bots`:

```sh
nix develop --offline --no-write-lock-file \
  path:./spikes/007-native-packet-ast/toolchain -c \
  python3 spikes/008-qualified-packet-catalogue/compiler_catalogue.py \
  --output /home/otto/.hermes/cache/scratch/qualified-packet-catalogue-candidates.json
```

Only `--output` is accepted. Response files, arbitrary compiler flags and plugins
are not CLI inputs. Output into the configured source, checkout or Nix store is
rejected before collection. Generated oracles and stdout/stderr evidence persist
in a new private scratch directory, with exact commands and hashes in the output.

## Authority and replay boundary

The producer pins the actual qualified installed package, NAR, metadata bytes,
MAP CPP/profile flags and public configured source projection. It checks all
3,216 installed inventory entries and exactly ten recorded generated Makefiles;
the actual source must equal the remaining 3,206 entries, with canonical closure
`1f2d601dc86d572af78bae036f444fbbd469539457569e4f951438b30e74236a`.
Source/NAR guards run before compiler launch and again before oracle compilation
and publication. Compiler environment removes caller CPP/include/flag variables;
GCC 16.2.0 and Clang 21.1.8 wrappers have fixed immutable paths and their actual
version output is recorded. Both frontends check the live MAIN20180704/pre-re
macro profile, including absent obfuscation and warning macros.

This is scoped CPP/frontend/layout replay, **not backend/binary equivalence**.
The saved installed map recipe selects NPC `obj/npc.o` / `CXXFLAG_CLEARS`, not
clif `obj/%.o` / full `CXXFLAGS`. `CFLAGS -ffast-math` does not establish clif's
CXX flags. Bundled libconfig/rapidyaml/c4core and actual installed MariaDB dev
include paths come from the reviewed recipe/include definitions. No convenient
`-U` bypass, extracted-header replacement, allocator/sink stub or fake runtime
table is introduced.

## Discovery and uncertainty

Full unchanged `config/core.hpp`, `map/packets.hpp` (including
`map/packets_struct.hpp`) and `common/packets.hpp` are compiled under the MAP
profile. Common and map require separate translation units because their original
header guards collide; those guards are not modified. Clang JSON AST filters
`PACKET_` and `packet_` discover complete active CXX records. Filtering does not
join AST declaration IDs across invocations. Raw AST locations are retained;
omitted filenames are not reconstructed from nearby text.

Counts mean **declarations**, not unique spellings or a complete packet universe.
Use `declaration_key` (translation-unit scope plus literal name). There are two
separate actual `PACKET_SC_NOTIFY_BAN` declarations, in common and map; neither is
silently discarded or relabelled as a fictitious C++ namespace.

GCC and Clang independently measure every supported discovered declaration.
Failures retain logs and unresolved rows; disagreement retains both observations
and marks `UNRESOLVED_MANUAL_REVIEW`. Non-addressable bitfields, anonymous fields
and absent standard-layout proof get explicit nullable offset reasons. Unsupported
identifier forms cannot become generated C++ expressions. Field type and layout
do not prove serialization. Header candidates require active AST `const int16`
declarations and actual compiler integer stdout within uint16 range, with agreement;
association is only `CONVENTIONAL_NAME_CANDIDATE_NOT_SENDER_BINDING`. Unpaired
records remain null. Header compiler values remain separately available on conflict.

The validator's explicit collector grammar now consumes these retained failure
outputs: source-known rows remain in records with manual status, nonempty reason,
nullable missing compiler layouts and null candidate; both measured layouts and
independent uint16-or-null header observations are preserved without choosing.
Raw discovered=len(records), compiled=layout-only rows, unresolved=manual rows;
global failure strings and the mandatory final limitation notices count separately.
Validator alias downgrades do not change raw coverage. UNIT failure seams exercise
the real collect assembly path and are labelled synthetic, not actual failed-GCC
observations. No historical generator/tracer budget is reset.

Every successful row is `LAYOUT_ONLY_NO_FRAMING_ADMISSION`. No sizeof==wire-length,
name-prefix direction, actual packet header assignment, sender path, receiver
registration, queueing or receipt is inferred. Nonprefix declarations, aliases,
variable/raw WFIFO senders, char/login/PIN/outgoing integration and complete sender
coverage remain outside this tranche. U2–U5 are UNDISCHARGED; U6 states conditional
copy only. Parent producer/contract integration and independent review remain
required before approving this new offline artifact.

## Verification

Scoped tests include labelled synthetic-unit discovery/type/conflict fixtures,
source-drift denial before launch, rejection of flags/response/plugin inputs,
protected-output denial and a real compiler failure with preserved stderr. Real
integration measures the pinned full headers and checks emotion size7/header192,
stop size10/header136 and actor sizes110/103/104. Synthetic observations are never
published as catalogue evidence.

The initial protected-output RED test accidentally wrote `null` to the private
configured scratch `src/config/core.hpp`. It was immediately restored from a
cached public header whose bytes matched the immutable installed inventory SHA256
`ba04ee9f32d9d334f59b345326105864ddc5fed296ebbaf9d599c26e48aea7ae`.
The test now uses a synthetic scratch source root. Final full projection/NAR guards
and real compiler replay were repeated; no repository/package source was changed.
