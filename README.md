# ro-bots

Experiment: a private **Ragnarok Online** server (rAthena) populated with server-side
bot players whose behavior is driven by **Clef**, a decision model, at every game tick —
with an LLM escalation path for complex actions and chat.

The thesis: a typed decision model (single forward pass, no text generation, calibrated
probabilities) can handle 95%+ of bot cognition — grinding, farming, idling in town,
taking level-appropriate quests, party/guild formation, premade chat phrases — and only
fall back to a generative LLM for free-form chat and complex decisions. Goal: measure
how fast and dynamic a "living" MMO world can be pushed on a single machine.

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                    rAthena (C++)                        │
│   login:6900   char:6121   map:5121   + MariaDB        │
└──────▲───────────────────────────────▲─────────────────┘
       │ raw RO wire protocol          │ (same protocol)
       │ (clientless connections)      │
┌──────┴─────────────────────────────────────────────────┐
│                  Bot runtime (per bot)                  │
│  ┌───────────────┐    low-confidence / complex / chat  │
│  │ Clef decider  │──────────────┐                      │
│  │ (every tick:  │              ▼                      │
│  │ state + ~15   │    ┌──────────────────┐              │
│  │ noul/choice/  │    │  LLM (small Qwen │              │
│  │ score Qs)     │    │  local first,    │              │
│  └───────────────┘    │  remote later)   │              │
│         ▲             └──────────────────┘              │
│         │ SystemOne API                                  │
└─────────┼───────────────────────────────────────────────┘
          │
┌─────────┴───────────────────────────────────────────────┐
│  Clef-Flash (9B) via llama.cpp — POST /v1/systemone     │
│  one forward pass → probability per option, no gen      │
└──────────────────────────────────────────────────────────┘
```

Key properties:

- **Bots are clientless** — they speak the RO packet protocol directly (login →
  char → map servers), so each bot is just a socket + a brain. Indistinguishable
  server-side from a real player.
- **Clef does the routine work** — every tick, the bot serializes its state (hp/sp,
  position, nearby players/monsters, inventory, party invites, recent chat) and asks
  ~15 typed questions. The answer arrives as probabilities in one pass (~sub-second).
- **Premade chat lives in Clef's choice space** — "LFP" (looking for party), "buffs
  plz", greetings etc. are just options on a `chat_premade` question; the bot emits
  them with zero LLM involvement.
- **LLM escalation is the exception** — free-form replies, complex multi-step
  decisions, and low-confidence Clef outputs go to a small local Qwen instruct model
  (provider abstraction allows a remote API later).

## Layout

```
rathena/            fork of rathena/rathena (submodule, branch bot-infra) — server-side
                    bot support lands here; upstream tracked via `upstream` remote
spikes/
  001-clef-local/    Clef-Flash running locally behind /v1/systemone + latency bench
  002-rathena-up/    rAthena + MariaDB via nix flake devShell + clientless handshake test
  003-clientless-limbs/  (pending) move/attack/loot/chat/party over raw packets
  004-brain-loop/    (pending) 5-10 bots with full Clef tick-loop brains
dashboard/          Rust web dashboard (own Cargo workspace) — observer + control
                    plane over the WorldFeed contract (ADR-007/008)
```

Each spike has its own `README.md` ending in a `## Verdict:` block.

## Running

Each spike directory documents its own setup (see its README). The host is NixOS —
all dependencies come from nix (`nix develop` in the relevant directory).

## Status

Spikes 001 and 002 in progress. Verdicts land here as they complete.
