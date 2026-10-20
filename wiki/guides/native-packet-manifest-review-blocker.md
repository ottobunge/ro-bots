---
title: Packet catalogue recognizer — final review blocker
created: 2026-10-07
updated: 2026-10-07
type: guide
status: proposed
tags: [protocol, testing]
---

# Final review: rejected; automatic repairs exhausted

See [[native-packet-manifest]] and [[goals-ledger]]. This records a blocker,
not a new accepted architecture or permission for runtime effects.

The second repair passes the configured gate: 3655 physical tests plus 65
subtests, 95% coverage, on 185 unchanged frozen inputs. Final independent review
runs 137 physical cases: 43 owned, 71 previous and 23 fresh. Nine fresh cases fail.
Parent verifies all 162 artifacts and re-executes all nine compiled counterexamples.

Three remaining problems:
- Unary-plus and logical-context lambdas evade exclusion; a parameter shadows the
  outer packet, falsely attributing header 1/length 66 to an actual 2/4 send.
- Parenthesized object/member writes and indirect prefix mutations evade write
  recognition; the inferred header is 1 but actual output is 2/66.
- Helpers and pointer/reference aliases can mutate the packet without recognition;
  the inferred header is again 1 while actual output is 2/66.

No incorrect row in the current pinned catalogue is established. Its unchanged
263 resolved/104 unresolved output does not establish sound sender recognition.
Compiler/profile authority checks remain protected; they do not solve C++ identity.

Both automatic repairs are exhausted. Stop implementation and request architectural
 direction; do not add a third patch, waive negative cases, or integrate the catalogue.
A compiler-identity-based offline redesign experiment is the proposed next direction,
not an approved implementation. Preserve old failed reports, fixtures and catalogue.

Evidence: `run/reviews/native-manifest-generator-final-review.json` and
`run/reviews/manifest-cycle2-parent-gate.json`. Runtime framing and world state
remain unchanged; damage, XP, loot and the six full milestones remain unaccepted.

Subsequent user decision: **Proceed with the offline AST/hybrid experiment**.
This authorizes the standalone experiment in [[native-packet-ast-spike]], not another
repair of this rejected implementation or admission to the runtime catalogue.
