"""Population generator (ADR-005 society layer, operator criterion 3).

Pure, deterministic generation of a bot population for a world: friend
groups (shared play-style family + mostly-overlapping weekly schedules) and
solo outsiders (their own schedule, disjoint from everyone by construction).

Outputs mirror the existing world artifacts so downstream consumers need no
adaptation:

- ``manifest``: the host-manifest schema of
  ``run/worlds/.../host-manifest.json`` — consumed directly by
  :func:`robots.app.agent_runtime.load_manifest` (and thus ``build_host``).
- ``fixture_sql``: the two-bot ``fixture.sql`` pattern — novice start rows
  (``status_point`` 48, ``skill_point`` 9, Basic Skill lv 9) with account ids
  in the unreserved band below.
- ``summary()``: the human-readable ``population.json``; its ``schedules``
  mapping doubles as the ``--schedule-file`` config ``playing.py`` accepts
  (``{persona_id: [[day, start_hour, end_hour], ...]}``), so reconnects
  resume the same weekly windows per persona.

Everything is derived from ``random.Random`` keyed by spec+seed (string-keyed
seeding is process/platform independent), so the same spec and seed always
generate the identical population. No DB, docker, or server involved.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, final

Window = tuple[int, float, float]  # (day_of_week 0-6, start_hour, end_hour)

ACCOUNT_ID_BASE: Final = 2_200_000  # unreserved band; two-bot fixture uses 2000000+
CHAR_ID_BASE: Final = 300_000  # rAthena auto-creates chars from 150000 upward
LOGIN_HOST: Final = "127.0.0.1"
LOGIN_PORT: Final = 16_900
MAX_GROUP_SIZE: Final = 12  # rAthena party size
# Quarter-hour week grid: 7 days x 96 quarter-hour slots.
QUARTERS_PER_DAY: Final = 96
SLOTS_PER_WEEK: Final = 7 * QUARTERS_PER_DAY


@final
@dataclass(frozen=True, slots=True)
class BuildPath:
    """One class path from run/knowledge/builds/pre-re (digest + sidecar)."""

    family: str
    path: str
    playstyle: str


# Derived from run/knowledge/builds/pre-re/*.json (playstyle_axis per sidecar);
# tests/test_popgen.py pins parity against the sidecars themselves. Everyone is
# emitted at the novice-bootstrap stage now; ``build`` names the class path the
# persona takes later.
BUILDS: Final[tuple[BuildPath, ...]] = (
    BuildPath("novice", "novice-bootstrap", "all (shared 0-zeny bootstrap)"),
    BuildPath("swordman", "swordman-tank", "tank"),
    BuildPath("swordman", "swordman-grinder", "grinder"),
    BuildPath("mage", "mage-grinder", "grinder"),
    BuildPath("mage", "mage-aoe-control", "evasive/lethal"),
    BuildPath("archer", "archer-ds-kiter", "evasive/lethal"),
    BuildPath("archer", "archer-range-grinder", "grinder"),
    BuildPath("thief", "thief-stealth-lethal", "evasive/lethal"),
    BuildPath("thief", "thief-flee-grinder", "grinder"),
    BuildPath("acolyte", "acolyte-support", "support/party"),
    BuildPath("acolyte", "acolyte-battle", "grinder"),
    BuildPath("merchant", "merchant-economy", "merchant-economy"),
    BuildPath("merchant", "merchant-battle", "grinder"),
)

CLASS_FAMILIES: Final[tuple[str, ...]] = (
    "swordman",
    "mage",
    "archer",
    "thief",
    "acolyte",
    "merchant",
)

# Field save points near the starting towns (map, x, y); solos drift there.
FIELD_SAVES: Final[tuple[tuple[str, int, int], ...]] = (
    ("prt_fild08", 167, 352),
    ("prt_fild05", 357, 127),
    ("gef_fild07", 196, 197),
    ("pay_fild04", 181, 174),
)

_NAME_HEADS: Final[tuple[str, ...]] = (
    "Poring",
    "Zeny",
    "Kafra",
    "Luna",
    "Aero",
    "Kiri",
    "Sol",
    "Misu",
    "Rune",
    "Talon",
    "Vel",
    "Yuffie",
    "Nyx",
    "Pipin",
    "Doram",
    "Fluff",
    "Sora",
    "Mika",
    "Rince",
    "Hyu",
)
_NAME_TAILS: Final[tuple[str, ...]] = (
    "nyan",
    "wind",
    "blade",
    "song",
    "drop",
    "muffin",
    "fy",
    "rin",
    "ko",
    "wing",
    "star",
    "punch",
    "hunter",
    "knight",
    "sama",
    "walker",
)


@final
@dataclass(frozen=True, slots=True)
class PopulationSpec:
    """What to generate: friend groups, their size range, and solo outsiders."""

    friend_groups: int
    friends_per_group: tuple[int, int]
    solo_agents: int
    seed: int

    def __post_init__(self) -> None:
        if self.friend_groups < 0:
            msg = "friend_groups must be zero or more"
            raise ValueError(msg)
        lo, hi = self.friends_per_group
        if lo < 2 or hi < lo or hi > MAX_GROUP_SIZE:
            msg = "friends_per_group must be 2 <= min <= max <= 12"
            raise ValueError(msg)
        if self.solo_agents < 0:
            msg = "solo_agents must be zero or more"
            raise ValueError(msg)
        if self.friend_groups == 0 and self.solo_agents == 0:
            msg = "empty population: friend_groups or solo_agents required"
            raise ValueError(msg)


@final
@dataclass(frozen=True, slots=True)
class PersonaProfile:
    """One generated bot identity + its stable weekly connect schedule."""

    persona_id: str
    name: str
    account: str
    password: str
    pincode: str
    sex: str
    group_id: str | None  # None = solo outsider
    playstyle: str
    build: str
    schedule: tuple[Window, ...]
    save_map: str
    save_point: tuple[int, int]


@final
@dataclass(frozen=True, slots=True)
class GeneratedPopulation:
    """The generated personas plus the world-ready artifacts."""

    spec: PopulationSpec
    personas: tuple[PersonaProfile, ...]
    fixture_sql: str
    manifest: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        """Human-readable population.json; ``schedules`` is a schedule-file."""
        groups: dict[str, list[str]] = {}
        for persona in self.personas:
            if persona.group_id is not None:
                groups.setdefault(persona.group_id, []).append(persona.persona_id)
        lo, hi = self.spec.friends_per_group
        solo_count = sum(1 for p in self.personas if p.group_id is None)
        return {
            "schema": 1,
            "generator": "robots.popgen",
            "seed": self.spec.seed,
            "spec": {
                "friend_groups": self.spec.friend_groups,
                "friends_per_group": [lo, hi],
                "solo_agents": self.spec.solo_agents,
            },
            "login_host": self.manifest["login_host"],
            "login_port": self.manifest["login_port"],
            "account_id_base": ACCOUNT_ID_BASE,
            "char_id_base": CHAR_ID_BASE,
            "counts": {
                "personas": len(self.personas),
                "friend_groups": len(groups),
                "solo_agents": solo_count,
            },
            "groups": [
                self._group_row(group_id, members) for group_id, members in sorted(groups.items())
            ],
            "personas": [
                self._persona_row(persona, index) for index, persona in enumerate(self.personas)
            ],
            "schedules": {
                persona.persona_id: [list(w) for w in persona.schedule] for persona in self.personas
            },
        }

    def _group_row(self, group_id: str, members: list[str]) -> dict[str, Any]:
        first = self.personas[
            next(i for i, p in enumerate(self.personas) if p.group_id == group_id)
        ]
        return {
            "group_id": group_id,
            "member_persona_ids": members,
            "save_map": first.save_map,
            "save_point": list(first.save_point),
        }

    def _persona_row(self, persona: PersonaProfile, index: int) -> dict[str, Any]:
        x, y = persona.save_point
        return {
            "persona_id": persona.persona_id,
            "name": persona.name,
            "account": persona.account,
            "group_id": persona.group_id,
            "playstyle": persona.playstyle,
            "build": persona.build,
            "build_stage": "novice-bootstrap",
            "save_map": persona.save_map,
            "save_point": [x, y],
            "weekly_online_hours": weekly_online_hours(persona.schedule),
            "account_id": ACCOUNT_ID_BASE + index,
            "char_id": CHAR_ID_BASE + index,
            "schedule": [list(w) for w in persona.schedule],
        }


# ---- weekly schedule math (quarter-hour slot grid, midnight wrap aware) ----


def schedule_to_slots(windows: Sequence[Window]) -> frozenset[int]:
    """Week slots (day*96 + quarter) covered by ``windows``; wraps midnight."""
    slots: set[int] = set()
    for day, start, end in windows:
        first = day * QUARTERS_PER_DAY + round(start * 4)
        length = QUARTERS_PER_DAY if start == end else round((end - start) % 24 * 4)
        slots.update((first + offset) % SLOTS_PER_WEEK for offset in range(length))
    return frozenset(slots)


def overlap_fraction(left: Sequence[Window], right: Sequence[Window]) -> float:
    """Shared weekly online time vs the smaller schedule (0.0 = disjoint)."""
    left_slots = schedule_to_slots(left)
    right_slots = schedule_to_slots(right)
    if not left_slots or not right_slots:
        return 0.0
    smaller = min(len(left_slots), len(right_slots))
    return len(left_slots & right_slots) / smaller


def weekly_online_hours(windows: Sequence[Window]) -> float:
    """Total online hours per week (window overlaps not double-counted)."""
    return len(schedule_to_slots(windows)) / 4.0


# ---- generation -------------------------------------------------------------


def generate_population(spec: PopulationSpec, seed: int | None = None) -> GeneratedPopulation:
    """Generate the deterministic population for ``spec`` (seed overrides)."""
    actual_seed = spec.seed if seed is None else seed
    rng = random.Random(f"popgen:{actual_seed}")
    tag = actual_seed % 0x10000
    personas: list[PersonaProfile] = []
    used_names: set[str] = set()
    occupied: set[int] = set()  # slots taken so far; solos avoid all of them
    for gi in range(spec.friend_groups):
        group_id = f"pop_{tag:04x}_g{gi:02d}"
        size = rng.randint(spec.friends_per_group[0], spec.friends_per_group[1])
        family = rng.choice(CLASS_FAMILIES)
        sessions = _group_sessions(rng)
        save_point = _plaza_point(rng)
        for mi in range(size):
            persona = _group_member(
                rng,
                persona_id=f"{group_id}m{mi:02d}",
                account=f"pop{tag:04x}_g{gi:02d}m{mi:02d}",
                group_id=group_id,
                family=family,
                sessions=sessions,
                save_point=save_point,
                used_names=used_names,
            )
            personas.append(persona)
            occupied |= schedule_to_slots(persona.schedule)
    for si in range(spec.solo_agents):
        persona = _solo_outsider(
            rng,
            persona_id=f"pop_{tag:04x}_s{si:02d}",
            account=f"pop{tag:04x}_s{si:02d}",
            occupied=occupied,
            used_names=used_names,
        )
        personas.append(persona)
        occupied |= schedule_to_slots(persona.schedule)
    return GeneratedPopulation(
        spec=spec,
        personas=tuple(personas),
        fixture_sql=_fixture_sql(personas),
        manifest=_manifest(personas),
    )


def _group_sessions(rng: random.Random) -> list[tuple[int, int, int]]:
    """Base (day, start_quarter, duration_quarters) evening sessions per group."""
    return [
        (
            rng.randrange(7),
            rng.randrange(60, 92),  # 15:00-22:45, evening play sessions
            rng.randrange(12, 21),  # 3-5 hours
        )
        for _ in range(rng.randint(2, 4))
    ]


def _windows_from_sessions(
    rng: random.Random, sessions: Sequence[tuple[int, int, int]]
) -> tuple[Window, ...]:
    """Per-member jittered copies of the group's base sessions.

    The jitter bounds (start +-1 quarter, duration +-2) keep any two members'
    shared time >= 50% of the smaller schedule by construction.
    """
    windows: list[Window] = []
    for day, start, duration in sessions:
        start_q = (start + rng.randrange(-1, 2)) % QUARTERS_PER_DAY
        duration_q = max(4, duration + rng.randrange(-2, 3))
        end_q = (start_q + duration_q) % QUARTERS_PER_DAY
        windows.append((day, start_q / 4.0, end_q / 4.0))
    return tuple(windows)


def _solo_windows(rng: random.Random, occupied: set[int]) -> tuple[Window, ...]:
    """Independent sessions placed only on slots nobody else occupies."""
    windows: list[Window] = []
    for _ in range(rng.randint(2, 3)):
        duration = rng.randrange(8, 17)  # 2-4 hours
        day = rng.randrange(7)
        first = day * QUARTERS_PER_DAY + rng.randrange(64, 92 - duration)
        start = _find_free_run(occupied, first, duration)
        end = (start + duration) % SLOTS_PER_WEEK
        windows.append(
            (
                start // QUARTERS_PER_DAY,
                (start % QUARTERS_PER_DAY) / 4.0,
                (end % QUARTERS_PER_DAY) / 4.0,
            )
        )
    return tuple(windows)


def _find_free_run(occupied: set[int], first: int, duration: int) -> int:
    """Earliest contiguous free slot run of ``duration`` from ``first`` (wrap)."""
    for offset in range(SLOTS_PER_WEEK - duration):
        start = (first + offset) % SLOTS_PER_WEEK
        run = {(start + k) % SLOTS_PER_WEEK for k in range(duration)}
        if not run & occupied:
            return start
    msg = "no free weekly slot run: population schedule density too high"
    raise RuntimeError(msg)  # pragma: no cover - unreachable at sane densities


def _plaza_point(rng: random.Random) -> tuple[int, int]:
    """A shared prontera plaza save point for one friend group."""
    return 150 + rng.randrange(-10, 11), 150 + rng.randrange(-10, 11)


def _field_point(rng: random.Random) -> tuple[str, tuple[int, int]]:
    """A field save point for a solo outsider."""
    map_name, x, y = rng.choice(FIELD_SAVES)
    return map_name, (x + rng.randrange(-25, 26), y + rng.randrange(-25, 26))


def _draw_name(rng: random.Random, used: set[str]) -> str:
    """A plausible RO-player handle, unique in the population, rAthena-safe."""
    while True:
        head = rng.choice(_NAME_HEADS)
        tail = rng.choice(_NAME_TAILS)
        style = rng.randrange(4)
        if style == 0:
            name = f"{head}{tail.capitalize()}"
        elif style == 1:
            name = f"{head.lower()}_{tail}"
        elif style == 2:
            name = f"xX{head}{tail}Xx"
        else:
            name = f"{head}{tail.capitalize()}{rng.randrange(1, 100)}"
        name = name[:23]
        if name not in used:
            used.add(name)
            return name


def _credentials(rng: random.Random) -> tuple[str, str, str]:
    """(password, pincode, sex) fixture credentials, deterministic."""
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
    password = "".join(rng.choice(alphabet) for _ in range(20))
    pincode = "".join(str(rng.randrange(10)) for _ in range(4))
    return password, pincode, rng.choice(("M", "F"))


def _persona_build(rng: random.Random, family: str | None) -> BuildPath:
    """The class path: one family per friend group, any family for solos."""
    candidates = [
        b for b in BUILDS if b.path != "novice-bootstrap" and (family is None or b.family == family)
    ]
    return rng.choice(candidates)


def _group_member(
    rng: random.Random,
    *,
    persona_id: str,
    account: str,
    group_id: str,
    family: str,
    sessions: Sequence[tuple[int, int, int]],
    save_point: tuple[int, int],
    used_names: set[str],
) -> PersonaProfile:
    """One friend-group member: shared family, shared save site, jittered windows."""
    password, pincode, sex = _credentials(rng)
    build = _persona_build(rng, family)
    return PersonaProfile(
        persona_id=persona_id,
        name=_draw_name(rng, used_names),
        account=account,
        password=password,
        pincode=pincode,
        sex=sex,
        group_id=group_id,
        playstyle=build.playstyle,
        build=build.path,
        schedule=_windows_from_sessions(rng, sessions),
        save_map="prontera",
        save_point=save_point,
    )


def _solo_outsider(
    rng: random.Random,
    *,
    persona_id: str,
    account: str,
    occupied: set[int],
    used_names: set[str],
) -> PersonaProfile:
    """One solo outsider: own schedule (disjoint by construction), field save."""
    password, pincode, sex = _credentials(rng)
    build = _persona_build(rng, None)
    save_map, save_point = _field_point(rng)
    return PersonaProfile(
        persona_id=persona_id,
        name=_draw_name(rng, used_names),
        account=account,
        password=password,
        pincode=pincode,
        sex=sex,
        group_id=None,
        playstyle=build.playstyle,
        build=build.path,
        schedule=_solo_windows(rng, occupied),
        save_map=save_map,
        save_point=save_point,
    )


# ---- artifacts ---------------------------------------------------------------


def _hex(value: str) -> str:
    return f"X'{value.encode().hex()}'"


def _fixture_sql(personas: Sequence[PersonaProfile]) -> str:
    """The two-bot fixture.sql pattern: novice start, status 48, skill 9."""
    lines = ["USE `ragnarok`;"]
    for index, persona in enumerate(personas):
        account_id = ACCOUNT_ID_BASE + index
        char_id = CHAR_ID_BASE + index
        last_x = 150 + 2 * (index % 5)
        save_x, save_y = persona.save_point
        lines.append(
            # nosec B608: fixture-file text, never executed; generated ids only
            "INSERT INTO `login` (`account_id`, `userid`, `user_pass`, `sex`, "  # nosec B608
            "`email`, `group_id`, `state`, `pincode`, `pincode_change`) VALUES "
            f"({account_id}, {_hex(persona.account)}, {_hex(persona.password)}, "
            f"'{persona.sex}', '', 0, 0, {_hex(persona.pincode)}, "
            "UNIX_TIMESTAMP());"
        )
        lines.append(
            # nosec B608: fixture-file text, never executed; generated ids only
            "INSERT INTO `char` (`char_id`, `account_id`, `char_num`, `name`, "  # nosec B608
            "`class`, `base_level`, `job_level`, `str`, `agi`, `vit`, `int`, "
            "`dex`, `luk`, `max_hp`, `hp`, `max_sp`, `sp`, `last_map`, "
            "`last_x`, `last_y`, `save_map`, `save_x`, `save_y`, `sex`, "
            f"`online`, `status_point`, `skill_point`) VALUES ({char_id}, "
            f"{account_id}, 0, {_hex(persona.name)}, 0, 10, 10, 1, 1, 1, 1, "
            f"1, 1, 40, 40, 11, 11, 'prontera', {last_x}, 150, "
            f"'{persona.save_map}', {save_x}, {save_y}, '{persona.sex}', "
            "0, 48, 9);"
        )
        lines.append(
            f"INSERT INTO `skill` (`char_id`, `id`, `lv`, `flag`) VALUES ({char_id}, 1, 9, 0);"  # nosec B608
        )
    return "\n".join(lines) + "\n"


def _manifest(personas: Sequence[PersonaProfile]) -> dict[str, Any]:
    """The host-manifest schema build_host consumes via load_manifest()."""
    return {
        "login_host": LOGIN_HOST,
        "login_port": LOGIN_PORT,
        "accounts": [
            {
                "persona_id": persona.persona_id,
                "account": persona.account,
                "password": persona.password,
                "char_name": persona.name,
                "pincode": persona.pincode,
            }
            for persona in personas
        ],
    }


# ---- CLI ---------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    """Write manifest.json + fixture.sql + population.json into --out-dir."""
    parser = argparse.ArgumentParser(
        prog="python -m robots.popgen",
        description="Generate a deterministic bot population for a world.",
    )
    parser.add_argument("--friend-groups", type=int, default=2)
    parser.add_argument("--friends-min", type=int, default=2)
    parser.add_argument("--friends-max", type=int, default=4)
    parser.add_argument("--solo", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    try:
        population = generate_population(
            PopulationSpec(
                friend_groups=args.friend_groups,
                friends_per_group=(args.friends_min, args.friends_max),
                solo_agents=args.solo,
                seed=args.seed,
            )
        )
    except ValueError as error:
        parser.error(str(error))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(json.dumps(population.manifest, indent=1) + "\n")
    (out_dir / "fixture.sql").write_text(population.fixture_sql)
    (out_dir / "population.json").write_text(json.dumps(population.summary(), indent=1) + "\n")
    sys.stdout.write(f"wrote {len(population.personas)} personas to {args.out_dir}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
