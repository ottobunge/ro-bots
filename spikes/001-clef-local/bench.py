#!/usr/bin/env python3
"""Spike 001-clef-local benchmark.

Benchmarks a local llama.cpp server's POST /v1/systemone endpoint
(ggml-org/Clef-Flash-GGUF Q4_K_M) with a realistic Ragnarok Online
bot decision request.

Measures:
  - cold first decision (server restart, fresh process)
  - warm single decision latency: p50 / p95 over N runs
  - batched throughput: 8 different bot states in parallel (8 concurrent
    HTTP requests, mirroring collate_records batching of 8 records)
  - input token counts

Usage:
  python3 bench.py [--url http://127.0.0.1:8091] [--runs 20]
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import string
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------- RO state

MONSTERS = ["Poring", "Lunatic", "Fabre", "Drops", "Poporing", "Orc Warrior",
            "Orc Lady", "High Orc", "Steam Goblin", "Hornet", "Thief Bug", "Wolf"]
PLAYERS = ["KafraFan99", "xXAssassinXx", "PoringLover", "GeffenWizard",
           "MjolnirKid", "TristanIII", "YggdrasilSeed", "BuffBotPrime"]
MAPS = ["prontera", "geffen", "morocc", "payon", "alberta", "izlude",
        "moc_fild04", "prt_fild08", "gef_fild03", "pay_fild04", "aldebaran"]
ITEMS = ["Jellopy", "Sticky Mucus", "Feather", "Clover", "Red Herb",
         "Zargon", "Orc's Fang", "Golden Gem", "Green Live", "Wing of Fly"]
CHAT_LINES = [
    "anyone selling zargons??",
    "lvl 62 hunter LFP grinding orcs",
    "wts +7 chain mail 350k",
    "heal plz",
    "thanks!",
    "where is the kafra here",
    "GG",
    "bot much?",
    "join my party, 3/5 so far",
    "any buffs before orc dungeon run?",
]


def make_bot(bot_id: int, rng: random.Random) -> dict:
    """A realistic RO bot decision request: state + >=15 mixed questions."""
    hp = rng.randint(12, 100)
    sp = rng.randint(0, 100)
    near_monsters = [
        {
            "name": rng.choice(MONSTERS),
            "level": rng.randint(5, 60),
            "distance": rng.randint(1, 14),
            "aggro": rng.choice([True, False]),
            "hp_pct": rng.randint(10, 100),
        }
        for _ in range(rng.randint(1, 5))
    ]
    near_players = [
        {
            "name": rng.choice(PLAYERS),
            "level": rng.randint(20, 99),
            "distance": rng.randint(2, 15),
            "job": rng.choice(["Swordsman", "Mage", "Acolyte", "Merchant", "Thief"]),
            "party": rng.choice([None, "OrcSlayers", "GeffenGrind"]),
        }
        for _ in range(rng.randint(0, 4))
    ]
    state = {
        "bot": {
            "id": bot_id,
            "job": rng.choice(["Hunter", "Knight", "Wizard", "Blacksmith", "Priest"]),
            "level": rng.randint(40, 99),
            "hp": hp,
            "hp_max": 100,
            "sp": sp,
            "sp_max": 100,
            "weight_pct": rng.randint(0, 90),
            "zeny": rng.randint(500, 900000),
        },
        "position": {
            "map": rng.choice(MAPS),
            "x": rng.randint(10, 390),
            "y": rng.randint(10, 390),
            "save_map": "prontera",
        },
        "nearby": {"monsters": near_monsters, "players": near_players},
        "inventory": {
            item: rng.randint(0, 350) for item in rng.sample(ITEMS, 5)
        },
        "party": {
            "in_party": rng.choice([True, False]),
            "party_name": rng.choice([None, "OrcSlayers", "GeffenGrind"]),
            "invites_pending": rng.choice([[], ["OrcSlayers"], ["GeffenGrind", "MjolnirKid"]]),
        },
        "quest": {
            "active": rng.choice([True, False]),
            "target_item": rng.choice(["Zargon", "Orc's Fang", "Golden Gem", None]),
            "collected": rng.randint(0, 40),
            "needed": 50,
        },
        "chat": {
            "last_lines": [
                {"from": rng.choice(PLAYERS), "text": rng.choice(CHAT_LINES)}
                for _ in range(3)
            ],
        },
        "time": {"server_hour": rng.randint(0, 23), "online_minutes": rng.randint(5, 400)},
    }

    questions = {
        "next_action": {
            "type": "choice",
            "instructions": "What should the bot do next?",
            "criteria": {
                "grind": "Attack nearby monsters to level up",
                "farm_item": "Farm the quest target item from nearby monsters",
                "idle_town": "Walk to town and idle near the Kafra",
                "take_quest": "Go to the quest board and take a new quest",
                "join_party": "Accept a pending party invite",
                "reply_chat": "Answer the most recent chat line addressed to the bot",
            },
        },
        "should_reply_to_chat": {
            "type": "noul",
            "instructions": "Does the latest chat line address or ask the bot something?",
        },
        "hp_low": {
            "type": "noul",
            "instructions": "Is the bot's HP low enough to need healing or a retreat?",
        },
        "target_map": {
            "type": "choice",
            "instructions": "Which map should the bot travel to if it relocates?",
            "criteria": {m: None for m in ["prt_fild08", "moc_fild04", "gef_fild03", "pay_fild04", "prontera"]},
        },
        "threat_level": {
            "type": "score",
            "instructions": "How dangerous is the current surroundings for the bot?",
            "criteria": [
                "no threat at all",
                "weak harmless monsters",
                "moderate monsters, manageable",
                "dangerous, could kill the bot",
                "lethal, immediate escape needed",
            ],
        },
        "chat_premade": {
            "type": "choice",
            "instructions": "If the bot speaks, which canned line fits best?",
            "criteria": {
                "searching_party": "Looking for a party",
                "need_buffs": "Asking for buffs or heal",
                "greet": "A friendly greeting",
                "none": "Stay silent",
            },
        },
        "loot_pickup": {
            "type": "noul",
            "instructions": "Is there loot on the ground worth walking over to pick up?",
        },
        "use_potion": {
            "type": "noul",
            "instructions": "Should the bot drink a red potion right now?",
        },
        "weight_action": {
            "type": "choice",
            "instructions": "What to do about inventory weight?",
            "criteria": {
                "keep_grinding": "Underweight, ignore it",
                "sell_junk": "Sell junk items to the NPC trader",
                "storage_run": "Store items at the Kafra storage",
                "overweight_flee": "Overweight, move carefully to town",
            },
        },
        "engagement_range": {
            "type": "score",
            "instructions": "How close should the bot let monsters approach before attacking?",
            "criteria": [
                "attack at maximum range",
                "attack at mid range",
                "let them come close",
                "only melee when adjacent",
            ],
        },
        "party_accept": {
            "type": "choice",
            "instructions": "How should the bot treat the pending party invite?",
            "criteria": {
                "accept": "Join the party",
                "decline": "Politely decline",
                "ignore": "Do nothing for now",
                "none_pending": "There is no invite",
            },
        },
        "mob_is_aggro": {
            "type": "noul",
            "instructions": "Is any nearby monster currently aggressive toward the bot?",
        },
        "monster_priority": {
            "type": "choice",
            "instructions": "Which nearby monster should be attacked first?",
            "criteria": {
                "closest": "The closest monster regardless of level",
                "weakest": "The lowest level monster",
                "quest_target": "The monster that drops the quest item",
                "aggressive": "The monster already attacking the bot",
                "none": "No monster worth attacking",
            },
        },
        "chat_tone": {
            "type": "score",
            "instructions": "How friendly should the bot's next chat message be?",
            "criteria": [
                "silent or curt",
                "neutral",
                "polite",
                "very friendly and chatty",
            ],
        },
        "skill_to_cast": {
            "type": "choice",
            "instructions": "Which skill should the bot use next?",
            "criteria": {
                "attack_skill": "The main damage skill",
                "buff_skill": "A self-buff",
                "heal_skill": "A heal or recovery skill",
                "none": "No skill, auto-attack only",
            },
        },
        "warp_scroll": {
            "type": "noul",
            "instructions": "Would using a Wing of Fly / Butterfly Wing be wise right now?",
        },
        "profit_check": {
            "type": "choice",
            "instructions": "How is the farming session going economically?",
            "criteria": {
                "great": "Loot value is high, keep going",
                "ok": "Average drop rate, keep going",
                "poor": "Bad drops, consider switching map",
                "losing": "Losing money, stop and return to town",
            },
        },
        "pvp_risk": {
            "type": "noul",
            "instructions": "Is there a player nearby that might attack the bot (PVP risk)?",
        },
    }

    return {"model": "clef-flash", "state": state, "questions": questions}


# ---------------------------------------------------------------- helpers

def post(url: str, body: dict, timeout: float = 300.0) -> tuple[dict, float]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read())
    return payload, time.perf_counter() - t0


def pct(values: list[float], p: float) -> float:
    values = sorted(values)
    if len(values) == 1:
        return values[0]
    k = (len(values) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


# ---------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8091")
    ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()
    url = args.url.rstrip("/") + "/v1/systemone"
    rng = random.Random(4242)

    print(f"target: {url}\n")

    # -- sanity + cold timing (first decision of this process)
    req0 = make_bot(0, rng)
    n_questions = len(req0["questions"])
    print(f"questions per request: {n_questions} "
          f"(choice={sum(1 for q in req0['questions'].values() if q['type']=='choice')}, "
          f"noul={sum(1 for q in req0['questions'].values() if q['type']=='noul')}, "
          f"score={sum(1 for q in req0['questions'].values() if q['type']=='score')})")
    try:
        ans0, cold = post(url, req0)
    except urllib.error.URLError as e:
        raise SystemExit(f"server unreachable at {url}: {e}") from e
    print(f"cold decision (first request, warm model): {cold*1000:.0f} ms")
    print(f"usage reported by server: {ans0.get('usage')}")
    na = ans0["answers"]["next_action"]
    print(f"sample answer next_action: {na['choice']}  (p={na['probabilities'][na['choice']]:.3f})")
    print(f"sample answer hp_low: {ans0['answers']['hp_low']}")

    # -- warm single decisions
    lats = []
    tokens = []
    for i in range(args.runs):
        req = make_bot(i + 1, rng)
        _, dt = post(url, req)
        lats.append(dt)
        if i == 0:
            tokens = ans0.get("usage", {}).get("input_tokens")
    lats_ms = [l * 1000 for l in lats]
    print(f"\nwarm single decision over {args.runs} runs:")
    print(f"  p50 = {pct(lats_ms, 50):.0f} ms   p95 = {pct(lats_ms, 95):.0f} ms   "
          f"mean = {statistics.mean(lats_ms):.0f} ms   min = {min(lats_ms):.0f}   max = {max(lats_ms):.0f}")

    # -- batched: 8 different bots, one HTTP request each, fired concurrently
    import threading
    bots = [make_bot(100 + i, random.Random(1000 + i)) for i in range(args.batch)]
    results = [None] * args.batch

    def worker(idx: int, req: dict) -> None:
        try:
            results[idx] = post(url, req)
        except Exception as e:  # noqa: BLE001
            results[idx] = e

    batch_times = []
    for trial in range(5):
        threads = [threading.Thread(target=worker, args=(i, r)) for i, r in enumerate(bots)]
        t0 = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        wall = time.perf_counter() - t0
        errs = [r for r in results if isinstance(r, Exception)]
        if errs:
            print(f"batch trial {trial}: {len(errs)} errors: {errs[0]!r}")
            continue
        batch_times.append(wall)
        per_call = [r[1] * 1000 for r in results if not isinstance(r, Exception)]
        print(f"batch trial {trial}: wall={wall*1000:.0f} ms for {args.batch} bots "
              f"(= {wall*1000/args.batch:.0f} ms/bot), slowest call {max(per_call):.0f} ms")

    if batch_times:
        best = min(batch_times)
        print(f"\nbatched throughput: {args.batch} bots in {best*1000:.0f} ms wall "
              f"-> {args.batch/best:.1f} decisions/s "
              f"(vs single-bot rate {1000/ (pct(lats_ms,50)):.1f}/s at p50)")
    print("\nNOTE: 'cold' above is first-request-of-process with model already loaded. "
          "True cold start (model load) is measured by bench_cold.py / README procedure.")


if __name__ == "__main__":
    main()
