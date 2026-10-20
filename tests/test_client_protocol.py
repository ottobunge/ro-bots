"""Offline protocol regressions: deterministic sockets, never native acceptance."""

import ast
import importlib.util
import json
import secrets
import socket
import struct
import threading
from collections import deque
from collections.abc import Callable, Iterable
from pathlib import Path
from types import TracebackType
from typing import Any, Self

import pytest

CLIENT_PATH = Path(__file__).resolve().parents[1] / "spikes/003-clientless-limbs/client.py"
spec = importlib.util.spec_from_file_location("spike_client_protocol", CLIENT_PATH)
assert spec is not None
assert spec.loader is not None
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class FakeSocket:
    def __init__(self, chunks: Iterable[bytes | BaseException] = ()) -> None:
        self.chunks: deque[bytes | BaseException] = deque(chunks)
        self.sent: list[bytes] = []
        self.timeouts: list[float] = []
        self.closed = False
        self.shutdown_called = False
        self.recv_calls = 0

    def settimeout(self, value: float) -> None:
        self.timeouts.append(value)

    def recv(self, count: int) -> bytes:
        self.recv_calls += 1
        if not self.chunks:
            msg = "unexpected read: queued frames were lost"
            raise AssertionError(msg)
        chunk = self.chunks.popleft()
        if isinstance(chunk, BaseException):
            raise chunk
        if len(chunk) > count:
            self.chunks.appendleft(chunk[count:])
            return chunk[:count]
        return chunk

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)

    def shutdown(self, how: int) -> None:
        self.shutdown_called = True

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


@pytest.fixture
def bot() -> Any:
    return client.BotClient("offline_operator", secrets.token_hex(12), verbose=False)


def test_exact_read_resumes_after_timeout_without_losing_bytes(bot):
    sock = FakeSocket([b"ab", TimeoutError(), b"cd"])
    with pytest.raises(socket.timeout):
        bot._recv_exact(sock, 4)
    assert bot._recv_exact(sock, 4) == b"abcd"


@pytest.mark.parametrize("split", [1, 2, 3, 4, 5, 7, 10])
def test_frame_resumes_at_every_header_or_payload_timeout(bot, split):
    raw = client.pdb.pack(0x008D, struct.pack("<I", 42) + b"hello\x00")
    sock = FakeSocket([raw[:split], TimeoutError(), raw[split:]])
    with pytest.raises(socket.timeout):
        bot._read_one(sock)
    assert bot._read_one(sock) == (0x008D, raw)


def test_coalesced_frames_are_returned_in_order_without_more_reads(bot):
    frames = [client.pdb.pack(0x007D), client.pdb.pack(0x0081, b"\x03")]
    sock = FakeSocket([b"".join(frames)])
    assert [bot._read_one(sock), bot._read_one(sock)] == [(0x007D, frames[0]), (0x0081, frames[1])]
    assert sock.recv_calls == 1


def test_handshake_buffers_are_isolated_by_socket(bot):
    first = client.pdb.pack(0x008D, struct.pack("<I", 42) + b"one\x00")
    second = client.pdb.pack(0x007D)
    sock1 = FakeSocket([first[:3], TimeoutError(), first[3:]])
    sock2 = FakeSocket([second])
    with pytest.raises(socket.timeout):
        bot._read_one(sock1)
    assert bot._read_one(sock2) == (0x007D, second)
    assert bot._read_one(sock1) == (0x008D, first)


def test_partial_frame_eof_is_an_explicit_failure(bot):
    sock = FakeSocket([b"\x8d", b""])
    with pytest.raises(ConnectionError, match="EOF"):
        bot._read_one(sock)


@pytest.mark.parametrize(("pid", "size"), [(0x09FD, 110), (0x09FE, 103), (0x09FF, 104)])
def test_actor_entry_and_vanish_use_wire_id_not_character_id(bot, pid, size):
    raw = bytearray(size)
    struct.pack_into("<HHBII", raw, 0, pid, size, 0, 42, 9001)
    bot._dispatch(pid, bytes(raw))
    assert set(bot.actors) == {42}
    assert bot.actors[42]["gid"] == 42
    assert bot.actors[42]["char_id"] == 9001
    bot._dispatch(0x0080, client.pdb.pack(0x0080, struct.pack("<IB", 42, 0)))
    assert not bot.actors


def test_receive_loop_dispatches_chat_once_even_after_repeated_drains(bot):
    raw = client.pdb.pack(0x008D, struct.pack("<I", 42) + b"once\x00")
    bot.sock = FakeSocket([raw, b""])
    bot.running = True
    bot._recv_loop()
    assert bot.chat == [(42, "once")]
    bot.drain()
    bot.drain()
    assert bot.chat == [(42, "once")]
    assert bot.packet_counts[0x008D] == 1


@pytest.mark.parametrize("stage", ["login_refused", "login_eof", "char_echo_eof", "char_refused"])
def test_failed_handshake_closes_temporary_socket(bot, monkeypatch, stage):
    bot.aid = 42
    inputs = {
        "login_refused": [client.pdb.pack(0x006A, bytes(21))],
        "login_eof": [b""],
        "char_echo_eof": [b"\x2a", b""],
        "char_refused": [struct.pack("<I", 42), client.pdb.pack(0x006C, b"\x01")],
    }
    sock = FakeSocket(inputs[stage])
    monkeypatch.setattr(client.socket, "create_connection", lambda *_args, **_kwargs: sock)
    if stage.startswith("login"):
        with pytest.raises((RuntimeError, ConnectionError)):
            bot._login_server()
    else:
        with pytest.raises((RuntimeError, ConnectionError)):
            bot._char_server("offline", 1)
    assert sock.closed
    assert sock not in bot._handshake_buffers
    assert sock not in bot._handshake_packets


def test_failed_connect_closes_map_socket(bot, monkeypatch):
    sock = FakeSocket()
    monkeypatch.setattr(bot, "_login_server", lambda: ("offline", 1))
    monkeypatch.setattr(bot, "_char_server", lambda *_args: ("offline", 1))

    def fail_map(ip: str, port: int) -> None:
        bot.sock = sock
        bot.running = True
        msg = "map handshake rejected"
        raise RuntimeError(msg)

    monkeypatch.setattr(bot, "_map_server", fail_map)
    with pytest.raises(RuntimeError, match="map handshake rejected"):
        bot.connect()
    assert sock.closed
    assert bot.sock is None
    assert not bot.running
    assert not bot.connected_map


class BlockingSocket(FakeSocket):
    def __init__(self) -> None:
        super().__init__()
        self.read_started = threading.Event()
        self.release = threading.Event()

    def recv(self, count: int) -> bytes:
        self.read_started.set()
        if not self.release.wait(2):
            msg = "reader was not interrupted"
            raise AssertionError(msg)
        msg = "socket shut down"
        raise OSError(msg)

    def shutdown(self, how: int) -> None:
        super().shutdown(how)
        self.release.set()


def test_close_interrupts_and_joins_reader_before_clearing_socket(bot):
    sock = BlockingSocket()
    bot.sock = sock
    bot.running = True
    thread = threading.Thread(target=bot._recv_loop)
    bot.rx_thread = thread
    thread.start()
    assert sock.read_started.wait(1)
    try:
        bot.close()
        assert sock.shutdown_called
        assert not thread.is_alive()
        assert bot.rx_thread is None
        assert bot.sock is None
        bot.close()  # idempotent
    finally:
        sock.release.set()
        thread.join(2)


def test_retry_stops_old_reader_before_starting_next_handshake(bot, monkeypatch):
    sock = BlockingSocket()
    bot.sock = sock
    bot.running = True
    old_thread = threading.Thread(target=bot._recv_loop)
    bot.rx_thread = old_thread
    old_thread.start()
    assert sock.read_started.wait(1)

    def login() -> tuple[str, int]:
        assert not old_thread.is_alive()
        assert sock.closed
        return "offline", 1

    monkeypatch.setattr(bot, "_login_server", login)
    monkeypatch.setattr(bot, "_char_server", lambda *_args: ("offline", 1))
    monkeypatch.setattr(bot, "_map_server", lambda *_args: None)
    try:
        assert bot.connect() is bot
    finally:
        sock.release.set()
        old_thread.join(2)


def test_reader_that_will_not_stop_blocks_retry_and_is_not_forgotten(bot, monkeypatch):
    class StuckReader:
        def is_alive(self) -> bool:
            return True

        def join(self, timeout: float) -> None:
            pass

    reader = StuckReader()
    bot.rx_thread = reader
    bot.sock = FakeSocket()
    monkeypatch.setattr(bot, "_login_server", lambda: pytest.fail("unsafe reader reuse"))
    with pytest.raises(RuntimeError, match=r"reader.*stop"):
        bot.connect()
    assert bot.rx_thread is reader


@pytest.mark.parametrize(
    ("chunks", "error_type"),
    [
        ([b""], ConnectionError),
        ([b"\xff\xff"], ValueError),
        ([OSError("offline receive failure")], OSError),
    ],
)
def test_receive_failure_is_retained_for_harness_health(bot, chunks, error_type):
    bot.sock = FakeSocket(chunks)
    bot.running = True
    bot.connected_map = True
    bot._recv_loop()
    assert isinstance(bot.rx_error, error_type)
    assert not bot.running
    assert not bot.connected_map


def test_dispatch_failure_is_retained_while_reader_continues(bot, monkeypatch):
    raw = client.pdb.pack(0x007D)
    bot.sock = FakeSocket([raw, raw, b""])
    bot.running = True
    attempts: list[int] = []

    def fail_dispatch(pid: int, frame: bytes) -> None:
        attempts.append(pid)
        msg = "offline dispatch failure"
        raise ValueError(msg)

    monkeypatch.setattr(bot, "_dispatch", fail_dispatch)
    bot._recv_loop()
    assert attempts == [0x007D, 0x007D]
    assert bot.dispatch_errors == [
        (0x007D, "offline dispatch failure"),
        (0x007D, "offline dispatch failure"),
    ]


def test_intentional_close_does_not_poison_receive_health(bot):
    sock = BlockingSocket()
    bot.sock = sock
    bot.running = True
    thread = threading.Thread(target=bot._recv_loop)
    bot.rx_thread = thread
    thread.start()
    assert sock.read_started.wait(1)
    try:
        bot.close()
        assert bot.rx_error is None
    finally:
        sock.release.set()
        thread.join(2)


class FakeClock:
    def __init__(self, now: float = 100.0) -> None:
        self.now = now

    def monotonic(self) -> float:
        return self.now


@pytest.mark.parametrize("budget", [0.0, -1.0])
def test_expired_connect_deadline_opens_no_socket(bot, monkeypatch, budget):
    clock = FakeClock()
    monkeypatch.setattr(client.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(
        client.socket,
        "create_connection",
        lambda *_args, **_kwargs: pytest.fail("expired budget opened socket"),
    )
    with pytest.raises(TimeoutError, match="deadline"):
        bot.connect(deadline=clock.now + budget)


def test_login_loop_is_bounded_by_shared_monotonic_deadline(bot, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(client.time, "monotonic", clock.monotonic)
    raw = client.pdb.pack(0x007D)

    class AdvancingSocket(FakeSocket):
        def recv(self, count: int) -> bytes:
            clock.now += 0.25
            return super().recv(count)

    sock = AdvancingSocket([raw] * 20)
    connect_timeouts: list[float] = []

    def open_socket(address: tuple[str, int], timeout: float) -> FakeSocket:
        connect_timeouts.append(timeout)
        return sock

    monkeypatch.setattr(client.socket, "create_connection", open_socket)
    with pytest.raises(TimeoutError, match="deadline"):
        bot.connect(deadline=101.0)
    assert clock.now == 101.0
    assert connect_timeouts == [1.0]
    assert sock.timeouts[-4:] == [1.0, 0.75, 0.5, 0.25]
    assert sock.closed


def test_default_connection_budget_also_bounds_login(bot, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(client.time, "monotonic", clock.monotonic)

    class TimeoutSocket(FakeSocket):
        def recv(self, count: int) -> bytes:
            clock.now += self.timeouts[-1]
            raise TimeoutError()

    sock = TimeoutSocket()
    monkeypatch.setattr(client.socket, "create_connection", lambda *_args, **_kwargs: sock)
    with pytest.raises(TimeoutError, match="deadline"):
        bot.connect()
    assert 100.0 < clock.now <= 145.0
    assert sock.closed


def test_connection_budget_is_shared_across_stages_but_not_runtime(bot, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(client.time, "monotonic", clock.monotonic)
    sock = FakeSocket()

    def login() -> tuple[str, int]:
        clock.now += 2.0
        return "offline", 1

    def chars(ip: str, port: int) -> tuple[str, int]:
        assert bot._connection_timeout(5.0) == 1.0
        return "offline", 1

    def maps(ip: str, port: int) -> None:
        bot.sock = sock
        bot.connected_map = True

    monkeypatch.setattr(bot, "_login_server", login)
    monkeypatch.setattr(bot, "_char_server", chars)
    monkeypatch.setattr(bot, "_map_server", maps)
    assert bot.connect(deadline=103.0) is bot
    clock.now = 1000.0
    assert bot._connection_timeout(5.0) == 5.0
    bot.keepalive()
    assert len(sock.sent) == 1


def test_unsupported_character_creation_fails_closed_before_any_wire_write(bot):
    sock = FakeSocket()
    with pytest.raises(NotImplementedError, match=r"native.*layout"):
        bot._create_char(sock)
    assert not sock.sent
    assert sock.recv_calls == 0


def test_cli_has_no_reusable_credential_defaults():
    tree = ast.parse(CLIENT_PATH.read_text())
    defaulted = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and len(node.args) > 1
        ):
            key = node.args[0]
            if isinstance(key, ast.Constant) and key.value in {"BOT_USER", "BOT_PASS"}:
                defaulted.append(key.value)
    assert defaulted == []


def test_operator_manifest_requires_private_file(bot, tmp_path):
    path = tmp_path / "operator.json"
    path.write_text(json.dumps({"user": bot.user, "password": bot.password}))
    path.chmod(0o644)
    with pytest.raises(ValueError, match="private"):
        client._load_operator_manifest(path)
    path.chmod(0o600)
    values = client._load_operator_manifest(path)
    assert values["user"] == bot.user
    assert values["password"] == bot.password


def test_operator_manifest_refuses_symlink(bot, tmp_path):
    target = tmp_path / "operator.json"
    target.write_text(json.dumps({"user": bot.user, "password": bot.password}))
    target.chmod(0o600)
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(OSError, match="Too many levels of symbolic links"):
        client._load_operator_manifest(link)


def test_map_eof_after_accept_does_not_report_success(bot, monkeypatch):
    accept = client.pdb.pack(0x02EB, bytes(11))
    sock = FakeSocket([accept, b""])
    monkeypatch.setattr(client.socket, "create_connection", lambda *_args, **_kwargs: sock)

    class InlineReader:
        def __init__(self, target: Callable[[], None], **kwargs: object) -> None:
            self.target = target

        def start(self) -> None:
            self.target()

    monkeypatch.setattr(client.threading, "Thread", InlineReader)
    with pytest.raises(ConnectionError, match=r"receive|EOF"):
        bot._map_server("offline", 1)
    assert not bot.connected_map


def test_character_loop_propagates_expired_shared_deadline(bot, monkeypatch):
    clock = FakeClock()

    def advancing_monotonic() -> float:
        clock.now += 0.01
        return clock.now

    monkeypatch.setattr(client.time, "monotonic", advancing_monotonic)
    bot._connect_deadline = 101.0
    bot.aid = 42

    class TimeoutSocket(FakeSocket):
        def recv(self, count: int) -> bytes:
            if self.chunks:
                return super().recv(count)
            clock.now += self.timeouts[-1]
            raise TimeoutError()

    sock = TimeoutSocket([struct.pack("<I", 42)])
    monkeypatch.setattr(client.socket, "create_connection", lambda *_args, **_kwargs: sock)
    with pytest.raises(TimeoutError, match="deadline"):
        bot._char_server("offline", 1)
    assert clock.now < 101.1
    assert sock.closed


def test_login_send_uses_budget_remaining_after_tcp_connect(bot, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(client.time, "monotonic", clock.monotonic)
    bot._connect_deadline = 101.0

    class SendBudgetSocket(FakeSocket):
        def sendall(self, data: bytes) -> None:
            assert self.timeouts
            assert self.timeouts[-1] <= 0.25
            super().sendall(data)

    sock = SendBudgetSocket([client.pdb.pack(0x006A, bytes(21))])

    def open_socket(address: tuple[str, int], timeout: float) -> FakeSocket:
        clock.now = 100.75
        return sock

    monkeypatch.setattr(client.socket, "create_connection", open_socket)
    with pytest.raises(RuntimeError, match="login refused"):
        bot._login_server()
    assert sock.closed


def test_map_send_refuses_expired_handshake_budget(bot, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(client.time, "monotonic", clock.monotonic)
    bot._connect_deadline = 100.0
    sock = FakeSocket()
    bot.sock = sock
    with pytest.raises(TimeoutError, match="deadline"):
        bot._send(client.pdb.pack(0x007D))
    assert not sock.sent


def test_reader_start_failure_still_closes_socket_and_preserves_failure(bot, monkeypatch):
    class CannotStart(threading.Thread):
        def start(self) -> None:
            msg = "offline reader start failed"
            raise RuntimeError(msg)

    sock = FakeSocket()
    monkeypatch.setattr(client.threading, "Thread", CannotStart)
    monkeypatch.setattr(client.socket, "create_connection", lambda *_args, **_kwargs: sock)
    monkeypatch.setattr(bot, "_login_server", lambda: ("offline", 1))
    monkeypatch.setattr(bot, "_char_server", lambda *_args: ("offline", 1))
    with pytest.raises(RuntimeError, match="offline reader start failed"):
        bot.connect()
    assert sock.closed
    assert bot.sock is None
    assert bot.rx_thread is None
