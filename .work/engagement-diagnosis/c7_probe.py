"""The C7 probe: click the dealer, C5 sell-open, dump the raw exchange.

Leg 28's sell churn: 32 NpcShopSellOpen, zero completed sells, npc_stage
'blocked'. This probe reproduces ONE exchange at the frame level against the
LIVE e2e dealer: click 0x0090 -> C4 -> C5 sell_open (production builder,
type 1) -> does ZC_PC_SELL_ITEMLIST 0xC7 arrive?
"""
import json
import struct
import sys
import time

sys.path.insert(0, "/home/otto/dev/ro-bots/spikes/003-clientless-limbs")
sys.path.insert(0, "/home/otto/dev/ro-bots/src")

import packetdb as packets  # noqa: E402
from client import BotClient  # noqa: E402
from robots.adapters import native_gameplay as ng  # noqa: E402

a0 = json.load(open("/tmp/probe_identity.json"))
bot = BotClient(
    user=a0["user"],
    password=a0["password"],
    char_name=a0["char_name"],
    pincode=a0.get("pincode"),
    login_ip="127.0.0.1",
    login_port=26900,
)
bot.connect()
time.sleep(4)
print("aid:", bot.aid, "gid:", bot.gid, "pos:", (bot.x, bot.y), bot.map_name, flush=True)

# find the dealer: npc-kind actor nearest the cited cell (172,130)
near = [
    (gid, info)
    for gid, info in getattr(bot, "actors", {}).items()
    if gid != bot.gid and abs(info.get("x", 0) - 172) <= 3 and abs(info.get("y", 0) - 130) <= 3
]
print("actors near the dealer cell:", [(g, i.get("x"), i.get("y")) for g, i in near][:6], flush=True)
if not near:
    print("PROBE FAIL: no dealer actor received", flush=True)
    raise SystemExit(1)
dealer_gid = min(near, key=lambda kv: abs(kv[1]["x"] - 172) + abs(kv[1]["y"] - 130))[0]
print("clicking dealer gid", dealer_gid, flush=True)

# CZ_CONTACTNPC 0x0090: production's exact frame (native_npc_dialogue.py:115)
bot._send(struct.pack("<HIB", 0x0090, dealer_gid, 1))
time.sleep(2.5)
for ts, pid, raw in list(bot.raw_log)[-12:]:
    if pid in (0x00B4, 0x00C4, 0x00C7):
        print(f"post-click 0x{pid:04x}: {raw[:48].hex()}", flush=True)

print("--- sending C5 sell_open (production builder) ---", flush=True)
bot._send(ng.sell_open(dealer_gid))
time.sleep(8)
counts = getattr(bot, "packet_counts", {})
for pid in (0x00C4, 0x00C6, 0x00C7, 0x00B1, 0x00CB):
    n = counts.get(pid, 0)
    print(f"0x{pid:04x}: {n}", flush=True)
for ts, pid, raw in list(bot.raw_log)[-200:]:
    if pid in (0x00C4, 0x00C7):
        print(f"raw 0x{pid:04x} len={len(raw)}: {raw[:80].hex()}", flush=True)
print("PROBE DONE")
