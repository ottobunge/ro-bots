"""Exactly four reviewed pointer corrections in the pinned clif_send_sub body."""

import hashlib
import sys
from pathlib import Path

UPSTREAM_SHA256 = "0b1db098158c240b090c6edb8417978ba495957c8a2df4cd9a0ab4cb39884ac5"
QUALIFIED_SHA256 = "ace16f15be3b60f730522d620b73a68a9f2cc384016aadce9c985888aea9a1ac"
BODY_BEFORE = "cc5199666ee7cedc35d14ad724695eacfed9cfccf525c452325b0103136758d5"
BODY_AFTER = "d85da9f09dba50ed8766ef8fc97887683a1ef10d260b424cc5e7ba3c809a4f4c"
START, END = 10749, 12589
REPLACEMENTS = (
    (b"\tblock_list *src_bl;", b"\tconst block_list *src_bl;"),
    (b"\tunsigned char *buf;", b"\tconst unsigned char *buf;"),
    (
        b"buf = va_arg(ap,unsigned char*);",
        b"buf = static_cast<const unsigned char*>(va_arg(ap,const void*));",
    ),
    (b"va_arg(ap,block_list*)", b"va_arg(ap,const block_list*)"),
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def transform(data: bytes) -> bytes:
    """Validate every input/output guard before returning any changed bytes."""
    if len(data) != 775974 or digest(data) != UPSTREAM_SHA256:
        message = "pinned clif source hash/size drift"
        raise ValueError(message)
    body = data[START:END]
    if digest(body) != BODY_BEFORE:
        message = "bounded callback body drift"
        raise ValueError(message)
    for old, new in REPLACEMENTS:
        if body.count(old) != 1:
            message = "callback unique anchor drift"
            raise ValueError(message)
        body = body.replace(old, new)
    result = data[:START] + body + data[END:]
    if digest(body) != BODY_AFTER or digest(result) != QUALIFIED_SHA256:
        message = "qualified callback output drift"
        raise ValueError(message)
    return result


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        message = "expected exactly one literal absolute public source root"
        raise ValueError(message)
    token = argv[0]
    if not token.startswith("/") or any(part in {"", ".", ".."} for part in token[1:].split("/")):
        message = "source root spelling rejected"
        raise ValueError(message)
    root = Path(token)
    target = root / "src/map/clif.cpp"
    if root.resolve() != root or target.is_symlink() or not target.is_file():
        message = "controlled regular public source required"
        raise ValueError(message)
    if target.resolve() != target:
        message = "source ancestor alias rejected"
        raise ValueError(message)
    corrected = transform(target.read_bytes())
    target.write_bytes(corrected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
