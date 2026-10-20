"""Derive public SQL reference bytes only. No SQL execution or world authority."""

import hashlib
import re
import subprocess  # nosec B404
from collections import Counter
from pathlib import Path
from typing import NoReturn

SOURCE = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source")
SOURCE_NAR = "sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI="
REVISION = "e985006171d2eb320ee512a653f4c83aea3d81b6"
FILE_HASHES = {
    "main.sql": "40bafce9c3aa14dd997d911b6dd42151d4b0e7afae9273d1ba96993ffdea1c80",
    "logs.sql": "e2fab8bd57401696403746cdc7dce45330a62ca655517be655202cc4e069439c",
    "web.sql": "cdfde52db2db5250f5292ff4fd4fff08b52064be4db244ee6db2e8c35def3546",
    "roulette_default_data.sql": "1f393ee750d7b976f950c1819fd8a953a124f115bec3b0b3afae68a8a0f9d7d8",
}


def reject(message: str) -> NoReturn:
    raise ValueError(message)


def attest() -> None:
    try:
        result = subprocess.run(  # nosec B603, B607
            ["nix", "hash", "path", "--sri", str(SOURCE)],
            check=False,
            capture_output=True,
            timeout=60,
        )
    except OSError, subprocess.SubprocessError:
        message = "pinned public source attestation failed"
        raise ValueError(message) from None
    if result.returncode or result.stdout.strip() != SOURCE_NAR.encode("ascii"):
        reject("pinned public source attestation failed")


def suppress_default(raw: bytes) -> bytes:
    """Fixed line/span proof under a whole-file hash; never an arbitrary SQL filter."""
    if hashlib.sha256(raw).hexdigest() != FILE_HASHES["main.sql"]:
        reject("pinned public SQL file drift")
    lines = raw.splitlines(keepends=True)
    target = lines[798]
    columns = b"(`account_id`, `userid`, `user_pass`, `sex`, `email`)"
    valid = all(
        (
            sum(map(len, lines[:795])) == 29900,
            sum(map(len, lines[:799])) == 30138,
            all(line.startswith(b"--") for line in lines[795:797]),
            not lines[797].strip(),
            target.startswith(b"INSERT INTO `login` " + columns + b" VALUES ("),
            target.rstrip().endswith(b");"),
            target.count(b";") == 1,
            raw.count(b"INSERT INTO `login`") == 1,
        )
    )
    if not valid:
        reject("pinned default suppression proof failed")
    # Remove the adjacent public account comments too: they expose reusable defaults.
    return raw[:29900] + raw[30138:]


def derive() -> dict[str, bytes]:
    """Read only the fixed public source after actual NAR attestation."""
    attest()
    assets = {name: (SOURCE / "sql-files" / name).read_bytes() for name in FILE_HASHES}
    for name, raw in assets.items():
        if hashlib.sha256(raw).hexdigest() != FILE_HASHES[name]:
            reject("pinned public SQL file drift")
    assets["main.sql"] = suppress_default(assets["main.sql"])
    return assets


def schema_projection(raw: bytes) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Project the pinned DDL, not a general SQL parser or server acceptance test."""
    tables: list[dict[str, object]] = []
    engines: list[str] = []
    pattern = rb"^CREATE TABLE IF NOT EXISTS `([^`]+)` \(\n([^;]*?)^\) ENGINE\s*=\s*(\w+)[^;\n]*;"
    for match in re.finditer(pattern, raw, re.MULTILINE | re.DOTALL):
        columns = re.findall(rb"^\s+`([^`]+)`\s+", match[2], re.MULTILINE)
        engine = match[3].decode("ascii")
        engines.append(engine)
        tables.append(
            {
                "name": match[1].decode("ascii"),
                "engine": engine,
                "columns": [column.decode("ascii") for column in columns],
                "field_count": len(columns),
            }
        )
    return tables, dict(Counter(engines))


def reference_bundle() -> tuple[dict[str, bytes], dict[str, object]]:
    """Return attested SQL bytes and a public, non-authorizing provenance manifest."""
    assets = derive()
    files: dict[str, object] = {}
    expected = {"main.sql": 56, "logs.sql": 10, "web.sql": 4, "roulette_default_data.sql": 0}
    for name, raw in assets.items():
        tables, engines = schema_projection(raw)
        original = (SOURCE / "sql-files" / name).read_bytes()
        if schema_projection(original) != (tables, engines) or len(tables) != expected[name]:
            reject("pinned schema projection mismatch")
        files[name] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw),
            "source_sha256": FILE_HASHES[name],
            "source_size": len(original),
            "tables": tables,
            "table_count": len(tables),
            "engines": engines,
            "insert_count": len(re.findall(rb"^INSERT INTO `[^`]+`", raw, re.MULTILINE)),
        }
    manifest: dict[str, object] = {
        "version": 1,
        "scope": "public-reference-derivation-only",
        "source": str(SOURCE),
        "source_nar": SOURCE_NAR,
        "revision": REVISION,
        "attestation": "fixed nix hash path --sri, checked before reading assets",
        "sql_executed": False,
        "mutation_authorized": False,
        "server_sql_acceptance": False,
        "files": files,
        "suppression": {
            "target": "standard operational login INSERT [REDACTED]",
            "table": "login",
            "statement_count": 1,
            "source_statement_line": 799,
            "columns": ["account_id", "userid", "user_pass", "sex", "email"],
            "adjacent_comment_lines": [796, 797],
            "source_byte_span": [29900, 30138],
            "proof": "whole-file SHA256 plus exact pinned line/span/count/shape",
        },
        "limitations": [
            "Static projection only; no SQL parser or database acceptance.",
            "Upstream MyISAM/InnoDB parity retained; no rollback or conversion claim.",
            "Default server row absent; separate owned private account write/readback required.",
            "No initialization/reset/launch permission, engine route, or readiness claim.",
        ],
    }
    return assets, manifest
