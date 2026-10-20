"""Capture actual configured public source hashes before the native build."""

import hashlib
import json
from pathlib import Path

QUALIFIED_SHA256 = "ace16f15be3b60f730522d620b73a68a9f2cc384016aadce9c985888aea9a1ac"


def inventory(root: Path) -> dict[str, str]:
    files = {}
    for area in ("src", "3rdparty"):
        for path in sorted((root / area).rglob("*")):
            if path.is_symlink():
                message = "symlink in public configured source"
                raise ValueError(message)
            if path.is_file():
                files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    if files.get("src/map/clif.cpp") != QUALIFIED_SHA256:
        message = "qualified configured clif source drift"
        raise ValueError(message)
    return files


def main() -> int:
    root = Path.cwd()
    files = inventory(root)
    auxiliary = {
        "core-start.cpp": hashlib.sha256((root / "core-start.cpp").read_bytes()).hexdigest()
    }
    manifest = {
        "schema": "callback-qualified-configured-source-v1",
        "variant": "callback-qualified",
        "revision": "e985006171d2eb320ee512a653f4c83aea3d81b6",
        "files": files,
        "auxiliary": auxiliary,
        "closure_sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
    }
    (root / "configured-source.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
