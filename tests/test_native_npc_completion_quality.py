"""Offline completion gate: unchanged thresholds, no native effects."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_received_metadata_runtime_meets_existing_complexity_gate() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "xenon",
            "--max-absolute",
            "B",
            "--max-modules",
            "B",
            "--max-average",
            "A",
            str(ROOT / "src/robots/app/playing_runtime.py"),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
