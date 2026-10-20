"""L3-TEMP: supported handshake lifecycle, fake transports only; no live sockets."""

import importlib.util
import secrets
import struct
import sys
from collections import deque
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPIKE = ROOT / "spikes/003-clientless-limbs"
sys.path.insert(0, str(SPIKE))


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


client = load_module("temporary_cleanup_client", SPIKE / "client.py")


class Transport:
    def __init__(
        self, chunks: tuple[bytes, ...] | list[bytes] = (), error=None, close_error=None
    ) -> None:
        self.chunks = deque(chunks)
        self.error = error
        self.close_error = close_error
        self.closed = False
        self.closes = 0
        self.sent: list[bytes] = []

    def settimeout(self, value) -> None:
        pass

    def recv(self, count) -> bytes:
        if self.error is not None:
            raise self.error
        chunk = self.chunks.popleft()
        if len(chunk) > count:
            self.chunks.appendleft(chunk[count:])
        return chunk[:count]

    def sendall(self, raw) -> None:
        self.sent.append(raw)

    def shutdown(self, how) -> None:
        pass

    def close(self) -> None:
        self.closes += 1
        if self.close_error is not None:
            raise self.close_error
        self.closed = True

    def __enter__(self) -> Any:
        return self

    def __exit__(self, *_args) -> None:
        self.close()


def bot_for_stage(monkeypatch, stage, transport) -> Any:
    bot = client.BotClient("offline", secrets.token_hex(8), char_name="Selected", verbose=False)
    bot.aid = 11
    monkeypatch.setattr(client.socket, "create_connection", lambda *_a, **_k: transport)
    if stage == "char":
        monkeypatch.setattr(bot, "_login_server", lambda: ("127.0.0.1", 1))
    return bot


@pytest.mark.parametrize("stage", ["login", "char"])
def test_handshake_origin_survives_unreleased_temporary_cleanup(monkeypatch, stage):
    origin = ValueError("sentinel-origin-not-for-output")
    cleanup = OSError("sentinel-cleanup-not-for-output")
    chunks = [struct.pack("<I", 11)] if stage == "char" else []
    transport = Transport(chunks, close_error=cleanup)
    # Character entry consumes its account echo before the failing frame read.
    original_recv = transport.recv

    def recv(count) -> bytes:
        if transport.chunks:
            return original_recv(count)
        raise origin

    monkeypatch.setattr(transport, "recv", recv)
    bot = bot_for_stage(monkeypatch, stage, transport)
    with pytest.raises(ValueError, match="sentinel-origin") as caught:
        bot.connect()
    assert caught.value is origin
    traceback_names = []
    traceback = caught.value.__traceback__
    while traceback is not None:
        traceback_names.append(traceback.tb_frame.f_code.co_name)
        traceback = traceback.tb_next
    assert "recv" in traceback_names
    assert bot.cleanup_errors
    assert not transport.closed
    assert all("sentinel" not in note for note in origin.__notes__)
    monkeypatch.setattr(bot, "_login_server", lambda: pytest.fail("unsafe client reuse"))
    with pytest.raises(RuntimeError, match="cleanup"):
        bot.connect()


class Reader:
    def __init__(self, error=None) -> None:
        self.live = True
        self.error = error
        self.joins = 0

    def is_alive(self) -> bool:
        return self.live

    def join(self, *, timeout) -> None:
        self.joins += 1
        if self.error is not None:
            raise self.error
        self.live = False


def test_temporary_map_reader_cleanup_attempts_are_independent(monkeypatch):
    bot = client.BotClient("offline", secrets.token_hex(8), verbose=False)
    temporary = Transport(close_error=KeyboardInterrupt("sentinel-temporary"))
    bot._temporary_sockets.append(temporary)
    map_transport = Transport(close_error=KeyboardInterrupt("sentinel-map"))
    reader = Reader(error=SystemExit("sentinel-reader"))
    bot.sock, bot.rx_thread = map_transport, reader
    with pytest.raises(RuntimeError, match="cleanup"):
        bot.close()
    assert temporary.closes == map_transport.closes == reader.joins == 1
    assert bot._temporary_sockets == [temporary]
    assert vars(bot)["sock"] is map_transport
    assert vars(bot)["rx_thread"] is reader
    assert {type(error) for error in bot.cleanup_errors} >= {KeyboardInterrupt, SystemExit}
    temporary.close_error = map_transport.close_error = reader.error = None
    bot.close()
    assert not bot._temporary_sockets
    assert bot.sock is None
    assert bot.rx_thread is None
    counts = temporary.closes, map_transport.closes, reader.joins
    bot.close()
    assert counts == (temporary.closes, map_transport.closes, reader.joins)


@pytest.mark.parametrize("interruption", [False, True])
def test_harness_retains_unknown_temporary_release_and_cleans_every_participant(interruption):
    limbs = load_module("temporary_cleanup_limbs", SPIKE / "test_limbs.py")
    budget = limbs.Budget(59)
    bot = limbs.FixtureClient("offline", secrets.token_hex(8), verbose=False)
    bot._temporary_sockets.append(Transport(close_error=OSError()))
    other = limbs.FixtureClient("other", secrets.token_hex(8), verbose=False)
    closed = []
    attempts = []

    def unknown_close():
        if interruption:
            message = "sentinel-cleanup-not-for-output"
            raise KeyboardInterrupt(message)
        # A normal return is not release confirmation while ownership remains.

    def other_close():
        closed.append(1)

    bot.close = unknown_close
    other.close = other_close

    def limb(participants, _budget):
        attempts.append(1)
        participants.extend((bot, other))
        message = "sentinel-origin-not-for-output"
        raise ValueError(message)

    limbs.run_limb("first", limb, budget)
    assert closed == [1]
    assert budget.unreleased_clients == [bot]
    assert not limbs.results[-1][1]
    assert "sentinel" not in limbs.results[-1][3]
    limbs.run_limb("later", limb, budget)
    assert attempts == [1]
    with pytest.raises(RuntimeError, match="cleanup"):
        limbs.connect_pair([], budget)


def accepted_frames(stage) -> bytes:
    if stage == "login":
        raw = bytearray(80)
        struct.pack_into("<HH", raw, 0, 0x0AC4, len(raw))
        struct.pack_into("<I", raw, 8, 11)
        raw[64:68] = bytes([127, 0, 0, 1])
        struct.pack_into("<H", raw, 68, 6121)
        return bytes(raw)
    raw = bytearray(27 + 155)
    struct.pack_into("<HHI", raw, 0, 0x006B, len(raw), 0)
    struct.pack_into("<I", raw, 27, 21)
    raw[115:139] = b"Selected".ljust(24, b"\0")
    raw[145] = 5
    zone = bytearray(28)
    struct.pack_into("<HI", zone, 0, 0x0071, 21)
    zone[22:26] = bytes([127, 0, 0, 1])
    struct.pack_into("<H", zone, 26, 5121)
    pin_status = struct.pack("<HIIH", 0x08B9, 123, 11, 0)
    return struct.pack("<I", 11) + bytes(raw) + pin_status + bytes(zone)


@pytest.mark.parametrize("stage", ["login", "char"])
@pytest.mark.parametrize("cleanup_type", [OSError, KeyboardInterrupt, SystemExit])
def test_completed_handshake_preserves_cleanup_origin_until_confirmed_release(
    monkeypatch, stage, cleanup_type
):
    cleanup = cleanup_type("sentinel-cleanup-not-for-output")
    transport = Transport([accepted_frames(stage)], close_error=cleanup)
    bot = bot_for_stage(monkeypatch, stage, transport)
    with pytest.raises(cleanup_type) as caught:
        bot.connect()
    assert caught.value is cleanup
    assert bot._temporary_sockets == [transport]
    assert transport in bot._handshake_buffers
    assert transport in bot._handshake_packets
    assert cleanup in bot.cleanup_errors
    assert all("sentinel" not in note for note in cleanup.__notes__)
    traceback = caught.value.__traceback__
    names = []
    while traceback is not None:
        names.append(traceback.tb_frame.f_code.co_name)
        traceback = traceback.tb_next
    assert "close" in names
    transport.close_error = None
    bot.close()
    assert transport.closed
    assert not bot._temporary_sockets
    assert not bot._handshake_buffers
    assert not bot._handshake_packets
    count = transport.closes
    bot.close()
    assert transport.closes == count


@pytest.mark.parametrize("stage", ["login", "char"])
def test_normal_handshake_closes_once_and_forgets_framing(monkeypatch, stage):
    transport = Transport([accepted_frames(stage)])
    bot = bot_for_stage(monkeypatch, stage, transport)
    result = bot._login_server() if stage == "login" else bot._char_server("127.0.0.1", 1)
    assert result == ("127.0.0.1", 6121 if stage == "login" else 5121)
    assert transport.closed
    assert transport.closes == 1
    assert not bot._temporary_sockets
    assert not bot._handshake_buffers
    assert not bot._handshake_packets
    assert not bot.cleanup_errors
    bot.close()
    assert transport.closes == 1


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds) -> None:
        self.now += seconds


@pytest.mark.parametrize("stage", ["login", "char"])
@pytest.mark.parametrize("completion", [False, True])
@pytest.mark.parametrize("cleanup_type", [OSError, KeyboardInterrupt])
def test_actual_fixture_handshake_failure_blocks_retry_later_limbs_and_pass(
    monkeypatch, stage, completion, cleanup_type
):
    limbs = load_module("temporary_actual_limbs", SPIKE / "test_limbs.py")
    clock = Clock()
    budget = limbs.Budget(59, clock=clock.monotonic, sleep=clock.sleep)
    monkeypatch.setattr(limbs.time, "monotonic", clock.monotonic)
    accounts = [
        {
            "username": f"offline-{i}",
            "password": secrets.token_hex(8),
            "character": "Selected" if i == 1 else "Other",
            "account_id": 10 + i,
            "char_id": 20 + i,
        }
        for i in (1, 2)
    ]
    monkeypatch.setattr(
        limbs,
        "fixture",
        {
            "schema": 1,
            "isolated_disposable": True,
            "login_host": "127.0.0.1",
            "login_port": 6900,
            "accounts": accounts,
        },
    )
    raw = (
        accepted_frames(stage)
        if completion
        else (
            client.pdb.pack(0x006A, bytes(21))
            if stage == "login"
            else struct.pack("<I", 11) + client.pdb.pack(0x006C, b"\x01")
        )
    )
    transport = Transport([raw], close_error=cleanup_type("sentinel-cleanup"))
    monkeypatch.setattr(client.socket, "create_connection", lambda *_a, **_k: transport)
    actual_login = limbs.FixtureClient._login_server
    attempts = []

    def login(bot):
        attempts.append(clock.now)
        bot.aid, bot.gid = 11, 21
        if stage == "login":
            return actual_login(bot)
        return "127.0.0.1", 1

    monkeypatch.setattr(limbs.FixtureClient, "_login_server", login)

    def limb(participants, shared_budget):
        limbs.connect_pair(participants, shared_budget)
        return "OK synthetic evidence"

    # Cleanup-origin BaseExceptions propagate, but still poison the shared budget.
    if completion and cleanup_type is KeyboardInterrupt:
        with pytest.raises(KeyboardInterrupt):
            limbs.run_limb("first", limb, budget)
    else:
        limbs.run_limb("first", limb, budget)
        assert not limbs.results[-1][1]
        assert "sentinel" not in limbs.results[-1][3]
    assert attempts == [100.0]
    assert len(budget.unreleased_clients) == 1
    assert budget.unreleased_clients[0]._temporary_sockets == [transport]
    assert not transport.closed
    assert budget.connect_not_before >= 130.0
    clock.sleep(30)
    limbs.run_limb("later", limb, budget)
    assert attempts == [100.0]
    assert not limbs.results[-1][1]
