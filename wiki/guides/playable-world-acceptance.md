---
title: Playable-world acceptance — all six required milestones
created: 2026-10-05
updated: 2026-10-05
type: guide
status: proposed
tags: [architecture, rathena, testing, ops]
---

# Playable-world acceptance

Criterion 8 makes every milestone below required, in addition to criteria 1–7.
This is an acceptance specification, not a completion report. Current dispositions
remain in [[goals-ledger]]; offline preparation follows proposed
[[adr-016-private-runtime-before-world-launch]].

## Evidence rules

- Distinguish offline models, injected-client tests, actual transport observations,
  human-client observations and authoritative owned-world state readback.
- Associate evidence with the exact run, world, source/compiler profile, persona,
  account/character and observation time. Do not use a previous run's party roster,
  loot, position or stored experience as proof of a fresh action.
- A successful send is not delivery; a goal/event counter is not gameplay. Native
  acceptance requires actual observed effects with suitable independent readback.
- Keep private values out of every report. Observer/dashboard knowledge is not
  automatically allowed into an agent's perception or private memory.
- Passing a small population scenario is not population-scale acceptance. Neither
  test counts nor scoped review approval imply that a whole milestone is complete.

## Required milestones

| Milestone | Minimum acceptance evidence | Current disposition |
|---|---|---|
| A world you can join | Exact owned-world assets/config/schema; successful isolated startup; compatible human client joins and observes the map; safe stop/start preserves that world's data; disposable-test initialization/reset cannot affect debug, foreign or named production storage. | Not accepted: offline package exists, but launch is deliberately blocked. |
| Bots visibly playing | Scheduled native agents actually move/arrive, damage and kill mobs, gain XP, acquire targeted inventory, chat and form a correlated party roster. Clef, canned phrases and actual LLM escalation run through the owning workers; scheduled disconnect/reconnect changes native presence. | Not accepted: offline cognition/transport foundations are not sustained gameplay. |
| Persistent, believable agents | Human/bot interaction becomes privately stored knowledge; reconnect and process restart retain the correct persona history and persisted summary cache; uninformed agents cannot access another agent's private events; character switching preserves persona identity and per-character state; contribution perception originates from observed damage/heal/buff events. | Not accepted: raw journals and shared host memory are only bounded offline foundations. |
| The full social scope | Friend groups demonstrably coordinate schedules/parties and follow differing attitudes; solo outsiders can interact across groups; human contributions change rapport; allowed attenuated gossip moves through actual social links; guild creation and WoE participation have native effects. | Not accepted: policy models alone do not satisfy this milestone. |
| Real dashboard control | Generation reconciles actual owned accounts, characters, workers and memories; inspection shows real agent state; persona/goal/schedule edits and supported commands affect owning agents; browser/Rust delivery statuses preserve uncertainty and rejection rather than converting notes into success. | Not accepted: live generation/reconciliation and browser/Rust command integration remain open. |
| Progression and acceptance | Ruleset-separated legal builds and mechanical comparisons govern equipment acquisition/equip/sell/store through normal progression; repeatable clean E2E/playground tests exercise actual goals; long-running population tests and comparable Framework GPU/Cloudflare/Heavengraph measurements are evidenced. | Not accepted: both-rule data research is not complete executable progression or E2E. |

## First end-to-end scenario, not a substitute for the whole scope

Start with two friend personas and one solo persona, all using explicitly owned
fixture identities and valid starter builds derived from the active pinned ruleset.
This exercises both group and solo generation without claiming large-population
support or confusing resource bounds with native party capacity.

1. Prepare an actual private runtime bundle and prove its public asset/config
   dependencies. Keep launch blocked until the separate executor/admission work.
2. After exact live-target authorization and ownership/admission checks, initialize
   a fresh disposable test world, start it and establish native agent presence.
3. Observe a complete grind/farm cycle: movement, real combat, XP and target-item
   inventory change. Observe friend coordination and the solo's independent goal.
4. Trigger appropriate public chat, a canned phrase and an actual LLM reply; retain
   truthful host command status separately from native receipt/visibility evidence.
5. Stop and reconstruct the host; reconnect the owned agents and verify their
   private knowledge. Perform a human-client interaction/playtest when available.
6. Repeat from a clean test world and also test preserving an existing debug world.
   Never extend disposable-test reset authority to named production or human data.

Further acceptance must cover level-appropriate quests, multiple characters,
complete class/playstyle variation, native relationship/reputation and guild/WoE
behavior, sustained populations and both rulesets. No item is silently deferred out
of the user's requested completion scope.

## Coordination

The coordinator maintains every criterion and reconciles verified artifacts and
reviews. Runtime preparation, bootstrap-source reconnaissance and independent
package review have disjoint ownership. Full integration gates run on stable
completed snapshots; transient intermediate files are not evidence of acceptance.
