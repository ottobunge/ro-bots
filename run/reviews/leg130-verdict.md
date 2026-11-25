# leg-130 verdict — economy peaks (16 sellers, +234z, kills 42); s01 re-trap persists as a LAST-POSITION defect; attackers rotate down to 21

Leg 130 ran Wed 2026-11-25 14:00–15:30 Madrid (schedule `[[2,14.0,15.5]]`, 29 personas) on
main `bf1dfa69`. Shepherd launch 13:40:46 via `systemd-run --user --unit=leg130-runner`
(duration 7454 = close+900, RuntimeMaxSec 8354), preflight green (DECIDE-OK 0.47s
answers=10 warm, chat 200, all four e2e containers up, no stale runners). Receipt
`population-receipt-130-1795610453.json` close-write verified ON DISK at 15:30 with the
unit still active (kill-safe shape); clean wind-down `DONE: steps 22210, errors 0` at
15:45, unit inactive.

**Bars: 3 of 5 met** — kills MET, sells/zeny MET, close-write MET; attackers FAILED
(21 vs bar 26); s01 FAILED-as-shaped (pinned all window; the respawn clause was never
exercised because the agent never died).

## Bars

1. **s01 xXHyupunchXx no re-trap — FAILED as-shaped, and the defect moved one level up.**
   The savepoint correction (save_map/x/y → pay_fild04 (20,165), coordinator-applied
   pre-launch) is real but CANNOT fire without a death: s01 logged in at its LAST
   position — leg-129's logout had re-poisoned last_map/x/y back to (163,177) — and the
   cell is the same sealed unwalkable pocket. It stayed pinned the entire window: 168
   runner samples, 1 distinct cell, `stuck_cell_exhausted 8`, 36 stuck lines naming
   (163,177), 106 decisions, 0 moves, logout row pay_fild04 (163,177) zeny 0. No death
   event occurred (nothing in the pocket can kill a pinned agent and nothing drains HP),
   so the corrected respawn path never ran — **the savepoint correction remains
   unvalidated live**. Class framing: login-at-last-position re-traps after every
   logout from the pocket; a savepoint fix alone cannot clear a pocket the agent
   re-enters on login.
2. **Attackers >= 26/29 — FAILED, 21/29** (leg-129: 26/29). Rotation, not collapse:
   leg-129's three zero-authored all improved or held (g00m03 → 22 atk/4 kills, s03 →
   11 atk/3 kills; g02m01 still zero), but a NEW zero cohort of 8 appeared
   (`pop_0003_g00m01` RinceNyan, `pop_0003_s00` YuffieFy81, `pop_0069_g02m01`,
   `pop_0069_g03m00`, `pop_0069_g03m02` (a leg-129 killer, now 0), `pop_0069_g03m03`,
   `pop_0069_g04m00`, `pop_0069_s01` pinned). Three of the zero cohort were the window's
   biggest sellers (RinceNyan +34z, YuffieFy81 +35z, zeny_hunter +8z): merchant trips
   displace attacks. Sell participation doubled (10 → 16 sellers) while attackers fell
   (26 → 21) — the two fight for the same decide budget, the 2026-11-24 chat-era shape
   returning through the merchant lane. 16 of 21 attackers authored >= 3 attacks; the
   funnel volume held.
3. **Kills >= 30 — MET, 42** (leg-129: 39, +8%). Per-attacker 2.00 (leg-129 1.5 — the
   participation dip bought back kill volume). Funnel: 107 attacks authored → 180
   swings → 3,563 damage → 42 kill_credits; drops_seen 82, pickups 16 (floor-ingest to
   pickup conversion is the funnel's weakest link this window). picklog M rows +42 in
   window — correlates with kill_credits exactly, as in leg-129.
4. **Sells >= 8 distinct, zeny vs 2,789 — MET, best sell window of the era.** 16
   distinct sellers, 18 zenylog S-rows summing +234z; fleet zeny 2,789 → **3,023**.
   Per-persona reconcile EXACT: 16 personas moved (sum +234), 13 unchanged. Top movers:
   RinceNyan +34, YuffieFy81 +35, zeny_wing +40, LunaHunter +29, RinceNyan-trip
   partner PoringMuffin14 +17 → 787z (fleet's richest). Post-sell travel visible:
   PoringMuffin14/xXAerofyXx/rince_ko/sora_sama closed on prt_fild06.
5. **Receipt close-write — MET** (on disk 15:30, unit active; ad3d2ce0 shape held).

## DB readback (docker-run client sidecar on ro-bots-e2e_default; secret read inside the container only; DB UTC vs runner CET)

- Fleet zeny 2,789 → **3,023** (+234; 16 movers / 13 unchanged — see bar 4).
- zenylog in-window: 18 S-rows, all type S, 13:01–14:09 UTC — reconciles to the
  per-persona delta exactly.
- picklog totals M269 → **311** (+42), P129 → **151** (+22), L183 → **238** (+55),
  S110 → **139** (+29) — every baseline advanced; M-delta == kill_credits.
- Levels static: 26 chars base 10, 3 at base 11 (RinceNyan, PipinWalker, xXLunasongXx).
- Close positions: 24/29 prt_fild08 grounds, 4 prt_fild06 (post-sell travel), s01
  pay_fild04 (163,177) (the pocket).

## Health

- steps 18,871 at close (22,210 at DONE via post-close drain), step_errors 0.
- Transport: 29 one-shot TRANSPORT DOWN (one per agent), all recovered, none exhausted;
  1 connect RuntimeError (g02m02 — recovered, finished top attacker 54 atk/5 kills).
- Decide backend: 12 PlayingBackendError decide timeouts absorbed by the runtime
  (small saturation footprint this window; no wedge).

## Decisions taken

- `seed-zeny.json` advanced to the post-window fleet **3,023** (zeny CHANGED): 16
  personas moved, 13 verified unchanged against the DB, delta reconciles exactly
  against the 18 zenylog rows.
- Receipt, verdict, wiki/log.md entry, seed-zeny.json committed in ONE commit,
  explicit paths, pushed.

## Named next signature

**s01 last-position re-trap (primary).** The savepoint correction cannot help while
login uses last_map/x/y: every logout from (163,177) re-seeds the trap and no runtime
path extracts a pinned agent from the sealed pocket (leg-129 GAT-verified: nearest
walkable (182,158), Chebyshev 19). Two-part fix: (a) re-apply the operator last-position
reset (163,177 → 20,165) before leg-131 — the DB write leg-129's shepherd proved;
(b) close the class — popgen must verify savepoint walkability at seed time (defect
recorded 2026-11-23), and/or the runtime should detect an unwalkable login cell and
request savepoint relocation server-side instead of burning stuck-cell budgets.

**Attacker/seller budget competition (secondary).** As sell participation doubled,
attackers fell 26 → 21 with a fresh zero-authored cohort dominated by big sellers and
g03/g04 members. Watch leg-131: if the rotation persists, cap merchant-trip duration or
author attacks immediately post-sale, so the economy boom stops buying participation
losses. Also watch the pickup funnel (drops_seen 82 → pickups 16).
