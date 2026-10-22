# Agent Wants System (Sims-style motivation model)

Design for motivation-driven agent behavior. Each agent carries a set of
**wants**, each a numerical score **0 (unsatisfied) … 100 (satisfied)**.
Wants decay over time at rates modulated by the agent's personality; actions
in the game satisfy them. The want block is part of every decide context, so
Clef chooses actions that serve the currently most-pressing wants — including
socializing, switching characters, or creating a new one.

---

## 1. The wants

| Want | What it measures | Base decay / game-hour | Satisfied by |
|---|---|---|---|
| **Power** | leveling drive | 6/h | kill (+1 per kill, +3 vs higher-level mob), level-up (+25), quest turn-in (+20), party EXP share (+1/tick while sharing) |
| **Wealth** | zeny accumulation | 4/h | sell items (+1 per 10 zeny gained), loot valuable (+2), quest reward (+10); buying (-10), death (-5) |
| **Equipment** | build/gear progress | 3/h | equip a planned item (+20), loot a wanted item (+8), zeny crosses a budget tier (+10); failed purchase (-5), death (-4) |
| **Social** | belonging, group presence | 5/h | join party (+15), receive invite (+8), party chat exchange (+3 each), buff/heal a friend (+4), group objective step (+5) |
| **Novelty** | variety, discovery | 4/h | new map (+12), new monster species (+6), new quest (+15), changing activity (+4); hour 3+ of the same grind cell (-2/h extra) |
| **Comfort** | safety, downtime | 3/h | idle in town (+2/tick while resting), Kafra rest (+10), safe low-risk activity (+1); death (-25), HP<25% (-3/tick), dangerous map (-2/h) |
| **Competence** | mastery, solo skill | 4/h | solo kill (+2), kill a mob 5+ levels above (+10), win a fight started at <30% HP (+8); death (-15), long miss streak (-2) |
| **Friendship** (per relationship) | bond with a specific friend | 2/h per friend (weakest bond decays) | co-presence same map (+1/10min), joint kill (+2), party together (+4), received gift/help (+6) |
| **CharSwitch** (special) | itch to play another character | 1/h + triggers | logging another roster character (+60), creating a new character (+100); nothing else satisfies it |

Clamp all scores to [0, 100]. Decay applies per in-game hour while online
(offline wants decay at 25% rate — characters "miss" their agent).

## 2. The CharSwitch want in detail

Rises faster when any of these hold (added to base decay):

- +2/h per full hour of the current character session beyond the second hour
- +5/h while the agent's friend group is **new** (no member has a character
  at level 30 or higher) — fresh groups want fresh starts together
- +3 one-shot when a friend announces a character change in chat
- +2/h if the agent's other characters are within 5 levels of the current
  one (grass-is-greener)

Satisfied only by actually switching to another roster character (+60) or
creating a new one (+100).

**New-character creation** is a vanishing-probability roll, checked only when
`CharSwitch > 80`:

```
p_create = 0.10 * personality.create_factor * (1 - chars_in_roster / personality.char_cap)
```

If the roll fails, the agent switches to an existing roster character
instead (or keeps playing and the itch keeps building). Roster cap is
personality-defined (4–6).

## 3. Personality types

Each personality is a per-want **decay multiplier** (higher = that want
becomes unsatisfied faster, i.e. it dominates behavior) plus a roster cap
and a create-factor. One multiplier row per personality; the tables above
show base rates.

| Personality | Power | Wealth | Equip | Social | Novelty | Comfort | Competence | Friend | CharSwitch | Roster cap | create_factor |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Achiever** | 2.0 | 1.2 | 1.3 | 0.6 | 0.8 | 0.5 | 1.5 | 0.7 | 1.0 | 4 | 0.6 |
| **Socializer** | 0.5 | 0.7 | 0.8 | 2.0 | 1.0 | 1.2 | 0.6 | 2.0 | 1.4 | 6 | 1.2 |
| **Explorer** | 1.0 | 0.8 | 1.0 | 0.8 | 2.0 | 0.4 | 1.2 | 0.9 | 1.3 | 5 | 1.0 |
| **Tycoon** | 0.8 | 2.0 | 1.5 | 0.7 | 1.2 | 0.8 | 0.9 | 0.8 | 0.9 | 4 | 0.5 |
| **Casual** | 0.4 | 0.6 | 0.7 | 1.2 | 1.5 | 2.0 | 0.5 | 1.1 | 1.2 | 6 | 1.1 |
| **Competitor** | 1.5 | 1.0 | 1.1 | 0.9 | 0.9 | 0.3 | 2.0 | 0.8 | 0.8 | 5 | 0.7 |

Behavioral signatures that fall out of these numbers:

- **Achiever** chains grind sessions, barely socializes, few characters.
- **Socializer** re-joins parties constantly, keeps a big roster, is the
  first to roll a new character when the group is new.
- **Explorer** never grinds one cell for long, roams maps, tolerates danger.
- **Tycoon** loops shop trips, hoards, treats gear as an investment.
- **Casual** towns a lot, plays safe, changes characters often out of
  novelty.
- **Competitor** seeks fights above its level, ignores comfort entirely.

popgen assigns a personality per agent (with the friend group mixing
personalities — a Socializer in an Achiever group is the interesting case).

## 4. Decide-context integration

Every decide request carries a compact want block (~9 lines, ≤150 tokens):

```
wants: Power 34↓ Social 71↓ Novelty 55→ Comfort 82 Wealth 12↓↓
top_want: Social 71 (partyless for 2h; friends NyxSong+RinceNyan online)
char_switch_itch: 44 (group is new: no member >= level 30)
```

`top_want` is the highest-urgency want (lowest score × decay pressure).
Clef's action vocabulary already covers the satisfiers: grind, loot, sell,
shop, seek-party, party-chat, idle-town, travel, switch-character (new).
The decide answers gain one question — `which_want_to_serve` — so the model
can reason about motivation, not just mechanics.

## 5. Runtime wiring

1. `src/robots/society/wants.py` — `WantState`: scores, personality
   profile, `decay(hours_online)`, `satisfy(want, amount, reason)`,
   `top_want()`, `decide_block()` (the ≤150-token context), the
   CharSwitch roll.
2. Runtime satisfaction hooks (event → want-satisfaction map):
   kill, level-up, loot, sell, buy, party-join/leave, chat-exchange,
   buff, death, map-change, quest — all already observed by the runtime.
3. Idle-watch interplay: the idle review's decide block carries the want
   block, so a forced review on an idle agent is motivation-aware — an
   idle Socializer goes looking for its party; an idle Achiever re-plans
   the grind.
4. CharSwitch actuation: the account already holds multiple characters;
   switching = disconnect → char-select → reconnect as the other
   character (the runtime's reconnect path reused); creation = the
   char-create packet once, then the normal flow. Both emit memory
   entries and the group-objective updates.
5. popgen: the personality assignment per agent + the per-character
   level brackets so "new group" is a real state.

## 6. Acceptance

- Want scores decay online/offline per the tables, clamped 0-100.
- The decide payload carries the want block; the top_want changes the
  chosen action in at least the observable cases (the idle Socializer
  seeks the party; the idle Achiever re-plans the grind).
- A new-group agent with CharSwitch > 80 rolls creation once per the
  vanishing probability, otherwise switches to the roster.
- The rosters never exceed the personality cap.
