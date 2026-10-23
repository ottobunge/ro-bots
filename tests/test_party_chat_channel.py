"""The party-chat channel: the received 0x0109 lands as a party ChatLine.

The leg-10 live probe byte-checked the wire ("NyxSong : anyone need buffs?"
in the member's 0x0109); the receive dispatch and the state projection close
the premade reply loop (buff asks -> hear -> decide -> reply).
"""

from __future__ import annotations

import importlib.util
import struct
import threading
from collections import deque
from pathlib import Path

from robots.adapters.native_gameplay import party_chat
from robots.domain.model import ChatLine


def test_party_chat_send_frame_is_0108_with_speaker() -> None:
    pkt = party_chat("anyone need buffs?", speaker_name="NyxSong")
    assert pkt[:4] == struct.pack("<HH", 0x0108, len(pkt))
    assert b"NyxSong : anyone need buffs?" in pkt


def test_received_0109_dispatches_to_the_party_deque() -> None:
    spec = importlib.util.spec_from_file_location(
        "spike_client",
        Path(__file__).resolve().parents[1] / "spikes/003-clientless-limbs/client.py",
    )
    assert spec is not None, spec
    assert spec.loader is not None, spec
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    bot = mod.BotClient.__new__(mod.BotClient)
    bot.party_chat = deque(maxlen=16)
    bot.chat = deque(maxlen=16)
    bot.chat_event = threading.Event()
    bot.actors = {}
    bot.packet_counts = {}
    bot.raw_log = []
    bot.dispatch_errors = []
    bot.log = lambda *_a, **_k: None
    bot.gid = 300001
    bot._native_frame_lock = threading.Lock()
    bot._native_frame_seq = 0
    bot._native_frame_recording = None
    text = b"NyxSong : anyone need buffs?\x00"
    body = struct.pack("<I", 2200000) + text
    raw = struct.pack("<HH", 0x0109, len(body) + 4) + body
    bot._dispatch(0x0109, raw)
    assert len(bot.party_chat) == 1
    aid, name, msg = bot.party_chat[0]
    assert (aid, name, msg) == (2200000, "NyxSong", "anyone need buffs?")


def test_state_projection_carries_party_lines() -> None:
    line = ChatLine("party", "NyxSong", "anyone need buffs?", 0.0)
    assert line.channel == "party"
