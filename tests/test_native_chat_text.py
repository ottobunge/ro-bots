"""Offline public-chat frames through the real playing and wire Say seams."""

import struct

import pytest

from robots.adapters.native_chat_text import PUBLIC_CHAT_TEXT_MAX_BYTES, public_chat_text
from robots.adapters.native_gameplay import party_chat
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import PartyChat, Say
from tests.test_client_protocol import client as wire_client
from tests.test_playing_runtime import Wire

# Existing synthetic selected name: WireNovice (10 UTF-8 bytes).
PEER_TEXT_BUDGET = 255 - len(b"WireNovice : ")


class ChatWire(Wire):
    def log(self, message: str) -> None:
        pass

    def say(self, text: str) -> None:
        # Execute the unchanged serializer; only its network sink is a fake.
        wire_client.BotClient.say(self, text)


def public_message(wire: ChatWire) -> bytes:
    assert len(wire.sent) == 1
    frame = wire.sent[0]
    assert isinstance(frame, bytes)
    assert struct.unpack_from("<HH", frame) == (0x00F3, len(frame))
    prefix = f"{wire.char_name} : ".encode()
    assert frame[4:].startswith(prefix)
    assert frame.endswith(b"\x00")
    return frame[4 + len(prefix) : -1]


def source_shaped_relay(wire: ChatWire) -> bytes:
    """Simulate pinned clif_process_message/GlobalMessage, not native delivery."""
    message = public_message(wire)
    assert len(message) + 1 + 1 <= 255  # Wire NUL plus modern-branch increment.
    frame = wire.sent[0]
    assert isinstance(frame, bytes)
    full = frame[4:].split(b"\x00", 1)[0]
    length = min(len(full) + 1, 256)
    return full[: length - 1]  # safestrncpy retains len-1 visible bytes.


def test_selected_sender_full_message_survives_source_shaped_relay() -> None:
    wire = ChatWire()
    wire.char_name = "SelectedPeer"
    PlayingClient(wire).perform_native(Say("a" * 253))
    assert source_shaped_relay(wire) == wire.sent[0][4:-1]


@pytest.mark.parametrize("sender_name", ["a" * 253, "界" * 85])
def test_sender_exceeding_full_visible_budget_fails_before_send(sender_name: str) -> None:
    wire = ChatWire()
    wire.char_name = sender_name
    with pytest.raises(ValueError, match="sender exceeds public chat budget"):
        PlayingClient(wire).perform_native(Say("hello"))
    assert not wire.sent


def test_generated_size_reply_fits_pinned_current_wire_budget() -> None:
    # Synthetic 282-character/286-byte counterpart, not private model text.
    text = "a" * 280 + "界界"
    assert (len(text), len(text.encode("utf-8"))) == (282, 286)
    wire = ChatWire()
    PlayingClient(wire).perform_native(Say(text))
    message = public_message(wire)
    # clif.cpp10511,10528,10532: wire NUL plus modern-branch extra byte.
    assert len(message) + 1 + 1 <= 256 - 1
    assert message.decode("utf-8") == "a" * PEER_TEXT_BUDGET
    assert source_shaped_relay(wire) == wire.sent[0][4:-1]


def test_clipping_inside_utf8_character_keeps_only_complete_prefix() -> None:
    text = "a" * (PEER_TEXT_BUDGET - 1) + "界"
    wire = ChatWire()
    PlayingClient(wire).perform_native(Say(text))
    assert public_message(wire).decode("utf-8") == "a" * (PEER_TEXT_BUDGET - 1)


@pytest.mark.parametrize("text", ["", "hello", "界🙂 café", "a" * PEER_TEXT_BUDGET, "a\x00b"])
def test_short_text_preserves_exact_existing_wire_bytes(text: str) -> None:
    wire = ChatWire()
    assert public_chat_text(text, wire.char_name) is text
    PlayingClient(wire).perform_native(Say(text))
    assert public_message(wire) == text.encode("utf-8")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a" * 254, "a" * PEER_TEXT_BUDGET),
        ("a" * (PEER_TEXT_BUDGET - 2) + "é", "a" * (PEER_TEXT_BUDGET - 2) + "é"),
        ("a" * (PEER_TEXT_BUDGET - 1) + "é", "a" * (PEER_TEXT_BUDGET - 1)),
        ("a" * (PEER_TEXT_BUDGET - 3) + "界", "a" * (PEER_TEXT_BUDGET - 3) + "界"),
        ("a" * (PEER_TEXT_BUDGET - 2) + "界", "a" * (PEER_TEXT_BUDGET - 2)),
        ("a" * (PEER_TEXT_BUDGET - 1) + "界", "a" * (PEER_TEXT_BUDGET - 1)),
        ("a" * (PEER_TEXT_BUDGET - 4) + "🙂", "a" * (PEER_TEXT_BUDGET - 4) + "🙂"),
        ("a" * (PEER_TEXT_BUDGET - 3) + "🙂", "a" * (PEER_TEXT_BUDGET - 3)),
        ("a" * (PEER_TEXT_BUDGET - 2) + "🙂", "a" * (PEER_TEXT_BUDGET - 2)),
        ("a" * (PEER_TEXT_BUDGET - 1) + "🙂", "a" * (PEER_TEXT_BUDGET - 1)),
        ("界" * 100, "界" * (PEER_TEXT_BUDGET // 3)),
        ("🙂" * 100, "🙂" * (PEER_TEXT_BUDGET // 4)),
    ],
)
def test_utf8_byte_frontier_is_longest_complete_prefix(text: str, expected: str) -> None:
    wire = ChatWire()
    assert public_chat_text(text, wire.char_name) == expected
    PlayingClient(wire).perform_native(Say(text))
    message = public_message(wire)
    assert message.decode("utf-8") == expected
    assert text.startswith(expected)
    assert len(message) <= PUBLIC_CHAT_TEXT_MAX_BYTES
    if len(expected) < len(text):
        assert len(text[: len(expected) + 1].encode("utf-8")) > PEER_TEXT_BUDGET


@pytest.mark.parametrize("text", ["\ud800", "a" * 280 + "\udfff"])
def test_invalid_source_unicode_raises_before_any_send(text: str) -> None:
    with pytest.raises(UnicodeEncodeError):
        public_chat_text(text, "WireNovice")
    wire = ChatWire()
    with pytest.raises(UnicodeEncodeError):
        PlayingClient(wire).perform_native(Say(text))
    assert not wire.sent


@pytest.mark.parametrize("unavailable", ["transport", "vitals", "position", "progression"])
def test_say_retains_native_readiness_before_text_processing(unavailable: str) -> None:
    wire = ChatWire()
    if unavailable == "transport":
        wire.running = False
    elif unavailable == "vitals":
        wire.status_params = {}
    elif unavailable == "position":
        wire.frames = []
    else:
        wire.class_fresh = False
    with pytest.raises(NativeTelemetryUnavailable):
        PlayingClient(wire).perform_native(Say("\ud800"))
    assert not wire.sent


@pytest.mark.parametrize("sender_name", ["", "N", "界🙂", "a" * 252])
def test_selected_name_byte_frontier_keeps_longest_complete_prefix(sender_name: str) -> None:
    wire = ChatWire()
    wire.char_name = sender_name
    text = "界🙂" * 100
    expected = public_chat_text(text, sender_name)
    budget = min(253, 255 - len(f"{sender_name} : ".encode()))
    PlayingClient(wire).perform_native(Say(text))
    assert public_message(wire).decode("utf-8") == expected
    assert source_shaped_relay(wire) == wire.sent[0][4:-1]
    assert text.startswith(expected)
    assert len(expected.encode("utf-8")) <= budget
    assert len(text[: len(expected) + 1].encode("utf-8")) > budget


def test_invalid_sender_unicode_raises_before_any_send() -> None:
    wire = ChatWire()
    wire.char_name = "\ud800"
    with pytest.raises(UnicodeEncodeError):
        PlayingClient(wire).perform_native(Say("hello"))
    assert not wire.sent


def test_operator_say_uses_same_bounded_native_seam() -> None:
    wire = ChatWire()
    PlayingClient(wire).say("a" * 254)
    assert public_message(wire) == b"a" * PEER_TEXT_BUDGET


def test_party_chat_keeps_its_separate_non_nul_budget() -> None:
    wire = ChatWire()
    wire.party_id = 1
    text = "a" * 254
    PlayingClient(wire).perform_native(PartyChat(text))
    assert wire.sent == [party_chat(text, speaker_name=wire.char_name)]
