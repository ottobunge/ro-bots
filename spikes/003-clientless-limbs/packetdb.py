#!/usr/bin/env python3
"""
Spike 003-clientless-limbs: inherited packet snapshot with native corrections.

RECOVERY SCOPE
==============
The embedded numeric table was originally derived for 20211103 RE. The native
server actually builds with PACKETVER=20180704 MAIN/pre-re (config.log). Explicit
overrides below correct the packet families exercised by the four-limb test;
this is not an exhaustive regeneration. Numeric registrations alone exclude
struct-only S->C packets and final clif_shuffle.hpp mappings. Unknown receive IDs
now fail rather than inventing a two-byte frame. See README.md for live evidence.

HISTORICAL SNAPSHOT PROVENANCE
==============================
The following notes describe the original snapshot derivation, not full native
protocol validation. Use the pinned rAthena source in ../rathena/:

  * src/map/clif_packetdb.hpp           - the `packet(id, len)` /
                                          `parseable_packet(id, len, func, ...)`
                                          registrations, wrapped in
                                          `#if PACKETVER >= YYYYMMDD` blocks
                                          (later registrations override earlier
                                          ones: packetdb_addpacket() just
                                          overwrites packet_db[cmd], see
                                          src/map/clif.cpp:25808).
  * src/common/packets.hpp              - DEFINE_PACKET_HEADER(name, id) +
                                          `sizeof(struct PACKET_X)` struct
                                          definitions (CHARACTER_INFO etc.),
                                          version-gated field by field.
  * src/map/packets.hpp                 - map-server DEFINE_PACKET_HEADER +
                                          struct definitions.
  * src/map/packets_struct.hpp          - the `enum packet_headers` aliases
                                          (spawn_unitType, authokType, ...)
                                          with their own PACKETVER gates, used
                                          for server->client packets that are
                                          only registered by sizeof().
  * src/common/mmo.hpp                  - NAME_LENGTH=24, MAP_NAME_LENGTH_EXT=16.

The historical scripts/gen_packetdb.py entrypoint is retired fail-closed.
Use derive_table()/self_test() in this module for strict MAIN 20180704 numeric
derivation. Struct-only lengths require independent compiler evidence; no
numeric generator is an exhaustive native layout oracle.

VARIABLE-LENGTH packets carry -1 in rAthena's table: the 2 bytes at offset 2
after the id are the TOTAL packet length (id + length + payload), exactly like
doc/packet_struct_notation.txt's "<packet len>.W" convention.

SELF-TEST: `python3 packetdb.py` parses ../rathena/src/map/clif_packetdb.hpp
at the native MAIN date and compares numeric registrations, accounting for
three explicitly verified later overrides. The inherited snapshot remains
non-exhaustive native evidence; tests/test_packet_conditions.py additionally
checks derivation and creation sizes against the pinned C++ compiler output.
"""
import re
import struct
import sys
from pathlib import Path

# config.log CPPFLAGS: -DPACKETVER=20180704 -DPRERE. config/core.hpp plus
# custom/defines_{pre,post}.hpp were checked with g++ -E -dM under nix develop.
# config/packets.hpp:20180704 is MAIN (the RE window ends strictly before it).
# None denotes known undefined macros; "" denotes empty flag replacements,
# valid for defined() but not numeric expressions.
PACKETVER = 20180704
NATIVE_MACROS: dict[str, int | str | None] = {
    "PACKETVER": PACKETVER, "PACKETVER_MAIN_NUM": PACKETVER,
    "PACKETVER_RE": None, "PACKETVER_RE_NUM": None,
    "PACKETVER_ZERO": None, "PACKETVER_ZERO_NUM": None,
    "PRERE": 1, "RENEWAL": None,
    "PACKET_OBFUSCATION": "", "PACKET_OBFUSCATION_WARN": "",
}
RA_ROOT = Path(__file__).resolve().parents[2] / "rathena"
PACKETDB_HPP = RA_ROOT / "src" / "map" / "clif_packetdb.hpp"

# id -> length. -1 = variable (2-byte total-length word at offset 2).
# Derived by scripts/gen_packetdb.py from clif_packetdb.hpp @ PACKETVER 20211103.
PACKET_DB: dict[int, int] = {
    # ZC_STATUS_CHANGE_ACK (packets_struct.hpp:4219-4225): <stat>.W <ok>.B
    # <value>.B = 6 bytes. Missing from the derived table at this PACKETVER:
    # without it the first stat-spend ack desyncs the client stream.
    0x00BC: 6,
    # Inherited numeric snapshot, not every packet the native server can send.
    # Source-backed overrides below cover reviewed families only. parse_stream
    # rejects unknown IDs before consulting the legacy length_of helper.
    # Highlights (also in PACKET_DB_NOTES below):
    #   0x0064 CA_LOGIN 55 | 0x0065 CH_ENTER 17 | 0x0066 CH_SELECT_CHAR 3
    #   0x006B HC_ACCEPT_ENTER var (27 + N*155, LIVE) | 0x0AC5 HC_NOTIFY_ZONESVR
    #   156 fixed (LIVE) | 0x007D LoadEndAck 2 | 0x02EB ZC_ACCEPT_ENTER 13
    #   C->S: 0x0881 move 5, 0x00F3 chat var, 0x088E act 7, 0x01E8 party
    #   create 28, 0x086D invite 26, 0x02C7 reply 7, 0x0363 tick 6
    #   S->C: 0x008D chat var, 0x08C8 act/damage 34, 0x09FD/9FE/9FF entries
    #   var (LIVE 110/103/104), 0x02C5/0x02C6 party 30, 0x0AE4/0x0AE5 var
    0x0064: 55, 0x0065: 17, 0x0066: 3, 0x0067: 37, 0x0068: 46, 0x0069: -1,
    0x006A: 23, 0x006B: -1, 0x006C: 3, 0x006D: 149, 0x006E: 3, 0x006F: 2,
    0x0070: 3, 0x0071: 28, 0x0072: 22, 0x0075: -1, 0x0076: 9, 0x0077: 5,
    0x0079: 53, 0x007A: 58, 0x007B: 60, 0x007C: 44, 0x007D: 2, 0x007E: 105,
    0x0082: 2, 0x0083: 2, 0x0084: 2, 0x0085: 10, 0x0089: 11, 0x008B: 2,
    0x008C: 14, 0x008D: -1, 0x008E: -1, 0x0093: 2, 0x0094: 19, 0x0096: -1,
    0x009B: 34, 0x009E: 17, 0x009F: 20, 0x00A2: 14, 0x00A7: 9, 0x00AB: 4,
    0x00AE: -1, 0x00B0: 8, 0x00B1: 8, 0x00B2: 3, 0x00B6: 6, 0x00B8: 7, 0x00B9: 6, 0x00BA: 2,
    0x00BB: 5,
    0x00C0: 7, 0x00C1: 2, 0x00C3: 8, 0x00C6: -1, 0x00C8: -1, 0x00CA: 3, 0x00CB: 3,
    0x00CC: 6, 0x00CD: 3, 0x00CE: 2, 0x00CF: 27, 0x00D3: 2, 0x00E0: 30,
    0x00E2: 26, 0x00E3: 2, 0x00E4: 6, 0x00E5: 26, 0x00E6: 3, 0x00EA: 5,
    0x00EB: 2, 0x00ED: 2, 0x00EF: 2, 0x00F3: -1, 0x00F5: 11, 0x00F7: 17,
    0x00FB: -1, 0x00FD: 27, 0x0101: 6, 0x0102: 6, 0x0104: 79, 0x0108: -1,
    0x0109: -1, 0x0112: 4, 0x0113: 25, 0x0114: 31, 0x0115: 35, 0x0116: 17,
    0x0118: 2, 0x0119: 13, 0x011D: 2, 0x011F: 16, 0x012A: 2, 0x012E: 2,
    0x012F: -1, 0x0130: 6, 0x0138: 3, 0x013F: 26, 0x0145: 19, 0x0147: 39,
    0x0149: 9, 0x014A: 6, 0x014D: 2, 0x014F: 6, 0x0150: 110, 0x0151: 6,
    0x0152: -1, 0x0153: -1, 0x0154: -1, 0x0157: 6, 0x0158: -1, 0x015F: 42,
    0x0161: -1, 0x0164: -1, 0x0165: 30, 0x0166: -1, 0x016C: 43, 0x016E: 186,
    0x0170: 14, 0x0172: 10, 0x0175: 6, 0x0176: 106, 0x0177: -1, 0x017B: -1,
    0x017E: -1, 0x0180: 6, 0x0182: 106, 0x0183: 10, 0x0185: 34, 0x0187: 6,
    0x018A: 4, 0x018B: 4, 0x0190: 23, 0x0193: 2, 0x0196: 9, 0x0198: 8,
    0x0199: 4, 0x019A: 14, 0x019D: 6, 0x019F: 6, 0x01A1: 3, 0x01A3: 5,
    0x01A5: 26, 0x01A6: -1, 0x01A7: 4, 0x01A8: 4, 0x01A9: 6, 0x01AC: 6,
    0x01AD: -1, 0x01AF: 4, 0x01B0: 11, 0x01B1: 7, 0x01B2: -1, 0x01B5: 18,
    0x01B6: 114, 0x01B7: 6, 0x01B8: 3, 0x01BA: 26, 0x01BB: 26, 0x01BC: 26,
    0x01BD: 26, 0x01BE: 2, 0x01BF: 3, 0x01C0: 2, 0x01C1: 14, 0x01C2: 10,
    0x01C3: -1, 0x01C6: 4, 0x01C7: 2, 0x01CA: 3, 0x01CB: 9, 0x01CC: 9,
    0x01CF: 28, 0x01D0: 8, 0x01D7: 11, 0x01D8: 54, 0x01D9: 53, 0x01DA: 60,
    0x01DB: 2, 0x01DC: -1, 0x01DD: 47, 0x01DE: 33, 0x01DF: 6, 0x01E0: 30,
    0x01E1: 8, 0x01E2: 34, 0x01E3: 14, 0x01E4: 2, 0x01E5: 6, 0x01E6: 26,
    0x01E7: 2, 0x01EC: 26, 0x01ED: 2, 0x01F0: -1, 0x01F1: -1, 0x01F3: 10,
    0x01F6: 34, 0x01F8: 2, 0x01F9: 6, 0x01FA: 48, 0x01FB: 56, 0x01FC: -1,
    0x0200: 26, 0x0201: -1, 0x0202: 5, 0x0203: 10, 0x0204: 18, 0x0207: 34,
    0x0208: 14, 0x0209: 36, 0x020A: 10, 0x020D: -1, 0x020E: 32, 0x020F: 10,
    0x0210: 22, 0x0212: 26, 0x0213: 26, 0x0214: 42, 0x0216: 6, 0x021E: 6,
    0x021F: 66, 0x0220: 10, 0x0221: -1, 0x0222: 6, 0x0227: 18, 0x0228: 18,
    0x0229: 15, 0x022A: 58, 0x022B: 57, 0x022C: 65, 0x022D: 19, 0x022E: 71,
    0x022F: 5, 0x0231: 26, 0x0233: 11, 0x0234: 6, 0x023A: 4, 0x023B: 26,
    0x023C: 6, 0x023D: -1, 0x023E: 8, 0x023F: 2, 0x0240: -1, 0x0241: 6,
    0x0242: -1, 0x0243: 6, 0x0244: 6, 0x0245: 3, 0x0246: 4, 0x0247: 8,
    0x0248: -1, 0x0249: 3, 0x024A: 70, 0x024B: 4, 0x024C: 8, 0x024D: 14,
    0x024E: 6, 0x0250: 3, 0x0251: 32, 0x0252: -1, 0x0253: 3, 0x0254: 3,
    0x0255: 5, 0x0256: 5, 0x0257: 8, 0x0258: 2, 0x0259: 3, 0x025C: 4,
    0x025D: 6, 0x025E: 4, 0x025F: 6, 0x0260: 6, 0x0261: 11, 0x0262: 11,
    0x0263: 11, 0x0264: 20, 0x0265: 20, 0x0266: 30, 0x0267: 4, 0x0268: 4,
    0x0269: 4, 0x026A: 4, 0x026B: 4, 0x026C: 4, 0x026D: 4, 0x026F: 2,
    0x0270: 2, 0x0271: 40, 0x0272: 44, 0x0273: 30, 0x0274: 8, 0x0277: 84,
    0x0278: 2, 0x0279: 2, 0x027A: -1, 0x027B: 14, 0x027C: 60, 0x027D: 62,
    0x027E: -1, 0x027F: 8, 0x0280: 12, 0x0281: -1, 0x0282: 284, 0x0283: 6,
    0x0284: 14, 0x0285: 6, 0x0286: 4, 0x0287: -1, 0x0288: -1, 0x0289: 12,
    0x028B: -1, 0x028C: 46, 0x028D: 34, 0x028E: 4, 0x028F: 6, 0x0290: 4,
    0x0292: 2, 0x0293: 70, 0x0294: 10, 0x029B: 80, 0x029C: 66, 0x029D: -1,
    0x029E: 11, 0x029F: 3, 0x02A0: -1, 0x02A1: -1, 0x02A2: 8, 0x02A3: -1,
    0x02A4: -1, 0x02A5: 8, 0x02A6: -1, 0x02A7: -1, 0x02A8: 162, 0x02A9: 58,
    0x02AA: 4, 0x02AB: 36, 0x02AC: 6, 0x02AD: 8, 0x02B0: 85, 0x02B1: -1,
    0x02B2: -1, 0x02B3: 107, 0x02B4: 6, 0x02B5: -1, 0x02B7: 7, 0x02B9: 191,
    0x02BA: 11, 0x02BC: 6, 0x02BF: -1, 0x02C0: -1, 0x02C1: -1, 0x02C2: -1,
    0x02C4: 6, 0x02C5: 30, 0x02CA: 3, 0x02CB: 65, 0x02CC: 4, 0x02CD: 71,
    0x02CE: 10, 0x02CF: 6, 0x02D5: 2, 0x02D6: 6, 0x02D8: 10, 0x02D9: 10,
    0x02DB: -1, 0x02DC: -1, 0x02DD: 32, 0x02DE: 6, 0x02DF: 36, 0x02E0: 34,
    0x02E2: 20, 0x02E3: 22, 0x02E4: 11, 0x02E5: 9, 0x02E6: 6, 0x02E7: -1,
    0x02EC: 67, 0x02ED: 59, 0x02EE: 60, 0x02EF: 8, 0x02F0: 10, 0x02F1: 2,
    0x02F2: 2, 0x02F3: -1, 0x02F4: -1, 0x02F5: -1, 0x02F6: -1, 0x02F7: -1,
    0x02F8: -1, 0x02F9: -1, 0x02FA: -1, 0x02FB: -1, 0x02FC: -1, 0x02FD: -1,
    0x02FE: -1, 0x02FF: -1, 0x0300: -1, 0x0301: -1, 0x0302: -1, 0x0303: -1,
    0x0304: -1, 0x0305: -1, 0x0306: -1, 0x0307: -1, 0x0308: -1, 0x0309: -1,
    0x030A: -1, 0x030B: -1, 0x030C: -1, 0x030D: -1, 0x030E: -1, 0x030F: -1,
    0x0310: -1, 0x0311: -1, 0x0312: -1, 0x0313: -1, 0x0314: -1, 0x0315: -1,
    0x0316: -1, 0x0317: -1, 0x0318: -1, 0x0319: -1, 0x031A: -1, 0x031B: -1,
    0x031C: -1, 0x031D: -1, 0x031E: -1, 0x031F: -1, 0x0320: -1, 0x0321: -1,
    0x0322: -1, 0x0323: -1, 0x0324: -1, 0x0325: -1, 0x0326: -1, 0x0327: -1,
    0x0328: -1, 0x0329: -1, 0x032A: -1, 0x032B: -1, 0x032C: -1, 0x032D: -1,
    0x032E: -1, 0x032F: -1, 0x0330: -1, 0x0331: -1, 0x0332: -1, 0x0333: -1,
    0x0334: -1, 0x0335: -1, 0x0336: -1, 0x0337: -1, 0x0338: -1, 0x0339: -1,
    0x033A: -1, 0x033B: -1, 0x033C: -1, 0x033D: -1, 0x033E: -1, 0x033F: -1,
    0x0340: -1, 0x0341: -1, 0x0342: -1, 0x0343: -1, 0x0344: -1, 0x0345: -1,
    0x0346: -1, 0x0347: -1, 0x0348: -1, 0x0349: -1, 0x034A: -1, 0x034B: -1,
    0x034C: -1, 0x034D: -1, 0x034E: -1, 0x034F: -1, 0x0350: -1, 0x0351: -1,
    0x0352: -1, 0x0353: -1, 0x0354: -1, 0x0355: -1, 0x0356: -1, 0x0357: -1,
    0x0358: -1, 0x0359: -1, 0x035A: -1, 0x035B: -1, 0x035C: 2, 0x035D: -1,
    0x035E: 2, 0x035F: 6, 0x0360: 6, 0x0361: 5, 0x0362: 6, 0x0363: 6,
    0x0364: 6, 0x0365: 41, 0x0366: 90, 0x0367: 90, 0x0368: 6, 0x0369: 7,
    0x0389: -1, 0x040C: -1, 0x040D: -1, 0x040E: -1, 0x040F: -1, 0x0410: -1,
    0x0411: -1, 0x0412: -1, 0x0413: -1, 0x0414: -1, 0x0415: -1, 0x0416: -1,
    0x0417: -1, 0x0418: -1, 0x0419: -1, 0x041A: -1, 0x041B: -1, 0x041C: -1,
    0x041D: -1, 0x041E: -1, 0x041F: -1, 0x0420: -1, 0x0421: -1, 0x0422: -1,
    0x0423: -1, 0x0424: -1, 0x0425: -1, 0x0426: -1, 0x0427: -1, 0x0428: -1,
    0x0429: -1, 0x042A: -1, 0x042B: -1, 0x042C: -1, 0x042D: -1, 0x042E: -1,
    0x042F: -1, 0x0430: -1, 0x0431: -1, 0x0432: -1, 0x0433: -1, 0x0434: -1,
    0x0435: -1, 0x0436: 26, 0x0437: 5, 0x0438: 6, 0x0439: 8, 0x043E: -1,
    0x043F: 25, 0x0444: -1, 0x0445: 10, 0x0446: 14, 0x0447: 2, 0x0448: -1,
    0x0449: 4, 0x044A: 6, 0x07D7: 8, 0x07D8: 8, 0x07D9: 268, 0x07DA: 6,
    0x07E2: 8, 0x07E3: 6, 0x07E4: 6, 0x07E5: 8, 0x07E7: 32, 0x07E8: -1,
    0x07E9: 5, 0x07EC: 8, 0x07F5: 6, 0x07F6: 14, 0x07F7: -1, 0x07F8: -1,
    0x07F9: -1, 0x07FC: 10, 0x0802: 26, 0x0803: 4, 0x0804: 14, 0x0805: -1,
    0x0806: 2, 0x0807: 4, 0x0808: 14, 0x0809: 50, 0x080A: 18, 0x080B: 6,
    0x0810: 3, 0x0811: -1, 0x0812: 8, 0x0815: -1, 0x0817: 2, 0x0819: -1,
    0x081A: 4, 0x081B: 10, 0x081C: 10, 0x081D: 22, 0x0820: 11, 0x0835: 2,
    0x0838: 6, 0x083B: 2, 0x083C: 10, 0x0842: 6, 0x0843: 6, 0x0844: 2,
    0x0849: 16, 0x084A: 2, 0x084B: 19, 0x0856: -1, 0x0857: -1, 0x0858: -1,
    0x085A: 90, 0x085D: 18, 0x0861: 8, 0x0862: 10, 0x0863: 10, 0x0865: 6,
    0x0868: -1, 0x086A: 19, 0x086C: 8, 0x086D: 26, 0x086F: 26, 0x0870: -1,
    0x0871: 5, 0x0874: 8, 0x0879: 41, 0x0881: 5, 0x0884: 6, 0x0885: 5,
    0x0886: 2, 0x0887: 6, 0x0888: 19, 0x0889: 90, 0x088A: 6, 0x088B: 2,
    0x088D: 26, 0x088E: 7, 0x0890: 5, 0x0891: 6, 0x0893: 8, 0x0897: 5,
    0x0898: 6, 0x089B: 10, 0x089C: 26, 0x089E: 6, 0x089F: 6, 0x08A0: 8,
    0x08A1: 6, 0x08A5: 18, 0x08A6: 8, 0x08A8: 36, 0x08AA: 7, 0x08AB: -1,
    0x08AC: 8, 0x08AD: 90, 0x08B3: -1, 0x08C7: 20, 0x08C9: 2, 0x08D2: 10,
    0x08D7: 28, 0x08D8: 27, 0x08D9: 30, 0x08DA: 26, 0x08DB: 27, 0x08DC: 26,
    0x08DD: 27, 0x08DE: 27, 0x08DF: 50, 0x08E0: 51, 0x08E1: 51, 0x08E3: 149,
    0x08E5: 41, 0x08E6: 4, 0x08E7: 10, 0x08E8: -1, 0x08E9: 2, 0x08EA: 4,
    0x08EB: 39, 0x08EC: 73, 0x08ED: 43, 0x08EE: 6, 0x08EF: 6, 0x08F0: 6,
    0x08F1: 6, 0x08F2: 36, 0x08F3: -1, 0x08F4: 6, 0x08F5: -1, 0x08F6: 22,
    0x08F7: 3, 0x08F8: 7, 0x08F9: 6, 0x08FA: 6, 0x08FB: 6, 0x08FE: -1,
    0x090A: 26, 0x090F: -1, 0x0914: -1, 0x0915: -1, 0x091C: 26, 0x091D: 41,
    0x0922: -1, 0x0929: 26, 0x0933: 6, 0x0938: -1, 0x093B: 8, 0x093F: 5,
    0x0945: -1, 0x0947: 36, 0x094A: 6, 0x094B: 19, 0x094C: 6, 0x094E: -1,
    0x0953: 5, 0x0959: 10, 0x0960: 5, 0x0961: 36, 0x0963: 8, 0x096A: 6,
    0x0974: 2, 0x0977: 14, 0x0978: 6, 0x0979: 50, 0x097A: -1, 0x097F: -1,
    0x0980: 7, 0x0983: 29, 0x098D: -1, 0x099B: 8, 0x099F: 22, 0x09AF: 4,
    0x09B1: 4, 0x09B4: 6, 0x09BC: 6, 0x09C3: 8, 0x09CA: 23, 0x09CE: 102,
    0x09D1: 14, 0x09D4: 2, 0x09D7: -1, 0x09D8: 2, 0x09DB: -1, 0x09DC: -1,
    0x09DD: -1, 0x09E6: 22, 0x09E7: 3, 0x09E8: 11, 0x09E9: 2, 0x09EA: 11,
    0x09EC: -1, 0x09ED: 3, 0x09EE: 11, 0x09EF: 11, 0x09F0: -1, 0x09F1: 11,
    0x09F2: 12, 0x09F3: 11, 0x09F4: 12, 0x09F5: 11, 0x09F6: 11, 0x09F7: 75,
    0x09F8: -1, 0x09F9: 143, 0x09FA: -1, 0x09FB: -1, 0x09FC: 6, 0x09FD: -1,
    0x09FE: -1, 0x09FF: -1, 0x0A00: 269, 0x0A01: 3, 0x0A03: 2, 0x0A04: 6,
    0x0A06: 6, 0x0A07: 9, 0x0A08: 26, 0x0A0E: 14, 0x0A12: 27, 0x0A13: 26,
    0x0A14: 10, 0x0A19: 2, 0x0A1A: 23, 0x0A1B: 2, 0x0A1C: -1, 0x0A1D: 2,
    0x0A1E: 3, 0x0A1F: 2, 0x0A21: 3, 0x0A22: 5, 0x0A23: -1, 0x0A24: 66,
    0x0A25: 6, 0x0A26: 7, 0x0A2E: 6, 0x0A2F: 7, 0x0A32: 2, 0x0A35: 4,
    0x0A44: -1, 0x0A4A: 6, 0x0A4B: 22, 0x0A4C: 28, 0x0A51: 34, 0x0A68: 3,
    0x0A6E: -1, 0x0A77: 15, 0x0A78: 15, 0x0A7D: -1, 0x0A97: 8, 0x0A98: 10,
    0x0A99: 4, 0x0A9A: 10, 0x0A9B: -1, 0x0A9C: 2, 0x0A9D: 4, 0x0AA5: -1,
    0x0AC0: 26, 0x0AC1: 26, 0x0ACC: 18, 0x0ACE: 4, 0x0ADD: 22, 0x0ADE: 6,
    0x0AE8: 2, 0x0AEF: 2, 0x0AF0: 10, 0x0AF4: 11, 0x0B4C: 2, 0x0B93: 12,
}
# sizeof-registered ids (literal lengths not present in clif_packetdb.hpp):
PACKET_DB.update({
    0x006D: 149,   # HC_ACCEPT_MAKECHAR legacy id (superseded by 0x0B6F)
    0x00FC: 6,     # CZ_REQ_JOIN_GROUP (legacy invite)
    0x00FF: 10,    # CZ_JOIN_GROUP (legacy reply)
    0x01E8: 28,    # CZ_PARTY_CREATE2 (name[24] + 2 bytes)
    # 0x02C4 omitted: DropItem remap wins at this PACKETVER (invite = 0x086D)
    0x02C7: 7,     # CZ_PARTY_JOIN_REQ_ACK (reply: party_id.L flag.B)
})
# Live-verified overrides (see README "Packet-id table"):
PACKET_DB.update({
    0x0AC5: 156,   # HC_NOTIFY_ZONESVR: NO len word, 156B total (LIVE)
    0x009A: -1,    # ZC_BROADCAST (sent via sizeof; struct has len.W msg[])
})

# Cross-server + sizeof()-sent S->C packets. clif_packetdb.hpp only covers the
# MAP server's registrations; login/char server packets and map S->C packets
# sent via clif_send(&struct, sizeof(struct)) never appear there, yet the recv
# parser needs their on-wire lengths. Sizes derived from the structs in
# src/common/packets.hpp / src/map/packets.hpp at PACKETVER 20211103:
PACKET_DB.update({
    # ---- login-server S->C ----
    0x0AC4: -1,     # AC_ACCEPT_LOGIN (>=20170315): len word @2 (LIVE 224B)
    0x006A: 23,     # AC_REFUSE_LOGIN (already in derived table)
    0x0081: 3,      # SC_NOTIFY_BAN: type(2) result(1)
    # ---- char-server S->C ----
    0x082D: 29,     # HC_ACCEPT_ENTER2: 2+2+1+4+1+1+2+16 (LIVE)
    0x020D: -1,     # HC_BLOCK_CHARACTER: len word + 24B/entry (empty here)
    0x09A0: 6,      # HC_CHARLIST_NOTIFY: type(2) pageNum(4)
    # Pinned common/packets.hpp:621-626 (#else branch @20180704): int16
    # packetType + int16 packetLength + CHARACTER_INFO(155)[] tail. Sent only
    # in reply to client CH_CHARLIST_REQ 0x09A1 (char_clif.cpp:893-898),
    # twice when exactly 3 chars. Executed pinned-include oracle
    # (.work/playing-grind-protocol-completion/evidence/oracle_pinned_layout.log):
    # HEADER=0x099d, base sizeof=4, len word @2. 0x0B72 needs MAIN>=20201007.
    0x099D: -1,     # HC_ACK_CHARINFO_PER_PAGE: len word @2, 155B/char entry
    0x0B6F: 175,    # HC_ACCEPT_MAKECHAR: 2 + CHARACTER_INFO(173 @20211103 RE)
    0x0840: -1,     # HC_NOTIFY_ACCESSIBLE_MAPNAME: len word + entries
    0x08B8: 10,     # CH_SECOND_PASSWD_ACK: pinned packed int16 + uint32 AID + char[4]
    0x08B9: 12,     # HC_SECOND_PASSWD_LOGIN: int16 + uint32 seed/AID + uint16 result
    # ---- map-server S->C sent via clif_send(&p, sizeof(p)) ----
    0x02EB: 13,     # ZC_ACCEPT_ENTER2: type(2) start(4) posDir(3) xSize ySize font(2) (LIVE)
    0x0074: 3,      # ZC_REFUSE_ENTER: type(2) error(1)
    # Pinned MAIN/pre-re20180704 packets.hpp:2007-2011, clif.cpp:11187-11195.
    # Executed packed C++ oracle: header 0x007F, sizeof 6, uint32 time@2.
    0x007F: 6,      # ZC_NOTIFY_TIME: server clock reply, not position/readiness
    # Pinned packets_struct.hpp:3586-3602 / clif.cpp:9987-10082.
    # Unaltered guarded C++ oracle MAIN/pre-re20180704: NAME_LENGTH=24,
    # packed sizeof=58; gid@2, groupId@6, name@10, title@34.
    0x0ADF: 58,     # ZC_ACK_REQNAMEALL_NPC (also ordinary monster name replies)
    0x0088: 10,     # ZC_STOPMOVE: pinned packed int16 + uint32 AID + uint16 x/y
    0x0080: 7,      # ZC_NOTIFY_VANISH: type(2) gid(4) type(1)
    0x0091: 22,     # ZC_NPCACK_MAPMOVE: type(2) map(16) x(2) y(2)
    0x0092: 28,     # ZC_NPCACK_SERVERMOVE (classic id): ...+ip(4)+port(2)
    0x0AC7: 156,    # ZC_NPCACK_SERVERMOVE_DOMAIN: 0x92 + domain(128)
    0x08C8: 34,     # ZC_NOTIFY_ACT3: ...+damage2(4) (LIVE; sit/stand use it)
    0x02C6: 30,     # ZC_PARTY_JOIN_REQ: type(2) party_id(4) name(24)
    0x00FA: 3,      # ZC_ACK_MAKE_GROUP: type(2) result(1)
    0x0AE4: 89,     # ZC_ADD_MEMBER_TO_GROUP @>=20171207: 2+4+4+4+2+2+2+2+1+24+24+16+1+1
    0x0AE5: -1,     # ZC_GROUP_LIST: len word @2, members 54B each
    0x02C9: 3,      # PACKET_ZC_PARTY_CONFIG: packed int16 + uint8
    0x02DA: 3,      # PACKET_ZC_CONFIG_NOTIFY: packed int16 + uint8
    0x013A: 4,      # PACKET_ZC_ATTACK_RANGE: packed int16 + int16
    0x0141: 14,     # PACKET_ZC_COUPLESTATUS: int16 + uint32 + int32 + int32
    0x0A0D: -1,     # 20180704 inventorylistequipType: total-length word at 2
    0x080E: 14,     # PACKET_ZC_NOTIFY_HP_TO_GROUPM: int16 + uint32 + int + int
    0x0100: 2,      # PACKET_CZ_REQ_LEAVE_GROUP: just int16 packetType
    0x0105: struct.calcsize("<Hi24sb"),  # ZC_DELETE_MEMBER_FROM_GROUP
    0x010F: -1,     # PACKET_ZC_SKILLINFO_LIST: int16 + int16 length + skills[]
    0x0ACB: struct.calcsize("<HHq"),  # PACKET_ZC_LONGLONGPAR_CHANGE
    0x00BD: struct.calcsize("<HH12B14h"),  # PACKET_ZC_STATUS
    0x0110: struct.calcsize("<HHhHBB"),  # 20180704 MAIN ZC_ACK_TOUSESKILL
    0x0A30: struct.calcsize("<Hi24s24s24s24si"),  # ZC_ACK_REQNAMEALL
    0x02C5: struct.calcsize("<H24si"),  # ZC_PARTY_JOIN_REQ_ACK
    0x0107: struct.calcsize("<Hihh"),  # ZC_NOTIFY_POSITION_TO_GROUPM
    # Final clif_shuffle.hpp registrations for PACKETVER > 20180307.
    0x035F: 5,      # clif_parse_WalkToXY, position at offset 2
    0x0360: 6,      # clif_parse_TickSend (0x0363 is DropItem, NOT TickSend)
    0x0437: 7,      # clif_parse_ActionRequest: target@2, type@6
    0x0087: struct.calcsize("<HI6s"),  # ZC_NOTIFY_PLAYERMOVE
    0x0A37: 59,     # MAIN20180704 PACKET_ZC_ITEM_PICKUP_ACK (compiled packed struct)
    0x0991: -1,    # packet_itemlist_normal: header4 + NORMALITEM_INFO rows24
    0x00A1: 6,     # PACKET_ZC_ITEM_DISAPPEAR: int16 + uint32 itemAid
    0x0148: 8,     # PACKET_ZC_RESURRECTION: int16 + uint32 gid + int16 type
    0x00AF: 6,     # PACKET_ZC_ITEM_THROW_ACK: int16 + uint16 index/count
    0x0111: 39,     # ZC_ADD_SKILL: audited MAIN20180704 fixed sizeof
    0x0139: 16,     # ZC_ATTACK_FAILURE_FOR_DISTANCE: audited MAIN20180704 fixed sizeof
    0x0AB2: 7,     # ZC_GROUP_ISALIVE: audited MAIN20180704 fixed sizeof
    0x009D: 17,     # ZC_ITEM_ENTRY: audited MAIN20180704 fixed sizeof
    0x02B8: 22,     # ZC_ITEM_PICKUP_PARTY: audited MAIN20180704 fixed sizeof
    0x0117: 18,     # ZC_NOTIFY_GROUNDSKILL: audited MAIN20180704 fixed sizeof
    0x0ABD: 10,     # ZC_NOTIFY_MEMBERINFO_TO_GROUPM: audited MAIN20180704 fixed sizeof
    0x0441: 4,     # ZC_SKILLINFO_DELETE: audited MAIN20180704 fixed sizeof
    0x010E: 11,     # ZC_SKILLINFO_UPDATE: audited MAIN20180704 fixed sizeof
    0x07E1: 15,     # ZC_SKILLINFO_UPDATE2: audited MAIN20180704 fixed sizeof
    0x0120: 6,     # ZC_SKILL_DISAPPEAR: audited MAIN20180704 fixed sizeof
    0x043D: 8,     # ZC_SKILL_POSTDELAY: audited MAIN20180704 fixed sizeof
    0x07FB: 25,     # ZC_USESKILL_ACK: audited MAIN20180704 fixed sizeof
    0x09CB: 17,     # ZC_USE_SKILL: audited MAIN20180704 fixed sizeof
    0x07FA: 8,     # PACKET_ZC_DELETE_ITEM_FROM_BODY: includes int16 deleteType
})
# Native char creation: compiler-verified against src/common/packets.hpp
# with config.log CPPFLAGS (-DPACKETVER=20180704 -DPRERE). CHARACTER_INFO is
# 155 bytes, so HC_ACCEPT_MAKECHAR is 2+155, not the inherited 149-byte entry.
# This MAIN profile uses 0x006D; 0x0B6F belongs to later profiles.
PACKET_DB.update({
    0x0A39: 36,    # CH_MAKE_CHAR: <H24sBHHIB
    0x006D: 157,   # HC_ACCEPT_MAKECHAR: int16 + CHARACTER_INFO
    0x006E: 3,     # HC_REFUSE_MAKECHAR: int16 + uint8 error
})


# Native MAIN 20180704/pre-renewal compiled sizes, not historical RE sizes.
# Independently compiled unaltered struct excerpts in
# tests/test_protocol_rereview_repairs.py. Metadata only: parse_stream still
# honors the on-wire variable length. CHARACTER_INFO=155, name@88, CharNum@118.
ACTOR_ENTRY_LEN = {0x09FD: 110, 0x09FE: 103, 0x09FF: 104}

# names for log output
NAMES: dict[int, str] = {
    0x0064: "CA_LOGIN", 0x0065: "CH_ENTER", 0x0066: "CH_SELECT_CHAR",
    0x0069: "AC_ACCEPT_LOGIN", 0x006A: "AC_REFUSE_LOGIN",
    0x006B: "HC_ACCEPT_ENTER", 0x006C: "HC_REFUSE_ENTER",
    0x006D: "HC_ACCEPT_MAKECHAR", 0x006E: "HC_REFUSE_MAKECHAR",
    0x0071: "HC_NOTIFY_ZONESVR", 0x0081: "SC_NOTIFY_BAN",
    0x007D: "CZ_NOTIFY_ACTORINIT", 0x007F: "ZC_NOTIFY_TIME",
    0x0080: "ZC_NOTIFY_VANISH", 0x0088: "ZC_STOPMOVE",
    0x0085: "CZ_REQUEST_MOVE(modern)", 0x008D: "ZC_NOTIFY_CHAT",
    0x008E: "ZC_NOTIFY_UPDATECHAT", 0x0096: "CZ_WHISPER",
    0x009A: "ZC_BROADCAST", 0x00FA: "ZC_ACK_MAKE_GROUP",
    0x0187: "PING", 0x020D: "HC_BLOCK_CHARACTER", 0x0283: "SC_NOTIFY_AUTH",
    0x01E8: "CZ_PARTY_CREATE2", 0x02C5: "ZC_PARTY_JOIN_REQ_ACK",
    0x02C6: "ZC_PARTY_JOIN_REQ", 0x02C7: "CZ_PARTY_JOIN_REQ_ACK",
    0x02C9: "ZC_PARTY_CONFIG", 0x02E1: "ZC_NOTIFY_ACT(legacy)",
    0x02EB: "ZC_ACCEPT_ENTER2", 0x0363: "CZ_DROP_ITEM",
    0x0437: "CZ_REQUEST_ACT", 0x086D: "CZ_PARTY_JOIN_REQ",
    0x035F: "CZ_REQUEST_MOVE", 0x0360: "CZ_REQUEST_TIME",
    0x0881: "CZ_REQUEST_MOVE", 0x0888: "CZ_ENTER",
    0x088E: "CZ_REQUEST_ACT", 0x08C8: "ZC_NOTIFY_ACT",
    0x082D: "HC_ACCEPT_ENTER2", 0x0840: "HC_NOTIFY_ACCESSIBLE_MAPNAME",
    0x08B8: "CH_SECOND_PASSWD_ACK",
    0x08B9: "HC_SECOND_PASSWD_LOGIN", 0x099D: "HC_ACK_CHARINFO_PER_PAGE",
    0x09A0: "HC_CHARLIST_NOTIFY", 0x09A1: "CH_CHARLIST_REQ",
    0x09FD: "ZC_NOTIFY_MOVEENTRY", 0x09FE: "ZC_NOTIFY_NEWENTRY",
    0x09FF: "ZC_NOTIFY_STANDENTRY", 0x0AC4: "AC_ACCEPT_LOGIN(modern)",
    0x0AC5: "HC_NOTIFY_ZONESVR(modern)", 0x0AE4: "ZC_ADD_MEMBER_TO_GROUP",
    0x0AE5: "ZC_GROUP_LIST", 0x0B0B: "ZC_ACK_COUNTDOWN",
    0x0B1B: "ZC_NOTIFY_ACTORINIT", 0x0B6F: "HC_ACCEPT_MAKECHAR(modern)",
    0x0B72: "HC_ACK_CHARINFO_PER_PAGE(modern)", 0x0977: "ZC_MONSTER_HP",
    0x0983: "ZC_MSG_STATE_CHANGE3", 0x0091: "ZC_CHANGEMAP",
    0x0092: "ZC_CHANGEMAP_TELEPORT",
    0x0111: "ZC_ADD_SKILL",
    0x0139: "ZC_ATTACK_FAILURE_FOR_DISTANCE",
    0x0AB2: "ZC_GROUP_ISALIVE",
    0x009D: "ZC_ITEM_ENTRY",
    0x02B8: "ZC_ITEM_PICKUP_PARTY",
    0x0117: "ZC_NOTIFY_GROUNDSKILL",
    0x0ABD: "ZC_NOTIFY_MEMBERINFO_TO_GROUPM",
    0x0441: "ZC_SKILLINFO_DELETE",
    0x010E: "ZC_SKILLINFO_UPDATE",
    0x07E1: "ZC_SKILLINFO_UPDATE2",
    0x0120: "ZC_SKILL_DISAPPEAR",
    0x043D: "ZC_SKILL_POSTDELAY",
    0x07FB: "ZC_USESKILL_ACK",
    0x09CB: "ZC_USE_SKILL",
    0x0ADF: "ZC_ACK_REQNAMEALL_NPC",
}

VAR = -1


def length_of(pid: int) -> int:
    """Total on-wire length for packet id, or -1 if variable (len word @2)."""
    return PACKET_DB.get(pid, 2)


def is_variable(pid: int) -> bool:
    return length_of(pid) == VAR


def name_of(pid: int) -> str:
    return NAMES.get(pid, "0x%04x" % pid)


# --------------------------------------------------------------------------
# Self-test: re-derive the table straight from clif_packetdb.hpp and compare.
# --------------------------------------------------------------------------
class _ConditionParser:
    """Strict C guard subset; never executes source text or skips validation."""

    _token = re.compile(
        r"\s*(0[xX][0-9a-fA-F]+|[0-9]+|[A-Za-z_]\w*|&&|\|\||==|!=|<=|>=|\+\+|--|[()!<>+-])"
    )

    def __init__(self, source: str, macros: dict[str, int | str | None]):
        self.macros = macros
        self.tokens: list[str] = []
        self.pos = 0
        source = source.strip()
        offset = 0
        while offset < len(source):
            match = self._token.match(source, offset)
            if match is None:
                raise ValueError(f"unsupported guard syntax at {source[offset:]!r}")
            self.tokens.append(match[1])
            offset = match.end()

    def _accept(self, token: str) -> bool:
        if self.pos < len(self.tokens) and self.tokens[self.pos] == token:
            self.pos += 1
            return True
        return False

    def _require(self, token: str) -> None:
        if not self._accept(token):
            raise ValueError(f"expected {token!r} in guard")

    def _macro(self, name: str) -> int | str | None:
        if name not in self.macros:
            raise ValueError(f"unknown guard macro {name!r}")
        return self.macros[name]

    def parse(self) -> bool:
        value = self._or()
        if self.pos != len(self.tokens):
            raise ValueError(f"unexpected guard token {self.tokens[self.pos]!r}")
        return bool(value)

    def _or(self) -> int:
        value = self._and()
        while self._accept("||"):
            rhs = self._and()  # Parse both sides, including unreachable syntax.
            value = int(bool(value) or bool(rhs))
        return value

    def _and(self) -> int:
        value = self._equality()
        while self._accept("&&"):
            rhs = self._equality()
            value = int(bool(value) and bool(rhs))
        return value

    def _equality(self) -> int:
        value = self._comparison()
        while self.pos < len(self.tokens) and self.tokens[self.pos] in ("==", "!="):
            op = self.tokens[self.pos]
            self.pos += 1
            rhs = self._comparison()
            value = int(value == rhs if op == "==" else value != rhs)
        return value

    def _comparison(self) -> int:
        value = self._unary()
        while self.pos < len(self.tokens) and self.tokens[self.pos] in ("<", ">", "<=", ">="):
            op = self.tokens[self.pos]
            self.pos += 1
            rhs = self._unary()
            value = int({"<": value < rhs, ">": value > rhs,
                         "<=": value <= rhs, ">=": value >= rhs}[op])
        return value

    def _unary(self) -> int:
        if self._accept("+"):
            return self._unary()
        if self._accept("-"):
            return -self._unary()
        if self._accept("!"):
            return int(not self._unary())
        if self._accept("("):
            value = self._or()
            self._require(")")
            return value
        if self.pos == len(self.tokens):
            raise ValueError("missing guard operand")
        token = self.tokens[self.pos]
        self.pos += 1
        if token == "defined":
            parenthesized = self._accept("(")
            if self.pos == len(self.tokens):
                raise ValueError("missing macro after defined")
            name = self.tokens[self.pos]
            self.pos += 1
            if not re.fullmatch(r"[A-Za-z_]\w*", name):
                raise ValueError("defined requires a macro identifier")
            value = int(self._macro(name) is not None)
            if parenthesized:
                self._require(")")
            return value
        if re.fullmatch(r"0[xX][0-9a-fA-F]+|[0-9]+", token):
            try:
                return int(token, 16 if token.lower().startswith("0x") else
                           8 if len(token) > 1 and token.startswith("0") else 10)
            except ValueError as exc:
                raise ValueError(f"invalid C integer {token!r}") from exc
        if re.fullmatch(r"[A-Za-z_]\w*", token):
            value = self._macro(token)
            if isinstance(value, str):
                raise ValueError(f"macro {token!r} has no supported integer replacement")
            return value or 0
        raise ValueError(f"unexpected guard operand {token!r}")


def _eval_cond(cond: str, ver: int = PACKETVER,
               *, macros: dict[str, int | str | None] | None = None) -> bool:
    """Evaluate only integer, macro, comparison and C boolean expressions."""
    environment = NATIVE_MACROS.copy() if macros is None else macros.copy()
    if macros is None:
        # `ver` changes the date within the native MAIN/pre-re profile; it does
        # not silently switch executable family or ruleset.
        environment["PACKETVER"] = ver
        environment["PACKETVER_MAIN_NUM"] = ver
    return _ConditionParser(cond, environment).parse()


def derive_table(hpp_path: Path | None = None) -> dict[int, int]:
    """
    Simulate the C preprocessor over clif_packetdb.hpp for PACKETVER and
    return {id: length} with 'later registration wins' semantics (exactly
    what packetdb_addpacket() does at runtime).
    """
    path = hpp_path or PACKETDB_HPP
    if not path.exists():
        raise FileNotFoundError(f"rAthena packetdb header not found: {path}")
    source = path.read_text()
    # Replace comments with whitespace, preserving physical line numbers.
    source = re.sub(r"/\*.*?\*/|//[^\n]*",
                    lambda match: " " + "\n" * match[0].count("\n"),
                    source, flags=re.S)
    if "/*" in source or "*/" in source:
        raise ValueError(f"{path}: malformed block comment")
    lines = source.splitlines()
    macros = NATIVE_MACROS.copy()

    # [outer_active, any_previous_match, current_match, else_seen]
    stack: list[list[bool]] = []
    entries: list[tuple[int, int]] = []

    def active() -> bool:
        return not stack or (stack[-1][0] and stack[-1][2])

    for lineno, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("#"):
            directive = re.fullmatch(r"#\s*([A-Za-z_]\w*)\s*(.*)", s)
            if directive is None:
                raise ValueError(f"{path}:{lineno}: malformed directive")
            kind, argument = directive.groups()
            try:
                if kind in ("if", "ifdef", "ifndef"):
                    outer = active()
                    if kind == "if":
                        matched = _eval_cond(argument, macros=macros)
                    else:
                        if not re.fullmatch(r"[A-Za-z_]\w*", argument):
                            raise ValueError(f"#{kind} requires one macro name")
                        # Explicit existence checks may introduce an undefined
                        # include guard; unknown numeric guard names still fail.
                        macros.setdefault(argument, None)
                        matched = macros[argument] is not None
                        if kind == "ifndef":
                            matched = not matched
                    stack.append([outer, matched, matched, False])
                elif kind == "define":
                    # Only these exact function-like registrations are part of
                    # the pinned header. Arbitrary replacement code is rejected.
                    registration_macros = {
                        "packet(cmd,length) packetdb_addpacket(cmd,length,nullptr,0)",
                        "parseable_packet(cmd,length,func,...) "
                        "packetdb_addpacket(cmd,length,func,__VA_ARGS__,0)",
                    }
                    if argument not in registration_macros:
                        definition = re.fullmatch(
                            r"([A-Za-z_]\w*)(?:\s+(0[xX][0-9a-fA-F]+|[0-9]+))?",
                            argument,
                        )
                        if definition is None:
                            raise ValueError("unsupported #define replacement")
                        name, literal = definition.groups()
                        if literal is None:
                            value: int | str = ""
                        else:
                            parser = _ConditionParser(literal, macros)
                            value = parser._unary()
                        if active():
                            macros[name] = value
                elif kind == "undef":
                    if not re.fullmatch(r"[A-Za-z_]\w*", argument):
                        raise ValueError("#undef requires one macro name")
                    if active():
                        macros[argument] = None
                elif kind == "elif":
                    if not stack or stack[-1][3]:
                        raise ValueError("#elif without #if or after #else")
                    matched = _eval_cond(argument, macros=macros)
                    stack[-1][2] = not stack[-1][1] and matched
                    stack[-1][1] = stack[-1][1] or matched
                elif kind == "else":
                    if argument or not stack or stack[-1][3]:
                        raise ValueError("malformed, unmatched or duplicate #else")
                    stack[-1][2] = not stack[-1][1]
                    stack[-1][1] = True
                    stack[-1][3] = True
                elif kind == "endif":
                    if argument or not stack:
                        raise ValueError("malformed or unmatched #endif")
                    stack.pop()
                else:
                    raise ValueError(f"unsupported directive #{kind}")
            except ValueError as exc:
                raise ValueError(f"{path}:{lineno}: {exc}") from exc
        elif not active():
            continue
        else:
            m = re.match(r"(?:parseable_)?packet\(\s*(0[xX][0-9a-fA-F]+)\s*,\s*(-?\d+)", s)
            if m:
                entries.append((int(m.group(1), 16), int(m.group(2))))
                continue
            m = re.match(
                r"(?:parseable_)?packet\(\s*HEADER_(\w+)\s*,\s*sizeof\s*\(\s*(?:struct\s+)?PACKET_\w+\s*\)",
                s,
            )
            if m:
                # sizeof-registered packet: id/len resolved from the struct
                # headers, transcribed into PACKET_DB above (asserted by the
                # caller via EXPECTED_LEN_HEADERS)
                continue

    if stack:
        raise ValueError(f"{path}: unterminated #if block")
    table: dict[int, int] = {}
    for pid, ln in entries:  # later wins, like packetdb_addpacket()
        table[pid] = ln
    return table


# ids whose final length in PACKET_DB came from a sizeof() registration
# (header name -> our embedded value) - kept for documentation purposes only.
EXPECTED_LEN_HEADERS: dict[str, tuple[int, int]] = {
    "CZ_MAKE_GROUP2": (0x01E8, 28),
    "CZ_PARTY_JOIN_REQ_ACK": (0x02C7, 7),
    "CZ_REQ_JOIN_GROUP": (0x00FC, 6),
    "CZ_JOIN_GROUP": (0x00FF, 10),
    "CZ_PARTY_JOIN_REQ": (0x02C4, 26),  # NOTE: overridden by DropItem remap; use 0x086D
}


# (raw numeric registration, verified final native length). These are not
# blanket exclusions: both values must match, so changes in either source or
# the embedded final mapping fail self_test. Sources: common/packets.hpp for
# HC_ACCEPT_MAKECHAR; final map/clif_shuffle.hpp for move/action registrations.
_NATIVE_REGISTRATION_SHADOWS = {
    0x006D: (149, 157),
    0x035F: (6, 5),
    0x0437: (5, 7),
    # MAIN 20180704 re-registers 0x2c4 as CZ_PARTY_JOIN_REQ (26B, invite by
    # name -> clif_parse_PartyInvite2); the inherited snapshot carried the
    # older-era 6B entry. Live-verified: the dealer invite went out and the
    # members' accept path (0x2c7) is the registered reply.
    0x2C4: (6, 26),
    # the guild invite-by-account: the derived 2B stub vs the 20180704 parse
    # registration (14B); live-verified.
    0x0168: (2, 14),
}


def self_test(verbose: bool = True) -> bool:
    """Check numeric derivation plus explicit, verified native overrides."""
    derived = derive_table()
    ok = True
    for pid, ln in sorted(derived.items()):
        ours = PACKET_DB.get(pid)
        if ours is None:
            # unknown packet: fine as long as it's not one we rely on
            continue
        if pid in _NATIVE_REGISTRATION_SHADOWS:
            expected_raw, expected_final = _NATIVE_REGISTRATION_SHADOWS[pid]
            matches = ln == expected_raw and ours == expected_final
        else:
            matches = ours == ln
        if not matches:
            ok = False
            print(f"MISMATCH 0x{pid:04x}: embedded={ours} derived={ln}")
    if verbose:
        print(f"packetdb self-test: {len(derived)} ids derived, "
              f"{len(PACKET_DB)} embedded, mismatches={0 if ok else 'see above'}")
    return ok


def pack(pid: int, payload: bytes = b"") -> bytes:
    """Build a client->server packet (fixed or variable length)."""
    if is_variable(pid):
        total = 4 + len(payload)
        return struct.pack("<HH", pid, total) + payload
    total = length_of(pid)
    if 2 + len(payload) != total:
        raise ValueError(
            f"packet 0x{pid:04x} ({name_of(pid)}): fixed length {total} "
            f"but payload gives {2 + len(payload)}"
        )
    return struct.pack("<H", pid) + payload


# Narrow source/compiler-proven NPC receive additions. Preserve all 890 prior
# entries and strict unknown rejection. See protocol/...-npc-dialogue.json.
PACKET_DB.update({0x00B4: -1, 0x00B5: 6, 0x00B7: -1,
                  0x00C4: 6, 0x0142: 6, 0x01D4: 6})


# Source/compiler-measured cut-in presentation only; no NPC/gameplay authority.
# See protocol/main-20180704-pre-re-npc-cutin.json.
PACKET_DB.update({0x01B3: 67})


# Narrow source/compiler-proven status-change receive addition. Preserve all
# prior entries and strict unknown rejection. ZC_STATUS_CHANGE 0x00BE
# (<statusID>.W <value>.B, 5B packed — packets_struct.hpp:368-373, oracle
# sizeof=5) is the SP_U* point-cost update the pinned server sends during the
# login status calc and after every stat spend (clif.cpp:3774); without it the
# reader dies mid-login-burst and the session starves. Executed pinned-include
# oracle: .work/e2e-run/evidence/oracle_zc_status_change.log
PACKET_DB.update({0x00BE: 5})


# Narrow source-proven party invite addition. Preserve all prior entries and
# strict unknown rejection. CZ_PARTY_JOIN_REQ 0x2c4 is the 20180704
# invite-by-name (packets.hpp:1368-1373: type(2) + name[24] = 26B ->
# clif_parse_PartyInvite2); the w84-era 0x086d id was unregistered and the
# invite was silently dropped (0 parties across legs 4/5).
PACKET_DB.update({0x2C4: 26})


# Guild creation ack: ZC_RESULT_MAKE_GUILD 0x0167, type(2)+result(1)=3B
# (clif.cpp:8628-8637; the result byte: 0 ok, 3 emperium missing). The
# strict framer rejected it and killed the parse loop on the first
# guild-create attempt.
PACKET_DB.update({0x0167: 3})


# Guild invite chain (20180704, packets.hpp:1302-1330): the inviter ack
# ZC_ACK_REQ_JOIN_GUILD 0x0169 (type+result, 3B), the invitee prompt
# ZC_REQ_JOIN_GUILD 0x016a (type+guild_id+guild_name[24], 30B) and the
# reply echo CZ_JOIN_GUILD 0x016b (type+guild_id+answer, 10B).
PACKET_DB.update({0x0169: 3, 0x016A: 30, 0x016B: 10})
# The invite-by-name request itself: the numeric section derives 0x0168 = 2B
# (the older-era stub), but the 20180704 parse registration is
# CZ_REQ_JOIN_GUILD (packets.hpp:1302-1308): type(2)+AID(4)+inviter_AID(4)+
# inviter_CID(4) = 14B, live-verified (the invite reached the member and the
# accept landed char.guild_id). Same shadow pattern as 0x2C4.
PACKET_DB.update({0x0168: 14})


# Narrow source-proven shop-list additions. Preserve all prior entries and
# strict unknown rejection. ZC_PC_PURCHASE_ITEMLIST 0x00C6 and
# ZC_PC_SELL_ITEMLIST 0x00C7 are length-prefixed variable packets
# (clif.cpp:2265-2280 builds packetLength = sizeof + count*row; the 2 bytes at
# offset 2 are the total length, the documented "-1" convention). Without them
# the framer strictly rejects the dealer's sell list and the shop offer never
# reaches the tracker (the w82/w83 null-offer trace: 0xC4 received, 0xC5 sent,
# 0xC7 invisible).
PACKET_DB.update({0x00C6: -1, 0x00C7: -1})


# Leg 35 (2026-10-28): the wear-equip ack. A Knife in the right hand
# makes the runtime's equip progression send CZ_REQ_WEAR_EQUIP (0x0998);
# the pinned server answers with ZC_ACK_WEAR_EQUIP_V5 0x0999
# (<index>.W <wear location>.L <view id>.W <result>.B = 11B,
# packets_struct.hpp:1269-1276, clif.cpp:4302-4328). The framer did not
# know it: parse_stream raised "unknown packet 0x0999", the rx thread
# died and all seven leg-35 agents froze on a silent transport loss.
PACKET_DB.update({0x0999: 11})


# The guild member login notice, the next frame in the same path:
# ZC_UPDATE_CHARSTAT 0x01f2 (<account id>.L <char id>.L <status>.L
# <gender>.W <hair style>.W <hair color>.W = 20B, map/packets.hpp:876-885;
# compiled sizeof=20). The server sends it to a guild's other members when
# one logs in (map/guild.cpp:1439 -> clif_guild_memberlogin_notice), so it
# arrives at any char that shares a guild - the same silent transport loss.
PACKET_DB.update({0x01F2: 20})


# The guild member position notice - the THIRD frame in the same path, and
# the one that killed the rx thread after 0x0999 and 0x01f2 were framed.
# ZC_NOTIFY_POSITION_TO_GUILDM 0x01eb (<account id>.L <x>.W <y>.W = 10B,
# map/packets.hpp:859-865; compiled sizeof=10). The server sends it to a
# guild's members when one of them moves (map/clif.cpp:3316-3335), so it
# reaches every char that shares a guild - the same silent transport loss.
PACKET_DB.update({0x01EB: 10})


def parse_stream(buf: bytes) -> tuple[list[tuple[int, bytes]], bytes]:
    """
    Split a byte stream into complete (pid, raw) packets.
    Returns (packets, leftover_bytes). Handles variable-length packets by
    reading the total-length word at offset 2.
    """
    out: list[tuple[int, bytes]] = []
    pos = 0
    n = len(buf)
    while pos + 2 <= n:
        pid = struct.unpack_from("<H", buf, pos)[0]
        if pid not in PACKET_DB:
            raise ValueError(
                f"unknown packet 0x{pid:04x} at {pos}, "
                f"preceding={[hex(p) for p, _ in out[-3:]]}, "
                f"tail={buf[pos:pos + 100].hex()}"
            )
        ln = length_of(pid)
        if ln == VAR:
            if pos + 4 > n:
                break
            ln = struct.unpack_from("<H", buf, pos + 2)[0]
            if ln < 4:
                raise ValueError(f"bad variable length {ln} for 0x{pid:04x}")
        if pos + ln > n:
            break  # incomplete packet, wait for more bytes
        out.append((pid, buf[pos:pos + ln]))
        pos += ln
    return out, buf[pos:]


if __name__ == "__main__":
    ok = self_test()
    # extra structural assertions for the lengths transcribed from structs
    assert ACTOR_ENTRY_LEN == {0x09FD: 110, 0x09FE: 103, 0x09FF: 104}
    assert length_of(0x0881) == 5 and length_of(0x088E) == 7
    assert length_of(0x0888) == 19 and length_of(0x0363) == 6
    assert length_of(0x086D) == 26 and length_of(0x02C7) == 7
    assert length_of(0x01E8) == 28 and length_of(0x007D) == 2
    assert is_variable(0x008D) and is_variable(0x008E) and is_variable(0x009A) and is_variable(0x00F3)
    assert is_variable(0x09FD) and is_variable(0x09FE) and is_variable(0x09FF)
    sys.exit(0 if ok else 1)
