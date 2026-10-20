---
title: Classic Paladin research — acquisition and reset precision addendum
created: 2026-10-05
updated: 2026-10-05
type: guide
status: proposed
tags: [rathena, testing, ops]
---

# Research correction, not executable progression

Related: [[classic-paladin-build-evidence]], [[goals-ledger]],
[[adr-009-character-builds-item-cognition]].

The independent review supports the shared Paladin skill-pool interpretation,
stage allocations and nonlinear stat calculations. It does not approve a build
executor, equipment receipt, actual acquisition or gameplay.

## Acquisition categories

Parent independently parsed the pinned pre-re mob database and matched all
**46 ordinary `Drops` rows** in the original research. There is also **one MVP
reward row**, yielding **47 rows across the two inspected categories** for the
15 exact equipment candidates. The original research/report is preserved.

| Category | Monster | Exact item | Raw source Rate |
|---|---|---|---|
| `MvpDrops` | Stormy Knight, ID1251 | `Boots_`, ID2406 | 500 |

Authority: pinned revision `e985006171d2eb320ee512a653f4c83aea3d81b6`,
`db/pre-re/mob_db.yml:11594–11636`, specifically lines11629–11633.
The raw Rate is not a measured live probability. MVP rewards are not interchangeable
with ordinary loot; effective rewards, eligibility, multipliers, map access,
quest/import availability and farm feasibility remain unverified.

Actual computed evidence and source hash:
`run/reviews/classic-paladin-acquisition-addendum.json`.
Independent original review:
`run/reviews/classic-paladin-build-independent-review.json`.

## Reset and quest precision

- Rebirth resets paid allocations; quest skills are not universally wiped when
  `quest_skill_reset: no` applies. Preserve explicit per-skill reset semantics.
  Authority: `src/map/pc.cpp:9237–9273,9477–9529` and
  `conf/battle/player.conf` at the same pinned revision.
- Valkyrie dialogue mentions pets, but the inspected executable gate does not
  contain an explicit pet predicate. Do not turn dialogue into a proven gate.
  Authority: `npc/jobs/valkyrie.txt:44–108,148–155`.

Literal high-class aliases, ambiguous item identity, life/class/base/job planning,
private import checks and separately authorized native gameplay remain open.
No source code, original evidence, character, SQL or world was changed.
