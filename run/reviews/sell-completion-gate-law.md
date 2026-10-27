# The sell-completion gate: the law for the NPC shop loop (ro-bots)

Status: DRAFT (research slice; production `src/` is READ-ONLY here).
Author: the research sub-agent (law slice). Owner of the port: the coordinator.
Scope: the sell half of the NPC shop loop only — click 0x0090 -> ZC_SELECT_DEALTYPE
0x00C4 -> CZ_ACK_SELECT_DEALTYPE 0x00C5 type 1 (`native_gameplay.sell_open`) ->
ZC_PC_SELL_ITEMLIST 0x00C7 (rows: index/price/overcharge) -> sell rows -> zeny.

---

## 0. The established evidence this law rests on (not re-derived)

- **The wire is healthy.** `.work/engagement-diagnosis/c7_probe.py` (2026-10-27 18:54,
  against the LIVE e2e dealer) proved the full frame exchange:
  `0x0090` click -> `0x00C4` -> `0x00C5` type 1 -> **ZC_PC_SELL_ITEMLIST 0x00C7
  ARRIVES** (14 bytes, one row: Emperium 714 @ 1z). Zero frame-level defects.
- **The runtime never progressed.** Leg 28
  (`run/plain_host_receipts/population-receipt-28-1793096707.json`) shows agent
  `pop_0003_g01m00` (PipinWalker) minting 32 `NpcShopSellOpen` with ZERO completed
  sells; `npc_stage` went `unsupported_shop` (t=3641.4) -> `blocked` (t=3731.5) and
  STAYED blocked; zeny stayed 0 for the whole window.
- **The agent held sellable stock the whole time.** The leg-28 trace
  (`.work/runtime/population-live/traces/pop_0003_g01m00.jsonl`) shows
  `state_tick` `inventory_counts = {'714': 1, '909': 1}` continuously from 11:20 to
  11:39 UTC — item 909 (Jellopy) is in `SELLABLE_ITEM_IDS`
  (`src/robots/app/scripts.py:201`), so `shop_sellable_stock` was 1 the entire time.
  **The sell was never blocked by "nothing to sell".**

---

## 1. THE MECHANISM — why the runtime did not progress C7 -> sell

### 1.1 The guard chain, enumerated, per decide tick

The decide tick's shop path is `mechanical_actions` (`src/robots/app/playing_runtime.py:1674`)
-> `_shop_loop_mechanical` (`:1037`) -> `_shop_loop_action` (`:1062`). Every guard,
in evaluation order:

| # | Guard | Source | Leg-28 value | Verdict |
|---|-------|--------|---------------|---------|
| 1 | an authored `NpcShopPurchase/NpcShopBuySelection/NpcShopSell/NpcShopSellOpen` already present | `:1065-1069` | none authored (the trace shows the agent authored `TalkToNpc`, never a shop action) | PASS |
| 2 | `state.alive is True` | `:1070` | alive | PASS |
| 3 | `self._npc.failed` (a denied dialogue) | `:1070` | False while the stage is `unsupported_shop` | PASS |
| 4 | `self._npc.cancel_uncertain` | `:1070` | False | PASS |
| 5 | `_pending_sell(tracker)`: a received C7 exists, its `seq` not already sent, `shop_sell_entries` non-empty | `:1080-1093` | **`tracker.view.sell_lists` is EMPTY** | **FAIL (by consequence)** |
| 6 | `_buy_mint_attempt()` | `:1095-1104` | `self._shop_context.offer` is None (no C6) | PASS (no buy attempted) |
| 7 | `_sell_open_action(tracker)`: stage is `unsupported_shop`, the epoch dedupe key is not yet issued, `shop_sellable_stock > 0` | `:1106-1120` | stage `unsupported_shop`; dedupe key NOT issued; stock = 1 | **PASS -> mints `NpcShopSellOpen`** |

So the tick **minted** the action. The failure is one level deeper, in the
DISPATCH of the minted action, which is a separate call
(`agent_runtime.execute_actions` -> `_perform` -> `client.perform_native`,
`src/robots/app/agent_runtime.py:1179-1190`, `:1282-1286`):

`perform_native` (`:736`) -> `_dispatch_shop_action` (`:717`) -> `_send_sell_open` (`:1133`):

| # | Guard in `_send_sell_open` | Source | Leg-28 value | Verdict |
|---|---------------------------|--------|---------------|---------|
| A | the mint is bound to this exact action + owner | `:1136-1137` | bound | PASS |
| B | `self._tracker` / `self._npc.view` present | `:1139-1141` | present | PASS |
| C | `_sell_open_request_ready(action, tracker, dialog)` | `:1142`, `:1148-1166` | **see 1.2 — FAILS** | **FAIL** |
| D | `self._npc.requests += 1`; latch `self._sell_open_issued = (opened_sequence, prompt_sequence)`; `self._send_npc(sell_open(npc_id))` | `:1144-1146` | **never reached** | **NOT SENT** |

**The C5 type 1 was never put on the wire.** The 0xC5 never left the client, so the
server never answered with a 0xC7, so guard 5 above could never pass, so the sell
never happened. The chain is self-consistent and terminates exactly at guard C.

### 1.2 The failing check inside `_sell_open_request_ready`

`_sell_open_request_ready` (`:1148-1166`) requires all of:

```
self._npc.requests < 32                                  # :1161
self._sell_actuation_ready(tracker.view)                # :1162
dialog.stage == "unsupported_shop"                       # :1163
fields_match  (npc_id, epoch, sequence, map_name, opened_sequence)   # :1152-1158
```

`_sell_actuation_ready` (`:1026-1035`) requires all of:

```
self._life(view) is True          # alive                      -> True
self._standing is True            # the received SELF pose     -> True
self._stand_pending is None                                    -> None
self._rest_seq is None                                        -> None
self._npc_motion_ready()                                     -> **False**
```

`_npc_motion_ready` (`:1298-1300`):

```python
return tracker is not None and tracker.view.arrival_confirmed and self._pending is None
```

**`tracker.view.arrival_confirmed` is the failing term.**

`arrival_confirmed` is the tracker's `_arrival` flag
(`src/robots/adapters/native_gameplay.py:317`, set at `:742`, `:756`, `:759`).
On a 0x0087 walk frame it is:

```python
self._arrival = (position.x, position.y) == destination      # native_gameplay.py:756
```

i.e. **True only for a ZERO-LENGTH walkok** (from == to). The pinned production
comment at `native_gameplay.py:750-752` states this outright: *"a moving walkok
(from != to) is a walk IN FLIGHT — only a zero-length walkok proves arrival."*

**The agent WALKED to the dealer.** The leg-28 trace shows the agent moving
`(156,156) -> (156,171) -> (156,187) -> (166,202) -> (173,217) -> (173,130)` — a
real, non-zero-length walk. Its final 0x0087 frame therefore left `_arrival = False`,
and **nothing ever sets it back to True** except a zero-length walkok, a map change
(0x0091, `:741-742`) or a 0x02EB entry (`:759`). The agent stood still at
`(173,130)` from 11:25:55 to 11:39:07 with `arrival_confirmed` permanently False.

This is **the same class of defect the w82 fix already cured for the CLICK path.**
Commit `e06dc511` — *"fix: the npc click gate is tracked adjacency, not the arrival
flag — arrival stays False after every real walk (a moving walkok proves nothing
about the destination) and silently dropped in-range clicks (w82 null-offer)"* —
removed the arrival flag from `_talk_npc` and replaced it with tracked adjacency
(`_talk_npc`, `:1305-1332`; the rationale is in the comment at `:1310-1314`).
**The sell-open limb was never given the same treatment**: it still gates on
`_npc_motion_ready()`, which still requires the arrival flag. The click succeeded
(the C4 arrived — the trace proves the stage reached `unsupported_shop`); the
C5 that follows it could never leave.

### 1.3 The reproduction (offline, read-only against production `src/`)

`.work/engagement-diagnosis/sell_gate_probe.py` (this branch) rebuilds the leg-28 shape offline —
entry + map + **a real 0x0087 walk** into the dealer cell + the dealer NPC actor
(0x09FE) + Jellopy stock + the click (`_npc.begin`) + the received 0x00C4 — and then
prints every guard separately. Its output:

```
CASE A: the agent WALKED to the dealer (the leg-28 shape)
  stage                 = unsupported_shop
  arrival_confirmed     = False
  _npc_motion_ready     = False
  _sell_actuation_ready = False
  mechanical_actions -> (NpcShopSellOpen(... opened_sequence=9, prompt_sequence=10),)
  wire.sent             = []
  C5 (0xC5 type 1) sent?= False
  _sell_open_issued     = None
  2nd tick mechanical_actions -> (NpcShopSellOpen(... SAME opened/prompt sequence ...),)
                                                 <- the mint repeats; the dedupe never latched

CASE B: the agent STOOD at the dealer (zero-length walkok)
  arrival_confirmed     = True
  _npc_motion_ready     = True
  _sell_actuation_ready = True
  wire.sent             = [b'\xc5\x00b~\x8e\x06\x01']      <- the C5 type 1 goes out
  _sell_open_issued     = (9, 10)                          <- the dedupe latches
  2nd tick mechanical_actions -> (NpcShopBuySelection(...),)   <- no re-mint of the sell-open
```

CASE A is leg 28. CASE B is the same state with the arrival proof. The **only**
difference is the arrival flag, and it is the difference between 32 dead mints and
a live sell.

### 1.4 Why the opens RE-MINTED — and why the dedupe key advanced

Two separate facts, both visible in the trace, and they must not be conflated:

**(a) The re-mint within one epoch is a direct consequence of the failed dispatch.**
`_sell_open_issued` is latched at `:1145`, i.e. **inside `_send_sell_open`, AFTER
the `_sell_open_request_ready` guard at `:1142`**. When that guard fails, the latch
is never written, so `_sell_open_action` (`:1110`) mints the identical action again
on the next tick. The trace shows exactly this: **8 consecutive mints with the SAME
`(opened_sequence=1220, prompt_sequence=1221)`**, then 8 with `(1224, 1226)`, then
`(1227, 1229)`, then `(1230, 1232)` — 32 in total, in four bursts.

**(b) The key advanced BETWEEN bursts because the dialogue was re-begun, not because
"the server dialog updated".** The `opened_sequence` is the metadata cursor at the
moment `_npc.begin()` ran (`:104` — `NpcDialogue(npc_id, epoch, map_name, sequence,
sequence, "opening")`), so a **new `opened_sequence` means a NEW CLICK**. The trace
confirms a fresh click per burst: a `NpcDialogueReceived` world event with
`stage='opening'` precedes each burst (11:26:09.118, 11:26:30.057, 11:26:50.975).
The receipt's own `npc_stage` column is too coarse to show the re-clicks (its
30s sampler catches only `unsupported_shop` at t=3641.4 and `blocked` at
t=3731.5 — the ~3s `opening` windows fall between samples); the **trace** is the
instrument that resolves the re-click cadence.

**So the answer to the brief's question is: NO — the re-mint was NOT the dedupe key
advancing on server dialog updates.** The key advanced because the runtime **re-clicked
the dealer** (a fresh 0x0090), which is the deny-origin recovery path
(`_retry_blocked_dialogue`, `:781-806`; `_retry_blocked_dialogue_on_tick`,
`:1782-1803`). The dialogue had expired (its 15s/120s deadline, `native_npc_dialogue.py:106-109`,
`:130-136`), was denied with `deny_origin='timeout'`, and the recovery re-clicked.
Each re-click produced a fresh C4 and a fresh `(opened_sequence, prompt_sequence)`
pair; each new pair was again blocked at guard C; each expiry again denied and
re-clicked — until `NPC_RETRY_BUDGET = 3` (`:192`) was spent and the barrier held
the dialogue in `blocked` for the rest of the window (the receipt's `npc_stage`
stays `blocked` from t=3731.5 to the end).

**The loop was: click -> C4 -> mint -> guard C fails -> C5 never sent -> no C7 ->
deadline -> deny(timeout) -> retry re-click -> ... , 4 epochs, budget spent, blocked.**

`self._npc.requests` (the 32-request cap at `:1161`) never fired: `begin()` resets it
to 1 (`:107`) on every re-click, so the counter never accumulated across epochs.

### 1.5 Why "the C7 never reached the tracker" is a symptom, not the cause

The tracker ingests 0x00C7 correctly (`native_gameplay.py:488-489` -> `_sell_list`,
`:716-726`: `<HII` rows of index/price/overcharge, `(len-4) % 10 == 0`), and the
framer knows 0xC7 (commit `c6f16717`). **No C7 ever existed**, because the C5 was
never sent. There is no tracker defect here. The brief's "the C7 either never reached
the tracker, or arrived and the loop did not progress to the sell" resolves to the
first horn, and the reason is upstream of the tracker.

**The tracker's `sell_lists` is EMPTY in leg 28** — confirmed by the fact that
`_pending_sell` (`:1081-1082`) never minted a sell, and by the receipt's zeny 0.

### 1.6 One more latent defect the reproduction exposed (must be fixed in the same port)

`_send_sell` (`:1168-1185`) has a **fail-OPEN** guard:

```python
if tracker is None or self._sell_request_target(action, tracker) is None:
    return
```

`_sell_request_target` (`:1187`) returns a **bool**, never `None`. `False is None`
is `False`, so **the guard never fires** — the sell request is sent even when every
local guard inside `_sell_request_target` says no. The probe's CASE C shows it: with
`arrival_confirmed = False` and `_sell_actuation_ready = False`, the C9
(`b'\xc9\x00\x08\x00\x06\x00\x05\x00'`) was **sent anyway**. The correct comparison
is `not self._sell_request_target(...)`. This is a fail-open where the whole
codebase's convention is fail-closed, and it must be corrected in the same port.

---

## 2. THE COMPLETION-GATE DESIGN

The law's shape, in one sentence: **the shop loop is a state machine over DIALOG
EPOCHS, where an epoch is one received C4 and its one sell-list request; the stage
advances ONLY on received frames; a dead epoch is recovered by a fresh CLICK, never
by a second C5.**

### 2.0 Terms

- **DIALOG EPOCH** — one `begin()` -> one C4 -> one C5 -> (one C7) -> (one C9) chain.
  Its identity is `(npc_id, epoch, opened_sequence)`. `opened_sequence` is assigned
  by `begin()` (`:104`) and is unique per click; the C4's own arrival sequence is
  `dialog.sequence` (`:159`) and is the **prompt** within the epoch, not the epoch.
- **C5** — `CZ_ACK_SELECT_DEALTYPE` type 1, `native_gameplay.sell_open(npc_id)`
  (`src/robots/adapters/native_gameplay.py:80-101`; the type-1 semantics are pinned
  to `rathena/src/map/npc.cpp:2411` `type == 0 -> clif_buylist`, so type 1 ->
  `clif_selllist`, `rathena/src/map/clif.cpp:2265-2280`).
- **C7** — `ZC_PC_SELL_ITEMLIST`, the received sell list.
- **C9** — `CZ_PC_SELL_ITEMLIST`, the sell request (`native_gameplay.sell`, `:103`).

### 2.1 LAW 1 — The actuation gate for the shop limbs must NOT require the arrival flag

**Rule.** The shop limbs' actuation readiness must use **tracked adjacency** (the
agent is within the shop-NPC's range of its tracked position), exactly as the CLICK
limb already does (`_talk_npc`, `:1305-1332`, cured by `e06dc511`). It must NOT
require `tracker.view.arrival_confirmed`.

**Why.** `arrival_confirmed` is a property of the walk protocol, not of the shop.
A clientless client walking to a dealer can never prove arrival (the 0x0087
from != to), so gating the shop on it makes the shop unreachable for exactly the
agents that walked there — which is all of them. The click limb already learned
this; the shop limb must learn the same lesson.

**Concrete change.** Introduce a shop-specific readiness predicate, e.g.

```python
def _shop_actuation_ready(self, view: NativeGameplayView) -> bool:
    """The shop limbs need tracked adjacency, NOT the arrival flag.

    arrival_confirmed stays False after every real walk (native_gameplay.py:756;
    a moving walkok is IN FLIGHT, only a zero-length walkok proves arrival), so
    gating the shop on it makes the shop unreachable for any walking agent -
    the exact defect leg 28 hit (the C5 never left the client). The CLICK limb
    was cured for the same reason (e06dc511, the w82 null-offer). The tracked
    position plus the observed dealer actor is the sufficient range proof.
    """
    return all((
        self._life(view) is True,
        self._standing is True,
        self._stand_pending is None,
        self._rest_seq is None,
        self._pending is None,          # not mid-walk (the real proof of motion)
        self._shop_adjacent(view),      # tracked adjacency to the dealer
    ))
```

`_shop_adjacent(view)` = the observed dealer actor exists, is not walking, and is
within the dealer range of the tracked position — the same predicate
`_talk_npc` uses at `:1315-1327` (actor present, `actor.walking` false, and the
`distance > 3` branch that moves closer). Note `_validate_npc_context`
(`:1291-1305`) already invalidates the dialogue when the actor is missing, is
walking, or is beyond range 3, so the dialogue's own validity already carries the
adjacency proof; the shop readiness must not add a *stricter* one.

**Do not** relax `_npc_motion_ready()` globally — it is used by the NpcNext/NpcSelect
path (`:903`) and by `_npc_self_ready` (`:1537`), where the arrival flag may still
be the right question. Add a shop-specific predicate.

### 2.2 LAW 2 — ONE sell-open per DIALOG EPOCH, latched BEFORE the send

**Rule.** At most one `NpcShopSellOpen` may be **minted** and at most one C5 may be
**sent** per dialog epoch. The latch must be written **when the mint is handed to
the dispatch path**, not inside `_send_sell_open` after its guards.

**Why.** Leg 28 minted 32 opens across 4 epochs because the latch at `:1145` lives
after the failing guard at `:1142`: a failed send never latched, so the mint
repeated every tick. Latching at the mint site makes "one per epoch" a property of
the MINT, which is the only place that can enforce it (the dispatch is downstream
and may legitimately fail for an unrelated reason — a reconnected wire, a changed
owner binding — and those failures must not multiply the opens).

**Concrete change.** Split the single `_sell_open_issued` latch into two, with
different owners:

- `self._sell_open_minted: tuple[int, int] | None` — the **mint** latch, keyed by
  `(opened_sequence, prompt_sequence)`, written in `_shop_loop_mechanical`
  (`:1058-1059`, where `_sell_open_mint` is already recorded) the moment the
  `NpcShopSellOpen` is produced. `_sell_open_action` (`:1110`) reads this latch.
- `self._sell_open_sent: tuple[int, int] | None` — the **send** latch, written in
  `_send_sell_open` (`:1145`) once the C5 is actually on the wire.

The mint latch key must be the **epoch** identity `(opened_sequence, prompt_sequence)`
— exactly what `_sell_open_issued` uses today (`:1110`, `:1145`) — so the
re-mint-within-an-epoch is impossible while a genuine new epoch (a new click, a
new `opened_sequence`) still legitimately mints again.

**Careful:** the mint latch must be keyed on the pair that `NpcShopSellOpen`
carries — `opened_sequence` (the click) and `prompt_sequence` (the prompt) — not
on `dialog.sequence`, which advances on every received C4-family frame (`:159`).

### 2.3 LAW 3 — The stage advances ONLY on received C7 rows

**Rule.** The sell side's progress must be driven by **received frames**, never by
the agent's own send or by a timeout. Concretely:

- The **sell list** becomes available to the loop ONLY when a 0xC7 has been received
  and ingested (`tracker.view.sell_lists`). `_pending_sell` (`:1080-1093`) already
  does this correctly — it is the ONLY producer of `NpcShopSell`.
- The **sell request** (C9) may be minted ONLY within the same epoch as the C7 that
  authorised it, and only once per C7 receipt.

**Why.** The whole leg-28 failure was the loop believing it had made progress
(mints!) while the server had made none. Progress is a property of the received
side. The existing `_pending_sell` already has this shape; the law's job is to make
sure the port does not weaken it, and to add the **epoch binding** it currently
lacks.

**Concrete change — the epoch binding.** `_pending_sell` (`:1080-1093`) currently
reads `tracker.view.sell_lists[-1]` — the most recent C7 — with **no epoch check**.
A C7 received in epoch A must not authorise a sell in epoch B. Bind the C7 to its
epoch:

- The runtime records, at C5-send time, the epoch that the C5 belonged to.
- `_pending_sell` only considers a C7 whose receipt sequence is **after** the C5
  that was sent for the CURRENT epoch, and it must not reuse a C7 already sent
  (`latest.seq in self._sell_sent`, `:1085` — keep this).

The natural implementation is to keep the existing `_sell_sent` deque (`:308`) as
the "already spent" set and to add a per-epoch record of the sequence at which the
C5 was sent, so `latest.seq > c5_sent_seq` is the epoch-scoped admissibility test.

### 2.4 LAW 4 — The no-C7 deadline: a dead epoch is recovered by a FRESH CLICK, never by a second C5

**Rule.** If the C5 of epoch E has been sent and **no C7 arrives within N seconds**,
epoch E is **dead**. The recovery for a dead epoch is a **fresh CLICK (0x0090)**,
which opens a NEW epoch (a new `opened_sequence`). **Never a second C5 in the same
epoch.**

**Why not a second C5.** The C5 is `CZ_ACK_SELECT_DEALTYPE` — an ANSWER to a
received `ZC_SELECT_DEALTYPE` (the C4). The server's handler
(`rathena/src/map/clif.cpp:12256-12271` -> `npc_buysellsel`,
`rathena/src/map/npc.cpp:2387-2418`) does not check the client's dialogue state
beyond `npc_checknear`; but the **client's** epoch is the unit of progress. A
second C5 inside a dead epoch re-sends an answer to a prompt the server has already
moved past — and, on the pinned server, the NPC dialogue has its own idle timeout
(`NPC_SECURE_TIMEOUT_NEXT` / `_MENU` = 60s, `rathena/src/config/secure.hpp:28-40`,
enforced by `npc_secure_timeout_timer`, `rathena/src/map/npc.cpp:1134-1177`), after
which `pc_close_npc` tears the dialogue down. Re-clicking is the only recovery that
re-establishes a real prompt.

**Choosing N.** N must be:
- **long enough** that a healthy C7 is never missed — the probe measured the C7
  arriving within the same second as the C5 (the exchange completes inside one
  round trip; `clif_selllist` is a direct reply inside `npc_buysellsel`), so
  N = **5 seconds** is generous by an order of magnitude;
- **short enough** that a dead epoch is abandoned before the server's own 60s
  dialogue timeout closes the shop, so the fresh click lands on a live dealer.

The pinned constant in the runtime should be explicit and named, e.g.
`SELL_LIST_TIMEOUT_S = 5.0`, beside `NPC_RETRY_CADENCE_S` (`:193`).

**Where the deadline lives.** The C5 is sent through `_send_npc` (`:1146`) — it does
**not** go through `NativeNpcDialogue.request()` (`:195`), so the dialogue's own
5s/15s response deadline (`:106`, `:171-174`) is **not** refreshed by the C5 and
must not be relied on for the C7 window. The epoch's C7 deadline is the runtime's
own, tracked against the epoch.

### 2.5 LAW 5 — Bounded epoch retries, and the deny-origin interaction

**Rule.** The number of epochs spent on ONE sell attempt is bounded. When the bound
is reached, the attempt is abandoned **cleanly** (no further clicks, no blocked
dialogue, the agent returns to its goal) and the failure is recorded.

**Composition with the existing deny-origin recovery — NOT a duplicate.** The
runtime already has a retry mechanism for exactly this class of failure:

- `_deny(origin)` (`native_npc_dialogue.py:138-144`) marks the dialogue failed and
  records `deny_origin`; only `origin == "timeout"` is retryable (`:138-141`).
- `_retry_blocked_dialogue` (`:781-806`) and `_retry_blocked_dialogue_on_tick`
  (`:1782-1803`) re-`begin()` the dialogue (a fresh 0x0090) on a `NPC_RETRY_CADENCE_S`
  cadence, bounded by `NPC_RETRY_BUDGET = 3` per epoch (`:192`).

**The law composes with this: the C7 deadline must REUSE the deny-origin
mechanism, not add a second one.** Concretely:

- When epoch E's C7 deadline expires, the runtime marks the dialogue **denied with
  `deny_origin = "timeout"`** — the same marker `_expire` uses
  (`native_npc_dialogue.py:136`) — so the EXISTING retry path picks it up and
  performs the fresh CLICK. **Do not write a second click path.**
- The sell-side epoch bookkeeping must be **reset by the same `begin()`** that the
  recovery performs, so a new epoch starts with a clean slate (no stale mint latch,
  no stale C5-sent record). `begin()` already resets `failed`, `cancel_uncertain`
  and `deny_origin` (`:110-114`); the runtime's shop-side epoch state must be
  reset alongside it.
- `NPC_RETRY_BUDGET = 3` (`:192`) is the bound. When it is spent, the barrier
  holds (`:790-791`) — which is the correct final state for a shop that cannot be
  reached, but the agent must then **stop minting sell-opens** rather than churn.

**One more requirement.** The retry budget is currently spent **per dialogue**, not
per shop attempt, and the recovery re-click is what advanced `opened_sequence` in
leg 28. Under the new law each retry IS a new epoch (a new click), so the
"one sell-open per epoch" rule yields exactly one C5 per recovery — the leg-28
churn of 8 mints per epoch becomes 1.

### 2.6 LAW 6 — The stage vocabulary the port needs

The dialogue's stage vocabulary (`native_npc_dialogue.py:22-28`) has
`"unsupported_shop"` for the C4. The sell loop needs to distinguish:

- **`unsupported_shop`** — a C4 was received; a C5 is owed for this epoch (this is
  what the stage means today, and `_sell_open_action` keys off it at `:1108`).
- **`sell_list`** — the C7 arrived for THIS epoch; a C9 is owed (the sell-list
  receipt is the only authority; the stage must advance on the RECEIVED C7, never
  on the send of the C5).
- **`selling`** — the C9 was sent; the 0xCB result (`ZC_PC_PURCHASE_RESULT`'s
  sibling `0x00CB`, ingested at `native_gameplay.py:490-491` -> `_sell_result`,
  `:728-732`) is owed. A `result == 0` is success (`:732`).

Note `0x00C7` is **not** in `NPC_RECEIVE_IDS` (`native_npc_dialogue.py:21`) — the
dialogue state machine does not see the C7. Two options, and the law picks the
first:

- **(preferred) Keep the stage machine out of it.** The sell-list/selling progress
  is tracked in the **runtime's** shop-side epoch state, alongside the C5-send
  record and the epoch identity. The dialogue machine keeps owning the click /
  prompt / deny lifecycle. This avoids widening `NPC_RECEIVE_IDS` and the risk that
  a malformed C7 becomes a dialogue deny.
- (rejected) Add 0xC7 to `NPC_RECEIVE_IDS` and give the dialogue a sell stage.
  This couples a variable-length shop receipt to the dialogue's strict
  `_matching_response` geometry checks (`native_npc_dialogue.py:48-57`), which are
  written for fixed NPC-prompt frames.

### 2.7 LAW 7 — the fail-OPEN sell guard must be closed

`_send_sell` (`:1181`) must read `not self._sell_request_target(...)`, not
`... is None`. `_sell_request_target` returns a bool (`:1187-1205`); the current
comparison never fires, so the C9 is sent even when every local guard rejects it
(probe CASE C: the C9 went out with `arrival_confirmed = False` and
`_sell_actuation_ready = False`). This is the one place in the shop path that can
send on a **negative** verdict; the port must make it fail-closed like every other
guard in the file.

### 2.8 The invariants this law protects (the port must not break these)

1. **The received side is the only progress authority.** A C7 is the only thing
   that authorises a sell; a 0xCB result is the only thing that confirms one; a
   received zeny receipt is the only money authority. No send implies no progress.
2. **Fail-closed everywhere.** A guard that says "not ready" must stop the send.
   (Law 7.)
3. **One request per prompt.** One C5 per C4-epoch, one C9 per C7-receipt, one C9
   per received C7 sequence (`_sell_sent`, `:308`).
4. **No send implies a retry.** A refused send must not multiply the mint
   (Law 2), and the epoch's retry must be bounded (Law 5).
5. **The recovery is a CLICK.** A dead epoch is recovered by a fresh 0x0090 through
   the EXISTING deny-origin path, never by a second C5 (Law 4) and never by a
   second, parallel retry mechanism (Law 5).
6. **The arrival flag is not a shop property.** (Law 1.)

---

## 3. THE RED TESTS the coordinator writes BEFORE the port

The coordinator lands the port TDD-gated. These are the RED tests, in the order
they should be written. Each names the state it pins; the file is
`tests/test_shop_sell_loop.py` (the existing home of the sell leg) plus
`tests/test_playing_runtime.py` for the shared `Wire`/`entry`/`map_frame`/
`walk_ack` helpers (`:32-50`, `:270-283`).

**T1 — `test_sell_open_is_sent_after_a_real_walk_to_the_dealer`**
(Pins LAW 1. The leg-28 regression, exactly.)
Wire: `entry()`, `map_frame()`, a **non-zero-length** `walk_ack((170,120),(173,130))`
(a REAL walk — `walk_ack` with differing cells), the dealer actor as a 0x09FE
frame (objecttype 6) at `(172,130)`, an inventory with item 909 x5, a weight frame,
then `_npc.begin(DEALER, epoch, map, cursor, now)` and a 0x00C4 frame.
Assert: `client.perform_native(action)` puts `ng.sell_open(DEALER)` on the wire.
RED today because `arrival_confirmed` is False after a real walk and
`_sell_actuation_ready` therefore refuses.

**T2 — `test_sell_open_readiness_does_not_require_the_arrival_flag`**
(Pins LAW 1 directly, without the wire.)
Assert: with `tracker.view.arrival_confirmed is False` and the dealer adjacent,
the shop readiness predicate is True — i.e. the shop's readiness is a function of
tracked adjacency, not of the walk-arrival proof. RED today (the shop reads
`_npc_motion_ready`).

**T3 — `test_sell_open_is_minted_once_per_dialog_epoch`**
(Pins LAW 2.)
Two consecutive `client.mechanical_actions(state, ())` calls against the SAME
received C4 must yield exactly ONE `NpcShopSellOpen` across both, and the second
call must not re-mint it. RED today: the second call re-mints (the latch is only
written after the send guard, which never passes).

**T4 — `test_a_new_dialog_epoch_mints_a_new_sell_open`**
(Pins LAW 2's other half — the latch must not over-suppress.)
After a second `begin()` (a new click -> a new `opened_sequence`) and its C4, a
fresh `NpcShopSellOpen` IS minted. This is the anti-regression for T3: the dedupe
is per-epoch, not global.

**T5 — `test_a_c7_from_a_previous_epoch_does_not_authorise_a_sell`**
(Pins LAW 3's epoch binding.)
Receive a C7 in epoch A; then start epoch B (a new click + C4) WITHOUT a new C7.
Assert: `mechanical_actions` yields NO `NpcShopSell` — the stale C7 must not
authorise a sell under the new epoch. RED today: `_pending_sell` reads
`tracker.view.sell_lists[-1]` with no epoch check (`:1084`).

**T6 — `test_a_sell_is_minted_once_per_received_c7`**
(Pins LAW 3 / invariant 3.)
With one C7 received and consumed, a second `mechanical_actions` yields no second
`NpcShopSell` (the `_sell_sent` guard, `:1085`). This one should be GREEN today —
it pins existing behaviour the port must not break.

**T7 — `test_no_c7_within_the_deadline_recovers_with_a_fresh_click_not_a_second_c5`**
(Pins LAW 4 — the core recovery rule.)
Send the C5 for an epoch; advance the clock past `SELL_LIST_TIMEOUT_S` with no
C7 arriving. Assert: the wire then carries a **0x0090 click** (a fresh epoch), and
the epoch's C5 count is **exactly one** — the wire contains no second 0xC5.
RED today: nothing detects the missing C7.

**T8 — `test_a_c7_arriving_within_the_deadline_cancels_the_recovery`**
(Pins LAW 4's other half — no false recovery.)
Send the C5; receive the C7 within the deadline. Assert: NO 0x0090 re-click, and
the sell (`NpcShopSell`) is minted from that C7.

**T9 — `test_a_dead_epoch_marks_the_dialogue_denied_with_the_timeout_origin`**
(Pins LAW 5's composition — the deny-origin marker is reused, not duplicated.)
After the C7 deadline expires, assert `client._npc.deny_origin == "timeout"` and
`client._npc.failed is True` — the SAME markers `_expire` uses
(`native_npc_dialogue.py:136`). This is what makes the existing
`_retry_blocked_dialogue` / `_retry_blocked_dialogue_on_tick` pick the epoch up.

**T10 — `test_the_epoch_retries_are_bounded`**
(Pins LAW 5's bound.)
Drive the deadline expiry repeatedly (more than `NPC_RETRY_BUDGET`) and assert the
click count stops growing at the budget, and that the dialogue does NOT mint
further `NpcShopSellOpen`s once the budget is spent.

**T11 — `test_the_sell_request_is_fail_closed_on_a_rejected_target`**
(Pins LAW 7 — the fail-open guard.)
Build a `NpcShopSell` whose `_sell_request_target` would be False (e.g. a
`sell_sequence` that is not the latest C7, or a non-matching epoch). Assert
`client.wire.sent` contains NO 0xC9. RED today: `_send_sell` compares a bool to
`None` (`:1181`), so the request goes out anyway.

**T12 — `test_the_sell_request_carries_the_epoch_of_its_c7`**
(Pins LAW 3 + invariant 1 end to end.)
The `NpcShopSell` the loop mints must be bound to the epoch that received its C7
(and the runtime must refuse a sell whose epoch is not the live one).

**T13 — `test_the_zeny_receipt_is_the_only_money_authority`**
(Pins invariant 1.)
No zeny receipt received -> no zeny claimed. (If the port adds a money projection,
this pins it.)

### 3.1 The RED-test order and the port's TDD discipline

The coordinator writes **T1, T2, T7, T9, T11** first — they are the five that are
RED today and that pin the law's core (the actuation gate, the mint latch, the
deadline, the deny-origin composition, the fail-open guard). Then T3/T4/T5/T6/T8
(the epoch-boundary rules). T10/T12/T13 last.

The port lands TDD-gated: RED first, one slice at a time, in this order:
**(a) Law 1** (T1, T2) — the shop becomes reachable at all;
**(b) Law 2** (T3, T4) — the churn stops;
**(c) Law 4 + Law 5** (T7, T8, T9, T10) — the epoch recovers by a click, bounded;
**(d) Law 3** (T5, T6, T12) — the epoch binding on the C7;
**(e) Law 7** (T11) — the fail-open guard closes.

Each slice must keep the existing green suite green (`nix develop -c task check`;
note the repo's `task` invocation is `task --dir . check` on this host, because
another agent's `pkill -f "[t]ask check"` kills the plain form).

### 3.2 The live proof the coordinator runs after the port

The port is not done until a LIVE leg shows a completed sell. The acceptance
evidence must be:
1. **The trace shows the C5 on the wire** — the `NpcShopSellOpen` action appears
   ONCE per epoch (not 8 times), and the `npc_stage`/`opened_sequence` sequence
   shows one epoch per attempt.
2. **The tracker shows the C7** — `sell_lists` non-empty in the receipt samples
   (the receipt's `npc_stage` column is the visible proxy; a C7-bearing epoch
   advances the stage to `sell_list` under Law 6).
3. **The DB shows the zeny** — the character row's zeny increased by the sold
   items' price. This is the receipt of record (the inventory emptying is the
   second proof).
4. **The 0xCB result is success** — `result == 0` (`native_gameplay.py:732`).

The `c7_probe.py` frame-level exchange is the WIRE proof and it is already green;
it is NOT the port's proof. The port's proof is a completed sell in a live leg.

---

## 4. Citations index

**Production (read-only, cited):**
- `src/robots/app/playing_runtime.py` — `:192-194` (budgets), `:304-310` (shop
  seam state), `:717-734` (`_dispatch_shop_action`), `:736-742` (`perform_native`),
  `:781-806` (`_retry_blocked_dialogue`), `:1037-1060` (`_shop_loop_mechanical`),
  `:1062-1078` (`_shop_loop_action`), `:1080-1093` (`_pending_sell`),
  `:1106-1120` (`_sell_open_action`), `:1133-1146` (`_send_sell_open`),
  `:1148-1166` (`_sell_open_request_ready`), `:1168-1185` (`_send_sell`),
  `:1187-1205` (`_sell_request_target`), `:1298-1300` (`_npc_motion_ready`),
  `:1305-1332` (`_talk_npc`), `:1782-1803` (`_retry_blocked_dialogue_on_tick`).
- `src/robots/adapters/native_npc_dialogue.py` — `:21-28` (receive ids/stages),
  `:103-115` (`begin`), `:130-144` (`_expire`/`_deny`), `:146-174` (`_receive`).
- `src/robots/adapters/native_gameplay.py` — `:80-101` (`sell_open`), `:103`
  (`sell`), `:317` (`arrival_confirmed`), `:488-491` (C7/CB ingest),
  `:716-732` (`_sell_list`/`_sell_result`), `:734-763` (`_self_position`).
- `src/robots/app/scripts.py` — `:201-215` (`SELLABLE_ITEM_IDS`,
  `shop_sellable_stock`), `:238-250` (`shop_sell_entries`).
- `src/robots/app/agent_runtime.py` — `:1179-1190` (`execute_actions`),
  `:1256-1270` (`_trace_action`), `:1282-1286` (`_perform`).
- `src/robots/domain/actions.py` — `:136-171` (`NpcShopSellOpen`, `NpcShopSell`).

**Server (rathena e985006171d2, read-only):**
- `rathena/src/map/clif.cpp:12256-12271` (`clif_parse_NpcBuySellSelected`),
  `:2223-2230` (`clif_npcbuysell`), `:2265-2280` (`clif_selllist`).
- `rathena/src/map/npc.cpp:2387-2418` (`npc_buysellsel`; `type == 0` -> buy,
  else sell), `:1134-1177` (`npc_secure_timeout_timer`).
- `rathena/src/config/secure.hpp:28-40` (`NPC_SECURE_TIMEOUT_INPUT/MENU/NEXT`).

**Evidence:**
- `run/plain_host_receipts/population-receipt-28-1793096707.json` (leg 28 receipt:
  the `npc_stage` walk, zeny 0, 32 opens).
- `.work/runtime/population-live/traces/pop_0003_g01m00.jsonl` (leg 28 trace: the
  32 mints in 4 bursts, the 8-per-burst same-key re-mint, the `opening` re-click
  events, the held Jellopy, the walk).
- `.work/engagement-diagnosis/c7_probe.py` (the wire proof: click -> C4 -> C5 ->
  C7 arrives).
- `.work/engagement-diagnosis/sell_gate_probe.py` (this branch: the offline
  reproduction, CASES A/B/C; run it with
  `nix develop -c uv run python3 .work/engagement-diagnosis/sell_gate_probe.py`
  from the repo root).
- Commits `e06dc511`/`a3d28abe` (the w82 click gate: adjacency, not the arrival
  flag), `c6f16717`/`512400b2` (the framer learns 0xC6/0xC7), `a2e1fe48` (the
  deny-origin marker + the retry cadence), `492c94f7` (leg 28's NoRoute direct
  send).
