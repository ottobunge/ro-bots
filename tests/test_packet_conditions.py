"""Offline regression tests for spike 003 packet preprocessor guards."""

from __future__ import annotations

import importlib.util
import re
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "packet_conditions_db", ROOT / "spikes/003-clientless-limbs/packetdb.py"
)
assert SPEC is not None
assert SPEC.loader is not None
packetdb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(packetdb)


class ConditionTests(unittest.TestCase):
    def test_malicious_guard_cannot_create_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "executed"
            expression = f"__import__('pathlib').Path({str(marker)!r}).touch()"
            with pytest.raises(ValueError, match=r"guard|macro|integer|defined"):
                packetdb._eval_cond(expression)
            assert not marker.exists()

    def test_empty_flag_definitions_are_not_numeric_truthy_values(self):
        with pytest.raises(ValueError, match=r"guard|macro|integer|defined"):
            packetdb._eval_cond("PACKET_OBFUSCATION >= 1")

    def test_signed_integer_operands(self):
        for expression in ("-1 < 0", "+1 == 1", "!-1 == 0", "(-0x10) == -020"):
            with self.subTest(expression=expression):
                assert packetdb._eval_cond(expression)

    def test_native_profile_is_main_pre_renewal(self):
        assert packetdb.PACKETVER == 20180704
        for expression in (
            "PACKETVER == 20180704",
            "PACKETVER_MAIN_NUM == PACKETVER",
            "!defined(PACKETVER_RE) && PACKETVER_RE_NUM == 0",
            "!defined PACKETVER_ZERO && PACKETVER_ZERO_NUM == 0",
            "defined(PRERE) && !defined(RENEWAL)",
            "defined(PACKET_OBFUSCATION)",
        ):
            with self.subTest(expression=expression):
                assert packetdb._eval_cond(expression)
        assert not packetdb._eval_cond("PACKETVER_RE_NUM >= 20180704")

    def test_c_boolean_precedence_and_integer_literals(self):
        cases = {
            "0 && 1 || 1": True,
            "1 || 0 && 0": True,
            "!(1 || 0)": False,
            "!0 && !!1": True,
            "0x10 == 020": True,
            "1 < 2 < 2": True,
            "2 > 1 == 1": True,
            "2 <= 1 || 3 != 3": False,
            "PACKETVER > 20180704 && PACKETVER < 20200101": False,
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                assert packetdb._eval_cond(expression) == expected

    def test_rejects_executable_and_unsupported_expressions(self):
        # Harmless payloads detect acceptance without executing side effects.
        for expression in (
            "__import__('os')",
            "len(())",
            "(1).__class__",
            "import os",
            "PACKETVER + 1",
            "PACKETVER & 1",
            "UNKNOWN_MACRO >= 1",
            "PACKETVER ??? 1",
            "",
            "1 || len(())",
            "0 && UNKNOWN_MACRO",
            "++1",
            "--1",
            "1UL",
            "defined()",
            "defined(1)",
            "True",
            "MAX_UNKNOWN > 0",
            "(1",
            "1)",
        ):
            with (
                self.subTest(expression=expression),
                pytest.raises(ValueError, match=r"guard|macro|integer|defined"),
            ):
                packetdb._eval_cond(expression)


class DirectiveTests(unittest.TestCase):
    def derive(self, source: str) -> dict[int, int]:
        with tempfile.TemporaryDirectory() as directory:
            header = Path(directory) / "packets.hpp"
            header.write_text(source)
            return cast(dict[int, int], packetdb.derive_table(header))

    def test_include_guard_definitions_comments_and_undef(self):
        table = self.derive("""
/* #if 1 -- comment must not become a directive
packet(0x1234, 99); */
# ifndef FIXTURE_HPP
# define FIXTURE_HPP
#define COUNT 2
# if defined(FIXTURE_HPP) && COUNT == 2 // inline comment
packet(0x1234, 5);
# endif /* conditional */
#undef COUNT
#ifdef COUNT
packet(0x1234, 6);
#else
packet(0x1235, 7);
#endif
#endif // include guard
#ifndef FIXTURE_HPP
packet(0x1235, 8);
#endif
""")
        assert table == {0x1234: 5, 0x1235: 7}

    def test_pinned_header_derives_numeric_lengths_for_native_profile(self):
        table = packetdb.derive_table()
        # Raw numeric registrations, BEFORE clif_shuffle.hpp final overrides.
        # Runtime PACKET_DB retains separately verified final move/action sizes.
        assert table[0x035F] == 6
        assert table[0x0437] == 5
        assert table[0x0360] == 6
        assert 0x0B93 not in table  # 2020-only branch, not native 2018.

    def test_rejects_malformed_or_unsupported_directives(self):
        for source in (
            "#else",
            "#elif 1",
            "#endif",
            "#if 1",
            "#if 1\n#else\n#else\n#endif",
            "#if 1\n#else\n#elif 1\n#endif",
            "#if 1\n#else garbage\n#endif",
            "#if 1\n#endif garbage",
            "#iffoo 1",
            "#ifdef",
            "#ifndef FOO garbage",
            "#include <other.hpp>",
            "#define DANGER(x) x",
            "#define FOO 1 + 2",
            "#undef",
            "#if 0\n#include <other.hpp>\n#endif",
            "#if 0\n#if len(())\n#endif\n#endif",
            "#if 1\n#elif UNKNOWN_MACRO\n#endif",
            "#define FOO\n#if FOO\n#endif",
            "/* unterminated\n#if 0\npacket(0x1234, 3);\n#endif",
        ):
            with (
                self.subTest(source=source),
                pytest.raises(ValueError, match=r"directive|macro|replacement|#|block comment"),
            ):
                self.derive(source)

    def test_elif_uses_current_branch_not_prior_match(self):
        table = self.derive("""
#if 1
packet(0x1234, 5);
#elif 1
packet(0x1234, 6);
#elif 0
packet(0x1234, 7);
#else
packet(0x1234, 8);
#endif
#if 0
packet(0x1235, 5);
#elif 0
packet(0x1235, 6);
#elif 1
packet(0x1235, 7);
#elif 1
packet(0x1235, 8);
#else
packet(0x1235, 9);
#endif
#if 0
#if 1
packet(0x1236, 5);
#elif 1
packet(0x1236, 6);
#endif
#else
#if 0
packet(0x1236, 7);
#else
packet(0x1236, 8);
#endif
#endif
""")
        assert table == {0x1234: 5, 0x1235: 7, 0x1236: 8}


class NativeCreationTests(unittest.TestCase):
    def test_pinned_compiler_oracle_matches_profile_sizes_and_numeric_table(self):
        # No server/network calls: use the installed compiler on pinned sources.
        config_log = (packetdb.RA_ROOT / "config.log").read_text()
        match = re.search(r"^CPPFLAGS='([^']*)'", config_log, re.M)
        assert match is not None
        flags = [flag for flag in shlex.split(match[1]) if flag.startswith("-D")]
        assert "-DPACKETVER=20180704" in flags
        assert "-DPRERE" in flags
        base = [
            "g++",
            "-x",
            "c++",
            "-std=c++17",
            *flags,
            "-I" + str(packetdb.RA_ROOT / "src"),
            "-I" + str(packetdb.RA_ROOT / "3rdparty/libconfig"),
        ]
        source = """
#include <common/packets.hpp>
#include <cstdio>
#ifdef PACKETVER_RE
#error native profile must not define PACKETVER_RE
#endif
#ifdef RENEWAL
#error native profile must not define RENEWAL
#endif
static_assert(PACKETVER_MAIN_NUM == 20180704);
int main() {
    std::printf("%d %zu %zu %d %zu %d %zu", HEADER_CH_MAKE_CHAR,
        sizeof(PACKET_CH_MAKE_CHAR), sizeof(CHARACTER_INFO),
        HEADER_HC_ACCEPT_MAKECHAR, sizeof(PACKET_HC_ACCEPT_MAKECHAR),
        HEADER_HC_REFUSE_MAKECHAR, sizeof(PACKET_HC_REFUSE_MAKECHAR));
}
"""
        with tempfile.TemporaryDirectory() as directory:
            exe = str(Path(directory) / "sizes")
            subprocess.run(
                [*base, "-o", exe, "-"],
                input=source,
                text=True,
                capture_output=True,
                check=True,
                timeout=30,
            )
            output = subprocess.run(
                [exe], text=True, capture_output=True, check=True, timeout=5
            ).stdout
        values = list(map(int, output.split()))
        assert values == [0x0A39, 36, 155, 0x006D, 157, 0x006E, 3]
        preprocessed = subprocess.run(
            [*base, "-E", "-P", "-include", "config/core.hpp", "-"],
            input="#include <map/clif_packetdb.hpp>\n",
            text=True,
            capture_output=True,
            check=True,
            timeout=30,
        ).stdout
        compiler_table = {
            int(pid, 16): int(length)
            for pid, length in re.findall(
                r"packetdb_addpacket\(\s*(0[xX][0-9a-fA-F]+)\s*,\s*(-?\d+)",
                preprocessed,
            )
        }
        assert compiler_table
        assert packetdb.derive_table() == compiler_table

    def test_native_self_test_accounts_for_verified_later_overrides(self):
        assert packetdb.self_test(verbose=False)

    def test_native_creation_packet_sizes_and_stream_framing(self):
        # g++ with config.log's -DPACKETVER=20180704 -DPRERE, pinned
        # src/common/packets.hpp: CHARACTER_INFO=155, request=36, success=157.
        assert packetdb.length_of(0x0A39) == 36
        assert packetdb.length_of(0x006D) == 157
        assert packetdb.length_of(0x006E) == 3
        request = packetdb.pack(0x0A39, bytes(34))
        assert len(request) == 36
        for pid, size in ((0x006D, 157), (0x006E, 3)):
            raw = pid.to_bytes(2, "little") + bytes(size - 2)
            following = bytes.fromhex("da0200")
            for split in (1, 2, size - 1):
                with self.subTest(pid=pid, split=split):
                    packets, tail = packetdb.parse_stream(raw[:split])
                    assert packets == []
                    assert tail == raw[:split]
                    packets, tail = packetdb.parse_stream(tail + raw[split:] + following)
                    assert packets == [(pid, raw), (0x02DA, following)]
                    assert tail == b""


if __name__ == "__main__":
    unittest.main()
