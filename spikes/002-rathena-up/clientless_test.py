#!/usr/bin/env python3
"""
Spike 002-rathena-up: clientless RO protocol test (stdlib only: socket + struct + time).

Chosen server packet version: PACKETVER 20180704, pre-renewal (PRERE), packet
obfuscation disabled, PIN code disabled (see README.md).

Packet IDs verified against rAthena sources (src/common/packets.hpp,
src/map/clif_packetdb.hpp) for PACKETVER 20180704:
  CA_LOGIN                0x0064 (55 bytes, plaintext password)
  AC_ACCEPT_LOGIN         0x0069
  AC_REFUSE_LOGIN         0x006a
  CH_SELECT_CHAR          0x0066 (3 bytes: type + slot)
  CH_MAKE_CHAR            0x0067 (37 bytes: name[24] str agi vit int dex luk slot hair_color.W hair_style.W)
  CH_ENTER                0x0436 (19 bytes: AID.L CID.L login_id1.L client_tick.L sex.B)
  HC_ACCEPT_ENTER         0x006b
  HC_ACCEPT_MAKECHAR      0x006d
  HC_REFUSE_MAKECHAR      0x006e
  HC_NOTIFY_ZONESVR       0x0071 (CID.L mapname[16] ip.L port.W)
  SC_NOTIFY_BAN           0x0081
  ZC_ACCEPT_ENTER         0x0073 (auth ok, map entry)
  ZC_REFUSE_ENTER         0x0074
  CZ_REQUEST_TIME         0x007e -> ZC_NOTIFY_TIME 0x007f
  ZC_NOTIFY_UPDATECHAT    0x008e (self chat echo)
  ZC_NOTIFY_CHAT          0x008d (chat from others/npc)
  ZC_BROADCAST            0x009a (global broadcast; MOTD may arrive as 0x009a/0x01c3)

Chain: login(6900) -> char(6121) -> map(5121).
"""
import socket
import struct
import sys
import time

LOGIN_IP = "127.0.0.1"
LOGIN_PORT = 6900
USER = "spikebot01"
PASS = "spikepass123"
CHAR_NAME = "SpikeBot01"

t0 = time.time()
def ts():
    return f"[{time.time()-t0:7.3f}s] "

def recv_exact(sock, n, timeout=5.0):
    sock.settimeout(timeout)
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("EOF while receiving")
        buf += chunk
    return buf

def recv_packet(sock, timeout=5.0):
    """Read one packet: 2-byte id, then length (from packet_db or fixed)."""
    hdr = recv_exact(sock, 2, timeout)
    pid = struct.unpack("<H", hdr)[0]
    # variable-length packets (packet_db lengths for our version); 0x0ac4 = modern AC_ACCEPT_LOGIN
    var_len = {0x69, 0x6b, 0x8d, 0x8e, 0x9a, 0x1c3, 0x2eb, 0x0ac4, 0x0828, 0x0840, 0x09a0, 0x020d}
    if pid in var_len:
        rest = recv_exact(sock, 2, timeout)
        # .W at offset 2 = total length incl. the 2 id bytes and the 2 length bytes
        ln_total = struct.unpack("<H", rest)[0]
        body = recv_exact(sock, max(0, ln_total - 4), timeout)
        return pid, hdr + rest + body
    fixed_len = {
        0x6a: 23, 0x6c: 3, 0x6d: 110, 0x6e: 3, 0x6f: 2, 0x70: 3,
        0x71: 150, 0x73: 11, 0x74: 3, 0x7f: 6, 0x81: 3,
        0x82: 2, 0x83: 2, 0x84: 2, 0x283: 6,
        0x082d: 29, 0x08b9: 10, 0x099d: 4,
    }
    ln = fixed_len.get(pid, 2)
    body = recv_exact(sock, ln - 2, timeout)
    return pid, hdr + body

def hexdump(data, limit=64):
    return data[:limit].hex(" ")

def main():
    # ---------- 1. LOGIN ----------
    print(ts() + f"connecting to login-server {LOGIN_IP}:{LOGIN_PORT} ...")
    s = socket.create_connection((LOGIN_IP, LOGIN_PORT), timeout=5)
    print(ts() + "TCP connected")

    # PACKET_CA_LOGIN (packed): type.W + version.L + username[24] + password[24] + clienttype.B = 55
    p = struct.pack("<HI24s24sB",
                    0x0064,   # CA_LOGIN
                    0,        # client version (unchecked)
                    USER.encode().ljust(24, b"\x00"),
                    PASS.encode().ljust(24, b"\x00"),
                    0)        # clienttype 0 = normal binary client
    assert len(p) == 55, len(p)
    s.sendall(p)
    print(ts() + "-> CA_LOGIN (0x0064) sent, 55 bytes")

    while True:
        pid, data = recv_packet(s)
        if pid in (0x0069, 0x0ac4):
            t_login = time.time() - t0
            modern = pid == 0x0ac4  # PACKETVER >= 20170315: token + 128-byte unknown per server
            print(ts() + f"<- AC_ACCEPT_LOGIN (0x{pid:04x}), {len(data)} bytes, dt={t_login:.3f}s")
            # struct: .W id .W len .L login_id1 .L AID .L login_id2 .L last_ip .B[26] last_login .B sex
            #         [+ token[17] if modern]
            login_id1 = struct.unpack_from("<I", data, 4)[0]
            aid       = struct.unpack_from("<I", data, 8)[0]
            login_id2 = struct.unpack_from("<I", data, 12)[0]
            # sex sits after last_login[26]: 2+2+4+4+4+4 + 26 = 46
            sex       = data[46]  # 0=F, 1=M (SEX_FEMALE/SEX_MALE enum)
            entry_hdr = 64 if modern else 47     # header incl. token when modern
            entry_size = 158 if modern else 32
            off = entry_hdr
            c_ip = struct.unpack_from("<I", data, off)[0]
            c_port_le = struct.unpack_from("<H", data, off+4)[0]  # rAthena sends port little-endian (ntows quirk)
            c_name = data[off+6:off+26].split(b"\x00")[0].decode()
            ip_str = socket.inet_ntoa(struct.pack("<I", c_ip))
            print(ts() + f"   AID={aid} login_id1={login_id1:#x} login_id2={login_id2:#x} sex={sex}")
            print(ts() + f"   char-server: {c_name!r} {ip_str}:{c_port_le}")
            break
        elif pid == 0x006a:
            err = data[2]
            print(ts() + f"<- AC_REFUSE_LOGIN (0x006a) error={err}")
            sys.exit(1)
        elif pid == 0x0081:
            print(ts() + f"<- SC_NOTIFY_BAN (0x0081) result={data[2]}")
            sys.exit(1)
        else:
            print(ts() + f"<- (login) unexpected 0x{pid:04x} {hexdump(data)}")

    s.close()

    # ---------- 2. CHAR SERVER ----------
    print(ts() + f"connecting to char-server {ip_str}:{c_port_le} ...")
    c = socket.create_connection((ip_str, c_port_le), timeout=5)
    print(ts() + "TCP connected")

    p = struct.pack("<HHLLLHB",
                    0x0065,   # connect of player
                    0,        # (padding, rAthena reads from offset 2)
                    aid, login_id1, login_id2,
                    0,        # who (unused)
                    sex)
    # NOTE: rAthena chclif_parse_reqtoconnect reads: .L account_id @2, .L login_id1 @6,
    # .L login_id2 @10, (tick @14 unused), .B sex @16  => 17 bytes total
    p = struct.pack("<HHLLLB", 0x0065, 0, aid, login_id1, login_id2, sex)[:17]
    # rebuild explicitly to be safe:
    p = struct.pack("<H", 0x0065) + struct.pack("<I", aid) + struct.pack("<I", login_id1) \
        + struct.pack("<I", login_id2) + b"\x00\x00" + struct.pack("<B", sex)
    assert len(p) == 17, len(p)
    c.sendall(p)
    print(ts() + "-> CH_CONNECT (0x0065) sent, 17 bytes")

    # char-server replies: 4 bytes raw AID echo, then possibly auth result, then char list
    first = recv_exact(c, 4)
    echo_aid = struct.unpack("<I", first)[0]
    print(ts() + f"<- AID echo: {echo_aid} (expect {aid})")

    # after account data round-trip we get HC_ACCEPT_ENTER2 0x82d (>=2013) then 0x6b char list
    char_list = None
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            pid, data = recv_packet(c, timeout=3)
        except (socket.timeout, TimeoutError):
            continue
        if pid == 0x081:
            print(ts() + f"<- SC_NOTIFY_BAN (0x0081) result={data[2]} (auth refused)")
            sys.exit(1)
        elif pid == 0x082d:
            if len(data) >= 9:
                print(ts() + f"<- HC_ACCEPT_ENTER2 (0x082d) slots: normal={data[4]} premium={data[5]} billing={data[6]} total={data[8]}")
            else:
                print(ts() + f"<- HC_ACCEPT_ENTER2 (0x082d) {len(data)} bytes")
        elif pid == 0x06b:
            t_char = time.time() - t0
            n_items = struct.unpack_from("<H", data, 2)[0]
            total = data[4]
            premium_start = data[5]
            premium_end = data[6]
            print(ts() + f"<- HC_ACCEPT_ENTER (0x006b) {len(data)} bytes dt={t_char:.3f}s: "
                         f"n_slots={total} premium={premium_start}-{premium_end}")
            # chars: header 4 + 1 total + 1 + 1 + 20 extension = 27 bytes, each CHARACTER_INFO 20180704 = 147 bytes
            # 147 = read from clif: 0x6b per-char size with PACKETVER 20180704
            off = 27
            chars = []
            per = 147
            while off + per <= len(data):
                gid = struct.unpack_from("<I", data, off)[0]
                exp = struct.unpack_from("<i", data, off+4)[0]
                zeny = struct.unpack_from("<i", data, off+12)[0]
                jlvl = struct.unpack_from("<i", data, off+16)[0]
                # name at off+52 (per struct CHARACTER_INFO), 24 bytes
                name = data[off+52:off+52+24].split(b"\x00")[0].decode(errors="replace")
                chars.append((gid, name, exp, zeny, jlvl))
                off += per
            print(ts() + f"   existing chars: {[(n, g) for g, n, *_ in chars] if chars else '[]'}")
            char_list = chars
            break
        elif pid == 0x06c:
            print(ts() + f"<- HC_REFUSE_ENTER (0x006c) error={data[2]}")
            sys.exit(1)
        else:
            print(ts() + f"<- (char) unexpected 0x{pid:04x} {hexdump(data)}")
    if char_list is None:
        print(ts() + "!! stalled waiting for HC_ACCEPT_ENTER (0x006b) char list")
        sys.exit(2)

    # ---------- 3. CREATE CHARACTER ----------
    exists = any(name == CHAR_NAME for _, name, *_ in char_list)
    if not exists:
        # PACKETVER >= 20151001: CH_MAKE_CHAR 0x0a39 (36 bytes):
        #   type.W name[24] slot.B hair_color.W hair_style.W job.L sex.B
        # (job 0 = JOB_NOVICE; sex 1 = M)
        p = struct.pack("<H", 0x0a39)
        p += CHAR_NAME.encode().ljust(24, b"\x00")
        p += bytes([0])                        # slot 0
        p += struct.pack("<HH", 1, 1)          # hair_color, hair_style
        p += struct.pack("<I", 0)              # job = JOB_NOVICE
        p += bytes([1])                        # sex M
        assert len(p) == 36, len(p)
        c.sendall(p)
        print(ts() + f"-> CH_MAKE_CHAR (0x0a39) sent: name={CHAR_NAME!r} slot=0 job=novice sex=M")
        pid, data = recv_packet(c, timeout=10)
        t_make = time.time() - t0
        if pid == 0x0b6f:  # HC_ACCEPT_MAKECHAR for PACKETVER >= 20201007? no: 20180704 -> 0x006d
            gid = struct.unpack_from("<I", data, 4)[0]
            print(ts() + f"<- HC_ACCEPT_MAKECHAR (0x{pid:04x}) dt={t_make:.3f}s: GID={gid}")
        elif pid == 0x006d:
            gid = struct.unpack_from("<I", data, 4)[0]
            name = data[56:56+24].split(b"\x00")[0].decode(errors="replace")
            print(ts() + f"<- HC_ACCEPT_MAKECHAR (0x006d) dt={t_make:.3f}s: GID={gid} name={name!r}")
        elif pid == 0x006e:
            print(ts() + f"<- HC_REFUSE_MAKECHAR (0x006e) reason={data[2]} (0=char slot denied, "
                         "1=too many chars, 0xFF=name taken etc.)")
            sys.exit(3)
        else:
            print(ts() + f"!! expected 0x006d/0x006e, got 0x{pid:04x} {hexdump(data)}")
            sys.exit(4)
    else:
        gid = next(g for g, n, *_ in char_list if n == CHAR_NAME)
        print(ts() + f"character {CHAR_NAME!r} already exists (GID={gid}), reusing")

    # ---------- 4. SELECT CHARACTER / MAP ENTRY ----------
    p = struct.pack("<HBB", 0x0066, 0, 0)   # CH_SELECT_CHAR, slot 0 (packet len 3: type + slot + pad)
    # rAthena packet_db: 0x0066 length 6 for >=090603? classic is 3; read handler takes slot @2
    c.sendall(struct.pack("<HBB", 0x0066, 0, 0)[:3])
    print(ts() + "-> CH_SELECT_CHAR (0x0066) slot 0 sent")

    map_ip = map_port = None
    deadline = time.time() + 10
    while time.time() < deadline:
        pid, data = recv_packet(c, timeout=3)
        if pid == 0x0071:
            cid = struct.unpack_from("<I", data, 2)[0]
            mapname = data[6:6+16].split(b"\x00")[0].decode()
            map_ip = socket.inet_ntoa(struct.pack("<I", struct.unpack_from("<I", data, 22)[0]))
            map_port = struct.unpack_from("<H", data, 26)[0]  # rAthena sends LE (ntows quirk)
            print(ts() + f"<- HC_NOTIFY_ZONESVR (0x0071) dt={time.time()-t0:.3f}s: CID={cid} map={mapname!r} {map_ip}:{map_port}")
            break
        elif pid == 0x0840:
            print(ts() + "<- HC_NOTIFY_ACCESSIBLE_MAPNAME (0x0840) (map server for start map missing?)")
            sys.exit(5)
        elif pid == 0x0081:
            print(ts() + f"<- SC_NOTIFY_BAN (0x0081) result={data[2]}")
            sys.exit(1)
        else:
            print(ts() + f"<- (char) unexpected 0x{pid:04x} {hexdump(data)}")
    if map_ip is None:
        print(ts() + "!! stalled waiting for HC_NOTIFY_ZONESVR (0x0071)")
        sys.exit(6)
    c.close()

    # ---------- 5. MAP SERVER ----------
    print(ts() + f"connecting to map-server {map_ip}:{map_port} ...")
    m = socket.create_connection((map_ip, map_port), timeout=5)
    print(ts() + "TCP connected")

    # clif_parse_WantToConnection via packet 0x0436 (>=20080910, 19 bytes):
    # AID.L @2, CID.L @6, login_id1.L @10, client_tick.L @14, sex.B @18
    p = struct.pack("<H", 0x0436)
    p += struct.pack("<I", aid)      # account_id
    p += struct.pack("<I", gid)      # char_id
    p += struct.pack("<I", login_id1)
    p += struct.pack("<I", 0x12345678)  # client tick
    p += struct.pack("<B", sex)
    assert len(p) == 19, len(p)
    m.sendall(p)
    print(ts() + "-> CH_ENTER (0x0436 WantToConnection) sent: AID/CID/login_id1/tick/sex")

    # server sends 0x0283 (AID echo) after accepting, then ZC_ACCEPT_ENTER 0x0073 after chrif auth
    got_283 = got_73 = False
    chat_seen = []
    motd_seen = False
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            pid, data = recv_packet(m, timeout=2)
        except (socket.timeout, TimeoutError):
            if got_73:
                break  # enough silence-watching after map entry
            continue
        if pid == 0x0283 and not got_283:
            srv_id = struct.unpack_from("<I", data, 2)[0]
            print(ts() + f"<- 0x0283 account id registration: {srv_id}")
            got_283 = True
        elif pid == 0x0073:
            start_time = struct.unpack_from("<I", data, 2)[0]
            print(ts() + f"<- ZC_ACCEPT_ENTER (0x0073) dt={time.time()-t0:.3f}s: start_time={start_time} posDir={data[6:9].hex()}  *** MAP ENTRY OK ***")
            got_73 = True
            # immediately send map-load-complete (CZ_NOTIFY_ACTORINIT) so server spawns us
            m.sendall(struct.pack("<HH", 0x007d, 2))  # clif_parse_LoadEndAck
            print(ts() + "-> 0x007d LoadEndAck (map load complete) sent")
        elif pid == 0x007f:
            print(ts() + f"<- ZC_NOTIFY_TIME (0x007f): {struct.unpack_from('<I', data, 2)[0]}")
        elif pid == 0x0091 or pid == 0x0092:
            print(ts() + f"<- 0x{pid:04x} map change/load packet")
        elif pid == 0x008e:
            msg = data[8:].split(b"\x00")[0].decode(errors="replace")
            print(ts() + f"<- ZC_NOTIFY_UPDATECHAT (0x008e): {msg!r}")
            chat_seen.append(("8e", msg))
        elif pid == 0x008d:
            who = struct.unpack_from("<I", data, 4)[0]
            msg = data[8:].split(b"\x00")[0].decode(errors="replace")
            print(ts() + f"<- ZC_NOTIFY_CHAT (0x008d) gid={who}: {msg!r}")
            chat_seen.append(("8d", msg))
        elif pid == 0x009a:
            msg = data[4:].split(b"\x00")[0].decode(errors="replace")
            print(ts() + f"<- ZC_BROADCAST (0x009a): {msg!r}")
            motd_seen = True
        elif pid == 0x01c3:
            msg = data[16:].split(b"\x00")[0].decode(errors="replace")
            print(ts() + f"<- ZC_BROADCAST2 (0x01c3): {msg!r}")
            motd_seen = True
        elif pid == 0x0081:
            print(ts() + f"<- SC_NOTIFY_BAN (0x0081) result={data[2]} — auth refused by map-server")
            sys.exit(7)
        elif pid == 0x0074:
            print(ts() + f"<- ZC_REFUSE_ENTER (0x0074) error={data[2]}")
            sys.exit(8)
        else:
            # world packets (inventory, stats, spawn...) — count silently
            chat_seen.append((f"{pid:04x}", f"<{len(data)} bytes>"))
    t_end = time.time() - t0

    # ---------- verdict ----------
    print()
    print(ts() + "=== SUMMARY ===")
    print(f"login ok:            AC_ACCEPT_LOGIN received")
    print(f"char list ok:        HC_ACCEPT_ENTER received")
    print(f"char create ok:      {'HC_ACCEPT_MAKECHAR (created)' if not exists else 'reused existing'}")
    print(f"map entry ok:        {'ZC_ACCEPT_ENTER (0x0073) received' if got_73 else 'NO — stalled'}")
    print(f"packets after entry: {len(chat_seen)} non-keepalive packets seen")
    print(f"MOTD/broadcast seen: {motd_seen}")
    print(f"total elapsed:       {t_end:.3f}s")
    sys.exit(0 if got_73 else 9)

if __name__ == "__main__":
    main()
