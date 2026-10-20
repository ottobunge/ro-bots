"""Read-only exact test resources and fixture offline preflight, safe summary only."""

import json
import os
import subprocess
import sys
from pathlib import Path

if sys.flags.optimize != 0:
    raise RuntimeError("optimized helper execution refused")

ROOT = Path("/home/otto/dev/ro-bots")
S = Path("/home/otto/.hermes/cache/scratch")


def run(args):
    result = subprocess.run(
        args,
        cwd=ROOT,
        env=dict(os.environ, PYTHONOPTIMIZE="0", PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True,
        timeout=35,
    )
    if result.returncode:
        raise RuntimeError("Sanitized live-preflight read-only query failed")
    return result.stdout


raw = run([sys.executable, "-B", "-m", "robots.adapters.world_inventory"])
inventory = json.loads(raw)
assert len(inventory["containers"]) == 4 and not inventory["foreign_volume_users"]
assert len({c["id"] for c in inventory["containers"]}) == 4
database = [c for c in inventory["containers"] if c["database_service"]]
assert len(database) == 1 and database[0]["database_mount"]
assert all(
    c["test_project"] and c["test_volume_mounted"] and c["state"] == "running"
    for c in inventory["containers"]
)
(S / "playing-mvp-engine-inventory.json").write_bytes(raw)
run(
    [
        sys.executable,
        "-B",
        str(
            Path(
                "/home/otto/.hermes/cache/scratch/native-observer-helper-repair2/playing-mvp-engine-preflight.py"
            )
        ),
    ]
)
projection = json.loads((S / "playing-mvp-engine-preflight.json").read_text())
deploy = json.loads(
    (ROOT / "run/reviews/playing-mvp-qualified-deployment.json").read_text()
)
assert all(
    c["image_id"] == deploy["target_image"]
    for c in projection["containers"]
    if c["service"] != "mariadb"
)
compatible = {
    "containers": [
        {
            "id": c["id"],
            "service": c["service"],
            "running": c["state"] == "running",
            "health": c["health"],
            "image": c["image_id"],
            "volume_mounts": [
                m["Destination"]
                for m in c["mounts"]
                if m["Name"] == "ro-bots-world-test"
            ],
        }
        for c in projection["containers"]
    ],
    "volume": "ro-bots-world-test",
    "exact_four_volume_users": True,
    "mutations": False,
    "no_native_connections_attempted": True,
}
(ROOT / "run/reviews/playing-mvp-fresh-engine-preflight.json").write_text(
    json.dumps(compatible, indent=2)
)
proof = json.loads(
    run(
        [
            sys.executable,
            "-B",
            str(
                Path(
                    "/home/otto/.hermes/cache/scratch/native-observer-helper-repair2/playing-mvp-readonly-baseline.py"
                )
            ),
        ]
    )
)
assert (
    proof["passed"]
    and proof["both_fixtures_offline"]
    and proof["all_online_character_count"] == 0
)
print(json.dumps(proof, indent=2))
