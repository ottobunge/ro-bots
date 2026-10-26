"""Bounded per-client NPC UI; e985 MAIN20180704/pre-re. No gameplay sends."""

import math
import struct
from dataclasses import replace

from robots.adapters.native_gameplay import NativeGameplayView, ObservedActor
from robots.adapters.native_shop import encode_buy_selection
from robots.adapters.native_textinput import (
    NpcStringPrompt,
    decode_string_prompt,
    encode_selected_name,
)
from robots.domain.actions import NpcClose, NpcNext, NpcSelect, NpcShopBuySelection, NpcSubmitName
from robots.domain.npc import NpcDialogue

MAX_NPC_PAGES = 32
# Qualified e985 secure.hpp: NEXT/MENU idle timeout 60s; local planning stays below it.
READY_UI_PLANNING_SECONDS = 30.0

NPC_RECEIVE_IDS = frozenset((0xB4, 0xB5, 0xB6, 0xB7, 0xC4, 0x142, 0x1D4))
STAGES = {
    0xB5: "next",
    0xB6: "close",
    0xC4: "unsupported_shop",
    0x142: "unsupported_input",
    0x1D4: "string_input",
}


def observed_npc(view: NativeGameplayView, npc_id: int) -> ObservedActor | None:
    if type(npc_id) is not int or not 0 < npc_id <= 0xFFFFFFFF:
        return None
    return next((a for a in view.actors if a.actor_id == npc_id and a.objecttype in (6, 12)), None)


def received_npc_name(raw: bytes) -> tuple[int, str] | None:
    """ZC_ACK_REQNAMEALL_NPC 0ADF, pinned name@10[24]; never classification."""
    if len(raw) != 58 or int.from_bytes(raw[:2], "little") != 0x0ADF:
        return None
    try:
        name = raw[10:34].split(b"\0", 1)[0].decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None
    return (int.from_bytes(raw[2:6], "little"), name) if name else None


def _matching_response(pid: int, raw: bytes, npc_id: int) -> bool:
    if pid == 0x1D4:
        return decode_string_prompt(raw).npc_id == npc_id
    variable = pid in (0xB4, 0xB7)
    minimum = 9 if variable else 6
    if len(raw) < minimum or int.from_bytes(raw[:2], "little") != pid:
        message = "Malformed NPC response"
        raise ValueError(message)
    offset = 4 if variable else 2
    return int.from_bytes(raw[offset : offset + 4], "little") == npc_id


def _dialog_text(raw: bytes) -> str:
    if int.from_bytes(raw[2:4], "little") != len(raw) or raw[-1:] != b"\0" or b"\0" in raw[8:-1]:
        message = "Malformed NPC text"
        raise ValueError(message)
    if len(raw) > 4105:
        message = "NPC text budget exceeded"
        raise ValueError(message)
    return raw[8:-1].decode("utf-8", errors="strict")


class NativeNpcDialogue:
    """One observed NPC and received cursor. Sends consume each UI stage once."""

    def __init__(self) -> None:
        self.view: NpcDialogue | None = None
        self.cursor = 0
        self.deadline = 0.0
        self.requests = 0
        self.presentations = 0
        self.absolute_deadline = 0.0
        self.failed = False
        self.cancel_uncertain = False
        self.deny_origin: str | None = None
        self._last_now = 0.0
        self.instructions_received = False

    @property
    def active(self) -> bool:
        # 'blocked' is deliberately NOT terminal: the fail-closed barrier
        # holds until the runtime schedules a fresh begin (the retry cadence)
        return self.view is not None and self.view.stage not in (
            "close_requested",
            "cancel_abandoned",
        )

    @property
    def actuation_blocked(self) -> bool:
        """UI execution and unknown cancellation both forbid unsafe native actions."""
        return self.active or self.cancel_uncertain

    def invalidate(self) -> None:
        self.view = None

    def begin(self, npc_id: int, epoch: int, map_name: str, sequence: int, now: float) -> bytes:
        self.view = NpcDialogue(npc_id, epoch, map_name, sequence, sequence, "opening")
        self.cursor = sequence
        self.deadline = now + 5.0
        self.requests = 1
        self.presentations = 0
        self.absolute_deadline = now + 120.0
        # a denied predecessor must not deafen the fresh dialogue (leg 23:
        # the blocked state froze the actuation for whole windows)
        self.failed = False
        self.cancel_uncertain = False
        self.deny_origin = None
        return struct.pack("<HIB", 0x0090, npc_id, 1)

    def consume(self, frames: tuple[tuple[int, float, int, bytes], ...], now: float) -> None:
        if type(now) not in (int, float) or not math.isfinite(now) or now < self._last_now:
            self._deny()
            return
        self._last_now = now
        self._expire(now)
        for seq, _, pid, raw in frames:
            if seq <= self.cursor:
                continue
            self.cursor = seq
            if pid in NPC_RECEIVE_IDS and self.active:
                self._receive(seq, pid, raw, now)

    def _expire(self, now: float) -> None:
        if self.active and now >= min(self.deadline, self.absolute_deadline):
            if self.cancel_uncertain and not self.failed and self.view is not None:
                # Local policy terminal only: the server may still be running prompt().
                self.view = replace(self.view, stage="cancel_abandoned", options=())
            else:
                self._deny("timeout")

    def _deny(self, origin: str = "poison") -> None:
        self.failed = True
        # "timeout" (the innocent deadline expiry) is the retryable origin;
        # the poison denies (the malformed/the send failure) hold the barrier.
        self.deny_origin = origin
        if self.view is not None:
            self.view = replace(self.view, stage="blocked", options=())

    def _receive(self, seq: int, pid: int, raw: bytes, now: float) -> None:
        view = self.view
        if view is None or self.failed:
            return
        try:
            if not _matching_response(pid, raw, view.npc_id):
                return
            self.presentations += 1
            if self.presentations > 64:
                self._deny()
            elif pid in (0xB4, 0xB7):
                self._receive_text(seq, pid, raw)
            elif len(raw) == 6:
                self.view = replace(view, sequence=seq, stage=STAGES[pid], options=())
            else:
                self._deny()
        except ValueError, UnicodeDecodeError:
            self._deny()
        self._commit_received_prompt(now)

    def _commit_received_prompt(self, now: float) -> None:
        """Only validated newly received UI may refresh its local response window."""
        if self.failed:
            return
        self.cancel_uncertain = False
        if self.view is not None and self.view.stage in ("next", "menu"):
            self.deadline = min(now + READY_UI_PLANNING_SECONDS, self.absolute_deadline)
        else:
            self.deadline = min(now + 15.0, self.deadline + 15.0)

    def _receive_text(self, seq: int, pid: int, raw: bytes) -> None:
        view = self.view
        if view is None:
            return
        text = _dialog_text(raw)
        if pid == 0xB7:
            labels = text.split(":")
            if len(labels) > 254:
                message = "NPC menu exceeds uint8 selection range"
                raise ValueError(message)
            options = tuple(enumerate(labels, start=1))
            self.view = replace(view, sequence=seq, stage="menu", options=options)
        else:
            pages = (*view.pages, text)
            if len(pages) > MAX_NPC_PAGES or sum(len(p.encode()) for p in pages) > 4096:
                message = "NPC page budget exceeded"
                raise ValueError(message)
            self.view = replace(view, sequence=seq, stage="text", pages=pages, options=())

    def request(
        self,
        action: NpcNext | NpcSelect | NpcClose | NpcSubmitName | NpcShopBuySelection,
        now: float,
        selected_name: str | None = None,
    ) -> bytes | None:
        view = self.view
        if (
            view is None
            or self.failed
            or action.npc_id != view.npc_id
            or type(action.npc_id) is not int
        ):
            return None
        raw = self._encode_request(view, action, selected_name)
        if raw is None:
            return None
        if isinstance(
            action, (NpcSubmitName, NpcShopBuySelection)
        ) and not self._name_request_clock(now):
            return None
        if self.requests >= 32:
            self._deny()
            return None
        self._commit_request(view, action, now)
        return raw

    def _encode_request(
        self,
        view: NpcDialogue,
        action: NpcNext | NpcSelect | NpcClose | NpcSubmitName | NpcShopBuySelection,
        selected_name: str | None,
    ) -> bytes | None:
        """Route only the concrete supported prompt operations; no fallback codec."""
        if isinstance(action, NpcShopBuySelection):
            return self._encode_shop(view, action)
        if isinstance(action, NpcSubmitName):
            return self._encode_name(view, action, selected_name)
        return self._encode_action(view, action)

    def _name_request_clock(self, now: float) -> bool:
        if (
            type(now) not in (int, float)
            or now < self._last_now
            or now >= min(self.deadline, self.absolute_deadline)
            or not math.isfinite(now)
        ):
            self._deny()
            return False
        self._last_now = now
        return True

    def _commit_request(
        self,
        view: NpcDialogue,
        action: NpcNext | NpcSelect | NpcClose | NpcSubmitName | NpcShopBuySelection,
        now: float,
    ) -> None:
        self.requests += 1
        self.cancel_uncertain = isinstance(action, NpcSelect) and action.received_index == 255
        stage = "close_requested" if isinstance(action, NpcClose) else "waiting"
        self.view = replace(view, stage=stage, options=())
        if isinstance(action, NpcClose) and view.pages:
            self.instructions_received = True
        self.deadline = now + 5.0

    @staticmethod
    def _encode_action(view: NpcDialogue, action: NpcNext | NpcSelect | NpcClose) -> bytes | None:
        if isinstance(action, NpcNext) and view.stage == "next":
            return struct.pack("<HI", 0xB9, view.npc_id)
        if isinstance(action, NpcClose) and view.stage in (
            "close",
            "unsupported_input",
            "string_input",
        ):
            return struct.pack("<HI", 0x146, view.npc_id)
        if isinstance(action, NpcSelect) and view.stage == "menu":
            choice = action.received_index
            if type(choice) is int and (choice == 255 or choice in dict(view.options)):
                return struct.pack("<HIB", 0xB8, view.npc_id, choice)
        return None

    @staticmethod
    def _encode_shop(view: NpcDialogue, action: NpcShopBuySelection) -> bytes | None:
        if not all(
            (
                view.stage == "unsupported_shop",
                type(action.epoch) is int and action.epoch == view.epoch,
                type(action.prompt_sequence) is int and action.prompt_sequence == view.sequence,
                type(action.opened_sequence) is int
                and action.opened_sequence == view.opened_sequence,
                type(action.map_name) is str and action.map_name == view.map_name,
            )
        ):
            return None
        return encode_buy_selection(view.npc_id)

    @staticmethod
    def _encode_name(
        view: NpcDialogue, action: NpcSubmitName, selected_name: str | None
    ) -> bytes | None:
        if (
            view.stage != "string_input"
            or type(action.epoch) is not int
            or action.epoch != view.epoch
            or type(action.prompt_sequence) is not int
            or action.prompt_sequence != view.sequence
            or selected_name is None
        ):
            return None
        try:
            return encode_selected_name(NpcStringPrompt(view.npc_id), selected_name)
        except TypeError, ValueError:
            return None
