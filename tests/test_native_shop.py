"""Pure shop representation tests; synthetic bytes are not native receipts."""

import hashlib
import importlib
import json
import shlex
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from tests.test_native_npc_close_framing import packet_module
from tests.test_native_protocol_manifest import CPPFLAGS, EVIDENCE, PROFILE, SOURCE
from tests.test_native_protocol_manifest import (
    test_immutable_source_profile_sender_binding as bind_source,
)


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"\xc6\x00",
        struct.pack("<HH", 0xC6, 4),
        struct.pack("<HH", 0xC7, 15) + bytes(11),
        struct.pack("<HH", 0xC6, 14) + bytes(11),
        struct.pack("<HH", 0xC6, 15) + bytes(10),
        struct.pack("<HH", 0xC6, 15) + bytes(12),
        struct.pack("<HH", 0xC6, 16) + bytes(12),
        struct.pack("<HH", 0xC6, 15) + bytes(11),
        struct.pack("<HH", 0xC6, 719) + struct.pack("<IIBH", 1, 1, 0, 1) * 65,
    ],
)
def test_offer_rejects_malformed_or_out_of_policy(raw: bytes) -> None:
    with pytest.raises(ValueError, match=r"shop|item ID|unsigned integer|purchase|currency"):
        shop().decode_shop_offer(raw)


def test_offer_accepts_engineering_cap() -> None:
    raw = struct.pack("<HH", 0xC6, 708) + struct.pack("<IIBH", 0, 0, 0, 1) * 64
    assert len(shop().decode_shop_offer(raw).rows) == 64


def test_explicit_buy_selection_and_purchase_bytes() -> None:
    codec = shop()
    assert codec.encode_buy_selection(0xFFFFFFFF) == struct.pack("<HIB", 0xC5, 0xFFFFFFFF, 0)
    entries = (codec.PurchaseEntry(item_id=65535, quantity=65535),)
    assert codec.encode_purchase(entries) == struct.pack("<HHHH", 0xC8, 8, 65535, 65535)
    assert len(codec.encode_purchase(entries * 64)) == 260


@pytest.mark.parametrize("value", [True, False, 0, -1, 65536, 1.0, "1", None])
def test_purchase_rejects_invalid_integer_fields(value: object) -> None:
    codec = shop()
    for entry in (codec.PurchaseEntry(value, 1), codec.PurchaseEntry(1, value)):
        with pytest.raises(ValueError, match=r"shop|item ID|unsigned integer|purchase|currency"):
            codec.encode_purchase((entry,))


@pytest.mark.parametrize("value", [True, False, 0, -1, 4294967296, 1.0, "1", None])
def test_buy_selection_rejects_invalid_actor(value: object) -> None:
    with pytest.raises(ValueError, match=r"shop|item ID|unsigned integer|purchase|currency"):
        shop().encode_buy_selection(value)


def test_purchase_rejects_empty_and_above_engineering_cap() -> None:
    codec = shop()
    for entries in ((), (codec.PurchaseEntry(1, 1),) * 65):
        with pytest.raises(ValueError, match=r"shop|item ID|unsigned integer|purchase|currency"):
            codec.encode_purchase(entries)


def test_received_marker_is_opaque_and_all_result_bytes_survive() -> None:
    codec = shop()
    assert codec.decode_deal_type(struct.pack("<HI", 0xC4, 0xFFFFFFFF)).npc_id == 0xFFFFFFFF
    for value in range(256):
        result = codec.decode_purchase_result(struct.pack("<HB", 0xCA, value))
        assert result.result == value
        assert result.reports_success is (value == 0)


@pytest.mark.parametrize(
    ("decoder", "raw"),
    [
        ("decode_deal_type", b""),
        ("decode_deal_type", struct.pack("<HI", 0xC5, 1)),
        ("decode_deal_type", struct.pack("<HI", 0xC4, 1) + b"x"),
        ("decode_purchase_result", b""),
        ("decode_purchase_result", struct.pack("<HB", 0xCB, 0)),
        ("decode_purchase_result", struct.pack("<HB", 0xCA, 0) + b"x"),
    ],
)
def test_fixed_receipts_reject_wrong_header_or_geometry(decoder: str, raw: bytes) -> None:
    with pytest.raises(ValueError, match=r"shop|item ID|unsigned integer|purchase|currency"):
        getattr(shop(), decoder)(raw)


def test_currency_uses_source_emitted_b1_not_assumed_b0() -> None:
    codec = shop()
    assert codec.ReceivedCurrency().balance is None
    for balance in (-2147483648, -1, 0, 2147483647):
        received = codec.decode_currency(struct.pack("<HHi", 0xB1, 20, balance))
        assert received.balance == balance
    assert codec.decode_currency(struct.pack("<HHi", 0xB1, 5, 42)) is None
    assert codec.decode_currency(struct.pack("<HHi", 0xB0, 20, 42)) is None


@pytest.mark.parametrize("raw", [b"", b"\xb1\x00", struct.pack("<HHi", 0xB1, 20, 1) + b"x"])
def test_currency_rejects_malformed_geometry(raw: bytes) -> None:
    with pytest.raises(ValueError, match=r"shop|item ID|unsigned integer|purchase|currency"):
        shop().decode_currency(raw)


def test_inherited_stream_frames_each_receipt_and_every_split() -> None:
    wire = packet_module()
    assert len(wire.PACKET_DB) == 899
    frames = [
        struct.pack("<HI", 0xC4, 123),
        struct.pack("<HHIIBH", 0xC6, 15, 73, 61, 255, 1201),
        struct.pack("<HB", 0xCA, 255),
        struct.pack("<HHi", 0xB1, 20, 42),
    ]
    npc = struct.pack("<HI", 0xB6, 123)
    own_status = struct.pack("<HHi", 0xB0, 5, 42)
    for frame in frames:
        assert wire.parse_stream(frame) == ([(int.from_bytes(frame[:2], "little"), frame)], b"")
        neighbors = [npc, frame, own_status]
        joined = b"".join(neighbors)
        expected = [(int.from_bytes(raw[:2], "little"), raw) for raw in neighbors]
        assert wire.parse_stream(joined) == (expected, b"")
        for split in range(len(joined) + 1):
            head, pending = wire.parse_stream(joined[:split])
            tail, pending = wire.parse_stream(pending + joined[split:])
            assert head + tail == expected
            assert pending == b""
        received = []
        pending = b""
        for byte in joined:
            parsed, pending = wire.parse_stream(pending + bytes((byte,)))
            received.extend(parsed)
        assert received == expected
        assert pending == b""


def test_shop_module_has_no_nonstdlib_import_side_effects() -> None:
    root = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            (
                f"import sys; sys.path.insert(0, {root!r}); "
                "import robots.adapters.native_shop; "
                "assert 'httpx' not in sys.modules; assert 'yaml' not in sys.modules"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr


def _checked_shop_manifest(manifest: dict) -> None:
    assert manifest["profile"] == PROFILE
    assert (
        hashlib.sha256(manifest["oracle_cpp"].encode()).hexdigest()
        == "3ed4690e9277189200753c5e135ab1800cd941c82283bf87f3352c14206eda30"
    )
    assert (
        hashlib.sha256(manifest["oracle_stdout"].encode()).hexdigest()
        == "b76a60bde614af1441072fdd8e2ffaf3ff5b8ae071faff719739f974ffebb338"
    )


@pytest.mark.parametrize("field", ["packetver", "client_family", "ruleset", "obfuscation"])
def test_shop_profile_denied_before_compilation(field: str) -> None:
    manifest = json.loads(
        (
            Path(__file__).resolve().parents[1] / "protocol/main-20180704-pre-re-shop.json"
        ).read_text()
    )
    manifest["profile"][field] = "unreviewed"
    with pytest.raises(AssertionError):
        _checked_shop_manifest(manifest)


@pytest.mark.parametrize("compiler_name", ["g++", "clang++"])
def test_source_bound_fresh_full_header_shop_oracle(tmp_path: Path, compiler_name: str) -> None:
    manifest = json.loads(
        (
            Path(__file__).resolve().parents[1] / "protocol/main-20180704-pre-re-shop.json"
        ).read_text()
    )
    _checked_shop_manifest(manifest)
    bind_source()
    configured = json.loads((EVIDENCE / "configured-source.json").read_text())
    assert len(configured["files"]) == 3216
    assert len(configured["auxiliary"]) == 1
    before = {p: hashlib.sha256((SOURCE / p).read_bytes()).hexdigest() for p in configured["files"]}
    assert before == configured["files"]
    for relative, expected in configured["auxiliary"].items():
        assert hashlib.sha256((EVIDENCE / relative).read_bytes()).hexdigest() == expected
    (tmp_path / "source-before.json").write_text(json.dumps(before, sort_keys=True))
    includes = [
        SOURCE / p
        for p in (
            "src",
            "src/common",
            "3rdparty/libconfig",
            "3rdparty/rapidyaml/src",
            "3rdparty/rapidyaml/ext/c4core/src",
        )
    ]
    includes += [
        Path("/nix/store/1w8g6rvhljfk44hx50qz4sc47sm1f28v-mariadb-connector-c-3.3.5-dev/include"),
        Path(
            "/nix/store/1w8g6rvhljfk44hx50qz4sc47sm1f28v-mariadb-connector-c-3.3.5-dev/include/mysql"
        ),
    ]
    compiler = shutil.which(compiler_name)
    assert compiler is not None
    cpp = tmp_path / "shop.cpp"
    cpp.write_text(manifest["oracle_cpp"])
    binary = tmp_path / "shop.elf"
    command = [
        compiler,
        *shlex.split(CPPFLAGS),
        *["-I" + str(p) for p in includes],
        str(cpp),
        "-o",
        str(binary),
    ]
    compiled = subprocess.run(command, capture_output=True, text=True, check=False, timeout=45)
    (tmp_path / "compile.log").write_text(compiled.stdout + compiled.stderr)
    assert compiled.returncode == 0, compiled.stderr
    observed = subprocess.run([str(binary)], capture_output=True, text=True, check=True, timeout=5)
    assert observed.stdout == manifest["oracle_stdout"]
    (tmp_path / "oracle.json").write_text(
        json.dumps(
            {
                "command": command,
                "stdout": observed.stdout,
                "elf_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            }
        )
    )
    bind_source()
    after = {p: hashlib.sha256((SOURCE / p).read_bytes()).hexdigest() for p in configured["files"]}
    assert after == before
    (tmp_path / "source-after.json").write_text(json.dumps(after, sort_keys=True))


def test_currency_rejects_nonstatus_header() -> None:
    with pytest.raises(ValueError, match="currency"):
        shop().decode_currency(struct.pack("<HHi", 0xCA, 20, 42))


def test_offer_preserves_every_opaque_item_type() -> None:
    for value in range(256):
        raw = struct.pack("<HHIIBH", 0xC6, 15, 0xFFFFFFFF, 0, value, 1)
        assert shop().decode_shop_offer(raw).rows[0].item_type == value


def shop() -> ModuleType:
    return importlib.import_module("robots.adapters.native_shop")


def test_received_offer_preserves_both_prices_and_opaque_type() -> None:
    raw = struct.pack("<HHIIBH", 0xC6, 15, 123456, 98765, 255, 65535)
    offer = shop().decode_shop_offer(raw)
    assert len(offer.rows) == 1
    row = offer.rows[0]
    assert (row.price, row.discount_price, row.item_type, row.item_id) == (
        123456,
        98765,
        255,
        65535,
    )
