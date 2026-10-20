"""Pinned MAIN 20180704 PIN handshake, injected transports only."""

import importlib.util
import struct
from collections import deque
from pathlib import Path
from typing import Any

import pytest

SPIKE = Path(__file__).resolve().parents[1] / "spikes/003-clientless-limbs"


def load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, SPIKE / filename)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


client = load("pin_client", "client.py")


def test_pin_reply_has_pinned_packet_metadata() -> None:
    assert client.pdb.PACKET_DB.get(0x08B8) == 10, "PIN reply packet metadata missing"
    assert client.pdb.NAMES.get(0x08B8) == "CH_SECOND_PASSWD_ACK"


def status(state: int, aid: int = 11, seed: int = 65534) -> bytes:
    return struct.pack("<HIIH", 0x08B9, seed, aid, state)


def characters() -> bytes:
    raw = bytearray(182)
    struct.pack_into("<HH", raw, 0, 0x006B, len(raw))
    struct.pack_into("<I", raw, 27, 21)
    raw[115:139] = b"Selected".ljust(24, b"\0")
    raw[145] = 5
    return bytes(raw)


def zone() -> bytes:
    raw = bytearray(28)
    struct.pack_into("<HI", raw, 0, 0x0071, 21)
    raw[22:26] = bytes([127, 0, 0, 1])
    struct.pack_into("<H", raw, 26, 5121)
    return bytes(raw)


class Wire:
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = deque(chunks)
        self.sent: list[bytes] = []
        self.closed = False
        self.accepted = False

    def settimeout(self, value: float) -> None:
        pass

    def recv(self, count: int) -> bytes:
        if not self.chunks:
            return b""
        raw = self.chunks.popleft()
        if len(raw) > count:
            self.chunks.appendleft(raw[count:])
        data = raw[:count]
        if status(0) in data:
            self.accepted = True
        return data

    def sendall(self, raw: bytes) -> None:
        if struct.unpack_from("<H", raw)[0] == 0x0066:
            assert self.accepted, "character selected before PIN success"
        self.sent.append(raw)

    def __exit__(self, *_args: object) -> None:
        self.closed = True


def replay(monkeypatch: pytest.MonkeyPatch, wire: Wire, **kwargs: Any) -> Any:
    monkeypatch.setattr(client.socket, "create_connection", lambda *_a, **_kw: wire)
    bot = client.BotClient(
        "offline", "synthetic-password", char_name="Selected", verbose=False, **kwargs
    )
    bot.aid = 11
    return bot


def test_pin_required_before_character_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = Wire([struct.pack("<I", 11), characters() + status(1), status(0) + zone()])
    bot = replay(monkeypatch, wire)
    with pytest.raises(RuntimeError, match="PIN"):
        bot._char_server("127.0.0.1", 6121)
    assert [struct.unpack_from("<H", raw)[0] for raw in wire.sent] == [0x0065]
    assert wire.closed
    assert not bot._temporary_sockets


@pytest.mark.parametrize("order", ["list-first", "pin-first", "fragmented"])
@pytest.mark.parametrize("seed", [0, 65534, 0xFFFFFFFF])
def test_supplied_pin_waits_for_success_and_inverts_native_decrypt(
    monkeypatch: pytest.MonkeyPatch, order: str, seed: int
) -> None:
    first = characters() + status(1, seed=seed)
    if order == "pin-first":
        first = status(1, seed=seed) + characters()
    chunks = [struct.pack("<I", 11), first, status(0) + zone()]
    if order == "fragmented":
        chunks = [struct.pack("<I", 11), first[:183], first[183:], status(0), zone()]
    wire = Wire(chunks)
    bot = replay(monkeypatch, wire, pincode="0379")
    assert bot._char_server("127.0.0.1", 6121) == ("127.0.0.1", 5121)
    assert [struct.unpack_from("<H", raw)[0] for raw in wire.sent] == [0x0065, 0x08B8, 0x0066]
    ack = wire.sent[1]
    assert len(ack) == 10
    assert struct.unpack_from("<I", ack, 2)[0] == bot.aid
    # Independent transcription of server decrypt, char.cpp:2153-2187.
    table = list(range(10))
    for i in range(1, 10):
        seed = (0x881234 + seed * 0x3498) % (2**32)
        pos = seed % (i + 1)
        table[i], table[pos] = table[pos], table[i]
    assert "".join(str(table[byte - 48]) for byte in ack[6:]) == "0379"
    assert wire.sent[2] == struct.pack("<HB", 0x0066, 5)
    assert wire.closed
    assert not bot._temporary_sockets


@pytest.mark.parametrize(
    "value", [1234, "123", "12345", "12a4", "\uff11\uff12\uff13\uff14", "1\n34", "", True]
)
def test_invalid_pin_rejected_without_transport(
    monkeypatch: pytest.MonkeyPatch, value: Any
) -> None:
    wire = Wire([])
    with pytest.raises(ValueError, match="pincode"):
        replay(monkeypatch, wire, pincode=value)
    assert not wire.sent


def test_account_echo_mismatch_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = Wire([struct.pack("<I", 12), characters() + status(0) + zone()])
    bot = replay(monkeypatch, wire)
    with pytest.raises(RuntimeError, match="account"):
        bot._char_server("127.0.0.1", 6121)
    assert len(wire.sent) == 1
    assert wire.closed


@pytest.mark.parametrize("state", [2, 3, 4, 5, 6, 7, 8, 65535])
def test_non_authentication_states_never_select(
    monkeypatch: pytest.MonkeyPatch, state: int
) -> None:
    wire = Wire([struct.pack("<I", 11), characters() + status(state)])
    bot = replay(monkeypatch, wire, pincode="0379")
    with pytest.raises(RuntimeError, match="PIN"):
        bot._char_server("127.0.0.1", 6121)
    assert len(wire.sent) == 1
    assert wire.closed


@pytest.mark.parametrize("state", [0, 1])
def test_pin_status_account_mismatch_never_uses_seed(
    monkeypatch: pytest.MonkeyPatch, state: int
) -> None:
    wire = Wire([struct.pack("<I", 11), characters() + status(state, aid=12)])
    bot = replay(monkeypatch, wire, pincode="0379")
    with pytest.raises(RuntimeError, match="PIN account"):
        bot._char_server("127.0.0.1", 6121)
    assert len(wire.sent) == 1
    assert wire.closed


@pytest.mark.parametrize("next_frame", [status(1), status(8), b""])
def test_one_attempt_no_resend_or_selection(
    monkeypatch: pytest.MonkeyPatch, next_frame: bytes
) -> None:
    wire = Wire([struct.pack("<I", 11), characters() + status(1), next_frame])
    bot = replay(monkeypatch, wire, pincode="0379")
    with pytest.raises((RuntimeError, ConnectionError)):
        bot._char_server("127.0.0.1", 6121)
    assert [struct.unpack_from("<H", raw)[0] for raw in wire.sent] == [0x0065, 0x08B8]
    assert wire.closed
    assert not bot._temporary_sockets


def test_disabled_pin_preserves_legacy_constructor(monkeypatch: pytest.MonkeyPatch) -> None:
    wire = Wire([struct.pack("<I", 11), characters() + status(0), zone()])
    bot = replay(monkeypatch, wire)
    assert bot._char_server("127.0.0.1", 6121) == ("127.0.0.1", 5121)
    assert [struct.unpack_from("<H", raw)[0] for raw in wire.sent] == [0x0065, 0x0066]


limbs = load("pin_limbs", "test_limbs.py")


def fixture() -> dict[str, Any]:
    return {
        "schema": 1,
        "isolated_disposable": True,
        "login_host": "127.0.0.1",
        "login_port": 6900,
        "accounts": [
            {
                "username": "one",
                "password": "synthetic",
                "character": "One",
                "account_id": 11,
                "char_id": 21,
            },
            {
                "username": "two",
                "password": "synthetic",
                "character": "Two",
                "account_id": 12,
                "char_id": 22,
            },
        ],
    }


@pytest.mark.parametrize("value", [1234, None, "123", "12345", "\uff11\uff12\uff13\uff14", "12x4"])
def test_fixture_rejects_invalid_pin_without_echo(value: Any) -> None:
    data = fixture()
    data["accounts"][0]["pincode"] = value
    with pytest.raises(ValueError, match="pincode") as caught:
        limbs.validate_fixture(data)
    assert str(value) not in str(caught.value)


def test_fixture_forwards_optional_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    data = fixture()
    data["accounts"][0]["pincode"] = "0379"
    monkeypatch.setattr(limbs, "fixture", data)
    clients: list[Any] = []
    seen: list[Any] = []

    def connect(bot: Any, *, deadline: float) -> Any:
        seen.append(bot._pincode)
        account = data["accounts"][len(seen) - 1]
        bot.aid, bot.gid = account["account_id"], account["char_id"]
        return bot

    monkeypatch.setattr(limbs.FixtureClient, "connect", connect)
    budget = limbs.Budget(59, sleep=lambda _seconds: None)
    limbs.connect_pair(clients, budget)
    assert seen == ["0379", None]
