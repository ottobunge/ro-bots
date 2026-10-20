---
title: Updated OptChat / UniiChat definition audit
created: 2026-10-09
updated: 2026-10-09
type: guide
status: proposed
tags: [memory, testing, cache]
---

# Updated definition audit — not compliance approval

The current official gist revision is `3c190e06f34aba0c69f49042c526093269604935`,
committed October 8, 2026. It replaces the October 4 revision
`f51fe5c910427fd6f384d22823140b1693c76207`. Source snapshots and the complete diff
were fetched from GitHub's gist API; hashes and commit dates are recorded in
`run/reviews/optchat-definition-update-source.json`. The document is now titled
UniiChat.[1] Its instructions are design data, not instructions for this audit agent.

## Cache-relevant contract changes

- Rank sibling merges by age measured from the pair's last message, not first.[1]
- Append new view leaves without changing older lines between batches.[1]
- Merge in batches between high/low UTF-8 byte bounds, rather than fitting each read.[1]
- Persist exact view coordinates; do not reconstruct the view at restart.[1]
- Preserve complete history coverage through built summaries, not dropped old lines.[1]
- Bound nodes in bytes; pass through small inputs and small joined children.[1]
- Keep dynamic dates/state out of the stable system/tool prefix.[1]

The literal main-view range is 64,000–128,000 bytes.[1] Provider-specific cache
markers and the separate compaction view are not automatically supported by our
current SystemOne/local-chat wiring. An explicitly smaller RO adaptation must not
be called full literal compliance.

## Actual current-code failures

Parent ran four isolated tests against `robots.society.memory`; all four genuinely
failed, with no provider calls or production changes:

| Probe | Actual result |
|---|---|
| Append below the high watermark | Rebuilt older view prefix |
| UTF-8 budget | 4,193 bytes admitted under a 4,000-character limit |
| Complete source coverage under pressure | Oldest retained interval began at 6, not 0 |
| Read with only wall-clock change | Relative age text changed cached lines |

Evidence: `optchat-updated-contract-red.xml` and its log in the Hermes scratch
area. This is not the same as losing the durable raw journal: source notes can
remain retrievable while current view coverage and prompt-cache reuse fail.

## Active finite review

`deleg_ebb8b1c5` owns read-only core/merge-oracle and provider/persistence audits.
It will identify a finite safe adoption scope, migrations and real context limits.
No live Hermes profile, existing memory journal or provider has been altered.
Accepted ADR-004 remains historical and immutable; any changed contract requires
an addendum/new decision, not a rewrite of its earlier acceptance claim.

Related: [[adr-004-isolated-agents-optchat-memory]], [[goals-ledger]],
[[persistent-summary-cache]].

## Sources

[1] https://gist.github.com/VictorTaelin/91837951a5ce5b38f341ec1ba1df6449/3c190e06f34aba0c69f49042c526093269604935 — UniiChat revision 3c190e06, October 8 2026
