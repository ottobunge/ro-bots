"""Pinned-public asset closure, not a replacement for rAthena's native parsers."""

import hashlib
import json
import re
import struct
import subprocess  # nosec B404
import zlib
from pathlib import Path

import yaml

from robots.adapters.rathena_runtime_io import read_path, reject

SOURCE = Path("/nix/store/9fnslka6gqn93qwrwzvj07i929fmhv68-source")
PACKAGE = Path("/nix/store/bnacwjisnzz146j80sdha606j3j96ipc-rathena-server-20180704-e985006171d2")
SOURCE_NAR = "sha256-ppi6wPYDqwXh+XR39ufl0SDS6gYfdKyHtQ9tU9rgrNI="
PACKAGE_NAR = "sha256-j/yjHMH+WB16iaKl1GEnNpzqfu+EKSgcvPP0NnsrjhA="
REVISION = "e985006171d2eb320ee512a653f4c83aea3d81b6"


def attest() -> None:
    for path, expected in ((SOURCE, SOURCE_NAR), (PACKAGE, PACKAGE_NAR)):
        # Only the fixed public-artifact Nix hash command is executed, never a server.
        result = subprocess.run(  # nosec B603, B607
            ["nix", "hash", "path", str(path)], check=False, capture_output=True, timeout=60
        )
        if result.returncode or result.stdout.decode("ascii").strip() != expected:
            reject("pinned public artifact attestation failed")
    profile = json.loads(read_path(PACKAGE / "share/rathena/build-evidence/profile.json"))
    if profile != {
        "packetver": 20180704,
        "main": 20180704,
        "renewal": False,
        "re": False,
        "zero": False,
        "obfuscation": False,
        "pincode": True,
    }:
        reject("unsupported compiled profile")


def reference(value: str) -> str:
    if not re.fullmatch(r"(?:conf|npc|db)/[A-Za-z0-9_./@-]+", value):
        reject("unsupported asset reference")
    if any(p in ("", ".", "..") for p in value.split("/")):
        reject("outside-source asset reference")
    return value


def optional_template(path: str) -> bool:
    candidates = (
        path.replace("conf/import/", "conf/import-tmpl/"),
        path.replace("conf/msg_conf/import/", "conf/msg_conf/import-tmpl/"),
        path.replace("db/import/", "db/import-tmpl/"),
    )
    return any(candidate != path and (SOURCE / candidate).is_file() for candidate in candidates)


def config_asset(
    path: str, assets: dict[str, bytes], omitted: set[str], visiting: set[str] | None = None
) -> None:
    visiting = set() if visiting is None else visiting
    if path in visiting:
        reject("cyclic configuration import")
    if path in assets:
        return
    visiting.add(path)
    raw = read_path(SOURCE / reference(path))
    lines: list[bytes] = []
    for line in raw.splitlines(keepends=True):
        active = line.split(b"//", 1)[0].strip()
        if active.startswith(b"import:"):
            target = reference(active.split(b":", 1)[1].strip().decode("ascii"))
            if optional_template(target):
                omitted.add(target)
                continue
            config_asset(target, assets, omitted, visiting)
        lines.append(line)
    assets[path] = b"".join(lines)
    visiting.remove(path)


def npc_closure(assets: dict[str, bytes]) -> list[str]:
    pending = ["npc/pre-re/scripts_main.conf"]
    visited: set[str] = set()
    scripts: set[str] = set()
    while pending:
        path = pending.pop()
        if path in visited:
            reject("cyclic or repeated NPC configuration import")
        visited.add(path)
        raw = read_path(SOURCE / reference(path))
        assets[path] = raw
        for original in raw.decode("utf-8").splitlines():
            line = original.split("//", 1)[0].strip()
            if not line:
                continue
            key, separator, target = line.partition(":")
            if not separator or key not in ("npc", "delnpc", "import"):
                reject("unsupported NPC import directive")
            target = reference(target.strip())
            if key == "import":
                pending.append(target)
            else:
                assets[target] = read_path(SOURCE / target)
                scripts.add(target)
    return sorted(scripts)


def yaml_footer(raw: bytes, assets: dict[str, bytes], omitted: set[str]) -> bytes:
    """Preserve body bytes; normalize only the pinned public import footer."""
    before, marker, footer = raw.partition(b"\nFooter:")
    if not marker:
        return raw
    data = yaml.safe_load(b"Footer:" + footer)
    imports = data["Footer"].get("Imports", [])
    selected: list[dict[str, object]] = []
    for entry in imports:
        if set(entry) - {"Path", "Mode", "Generator"}:
            reject("unsupported database import schema")
        target = reference(entry["Path"])
        mode = entry.get("Mode")
        if mode not in (None, "Prerenewal", "Renewal"):
            reject("unsupported database import mode")
        if mode == "Renewal" or entry.get("Generator") is True:
            omitted.add(target)
            continue
        if "Generator" in entry:
            reject("unsupported database generator import")
        if optional_template(target):
            omitted.add(target)
            continue
        if target not in assets:
            reject("missing selected database dependency")
        selected.append(entry)
    result = yaml.safe_dump({"Footer": {"Imports": selected}}, sort_keys=False).encode()
    return before + b"\n" + result


def cache_names(raw: bytes) -> set[str]:
    size, count = struct.unpack_from("<IH", raw)
    if size != len(raw):
        reject("mapcache size mismatch")
    offset = 8
    names: set[str] = set()
    for _ in range(count):
        name, width, height, length = struct.unpack_from("<12shhi", raw, offset)
        offset += 20
        if not 0 < width * height <= 512 * 512 or length <= 0:
            reject("unsupported mapcache record")
        cells = zlib.decompress(raw[offset : offset + length])
        if len(cells) != width * height:
            reject("mapcache cell length mismatch")
        names.add(name.split(b"\0", 1)[0].decode("ascii"))
        offset += length
    if offset != len(raw):
        reject("mapcache record frontier mismatch")
    return names


def map_report(assets: dict[str, bytes]) -> dict[str, object]:
    names = cache_names(assets["db/map_cache.dat"]) | cache_names(assets["db/pre-re/map_cache.dat"])
    configured = {
        line.split(b":", 1)[1].strip().decode("ascii")
        for line in assets["conf/maps_athena.conf"].splitlines()
        if line.startswith(b"map:")
    }
    missing = sorted(configured - names)
    if missing:
        reject("configured map missing from public mapcache")
    return {"mapcache_checked_maps": len(configured), "configured_maps_missing_from_cache": missing}


def database_assets(assets: dict[str, bytes], omitted: set[str]) -> None:
    for path in sorted((SOURCE / "db").rglob("*")):
        if path.is_symlink():
            reject("public asset symlink rejected")
        relative = path.relative_to(SOURCE).as_posix()
        if path.is_file() and not relative.startswith(("db/re/", "db/import-tmpl/")):
            assets[relative] = read_path(path)
    for asset_name in list(assets):
        if asset_name.endswith(".yml"):
            assets[asset_name] = yaml_footer(assets[asset_name], assets, omitted)


def configuration_assets(assets: dict[str, bytes], omitted: set[str]) -> None:
    roots = (
        "battle_athena.conf",
        "maps_athena.conf",
        "script_athena.conf",
        "packet_athena.conf",
        "channels.conf",
        "groups.yml",
        "atcommands.yml",
        "inter_server.yml",
        "motd.txt",
        "charhelp.txt",
    )
    for name in roots:
        config_asset("conf/" + name, assets, omitted)
    for path in sorted((SOURCE / "conf/msg_conf").glob("*.conf")):
        config_asset(path.relative_to(SOURCE).as_posix(), assets, omitted)
    for name in roots:
        path_name = "conf/" + name
        if name.endswith(".yml"):
            assets[path_name] = yaml_footer(assets[path_name], assets, omitted)


def public_assets() -> tuple[dict[str, bytes], dict[str, object]]:
    attest()
    assets: dict[str, bytes] = {}
    omitted: set[str] = set()
    scripts = npc_closure(assets)
    database_assets(assets, omitted)
    configuration_assets(assets, omitted)
    for role in ("login", "char", "map"):
        assets[f"bin/{role}-server"] = read_path(PACKAGE / f"libexec/rathena/{role}-server")
    assets["LICENSE"] = read_path(SOURCE / "LICENSE")
    report: dict[str, object] = {
        "npc_files": len(scripts),
        "npc_querysql_files": sum(b"query_sql" in assets[p].lower() for p in scripts),
        "removed_public_imports": sorted(omitted),
        "public_assets": {p: hashlib.sha256(raw).hexdigest() for p, raw in sorted(assets.items())},
        "parser_scope": (
            "checked selected NPC/config references and YAML import footers; "
            "not native parser acceptance"
        ),
        **map_report(assets),
    }
    return assets, report
