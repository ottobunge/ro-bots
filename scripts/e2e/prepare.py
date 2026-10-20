#!/usr/bin/env python3
"""Prepare the private isolated e2e world stage (files only; no containers).

Reuses the reviewed world-preparation pipeline (robots.adapters.world_prepare)
for every artifact that matters — the pinned runtime assets, the role confs
baked with the e2e ports 26900/26121/25121, the private bootstrap SQL and the
generated service secrets. The compose IDENTITY keys are pinned here to the
e2e contract (project ro-bots-e2e, volume ro-bots-e2e-world): the reviewed
WorldSelection validator only admits debug|test|prod|prod-NAME, so the asset
pipeline runs under the closest sanctioned identity and this script owns the
saved compose-inputs.json.

Idempotent: an existing stage whose identity matches is reported, not rebuilt.
A partial stage (interrupted preparation, no compose-inputs.json) is disposable
by contract and is removed before regenerating.
"""

from __future__ import annotations

import dataclasses
import json
import shutil
import sys
from pathlib import Path

from robots.adapters import world_prepare
from robots.adapters.world_compose import WorldSelection
from robots.adapters.world_prepare import PreparationSettings
from robots.adapters.world_prepare_cli import generated_settings

# The e2e compose identity (env.sh E2E_PROJECT/E2E_VOLUME/E2E_*_PORT).
IDENTITY = {
    "WORLD_KIND": "e2e",
    "WORLD_PROJECT": "ro-bots-e2e",
    "WORLD_VOLUME": "ro-bots-e2e-world",
    "WORLD_LOGIN_PORT": "26900",
    "WORLD_CHAR_PORT": "26121",
    "WORLD_MAP_PORT": "25121",
}
# Ports for the reviewed preparation settings (same values, int-typed keys).
PORTS = {"login_port": 26900, "char_port": 26121, "map_port": 25121}
# The reviewed pipeline's own selection: used ONLY to generate assets/confs.
# Its project/volume names are overridden by IDENTITY in compose-inputs.json.
ASSET_SELECTION_WORLD = "prod-e2e"


def compose_inputs(target: Path, settings: PreparationSettings) -> dict[str, str]:
    return IDENTITY | {
        "WORLD_DB_NAME": settings.db_name,
        "WORLD_DB_USER": settings.db_user,
        "WORLD_SCHEMA_DIR": str(target / "sql"),
        "WORLD_DB_ROOT_SECRET_FILE": str(target / "secrets/db-root"),
        "WORLD_DB_USER_SECRET_FILE": str(target / "secrets/db-user"),
    }


def verify_existing(inputs_path: Path) -> int:
    data = json.loads(inputs_path.read_text(encoding="utf-8"))
    for key, expected in IDENTITY.items():
        actual = str(data.get(key))
        if actual != expected:
            print(
                f"e2e-prepare: stage identity mismatch: {key} is {actual!r}, "
                f"expected {expected!r}",
                file=sys.stderr,
            )
            return 1
    print(f"e2e-prepare: stage already prepared at {inputs_path.parent}")
    return 0


def main(argv: list[str] | None = None) -> int:
    stage = Path(sys.argv[1] if argv is None else argv[0]).resolve()
    inputs = stage / "compose-inputs.json"
    if inputs.is_file():
        return verify_existing(inputs)
    if stage.exists():
        # Interrupted preparation leaves a partial tree; the stage is
        # git-ignored and disposable by definition (fixture.json records
        # isolated_disposable). Remove and regenerate.
        if stage.is_dir() and stage.parent.name == "e2e":
            shutil.rmtree(stage)
        else:
            print(f"e2e-prepare: refusing to remove unexpected path {stage}", file=sys.stderr)
            return 1
    settings = dataclasses.replace(generated_settings(), **PORTS)
    summary = world_prepare.create(stage, WorldSelection(ASSET_SELECTION_WORLD), settings)
    inputs.write_text(
        json.dumps(compose_inputs(stage, settings), sort_keys=True, indent=1) + "\n",
        encoding="utf-8",
    )
    inputs.chmod(0o600)
    print(
        json.dumps(
            {
                "prepared": True,
                "stage": str(stage),
                "project": IDENTITY["WORLD_PROJECT"],
                "volume": IDENTITY["WORLD_VOLUME"],
                "ports": f"{PORTS['login_port']}/{PORTS['char_port']}/{PORTS['map_port']}",
                "asset_files": summary["asset_files"],
                "npc_files": summary["npc_files"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
