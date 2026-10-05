---
title: Goals ledger — the experiment's standing goals
created: 2026-10-05
updated: 2026-10-05
type: guide
status: accepted
tags: [architecture, ops]
---

# Goals ledger

Living record of the experiment's goals (original + every criterion added
mid-loop). Each goal lists the ADRs that define it and its current
implementation status. Update `updated:` and the status column whenever a
slice lands. This page is the checklist the wiki drives the code against.

| # | Goal (as stated by Otto) | Defining ADRs | Status |
|---|---|---|---|
| G0 | Private rAthena server; server-side bots acting as real players | adr-000, adr-001 | **landed** (server up; clientless login→char→map proven, spike 002 PARTIAL→finished by 003 work) |
| G0 | Clef decides routine actions fast (noul/choice/score, one pass); LLM only for complex actions + chat replies | adr-000, adr-001, adr-006 | **landed** (EventDrivenBrain, escalation counters; local Clef service validated, spike 001 wrap-up in flight) |
| G0 | Premade chat phrases (LFP, buffs plz…) as Clef options — zero LLM cost | adr-001 | **landed** (PREMADE_CHAT as choice criteria) |
| G0 | Behaviors: grind levels, farm item, idle town, level-appropriate quests, form parties/guilds | adr-001, adr-002, adr-003, adr-005 | **landed** for scripts/plans/party-accept; guild/WoE behavior wiring in flight |
| G0 | Measure how fast/dynamic the world can be pushed | adr-001 (decision/escalation counters), adr-006 | **mechanism landed**; headline metrics come from the first live run |
| 1 | Isolated agents (no global knowledge), OptChat-style long-term memory, remember people across sessions | adr-004, adr-006 | **landed** (MemoryLog tree/view/zoom, ClefContextSelector, MemoryContextBridge) |
| 1 | Realistic relationships tracked between agents | adr-005 | **landed** (SocialGraph affinities seeded by friend groups) |
| 1 | Schedules: connect, play, disconnect, come back later — never out-pacing humans | adr-002, adr-005 | **landed** (randomized timers + shared jittered group schedules; used by roster + mock feed) |
| 1 | Human players can play alongside; agents remember the human | adr-005, adr-004 | **in flight** (society/human.py: HumanTracker + ContributionScorer + propagation_log) |
| 2 | Multiple characters per agent; class choice limited by play-style | adr-005, adr-009 | **landed** (persona playstyle → allowed classes → BuildAuthor) |
| 2 | Friend groups with overlapping schedules acting as friends, partying together | adr-005 | **landed** (ScheduleFactory shared windows; group seeding) |
| 2 | Guilds uniting multiple groups; WoE participation | adr-005 | **in flight** (society/guild.py: GuildRegistry, WoeCalendar, WoeParticipation) |
| 2 | Group attitudes (helpful-newbie / clique / event-focused / grinder) + solo outsiders drifting between groups | adr-005 | **landed** (Attitude enum + solo groups; WoeParticipation uses them) |
| 2 | Human friendship score from party usefulness; reputation propagates between allied groups (bad AND good) | adr-005 | **in flight** (ReputationStore.propagate landed; HumanTracker chattiness-gated gossip in flight) |
| 3 | Web dashboard (local, Docker-friendly): configure counts (agents/groups/solos/friends-range), generate | adr-007, adr-008 | **landed** (Rust dashboard + MockWorldFeed regenerate_roster command) |
| 3 | Track agents: memory view, related events, goals (personal/group/guild), schedule, characters | adr-007, adr-008 | **landed on mock** (inspector + SSE); **in flight**: real data via Python WorldFeed server |
| 3 | Edit personas; force actions on agents; see generated characters | adr-008 | **landed on mock** (edit_persona/force_action commands, operator_forced tagging) |
| 4 | Agents assign builds (final equip/skills/abilities as goals) chosen by play-style | adr-009 | **landed** (BuildAuthor via Clef; Build + BuildProgress) |
| 4 | Pre-calculated mechanics: agents see item digests, Clef decides equip/store/sell/discard | adr-009 | **landed** (MechanicsPort + StubMechanics; YamlMechanics over rAthena item_db pending) |
| 5 | `task e2e`: clean server + seeded default test agents (builds/playstyles/groups) + goal-directed behavior assertions + KEEP=1 playground mode | adr-010 | **in flight** (docker-compose.worlds.yml, scripts/e2e.sh, seed_test_agents.py) |
| 5 | Three isolated world volumes: debug (dev), test (wiped per e2e), prod-NAME (default prod-default) | adr-010 | **in flight** (compose-level isolation via WORLD_KIND; prod wipe protected by FORCE=1 gate) |

## In-flight / next (kept current)

- **In flight**: guild/WoE + human reputation layer; Python WorldFeed server
  (real dashboard data source); spike 001 bench wrap-up; spike 003 two-bot
  limb verification.
- **Next integration slice**: runner process unifying EventDrivenBrain +
  society schedules + BotClient (spike 003's client) — N scheduled agents on
  the live server, pushing real AgentRuntimeState into WorldState, replacing
  the dashboard's MockWorldFeed.
- **Pending**: rAthena item_db/skill_db YAML adapter for MechanicsPort;
  spike 002 README.
