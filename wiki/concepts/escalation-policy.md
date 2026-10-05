---
title: Escalation policy — Clef → LLM hand-off
created: 2026-10-05
updated: 2026-10-05
type: concept
status: accepted
tags: [escalation, llm, decision-model]
---

# Escalation policy

The experiment's headline metric is the **escalation rate**:
`escalation_count / decision_count` on `EventDrivenBrain`.

## Rules (current, `robots.app.escalation.EscalationPolicy`)

| Trigger | Escalates? | Handled by |
|---|---|---|
| Free-form chat directed at the bot (whisper, or name mentioned) | yes (if `reply_chat_always`) | LLM `ChatGenerator` |
| Premade phrase fits the situation (`premade_pick` + `use_premade`) | **no** | Clef choice → `PREMADE_CHAT` template |
| `next_action` confidence below `confidence_floor` (0.55 default) | yes (low_confidence) | LLM advisor (pending) |
| Party invite | no | Clef `accept_invite` noul |
| Monster reaction / damage reaction | no | Clef choice questions |

## Tuning knobs

- `confidence_floor` — raise it, more goes to the LLM; lower it, more stays in Clef.
- `reply_chat_always` — if false, even directed chat can be answered by premades.

## Design intent

Premades cover the *high-frequency, low-creativity* chatter (LFP, buffs plz,
greetings, WTS) so the world feels alive at Clef speed. The LLM handles the
long tail. The rate is logged per bot so we can measure how far Clef alone
can push the world.

Related: [[adr-000-hexagonal-architecture]], [[decision-flow]]
