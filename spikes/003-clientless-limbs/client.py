#!/usr/bin/env python3
"""Clientless protocol spike: login -> character -> map, with a receive reader.

The inherited packet table has native corrections in packetdb.py; this module
is not an exhaustive native protocol validation. Character creation is disabled
until its native response layout is independently verified.

Runtime methods: move, say, sit/stand, party_create/invite/reply, keepalive.
Actor lookup keys and actor["gid"] are wire object IDs; actor["char_id"] retains
its separate character ID. self.gid remains the selected character ID required
by the map handshake. The receive reader dispatches frames exactly once; queue
polling and drain observe/discard frames without dispatching them again.
"""

from __future__ import annotations

from collections import deque
from contextlib import contextmanager
import queue
import socket
import struct
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import packetdb as pdb  # noqa: E402

# Resolve the trusted checkout source independently of cwd; package deps remain required.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from robots.adapters.native_actor_presentation import parse_actor_presentation
from robots.adapters.native_progression import (
    SelectedCharacterSnapshot,
    decode_selected_character_snapshot,
)

LOGIN_IP = "127.0.0.1"
LOGIN_PORT = 6900

# CZ_REQUEST_ACT action codes (rAthena enum e_damage_type, clif.hpp)
ACT_SIT = 2
ACT_STAND = 3

# struct PACKET_ZC_NOTIFY_ACT (PACKETVER >= 20131223, packed), verified
# against src/map/packets.hpp: type(i16) srcID(i32) targetID(i32) tick(i32)
# srcSpeed(i32) dmgSpeed(i32) damage(i32) isSPDamage(i8) div(u16) type(u8)
# damage2(i32) => type byte @30, damage i32 @22.
#
# struct PACKET_ZC_ACCEPT_ENTER (0x2eb): type(i16) startTime(u32) posDir[3]
# xSize(u8) ySize(u8) font(u16) => posDir @6 (RBUFPOS-packed).


class BotClient:
    """One clientless bot: a full account + character + map session."""

    def __init__(
        self,
        user: str,
        password: str,
        char_name: str | None = None,
        login_ip: str = LOGIN_IP,
        login_port: int = LOGIN_PORT,
        create_char: bool = False,
        verbose: bool = True,
        pincode: str | None = None,
    ):
        if pincode is not None and (
            type(pincode) is not str
            or len(pincode) != 4
            or any(digit not in "0123456789" for digit in pincode)
        ):
            message = "pincode must be exactly four ASCII digits"
            raise ValueError(message)
        self._pincode = pincode
        self.user = user
        self.password = password
        self.char_name = char_name or (user.capitalize() if user.islower() else user)
        self.login_ip = login_ip
        self.login_port = login_port
        self.create_flag = create_char
        self.verbose = verbose

        # identity
        self.aid = 0  # account id
        self.gid = 0  # character id (GID on the map server)
        # Historical selection receipt only; never continuous current-job authority.
        self.selected_character_snapshot: SelectedCharacterSnapshot | None = None
        self.native_epoch = 0
        self.selection_epoch: int | None = None
        self.map_epoch: int | None = None
        self.class_fresh = False
        self._native_frame_lock = threading.Lock()
        self._native_frame_seq = 0
        self._native_frame_base = 0
        self._native_frame_recording = True
        self._native_frames: deque[tuple[int, float, int, bytes]] = deque(maxlen=4096)
        self.login_id1 = 0
        self.login_id2 = 0
        self.sex = 1

        # world model
        self.x = 0
        self.y = 0
        self.sitting = False
        self.map_name = ""
        self.actors: dict[int, dict] = {}
        # MAIN/pre-re 20180704 SELF status: absent keys mean unreceived.
        self.status_params: dict[int, int] = {}
        self.chat: list[tuple[int, str]] = []
        self.damage: list[tuple[int, int, int, int]] = []
        self.party_id = 0
        self.party_invite_from = ""  # name of last inviter (0x2c6)
        self.party_invite_pid = 0  # party id of last invite
        self.party_members: list[dict] = []
        self.chat_event = threading.Event()
        self.entry_event = threading.Event()
        self.actor_event = threading.Event()
        self.damage_event = threading.Event()

        # plumbing
        self.sock: socket.socket | None = None
        self.rx_buf = b""
        self._connect_deadline: float | None = None
        self._temporary_sockets: list[socket.socket] = []
        self._handshake_buffers: dict[socket.socket, bytes] = {}
        self._handshake_packets: dict[socket.socket, deque[tuple[int, bytes]]] = {}
        self.rx_queue: queue.Queue[tuple[int, bytes]] = queue.Queue()
        self.rx_thread: threading.Thread | None = None
        self.running = False
        self.rx_error: Exception | None = None
        self.cleanup_errors: list[BaseException] = []
        self.dispatch_errors: list[tuple[int, str]] = []
        self.packet_counts: dict[int, int] = {}
        self.raw_log: list[tuple[float, int, bytes]] = []  # last packets, for diagnosis
        self.party_create_result: int | None = None
        self.party_create_event = threading.Event()
        self.party_added: list[str] = []
        self.connected_map = False
        self.log_lines: list[str] = []

    # ------------------------------------------------------------------ util
    def _clear_native_selection(self) -> None:
        """Invalidate historical receipt and session authority at a lifecycle boundary."""
        self.selected_character_snapshot = None
        self.selection_epoch = None
        self.map_epoch = None
        self.class_fresh = False

    def log(self, msg: str) -> None:
        line = f"[{self.user}|{time.strftime('%H:%M:%S')}] {msg}"
        self.log_lines.append(line)
        if self.verbose:
            print(line, flush=True)

    def _recv_exact(self, sock: socket.socket, n: int, timeout: float = 5.0) -> bytes:
        """Receive n bytes; a timeout never discards a partial socket read."""
        while len(self._handshake_buffers.get(sock, b"")) < n:
            sock.settimeout(self._connection_timeout(timeout))
            buf = self._handshake_buffers.get(sock, b"")
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("EOF while receiving")
            self._handshake_buffers[sock] = buf + chunk
        buf = self._handshake_buffers.get(sock, b"")
        self._handshake_buffers[sock] = buf[n:]
        return buf[:n]

    def _send(self, data: bytes) -> None:
        if self.sock is None:
            raise ConnectionError("not connected")
        if self._connect_deadline is not None:
            self.sock.settimeout(self._connection_timeout(0.5))
        self.sock.sendall(data)

    def _connection_timeout(self, limit: float) -> float:
        """Clamp a handshake operation to the remaining monotonic budget."""
        if self._connect_deadline is None:
            return limit
        remaining = self._connect_deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("connection deadline expired")
        return min(limit, remaining)

    def _release_handshake_socket(self, sock):
        """Forget ownership/framing only after the socket exit confirms release.

        socket.socket.__exit__ calls close; a raising exit leaves release unknown.
        Keep this socket context contract for the existing offline transports too.
        """
        try:
            sock.__exit__(None, None, None)
        except BaseException as error:
            self.cleanup_errors.append(error)
            raise
        self._temporary_sockets.remove(sock)
        self._handshake_buffers.pop(sock, None)
        self._handshake_packets.pop(sock, None)

    @contextmanager
    def _handshake_socket(self, address):
        """Own temporary transports until cleanup confirms their release."""
        sock = socket.create_connection(address, timeout=self._connection_timeout(5))
        self._temporary_sockets.append(sock)
        try:
            sock.settimeout(self._connection_timeout(5.0))
            yield sock
        except BaseException as origin:
            try:
                self._release_handshake_socket(sock)
            except BaseException as error:
                origin.add_note(
                    f"temporary cleanup failed ({type(error).__name__}); reuse prohibited"
                )
            raise
        else:
            self._release_handshake_socket(sock)

    # ---------------------------------------------------------------- login
    def _login_server(self) -> tuple[str, int]:
        with self._handshake_socket((self.login_ip, self.login_port)) as s:
            self.log(f"login-server {self.login_ip}:{self.login_port} connected")
            # CA_LOGIN: type.W version.L user[24] pass[24] clienttype.B = 55
            s.sendall(
                pdb.pack(
                    0x0064,
                    struct.pack("<I", 0)
                    + self.user.encode().ljust(24, b"\x00")
                    + self.password.encode().ljust(24, b"\x00")
                    + bytes([0]),
                )
            )
            while True:
                try:
                    pid, raw = self._read_one(s)
                except socket.timeout, TimeoutError:
                    self._connection_timeout(5.0)
                    continue
                if pid == 0x0AC4:  # AC_ACCEPT_LOGIN (modern, len-prefixed)
                    self.login_id1 = struct.unpack_from("<I", raw, 4)[0]
                    self.aid = struct.unpack_from("<I", raw, 8)[0]
                    self.login_id2 = struct.unpack_from("<I", raw, 12)[0]
                    self.sex = raw[46]
                    c_ip = struct.unpack_from("<I", raw, 64)[0]
                    c_port = struct.unpack_from("<H", raw, 68)[0]  # rAthena ntows quirk: LE
                    return socket.inet_ntoa(struct.pack("<I", c_ip)), c_port
                if pid == 0x006A:
                    raise RuntimeError(f"login refused, error={raw[2]}")
                if pid == 0x0081:
                    raise RuntimeError(f"banned, result={raw[2]}")

    @staticmethod
    def _decode_character_list(
        raw: bytes,
    ) -> tuple[list[tuple[int, str, int]], dict[int, SelectedCharacterSnapshot]]:
        """Validate the whole source-shaped list before exposing any candidate."""
        message = "malformed native character list"
        if (
            type(raw) is not bytes
            or len(raw) < 27
            or raw[:2] != b"\x6b\x00"
            or struct.unpack_from("<H", raw, 2)[0] != len(raw)
            or (len(raw) - 27) % 155
        ):
            raise ValueError(message)
        characters: list[tuple[int, str, int]] = []
        snapshots: dict[int, SelectedCharacterSnapshot] = {}
        slots: set[int] = set()
        names: set[str] = set()
        for off in range(27, len(raw), 155):
            row = raw[off : off + 155]
            snapshot = decode_selected_character_snapshot(row)
            name = row[88:112].split(b"\x00")[0].decode(errors="replace")
            if snapshot.raw_char_id in snapshots or snapshot.slot in slots or name in names:
                raise ValueError(message)
            characters.append((snapshot.raw_char_id, name, snapshot.slot))
            snapshots[snapshot.raw_char_id] = snapshot
            slots.add(snapshot.slot)
            names.add(name)
        return characters, snapshots

    def _char_server(self, ip: str, port: int) -> tuple[str, int]:
        self.selected_character_snapshot = None
        self.selection_epoch = None
        self.class_fresh = False
        with self._handshake_socket((ip, port)) as s:
            self.log(f"char-server {ip}:{port} connected")
            # CH_ENTER: AID.L login_id1.L login_id2.L (unused tick).W sex.B = 17
            s.sendall(
                pdb.pack(
                    0x0065,
                    struct.pack("<I", self.aid)
                    + struct.pack("<I", self.login_id1)
                    + struct.pack("<I", self.login_id2)
                    + b"\x00\x00"
                    + bytes([self.sex]),
                )
            )
            echo = self._recv_exact(s, 4)
            echo_aid = struct.unpack("<I", echo)[0]
            if echo_aid != self.aid:
                message = "character account echo mismatch"
                raise RuntimeError(message)

            char_list: list[tuple[int, str, int]] = []
            snapshots: dict[int, SelectedCharacterSnapshot] = {}
            got_6b = False
            pin_ok = False
            pin_attempted = False
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    pid, raw = self._read_one(s, timeout=3)
                except socket.timeout, TimeoutError:
                    self._connection_timeout(3.0)
                    continue
                if pid == 0x082D:
                    self.log(f"HC_ACCEPT_ENTER2: slots normal={raw[4]} total={raw[8]}")
                elif pid == 0x006B:  # HC_ACCEPT_ENTER (len-prefixed)
                    # Pinned MAIN 20180704: header27 and CHARACTER_INFO155.
                    char_list, snapshots = self._decode_character_list(raw)
                    got_6b = True
                elif pid == 0x08B9:
                    seed, pin_aid, state = struct.unpack_from("<IIH", raw, 2)
                    if pin_aid != self.aid:
                        message = "PIN account mismatch"
                        raise RuntimeError(message)
                    if state == 0:
                        pin_ok = True
                    elif state == 1 and not pin_attempted and not pin_ok:
                        if self._pincode is None:
                            message = "PIN authentication requires explicit pincode"
                            raise RuntimeError(message)
                        # char.cpp:2153-2187 decrypts via shuffled table[wire_digit].
                        # Invert that permutation; uint32 arithmetic wraps each step.
                        table = list(range(10))
                        for i in range(1, 10):
                            seed = (0x881234 + seed * 0x3498) & 0xFFFFFFFF
                            pos = seed % (i + 1)
                            table[i], table[pos] = table[pos], table[i]
                        encrypted = bytes(48 + table.index(int(digit)) for digit in self._pincode)
                        # common/packets.hpp:551-564: packed i16/u32/char[4], 10B.
                        # Metadata is registered in the shared pinned packet table.
                        s.settimeout(self._connection_timeout(3.0))
                        pin_attempted = True
                        s.sendall(struct.pack("<HI", 0x08B8, self.aid) + encrypted)
                    else:
                        message = "PIN authentication refused or unsupported state"
                        raise RuntimeError(message)
                elif pid == 0x09A0:
                    pass  # HC_CHARLIST_NOTIFY (page 2 marker)
                elif pid == 0x006C:
                    raise RuntimeError(f"HC_REFUSE_ENTER error={raw[2]}")
                elif pid == 0x0081:
                    raise RuntimeError(f"auth refused, result={raw[2]}")
                elif pid == 0x020D:
                    pass  # HC_BLOCK_CHARACTER (empty)
                else:
                    self.log(f"(char) unhandled 0x{pid:04x} len={len(raw)}")
                if got_6b and pin_ok:
                    break
            if not pin_ok:
                message = "no PIN authentication status"
                raise RuntimeError(message)
            if not got_6b:
                raise RuntimeError("no HC_ACCEPT_ENTER char list")

            self.gid = 0
            if (self.aid, self.char_name) and any(n == self.char_name for _, n, _ in char_list):
                self.gid = next(g for g, n, _ in char_list if n == self.char_name)
                self.log(f"character {self.char_name!r} exists, GID={self.gid}")
            if self.gid == 0 and self.create_flag:
                self.gid = self._create_char(s)
            if self.gid == 0:
                raise RuntimeError(f"character {self.char_name!r} not found and create_flag=False")

            # CH_SELECT_CHAR: slot.B
            slot = next(slot for g, _, slot in char_list if g == self.gid)
            s.settimeout(self._connection_timeout(5.0))
            s.sendall(pdb.pack(0x0066, bytes([slot])))

            map_ip = map_port = None
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                try:
                    pid, raw = self._read_one(s, timeout=3)
                except socket.timeout, TimeoutError:
                    self._connection_timeout(3.0)
                    continue
                if pid == 0x0AC5:  # HC_NOTIFY_ZONESVR modern: NO len word, 156B
                    # type(2) CID(4)@2 mapname[16]@6 ip(4)@22 port(2)@26 domain[128]@28
                    cid = struct.unpack_from("<I", raw, 2)[0]
                    if cid != self.gid:
                        message = "selected character route mismatch"
                        raise RuntimeError(message)
                    self.map_name = raw[6:22].split(b"\x00")[0].decode(errors="replace")
                    m_ip = struct.unpack_from("<I", raw, 22)[0]
                    map_port = struct.unpack_from("<H", raw, 26)[0]
                    map_ip = socket.inet_ntoa(struct.pack("<I", m_ip))
                elif pid == 0x0071:  # classic
                    cid = struct.unpack_from("<I", raw, 2)[0]
                    if cid != self.gid:
                        message = "selected character route mismatch"
                        raise RuntimeError(message)
                    self.map_name = raw[6:22].split(b"\x00")[0].decode(errors="replace")
                    m_ip = struct.unpack_from("<I", raw, 22)[0]
                    map_port = struct.unpack_from("<H", raw, 26)[0]
                    map_ip = socket.inet_ntoa(struct.pack("<I", m_ip))
                elif pid == 0x0081:
                    raise RuntimeError(f"auth refused, result={raw[2]}")
                elif pid == 0x0840:
                    raise RuntimeError("map name not accessible")
                else:
                    continue
                self.log(f"map-server {map_ip}:{map_port} for {self.map_name!r} (CID={cid})")
                self.selected_character_snapshot = snapshots[self.gid]
                if self.native_epoch > 0:
                    self.selection_epoch = self.native_epoch
                    self.class_fresh = True
                return map_ip, map_port
            raise RuntimeError("no HC_NOTIFY_ZONESVR")

    def _create_char(self, s: socket.socket) -> int:
        """Fail closed until native character-creation response layout is verified."""
        raise NotImplementedError(
            "character creation disabled: native response layout is not verified; "
            "use an existing operator-provisioned character"
        )

    # ------------------------------------------------------------------ map
    def _map_server(self, ip: str, port: int) -> None:
        self.status_params.clear()
        self.sock = socket.create_connection((ip, port), timeout=self._connection_timeout(5))
        if self.selection_epoch == self.native_epoch and self.native_epoch > 0:
            self.map_epoch = self.native_epoch
        else:
            self.map_epoch = None
            self.class_fresh = False
        self.log(f"map-server connected {ip}:{port}")
        # CZ_ENTER 0x0888 (WantToConnection for this PACKETVER; 19 bytes):
        # AID.L CID.L login_id1.L client_tick.L sex.B
        self._send(
            pdb.pack(
                0x0888,
                struct.pack("<I", self.aid)
                + struct.pack("<I", self.gid)
                + struct.pack("<I", self.login_id1)
                + struct.pack("<I", 0x12345678)
                + bytes([self.sex]),
            )
        )
        self.rx_buf = b""
        self.running = True
        self.rx_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self.rx_thread.start()

        seen: set[int] = set()
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.rx_error is not None:
                raise ConnectionError("map receive failed during handshake") from self.rx_error
            if self.dispatch_errors:
                raise RuntimeError("map dispatch failed during handshake")
            pid, raw = self._poll(timeout=self._connection_timeout(2))
            if self.rx_error is not None:
                raise ConnectionError("map receive failed during handshake") from self.rx_error
            if pid is None:
                continue
            seen.add(pid)
            if pid == 0x0283:
                self.log(f"SC_NOTIFY_AUTH AID={struct.unpack_from('<I', raw, 2)[0]}")
            if pid == 0x02EB:  # ZC_ACCEPT_ENTER (0x2eb): posDir[3] @6, RBUFPOS-packed
                # Reader already applied entry and any later position frames.
                # Polling is observation only; never rewind to this queued entry.
                self._send(pdb.pack(0x007D))  # CZ_NOTIFY_ACTORINIT: map load done
                self.log(f"ZC_ACCEPT_ENTER: start pos ({self.x},{self.y}) -> LoadEndAck sent")
                # The handshake poll consumed the entry frame before the reader
                # existed, so the tracker never saw it: no own-position seed and
                # no inventory-known marker -> scripts gate on unknown state and
                # never act (fx0's shop-interior deadlock, w43-48). Dispatch the
                # consumed frame so the view starts seeded on EVERY login.
                try:
                    self._dispatch(pid, raw)
                except Exception as exc:  # never fail the join over telemetry
                    self.log(f"entry dispatch error: {exc}")
                self.connected_map = True
                return
            elif pid == 0x0074:
                raise RuntimeError(f"ZC_REFUSE_ENTER error={raw[2]}")
            elif pid == 0x0081:
                raise RuntimeError(f"map auth refused, result={raw[2]}")
        # Classify the stall shape (rest-farm-balance join bisect): the shape
        # names the fix instead of a generic timeout.
        if 0x0091 in seen and 0x02EB not in seen:
            shape = "map session pre-exists (0x0091 without 0x02EB); relogin required"
        elif 0x0283 in seen:
            shape = "auth seen (0x0283) but never accepted (no 0x02EB)"
        else:
            shape = "no map-server response"
        raise RuntimeError(
            f"no ZC_ACCEPT_ENTER from map-server ({shape}; "
            f"observed {sorted(hex(p) for p in seen)})"
        )

    # ----------------------------------------------------------- public API
    def connect(self, *, deadline: float | None = None) -> "BotClient":
        """Connect within an absolute monotonic deadline (default: 35 seconds).

        The budget covers the whole handshake, not the long-lived map reader.
        """
        with self._native_frame_lock:
            self.native_epoch += 1
            self._native_frame_recording = False
            self._native_frames.clear()
        self._clear_native_selection()
        self.status_params.clear()
        self._connect_deadline = time.monotonic() + 35.0 if deadline is None else deadline
        try:
            self.close()  # a prior reader must stop before any state is reused
            self.selected_character_snapshot = None
            self.selection_epoch = None
            self.map_epoch = None
            self.class_fresh = False
            with self._native_frame_lock:
                self._native_frames.clear()
                self._native_frame_base = self._native_frame_seq
                self._native_frame_recording = True
            self.status_params.clear()  # discard any final dispatch from the old reader
            self.rx_buf = b""
            self.drain()
            self._handshake_buffers.clear()
            self._handshake_packets.clear()
            self.rx_error = None
            self.dispatch_errors.clear()
            self._connection_timeout(5.0)
            ip, port = self._login_server()
            self._connection_timeout(5.0)
            ip, port = self._char_server(ip, port)
            self._connection_timeout(5.0)
            self._map_server(ip, port)
            self._connection_timeout(5.0)
            return self
        except BaseException as origin:
            try:
                self.close()
            except BaseException as cleanup_error:
                self.cleanup_errors.append(cleanup_error)
                origin.add_note(
                    f"cleanup failed ({type(cleanup_error).__name__}); reuse prohibited"
                )
            raise
        finally:
            self._connect_deadline = None

    def close(self) -> None:
        """Interrupt and join the reader before permitting another connection."""
        self._clear_native_selection()
        self.running = False
        with self._native_frame_lock:
            self._native_frame_recording = False
            self._native_frames.clear()
        self.connected_map = False
        temporary_errors = []
        for temporary in list(self._temporary_sockets):
            try:
                self._release_handshake_socket(temporary)
            except BaseException as error:
                temporary_errors.append(error)
        sock = self.sock
        socket_error = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            except BaseException as error:
                self.cleanup_errors.append(error)
                socket_error = error
            try:
                sock.close()
            except BaseException as error:
                self.cleanup_errors.append(error)
                socket_error = error
        thread = self.rx_thread
        reader_error = None
        try:
            if (
                thread is not None
                and thread.is_alive()
                and thread is not threading.current_thread()
            ):
                remaining = (
                    2.0
                    if self._connect_deadline is None
                    else max(0.0, min(2.0, self._connect_deadline - time.monotonic()))
                )
                thread.join(timeout=remaining)
            if thread is not None and thread.is_alive():
                raise RuntimeError("receive reader did not stop; client cannot be reused")
        except BaseException as error:
            self.cleanup_errors.append(error)
            reader_error = error
        if reader_error is not None:
            raise RuntimeError(
                "receive reader did not stop or cleanup failed; client cannot be reused"
            ) from reader_error
        if socket_error is not None:
            raise RuntimeError("socket cleanup failed; client cannot be reused") from socket_error
        self.rx_thread = self.sock = None
        self._clear_native_selection()
        with self._native_frame_lock:
            self._native_frames.clear()
            self._native_frame_base = self._native_frame_seq
        if temporary_errors:
            raise RuntimeError(
                "temporary socket cleanup failed; client cannot be reused"
            ) from temporary_errors[0]

    def move(self, x: int, y: int) -> None:
        """CZ_REQUEST_MOVE (0x035f): 3B PosDir, WBUFPOS-packed dest (dir 0)."""
        # server: RBUFPOS -> x = (p0<<2)|(p1>>6), y = ((p1&0x3f)<<4)|(p2>>4)
        # (clif.cpp WBUFPOS/RBUFPOS; RFIFOPOS in clif_parse_WalkToXY)
        b0 = (x >> 2) & 0xFF
        b1 = ((x & 0x03) << 6) | ((y >> 4) & 0x3F)
        b2 = ((y & 0x0F) << 4) & 0xFF
        self._send(pdb.pack(0x035F, bytes([b0, b1, b2])))
        self.log(f"move -> ({x},{y})")

    def say(self, text: str) -> None:
        """CZ_REQUEST_CHAT (0x00f3): len-prefixed '<name> : <message>'."""
        body = f"{self.char_name} : {text}".encode() + b"\x00"
        self._send(pdb.pack(0x00F3, body))
        self.log(f"say {text!r}")

    def sit(self) -> None:
        self._send(pdb.pack(0x0437, struct.pack("<I", self.gid) + bytes([ACT_SIT])))

    def stand(self) -> None:
        self._send(pdb.pack(0x0437, struct.pack("<I", self.gid) + bytes([ACT_STAND])))

    def party_create(self, name: str) -> None:
        """CZ_PARTY_CREATE2 (0x01e8): name[24] item_pickup.B item_share.B."""
        self._send(pdb.pack(0x01E8, name.encode().ljust(24, b"\x00") + bytes([1, 1])))
        self.log(f"party_create {name!r}")

    def party_invite(self, name: str) -> None:
        """CZ_PARTY_JOIN_REQ (0x086d): invite by name (PACKETVER-correct)."""
        self._send(pdb.pack(0x086D, name.encode().ljust(24, b"\x00")))

    def party_reply(self, party_id: int, accept: bool = True) -> None:
        """CZ_PARTY_JOIN_REQ_ACK (0x2c7): party_id.L flag.B (1 = accept)."""
        self._send(pdb.pack(0x02C7, struct.pack("<I", party_id) + bytes([1 if accept else 0])))

    def keepalive(self) -> None:
        """CZ_REQUEST_TIME (0x0360): final unshuffled tick registration."""
        self._send(pdb.pack(0x0360, struct.pack("<I", int(time.time() * 1000) & 0xFFFFFFFF)))

    # ------------------------------------------------------------- recv loop
    def _read_one(self, sock: socket.socket, timeout: float = 5.0) -> tuple[int, bytes]:
        """Read one frame, retaining partial bytes and every coalesced frame."""
        pending = self._handshake_packets.setdefault(sock, deque())
        while True:
            self._connection_timeout(timeout)
            if pending:
                return pending.popleft()
            packets, rest = pdb.parse_stream(self._handshake_buffers.get(sock, b""))
            self._handshake_buffers[sock] = rest
            pending.extend(packets)
            if pending:
                return pending.popleft()
            sock.settimeout(self._connection_timeout(timeout))
            chunk = sock.recv(65536)
            if not chunk:
                raise ConnectionError("EOF while receiving handshake")
            self._handshake_buffers[sock] += chunk

    def _poll(self, timeout: float = 0.5) -> tuple[int | None, bytes]:
        try:
            return self.rx_queue.get(timeout=timeout)
        except queue.Empty:
            return None, b""

    def _recv_loop(self) -> None:
        """Background reader: parses frames and feeds the world model."""
        try:
            sock = self.sock
            if sock is None:
                return
            sock.settimeout(0.5)
            while self.running:
                try:
                    chunk = sock.recv(65536)
                except socket.timeout, TimeoutError:
                    continue
                if not chunk:
                    if self.running:
                        self.rx_error = ConnectionError("EOF from map-server")
                        self.log("map-server closed connection")
                    break
                self.rx_buf += chunk
                packets, self.rx_buf = pdb.parse_stream(self.rx_buf)
                for pid, raw in packets:
                    self.packet_counts[pid] = self.packet_counts.get(pid, 0) + 1
                    self.raw_log.append((time.time(), pid, raw))
                    if len(self.raw_log) > 200:
                        del self.raw_log[:-100]
                    self.rx_queue.put((pid, raw))  # for _poll / handshake
                    try:
                        self._dispatch(pid, raw)
                    except Exception as exc:  # keep the loop alive, retain health failure
                        self.dispatch_errors.append((pid, str(exc)))
                        self.log(f"dispatch error on 0x{pid:04x}: {exc}")
        except Exception as exc:
            if self.running:
                self.rx_error = exc
                self.log(f"receive error: {exc}")
        finally:
            self.running = False
            self.connected_map = False

    # ---------------------------------------------------------- world model
    def _dispatch(self, pid: int, raw: bytes) -> None:
        self._dispatch_world(pid, raw)
        with self._native_frame_lock:
            self._native_frame_seq += 1
            if self._native_frame_recording:
                self._native_frames.append((self._native_frame_seq, time.monotonic(), pid, raw))

    def native_frame_snapshot(
        self,
    ) -> tuple[int, int, tuple[tuple[int, float, int, bytes], ...]]:
        """Atomic bounded map-frame copy; consumers must fail closed on sequence gaps.

        Sequence numbers survive reconnects; each epoch starts at base_seq. This
        ring excludes login/character/PIN handshakes and contains successful
        dispatches only. Raw diagnostic logs and queue polling remain unchanged.
        """
        with self._native_frame_lock:
            return self.native_epoch, self._native_frame_base, tuple(self._native_frames)

    def _dispatch_world(self, pid: int, raw: bytes) -> None:
        if pid == 0x01D7:
            # packets_struct.hpp ZC_SPRITE_CHANGE; clif.cpp disguised_bl_id
            # maps SELF AID to uint32(-int32(AID)). Appearance is not class.
            if type(raw) is not bytes or len(raw) != 11 or raw[:2] != b"\xd7\x01":
                message = "malformed native appearance packet"
                raise ValueError(message)
            _, aid, kind, _, _ = struct.unpack("<HIBHH", raw)
            if kind == 0 and aid in (self.aid, (-self.aid) & 0xFFFFFFFF):
                self.class_fresh = False
        elif pid == 0x02EB:
            if type(raw) is not bytes or len(raw) != 13 or raw[:2] != b"\xeb\x02":
                message = "malformed native entry position packet"
                raise ValueError(message)
            self.x, self.y = self._rbufpos(raw, 6)
        elif pid == 0x00B0:
            # Pinned packets_struct.hpp:354-359: packed i16/u16/i32.
            if len(raw) != 8 or raw[:2] != b"\xb0\x00":
                message = "malformed native status packet"
                raise ValueError(message)
            _, parameter, count = struct.unpack("<HHi", raw)
            if parameter in (5, 6, 7, 8, 11, 55):
                self.status_params[parameter] = count

        elif pid == 0x008D:  # ZC_NOTIFY_CHAT: len.W GID.L msg[]
            gid = struct.unpack_from("<I", raw, 4)[0]
            msg = raw[8:].split(b"\x00")[0].decode(errors="replace")
            self.chat.append((gid, msg))
            self.chat_event.set()
            self.log(f"chat from {gid}: {msg!r}")

        elif pid == 0x008E:  # ZC_NOTIFY_UPDATECHAT (self echo): len.W msg[]
            msg = raw[4:].split(b"\x00")[0].decode(errors="replace")
            self.chat.append((self.gid, msg))
            self.chat_event.set()
            self.log(f"chat (self): {msg!r}")

        elif pid == 0x009A:  # ZC_BROADCAST: len.W msg[]
            msg = raw[4:].split(b"\x00")[0].decode(errors="replace")
            self.chat.append((0, msg))
            self.chat_event.set()
            self.log(f"broadcast: {msg!r}")

        elif pid == 0x0080:  # ZC_NOTIFY_VANISH: GID.L
            gid = struct.unpack_from("<I", raw, 2)[0]
            self.actors.pop(gid, None)

        elif pid == 0x08C8:  # ZC_NOTIFY_ACT (damage / sit / stand)
            # LIVE-VERIFIED (len 34): type(i16) srcID@2 targetID@6 tick@10
            # srcSpeed@14 dmgSpeed@18 damage(i32)@22 isSP(i8)@26 div(u16)@27
            # type(u8)@29 damage2(i32)@30  -- note: srcID is bl.id (AID for PCs)
            src, tgt = struct.unpack_from("<ii", raw, 2)
            dmg = struct.unpack_from("<i", raw, 22)[0]
            act_type = raw[29]
            self.damage.append((src, tgt, dmg, act_type))
            self.damage_event.set()
            if act_type in (ACT_SIT, ACT_STAND):
                self.log(f"act {act_type} (sit/stand) by {src}")
            else:
                self.log(f"damage {src}->{tgt}: {dmg}")

        elif pid in (0x09FD, 0x09FE, 0x09FF):  # walking / new / stand entries
            info = self._parse_actor_entry(pid, raw)
            if info:
                self.actors[info["gid"]] = info
                self.actor_event.set()
                self.log(f"actor entry 0x{pid:04x}: {info}")

        elif pid == 0x02C6:  # ZC_PARTY_JOIN_REQ (incoming invite)
            self.party_invite_pid = struct.unpack_from("<I", raw, 2)[0]
            self.party_invite_from = raw[6:30].split(b"\x00")[0].decode(errors="replace")
            self.log(
                f"party invite from {self.party_invite_from!r} (party {self.party_invite_pid})"
            )

        elif pid == 0x02C5:  # ZC_PARTY_JOIN_REQ_ACK (invite result to inviter)
            nick = raw[2:26].split(b"\x00")[0].decode(errors="replace")
            result = struct.unpack_from("<i", raw, 26)[0]
            self.log(f"party invite result for {nick!r}: {result}")

        elif pid == 0x00FA:  # ZC_ACK_MAKE_GROUP
            self.party_create_result = raw[2]
            self.party_create_event.set()
            self.log(f"party create result={raw[2]}")

        elif pid == 0x0AE5:  # ZC_GROUP_LIST (len-prefixed)
            members = []
            off = 4 + 24
            # PACKET_ZC_GROUP_LIST_SUB: AID(u32) GID(u32) name[24] map[16]
            # leader(u8) offline(u8) class(i16) baseLevel(i16)
            per = 4 + 4 + 24 + 16 + 1 + 1 + 2 + 2
            while off + per <= len(raw):
                aid, gid = struct.unpack_from("<II", raw, off)
                name = raw[off + 8 : off + 32].split(b"\x00")[0].decode(errors="replace")
                leader = raw[off + 48]
                members.append({"aid": aid, "gid": gid, "name": name, "leader": leader})
                off += per
            self.party_members = members
            self.log(f"party roster: {[m['name'] for m in members]}")

        elif pid == 0x0AE4:  # ZC_ADD_MEMBER_TO_GROUP
            # AID(u32)@2 GID(u32)@6 leader(u32)@10 class(i16)@14 baseLevel(i16)@16
            # x(i16)@18 y(i16)@20 offline(u8)@22 partyName[24]@23 playerName[24]@47
            aid = struct.unpack_from("<I", raw, 2)[0]
            name = raw[47:71].split(b"\x00")[0].decode(errors="replace")
            self.party_added.append(name)
            self.log(f"party member added: {name!r} (AID {aid})")

        elif pid in (0x0091, 0x0092, 0x0AC7):
            # clif_changemap is same-server position refresh (including login).
            # clif_changemapserver is a cross-server route, NOT fresh auth.
            size = {0x0091: 22, 0x0092: 28, 0x0AC7: 156}[pid]
            if type(raw) is not bytes or len(raw) != size or raw[:2] != struct.pack("<H", pid):
                message = "malformed native map position packet"
                raise ValueError(message)
            self.map_name = raw[2:18].split(b"\x00")[0].decode(errors="replace")
            self.x, self.y = struct.unpack_from("<HH", raw, 18)
            if pid != 0x0091:
                self.class_fresh = False
                self.map_epoch = None
            elif self.connected_map is True and self.running is True and self.sock is not None:
                # pc_setpos7116-25 removes the PC before this same-server frame;
                # LoadEndAck10752-10850 restores its block and area perception.
                # Initial coalesced map refreshes precede connected_map and use
                # the existing entry ACK. An already-added PC ignores duplicates.
                self._send(pdb.pack(0x007D))
            self.log(f"map change to ({self.x},{self.y})")

    # Pinned MAIN 20180704/pre-renewal compiler layout, using unaltered
    # packet struct excerpts (tests/test_protocol_rereview_repairs.py).
    # These offsets are native-source evidence, not renewed live acceptance.
    #   0 PacketType(i16) 2 PacketLength(i16) 4 objecttype(u8) 5 AID(u32)
    #   9 GID(u32) 13 speed(i16) 15 bodyState(i16) 17 healthState(i16)
    #   19 effectState(i32) 23 job(i16) 25 head(i16) 27 weapon(u32)
    #   MAIN shield guard >=20181121 is inactive: no shield field here.
    #   31 accessory(i16) 33 accessory2 35 accessory3 37 headpalette
    #   39 bodypalette 41 headDir 43 robe 45 GUID(u32) 49 GEmblemVer(i16)
    #   51 honor(i16) 53 virtue(i32) 57 isPK(u8) 58 sex(u8)
    #   spawn (0x9fe, 103B): PosDir[3]@59 xSize@62 ySize@63 clevel@64
    #                        font@66 maxHP@68 HP@72 isBoss@76 body@77 name@79
    #   idle   (0x9ff, 104B): same + state(u8)@64 (name@80)
    #   walking(0x9fd, 110B): moveStartTime(u32)@33 shifts tail +4:
    #                        MoveData[6]@63 (WBUFPOS2 from+to) name@86
    ENTRY_WIRE_ID_OFF = 5
    ENTRY_GID_OFF = 9  # separate character ID, never the actor lookup key
    ENTRY_JOB_OFF = 23
    ENTRY_POSDIR_OFF = 59  # idle (0x9ff) & spawn (0x9fe)
    ENTRY_MOVEDATA_OFF = 63  # walking (0x9fd): MoveData[6] (WBUFPOS2)
    ENTRY_NAME_OFF_SPAWN = 79  # 0x9fe (len 103)
    ENTRY_NAME_OFF_IDLE = 80  # 0x9ff (len 104)
    ENTRY_NAME_OFF_WALK = 86  # 0x9fd (native len 110)

    @staticmethod
    def _rbufpos(p: bytes, o: int) -> tuple[int, int]:
        """RBUFPOS (clif.cpp): decode a 3-byte WBUFPOS position at offset o."""
        x = (p[o] << 2) | (p[o + 1] >> 6)
        y = ((p[o + 1] & 0x3F) << 4) | (p[o + 2] >> 4)
        return x, y

    @classmethod
    def _parse_actor_entry(cls, pid: int, raw: bytes) -> dict | None:
        """
        packet_unit_walking (0x9fd) / packet_spawn_unit (0x9fe) /
        packet_idle_unit (0x9ff). Layout compiler-verified (see comment above);
        sizes 110 / 103 / 104.
        """
        metadata = parse_actor_presentation(raw)
        if metadata.packet_id != pid:
            message = "Invalid native actor presentation frame"
            raise ValueError(message)
        gid = metadata.actor_id
        char_id = metadata.character_id
        job = struct.unpack_from("<H", raw, cls.ENTRY_JOB_OFF)[0]
        if pid == 0x09FD:  # walking: WBUFPOS2 MoveData[6]: from + to
            o = cls.ENTRY_MOVEDATA_OFF
            fx, fy = cls._rbufpos(raw, o)
            # RBUFPOS2 packs the destination across bytes 2..4; it is not
            # a second independent three-byte PosDir (clif.cpp:225..230).
            tx = ((raw[o + 2] & 0x0F) << 6) | (raw[o + 3] >> 2)
            ty = ((raw[o + 3] & 0x03) << 8) | raw[o + 4]
            info: dict = {
                "gid": gid,
                "job": job,
                "x": tx,
                "y": ty,
                "from": (fx, fy),
                "walking": True,
            }
            name_off = cls.ENTRY_NAME_OFF_WALK
        else:  # spawn / stand: PosDir[3]
            x, y = cls._rbufpos(raw, cls.ENTRY_POSDIR_OFF)
            info = {"gid": gid, "job": job, "x": x, "y": y, "walking": False}
            name_off = cls.ENTRY_NAME_OFF_IDLE if pid == 0x09FF else cls.ENTRY_NAME_OFF_SPAWN
        info["char_id"] = char_id
        info["objecttype"] = metadata.objecttype
        if len(raw) >= name_off:
            info["name"] = raw[name_off : name_off + 24].split(b"\x00")[0].decode(errors="replace")
        return info

    # ------------------------------------------------------------ shortcuts
    def wait_for(self, predicate, timeout: float = 5.0):
        """Block until predicate() is truthy (polled every 0.1s)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            result = predicate()
            if result:
                return result
            time.sleep(0.1)
        return None

    def dump_recent(self, n: int = 10) -> str:
        """Last n raw packets as hex, for FAIL diagnosis."""
        lines = []
        for ts, pid, raw in self.raw_log[-n:]:
            lines.append(f"  0x{pid:04x} ({pdb.name_of(pid)}) len={len(raw)}: {raw.hex()}")
        return "\n".join(lines) if lines else "  (no packets)"

    def wait_for_chat(self, needle: str, timeout: float = 5.0) -> tuple[int, str] | None:
        """Block until a chat line containing needle arrives (or timeout)."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            for gid, msg in self.chat:
                if needle in msg:
                    return gid, msg
            self.chat_event.wait(0.2)
            self.chat_event.clear()
        return None

    def wait_for_actor(self, gid: int, timeout: float = 5.0) -> dict | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if gid in self.actors:
                return self.actors[gid]
            self.actor_event.wait(0.2)
            self.actor_event.clear()
        return None

    def drain(self) -> None:
        """Discard observed frames; the receive reader already dispatched them."""
        while True:
            try:
                self.rx_queue.get_nowait()
            except queue.Empty:
                return


def _load_operator_manifest(path: Path) -> dict:
    """Read explicitly supplied credentials from an owner-only regular file."""
    import json
    import os
    import stat

    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "r") as stream:
        metadata = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.getuid()
            or metadata.st_mode & 0o077
        ):
            raise ValueError("operator manifest must be a private owner-only regular file")
        values = json.load(stream)
    if not isinstance(values, dict):
        raise ValueError("operator manifest must contain one account object")
    for key in ("user", "password"):
        value = values.get(key)
        if not isinstance(value, str) or not value or len(value.encode()) > 24:
            raise ValueError(f"operator manifest requires a nonempty {key} of at most 24 bytes")
    return values


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Offline-capable clientless protocol spike")
    parser.add_argument(
        "manifest", type=Path, help="private JSON account manifest (no credentials in argv)"
    )
    options = parser.parse_args()
    account = _load_operator_manifest(options.manifest)
    bot = BotClient(
        account["user"],
        account["password"],
        char_name=account.get("char_name"),
        login_ip=account.get("login_ip", LOGIN_IP),
        login_port=account.get("login_port", LOGIN_PORT),
        create_char=False,
    )
    try:
        bot.connect()
        bot.say("LFG")
        bot.move(bot.x + 1, bot.y)
        time.sleep(2)
    finally:
        bot.close()
