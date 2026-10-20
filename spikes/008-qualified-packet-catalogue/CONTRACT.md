# Stage B1: offline candidate contract

This is a new offline layout/catalogue contract, not a repair of the exhausted
original generator. It does not replace the inherited receiver table, its 888
rows, registrations, PIN/character/login/outgoing handling, or any runtime code.
The old manually rejected 263-row generator receives no new exception. The initial tranche is
common/map declarations under the actual qualified map CPP/profile; it is not a
complete wire catalogue or a general proof about arbitrary C++.

## Five distinct evidence levels

1. **Measured declaration layout:** compiler size, alignment and field offsets.
   A conventional HEADER_/PACKET_ association is a candidate, not sender binding.
   Character arrays, pointers, bases and other storage shapes are not approved
   serialization merely because a record compiles or someone calls it POD.
2. **Invocation-local identity:** optional single-emotion
   `ADDRESS_SIZEOF_IDENTITY_ONLY` evidence relates an object to its address and
   sizeof within one invocation tag. It cannot join AST IDs across invocations.
   Matching input IDs is structural validation, not authentication of an AST dump.
3. **Conditional copy/queue bounds:** healthy source object, allocator metadata,
   ownership, positive capacity, integer non-overflow, recipient/session survival,
   source lifetime, and noninterference are separate, undischarged requirements.
   Allocator OOM/shrink paths, queue-limit destruction and exception-skipped manual
   list restoration remain known negative cases, not waived defects.
4. **Runtime framing/admission:** no layout, header candidate, compiler agreement,
   artifact digest or identity observation admits a length or a sink. Helpers,
   uncertain dataflow, variable bodies and raw FIFO paths require manual review.
5. **Native receipt/gameplay:** neither compilation nor validation supplies a
   packet receipt, an observed world effect, or gameplay/milestone acceptance.

U1's qualification correction applies only to the offline variant, not a deployed
server. U2–U5 allocator/session/lifetime invariants remain UNPROVEN; the six
source-identified conditions in `default_preconditions()` are always
`UNDISCHARGED`. U6's seven-byte copy is conditional on a valid source and FIFO
capacity/session/lifetime bounds. There is no all-route U7 proof.
`sink_admission`, `runtime_admission` and `compiler_execution_authenticated`
are always false. No caller-provided PROVEN/semantic-approval waiver is accepted.

## API and CLI

`validate_facts(facts, metadata)` is pure: it accepts JSON-shaped data and a trusted
`PackageMetadata`, returns typed `Candidate`/`ContractReport` values, and does no
I/O, compiler launch, code execution or runtime operation. JSON-boundary `Any`
annotations are localized to dynamic objects. Importing the module has no effects.

```
python3 spikes/008-qualified-packet-catalogue/contract.py FACTS.json
```

Exit 0 emits a JSON report; exit 2 rejects input or unavailable immutable metadata.
The CLI reads the fixed immutable package's installed metadata. Optional
`authority.artifacts` is a mapping of local relative file paths to literal lowercase
SHA-256 digests; the CLI reads and hashes those files, rejects escape/symlink targets,
and never executes their contents. A forged stdout file with its correct digest
still cannot authenticate execution: the successful check is **metadata binding
and optional artifact integrity only**. Compiler commands are untrusted inventory
labels, not executable authority. No flags, response file, forced include or plugin
from a contract is launched or approved. Identity hashes describe inputs, not effects.

The package's source-evidence manifest is a reviewed, self-owned build receipt,
not an independently authenticated execution transcript. The pure API assumes its
`metadata` argument is trusted by its caller; supplied facts never establish that
trust. The CLI fixes the package path, binds the installed map CPP flags and saved
compile-recipe digests, verifies the public 3206-file closure after excluding the
ten explicitly named generated Makefiles, and checks role profiles. NAR identity is
a fixed reviewed expected identifier, not a fresh NAR recomputation by this CLI.
External compiler/include artifact completeness and actual compiler execution are
collector/reviewer responsibilities and remain outside this validator's proof.

**Backend envelope limitation:** the saved map recipe selects the NPC custom rule
with CXXFLAG_CLEARS; it is not the complete ordinary clif CXXFLAGS/backend recipe.
CPP/profile/frontend/layout scope must not be labelled backend or binary equality.
The parent's notification reports independent offline package approval, not sink
or runtime approval; this contract's independent review remains separate.

## Strict input shape (interface v1)

`interface.json` accounts explicitly for every collector field; unknown fields and
claims of proof/admission remain rejected. The actual collector supplies **four
primary header hashes**, not the entire include closure. Exact keys/digests bind
to trusted immutable package metadata. The report states
`PRIMARY_HEADER_HASHES_PLUS_IMMUTABLE_PACKAGE_SOURCE_MANIFEST`, not compiler
execution authentication. Configured/public counts and the ten generated Makefiles
bind to the immutable manifest. The complete 3206-file synthetic v1 form remains
supported; legacy literal sources and command labels are labelled unit fixtures only.

Authority preserves versions, oracle descriptions and complete command dictionaries
(argv, return code, hashes, paths, and only HOME/LC_ALL/PATH/TMPDIR environment).
These are **untrusted inventories**, never instructions: the validator neither
launches commands nor opens inventory paths. The explicit recipe limitation denies
full backend/binary equivalence. Oracle effects descriptions confer no permission.

Real `source` preserves translation_unit_scope, primary_headers, ast_location and
location_policy. Both common/map roots use the same MAP profile, independently
including their unchanged headers. Raw AST attributes and omitted filenames are
preserved without inference or filesystem access. Keys are exactly `scope:record_name`;
C++ spellings are never rewritten into namespaces. Both global PACKET_SC_NOTIFY_BAN
declarations survive: **632 keys, 631 spellings**. Same-scope duplicates are rejected.

Layouts retain positive integer size/alignment, literal names/types and strict
integer offsets. Real fields preserve offset_unresolved_reason (null when measured)
and UNKNOWN_LAYOUT_IS_NOT_WIRE_ENCODING. Null offsets require a nonempty reason;
no offset or span is fabricated. The **94 observed flexible/zero-extent tails** may
have offset equal to sizeof(prefix), only for a clear trailing []/[0] array with no
span. Scalars, pointers and pointer-to-array declarators at that offset are denied.
Positive supplied spans must fit inside the prefix; size is never a wire length.
Header observations and both gcc/clang uint16 values remain intact. Bools/floats
are rejected. Layout/header disagreement and alias ambiguity generate conflicts
by declaration key and conservatively mark manual review, never choose a value.
Directions remain UNKNOWN and sender_evidence remains UNRESOLVED.

Coverage retains both discovery units, count-unit, header-guard and same-spelling
warnings, complete_catalogue=false and four uncovered components. Counts account
compiled/unresolved **declarations**, not global limitation notices. The collector's
two global sender/framing notices survive while unresolved_records remains zero.
Exact count accounting is not global discovery proof.

The explicit collector mode requires all authority/coverage extras and object-form
scoped sources. Its discovered_records is len(records); compiled_records counts
raw LAYOUT_ONLY_NO_FRAMING_ADMISSION rows and unresolved_records counts raw
UNRESOLVED_MANUAL_REVIEW rows, before the validator's alias downgrades. Global
nonempty compiler-failure strings precede the two mandatory limitation notices;
they are not per-declaration counts. Legacy synthetic v1 instead retains separate
unresolved dictionaries and its original accounting, never nullable layouts.

Missing GCC/Clang layouts are null only on source-known manual-review collector
rows with a nonempty unresolved_reason; known layouts are fully validated and
preserved exactly, never replaced with empty objects or invented measurements.
Missing/unequal layouts or unequal header observations require manual status and
a null header_candidate. Each header observation independently permits null or a
strict uint16 integer; a missing layout cannot supply a measured header. Equal
retained header integers on a layout-conflict row are observations, not binding.
Layout-only rows require agreeing layouts, no unresolved reason, and either both
null header observations or exact agreement with their conventional candidate.
Optional identity requires the unique exact map:PACKET_ZC_EMOTION declaration,
actual source scope map (not authority.role), agreeing complete layouts, and no
manual/compiler/alias frontier. Synthetic invocation IDs remain nonauthenticated.

Malformed nested objects/lists/scalars are rejected by shape validation before
use: API ValueError and actual CLI exit2 with empty stdout. Unexpected internal
exceptions are not converted to fabricated success or blanket rejection.

The exact minimal collector U2-U5 UNDISCHARGED/U6 conditional-copy object is retained
as `input_required_preconditions`. The six stronger canonical source conditions
remain separate **requirements**, not proven or source-authenticated observations.
No allocator, capacity, OOM/exception, source/recipient lifetime or noninterference
condition is waived. Canonical synthetic preconditions remain supported unchanged.
Single-emotion identity still requires a unique matching declaration; ambiguity
fails closed rather than selecting the first spelling.

## Verification and remaining frontier

The real immutable artifact is read-only. A failing real integration regression
preceded harmonization; negative UNIT-only perturbations exercised scoped keys,
claims/provenance, numeric coercion, flexible tails, dropped components and conflicts.
Real GCC/Clang layouts, headers, provenance and all declarations are compared by
JSON value in output; only classification may downgrade. Synthetic perturbations
are never published observations. Original reports and the private header incident
remain unchanged evidence; this task never touches the restored header/source closure.
The integration report records actual CLI/test/gate results and hashes. No collector,
runtime/package/world/receiver code is changed. Repair cycle1 modifies only this
new integration; the original producer pipeline remains unchanged.

Offline common/map layout approval still requires the parent's stable combined gates
and fresh independent review. Validation never authenticates compiler execution,
admits framing/sinks, activates runtime, proves receipt, closes any of the six
milestones, or reopens the exhausted old-generator repair budget.
