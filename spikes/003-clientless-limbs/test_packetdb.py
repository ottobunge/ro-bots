"""Regression tests for spike 003's stream framing (no live server)."""

from __future__ import annotations

import struct
import unittest

import packetdb


class FramingTests(unittest.TestCase):
    def test_party_config_preserves_following_packets(self):
        # PACKET_ZC_PARTY_CONFIG is packed int16 + uint8, not just the ID.
        config = bytes.fromhex("c90200")
        stat = bytes.fromhex("d9020200000000000000")
        packets, leftover = packetdb.parse_stream(config + stat)
        self.assertEqual(packets, [(0x02C9, config), (0x02D9, stat)])
        self.assertEqual(leftover, b"")

    def test_party_config_split_across_reads(self):
        packets, leftover = packetdb.parse_stream(bytes.fromhex("c902"))
        self.assertEqual(packets, [])
        self.assertEqual(leftover, bytes.fromhex("c902"))
        packets, leftover = packetdb.parse_stream(leftover + b"\x00")
        self.assertEqual(packets, [(0x02C9, bytes.fromhex("c90200"))])
        self.assertEqual(leftover, b"")

    def test_pin_status_packet_preserves_next_frame(self):
        pin_status = struct.pack("<HIIH", 0x08B9, 12345, 2000000, 0)
        config = bytes.fromhex("da0200")
        stat = bytes.fromhex("d9020200000000000000")
        packets, leftover = packetdb.parse_stream(pin_status + config + stat)
        self.assertEqual(packets, [(0x08B9, pin_status), (0x02DA, config), (0x02D9, stat)])
        self.assertEqual(leftover, b"")

    def test_attack_range_preserves_next_frame(self):
        attack_range = bytes.fromhex("3a010100")
        stat = bytes.fromhex("b000060028000000")
        packets, leftover = packetdb.parse_stream(attack_range + stat)
        self.assertEqual(packets, [(0x013A, attack_range), (0x00B0, stat)])
        self.assertEqual(leftover, b"")

    def test_unknown_id_fails_instead_of_consuming_two_bytes(self):
        with self.assertRaisesRegex(ValueError, "unknown packet 0xffff"):
            packetdb.parse_stream(bytes.fromhex("ffff1234"))

    def test_walking_destination_uses_rbufpos2(self):
        from client import BotClient

        raw = bytearray(110)
        struct.pack_into("<HHBII", raw, 0, 0x09FD, 110, 0, 2000000, 150000)
        # Packed per rAthena clif.cpp WBUFPOS2, not two independent PosDir values.
        x0, y0, x1, y1 = 165, 145, 168, 145
        raw[63:69] = bytes(
            [
                x0 >> 2,
                ((x0 << 6) | ((y0 >> 4) & 0x3F)) & 0xFF,
                ((y0 << 4) | ((x1 >> 6) & 0x0F)) & 0xFF,
                ((x1 << 2) | ((y1 >> 8) & 0x03)) & 0xFF,
                y1 & 0xFF,
                0,
            ]
        )
        # Native MAIN 20180704 name@86/sizeof=110, independently compiled
        # from the pinned unaltered struct in test_protocol_rereview_repairs.
        raw[86:110] = b"SpikeBot01".ljust(24, b"\x00")
        actor = BotClient._parse_actor_entry(0x09FD, bytes(raw))
        assert actor is not None
        self.assertEqual((actor["x"], actor["y"]), (x1, y1))
        self.assertEqual(actor["from"], (x0, y0))
        self.assertEqual(actor["name"], "SpikeBot01")

    def test_action_damage_packet_layout(self):
        action = bytes.fromhex(
            "c80880841e0000000000000000000000000000000000000000000000000300000000"
        )
        self.assertEqual(len(action), 34)
        self.assertEqual(struct.unpack_from("<I", action, 2)[0], 2000000)
        self.assertEqual(action[29], 3)
        packets, leftover = packetdb.parse_stream(action)
        self.assertEqual(packets, [(0x08C8, action)])
        self.assertEqual(leftover, b"")

    def test_charinfo_per_page_framing_from_pinned_layout(self):
        # Pinned 20180704: HC_ACK_CHARINFO_PER_PAGE 0x099D is char-server S->C,
        # int16 type + int16 total len + N*CHARACTER_INFO(155) tail, only in
        # reply to client CH_CHARLIST_REQ 0x09A1 (common/packets.hpp:621-626
        # #else branch; char_clif.cpp:453-471). Executed pinned-include oracle:
        # .work/playing-grind-protocol-completion/evidence/oracle_pinned_layout.log
        page = struct.pack("<HH", 0x099D, 4 + 155 * 2) + bytes(155 * 2)
        notify = struct.pack("<HI", 0x09A0, 1)
        packets, leftover = packetdb.parse_stream(page + notify)
        self.assertEqual(packets, [(0x099D, page), (0x09A0, notify)])
        self.assertEqual(leftover, b"")

    def test_pinned_absent_ids_stay_unknown_denial(self):
        # Five of the six diagnostic IDs are NOT server->client packets at
        # MAIN 20180704, so unknown-ID denial stays correct for them:
        # 0x02E1 needs PACKETVER<20131223 (map/packets.hpp:1412/#else:1440,
        # packets_struct.hpp:54-55 -> damageType 0x8c8); 0x0B0B needs
        # MAIN>=20181002 (packets_struct.hpp:1235-1244); 0x0B1B needs
        # MAIN>=20190403 (packets_struct.hpp:4028-4033); 0x0B72 needs
        # MAIN>=20201007 || RE>=20211103 (common/packets.hpp:614-620);
        # 0x09A1 is the C->S CH_CHARLIST_REQ (common/packets.hpp:638-641,
        # parse-only registration char_clif.cpp:1608): the server never emits
        # it. Oracle guards_active 0x0b0b=0 0x0b1b=0 0x0b72=0.
        for pid in (0x02E1, 0x09A1, 0x0B0B, 0x0B1B, 0x0B72):
            with self.assertRaisesRegex(ValueError, f"unknown packet 0x{pid:04x}"):
                packetdb.parse_stream(struct.pack("<HH", pid, 4))


if __name__ == "__main__":
    unittest.main()


class PartyInviteTests(unittest.TestCase):
    def test_party_invite_2c4_is_registered_and_packs_padded_name(self):
        """MAIN 20180704 invite-by-name = CZ_PARTY_JOIN_REQ 0x2c4, 26B
        (packets.hpp:1368-1373). The w84-era 0x086d id was unregistered on
        the pinned server and the invite was silently dropped (0 parties
        across legs 4/5)."""
        name = b"RinceNyan".ljust(24, b"\x00")
        pkt = packetdb.pack(0x2C4, name)
        self.assertEqual(pkt[:2], b"\xc4\x02")
        self.assertEqual(pkt[2:11], b"RinceNyan")
        self.assertEqual(len(pkt), 26)
        self.assertIn(0x2C4, packetdb.PACKET_DB)
        self.assertEqual(packetdb.PACKET_DB[0x2C4], 26)
