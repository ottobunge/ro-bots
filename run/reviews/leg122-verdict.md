# LEG-122 VERDICT — farm combat throughput (05a89151) first live validation

Window: Mon 2026-11-23 22:30:34 -> 00:07:18 CET (receipt swing_conversion span), schedule
`[[0,22.5,23.9]]`, 29 personas (pop_0003 x7 + pop_0069 x22). Launched 22:30:26 immediately on
preflight green; unit `leg122-runner`, duration 5678 s, RuntimeMaxSec 5978, log
`/tmp/population_leg122.log`.

Preflight: DECIDE-OK 0.60s answers=10 (:8091), :8092 health 200. Post-launch the shared
:8091 saturated (probe 13.96s/10 mid-window) but never wedged.

## Health (clean)

- 11,079 steps, 0 step errors; 29/29 online across the whole scheduled window.
- One transient TRANSPORT DOWN (pop_0069_g00m00 keepalive send, t~4900) self-recovered;
  transport_recovery: 0 rebuild attempts, none exhausted. Clean logoff at close.
- Receipt written BEFORE unit exit (00:07, unit inactive on its own — no rtmax kill).
- Decide: 10,471 ok / 3,090 capped = **22.8% capped** (best recent window; leg-113 was 57%);
  TRUE success p50 13.62 s / p90 14.62 s — cold-prefill dominated, admission-side, not a wedge.

## HEADLINE BAR: fleet kills >= ~26 — NOT MET (21, 81% of bar)

Fleet `swing_conversion_v1` (wire-observation coverage, all 29 agents):

| stage | leg-121 | leg-122 | lift |
|---|---|---|---|
| attacks_authored | 34 | 124 | 3.6x |
| swings_sent | 20 | 93 | 4.7x |
| damage events / dealt | — | 83 / 1,927 | — |
| kill_credits | ~6 | **21** | 3.5x |
| base / job exp | — | 54 / 34 | — |
| drops_seen | — | 20 | — |
| pickup attempts / success | — | 6 / 4 | — |
| unattributed exp events | — | 0 | — |

Active combat agents: 11/29.

## Bars 2+3: MET

- **Taps fire and attribute: MET.** The combat-intent attribution chain produced a populated
  `swing_conversion_v1` block for all 29 agents with per-species rows, refusal reasons and
  0 unattributed exp events. Caveat stated plainly: the literal tap strings
  (combat_intent/combat_pump/attack_gate/kill_credit/drops_seen/pickup_attempts) never printed
  to the runner log (0 greps all window) — the data landed in the receipt block instead. The
  instrumentation works; its log-line rendering did not appear.
- **Authored->swing->kill conversion lifts: MET** (table above). Swing->damage conversion 89%
  (83/93). Refusals named: pending_walk 22, target_not_visible 5, cooldown 2,
  out_of_melee_range 2.

## Sell side (secondary): 0 conversions — zeny flat

- Fleet zeny 1746 == seed (unchanged); zenylog 27 == baseline 27; picklog S 44 == 44.
- 1 TalkToNpc all window. Merchant arm drained with `no_stock_below_zeny_floor`
  (zeny 8-39 < floor 50, **stock=0 has_stock=False**) while inventories hold sellables
  (909 x5, 915 x2 fleet) — the loot->stock admission did not register picked-up items.
- Loot ground truth: picklog M 89->107 (+18 drop rolls ~= drops_seen 20), P 51->57 (+6 player
  pickups vs taps 6 attempts / 4 success), L 27->41 (mob-GID rows, not agent looting).

## Participation leak (the kills gap)

18/29 agents authored ZERO attacks. The pop_0003 group and several solos stayed in
prontera/prt_in socializing all window: Say 7,415, GuildInvite 266, FoundGuild 14,
PartyChat 170, InviteToParty 26. The combat-intent pump only engages agents that reach a field;
the goal layer never sent most of the fleet to one tonight.

## NAMED NEXT SIGNATURE (leg-123)

Two defects, both upstream of the now-proven conversion funnel:

1. **Combat participation spread**: 18/29 authored 0 attacks because they never left town —
   goal/goal-layer sends agents social-first even inside a farm-scheduled window. Needs the
   schedule window to bias farm travel (or the combat pump to author travel, not just intent).
2. **Loot->stock admission**: picked-up sellables never became merchant-arm stock
   (stock=0/has_stock=False against real inventory rows) -> 0 sells, zeny flat. The post-pickup
   stock admission (f188bf46) did not fire for tonight's pickups.

Suggested leg-123 bar: >= 20/29 agents with >= 1 authored attack AND >= 1 sell conversion
sourced from in-window loot.

## Artifacts

- Receipt: `run/plain_host_receipts/population-receipt-122-1795469434.json` (3.5 MB)
- Runner log: `/tmp/population_leg122.log` (unit leg122-runner, DONE steps 11079 errors 0)
- Traces: `.work/runtime/population-live/traces/` (window-filtered counts only; the tree is
  cumulative across legs)
- DB readback: via ro-bots-e2e-mariadb-1 (`/tmp/leg122_readout.sql`), UTC rows.
