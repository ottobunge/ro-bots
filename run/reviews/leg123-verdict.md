# LEG-123 VERDICT — Tue 2026-11-24 03:00-04:30 Madrid (CET)

Runner: `leg123-runner` (systemd-run --user, launched 02:20:26 CET, duration 8674s,
RuntimeMaxSec 8974s). Repo HEAD at launch: `cc56be53`. Schedule
`run/worlds/population-live/schedule-leg123.json` ([[1,3.0,4.5]]), 29 personas.
Validation target: `205408c8` (keepalive field travel + ACK-gated loot->stock admission).

## INFRA FINDING FIRST: THE RECEIPT WAS LOST

`population-receipt-123-*.json` does **not exist**. The runner overshot its own
`--duration` deadline by ~265s (last sample t=8939.4 vs duration 8674) and the
RuntimeMaxSec backstop SIGTERM'd the unit at 04:50:00 (`Result: timeout`, Main PID
1941452 killed) **before the receipt write**. Three prior legs (119-122) wrote
receipts before unit exit; this leg's post-close drain exceeded the +300s backstop
margin. The runner died cleanly with the unit (no orphan process).

Salvage readout below is built from the per-agent JSONL traces
(`.work/runtime/population-live/traces/`, window-filtered 2026-11-24 02:00-03:31 UTC),
the runner log (`/tmp/population_leg123.log`), and the e2e DB readback. Per-agent
evidence is complete; only the receipt artifact (swing attribution taps, frame
counters) is missing — kill attribution is therefore a floor, not an exact count.

DB access note: `docker exec` broke this session (crun `oom_score_adj` write denied —
user manager runs at oom_score_adj 800; crun cannot lower it; exec-only, `docker run`
unaffected). Readout ran via a throwaway client sidecar on `ro-bots-e2e_default`.

## BARS

### Bar 1 — >= 20/29 agents with >= 1 authored attack: **NOT MET — 16/29**

Improvement over leg-122 (11/29 -> 16/29; zero-attack agents 18 -> 13). 140 attacks
authored fleet-wide (leg-122: 124), 18,570 swing observations (leg-122: 93 — a 200x
engagement explosion among the attacking cohort). The `goal_field_routed` keepalive
tap fired 3,140+ times for 9 distinct bots (log-side; char names NyxSong,
PipinWalker, RinceNyan, xXLunasongXx, PoringMuffin14, zeny_wing, rune_walker,
xXHyubladeXx, LunaHunter).

The 13 zero-attack agents are 11 chat-dominant town socializers
(pop_0069 NyxNyan18, KafraMuffin52, AeroSong25, aero_song, TalonWind, ZenySong,
RinceSong, sora_sama, doram_hunter, HyuStar71, VelRin85 — 116-279 `chat_sent` each,
37-59 state ticks, parked in prontera) plus 2 travelers (xXHyupunchXx reached
pay_fild04 with 0 attacks; pop_0069_g02m00-class idle). The chat-drain starvation
shape persists: 4,331 chats fleet-wide, and the keepalive field travel reached only
9 of the 11 socializers — the goal layer's chat premades keep re-claiming the tick.

### Bar 2 — >= 1 sell conversion from in-window loot: **MET — 6 conversions, +52z**

Fleet zeny 1746 -> 1798 (+52), exactly the 6 in-window zenylog S-rows (baseline 27
-> 33), zero in-window purchases:

| UTC time | char | persona | amount |
|---|---|---|---|
| 02:04:52 | rune_walker | pop_0069_g04m02 | +5 |
| 02:07:29 | xXHyubladeXx | pop_0069_g03m01 | +10 |
| 02:22:26 | misu_drop | pop_0069_g01m01 | +11 |
| 02:38:27 | LunaHunter | pop_0069_s00 | +6 |
| 02:47:31 | zeny_hunter | pop_0069_g02m01 | +10 |
| 03:21:43 | xXAerofyXx | pop_0069_g00m02 | +10 |

Strict in-window-loot link: 3 `stock_admission_fired` taps (the 205408c8 ACK-gated
loot->stock admission) — misu_drop (item 935 Clover) and zeny_hunter (item 909
Jellopy) BOTH converted to sales in-window, i.e. the admission -> merchant-arm ->
dealer -> zenylog chain closed on loot picked up during this leg. The third tap
(YuffieFy81, item 915) armed the arm but its counter trip completed without a sale
(its 915 is still held). The other four converters sold pre-held stock.
`_refuse_empty_counter`/dealer-ring taps: 11 `dealer_counter_yield` (reason=completed),
0 `sell_contact_gates` refusals — the FIFO rotation admitted cleanly.

### Secondary — kills vs leg-122's 21: **floor 13-15, attributed count lost**

picklog in-window: 15 M rows (drops: 705 x5, 909 x3, 512 x2, 915 x2, 938 x2, 935 x1),
14 L, 3 P, 11 S. In-view `ItemDrop` world events: 13. Kill-commit attribution lived in
the lost receipt. Swings did NOT convert to kills proportionally (18,570 swings vs a
~15-row drop floor): `target_species_skipped_expless` fired 603 times — the
target-species expless filter (src/robots/app/target_species.py:43) rejected ~600
candidate targets, and `attack_refused` only 8 (the gates are quiet; the authoring
filter is the throttle). 603 `DamageTaken`-adjacent events (134 DamageTaken).

## DECIDE HEALTH

7,414 ok / 1,452 capped (16.4% capped — best since leg-110's 0%; leg-122 was 22.8%).
TRUE decide p50 13.01s / p90 14.28s — 6x slower than legs 121-113 (~2s) but
uniform across agents and stable all window; admission-side improvement outweighed
the slower cadence. Startup burst: 30 PlayingBackendErrors during the login stagger
(03:00-03:05), sessions kept for retry (the known resilience path); errors stopped
accumulating after 03:20.

## SOCIAL / WORLD STATE

6,499 chat-heard / 4,331 chat-sent; parties persisted (party_ids set on 24/29
chars); guilds held (NyxSong guild 2, PipinWalker guild 3). End positions: 5 agents
prontera (sellers/socializers), 20 prt_fild08, 3 prt_fild06, 1 pay_fild04
(xXHyupunchXx odyssey travel). Inventory: 28/29 hold the Knife (1201); PoringMuffin14
still holds 1204; held Chrysalis 915 piles sold down to 1 held (YuffieFy81,
KafraMuffin52).

## VERDICT

**PARTIAL 1/2 bars.** Bar-2 (sell conversion from in-window loot) is MET with strong
mechanism evidence (admission taps -> conversions). Bar-1 (field participation) is
NOT MET at 16/29 vs the 20/29 bar, though participation improved 11/29 -> 16/29 and
engagement among attackers exploded (18,570 swings). The receipt loss is a new infra
defect: post-close drain exceeded the +300s RuntimeMaxSec margin — next legs must set
RuntimeMaxSec = duration + 900 (or the runner's stop path must honor `--duration`
promptly at loop granularity).

## NAMED NEXT SIGNATURE

The **town-socializer field gate**: 11 agents chat 116-279 times in prontera, tick
37-59 state ticks, and never reach a field — the keepalive field travel reached only
9 bots and chat premades re-claim the goal each heartbeat. Lever: once field-routed,
HOLD the field goal for a bounded persistence window against chat re-claim (or decay
per-window chat quota), so the routed 9 becomes the routed 20+. Secondary lever: the
expless-target filter rejected ~600 attack candidates (`target_species_skipped_expless`)
— farm plans on expless-heavy maps should re-target walkable EXP species before
roaming. Infra carry: RuntimeMaxSec = duration + 900 for the drain.

## ARTIFACTS

- No receipt (lost — see above). Traces: `.work/runtime/population-live/traces/pop_*.jsonl`
  (29 files, window 02:00-03:31 UTC complete).
- Runner log: `/tmp/population_leg123.log` (taps quoted above).
- DB readback: char/zenylog/picklog/inventory queries via client sidecar on
  ro-bots-e2e_default (SQL preserved in-session at /tmp/q123.sql).
- seed-zeny.json updated to post-window values (fleet 1798) — committed with this
  verdict per the zeny-changed rule.
