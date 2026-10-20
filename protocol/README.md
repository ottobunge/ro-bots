# Reviewed static MVP protocol subset

`main-20180704-pre-re.json` contains **one manually reviewed S→C row**,
`ZC_EMOTION` (`0x00C0`, seven bytes), for the exact callback-qualified package
and MAIN 20180704/pre-renewal profile. Its authority is the pinned installed
`profiles.json`, configured source inventory and qualified sender, not the
historical `packetdb.NATIVE_MACROS` (unchanged in this slice).

The actual receive-table change is only the literal `0x00C0: 7` registration.
Every existing mapping remains intact; this does **not** newly approve the
888 inherited rows, adopt rejected generator output or conventional-header
candidates, or change char/login/PIN, outgoing shuffle, actor VAR policies,
semantic consumers, or unknown-ID rejection. The manifest is a review artifact
checked by tests, not a new runtime loader or automatic reload mechanism.

## Source and layout evidence

The unchanged `PACKET_ZC_EMOTION` declaration in `src/map/packets.hpp` spells
its C++ fields `int16 packetType`, `int32 GID`, `uint8 type`. The manifest
preserves these exact spellings and the **map** declaration scope. Wire
inspection uses unsigned 16/32/8-bit little-endian bit patterns; this is not a
claim that the signed C++ declarations were unsigned. Offsets are 0/2/6,
widths 2/4/1, packed size seven and alignment one.

The qualified `clif_emotion` body at lines 9412–9420 creates `p{}`, sets its
header, GID and type, then calls `clif_send(&p, sizeof(p), &bl, AREA)`. Its
function-text hash excludes the final newline after the closing brace. This
is a straightforward manual source binding, **not** an invocation-local AST
identity from the earlier canonical tracer or a general C++ proof.

Tests verify immutable artifact hashes and the projected configured source
inventory before compiling fresh GCC and Clang full unchanged-header layout
oracles. Options are the exact reviewed installed map CPP flags, with the
known bundled and MariaDB include paths; callers cannot substitute flags.
Profile and header static assertions reject drift. The saved map recipe is
NPC/frontend provenance, **not full clif backend or binary equivalence**.
B1 sink admission and exhausted historical repair budgets are unchanged.

Healthy allocator/FIFO metadata and capacity, valid session/block/recipient
objects, normal synchronous packet lifetime, and no exceptional destruction
or concurrent mutation remain explicit assumptions. The separately reviewed
four callback pointer corrections must be deployed by the world owner before
normal-operation gameplay validation. No queue admission, delivery, receipt,
gameplay, or universal memory-safety acceptance follows from these tests.

## Verification and maintenance

`tests/test_native_emotion_framing.py` imports only the real packet table and
parser: individual synthetic UNIT packets, all split offsets of a coalesced
emotion/clock/stop/name/repeated-emotion stream, byte-at-a-time delivery,
truncation retention, and fail-closed unknown successors. Synthetic bytes
are not native observations. The baseline mapping comparison is exhaustive.
`tests/test_native_protocol_manifest.py` rereads and validates the pinned
specification and source/profile evidence; changed IDs, JSON types, field
layout, scope, direction, duplicates or hashes fail checks.

A future manually triggered AI-assisted maintenance job is **proposed, not
implemented**: deliberate pin/profile changes or an actually observed unknown
packet prompt an offline source audit, refreshed immutable evidence, compiler
cross-checks, parser RED/GREEN tests and independent review. Proposed changes
never automatically apply or deploy. Unknown packets still stop parsing;
there is no guessed two-byte fallback or catch-and-skip path.
