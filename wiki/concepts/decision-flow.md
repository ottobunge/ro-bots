---
title: Decision flow — the full loop
created: 2026-10-05
updated: 2026-10-05
type: concept
status: accepted
tags: [architecture, events, decision-model, escalation, timers]
---

# Decision flow

Normative map of one bot's control loop. Code: `robots.app.runner`,
`robots.app.brain`, `robots.app.scripts`, `robots.app.timers`.

```mermaid
flowchart TD
    subgraph LOOP["Runner tick loop (every tick_seconds)"]
        P[poll_state from GameClient] --> T{timers due?}
        T -->|TimerFired / PlanExpired| E[deliver event]
        T -->|no| W{world events?}
        W -->|MonsterSpotted etc| I{plan interrupt rules?}
        I -->|interrupts| E
        I -->|below notice| W
        W -->|none| S[step behavior script]
        E --> B
        S --> A[act: send packets]
    end

    subgraph BRAIN["EventDrivenBrain — the only Clef caller"]
        E --> B[build SystemOne request:<br/>state + event summary + questions]
        B --> C[Clef decision<br/>one forward pass]
        C --> D{event type}
        D -->|MonsterSpotted| R1[react: attack / flee / ignore]
        D -->|DamageTaken| R2[react: keep / rest / flee]
        D -->|ChatHeard| R3{directed at me?}
        D -->|InviteReceived| R4[accept / decline]
        D -->|Heartbeat / TimerFired| R5[goal review + farm plan authoring]
    end

    R3 -->|yes, policy says reply| L[ChatGenerator LLM<br/>escalation_count += 1]
    R3 -->|premade fits| PM[premade phrase<br/>zero LLM cost]
    R5 --> FP[FarmPlan: duration + target mobs<br/>+ interrupt threshold]
    FP --> FS[FarmScript active]
    R1 --> GS[GrindScript / flee move]
    L --> A
    PM --> A
    GS --> A
    FS --> A
```

## Properties (enforced by tests)

- Clef is called **only** from `handle_event` — never per tick (ADR-001).
- Premade chat (`PREMADE_CHAT`) is emitted **without** the LLM; the LLM is
  only for free-form replies (ADR-000 escalation split).
- While a FarmPlan is active, monster events below the plan's threshold never
  reach the brain (ADR-003).
- All timing is random-range and injectable (ADR-002).

Related: [[adr-000-hexagonal-architecture]], [[adr-001-event-driven-brain]],
[[escalation-policy]]
