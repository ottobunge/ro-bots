---
title: ADR-005: Society — personas, friend groups, schedules, reputation
created: 2026-10-05
updated: 2026-10-05
type: decision
status: accepted
tags: [architecture, events, llm]
---

# ADR-005: Society — personas, friend groups, schedules, reputation

## Decision

**Persona** (`SocietyPersona`): `name`, `playstyle` (limits class choice:
e.g. `tank/melee`, `healer/support`, `mage/nuker`, `trapper/hunter`),
`attitude` (`helpful_newbie`, `clique`, `event_focused`, `grinder`, `solo`),
`chattiness` (0–1), `base_level_band`.

**Friend groups**: a group of 2–6 personas with mostly-overlapping
**schedules** (connect together, disconnect together, come back later — they
must NOT grind 24/7 and out-pace humans). Groups carry a shared attitude.
**Solo agents** are groups of 1 that prefer joining other, bigger groups —
the outsiders that drift from party to party.

**Relations** (`SocialGraph`): directed edges agent→agent with
`affinity` in [-1, 1]. Edges are seeded inside friend groups (positive), and
grow/shrink from shared play (parties, chat, wipes).

**Human reputation** (`ReputationStore`): every human player has per-agent
and per-group scores in [-1, 1]. `ReputationEvent`s move them:
- useful party member (damage share, heals, buffs) → up
- dead weight / rude / kill-stealing → down
- **Propagation**: when an agent's score for a human changes materially,
  it reports to its friends: the human's score with the *friends' groups*
  moves by a fraction (0.25 default, damped by the inter-group edge
  affinity). Good news propagates the same way.

**WoE / guilds**: groups may form a `Guild` (multiple groups); WoE events
are scheduled world events that event-focused groups attend (brain layer:
`GuildEvent` world event + Clef questions — later slice).

## Consequences
- `robots.society` is a pure domain+app layer with a `SocietyClock`;
  the rAthena adapter feeds it perceptions and executes its schedules.
- Reputation propagation can create emergent "reputation shadows":
  behave badly in front of one clique, several cliques hear about it.

Related: [[adr-004-isolated-agents-optchat-memory]], [[escalation-policy]]
