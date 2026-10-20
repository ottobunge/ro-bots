"""New fixed-scenario authority; historical passive authority stays untouched."""

import hashlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path("/home/otto/dev/ro-bots")
HERE = Path(__file__).parent
AUTHORITY = ROOT / "run/reviews/npc-native-host-pilot-native-approved.json"
STATUS = "PARENT_APPROVED_FIXED_BARD_NEXT_NATIVE_HOST_PILOT"
SCENARIO = "received-Bard#brising-one-fixture-one-next"
ANCHORS = {
    (ROOT / "run/reviews/npc-host-integration-approved.json"): (
        "696afa166aa5e4217d5225ffcb50f828797370b55e27f60c32d9f79ec4ff909b"
    ),
    (ROOT / "run/reviews/npc-host-integration-independent-review.json"): (
        "a4b14111197b2e63486633bdd36093623dcb1b1d2bbec19a4164124ef9774a0e"
    ),
    (HERE.parent / "npc-host-integration-independent-freeze.json"): (
        "156860cfd8a73951b8d5d66c6636d541cf3d90166ac13ca0490d211d3b982daf"
    ),
    (ROOT / "run/reviews/npc-host-integration-combined-parent-gate.json"): (
        "f095673cbf70d8b60d43b9f06b03ec778f2552f6020d1cf90e46b3fe22c79f77"
    ),
    (ROOT / "run/reviews/playing-mvp-passive-skill-context-offline-approved.json"): (
        "457a4803e7ba03e4260cd20bc8cefcb8ab1949d7ad6770cab9e235fbf676c95a"
    ),
    (ROOT / "run/reviews/playing-mvp-native-observer-helper-repair2-approved.json"): (
        "40d4e93290f08dd162a2c6405e2eb5f9f40e97ce2cf9818913840bd8caa5f346"
    ),
}
LOCK_SOURCE = HERE.parent / "passive-skill-context-executor-repair1/native_launcher.py"
LOCK_DIGEST = "1ccce03fc6d57107690300aeb1f3f6bfb568bc01f781d2ca64e912cf7a92f1aa"
HELPERS = {
    (HERE.parent / "native-observer-helper-repair2/playing-mvp-engine-preflight.py"): (
        "5fdcf1681fe28e08325622873ba00418381ebe44e085eac3273becbfd26cfe1e"
    ),
    (HERE.parent / "native-observer-helper-repair2/playing-mvp-live-preflight.py"): (
        "0259eef01307a8287383a1c65ecca5b4a6f1e8afdd7a69eaf6b1f96703454af6"
    ),
    (HERE.parent / "native-observer-helper-repair2/playing-mvp-readonly-baseline.py"): (
        "12f21a99f8e0c7e0878faf75a3e3ebcdceccb3803594e9ed18a59ae90ab39cd8"
    ),
}
LIMITS = {
    "session_seconds": 90,
    "cleanup_readback_seconds": 35,
    "planning_episodes": 1,
    "completion_calls": 3,
    "decision_calls": 1,
    "npc_clicks": 1,
    "npc_responses": 1,
}
FIELDS = {
    "status",
    "scenario",
    "issued_at",
    "expires_at",
    "fixture_index",
    "limits",
    "authority_hashes",
    "executor_hashes",
    "helper_hashes",
    "source_hashes",
    "private_hashes",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        msg = "authorization object refused"
        raise ValueError(msg)
    return data


def fixed_hashes() -> dict[str, str]:
    return {str(path): value for path, value in ANCHORS.items()}


def executor_hashes() -> dict[str, str]:
    paths = [
        HERE / name
        for name in (
            "guards.py",
            "probe.py",
            "native_launcher.py",
            "pilot_evidence.py",
            "pilot_inputs.py",
        )
    ]
    return {str(path): digest(path) for path in paths}


def source_hashes() -> dict[str, str]:
    freeze = public_json(HERE.parent / "npc-host-integration-independent-freeze.json")
    bindings = {str(ROOT / key): value for key, value in freeze.items() if key.startswith("src/")}
    approved = public_json(
        ROOT / "run/reviews/playing-mvp-passive-skill-context-offline-approved.json"
    )
    for name in ("client.py", "packetdb.py"):
        key = str(ROOT / "spikes/003-clientless-limbs" / name)
        bindings[key] = approved["dependencies"][key]
    return bindings


def verify_hashes(bindings: dict[str, str]) -> None:
    for name, expected in bindings.items():
        path = Path(name)
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file() or digest(path) != expected:
            msg = "authorization dependency drift refused"
            raise ValueError(msg)


def fresh_times(document: dict[str, Any], now: float, *, cleanup: bool = False) -> bool:
    values = (now, document.get("issued_at"), document.get("expires_at"))
    numbers: list[float] = []
    for value in values:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False
        if not -1e12 < value < 1e12 or not math.isfinite(value):
            return False
        numbers.append(float(value))
    issued, expires = numbers[1:]
    allowance = LIMITS["session_seconds"] + LIMITS["cleanup_readback_seconds"] if cleanup else 0
    return bool(
        issued <= now < expires + allowance
        and now - issued <= 300 + allowance
        and expires - issued <= 300
    )


def validate_document(
    document: dict[str, Any], now: float, *, cleanup: bool = False
) -> dict[str, Any]:
    if document.keys() != FIELDS or document.get("status") != STATUS:
        msg = "authorization status/schema refused"
        raise ValueError(msg)
    if not fresh_times(document, now, cleanup=cleanup):
        msg = "authorization future/stale refused"
        raise ValueError(msg)
    if document["scenario"] != SCENARIO or document["limits"] != LIMITS:
        msg = "authorization scenario/budget refused"
        raise ValueError(msg)
    if type(document["fixture_index"]) is not int or document["fixture_index"] not in (0, 1):
        msg = "authorization selected fixture refused"
        raise ValueError(msg)
    return document


def guard(path: Path = AUTHORITY, *, cleanup: bool = False) -> dict[str, Any]:
    if sys.flags.optimize:
        msg = "optimized entry refused"
        raise ValueError(msg)
    document = validate_document(public_json(path), time.time(), cleanup=cleanup)
    verify_parent_authority(document)
    verify_operational_bindings(document)
    verify_private_bindings(document)
    return document


def verify_parent_authority(document: dict[str, Any]) -> None:
    if document["authority_hashes"] != fixed_hashes():
        msg = "authorization parent binding refused"
        raise ValueError(msg)
    verify_hashes(fixed_hashes())
    approved = public_json(ROOT / "run/reviews/npc-host-integration-approved.json")
    if approved["status"] != "BOUNDED_OFFLINE_ACTUAL_NPC_HOST_PHASE_APPROVED":
        msg = "authorization adopted host refused"
        raise ValueError(msg)
    freeze = public_json(HERE.parent / "npc-host-integration-independent-freeze.json")
    if len(freeze) != 420:
        msg = "authorization freeze count refused"
        raise ValueError(msg)
    verify_hashes(freeze)


def verify_operational_bindings(document: dict[str, Any]) -> None:
    for field, expected in (
        ("helper_hashes", {str(path): value for path, value in HELPERS.items()}),
        ("executor_hashes", executor_hashes()),
        ("source_hashes", source_hashes()),
    ):
        if document[field] != expected:
            msg = "authorization input binding refused"
            raise ValueError(msg)
        verify_hashes(expected)
    verify_hashes({str(LOCK_SOURCE): LOCK_DIGEST})


def verify_private_bindings(document: dict[str, Any]) -> None:
    private = document["private_hashes"]
    if not isinstance(private, dict) or private.keys() != {"config", "host_manifest"}:
        msg = "authorization private binding refused"
        raise ValueError(msg)
    for value in private.values():
        if (
            type(value) is not str
            or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value)
        ):
            msg = "authorization private digest refused"
            raise ValueError(msg)
